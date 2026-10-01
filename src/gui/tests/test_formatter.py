"""Headless check of the formatter over the protocol (no Qt needed).

    python src/gui/tests/test_formatter.py [path-to-prologd]

What the window's **Форматировать** will do is done here without a window: the
text goes out as a `format` request and the laid-out text comes back in a
`formatted` event.  The grammar lives in prlib and its golden tests are on the
C++ side; these checks are about the wire — the request's flags, the answer, and
the error of a source that does not parse.
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


EXAMPLE = "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\nфункция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n"


def test_the_soft_shape_comes_back_over_the_wire(executable: str) -> None:
    code, events = run_session(
        executable, [protocol.format_text(EXAMPLE, mode="soft")]
    )
    assert code == 0, f"exit code {code}"
    formatted = find(events, "formatted")
    assert formatted["text"] == (
        "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
        "\tфункция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n"
    ), ascii(formatted["text"])
    assert formatted["changed"] is True
    print("ok: the soft shape arrives in a formatted event")


def test_the_hard_shape_and_its_settings(executable: str) -> None:
    code, events = run_session(
        executable, [protocol.format_text(EXAMPLE, mode="hard", indent=2, unit="spaces")]
    )
    assert code == 0, f"exit code {code}"
    text = find(events, "formatted")["text"]
    assert text == (
        "правило(а,б,с):-функция1(а,б,с),\n"
        "        функция2(а,б,с),\n"
        "        функция3(а,б,с),\n"
        "        функция4(а,б,с),\n"
        "        функция5(а,б,с),\n"
        "        функция6(а,б,с).\n"
    ), ascii(text)
    # A narrow soft width breaks earlier: the settings reach the formatter.
    # At 40 the second goal moves down, and the third still fits beside it.
    code, events = run_session(
        executable, [protocol.format_text(EXAMPLE, mode="soft", width=40)]
    )
    narrow = find(events, "formatted")["text"]
    assert narrow != text
    assert "\n\tфункция2" in narrow and ", функция3" in narrow, ascii(narrow)
    # At 20 even the first goal cannot stay on the head's line.
    code, events = run_session(
        executable, [protocol.format_text(EXAMPLE, mode="soft", width=20)]
    )
    tiny = find(events, "formatted")["text"]
    assert tiny.startswith("правило(а,б,с):-\n\tфункция1"), ascii(tiny)
    print("ok: the hard shape, indentation units and the width reach the formatter")


def test_a_selection_is_formatted_up_to_its_last_complete_goal(executable: str) -> None:
    fragment = "факт(1).\nсчёт(Х):-факт(Х), ещё(Х), оста"
    code, events = run_session(
        executable, [protocol.format_text(fragment, mode="hard", selection=True)]
    )
    assert code == 0, f"exit code {code}"
    text = find(events, "formatted")["text"]
    assert text == "факт(1).\nсчёт(Х):-факт(Х),\n\tещё(Х), оста", ascii(text)
    print("ok: a fragment is formatted up to its last complete goal")


def test_a_broken_source_answers_with_an_error_and_the_session_lives_on(
    executable: str,
) -> None:
    code, events = run_session(
        executable,
        [
            protocol.format_text("цель(Х:-часть(Х).\n", mode="hard"),
            protocol.format_text("факт(1).\n", mode="hard"),
        ],
    )
    assert code == 0, f"exit code {code}"  # the session did not fail
    error = find(events, "error", kind="format")
    assert error["severity"] == "error"
    assert error["file"] == "<format>"
    assert error["line"] == 1
    assert [name for name in event_names(events)].count("formatted") == 1
    assert find(events, "formatted")["text"] == "факт(1).\n"
    print("ok: a broken source is reported, and the next request is answered")


def test_a_hard_layout_is_turned_back_by_the_soft_mode(executable: str) -> None:
    """«Из жёсткого обратно в мягкое»: the soft shape is rebuilt, not kept."""
    line_text = (
        "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с), "
        "функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n"
    )
    code, events = run_session(
        executable,
        [
            protocol.format_text(EXAMPLE, mode="hard"),
            protocol.format_text(EXAMPLE, mode="line"),
        ],
    )
    assert code == 0, f"exit code {code}"
    formatted = [event for event in events if event.get("event") == "formatted"]
    assert len(formatted) == 2
    hard_text = formatted[0]["text"]
    assert formatted[1]["text"] == line_text, ascii(formatted[1]["text"])
    # The hard layout laid out again with soft is the soft shape, not the hard one.
    code, events = run_session(executable, [protocol.format_text(hard_text, mode="soft")])
    assert code == 0, f"exit code {code}"
    back = find(events, "formatted")["text"]
    assert back == (
        "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
        "\tфункция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n"
    ), ascii(back)
    print("ok: hard and line formats convert back through the soft mode")


def test_ready_names_the_new_version(executable: str) -> None:
    code, events = run_session(executable, [])
    assert code == 0, f"exit code {code}"
    ready = find(events, "ready")
    assert ready["protocol"] == protocol.PROTOCOL_VERSION == 9
    print("ok: ready announces protocol 9")


def test_the_caret_carries_over_from_the_old_text_to_the_new() -> None:
    """The window's side of the formatter: old offsets onto the new text."""
    from prologd_gui import formatter

    old = "факт(1).\nцель(Х) :- часть(Х),   ещё(Х).\n"
    new = "факт(1).\nцель(Х):-часть(Х), ещё(Х).\n"
    caret = old.index("часть") + 2
    mapped = formatter.map_positions(old, new, [caret, 0, len(old)])
    assert mapped == [new.index("часть") + 2, 0, len(new)], mapped
    # Anything past the end is clamped: the answer is all there is to map onto.
    assert formatter.map_positions(old, new, [len(old) + 50]) == [len(new)]
    print("ok: the caret maps from the old text onto the formatted one")


def main(argv: list[str]) -> int:
    executable = argv[1] if len(argv) > 1 else check_default_executable()
    print(f"interpreter: {executable}")
    test_the_caret_carries_over_from_the_old_text_to_the_new()
    test_the_soft_shape_comes_back_over_the_wire(executable)
    test_the_hard_shape_and_its_settings(executable)
    test_a_selection_is_formatted_up_to_its_last_complete_goal(executable)
    test_a_broken_source_answers_with_an_error_and_the_session_lives_on(executable)
    test_a_hard_layout_is_turned_back_by_the_soft_mode(executable)
    test_ready_names_the_new_version(executable)
    print("all formatter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
