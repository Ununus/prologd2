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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QTextDocument  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui.highlighter import PrologHighlighter  # noqa: E402
from prologd_gui.keywords import Keywords  # noqa: E402
from prologd_gui.theme import Theme  # noqa: E402
from prologd_gui.tokens import (  # noqa: E402
    ATOM,
    CYRILLIC,
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
    ) -> None:
        self.line = line
        self.document = QTextDocument()
        self.highlighter = PrologHighlighter(self.document, keywords, theme)
        self.document.setPlainText(line)
        self.highlighter.rehighlight()

    def ranges(self) -> list[tuple[int, int, str, int, str, str]]:
        from PySide6.QtGui import QTextCharFormat

        block = self.document.firstBlock()
        layout = block.layout()
        assert layout is not None, "the document was never laid out"
        return [
            (
                item.start,
                item.length,
                item.format.foreground().color().name(),
                int(item.format.fontWeight()),
                # `noBrush` (an empty string) when the token has no band behind it.
                item.format.background().color().name()
                if item.format.background().style() != Qt.BrushStyle.NoBrush
                else "",
                # The wavy line's colour, `""` when the text is not underlined.
                item.format.underlineColor().name()
                if item.format.underlineStyle() != QTextCharFormat.UnderlineStyle.NoUnderline
                else "",
            )
            for item in layout.formats()
        ]

    def at(self, snippet: str) -> tuple[str | None, int | None]:
        """The colour and weight of the *first* occurrence of `snippet`."""
        assert snippet in self.line, f"{snippet!r} is not in {self.line!r}"
        offset = self.line.index(snippet)
        for start, length, colour, weight, _band, _underline in self.ranges():
            if start <= offset < start + length:
                return colour, weight
        return None, None

    def background(self, snippet: str) -> str:
        """The band behind the first occurrence of `snippet`, `""` for none."""
        assert snippet in self.line, f"{snippet!r} is not in {self.line!r}"
        offset = self.line.index(snippet)
        for start, length, _colour, _weight, band, _underline in self.ranges():
            if start <= offset < start + length:
                return band
        return ""

    def underline(self, snippet: str) -> str:
        """The wavy line under the first occurrence of `snippet`, `""` for none."""
        assert snippet in self.line, f"{snippet!r} is not in {self.line!r}"
        offset = self.line.index(snippet)
        for start, length, _colour, _weight, _band, underline in self.ranges():
            if start <= offset < start + length:
                return underline
        return ""

    def colour(self, snippet: str) -> str | None:
        return self.at(snippet)[0]


def test_colours_by_kind() -> None:
    coloured = Coloured("член(X) :- member(X), X = 1, НАЙТИВСЕ(Y, цель(Y), L), ПС. % привет")

    # Names: atom and variable have a colour each, and the alphabet does not
    # matter — one role, one colour (part 226).
    assert coloured.colour("член") == THEME.atom
    assert coloured.colour("member") == THEME.atom
    assert coloured.colour("цель") == THEME.atom
    assert coloured.colour("X") == THEME.variable
    assert coloured.colour("L") == THEME.variable

    # Reserved names, comments and punctuation.
    assert coloured.colour("НАЙТИВСЕ") == THEME.keyword
    assert coloured.colour("ПС") == THEME.keyword
    assert coloured.colour("% привет") == THEME.comment
    assert coloured.colour(":-") == THEME.punctuation
    # The comparison signs are reserved too (task_52): `=` is coloured like a
    # built-in name, while `:-` stays punctuation.
    assert coloured.colour("=") == THEME.keyword
    print("ok: every kind gets its colour, and names are told from variables")


def test_a_directive_is_bold_like_any_reserved_name() -> None:
    """task_111: `ИМПОРТ` keeps its weight when the kinds arrive.

    Two tables reach the window: `--list-keywords` has no kinds, so the name is a
    plain keyword, and the `ready` event says `directive`.  The colour was the same
    either way, but the bold mark was not — it disappeared after the first run.
    """
    line = ':- ИМПОРТ("файл.pld").'
    with_kinds = Coloured(line, keywords=TABLE)
    without = Coloured(line, keywords=Keywords([{"name": "ИМПОРТ", "arities": []}]))
    bold = int(QFont.Weight.Bold)
    assert with_kinds.at("ИМПОРТ") == (THEME.keyword, bold), with_kinds.at("ИМПОРТ")
    assert without.at("ИМПОРТ")[1] == bold, without.at("ИМПОРТ")
    print("ok: a directive is bold whether its kind is known or not")


def test_colours_on_a_query_line() -> None:
    coloured = Coloured('?цель("строка", 12, 1.5, #Н-1#)')

    assert coloured.colour("?") == THEME.query
    assert coloured.colour("цель") == THEME.atom
    assert coloured.colour('"строка"') == THEME.string
    assert coloured.colour("12") == THEME.number
    assert coloured.colour("1.5") == THEME.number
    assert coloured.colour("#") == THEME.expression
    print("ok: `?`, strings, numbers and `#` on a query line")


def test_the_comment_is_not_tokenized_further() -> None:
    """A `%` swallows the line: nothing inside it may be coloured as code."""
    coloured = Coloured("цель(X). % НАЙТИВСЕ(X) и \"строка\"")
    assert coloured.colour("% НАЙТИВСЕ(X) и \"строка\"") == THEME.comment
    # The code before the comment still is.
    assert coloured.colour("цель") == THEME.atom
    assert coloured.colour("X") == THEME.variable
    print("ok: a trailing comment keeps its own colour to the end of the line")


