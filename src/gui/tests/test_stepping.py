"""Headless checks of stepping over the protocol (no Qt needed).

    python src/gui/tests/test_stepping.py [path-to-prologu]

The window drives stepping through `prologd_gui.session`, which is a thin layer
over these events, so the wire format is worth checking on its own — and on a
machine without PySide6.  The requests are all written at once: the interpreter
reads a `step` answer when it pauses inside a step point, and a pipe holding the
whole script is exactly the front-end that answers it.

Messages are ASCII: a piped run encodes stdout with the ANSI code page (see
`ai/conventions.md`).
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import protocol  # noqa: E402
from protocol_smoke import check_default_executable, event_names, find, run_session  # noqa: E402

#: Two clauses, one nested goal: enough for call/exit/redo to show up.
PROGRAM = "факт(1).\nфакт(2).\nсчёт(X) :- факт(X).\n?счёт(X).\n"


def steps(events) -> list[dict]:
    return [event for event in events if event.get("event") == "step"]


def describe(event: dict) -> str:
    return (
        f"{event.get('action')} @{event.get('depth')} "
        f"{ascii(event.get('goal', ''))} {event.get('file')}:{event.get('line')}"
    )


def test_a_stepped_run_reports_its_points(executable: str) -> None:
    """`step:true` on the load, then one answer per point."""
    code, events = run_session(
        executable,
        [
            protocol.load_text(PROGRAM, "step.pld", step=True),
            protocol.step_answer("into"),
            protocol.step_answer("into"),
            protocol.step_answer("continue"),
        ],
    )
    assert code == 0, f"exit code {code}: {event_names(events)}"
    points = steps(events)
    assert len(points) >= 3, [describe(point) for point in points]

    # The query's own goal first, at depth 0 and standing on the `?` line of the
    # file; the goal inside the body is one deeper, called from line 3.
    assert (points[0]["action"], points[0]["depth"]) == ("call", 0), describe(points[0])
    assert points[0]["goal"] == "счёт(_1)", ascii(points[0].get("goal"))
    assert (points[0]["file"], points[0]["line"]) == ("step.pld", 4), describe(points[0])
    assert (points[1]["action"], points[1]["depth"]) == ("call", 1), describe(points[1])
    assert points[1]["goal"] == "факт(_1)", ascii(points[1].get("goal"))
    assert (points[1]["file"], points[1]["line"]) == ("step.pld", 3), describe(points[1])
    # `exit` names no goal — the front-end pops what `call` pushed — and its depth
    # is the depth of the goal that is leaving.
    assert points[2]["action"] == "exit" and points[2]["depth"] == 1, describe(points[2])
    # The run went on to its end after `continue`.  The answers arrive one line at
    # a time since task_49, in the order they were printed.
    assert find(events, "result", found=True), events
    answers = [event["text"] for event in events if event.get("event") == "output"]
    assert "X=1\n" in answers and "X=2\n" in answers, events
    assert answers.index("X=1\n") < answers.index("X=2\n"), answers
    print("ok: a stepped run reports call/exit points with depth and position")


def test_stepping_over_skips_the_points_inside(executable: str) -> None:
    code, events = run_session(
        executable,
        [
            protocol.load_text("а(1).\nб(X):-а(X).\n?б(1).\n", "over.pld", step=True),
            protocol.step_answer("over"),
            # `over` still stops when the goal itself is left, which is what tells
            # the user that the call is done — and then a `continue` runs on.
            protocol.step_answer("continue"),
        ],
    )
    assert code == 0, f"exit code {code}: {event_names(events)}"
    points = steps(events)
    # One call for `б` and then the `exit` of `б` itself: the `а(1)` call and exit
    # that happened in between are not stops, and they were not reported at all.
    assert [point["action"] for point in points] == ["call", "exit"], [
        describe(point) for point in points
    ]
    assert points[1]["depth"] == 0, describe(points[1])
    assert find(events, "result", found=True), events
    print("ok: 'over' runs to the end of the goal, and the points inside it are skipped")


def test_stopping_a_step_ends_the_query_like_an_interrupt(executable: str) -> None:
    code, events = run_session(
        executable,
        [
            protocol.load_text("а(1).\n?а(1).\n", "stop.pld", step=True),
            protocol.step_answer("stop"),
        ],
    )
    assert code == 3, f"expected the interrupted exit code, got {code}"
    failure = find(events, "error", kind="runtime")
    assert failure.get("line") == 2, failure
    assert not steps(events)[1:], "the run went on after `stop`"
    print("ok: 'stop' at a point ends the query with the exit code of an interrupt")


def test_a_step_answer_with_nothing_waiting_is_an_error(executable: str) -> None:
    code, events = run_session(executable, [protocol.step_answer("into")])
    assert find(events, "error", kind="protocol"), events
    assert code == 0, f"exit code {code}"
    print("ok: an answer with nothing waiting is reported as a protocol error")


def test_a_runtime_error_names_its_clause(executable: str) -> None:
    code, events = run_session(
        executable,
        [protocol.load_text("дели(Х):-БОЛЬШЕ(1,#1/0#).\n?дели(1).\n", "boom.pld")],
    )
    assert code == 3, f"exit code {code}"
    failure = find(events, "error", kind="runtime")
    assert failure.get("file") == "boom.pld", failure
    assert (failure.get("line"), failure.get("column")) == (1, 1), failure
    print("ok: a runtime error carries the file, the line and the column")


def test_a_parse_error_carries_its_position(executable: str) -> None:
    code, events = run_session(executable, [protocol.load_text("факт(1\n", "bad.pld")])
    assert code == 2, f"exit code {code}"
    failure = find(events, "error", kind="parse")
    assert failure.get("file") == "bad.pld", failure
    assert failure.get("line", 0) >= 1, failure
    print("ok: a parse error carries its file and line")


def test_the_trace_arrives_as_its_own_events(executable: str) -> None:
    code, events = run_session(
        executable,
        [protocol.load_text("факт(1).\n?факт(1).\n", "trace.pld", trace=True)],
    )
    assert code == 0, f"exit code {code}"
    traced = [event["text"] for event in events if event.get("event") == "trace"]
    assert traced, event_names(events)
    assert any("Согласуется с" in line for line in traced), traced
    # …and the program's own output does not contain it: the trace went to the
    # front-end, not into the output stream.
    printed = "".join(
        event["text"] for event in events if event.get("event") == "output"
    )
    assert "Согласуется" not in printed, printed
    print("ok: the trace arrives as trace events, apart from the program's output")


def main(argv: list[str]) -> int:
    executable = argv[1] if len(argv) > 1 else check_default_executable()
    print(f"interpreter: {executable}")
    test_a_stepped_run_reports_its_points(executable)
    test_stepping_over_skips_the_points_inside(executable)
    test_stopping_a_step_ends_the_query_like_an_interrupt(executable)
    test_a_step_answer_with_nothing_waiting_is_an_error(executable)
    test_a_runtime_error_names_its_clause(executable)
    test_a_parse_error_carries_its_position(executable)
    test_the_trace_arrives_as_its_own_events(executable)
    print("all stepping checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
