"""Checks of the plain-text search: the engine, then the bar in a window.

    python src/gui/tests/test_search.py

The first half needs no Qt and no build.  What goes wrong in a search is
arithmetic: an offset that points into the folded copy instead of the text, a match
counted twice, a wrap that never comes, and a «Заменить всё» that finds its own
output.  These are those cases, on a program that looks like the ones the users
write.

The second half is the bar itself, offscreen: an action that stayed disabled, a
highlight left behind after `Esc`, a «Заменить всё» that needs one `Ctrl+Z` per
match.  It opens a window but starts no interpreter.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import actions, search  # noqa: E402
from test_window import discard_changes, make_window  # noqa: E402

PROGRAM = "факт(1).\nфакт(2).\nфактик(3).\n#X+1#\nФАКТ(4).\n"

#: What the window half types: three `факт`, the third inside `фактик`.
BAR_PROGRAM = "факт(1).\nфакт(2).\nфактик(3).\n"


def test_matches_are_offsets_into_the_text_itself() -> None:
    # 0, 9 and 18 are the three lowercase "факт" — the last inside "фактик";
    # "ФАКТ" at 35 is the fourth only when the case is ignored.
    exact = search.Options(match_case=True)
    assert search.matches(PROGRAM, "факт", exact) == [0, 9, 18]
    assert PROGRAM[0:4] == "факт" and PROGRAM[18:22] == "факт"
    assert search.matches(PROGRAM, "ФАКТ", exact) == [35]
    assert PROGRAM[35:39].lower() == "факт"

    # The default ignores the case — and the offsets still point into the original
    # text, not into the folded copy that was compared.
    assert search.matches(PROGRAM, "факт") == [0, 9, 18, 35]
    assert search.matches(PROGRAM, "факт") == search.matches(
        PROGRAM, "факт", search.Options(match_case=False)
    )
    print("ok: matches are offsets into the text, whatever the case")


def test_whole_word_and_special_characters() -> None:
    # "фактик" is not the whole word "факт", but "факт(1)" is.
    assert search.matches(PROGRAM, "факт", search.Options(match_case=True, whole_word=True)) == [
        0,
        9,
    ]

    # No regular expressions: `#`, `+` and `.` are ordinary characters here.
    assert search.matches(PROGRAM, "#X+1#") == [29]
    assert search.matches(PROGRAM, "X+1") == [30]
    assert search.matches(PROGRAM, ".") == [7, 16, 27, 42]
    assert search.matches(PROGRAM, "") == [], "an empty question matches nothing"
    print("ok: whole words and characters that a regular expression would eat")


def test_next_and_previous_wrap_round() -> None:
    assert search.next_match(PROGRAM, "факт", 0) == 0
    assert search.next_match(PROGRAM, "факт", 1) == 9
    assert search.next_match(PROGRAM, "факт", 10) == 18
    assert search.next_match(PROGRAM, "факт", 19) == 35
    assert search.next_match(PROGRAM, "факт", 36) == 0, "from the last match it wraps"
    assert search.next_match(PROGRAM, "нет-такого", 0) is None

    assert search.previous_match(PROGRAM, "факт", 10) == 9
    assert search.previous_match(PROGRAM, "факт", 0) == 0, "the caret sits on the first match"
    # Backwards it wraps too — with a match that is behind the caret only.
    assert search.previous_match(PROGRAM, "ФАКТ", 0, search.Options(match_case=True)) == 35
    assert search.previous_match(PROGRAM, "нет-такого", 0) is None
    print("ok: the search wraps in both directions, and says so when nothing matches")


def test_a_search_can_be_limited_to_a_selection() -> None:
    span = search.Options(span=(9, 27))
    assert search.matches(PROGRAM, "факт", span) == [9, 18]
    assert search.count(PROGRAM, "факт", span) == 2

    # A span outside the text is clamped rather than crashing.
    assert search.matches(PROGRAM, "факт", search.Options(span=(100, 200))) == []
    assert search.matches(PROGRAM, "факт", search.Options(span=(-5, 4))) == [0]
    print("ok: the search can be limited to a selection, and a wild span is clamped")


def test_replace_all_never_scans_its_own_output() -> None:
    # Case-sensitively here: the fourth "ФАКТ" is a different predicate.
    replaced, how_many = search.replace_all(
        PROGRAM, "факт", "правило", search.Options(match_case=True)
    )
    assert how_many == 3
    assert replaced.startswith("правило(1).\nправило(2).\nправилоик(3).\n")
    assert "факт" not in replaced and "ФАКТ" in replaced

    # The classic runaway: the replacement contains the needle.
    grown, how_many = search.replace_all("ааа", "а", "аа")
    assert (grown, how_many) == ("аааааа", 3), (grown, how_many)

    unchanged, how_many = search.replace_all(PROGRAM, "нет-такого", "x")
    assert (unchanged, how_many) == (PROGRAM, 0)
    print("ok: 'replace all' counts each match once and cannot run away")


def main() -> int:
    test_matches_are_offsets_into_the_text_itself()
    test_whole_word_and_special_characters()
    test_next_and_previous_wrap_round()
    test_a_search_can_be_limited_to_a_selection()
    test_replace_all_never_scans_its_own_output()
    test_a_caret_inside_a_word_finds_that_word()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed, so the bar is not checked")
        print("all search checks passed")
        return 0

    application = QApplication(sys.argv[:1])
    test_the_five_search_commands_are_live()
    test_the_two_magnifiers_are_on_the_right_controls()
    test_the_bar_opens_on_the_word_under_the_caret()
    test_f3_walks_the_matches_and_reports_the_wrap()
    test_enter_in_the_field_steps_and_escape_closes()
    test_the_switches_change_what_is_found()
    test_a_question_that_matches_nothing_says_so()
    test_only_in_the_selection_needs_a_selection()
    test_replace_all_is_a_single_undo_step()
    test_the_highlight_lives_in_every_view_of_the_document()
    test_typing_in_the_editor_does_not_move_the_caret()
    test_the_bar_keeps_its_rows_and_never_grows_taller()
    print("all search checks passed")
    del application
    return 0


def test_a_caret_inside_a_word_finds_that_word() -> None:
    """`Ctrl+F` lands on the word the caret is *in*, not on the next one."""
    exact = search.Options(match_case=True)
    assert search.match_at(PROGRAM, "факт", 9, exact) == 9, "the first character"
    assert search.match_at(PROGRAM, "факт", 12, exact) == 9, "the last one is still inside"
    assert search.match_at(PROGRAM, "факт", 13, exact) is None, "one past it, nothing covers"
    assert search.match_at(PROGRAM, "факт", 8, exact) is None, "the character before it"
    assert search.match_at(PROGRAM, "нет-такого", 0) is None
    print("ok: the match covering the caret is the one it finds")


# -- the bar in a window (PySide6, offscreen, no interpreter) ----------------
#
# The window opens with a buffer and nothing running: searching is an editor
# feature, and needing a built `prologd.exe` for it would have made these checks
# part of the interpreter suite for no reason.


def search_window():
    """A window of its own, with the find bar and a throw-away settings file."""
    return make_window("prologd", ready=False)


def typed(window, text: str) -> None:
    """Fills the one buffer the way an opened file would, and marks it saved."""
    window.editor().setPlainText(text)
    window.buffers()[0].mark_saved()


def caret_to(view, offset: int) -> None:
    from PySide6.QtGui import QTextCursor

    cursor = QTextCursor(view.document())
    cursor.setPosition(offset)
    view.setTextCursor(cursor)


def select_range(view, start: int, end: int) -> None:
    from PySide6.QtGui import QTextCursor

    cursor = QTextCursor(view.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    view.setTextCursor(cursor)


def press_key(widget, key, modifiers=None) -> None:
    """Delivers a real key event to one widget.

    `QTest.keyClick` drives the *window* — shortcut resolution included — and that
    proved unreliable deep in a suite.  What is being checked here is the bar's own
    handling of `Enter`, `Shift+Enter` and `Esc`, so the event goes straight to the
    widget and its `keyPressEvent` runs for real.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    state = Qt.KeyboardModifier.NoModifier if modifiers is None else modifiers
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, key, state))


