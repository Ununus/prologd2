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

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui.editor import CURRENT_LINE_BACKGROUND, QUERY_MARKER_WIDTH, CodeEditor  # noqa: E402
from prologd_gui.keywords import Keywords  # noqa: E402


#: The reserved names the margin checks need; the rule itself is checked without
#: Qt in `test_queries.py`.
MARGIN_TABLE = Keywords(
    [
        {"name": "факт", "kind": "predicate", "arities": [1]},
        {"name": "сумма", "kind": "predicate", "arities": [2]},
    ]
)


def make_editor(text: str = "") -> CodeEditor:
    editor = CodeEditor()
    editor.setPlainText(text)
    return editor


def margin_editor(text: str) -> CodeEditor:
    """An editor with a real geometry: a margin click needs laid-out blocks."""
    editor = CodeEditor()
    editor.resize(500, 300)
    editor.show()
    editor.set_completion_keywords(MARGIN_TABLE)
    editor.setPlainText(text)
    QTest.qWait(1)
    return editor


def marker_point(editor: CodeEditor, line: int) -> QPoint:
    """A point inside the marker column of a 1-based line, in margin coordinates."""
    block = editor.document().findBlockByNumber(line - 1)
    geometry = editor.blockBoundingGeometry(block).translated(editor.contentOffset())
    return QPoint(4, int(geometry.top() + geometry.height() / 2))


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
    # One selection for the mark and one for the current line's band (task_29):
    # the band is painted first, so a mark on the same line still stands out.
    selections = editor.extraSelections()
    backgrounds = [selection.format.background().color().name() for selection in selections]
    assert "#ffd9d9" in backgrounds, backgrounds
    assert backgrounds[0] != "#ffd9d9", "the current-line band must stay underneath"
    marked = [selection for selection in selections
              if selection.format.background().color().name() == "#ffd9d9"]
    assert len(marked) == 1, backgrounds

    editor.mark_error_line(None)
    assert editor.error_line() is None
    assert [selection.format.background().color().name()
            for selection in editor.extraSelections()] == [CURRENT_LINE_BACKGROUND], (
        "only the caret's line is left"
    )

    # A line past the end is marked on the last line that exists: `непарные скобки`
    # is reported where the input ran out, which for a file that ends without its
    # closing bracket is one line past the end — and a mark that points at nothing
    # is not a mark at all.
    editor.mark_error_line(99)
    assert editor.error_line() == editor.document().blockCount(), editor.error_line()
    assert any(
        selection.format.background().color().name() == "#ffd9d9"
        for selection in editor.extraSelections()
    )

    # An edit clears the marks: a red line over text it no longer describes would
    # be a lie about where the program broke.
    editor.setPlainText("а\n")
    assert editor.error_line() is None
    assert [selection.format.background().color().name()
            for selection in editor.extraSelections()] == [CURRENT_LINE_BACKGROUND]
    print("ok: the error line is marked, clamped to a line that exists, and cleared by an edit")


def test_the_current_line_band_can_be_switched_off() -> None:
    """task_29: the pale band behind the caret's line, and its switch."""
    editor = make_editor("а\nб\n")
    assert [selection.format.background().color().name()
            for selection in editor.extraSelections()] == [CURRENT_LINE_BACKGROUND]

    # It follows the caret.
    cursor = editor.textCursor()
    cursor.setPosition(3)
    editor.setTextCursor(cursor)
    selections = editor.extraSelections()
    assert len(selections) == 1
    assert selections[0].cursor.blockNumber() == 1, selections[0].cursor.blockNumber()

    editor.set_current_line(False)
    assert editor.extraSelections() == [], "the band stayed behind"
    editor.set_current_line(True)
    assert len(editor.extraSelections()) == 1
    print("ok: the current line is banded while the switch is on, and only then")


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


def test_the_margin_marks_questions_and_nothing_else() -> None:
    """The icon column exists only for questions (task_36)."""
    editor = margin_editor("?факт(1).\n% ?сумма(5, С).\nфакт(2).\n%! С=15\n")
    assert editor.query_statements() == {1: "?факт(1).", 2: "?сумма(5, С)."}

    # The mark column is an addition to the numbers, and there is no margin at
    # all without line numbers.
    with_numbers = editor.line_number_area_width()
    expected = QUERY_MARKER_WIDTH + 12 + editor.fontMetrics().horizontalAdvance("9")
    assert with_numbers == expected, (with_numbers, expected)
    editor.set_line_numbers(False)
    assert editor.line_number_area_width() == 0
    assert editor.statement_at_margin_point(marker_point(editor, 1)) is None
    editor.set_line_numbers(True)
    assert editor.line_number_area_width() == with_numbers
    print("ok: the margin marks ?-lines and is exactly the marker column wider")


def test_a_click_on_a_marker_runs_the_question_and_changes_nothing_else() -> None:
    """The mark is clicked with a real mouse event, and the run is a signal.

    A caret that moved or a document that turned modified when a *run* was
    asked for would be an edit the user never made.
    """
    editor = margin_editor("?факт(1).\nфакт(2).\n")
    requested: list[str] = []
    editor.queryRequested.connect(requested.append)

    assert editor.statement_at_margin_point(marker_point(editor, 1)) == "?факт(1)."
    QTest.mouseClick(editor._margin, Qt.MouseButton.LeftButton, pos=marker_point(editor, 1))
    assert requested == ["?факт(1)."], requested

    # A click where there is no marker does nothing at all.
    QTest.mouseClick(editor._margin, Qt.MouseButton.LeftButton, pos=marker_point(editor, 2))
    assert requested == ["?факт(1)."], requested

    # The caret is put somewhere of the user's own, then the mark is clicked:
    # nothing of that state may change.
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position() + 2)
    editor.setTextCursor(cursor)
    editor.document().setModified(False)
    before = editor.textCursor().position()
    QTest.mouseClick(editor._margin, Qt.MouseButton.LeftButton, pos=marker_point(editor, 1))
    assert requested == ["?факт(1).", "?факт(1)."]
    assert editor.textCursor().position() == before, "the caret moved"
    assert not editor.textCursor().hasSelection(), "the selection changed"
    assert not editor.document().isModified(), "the document was marked modified"
    print("ok: a margin click asks for the statement and leaves the editing state alone")


def test_a_click_on_the_numbers_is_not_a_run() -> None:
    editor = margin_editor("?факт(1).\n")
    requested: list[str] = []
    editor.queryRequested.connect(requested.append)
    point = marker_point(editor, 1)
    QTest.mouseClick(
        editor._margin,
        Qt.MouseButton.LeftButton,
        pos=QPoint(point.x() + QUERY_MARKER_WIDTH, point.y()),
    )
    assert requested == [], requested
    print("ok: a click on the numbers is not a run")


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
    test_the_current_line_band_can_be_switched_off()
    test_a_document_made_outside_takes_the_pane_font()
    test_the_margin_marks_questions_and_nothing_else()
    test_a_click_on_a_marker_runs_the_question_and_changes_nothing_else()
    test_a_click_on_the_numbers_is_not_a_run()
    print("all editor checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
