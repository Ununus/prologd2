"""Headless checks of the keyword table (the `ready` event and `--list-keywords`).

    python src/gui/tests/test_keywords.py [path-to-prologd]

Qt-free and framework-free, like the other front-end tests.  Without an
interpreter argument the script looks for the newest build and, if there is
none, checks only the pure-Python part instead of failing.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import protocol  # noqa: E402
from prologd_gui.keywords import Keywords  # noqa: E402


def decode_one(payload: dict) -> dict:
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    events = list(protocol.Decoder().feed(line.encode("utf-8")))
    assert len(events) == 1, events
    return events[0]


def test_decode_with_keywords() -> None:
    event = decode_one(
        {
            "event": "ready",
            "protocol": protocol.PROTOCOL_VERSION,
            "version": "2.0.0",
            "keywords": [
                {"name": "ВЫВОД", "kind": "predicate", "arities": [], "variadic": True},
                {"name": "НАЙТИВСЕ", "kind": "predicate", "arities": [3]},
                {"name": "УМНОЖЕНИЕ", "kind": "predicate", "arities": [3, 4]},
                {"name": "mod", "kind": "operator", "arities": []},
                {"name": "ИМПОРТ", "kind": "directive", "arities": []},
            ],
        }
    )
    table = Keywords.from_event(event)
    assert len(table) == 5
    assert table.names() == ["mod", "ВЫВОД", "ИМПОРТ", "НАЙТИВСЕ", "УМНОЖЕНИЕ"]

    assert table.is_reserved("НАЙТИВСЕ")
    assert "ИМПОРТ" in table
    assert not table.is_reserved("нет_такого")
    assert table.arity("УМНОЖЕНИЕ") == (3, 4)
    assert table.arity("mod") == ()
    assert table.arity("нет_такого") == ()

    assert table.labels("ВЫВОД") == ("ВЫВОД/+",)
    assert table.labels("УМНОЖЕНИЕ") == ("УМНОЖЕНИЕ/3", "УМНОЖЕНИЕ/4")
    assert table.labels("mod") == ("mod",)
    assert table.labels("нет_такого") == ()
    assert table.all_labels() == [
        "mod",
        "ВЫВОД/+",
        "ИМПОРТ",
        "НАЙТИВСЕ/3",
        "УМНОЖЕНИЕ/3",
        "УМНОЖЕНИЕ/4",
    ]

    assert [keyword.name for keyword in table.predicates()] == ["ВЫВОД", "НАЙТИВСЕ", "УМНОЖЕНИЕ"]
    assert [keyword.name for keyword in table] == table.names()
    print("ok: decoding, lookups and labels")


def test_decode_without_keywords() -> None:
    """An interpreter older than protocol 2 must still parse, with no names."""
    event = decode_one({"event": "ready", "protocol": 1, "version": "2.0.0"})
    table = Keywords.from_event(event)
    assert len(table) == 0
    assert table.names() == []
    assert table.arity("ВЫП") == ()
    assert not table.is_reserved("ВЫП")
    assert table.all_labels() == []
    print("ok: a ready event without keywords is empty, not an error")


def test_junk_entries_are_ignored() -> None:
    """The table is data from another process: drop what does not fit."""
    table = Keywords.from_event(
        {
            "keywords": [
                {"name": ""},
                "не объект",
                {"name": "x", "arities": "нет"},
                {"name": "y", "arities": [1, "два", None]},
            ]
        }
    )
    assert table.names() == ["x", "y"]
    assert table.arity("x") == ()
    assert table.arity("y") == (1,)
    print("ok: malformed entries are ignored")


# The three candidates in `main.py`, `protocol_smoke.py` and here are the same
# list in three copies; task_26 moves it into one Qt-free module.
def find_executable(argv: list[str]) -> str | None:
    if len(argv) > 1:
        return argv[1]
    root = pathlib.Path(__file__).resolve().parents[3]
    for candidate in (
        root / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "linux-release" / "src" / "cli" / "prologd",
        root / "build" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "src" / "cli" / "prologd",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def test_against_the_interpreter(executable: str) -> None:
    """The CLI listing and the `ready` event are the same table, same order."""
    listing = subprocess.run(
        [executable, "--list-keywords"], capture_output=True, check=True
    )
    lines = listing.stdout.decode("utf-8").splitlines()
    assert lines, "no keywords printed"

    session = subprocess.run(
        [executable, "--protocol", "json"],
        input=protocol.quit_session(),
        capture_output=True,
        check=True,
    )
    events = list(protocol.Decoder().feed(session.stdout))
    ready = next(event for event in events if event.get("event") == "ready")
    assert ready["protocol"] == protocol.PROTOCOL_VERSION, ready
    table = Keywords.from_event(ready)

    assert table.all_labels() == lines, (table.all_labels(), lines)
    assert table.is_reserved("НАЙТИВСЕ")
    assert table.arity("НАЙТИВСЕ") == (3,)
    assert "НАЙТИВСЕ/3" in lines
    print(f"ok: {len(table)} reserved names, CLI and protocol agree")


def main(argv: list[str]) -> int:
    test_decode_with_keywords()
    test_decode_without_keywords()
    test_junk_entries_are_ignored()

    executable = find_executable(argv)
    if executable is None:
        print("skipped: no prologd build found, pass its path to check the interpreter")
        return 0
    print(f"interpreter: {executable}")
    test_against_the_interpreter(executable)
    print("all keyword checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
