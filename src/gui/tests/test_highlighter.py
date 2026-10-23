"""Checks that the palette reaches the document (needs PySide6, no display).

    python src/gui/tests/test_highlighter.py

`tokens.py` is tested on its own; what is checked here is the other half: that a
token's kind *and* alphabet select the intended colour, that the format is bold
where it should be, and that changing the table or the theme re-colours an open
document — the mechanism the settings dialog (task_29) and the session handshake
(`ready` carries the reserved names) both rely on.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QFont, QTextDocument  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui.highlighter import PrologHighlighter  # noqa: E402
from prologd_gui.keywords import Keywords  # noqa: E402
from prologd_gui.theme import Theme  # noqa: E402
from prologd_gui.tokens import (  # noqa: E402
    ATOM,
    CYRILLIC,
    MODE_ISO,
    MODE_OLD,
    STRING,
    VARIABLE,
)

TABLE = Keywords(
    [
        {"name": "НАЙТИВСЕ", "kind": "predicate", "arities": [3]},
        {"name": "ИМПОРТ", "kind": "directive", "arities": []},
        {"name": "mod", "kind": "operator", "arities": []},
        {"name": "ПС", "kind": "predicate", "arities": [0]},
    ]
)

THEME = Theme()


class Coloured:
    """A document with the highlighter attached, and a way to ask about colours."""

    def __init__(
        self,
        line: str,
        keywords: Keywords = TABLE,
        theme: Theme = THEME,
        mode: int = MODE_ISO,
    ) -> None:
        self.line = line
        self.document = QTextDocument()
        self.highlighter = PrologHighlighter(self.document, keywords, theme, mode)
        self.document.setPlainText(line)
        self.highlighter.rehighlight()

    def ranges(self) -> list[tuple[int, int, str, int]]:
        block = self.document.firstBlock()
        layout = block.layout()
        assert layout is not None, "the document was never laid out"
        return [
            (
                item.start,
                item.length,
                item.format.foreground().color().name(),
                int(item.format.fontWeight()),
            )
            for item in layout.formats()
        ]

    def at(self, snippet: str) -> tuple[str | None, int | None]:
        """The colour and weight of the *first* occurrence of `snippet`."""
        assert snippet in self.line, f"{snippet!r} is not in {self.line!r}"
        offset = self.line.index(snippet)
        for start, length, colour, weight in self.ranges():
            if start <= offset < start + length:
                return colour, weight
        return None, None

    def colour(self, snippet: str) -> str | None:
        return self.at(snippet)[0]


def test_colours_by_kind() -> None:
    coloured = Coloured("член(X) :- member(X), X = 1, НАЙТИВСЕ(Y, цель(Y), L), ПС. % привет")

    # Names: atoms and variables have a colour each, shared by both alphabets —
    # the Russian and English spellings look alike since task_50's colour round.
    assert coloured.colour("член") == THEME.atom_cyrillic
    assert coloured.colour("member") == THEME.atom_latin
    assert coloured.colour("цель") == THEME.atom_cyrillic
    assert coloured.colour("X") == THEME.variable_latin
    assert coloured.colour("L") == THEME.variable_latin

    # Reserved names, comments and punctuation.
    assert coloured.colour("НАЙТИВСЕ") == THEME.keyword
    assert coloured.colour("ПС") == THEME.keyword
    assert coloured.colour("% привет") == THEME.comment
    assert coloured.colour(":-") == THEME.punctuation
    # The comparison signs are reserved too (task_52): `=` is coloured like a
    # built-in name, while `:-` stays punctuation.
    assert coloured.colour("=") == THEME.keyword
    print("ok: every kind gets its colour, and names are told from variables")


def test_colours_on_a_query_line() -> None:
    coloured = Coloured('?цель("строка", 12, 1.5, #Н-1#)')

    assert coloured.colour("?") == THEME.query
    assert coloured.colour("цель") == THEME.atom_cyrillic
    assert coloured.colour('"строка"') == THEME.string
    assert coloured.colour("12") == THEME.integer
    assert coloured.colour("1.5") == THEME.float
    assert coloured.colour("#") == THEME.expression
    print("ok: `?`, strings, numbers and `#` on a query line")


def test_the_comment_is_not_tokenized_further() -> None:
    """A `%` swallows the line: nothing inside it may be coloured as code."""
    coloured = Coloured("цель(X). % НАЙТИВСЕ(X) и \"строка\"")
    assert coloured.colour("% НАЙТИВСЕ(X) и \"строка\"") == THEME.comment
    # The code before the comment still is.
    assert coloured.colour("цель") == THEME.atom_cyrillic
    assert coloured.colour("X") == THEME.variable_latin
    print("ok: a trailing comment keeps its own colour to the end of the line")


def test_a_parked_question_is_coloured_as_a_question() -> None:
    """`%   ?ВЕРСИЯ.` is a question the margin runs, not a note about one."""
    assert Coloured("%   ?ВЕРСИЯ.").colour("%") == THEME.query_comment
    # A comment that is not a question, and a question that does not start the
    # line, both keep the comment colour.
    assert Coloured("% привет").colour("%") == THEME.comment
    assert Coloured("факт(1). % ?факт(X).").colour("%") == THEME.comment
    print("ok: a question parked in a comment is coloured as a question")


def test_builtins_are_bold_and_names_are_not() -> None:
    coloured = Coloured("НАЙТИВСЕ(X)")
    keyword_colour, keyword_weight = coloured.at("НАЙТИВСЕ")
    assert keyword_colour == THEME.keyword
    assert keyword_weight == int(QFont.Weight.Bold)
    assert coloured.at("X")[1] != int(QFont.Weight.Bold)
    print("ok: built-ins are bold, names are not")


def test_changing_the_table_recolours() -> None:
    """An interpreter older than protocol 2 sends no names — and that is visible."""
    coloured = Coloured("НАЙТИВСЕ(X)", keywords=Keywords())
    assert coloured.colour("НАЙТИВСЕ") == THEME.variable_cyrillic

    # The session then says `ready` and the same text is a built-in again.
    coloured.highlighter.set_keywords(TABLE)
    assert coloured.colour("НАЙТИВСЕ") == THEME.keyword
    print("ok: the keyword table arrives with `ready` and re-colours the text")


def test_changing_the_theme_recolours() -> None:
    coloured = Coloured("член(X)")
    assert coloured.colour("член") == THEME.atom_cyrillic
    coloured.highlighter.set_theme(Theme(atom_cyrillic="#123456", variable_latin="#654321"))
    assert coloured.colour("член") == "#123456"
    assert coloured.colour("X") == "#654321"
    print("ok: the theme is data and re-applies without touching the text")


def test_the_naming_mode_changes_the_colours() -> None:
    """Mode 1 reads the old dialect's names (task_67): `д` is a variable there and
    `Молоко` a string constant, while mode 0 reads them the other way round."""
    coloured = Coloured("голова(д,Молоко)")
    assert coloured.colour("д") == THEME.color_for(ATOM, CYRILLIC)
    assert coloured.colour("Молоко") == THEME.color_for(VARIABLE, CYRILLIC)

    coloured.highlighter.set_mode(MODE_OLD)
    assert coloured.colour("д") == THEME.color_for(VARIABLE, CYRILLIC)
    assert coloured.colour("Молоко") == THEME.color_for(STRING, CYRILLIC)
    # A mode that does not move the colours must not cost a re-highlight either:
    # the value is what a document keeps, and setting it again changes nothing.
    coloured.highlighter.set_mode(MODE_OLD)
    assert coloured.highlighter.mode == MODE_OLD
    print("ok: the naming mode re-colours the old dialect's names")


def test_astral_characters_do_not_shift_the_rest_of_the_line() -> None:
    """Qt counts UTF-16 units, Python counts code points; the offsets are mapped."""
    coloured = Coloured('член(😀). % привет')
    assert coloured.colour("привет") == THEME.comment
    assert coloured.colour("член") == THEME.atom_cyrillic
    print("ok: an astral character in a comment does not shift the colours")


def test_quoted_atoms_and_underscore_names_in_both_modes() -> None:
    """task_100: the old dialect reads `'атом'` and `_имя` the way ISO does.

    A quoted constant is coloured as one in both modes, and a name starting with
    `_` is a variable in both.  The apostrophe is where the modes part: in the old
    dialect it is the suffix of a variable name and belongs to the token, while in
    ISO it opens a quoted atom and must stay a quote.
    """
    iso = Coloured("пункт('атом', _Пер, _пер)")
    assert iso.colour("'атом'") == THEME.quoted_atom
    assert iso.colour("_Пер") == THEME.color_for(VARIABLE, CYRILLIC)
    assert iso.colour("_пер") == THEME.color_for(VARIABLE, CYRILLIC)

    old = Coloured("пункт('атом', _Пер', _пер)", mode=MODE_OLD)
    assert old.colour("'атом'") == THEME.quoted_atom
    assert old.colour("_Пер") == THEME.color_for(VARIABLE, CYRILLIC)
    assert old.colour("_пер") == THEME.color_for(VARIABLE, CYRILLIC)
    # The apostrophe is part of the variable's token in the old dialect.
    spans = {old.line[start : start + length] for start, length, _c, _w in old.ranges()}
    assert "_Пер'" in spans, spans
    print("ok: атомы в кавычках и имена с подчёркиванием красятся в обеих модах")


def coloured_lines(text: str) -> list[list[tuple[str, str | None]]]:
    """Every line of a multi-line document, each as (text, colour) spans."""
    document = QTextDocument()
    highlighter = PrologHighlighter(document, TABLE, THEME, MODE_ISO)
    document.setPlainText(text)
    highlighter.rehighlight()
    lines = []
    block = document.firstBlock()
    while block.isValid():
        layout = block.layout()
        assert layout is not None, "the document was never laid out"
        line = block.text()
        lines.append([
            (line[item.start : item.start + item.length], item.format.foreground().color().name())
            for item in layout.formats()
        ])
        block = block.next()
    return lines


def test_a_block_comment_is_coloured_on_every_line() -> None:
    """A `/* … */` comment over several lines is one comment throughout (task_132).

    Qt colours one block at a time, so a line that *begins* inside a comment has
    to be told so by the block state; without it only the first line looked like
    a comment and the rest of it was coloured as code.
    """
    first, middle, last = coloured_lines(
        "p(X). /* начало\nсередина НАЙТИВСЕ\nконец */ q(X). % хвост"
    )
    # The opening line still has the code in front of the comment.  Qt merges
    # neighbouring spans of one format, so `)` and `.` arrive as one span.
    assert first == [
        ("p", THEME.atom_latin),
        ("(", THEME.punctuation),
        ("X", THEME.variable_latin),
        (").", THEME.punctuation),
        ("/* начало", THEME.comment),
    ]
    # The middle line is nothing but comment — the line that used to be coloured
    # as code, its built-in name included.
    assert middle == [("середина НАЙТИВСЕ", THEME.comment)]
    # The comment ends where `*/` closes it, and code follows on the same line.
    assert last == [
        ("конец */", THEME.comment),
        ("q", THEME.atom_latin),
        ("(", THEME.punctuation),
        ("X", THEME.variable_latin),
        (").", THEME.punctuation),
        ("% хвост", THEME.comment),
    ]
    print("ok: a block comment is coloured on all of its lines")


def main() -> int:
    application = QApplication(sys.argv[:1])
    test_colours_by_kind()
    test_colours_on_a_query_line()
    test_the_comment_is_not_tokenized_further()
    test_a_parked_question_is_coloured_as_a_question()
    test_builtins_are_bold_and_names_are_not()
    test_changing_the_table_recolours()
    test_changing_the_theme_recolours()
    test_the_naming_mode_changes_the_colours()
    test_quoted_atoms_and_underscore_names_in_both_modes()
    test_astral_characters_do_not_shift_the_rest_of_the_line()
    test_a_block_comment_is_coloured_on_every_line()
    print("all highlighter checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
