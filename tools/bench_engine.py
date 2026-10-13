#!/usr/bin/env python3
"""Measure the interpreter on the workloads that have limits worth watching.

Written for task_38, where two of these programs used to kill the process (a
deep environment chain and a deep list are both *released* through `shared_ptr`
destructors) and one of them is what a long search costs in memory.  Every
number in `ai/task_38_engine_limits.md` comes from this script, so a measurement
can be repeated instead of remembered.

Usage:
    python tools/bench_engine.py                 # the default sizes
    python tools/bench_engine.py --quick         # small, for a smoke run
    python tools/bench_engine.py --only queens   # one workload, by label substring
    python tools/bench_engine.py --exe build/windows-msvc/src/cli/Release/prologu.exe

task_42 added two workloads: a dispatch-bound step loop (the per-goal lookup
cost) and the N-queens search (few clauses with heavy bodies — the shape
first-argument indexing cannot prune) plus structured fact heads (the shape it
can).  See `ai/decisions.md`, ADR-017, for what they measured.

Output is ASCII only: when this script is piped through `Select-String`, a
redirect or a log file, Python encodes stdout with the ANSI code page, and a raw
Cyrillic message would raise `UnicodeEncodeError` while printing the failure it
was reporting (the rule is in `ai/conventions.md`).
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile
import time

# The recursion shape matters: the base clause does *not* cut, so a choice point
# survives at the deepest level.  That is the shape whose release used to walk
# the whole frame chain on the C++ stack (0xC00000FD after a correct answer).
DEEP_RECURSION = """\
л(0).
л(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), л(Н1).
?ТИХО, л({depth}), ВЫВОД(ok), ПС.
"""

DEEP_TERM = """\
{facts}?ТИХО, НАЙТИВСЕ(И, ф(И), _), ВЫВОД(ok), ПС.
"""

FACTS = """\
{facts}?ТИХО, ф({query}), ВЫВОД(ok), ПС.
"""

# Dispatch-bound (task_42 stage 1): fourteen trivial built-in goals and one user
# predicate per step, so the per-goal lookup cost is a large share of the work.
DISPATCH = """\
проверка(0) :- !.
проверка(Н) :- БОЛЬШЕ(Н, 0), РАВНО(1, 1), РАВНО(2, 2), РАВНО(3, 3),
    РАВНО(4, 4), РАВНО(5, 5), РАВНО(6, 6), РАВНО(7, 7), РАВНО(8, 8),
    РАВНО(9, 9), РАВНО(10, 10), РАВНО(11, 11), РАВНО(12, 12),
    СЛОЖЕНИЕ(М, 1, Н), проверка(М).
