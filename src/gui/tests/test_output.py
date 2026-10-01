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


def test_an_unfinished_line_is_written_at_once() -> None:
    """The prompt of `ВЫВОД`/`ВВОДСИМВ` has no newline — and must still be seen.

    Holding it back until the newline that arrives with the *answer* is exactly how
    a program looked as if it asked before printing anything.
    """
    buffer = panels.LineBuffer()
    pieces = buffer.feed("Введите символ")
    assert [(piece.text, piece.complete) for piece in pieces] == [("Введите символ", False)]
    assert buffer.pending() == "Введите символ"

    # The rest of the line continues it, and only the *new* text is handed over:
    # the pane has written the first half already.
    pieces = buffer.feed("!\n")
    assert [(piece.text, piece.complete) for piece in pieces] == [("!", True)]
    assert buffer.pending() == ""
    print("ok: an unfinished line goes out at once, and the rest continues it")


def test_chunks_are_split_and_joined() -> None:
    buffer = panels.LineBuffer()
    pieces = buffer.feed("один\nдва\nтри\n")
    assert [(piece.text, piece.complete) for piece in pieces] == [
        ("один", True),
        ("два", True),
        ("три", True),
    ]
    assert buffer.pending() == "", "a trailing newline leaves nothing behind"

    # A chunk that ends *on* the newline is complete; the next one opens a line.
    assert [piece.text for piece in buffer.feed("четыре\n")] == ["четыре"]
    assert [(piece.text, piece.complete) for piece in buffer.feed("пять")] == [("пять", False)]
    assert [(piece.text, piece.complete) for piece in buffer.feed("шесть\n")] == [("шесть", True)]
    print("ok: chunks are joined until a newline ends the line")


def test_a_change_of_kind_closes_the_open_line() -> None:
    buffer = panels.LineBuffer()
    assert [(piece.text, piece.complete) for piece in buffer.feed("вывод без ПС")] == [
        ("вывод без ПС", False)
    ]
    pieces = buffer.feed("--- заметка ---\n", panels.NOTE)
    assert [(piece.text, piece.kind, piece.complete) for piece in pieces] == [
        ("", panels.OUTPUT, True),  # the bare newline that closes the half-line
        ("--- заметка ---", panels.NOTE, True),
    ], "the half-line belongs to the program, not to the note"
    print("ok: a note closes the program's half-line and keeps its own colour")


def test_flush_and_reset() -> None:
    buffer = panels.LineBuffer()
    buffer.feed("хвост")
    assert [(piece.text, piece.complete) for piece in buffer.flush()] == [("", True)], (
        "flush only closes the line: its text is on screen already"
    )
    assert buffer.pending() == ""
    assert buffer.flush() == [], "nothing is closed twice"

    buffer.feed("что-то\n")
    buffer.reset()
    assert buffer.pending() == ""
    print("ok: flush closes the open line once, and reset forgets everything")


def test_the_pane_colours_lines_and_keeps_a_bounded_history() -> None:
    application = QApplication(sys.argv[:1])
    pane = panels.OutputPane(line_limit=100)
    try:
        pane.feed("программа\n", panels.OUTPUT)
        pane.feed("> 42\n", panels.ECHO)
        pane.feed("--- загрузка ---\n", panels.NOTE)
        assert pane.toPlainText().splitlines() == ["программа", "> 42", "--- загрузка ---"]

        # A prompt without a newline is on screen at once — the defect the user hit:
        # it used to wait for the newline that comes with the answer.
        pane.feed("Введите символ")
        assert pane.toPlainText().endswith("Введите символ"), ascii(pane.toPlainText())
        assert pane.pending() == "Введите символ", "the open line is remembered"

        # The echo is painted, the program's answer is left plain.  The colour sits
        # in the *character* format; `layout().formats()` holds block-level ones
        # (images and the like) and is empty here.
        def colour_of(pane, block: int) -> str:
            cursor = QTextCursor(pane.document())
            cursor.setPosition(pane.document().findBlockByNumber(block).position())
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, cursor.MoveMode.KeepAnchor)
            return cursor.charFormat().foreground().color().name()

        assert colour_of(pane, 1) == pane.kind_colors()[panels.ECHO], "the echo has no colour"
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


def test_following_the_end_can_be_forbidden() -> None:
    """task_29's «Следить за выводом»: off, new lines do not move the view.

    The pane already stops following by itself when the reader scrolls up; the
    switch is the other direction — «не уводите взгляд» — so it has to hold even
    while the view *is* at the end.
    """
    # The application of the check above, not a second one: Qt has one per
    # process, and a second is a hard error rather than a fresh window.
    application = QApplication.instance() or QApplication(sys.argv[:1])
    # A limit nothing reaches: the history trimming moves the view too (the oldest
    # lines go, and Qt keeps the visible anchor), and this check is about the
    # *following*, which must be the only thing that can move it here.
    pane = panels.OutputPane(line_limit=1000)
    try:
        for number in range(200):
            pane.feed(f"строка {number}\n")
        bar = pane.verticalScrollBar()
        assert bar.maximum() > 0, "nothing to scroll: the check would pass for free"
        assert pane.following() is True

        pane.set_follow_output(False)
        assert bar.value() == bar.maximum(), "the view must start at the end"
        was = bar.value()
        pane.feed("хвост\n")
        assert bar.value() == was, "the view moved with the switch off"
        assert bar.maximum() > was, "the text did not grow: the check proves nothing"

        pane.set_follow_output(True)
        bar.setValue(bar.maximum())
        pane.feed("ещё\n")
        assert bar.value() == bar.maximum(), "with the switch on it must follow again"
        print("ok: the output pane follows the end, and the switch can forbid it")
    finally:
        pane.deleteLater()
        del application


def main() -> int:
    if QApplication is None:
        print("skipped: PySide6 is not installed")
        return 0
    test_an_unfinished_line_is_written_at_once()
    test_chunks_are_split_and_joined()
    test_a_change_of_kind_closes_the_open_line()
    test_flush_and_reset()
    test_the_pane_colours_lines_and_keeps_a_bounded_history()
    test_following_the_end_can_be_forbidden()
    print("all output checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