def caption_button(bar, title: str):
    """The bar's button with this caption, found the way the user sees it."""
    from PySide6.QtWidgets import QPushButton

    for button in bar.findChildren(QPushButton):
        if button.text() == title:
            return button
    raise AssertionError(f"there is no {title!r} button on the bar")


def test_the_five_search_commands_are_live() -> None:
    """No entry of the «Поиск» menu says «ещё не реализовано» any more."""
    keys = ("find", "find_next", "find_prev", "find_selected", "find_selected_prev")
    for key in keys:
        entry = actions.BY_KEY[key]
        assert entry.implemented is True, key
        assert "не реализовано" not in entry.tooltip(), key
    window = search_window()
    try:
        for key in keys:
            assert window._actions[key].isEnabled() is True, key
    finally:
        discard_changes(window)
    print("ok: the five search commands are live in the menu and on the keys")


def test_the_two_magnifiers_are_on_the_right_controls() -> None:
    """«Поиск и замена…» carries the lens; the `R` belongs to «Замена».

    Both pictures are the same drawing with a letter in the glass — `search-find`
    (`F`) and `edit-find-replace` (`R`).  The command *opens the search*, so it
    shows the lens; the `R` sits on the triangle that opens the replacement half
    of the bar.  Each is named in `actions` (`FIND_ICON`, `REPLACE_ICON`), which
    is what keeps `test_icons.py` holding the files to a name — and this check is
    what stops a later tidy-up from swapping the two back, where the bar would
    show the same lens twice.
    """
    from prologd_gui import assets

    assert actions.BY_KEY["find"].icon == actions.FIND_ICON
    assert actions.FIND_ICON != actions.REPLACE_ICON

    window = search_window()
    try:
        lens = assets.icon(actions.FIND_ICON)
        replace = assets.icon(actions.REPLACE_ICON)
        assert lens is not None and replace is not None, "both pictures are drawn"
        assert lens.cacheKey() != replace.cacheKey(), "the two files are one and the same"
        assert window._actions["find"].icon().cacheKey() == lens.cacheKey(), (
            "«Поиск и замена…» is showing the wrong magnifier"
        )
        triangle = window.find_bar()._disclosure
        assert triangle.icon().cacheKey() == replace.cacheKey(), (
            "the «Замена» triangle is showing the wrong magnifier"
        )
    finally:
        discard_changes(window)
    print("ok: the lens is on «Поиск и замена…» and the R on the «Замена» triangle")