?ТИХО, проверка({steps}), ВЫВОД(ok), ПС.
"""

# Structured fact heads (task_42 stage 2): the same scan as FACTS, but every
# failed attempt compares a compound head, which is the work first-argument
# indexing would skip.
STRUCTURED_FACTS = """\
{facts}?ТИХО, ф(к({query})), ВЫВОД(ok), ПС.
"""

# Few clauses, heavy bodies (task_42 stage 2): the N-queens search, where every
# clause head shallow-matches and the work is in the body — the shape indexing
# cannot prune (measured; see ai/decisions.md, ADR-017).
QUEENS = """\
ферзь(0, N, [], A) :- список(N, A), !.
ферзь(N, M, [[N,X]|A], C) :- ферзь(#N-1#, #M+1#, A, B), выбрать(X, B, C),
                            можно([N,X], A).
список(0, []).
список(N, [N|A]) :- список(#N-1#, A).
выбрать(X, [X|A], A).
выбрать(X, [Y|A], [Y|B]) :- выбрать(X, A, B).
можно(_, []) :- !.
можно(A, [B|C]) :- НЕ(нельзя(A, B)), можно(A, C).
нельзя([A,_], [A,_]) :- !.
нельзя([_,A], [_,A]) :- !.
нельзя([A,B], [C,D]) :- abs(#A-C#, E), abs(#B-D#, F), РАВНО(E, F).
abs(X, Y) :- МЕНЬШЕ(X, 0), !, РАВНО(Y, #-1*X#).
abs(X, X).
ферзи(N, A) :- ферзь(N, 0, A, []).
?ТИХО, НАЙТИВСЕ(A, ферзи({size}, A), _), ВЫВОД(ok), ПС.
"""


def peak_megabytes(pid: int) -> float | None:
    """Peak working set of a live process, in megabytes."""
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes as wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32")
        psapi = ctypes.WinDLL("psapi")
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return None
            return counters.PeakWorkingSetSize / 1e6
        finally:
            kernel.CloseHandle(handle)
    try:  # POSIX: the child reports its own peak, sampled after it finished.
        import resource

        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        return usage.ru_maxrss / 1024.0
    except (ImportError, AttributeError):
        return None


def measure(executable: pathlib.Path, work: pathlib.Path, name: str, source: str,
            extra_args: list[str]) -> tuple[float, float | None, int, str, str]:
    path = work / f"{name}.pld"
    path.write_text(source, encoding="utf-8", newline="\n")
    started = time.perf_counter()
    child = subprocess.Popen([str(executable), *extra_args, "-s", str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8")
    peak = 0.0
    while child.poll() is None:
        value = peak_megabytes(child.pid)
        if value:
            peak = max(peak, value)
        time.sleep(0.02)
    out, err = child.communicate()
    seconds = time.perf_counter() - started
    return seconds, (peak or None), child.returncode, out.strip(), err.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe", default=None, help="path to the prologu executable")
    parser.add_argument("--quick", action="store_true", help="small sizes, for a smoke run")
    parser.add_argument("--only", default=None,
                        help="run only the workloads whose label contains this text")
    args = parser.parse_args()

    def wanted(label: str) -> bool:
        return args.only is None or args.only in label

    root = pathlib.Path(__file__).resolve().parents[1]
    candidates = [
        args.exe,
        root / "build/windows-msvc/src/cli/Release/prologu.exe",
        root / "build/src/cli/prologu",
        root / "build/windows-msvc/src/cli/Debug/prologu.exe",
    ]
    executable = next((pathlib.Path(c) for c in candidates if c and pathlib.Path(c).is_file()), None)
    if executable is None:
        print("prologu not found; pass --exe or build it first")
        return 2

    depth_sizes = [10_000, 50_000] if args.quick else [50_000, 100_000, 400_000]
    list_sizes = [10_000] if args.quick else [20_000, 60_000]
    fact_sizes = [10_000] if args.quick else [100_000]
    dispatch_steps = [10_000] if args.quick else [100_000]
    structured_sizes = [20_000] if args.quick else [50_000]
    queens_sizes = [6] if args.quick else [8]
    # The depth guard would stop these programs before the release is exercised,
    # which is the point of the measurement.
    unlimited = ["--max-depth", "0"]

    work = pathlib.Path(tempfile.mkdtemp(prefix="prologd_bench_"))
    rows: list[tuple[str, float, float | None, int]] = []

    for depth in depth_sizes:
        label = f"recursion depth {depth}"
        if not wanted(label):
            continue
        seconds, peak, code, out, err = measure(executable, work, f"recursion_{depth}",
                                                DEEP_RECURSION.format(depth=depth), unlimited)
        rows.append((label, seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! recursion depth {depth}: exit {code} (0x{code & 0xFFFFFFFF:08X}) "
                  f"out={out[:20]!r} err={err[:60]!r}")

    for size in list_sizes:
        label = f"list of {size} cells"
        if not wanted(label):
            continue
        facts = "".join(f"ф({index}).\n" for index in range(1, size + 1))
        seconds, peak, code, out, err = measure(executable, work, f"list_{size}",
                                                DEEP_TERM.format(facts=facts), unlimited)
        rows.append((label, seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! list {size}: exit {code} (0x{code & 0xFFFFFFFF:08X}) err={err[:60]!r}")

    for size in fact_sizes:
        facts = "".join(f"ф({index}).\n" for index in range(1, size + 1))
        for label, index in ((f"{size} facts, first clause", 1),
                             (f"{size} facts, last clause", size)):
            if not wanted(label):
                continue
            seconds, peak, code, out, err = measure(executable, work, f"facts_{size}_{index}",
                                                    FACTS.format(facts=facts, query=index),
                                                    unlimited)
            rows.append((label, seconds, peak, code))

    for steps in dispatch_steps:
        label = f"dispatch {steps} steps"
        if not wanted(label):
            continue
        seconds, peak, code, out, err = measure(executable, work, f"dispatch_{steps}",
                                                DISPATCH.format(steps=steps), unlimited)
        rows.append((label, seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! dispatch {steps}: exit {code} (0x{code & 0xFFFFFFFF:08X}) "
                  f"out={out[:20]!r} err={err[:60]!r}")

    for size in structured_sizes:
        facts = "".join(f"ф(к({index})).\n" for index in range(1, size + 1))
        for label, index in ((f"structured {size} facts, first", 1),
                             (f"structured {size} facts, last", size)):
            if not wanted(label):
                continue
            seconds, peak, code, out, err = measure(executable, work, f"structured_{size}_{index}",
                                                    STRUCTURED_FACTS.format(facts=facts,
                                                                            query=index),
                                                    unlimited)
            rows.append((label, seconds, peak, code))
            if code != 0 or out != "ok":
                print(f"  ! structured {size}/{index}: exit {code} "
                      f"(0x{code & 0xFFFFFFFF:08X}) err={err[:60]!r}")

    for size in queens_sizes:
        label = f"queens {size}"
        if not wanted(label):
            continue
        seconds, peak, code, out, err = measure(executable, work, f"queens_{size}",
                                                QUEENS.format(size=size), unlimited)
        rows.append((label, seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! queens {size}: exit {code} (0x{code & 0xFFFFFFFF:08X}) "
                  f"out={out[:20]!r} err={err[:60]!r}")

    if not rows:
        print(f"no workload matched --only {args.only!r}")
        return 2

    print(f"{executable}")
    print(f"{'workload':>26} {'time':>9} {'peak':>10}  exit")
    for label, seconds, peak, code in rows:
        peak_text = f"{peak:7.1f} MB" if peak else "        -"
        print(f"{label:>26} {seconds:8.2f}s {peak_text}  {code}")
    return 0 if all(code == 0 for _, _, _, code in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
