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

    def __init__(self, line: str, keywords: Keywords = TABLE, theme: Theme = THEME) -> None:
        self.line = line
        self.document = QTextDocument()
        self.highlighter = PrologHighlighter(self.document, keywords, theme)
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
    coloured = Coloured("член(X) :- member(X), НАЙТИВСЕ(Y, цель(Y), L), ПС. % привет")

    # Names: the colour tells the two alphabets apart, atoms and variables apart.
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
    print("ok: every kind gets its colour, and names follow their alphabet")


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


def test_astral_characters_do_not_shift_the_rest_of_the_line() -> None:
    """Qt counts UTF-16 units, Python counts code points; the offsets are mapped."""
    coloured = Coloured('член(😀). % привет')
    assert coloured.colour("привет") == THEME.comment
    assert coloured.colour("член") == THEME.atom_cyrillic
    print("ok: an astral character in a comment does not shift the colours")


def main() -> int:
    application = QApplication(sys.argv[:1])
    test_colours_by_kind()
    test_colours_on_a_query_line()
    test_the_comment_is_not_tokenized_further()
    test_a_parked_question_is_coloured_as_a_question()
    test_builtins_are_bold_and_names_are_not()
    test_changing_the_table_recolours()
    test_changing_the_theme_recolours()
    test_astral_characters_do_not_shift_the_rest_of_the_line()
    print("all highlighter checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
