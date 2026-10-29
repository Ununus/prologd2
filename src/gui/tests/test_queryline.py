"""Checks of the goal field: its history and the editor's completion (task_50).

    python src/gui/tests/test_queryline.py

The goal line under the editor gets two things the main editor already had: a
history walked by `Up`/`Down` (twenty commands), and the completion popup with
the *same* names — the reserved ones and the current document's predicates.
Driven by real key events, because the defects live in the wiring: an `Enter`
that submits while the popup is open, an `Up` that moves the caret instead of
the history.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.keywords import Keywords  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - main() reports it
    QApplication = None  # type: ignore[assignment]


DOCUMENT = "ученик(вова).\nученик(данил).\n?ученик(X).\n"

RESERVED = Keywords.from_list_lines("НАЙТИВСЕ/3\nВЫВОД/+")


def type_text(line, text: str) -> None:
    """Types through `keyPressEvent`, the way a keyboard does."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    for character in text:
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_unknown,
            Qt.KeyboardModifier.NoModifier,
            character,
        )
        QApplication.sendEvent(line, event)


def key(line, key, modifier=None) -> None:
    from PySide6.QtTest import QTest

    if modifier is None:
        QTest.keyClick(line, key)
    else:
        QTest.keyClick(line, key, modifier)


def test_the_history_records_and_walks() -> None:
    from PySide6.QtCore import Qt

    from prologd_gui.editor import QueryLine

    line = QueryLine()
    for text in ("?ученик(X).", "?НАЙТИВСЕ(Y, ученик(Y), Z)."):
        line.setText(text)
        key(line, Qt.Key.Key_Return)
    assert line.history() == ["?ученик(X).", "?НАЙТИВСЕ(Y, ученик(Y), Z)."], line.history()

    # `Up` goes older, clamps at the oldest; `Down` returns and restores the draft.
    line.setText("")
    key(line, Qt.Key.Key_Up)
    assert line.text() == "?НАЙТИВСЕ(Y, ученик(Y), Z).", line.text()
    key(line, Qt.Key.Key_Up)
    assert line.text() == "?ученик(X).", line.text()
    key(line, Qt.Key.Key_Up)
    assert line.text() == "?ученик(X).", "the oldest is the floor"
    key(line, Qt.Key.Key_Down)
    assert line.text() == "?НАЙТИВСЕ(Y, ученик(Y), Z).", line.text()
    key(line, Qt.Key.Key_Down)
    assert line.text() == "", "past the newest is the draft again"
    print("ok: Enter records a goal, Up/Down walk it, Down past the newest is the draft")


def test_the_history_keeps_twenty_and_drops_duplicates() -> None:
    from PySide6.QtCore import Qt

    from prologd_gui.editor import QueryLine

    line = QueryLine()
    for number in range(25):
        line.setText(f"?цель({number}).")
        key(line, Qt.Key.Key_Return)
    assert len(line.history()) == QueryLine.HISTORY_LIMIT, len(line.history())
    assert line.history()[0] == "?цель(5).", "the oldest five were dropped"
    assert line.history()[-1] == "?цель(24).", line.history()[-1]

    # The same goal twice is not two entries.
    before = len(line.history())
    line.setText("?цель(24).")
    key(line, Qt.Key.Key_Return)
    assert len(line.history()) == before, "a repeated goal was recorded twice"
    print("ok: the history is capped at twenty and a repeated goal is not recorded")


def test_completion_offers_the_editor_names() -> None:
    from PySide6.QtCore import Qt

    from prologd_gui.editor import QueryLine

    line = QueryLine(document_text=lambda: DOCUMENT)
    line.set_completion_keywords(RESERVED)
    line.set_auto_complete_after(1)

    # The document's own predicate and the reserved names, with their arities.
    type_text(line, "уче")
    assert line.completion_visible(), "the popup did not open"
    assert "ученик/1" in line.completion_labels(), line.completion_labels()

    line.setText("")
    type_text(line, "НАЙ")
    assert "НАЙТИВСЕ/3" in line.completion_labels(), line.completion_labels()

    # Enter takes the highlighted row and inserts the call form, caret after `(`.
    key(line, Qt.Key.Key_Return)
    assert line.text() == "НАЙТИВСЕ(, , )", line.text()
    assert line.cursorPosition() == len("НАЙТИВСЕ") + 1, line.cursorPosition()

    # A bracket typed before accepting is kept (part 238): the form brings the name
    # only, and the caret stops inside the call.
    line.setText("")
    type_text(line, "?НАЙТИ(")
    assert line.completion_visible(), "typing `(` closed the popup"
    assert line.completion_labels() == ["НАЙТИВСЕ/3"], line.completion_labels()
    key(line, Qt.Key.Key_Return)
    assert line.text() == "?НАЙТИВСЕ(", line.text()
    assert line.cursorPosition() == len("?НАЙТИВСЕ("), line.cursorPosition()
    print("ok: the goal field offers the editor's names and inserts the call form")


def test_escape_and_arrows_leave_the_line_alone() -> None:
    from PySide6.QtCore import Qt

    from prologd_gui.editor import QueryLine

    line = QueryLine(document_text=lambda: DOCUMENT)
    line.set_completion_keywords(RESERVED)
    type_text(line, "уче")
    assert line.completion_visible()

    key(line, Qt.Key.Key_Escape)
    assert not line.completion_visible(), "Escape did not close the popup"
    assert line.text() == "уче", "Escape changed the goal"
    print("ok: Escape closes the popup without touching the goal")


def main() -> int:
    if QApplication is None:
        print("skipped: PySide6 is not installed, so the goal field is not checked")
        return 0
    application = QApplication(sys.argv[:1])
    test_the_history_records_and_walks()
    test_the_history_keeps_twenty_and_drops_duplicates()
    test_completion_offers_the_editor_names()
    test_escape_and_arrows_leave_the_line_alone()
    del application
    print("all goal-field checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