def test_a_parked_question_is_coloured_as_the_comment_it_stands_in() -> None:
    """`%   ?ВЕРСИЯ.` is prose with a question in it, and reads as one colour.

    It used to have a colour of its own (part 226 removed that row): a comment is
    a comment, and the margin's marker is what tells a parked question apart.
    """
    assert Coloured("%   ?ВЕРСИЯ.").colour("%") == THEME.comment
    assert Coloured("% привет").colour("%") == THEME.comment
    assert Coloured("факт(1). % ?факт(X).").colour("%") == THEME.comment
    print("ok: a question parked in a comment is coloured as the comment")


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
    assert coloured.colour("НАЙТИВСЕ") == THEME.variable

    # The session then says `ready` and the same text is a built-in again.
    coloured.highlighter.set_keywords(TABLE)
    assert coloured.colour("НАЙТИВСЕ") == THEME.keyword
    print("ok: the keyword table arrives with `ready` and re-colours the text")


def test_changing_the_theme_recolours() -> None:
    coloured = Coloured("член(X)")
    assert coloured.colour("член") == THEME.atom
    coloured.highlighter.set_theme(Theme(atom="#123456", variable="#654321"))
    assert coloured.colour("член") == "#123456"
    assert coloured.colour("X") == "#654321"
    print("ok: the theme is data and re-applies without touching the text")


def test_a_mixed_alphabet_name_carries_a_band_while_the_box_is_ticked() -> None:
    """`abc_где` mixes the two alphabets, which is usually a typo (parts 226, 227).

    The mark is a *band*, as `#highlight[…]` paints one: the name keeps the colour
    of its role — an atom stays an atom, a variable stays a variable — and the
    band is what catches the eye.  It is a switch, not a colour: turning it off
    leaves a plain name, because to the interpreter the name is not wrong.
    """
    coloured = Coloured("член(abc_где, X_где, Y).")
    assert coloured.colour("abc_где") == THEME.atom
    assert coloured.colour("X_где") == THEME.variable
    assert coloured.background("abc_где") == THEME.mixed_background
    assert coloured.background("X_где") == THEME.mixed_background
    # The band alone is not enough: the current line is painted over the text's
    # background (part 228), so the wavy line is what stays visible there.
    assert coloured.underline("abc_где") == THEME.mixed_underline
    assert coloured.underline("X_где") == THEME.mixed_underline

    coloured.highlighter.set_flag_mixed(False)
    assert coloured.colour("abc_где") == THEME.atom
    assert coloured.background("abc_где") == "", "the band survived the switch"
    assert coloured.underline("abc_где") == "", "the wavy line survived the switch"

    # A name of one alphabet carries neither mark, whatever the switch says.
    coloured.highlighter.set_flag_mixed(True)
    for plain in ("член", "Y"):
        assert coloured.background(plain) == "", plain
        assert coloured.underline(plain) == "", plain
    print("ok: a name of two alphabets carries a band and a wavy line")


def test_astral_characters_do_not_shift_the_rest_of_the_line() -> None:
    """Qt counts UTF-16 units, Python counts code points; the offsets are mapped."""
    coloured = Coloured('член(😀). % привет')
    assert coloured.colour("привет") == THEME.comment
    assert coloured.colour("член") == THEME.atom
    print("ok: an astral character in a comment does not shift the colours")


def test_quoted_atoms_and_underscore_names() -> None:
    """A quoted constant is coloured as an atom — one role, one colour (part 226).

    An apostrophe opens a quoted atom and never ends a name: `_Пер'` is the
    variable `_Пер` and then a quote, which is what the old naming mode used to
    read as one token.
    """
    coloured = Coloured("пункт('атом', _Пер, _пер)")
    assert coloured.colour("'атом'") == THEME.atom
    assert coloured.colour("_Пер") == THEME.color_for(VARIABLE, CYRILLIC)
    assert coloured.colour("_пер") == THEME.color_for(VARIABLE, CYRILLIC)
    print("ok: атомы в кавычках и имена с подчёркиванием красятся")


def coloured_lines(text: str) -> list[list[tuple[str, str | None]]]:
    """Every line of a multi-line document, each as (text, colour) spans."""
    document = QTextDocument()
    highlighter = PrologHighlighter(document, TABLE, THEME)
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
        ("p", THEME.atom),
        ("(", THEME.punctuation),
        ("X", THEME.variable),
        (").", THEME.punctuation),
        ("/* начало", THEME.comment),
    ]
    # The middle line is nothing but comment — the line that used to be coloured
    # as code, its built-in name included.
    assert middle == [("середина НАЙТИВСЕ", THEME.comment)]
    # The comment ends where `*/` closes it, and code follows on the same line.
    assert last == [
        ("конец */", THEME.comment),
        ("q", THEME.atom),
        ("(", THEME.punctuation),
        ("X", THEME.variable),
        (").", THEME.punctuation),
        ("% хвост", THEME.comment),
    ]
    print("ok: a block comment is coloured on all of its lines")


def main() -> int:
    application = QApplication(sys.argv[:1])
    test_colours_by_kind()
    test_a_directive_is_bold_like_any_reserved_name()
    test_colours_on_a_query_line()
    test_the_comment_is_not_tokenized_further()
    test_a_parked_question_is_coloured_as_the_comment_it_stands_in()
    test_builtins_are_bold_and_names_are_not()
    test_changing_the_table_recolours()
    test_changing_the_theme_recolours()
    test_quoted_atoms_and_underscore_names()
    test_a_mixed_alphabet_name_carries_a_band_while_the_box_is_ticked()
    test_astral_characters_do_not_shift_the_rest_of_the_line()
    test_a_block_comment_is_coloured_on_every_line()
    print("all highlighter checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
