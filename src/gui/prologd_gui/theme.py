"""Colours for the editor, as lowercase `#rrggbb` strings so the module stays
Qt-free.

The palette is data, not code: the highlighter only asks `color_for(kind,
alphabet)`, and task_29 puts these fields behind the settings dialog.  Keeping
them out of `highlighter.py` means a colour can be tested and changed without
importing Qt.  Values are lowercase because that is what `QColor.name()`
returns, so a test can compare a palette entry with what the document holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tokens

#: Kinds that must not be italicised or bolded away from the rest.
_BOLD_KINDS = frozenset({tokens.KEYWORD})


@dataclass(frozen=True)
class Theme:
    """The colours of the editor.

    Names get their colour from the **alphabet** as well as the kind, which is
    the point the user asked for: `член` and `member` are otherwise easy to
    confuse while scanning a program, and a built-in is Russian far more often
    than not.
    """

    comment: str = "#0f7f0f"
    string: str = "#a31515"
    quoted_atom: str = "#b03060"
    keyword: str = "#00008b"  # reserved names: built-ins, `mod`/`div`, `ИМПОРТ`
    integer: str = "#505000"
    float: str = "#505000"
    punctuation: str = "#555555"
    query: str = "#0a22d6"
    expression: str = "#0a22d6"
    atom_latin: str = "#800000"
    atom_cyrillic: str = "#7b1fa2"
    variable_latin: str = "#00695c"
    variable_cyrillic: str = "#ad1457"
    mixed: str = "#4a148c"  # an identifier that mixes the two alphabets

    def color_for(self, kind: str, alphabet: str = "") -> str:
        """The colour of a token; an empty string means "leave it alone"."""
        if kind == tokens.COMMENT:
            return self.comment
        if kind == tokens.STRING:
            return self.string
        if kind == tokens.QUOTED_ATOM:
            return self.quoted_atom
        if kind in (tokens.KEYWORD, tokens.DIRECTIVE, tokens.OPERATOR):
            return self.keyword
        if kind == tokens.INTEGER:
            return self.integer
        if kind == tokens.FLOAT:
            return self.float
        if kind == tokens.PUNCTUATION:
            return self.punctuation
        if kind == tokens.QUERY:
            return self.query
        if kind == tokens.EXPRESSION:
            return self.expression
        if kind == tokens.ATOM:
            return self._name_colour(self.atom_latin, self.atom_cyrillic, alphabet)
        if kind == tokens.VARIABLE:
            return self._name_colour(self.variable_latin, self.variable_cyrillic, alphabet)
        return ""

    def is_bold(self, kind: str) -> bool:
        return kind in _BOLD_KINDS

    def _name_colour(self, latin: str, cyrillic: str, alphabet: str) -> str:
        if alphabet == tokens.CYRILLIC:
            return cyrillic
        if alphabet == tokens.MIXED:
            return self.mixed
        # Latin by default: a name without letters at all (say `_`) is not worth
        # a third colour.
        return latin
