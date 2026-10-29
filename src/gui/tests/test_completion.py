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
from prologd_gui.reference import Reference  # noqa: E402

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
            {"name": "НАЙТИВСЕ", "kind": "predicate", "arities": [3]},
            {"name": "ВЫВОД", "kind": "predicate", "arities": [], "variadic": True},
            {"name": "ВЫВОДПС", "kind": "predicate", "arities": [], "variadic": True},
            {"name": "mod", "kind": "operator", "arities": []},
        ]
    }
)


#: A reference with one record, for the label under the popup (task_37).
REFERENCE = Reference(
    [
        {
            "name": "abc",
            "aliases": ["abc_en"],
            "kind": "predicate",
            "arities": [1],
            "group": "test",
            "section": "1.1",
            "summary": "тестовый предикат",
            "variants": ["abc(X) — тест"],
        }
    ]
)


def labels(prefix: str, text: str = DOCUMENT, keywords=RESERVED, **kwargs) -> list[str]:
    model = completion.CompletionModel(keywords, **kwargs)
    model.update(text)
    return model.labels(prefix)


# -- the Qt-free model ------------------------------------------------------
def test_the_document_is_scanned_for_names() -> None:
    calls, atoms, quoted, notes = completion.collect_names(DOCUMENT, RESERVED)
    assert calls["член"] == {2}, calls
    assert {"дождь", "мокро", "пример"} <= atoms, atoms
    assert quoted == {"'Иван Петров'"}, quoted
    # A reserved name is not a document name, wherever it appears.
    assert "ВЫВОД" not in atoms and "ВЫВОД" not in calls
    # `член` is documented by the comment above its first clause, and only then:
    # the first mention of the name is inside that comment, which is not a clause.
    assert notes["член"] == "член(Элемент, Список) — истина, если Элемент входит в Список", notes
    assert "дождь" not in notes, "a name without a comment above it gets none"
    print(f"ok: the document gave {len(calls)} called names, {len(atoms)} atoms")


def test_lists_do_not_inflate_the_arity() -> None:
    """`член(2, [1, 2, 3])` is arity 2, not 4 — commas inside `[]` are data."""
    assert labels("член") == ["член/2"], labels("член")
    print("ok: commas inside a list are not argument separators")


def test_reserved_names_come_with_their_arity() -> None:
    assert labels("НАЙ") == ["НАЙТИВСЕ/3"]
    # A shorter name that is a prefix of a longer one goes first, and the longer
    # one is still offered: `ВЫВОД` is not a prefix match that hides `ВЫВОДПС`
    # (task_53 added the second variadic name).
    assert labels("ВЫ") == ["ВЫВОД/+", "ВЫВОДПС/+"]
    assert labels("ВЫВОДП") == ["ВЫВОДПС/+"]
    assert labels("mo") == ["mod"], "an operator is offered as the bare name"
    assert labels("чле") == ["член/2"]
    assert labels("дожд") == ["дождь"]
    print("ok: reserved and document names, with the right labels")


def test_the_call_form_is_inserted_with_the_caret_after_the_paren() -> None:
    """Accepting inserts `имя(` with the caret after `(`; arity adds commas."""
    offers = {offer.name: offer for offer in completion.collect(DOCUMENT, RESERVED)}
    assert offers["НАЙТИВСЕ"].label == "НАЙТИВСЕ/3"
    assert offers["НАЙТИВСЕ"].call_form == ("НАЙТИВСЕ(, , )", 9), offers["НАЙТИВСЕ"].call_form
    assert offers["ВЫВОД"].call_form == ("ВЫВОД()", 6), offers["ВЫВОД"].call_form
    assert offers["ВЫВОДПС"].call_form == ("ВЫВОДПС()", 8), offers["ВЫВОДПС"].call_form
    print("ok: accepting inserts the call form, with the caret after the opening parenthesis")


