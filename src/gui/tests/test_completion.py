"""Checks of completion: the Qt-free model, then the popup offscreen.

    python src/gui/tests/test_completion.py

The model half runs without PySide6.  The popup half is deliberately driven by
real key events (`QTest`, `QApplication.sendEvent`) rather than by calling the
methods: the defects worth catching live in the wiring — a popup that opens
inside a comment, an `Enter` that inserts its own newline as well, arrows that
stop moving the caret.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import completion  # noqa: E402
from prologd_gui.keywords import Keywords  # noqa: E402

DOCUMENT = """\
% член(Элемент, Список) — истина, если Элемент входит в Список
член(X, [X|_]).
член(X, [_|Хвост]) :- член(X, Хвост).
дождь.
мокро :- дождь.
пример :- член(2, [1, 2, 3]), ВЫВОД = 'Иван Петров'.
"""

RESERVED = Keywords.from_event(
    {
        "keywords": [
            {"name": "НАЙТИВСЁ", "kind": "predicate", "arities": [3]},
            {"name": "ВЫВОД", "kind": "predicate", "arities": [], "variadic": True},
            {"name": "mod", "kind": "operator", "arities": []},
        ]
    }
)


def labels(prefix: str, text: str = DOCUMENT, keywords=RESERVED, **kwargs) -> list[str]:
    model = completion.CompletionModel(keywords, **kwargs)
    model.update(text)
    return model.labels(prefix)


# -- the Qt-free model ------------------------------------------------------
def test_the_document_is_scanned_for_names() -> None:
    calls, atoms, quoted = completion.collect_names(DOCUMENT, RESERVED)
    assert calls["член"] == {2}, calls
    assert {"дождь", "мокро", "пример"} <= atoms, atoms
    assert quoted == {"'Иван Петров'"}, quoted
    # A reserved name is not a document name, wherever it appears.
    assert "ВЫВОД" not in atoms and "ВЫВОД" not in calls
    print(f"ok: the document gave {len(calls)} called names, {len(atoms)} atoms")


def test_lists_do_not_inflate_the_arity() -> None:
    """`член(2, [1, 2, 3])` is arity 2, not 4 — commas inside `[]` are data."""
    assert labels("член") == ["член/2"], labels("член")
    print("ok: commas inside a list are not argument separators")


def test_reserved_names_come_with_their_arity() -> None:
    assert labels("НАЙ") == ["НАЙТИВСЁ/3"]
    assert labels("ВЫ") == ["ВЫВОД/+"]
    assert labels("mo") == ["mod"], "an operator is offered as the bare name"
    assert labels("чле") == ["член/2"]
    assert labels("дожд") == ["дождь"]
    print("ok: reserved and document names, with the right labels")


def test_only_the_name_is_inserted() -> None:
    offers = {offer.name: offer for offer in completion.collect(DOCUMENT, RESERVED)}
    assert offers["НАЙТИВСЁ"].label == "НАЙТИВСЁ/3"
    assert offers["НАЙТИВСЁ"].insert_text == "НАЙТИВСЁ", "the arity must not be typed for the user"
    print("ok: the arity is shown but never inserted")


def test_matching_is_case_sensitive_by_default() -> None:
    """`Мод` is a different word from `мод`: matching it needs the option.

    An upper-case first letter makes a *variable* in this language, so a quoted
    atom is the only way to write the other case at all.
    """
    text = "мод(1).\n'Мод'.\n"
    assert labels("мо", text) == ["мод/1"]
    assert labels("мо", text, case_sensitive=False) == ["мод/1", "'Мод'"], labels(
        "мо", text, case_sensitive=False
    )
    print("ok: matching honours the case by default, and a predicate sorts before an atom")


def test_the_same_alphabet_sorts_first() -> None:
    """A name mixing the two alphabets is offered after a pure one.

    Both start with `x`, so the case rule cannot separate them; the alphabet of
    the *name* is what does.
    """
    assert labels("x", "x_член(1).\nx_latin(1).\n") == ["x_latin/1", "x_член/1"], labels(
        "x", "x_член(1).\nx_latin(1).\n"
    )
    print("ok: a mixed-alphabet name sorts after a single-alphabet one")


def test_completion_is_suppressed_inside_comments_and_strings() -> None:
    line = "факт(1). % комментарий здесь"
    assert completion.is_code_position(line, 3)
    assert not completion.is_code_position(line, len(line)), "at the end of a comment"

    string = 'ВЫВОД = "строка тут".'
    assert completion.is_code_position(string, 0)
    assert not completion.is_code_position(string, string.index("строка"))
    assert completion.is_code_position(string, len(string)), "after the closing quote"

    atom = "пример :- 'Иван Петров'."
    assert not completion.is_code_position(atom, atom.index("Иван"))

    expression = "х :- #1 + 2#."
    inside = expression.index("+")
    assert not completion.is_code_position(expression, inside), "inside #…#"
    assert completion.is_code_position(expression, len(expression)), "after the second #"
    print("ok: no completion inside a comment, a string, a quoted atom or #…#")


def test_the_word_being_typed_is_read_from_the_caret() -> None:
    assert completion.word_before("пример :- чле", 13) == "чле"

    call = "пример :- член(2"
    assert completion.word_before(call, call.index("(")) == "член", "stop at the parenthesis"
    # Purely lexical: inside the call it is the argument being typed.  A digit
    # prefix matches nothing, so the popup simply stays closed.
    assert completion.word_before(call, len(call)) == "2"

    quoted = "ВЫВОД = 'Ив"
    assert completion.word_before(quoted, len(quoted)) == "'Ив", "a quoted atom keeps its quote"

    second_line = "факт(1).\nчле"
    assert completion.word_before(second_line, len(second_line)) == "чле"
    print("ok: the typed word is taken from the caret, quotes included")


def test_the_candidate_list_is_cached_until_the_text_changes() -> None:
    calls: list[str] = []
    original = completion.collect

    def counting(text, keywords=None):
        calls.append(text)
        return original(text, keywords)

    completion.collect = counting  # type: ignore[assignment]
    try:
        model = completion.CompletionModel(RESERVED)
        model.update(DOCUMENT)
        model.update(DOCUMENT)
        assert len(calls) == 1, "the same text was scanned twice"
        model.labels("чле")  # asking for a prefix must not rescan either
        assert len(calls) == 1
        model.update(DOCUMENT + "новое(1).\n")
        assert len(calls) == 2
        model.set_keywords(RESERVED)
        model.update(DOCUMENT)
        assert len(calls) == 3, "new keywords invalidate the list"
    finally:
        completion.collect = original  # type: ignore[assignment]
    print("ok: the list is rebuilt only when the text or the keywords change")


# -- the popup --------------------------------------------------------------
def type_text(editor, text: str) -> None:
    """Types through `keyPressEvent`, the way a keyboard does."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    for character in text:
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_unknown, Qt.KeyboardModifier.NoModifier, character
        )
        QApplication.sendEvent(editor, event)


