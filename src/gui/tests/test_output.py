"""Checks of the output pane: the held tail, the colours, the bounded history.

    python src/gui/tests/test_output.py

The classic defect in a pane fed by arbitrary chunks is the *tail*: text that
reaches the window without a newline must be held until the rest of the line
arrives, or the last line of `ВЫВОД` output disappears.  `panels.LineBuffer` is
Qt-free so that part is tested directly; the pane itself is checked for the
colours and the truncation marker.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import panels  # noqa: E402

from PySide6.QtGui import QTextCursor  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - main() reports it
    QApplication = None  # type: ignore[assignment]


def test_a_partial_line_waits_for_its_newline() -> None:
    buffer = panels.LineBuffer()
    assert buffer.feed("да") == [], "half a line is not a line"
    assert buffer.pending() == "да"
    lines = buffer.feed("!\nвторое\n")
    assert [line.text for line in lines] == ["да!", "второе"]
    assert buffer.pending() == ""
    assert all(line.kind == panels.OUTPUT for line in lines)
    print("ok: a line without a newline is held until the rest of it arrives")


def test_several_lines_and_an_exact_newline() -> None:
    buffer = panels.LineBuffer()
    lines = buffer.feed("один\nдва\nтри\n")
    assert [line.text for line in lines] == ["один", "два", "три"]
    assert buffer.pending() == "", "a trailing newline leaves nothing behind"

    # A chunk that ends *on* the newline is complete; the next chunk starts a line.
    assert [line.text for line in buffer.feed("четыре\n")] == ["четыре"]
    assert buffer.feed("пять") == []
    assert [line.text for line in buffer.feed("шесть\n")] == ["пятьшесть"]
    print("ok: chunks are joined until a newline ends the line")


def test_a_change_of_kind_closes_the_held_line() -> None:
    buffer = panels.LineBuffer()
    assert buffer.feed("вывод без ПС") == []
    lines = buffer.feed("--- заметка ---\n", panels.NOTE)
    assert [line.text for line in lines] == ["вывод без ПС", "--- заметка ---"]
    assert [line.kind for line in lines] == [panels.OUTPUT, panels.NOTE], (
        "the half-line belongs to the program, not to the note"
    )
    print("ok: a note closes the program's half-line and keeps its own colour")


def test_flush_and_reset() -> None:
    buffer = panels.LineBuffer()
    buffer.feed("хвост")
    lines = buffer.flush()
    assert [line.text for line in lines] == ["хвост"], "the run ended mid-line"
    assert buffer.pending() == ""
    assert buffer.flush() == [], "nothing is written twice"

    buffer.feed("что-то\n")
    buffer.reset()
    assert buffer.pending() == ""
    print("ok: flush writes the last half-line once, and reset forgets everything")


def test_the_pane_colours_lines_and_keeps_a_bounded_history() -> None:
    application = QApplication(sys.argv[:1])
    pane = panels.OutputPane(line_limit=100)
    try:
        pane.feed("программа\n", panels.OUTPUT)
        pane.feed("> 42\n", panels.ECHO)
        pane.feed("--- загрузка ---\n", panels.NOTE)
        assert pane.toPlainText().splitlines() == ["программа", "> 42", "--- загрузка ---"]
        assert pane.pending() == ""

        # The echo is painted, the program's answer is left plain.  The colour sits
        # in the *character* format; `layout().formats()` holds block-level ones
        # (images and the like) and is empty here.
        def colour_of(pane, block: int) -> str:
            cursor = QTextCursor(pane.document())
            cursor.setPosition(pane.document().findBlockByNumber(block).position())
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, cursor.MoveMode.KeepAnchor)
            return cursor.charFormat().foreground().color().name()

        assert colour_of(pane, 1) == panels.KIND_COLORS[panels.ECHO], "the echo has no colour"
        assert colour_of(pane, 0) == "#000000", "the answer must stay plain: it is the data"

        # A runaway program: the oldest lines go, and the pane says so.
        for number in range(300):
            pane.feed(f"строка {number}\n")
        assert pane.truncated() is True
        assert pane.document().firstBlock().text() == panels.TRUNCATED_MARK
        assert pane.document().blockCount() <= pane.line_limit() + 1

        # Following the end, until the user scrolls up.
        assert pane.following() is True
        pane.verticalScrollBar().setValue(0)
        assert pane.following() is False, "reading the top must stop the follow"
        pane.feed("ещё\n")
        assert pane.pending() == ""

        pane.reset()
        assert pane.toPlainText() == "" and pane.truncated() is False
        assert pane.following() is True
        print("ok: the pane colours by kind, truncates with a marker, and follows the end")
    finally:
        pane.deleteLater()
        del application


def main() -> int:
    if QApplication is None:
        print("skipped: PySide6 is not installed")
        return 0
    test_a_partial_line_waits_for_its_newline()
    test_several_lines_and_an_exact_newline()
    test_a_change_of_kind_closes_the_held_line()
    test_flush_and_reset()
    test_the_pane_colours_lines_and_keeps_a_bounded_history()
    print("all output checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
