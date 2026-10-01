"""Headless smoke test for the interpreter protocol (no Qt needed).

    python src/gui/tests/protocol_smoke.py [path-to-prologd]

Exercises exactly what `prologd_gui.session` does — spawn the interpreter with
`--protocol json`, feed requests, read events — so the wire format can be checked
on a machine without PySide6 installed.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import protocol  # noqa: E402


def run_session(executable: str, requests: list[bytes], timeout: float = 30.0):
    """Runs one session to completion and returns (exit code, events)."""
    process = subprocess.Popen(
        [executable, "--protocol", "json"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = b"".join(requests) + protocol.quit_session()
    stdout, stderr = process.communicate(payload, timeout=timeout)
    events = list(protocol.Decoder().feed(stdout))
    if not events and stderr:
        raise AssertionError(f"no events, stderr: {stderr.decode('utf-8', 'replace')}")
    return process.returncode, events


def event_names(events) -> list[str]:
    return [str(event.get("event")) for event in events]


def find(events, name: str, **fields):
    for event in events:
        if event.get("event") != name:
            continue
        if all(event.get(key) == value for key, value in fields.items()):
            return event
    raise AssertionError(f"no {name} event with {fields}; got {event_names(events)}")


def check_default_executable() -> str:
    root = pathlib.Path(__file__).resolve().parents[3]
    for candidate in (
        root / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "linux-release" / "src" / "cli" / "prologd",
        root / "build" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "src" / "cli" / "prologd",
    ):
        if candidate.exists():
            return str(candidate)
    raise SystemExit("build prologd first, or pass its path as an argument")


def main(argv: list[str]) -> int:
    executable = argv[1] if len(argv) > 1 else check_default_executable()
    print(f"interpreter: {executable}")

    code, events = run_session(
        executable,
        [
            protocol.load_text("факт(1).\nфакт(2).\n?факт(X).\n"),
            protocol.query("?факт(2)."),
        ],
    )
    assert code == 0, f"exit code {code}"
    ready = find(events, "ready")
    assert ready["protocol"] == protocol.PROTOCOL_VERSION, ready
    reserved = {entry["name"] for entry in ready["keywords"]}
    assert {"НАЙТИВСЕ", "ВЫП", "ПС"} <= reserved, sorted(reserved)
    # One `output` event per written line (task_49): the answers of a query arrive
    # as they are printed — before the `result` that ends the query — so a
    # front-end shows the output of a run while it is still running.  The text is
    # the same as it always was, only the granularity is finer.
    answers = [event["text"] for event in events if event.get("event") == "output"]
    assert answers == ["X=1\n", "X=2\n", "ДА\n"], events
    assert len([e for e in events if e.get("event") == "result"]) == 2, events
    assert events[-1].get("event") == "bye", events
    print("ok: load, query, output and result events")
    print("ok: the output of a run arrives one line at a time")
    print(f"ok: ready carries {len(reserved)} reserved names")

    code, events = run_session(
        executable,
        [
            protocol.load_text("?ВВОДСТР(X), ВЫВОД(X).\n"),
            protocol.input_answer("ответ"),
        ],
    )
    assert code == 0, f"exit code {code}"
    assert find(events, "input_request", kind="line"), events
    assert find(events, "output", text="ответX=ответ\n"), events
    print("ok: interactive input round trip")

    code, events = run_session(executable, [protocol.load_text("это не программа")])
    assert code == 2, f"expected exit code 2, got {code}"
    assert find(events, "error", kind="parse"), events
    print("ok: parse failure is reported as an event with exit code 2")

    # task_46: the caps travel with the load, and the message names the limit and
    # its value.  It names nothing else: the interpreter knows nothing about the
    # window or its command line (ADR-020), so «where do I raise it» is answered
    # by whichever front-end put the number there.
    code, events = run_session(
        executable,
        [protocol.load_text("цикл :- цикл.\n?цикл.\n", limits={"maxSteps": 1000})],
        timeout=60.0,
    )
    assert code == 3, f"expected the run to end with a diagnostic, got {code}"
    stopped = find(events, "error", kind="runtime")
    message = stopped["message"]
    assert "предел шагов" in message, message
    assert "1000" in message, message
    assert "--max-steps" not in message and "настройках" not in message, message
    print("ok: a limit travels with the load and names itself when it fires")

    # A field of the wrong *type* is the front-end's mistake, not a reason to take
    # the session down: the request is answered with an error and the next one is
    # served (a negative limit is exactly such a mistake, and `value<size_t>`
    # throws on it).
    code, events = run_session(
        executable,
        [
            protocol.encode_request(cmd="load", text="факт(1).\n",
                                    limits={"maxSteps": -1}),
            # The refused load defined nothing, so the next request brings its own
            # program: what is checked is that the session reads it at all.
            protocol.load_text("?БОЛЬШЕ(2, 3).\n"),
        ],
    )
    assert code == 0, f"exit code {code}"
    assert find(events, "error", kind="protocol"), events
    assert find(events, "loaded"), events
    print("ok: a request with a bad field is an error event, and the session goes on")

    print("all protocol checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
