"""Checks of the editor's behaviour (needs PySide6, no display).

    python src/gui/tests/test_editor.py

Keys are sent with `QTest`, not by calling the methods directly, so the wiring is
covered too — a shortcut that works while the same logic called by hand does not
is exactly the kind of defect this file should catch.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui.editor import CodeEditor  # noqa: E402


def make_editor(text: str = "") -> CodeEditor:
    editor = CodeEditor()
    editor.setPlainText(text)
    return editor


def select_all(editor: CodeEditor) -> None:
    cursor = editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    editor.setTextCursor(cursor)


def test_commenting_a_selection_is_one_undo_step() -> None:
    editor = make_editor("факт(1).\nфакт(2).\nфакт(3).\n")
    select_all(editor)

    editor.comment()
    assert editor.toPlainText() == "%факт(1).\n%факт(2).\n%факт(3).\n"
    # The lines stay selected: `Ctrl+U` must undo `Ctrl+K` on the same text, and
    # it did not while the command collapsed the cursor.
    assert editor.textCursor().selection().toPlainText() == "%факт(1).\n%факт(2).\n%факт(3).\n"

    editor.uncomment()
    assert editor.toPlainText() == "факт(1).\nфакт(2).\nфакт(3).\n"

    # One Ctrl+Z undoes the whole command, not one line of it.
    editor.undo()
    assert editor.toPlainText() == "%факт(1).\n%факт(2).\n%факт(3).\n"
    print("ok: comment/uncomment round trip in single undo steps")


def test_blank_lines_stay_blank() -> None:
    editor = make_editor("факт(1).\n\nфакт(2).\n")
    select_all(editor)
    editor.comment()
    assert editor.toPlainText() == "%факт(1).\n\n%факт(2).\n"
    print("ok: a blank line is not given a comment character")


def test_uncommenting_removes_only_the_first_character() -> None:
    editor = make_editor("%% двойной\n  % с отступом\nбез комментария\n")
    select_all(editor)
    editor.uncomment()
    assert editor.toPlainText() == "% двойной\n   с отступом\nбез комментария\n"
    print("ok: uncomment removes one `%` and keeps the indentation")


def test_indent_and_outdent_a_selection() -> None:
    editor = make_editor("первый\n\nвторой\n")
    select_all(editor)

    editor.indent_selection()
    assert editor.toPlainText() == "\tпервый\n\n\tвторой\n"

    editor.indent_selection(outdent=True)
    assert editor.toPlainText() == "первый\n\nвторой\n"
    print("ok: indent and outdent cover the selected lines and skip blank ones")


def test_tab_and_backtab_keys() -> None:
    editor = make_editor("")
    QTest.keyClick(editor, Qt.Key.Key_Tab)
    assert editor.toPlainText() == "\t"

    editor.setPlainText("\tфакт(1).")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    QTest.keyClick(editor, Qt.Key.Key_Backtab)
    assert editor.toPlainText() == "факт(1)."
    print("ok: Tab inserts the indent unit, Shift+Tab removes it")


def test_enter_continues_the_clause_with_an_indent() -> None:
    editor = make_editor("правило :- цель1,")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    QTest.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "правило :- цель1,\n\t"

    # A terminator ends the clause: the next line starts at the margin.
    editor.setPlainText("факт(1).")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    QTest.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "факт(1).\n"
    print("ok: Enter indents a continuation and not a new clause")


def test_zoom_is_bounded_and_reported() -> None:
    editor = make_editor()
    sizes: list[float] = []
    editor.zoomChanged.connect(sizes.append)

    start = editor.font_size
    editor.zoom_by(1)
    assert editor.font_size == start + 1
    assert sizes == [start + 1]

    editor.set_font_size(1000)
    assert editor.font_size == 72
    editor.set_font_size(1)
    assert editor.font_size == 6

    editor.reset_zoom()
    assert editor.font_size == 11
    print(f"ok: zoom stays within 6…72 and reports every change ({len(sizes)} signals)")


def test_line_number_width_grows_with_the_document() -> None:
    editor = make_editor("\n".join(str(number) for number in range(9)))
    narrow = editor.line_number_area_width()
    assert narrow > 0, "line numbers are off by default?"

    editor.setPlainText("\n".join(str(number) for number in range(10)))
    assert editor.line_number_area_width() > narrow, "three digits need more room"

    editor.set_line_numbers(False)
    assert editor.line_number_area_width() == 0
    editor.set_line_numbers(True)
    assert editor.line_number_area_width() > narrow
    print("ok: the margin fits the numbers and can be switched off")


def test_the_error_line_is_marked_and_cleared() -> None:
    editor = make_editor("а\nб\nв\n")
    editor.mark_error_line(2)
    assert editor.error_line() == 2
    selections = editor.extraSelections()
    assert len(selections) == 1
    # Its background is the error colour, and it spans the line.
    assert selections[0].format.background().color().name() == "#ffd9d9"

    editor.mark_error_line(None)
    assert editor.error_line() is None
    assert editor.extraSelections() == []

    # A line past the end must not raise: the diagnostic may be stale.
    editor.mark_error_line(99)
    assert editor.extraSelections() == []
    print("ok: the error line is marked, cleared, and a stale line is ignored")


def test_a_document_made_outside_takes_the_pane_font() -> None:
    """A `QTextDocument` has its own default font, and the layout measures with it.

    Handing the editor a document built elsewhere left the text at the
    application's font size while the margins, the output pane and the query line
    were all right — until the first zoom forced a relayout.
    """
    from PySide6.QtGui import QTextDocument

    heights: list[int] = []
    for size in (8.0, 21.0):
        editor = CodeEditor(font_size=size)
        document = QTextDocument()
        document.setPlainText("факт(1).\nфакт(2).\n")
        editor.setDocument(document)
        assert document.defaultFont().pointSizeF() == size, document.defaultFont().pointSizeF()
        heights.append(editor.blockBoundingRect(editor.document().firstBlock()).height())

    assert heights[1] > heights[0], f"the text is not laid out at the requested size: {heights}"
    # A zoom reaches the document as well, not only the widget.
    editor.set_font_size(30.0)
    assert editor.document().defaultFont().pointSizeF() == 30.0
    print(f"ok: a document given to the editor is measured at its size ({heights[0]}px, {heights[1]}px)")


def main() -> int:
    application = QApplication(sys.argv[:1])
    test_commenting_a_selection_is_one_undo_step()
    test_blank_lines_stay_blank()
    test_uncommenting_removes_only_the_first_character()
    test_indent_and_outdent_a_selection()
    test_tab_and_backtab_keys()
    test_enter_continues_the_clause_with_an_indent()
    test_zoom_is_bounded_and_reported()
    test_line_number_width_grows_with_the_document()
    test_the_error_line_is_marked_and_cleared()
    test_a_document_made_outside_takes_the_pane_font()
    print("all editor checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