def test_a_typed_bracket_is_not_inserted_twice() -> None:
    """`БОЛ(` accepts as `БОЛЬШЕ(`, not `БОЛЬШЕ(, )(` (part 238).

    The name ends at the bracket the user typed, so the span to replace stops there
    and the form brings the name only; the caret stops inside the call.  The popup
    also matches on that name — with an empty prefix it used to offer everything.
    """
    assert completion.prefix_span("пример :- БОЛ", 13) == (10, 13)
    assert completion.prefix_span("пример :- БОЛ(", 14) == (10, 13), "the bracket stays"
    assert completion.prefix_span("пример :- БОЛ(", 13) == (10, 13), "caret before it"
    bracket = "пример :- ("
    assert completion.prefix_span(bracket, len(bracket)) == (
        len(bracket), len(bracket)
    ), "nothing typed before it"
    assert completion.word_before("пример :- БОЛ(", 14) == "БОЛ"

    offers = {offer.name: offer for offer in completion.collect(DOCUMENT, RESERVED)}
    assert offers["НАЙТИВСЕ"].call_form_after("(") == ("НАЙТИВСЕ", 9)
    assert offers["НАЙТИВСЕ"].call_form_after("") == ("НАЙТИВСЕ(, , )", 9)
    assert offers["ВЫВОД"].call_form_after("(") == ("ВЫВОД", 6)
    # A directive is offered as the whole statement: nothing to shorten.
    reserved = Keywords.from_event(
        {"keywords": [{"name": "ИМПОРТ", "kind": "directive", "arities": []}]}
    )
    model = completion.CompletionModel(reserved)
    model.update("")
    directive = model.candidates("ИМП")[0]
    assert directive.call_form_after("(") == directive.call_form
    print("ok: a bracket the user typed is kept, and only the name goes in")