def test_the_bar_opens_on_the_word_under_the_caret() -> None:
    window = search_window()
    try:
        assert window.find_open() is False, "the bar stood there before Ctrl+F"
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        assert window.find_open() is True, "Ctrl+F did not open the bar"
        view = window.editor()
        bar = window.find_bar()
        assert bar.needle() == "факт", bar.needle()
        # The caret was at 0, inside the first «факт»: that match is the one found,
        # it is selected in the editor, and the bar says which of how many it is.
        assert bar.status_text() == "1 из 3", bar.status_text()
        cursor = view.textCursor()
        assert cursor.selectedText() == "факт"
        assert cursor.selectionStart() == 0
        assert [start for start, _length in view.search_ranges()] == [0, 9, 18]

        # And from inside the *second* one it lands on that one.
        caret_to(view, 12)
        window._actions["find"].trigger()
        assert bar.status_text() == "2 из 3", bar.status_text()
        assert view.textCursor().selectionStart() == 9
    finally:
        discard_changes(window)
    print("ok: Ctrl+F opens the bar on the word under the caret, every match lit")


def test_f3_walks_the_matches_and_reports_the_wrap() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        view = window.editor()
        assert bar.status_text() == "1 из 3"

        window._actions["find_next"].trigger()
        assert bar.status_text() == "2 из 3", bar.status_text()
        window._actions["find_next"].trigger()
        assert bar.status_text() == "3 из 3", bar.status_text()
        window._actions["find_next"].trigger()
        assert bar.status_text() == "1 из 3 — поиск с начала", bar.status_text()
        assert view.textCursor().selectionStart() == 0

        window._actions["find_prev"].trigger()
        assert bar.status_text() == "3 из 3 — поиск с конца", bar.status_text()
        assert view.textCursor().selectionStart() == 18
        window._actions["find_prev"].trigger()
        assert bar.status_text() == "2 из 3", bar.status_text()
    finally:
        discard_changes(window)
    print("ok: F3 walks the matches in both directions and the wrap is reported")