def test_the_popup_opens_and_accepts() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor
    from PySide6.QtTest import QTest

    from prologd_gui.editor import CodeEditor

    editor = CodeEditor(auto_complete_after=2)
    editor.set_completion_keywords(RESERVED)
    editor.setPlainText("abc(1).\n")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    type_text(editor, "a")
    assert not editor.completion_visible(), "one letter is not enough by default"
    type_text(editor, "b")
    assert editor.completion_visible(), "the popup did not open after two letters"
    offers = editor.completion_labels()
    # `ab` is offered too: the line being typed is part of the document, and the
    # model does not pretend to know better than the file.
    assert offers[0] == "abc/1", offers
    assert "ab" in offers, offers

    QTest.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "abc(1).\nabc", editor.toPlainText()
    assert not editor.completion_visible(), "Enter must close the popup, not open a line"
    print("ok: two letters open the popup and Enter takes the name without a newline")


def test_escape_closes_and_arrows_keep_working() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor
    from PySide6.QtTest import QTest

    from prologd_gui.editor import CodeEditor

    editor = CodeEditor(auto_complete_after=1)
    editor.set_completion_keywords(RESERVED)
    editor.setPlainText("НА")
    editor.moveCursor(QTextCursor.MoveOperation.End)
    type_text(editor, "Й")
    assert editor.completion_visible(), "one letter should be enough here"

    QTest.keyClick(editor, Qt.Key.Key_Escape)
    assert not editor.completion_visible()
    assert editor.toPlainText() == "НАЙ", "Escape must not change the text"

    # Typing again would only lengthen the word; ask for the popup instead.
    QTest.keyClick(editor, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
    assert editor.completion_visible(), "the popup can be asked for again"
    before = editor.textCursor().position()
    QTest.keyClick(editor, Qt.Key.Key_Left)
    assert not editor.completion_visible(), "the arrow closes the popup"
    assert editor.textCursor().position() == before - 1, "and moves the caret anyway"
    print("ok: Escape closes without changing anything, arrows keep moving the caret")


def test_ctrl_space_opens_on_demand() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor
    from PySide6.QtTest import QTest

    from prologd_gui.editor import CodeEditor

    editor = CodeEditor(auto_complete_after=4)
    editor.set_completion_keywords(RESERVED)
    editor.setPlainText("НА")
    editor.moveCursor(QTextCursor.MoveOperation.End)
    QTest.keyClick(editor, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
    assert editor.completion_visible(), "Ctrl+Space must complete a short prefix"
    assert editor.completion_labels() == ["НАЙТИВСЁ/3"]
    print("ok: Ctrl+Space opens the popup before the automatic threshold")


def test_no_popup_inside_a_comment_or_a_string() -> None:
    from PySide6.QtGui import QTextCursor

    from prologd_gui.editor import CodeEditor

    editor = CodeEditor(auto_complete_after=1)
    editor.set_completion_keywords(RESERVED)
    editor.setPlainText("% комментарий")
    editor.moveCursor(QTextCursor.MoveOperation.End)
    type_text(editor, "НА")
    assert not editor.completion_visible(), "a comment is not code"

    editor.setPlainText('ВЫВОД = "стр')
    editor.moveCursor(QTextCursor.MoveOperation.End)
    type_text(editor, "НА")
    assert not editor.completion_visible(), "a string is not code"
    print("ok: typing inside a comment or a string offers nothing")


def main() -> int:
    test_the_document_is_scanned_for_names()
    test_lists_do_not_inflate_the_arity()
    test_reserved_names_come_with_their_arity()
    test_only_the_name_is_inserted()
    test_matching_is_case_sensitive_by_default()
    test_the_same_alphabet_sorts_first()
    test_completion_is_suppressed_inside_comments_and_strings()
    test_the_word_being_typed_is_read_from_the_caret()
    test_the_candidate_list_is_cached_until_the_text_changes()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed")
        return 0
    application = QApplication(sys.argv[:1])
    test_the_popup_opens_and_accepts()
    test_escape_closes_and_arrows_keep_working()
    test_ctrl_space_opens_on_demand()
    test_no_popup_inside_a_comment_or_a_string()
    del application
    print("all completion checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