def test_a_typed_bracket_survives_the_real_editor() -> None:
    """The whole road in a real editor: two letters, the bracket, Enter (part 238)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor
    from PySide6.QtTest import QTest

    from prologd_gui.editor import CodeEditor

    editor = CodeEditor(auto_complete_after=2)
    editor.set_completion_keywords(Keywords.from_list_lines("БОЛЬШЕ/2"))
    editor.setPlainText("тест :- ")
    editor.moveCursor(QTextCursor.MoveOperation.End)
    type_text(editor, "БОЛ(")
    assert editor.completion_visible(), editor.completion_labels()
    assert editor.completion_labels() == ["БОЛЬШЕ/2"], editor.completion_labels()
    QTest.keyClick(editor, Qt.Key.Key_Return)
    assert editor.toPlainText() == "тест :- БОЛЬШЕ(", editor.toPlainText()
    assert editor.textCursor().position() == len("тест :- БОЛЬШЕ("), (
        editor.textCursor().position()
    )
    print("ok: the bracket survives in the real editor too")


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


def test_an_imported_file_adds_its_predicates() -> None:
    """What `ИМПОРТ` brings in is offered too, and says where it came from (task_102).

    Predicates only: a library's atoms are not what the next goal is typed with.
    A name the document itself has stays the document's, and a reserved name is
    still a reserved name.
    """
    imported = {
        "/tmp/библиотека.pld": (
            "% библиотека\n"
            "член_списка(X, [X|_]).\n"
            "цвет(красный).\n"
            "ВЫВОД(что-то).\n"
        )
    }
    offers = completion.collect(DOCUMENT, RESERVED, imported)
    by_name = {offer.name: offer for offer in offers}
    member = by_name["член_списка"]
    assert member.source == completion.IMPORTED, member
    assert member.origin == "библиотека.pld", member
    assert member.arity == 2, member
    # Atoms of the imported file are not offered, and neither is a reserved name.
    assert "красный" not in by_name, by_name.keys()
    assert by_name["ВЫВОД"].source == completion.BUILTIN
    # The document's own `член` is not replaced by anything from the import.
    assert by_name["член"].source == completion.USER
    # Ranked after the document's own name when both match: `член` first.
    model = completion.CompletionModel(RESERVED)
    model.set_imported(imported)
    model.update(DOCUMENT)
    assert model.labels("член") == ["член/2", "член_списка/2"], model.labels("член")
    print("ok: an imported file offers its predicates, with the file they came from")


def test_a_comment_above_the_first_clause_is_carried_with_the_name() -> None:
    """The popup says what the file says above the clause (task_103).

    A wrapped comment is joined into one paragraph, a blank line ends the block (a
    file's header is not a predicate's description), and a comment *after* the
    clause on its own line — or on the same line — is not read.
    """
    text = (
        "% Шапка файла, она к первому предикату не относится.\n"
        "\n"
        "% Принадлежность элемента списку: member(Элемент, Список),\n"
        "% где Список — правильный список.\n"
        "member(X, [X|_]).\n"
        "member(X, [_|Хвост]) :- member(X, Хвост).\n"
        "\n"
        "дождь.\n"
        "% это комментарий после дождя, к следующему предикату\n"
        "мокро :- дождь.\n"
    )
    _calls, _atoms, _quoted, notes = completion.collect_names(text, RESERVED)
    assert notes["member"] == (
        "Принадлежность элемента списку: member(Элемент, Список), "
        "где Список — правильный список."
    ), notes["member"]
    assert "дождь" not in notes, notes
    assert notes["мокро"] == "это комментарий после дождя, к следующему предикату", notes
    # And the candidate carries it — a predicate of no arguments is an atom in this
    # scan, and it still says what its file says above it.
    offers = {offer.name: offer for offer in completion.collect(text, RESERVED)}
    assert offers["member"].summary == notes["member"], offers["member"]
    assert offers["мокро"].summary == notes["мокро"], offers["мокро"]
    assert offers["дождь"].summary is None, offers["дождь"]
    print("ok: a comment above the first clause travels with the name")


def test_a_directive_is_offered_as_the_whole_statement() -> None:
    """`ИМ` gives `:- ИМПОРТ("").` with the caret inside the quotes (task_105).

    A directive is not a goal: the skeleton is the statement, and the string it
    opens is the one that completes to a file name (task_104).  `ХОЛСТ` follows the
    same rule (task_106) and meets its comma.
    """
    reserved = Keywords.from_event(
        {
            "keywords": [
                {"name": "ИМПОРТ", "kind": "directive", "arities": []},
                {"name": "import", "kind": "directive", "arities": []},
                {"name": "ХОЛСТ", "kind": "directive", "arities": []},
                {"name": "canvas", "kind": "directive", "arities": []},
            ]
        }
    )
    model = completion.CompletionModel(reserved)
    model.update("")
    offers = model.candidates("ИМП")
    assert [offer.label for offer in offers] == [':- ИМПОРТ("").'], offers
    assert offers[0].call_form == (':- ИМПОРТ("").', 11), offers[0].call_form
    assert offers[0].directive is True
    # The English spelling has a skeleton of its own.
    assert [offer.label for offer in model.candidates("im")] == [':- import("").'], (
        model.candidates("im")
    )
    # `ХОЛСТ` names the height and the width, so the caret meets the comma.
    canvas = model.candidates("ХО")
    assert [offer.call_form for offer in canvas] == [(":- ХОЛСТ(, ).", 9)], canvas
    assert [offer.label for offer in model.candidates("ca")] == [":- canvas(, )."], (
        model.candidates("ca")
    )
    # Where the statement can start — the rule the editor applies, which has to
    # look at what stands *before* the word being typed.
    line = "  ИМ"
    assert completion.at_statement_start(line, len(line), "ИМ") is True
    body = "цель :- ИМ"
    assert completion.at_statement_start(body, len(body), "ИМ") is False
    print("ok: a directive is offered as its whole statement, only at a line start")


def test_the_candidate_list_is_cached_until_the_text_changes() -> None:
    calls: list[str] = []
    original = completion.collect

    def counting(text, keywords=None, imported=None):
        calls.append(text)
        return original(text, keywords, imported)

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
        model.update(DOCUMENT + "новое(1).\n")
        assert len(calls) == 3, "new keywords invalidate the list"
        # The imported texts are the third half of the list (task_102): a new set
        # of them has to rebuild it too, and the same set must not.
        model.set_imported({"/tmp/библиотека.pld": "библиотечное(1).\n"})
        model.update(DOCUMENT + "новое(1).\n")
        assert len(calls) == 4, "new imported files invalidate the list"
        model.set_imported({"/tmp/библиотека.pld": "библиотечное(1).\n"})
        model.update(DOCUMENT + "новое(1).\n")
        assert len(calls) == 4, "the same imported files must not"
    finally:
        completion.collect = original  # type: ignore[assignment]
    print("ok: the list is rebuilt only when the text, the keywords or the imports change")


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
    assert editor.toPlainText() == "abc(1).\nabc()", editor.toPlainText()
    assert editor.textCursor().position() == 12, editor.textCursor().position()
    assert not editor.completion_visible(), "Enter must close the popup, not open a line"
    print("ok: two letters open the popup and Enter inserts the call form without a newline")


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
    assert editor.completion_labels() == ["НАЙТИВСЕ/3"]
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


def test_the_popup_shows_the_description_of_the_highlighted_row() -> None:
    """The label under the popup (task_37, multi-line since 2026-10-02).

    It is a window of its own (`Qt.ToolTip`), so it must appear with the popup,
    follow the highlight and leave with the popup — and a name that has no record
    must leave it hidden rather than show a frame about the previous row.  What
    it shows is the record's title (name, alias, summary) and its argument modes.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextCursor
    from PySide6.QtTest import QTest

    from prologd_gui.editor import CodeEditor

    described = "abc (abc_en) — тестовый предикат\n\nabc(X) — тест"

    editor = CodeEditor(auto_complete_after=1)
    editor.set_completion_keywords(RESERVED)
    editor.set_reference(REFERENCE)
    editor.setPlainText("abc(1).\nabc2(2).\n")
    editor.moveCursor(QTextCursor.MoveOperation.End)

    type_text(editor, "a")
    assert editor.completion_visible()
    # `a` itself is offered last: the line being typed is part of the document.
    assert editor.completion_labels() == ["abc/1", "abc2/1", "a"], editor.completion_labels()
    assert editor.completion_detail() == described, editor.completion_detail()

    # Down moves the highlight to a name the reference does not know: the label
    # goes away, it does not keep describing `abc`.
    QTest.keyClick(editor, Qt.Key.Key_Down)
    assert editor.completion_detail() == "", editor.completion_detail()
    QTest.keyClick(editor, Qt.Key.Key_Up)
    assert editor.completion_detail() == described, editor.completion_detail()

    QTest.keyClick(editor, Qt.Key.Key_Escape)
    assert not editor.completion_visible()
    assert editor.completion_detail() == ""

    # No reference at all (a checkout without `doc/`): the popup works, and no
    # label appears — the description half simply does not exist.
    plain = CodeEditor(auto_complete_after=1)
    plain.set_completion_keywords(RESERVED)
    plain.setPlainText("abc(1).\n")
    plain.moveCursor(QTextCursor.MoveOperation.End)
    type_text(plain, "a")
    assert plain.completion_visible(), "completion works without a reference"
    assert plain.completion_detail() == ""
    print("ok: the popup's description follows the highlight and leaves with it")


def main() -> int:
    test_the_document_is_scanned_for_names()
    test_lists_do_not_inflate_the_arity()
    test_reserved_names_come_with_their_arity()
    test_the_call_form_is_inserted_with_the_caret_after_the_paren()
    test_a_typed_bracket_is_not_inserted_twice()
    test_matching_is_case_sensitive_by_default()
    test_the_same_alphabet_sorts_first()
    test_completion_is_suppressed_inside_comments_and_strings()
    test_the_word_being_typed_is_read_from_the_caret()
    test_an_imported_file_adds_its_predicates()
    test_a_comment_above_the_first_clause_is_carried_with_the_name()
    test_a_directive_is_offered_as_the_whole_statement()
    test_the_candidate_list_is_cached_until_the_text_changes()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed")
        return 0
    application = QApplication(sys.argv[:1])
    test_the_popup_opens_and_accepts()
    test_a_typed_bracket_survives_the_real_editor()
    test_escape_closes_and_arrows_keep_working()
    test_ctrl_space_opens_on_demand()
    test_no_popup_inside_a_comment_or_a_string()
    test_the_popup_shows_the_description_of_the_highlighted_row()
    del application
    print("all completion checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
