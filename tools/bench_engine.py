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
    python tools/bench_engine.py --exe build/windows-msvc/src/cli/Release/prologd.exe

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
{facts}?ТИХО, НАЙТИВСЁ(И, ф(И), _), ВЫВОД(ok), ПС.
"""

FACTS = """\
{facts}?ТИХО, ф({query}), ВЫВОД(ok), ПС.
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
    parser.add_argument("--exe", default=None, help="path to the prologd executable")
    parser.add_argument("--quick", action="store_true", help="small sizes, for a smoke run")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    candidates = [
        args.exe,
        root / "build/windows-msvc/src/cli/Release/prologd.exe",
        root / "build/src/cli/prologd",
        root / "build/windows-msvc/src/cli/Debug/prologd.exe",
    ]
    executable = next((pathlib.Path(c) for c in candidates if c and pathlib.Path(c).is_file()), None)
    if executable is None:
        print("prologd not found; pass --exe or build it first")
        return 2

    depth_sizes = [10_000, 50_000] if args.quick else [50_000, 100_000, 400_000]
    list_sizes = [10_000] if args.quick else [20_000, 60_000]
    fact_sizes = [10_000] if args.quick else [100_000]
    # The depth guard would stop these programs before the release is exercised,
    # which is the point of the measurement.
    unlimited = ["--max-depth", "0"]

    work = pathlib.Path(tempfile.mkdtemp(prefix="prologd_bench_"))
    rows: list[tuple[str, float, float | None, int]] = []

    for depth in depth_sizes:
        seconds, peak, code, out, err = measure(executable, work, f"recursion_{depth}",
                                                DEEP_RECURSION.format(depth=depth), unlimited)
        rows.append((f"recursion depth {depth}", seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! recursion depth {depth}: exit {code} (0x{code & 0xFFFFFFFF:08X}) "
                  f"out={out[:20]!r} err={err[:60]!r}")

    for size in list_sizes:
        facts = "".join(f"ф({index}).\n" for index in range(1, size + 1))
        seconds, peak, code, out, err = measure(executable, work, f"list_{size}",
                                                DEEP_TERM.format(facts=facts), unlimited)
        rows.append((f"list of {size} cells", seconds, peak, code))
        if code != 0 or out != "ok":
            print(f"  ! list {size}: exit {code} (0x{code & 0xFFFFFFFF:08X}) err={err[:60]!r}")

    for size in fact_sizes:
        facts = "".join(f"ф({index}).\n" for index in range(1, size + 1))
        for label, index in (("first", 1), ("last", size)):
            seconds, peak, code, out, err = measure(executable, work, f"facts_{size}_{label}",
                                                    FACTS.format(facts=facts, query=index),
                                                    unlimited)
            rows.append((f"{size} facts, {label} clause", seconds, peak, code))

    print(f"{executable}")
    print(f"{'workload':>26} {'time':>9} {'peak':>10}  exit")
    for label, seconds, peak, code in rows:
        peak_text = f"{peak:7.1f} MB" if peak else "        -"
        print(f"{label:>26} {seconds:8.2f}s {peak_text}  {code}")
    return 0 if all(code == 0 for _, _, _, code in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