def test_enter_in_the_field_steps_and_escape_closes() -> None:
    from PySide6.QtCore import Qt

    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        view = window.editor()
        assert bar.status_text() == "1 из 3"

        press_key(bar.find_field(), Qt.Key.Key_Return)
        assert bar.status_text() == "2 из 3", "Enter in the field is not F3"
        press_key(bar.find_field(), Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        assert bar.status_text() == "1 из 3", "Shift+Enter in the field is not Shift+F3"

        # F3 works with the bar closed as well — the question stays in the field.
        # The step starts at the caret again, because the bar no longer holds the
        # match it was on.
        window.close_find()
        assert window.find_open() is False
        caret_to(view, 0)
        window._actions["find_next"].trigger()
        assert window.find_open() is False, "F3 reopened the bar"
        assert view.textCursor().selectionStart() == 0
        window._actions["find_next"].trigger()
        assert view.textCursor().selectionStart() == 9, "F3 with the bar closed did not move"

        window._actions["find"].trigger()
        press_key(bar.find_field(), Qt.Key.Key_Escape)
        assert window.find_open() is False, "Esc left the bar on screen"
        assert view.search_ranges() == [], "the highlight outlived the bar"
        assert window.focusWidget() is view, "the focus did not come back to the editor"
    finally:
        discard_changes(window)
    print("ok: Enter and Shift+Enter step, Esc closes and hands the focus back")


def test_the_switches_change_what_is_found() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        assert bar.status_text() == "1 из 3"

        # Upper case first: `факт` and `ФАКТ` are different predicates, and this
        # program has no upper-case one at all.
        bar.find_field().setText("ФАКТ")
        assert bar.status_text() == "1 из 3", "the default is case-insensitive"
        bar.set_match_case(True)
        assert bar.status_text() == "не найдено", bar.status_text()
        bar.set_match_case(False)
        assert bar.status_text() == "1 из 3", bar.status_text()

        # «фактик» contains «факт» but is not the whole word.
        bar.set_whole_word(True)
        assert bar.status_text() == "1 из 2", bar.status_text()
        bar.set_whole_word(False)
        bar.find_field().setText("факт")
        assert bar.status_text() == "1 из 3", bar.status_text()
    finally:
        discard_changes(window)
    print("ok: the case and whole-word switches change what is found")


def test_a_question_that_matches_nothing_says_so() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        bar.find_field().setText("нет-такого")
        assert bar.status_text() == "не найдено", bar.status_text()
        assert window.editor().search_ranges() == [], "an empty search painted something"
        window._actions["find_next"].trigger()
        assert bar.status_text() == "не найдено", "stepping changed the answer"
    finally:
        discard_changes(window)
    print("ok: a question that matches nothing says so and paints nothing")


def test_only_in_the_selection_needs_a_selection() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        view = window.editor()
        # `Ctrl+F` selected a match, so the switch has a span to work with — and,
        # because the span is taken once, the search keeps it while it steps.
        bar.set_only_in_selection(True)
        assert bar.only_in_selection() is True
        assert bar.status_text() == "1 из 1", bar.status_text()
        bar.set_only_in_selection(False)
        assert bar.status_text() == "1 из 3", bar.status_text()

        # A wider span: the second and the third line, two of the three matches.
        select_range(view, 9, 27)
        bar.set_only_in_selection(True)
        assert bar.status_text() in ("1 из 2", "2 из 2"), bar.status_text()

        # With nothing selected the switch refuses instead of quietly meaning
        # «everywhere» — that would make the message in the bar a lie.
        bar.set_only_in_selection(False)
        caret_to(view, 5)
        bar.set_only_in_selection(True)
        assert bar.only_in_selection() is False, "it stayed on with nothing selected"
        assert bar.status_text() == "сначала выделите фрагмент", bar.status_text()
    finally:
        discard_changes(window)
    print("ok: 'only in the selection' keeps its span, and refuses without one")


def test_replace_all_is_a_single_undo_step() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        bar.show_replace(True)
        assert bar.replace_visible() is True
        bar.replace_field().setText("правило")
        caption_button(bar, "Заменить всё").click()
        assert bar.status_text() == "заменено 3", bar.status_text()
        assert window.editor().toPlainText() == "правило(1).\nправило(2).\nправилоик(3).\n"

        window._actions["undo"].trigger()
        assert window.editor().toPlainText() == BAR_PROGRAM, "one Ctrl+Z undid only part"
        assert window._actions["undo"].isEnabled() is False, "it was more than one step"

        # «Заменить» replaces the match the caret is on, then looks for the next
        # one: one `Заменить` per press, and the count shrinks as it goes.
        window._actions["find"].trigger()
        assert bar.status_text() == "2 из 3", bar.status_text()
        caption_button(bar, "Заменить").click()
        assert window.editor().toPlainText() == "факт(1).\nправило(2).\nфактик(3).\n"
        assert bar.status_text() == "2 из 2", "the search did not move on"
    finally:
        discard_changes(window)
    print("ok: 'replace all' is one undo step, 'replace' moves on to the next match")


def test_the_highlight_lives_in_every_view_of_the_document() -> None:
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window.split_editor(remember=False)
        assert window.pane_count() == 2
        window._actions["find"].trigger()
        buffer = window.active_pane().current_buffer()
        assert buffer is not None
        # One text, two views: «Найти» acts on the pane that was used last, and both
        # views show the matches because they show the same document.
        assert len(buffer.views()) == 2, len(buffer.views())
        for view in buffer.views():
            assert [start for start, _length in view.search_ranges()] == [0, 9, 18]
        window.close_find()
        for view in buffer.views():
            assert view.search_ranges() == [], "a highlight stayed behind in one view"
    finally:
        discard_changes(window)
    print("ok: the matches are lit in every view of the document, and cleared on Esc")


def test_typing_in_the_editor_does_not_move_the_caret() -> None:
    """The bar keeps the count honest without stealing the caret.

    The first version recomputed the search on every text change and moved the
    caret to the match it picked, so typing in the program threw the cursor into
    the next «факт» — the one thing an editor must never do.
    """
    window = search_window()
    try:
        typed(window, BAR_PROGRAM)
        window._actions["find"].trigger()
        bar = window.find_bar()
        view = window.editor()
        assert bar.status_text() == "1 из 3"

        end = len(BAR_PROGRAM)
        caret_to(view, end)
        view.insertPlainText("новое(1).\n")
        assert view.textCursor().position() == end + len("новое(1).\n")
        assert bar.status_text() == "1 из 3", "an edit moved the search"
        assert view.textCursor().hasSelection() is False, "the edit selected a match"
    finally:
        discard_changes(window)
    print("ok: editing with the bar open leaves the caret where the user put it")


def test_the_bar_keeps_its_rows_and_never_grows_taller() -> None:
    """Two defects the user's eye caught in the first minutes of using the bar.

    The three switches sat on the field's row, where they were the first thing
    squeezed out by a narrow window — a switch that cannot be read is a switch the
    user cannot use — and the bar had the default size policy, so the layout shared
    the window's spare height with the editor: the strip was as tall as the program
    pane and took half the window for three short lines.
    """
    from PySide6.QtWidgets import QSizePolicy

    window = search_window()
    try:
        bar = window.find_bar()
        window._actions["find"].trigger()
        assert bar.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum, (
            "the bar can grow into the editor's room again"
        )

        # Which row a widget is on is which row it is a child of.
        assert bar.find_field().parent() is bar.field_row()
        for box in bar.switch_boxes():
            assert box.parent() is bar.switch_row(), "a switch is not on the switch row"
        assert bar.switch_row() is not bar.field_row()

        # …and the rows are stacked: the switches under the field, the replacement
        # under the switches (and only then).
        bar.adjustSize()
        assert bar.switch_row().y() >= bar.field_row().geometry().bottom()
        assert bar.replace_row().isHidden() is True, "the replace row showed by itself"
        bar.show_replace(True)
        bar.adjustSize()
        assert bar.replace_row().y() >= bar.switch_row().geometry().bottom()
        assert bar.height() <= bar.sizeHint().height(), (
            "the bar is taller than its rows ask for",
            bar.height(),
            bar.sizeHint().height(),
        )
    finally:
        discard_changes(window)
    print("ok: the switches have a row of their own and the strip stays as tall as they need")


if __name__ == "__main__":
    raise SystemExit(main())
