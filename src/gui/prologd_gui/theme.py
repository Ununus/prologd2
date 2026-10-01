"""Colours for the editor, as lowercase `#rrggbb` strings so the module stays
Qt-free.

The palette is data, not code: the highlighter only asks `color_for(kind,
alphabet)`, and task_29 puts these fields behind the settings dialog.  Keeping
them out of `highlighter.py` means a colour can be tested and changed without
importing Qt.  Values are lowercase because that is what `QColor.name()`
returns, so a test can compare a palette entry with what the document holds.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

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

    comment: str = "#0d6a0d"
    # A question parked in a comment (`%   ?ВЕРСИЯ.`): a question to the reader,
    # and the margin will run it — orange, so it does not read as prose.
    query_comment: str = "#b45309"
    string: str = "#a31515"
    quoted_atom: str = "#b03060"
    keyword: str = "#00008b"  # reserved names: built-ins, `mod`/`div`, `ИМПОРТ`
    integer: str = "#505000"
    float: str = "#505000"
    punctuation: str = "#555555"
    query: str = "#0a22d6"
    expression: str = "#0a22d6"
    atom_latin: str = "#800000"
    atom_cyrillic: str = "#6a1b9a"
    variable_latin: str = "#00695c"
    variable_cyrillic: str = "#ad1457"
    mixed: str = "#4a148c"  # an identifier that mixes the two alphabets

    def color_for(self, kind: str, alphabet: str = "") -> str:
        """The colour of a token; an empty string means "leave it alone"."""
        if kind == tokens.COMMENT:
            return self.comment
        if kind == tokens.QUERY_COMMENT:
            return self.query_comment
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

    def colors(self) -> list[str]:
        """Every colour of the palette, for checks and the settings dialog."""
        return [
            value
            for name, value in vars(self).items()
            if isinstance(value, str) and value.startswith("#")
        ]


#: The syntax palette of the light theme: the colours of task_22, chosen against
#: a white page.  It is the `Theme` default, so an old settings file — and every
#: caller that has no palette — gets exactly what it had before.
LIGHT_SYNTAX = Theme()

#: The dark syntax palette (task_29).  Same kinds, same alphabet split, chosen
#: against `#1e1e1e`; every field clears WCAG AA on that page, the tightest being
#: `mixed` at 5.07.
DARK_SYNTAX = Theme(
    comment="#6a9955",
    query_comment="#e8a33d",
    string="#ce9178",
    quoted_atom="#e882b0",
    keyword="#569cd6",
    integer="#b5cea8",
    float="#b5cea8",
    punctuation="#9d9d9d",
    query="#4fc1ff",
    expression="#4fc1ff",
    atom_latin="#d2a679",
    atom_cyrillic="#c586c0",
    variable_latin="#4ec9b0",
    variable_cyrillic="#f071a8",
    mixed="#d16d9e",
)


@dataclass(frozen=True)
class Palette:
    """Everything a window is painted with: the syntax colours and the chrome.

    A dark window is *not* a switch over the light one.  The syntax colours are
    only correct against **their own** page, and so are the bands, the margin and
    the colours of the output's kinds — a half-done dark theme is worse than none,
    which is why task_29's colour page is this record rather than a checkbox.

    `background` is the page the editor paints (`QPalette.Base`), so a test can
    compare the two and the contrast of every colour is measured against the
    surface it is really drawn on.
    """

    name: str
    #: The page, and the reference every colour of the palette is measured against.
    background: str
    foreground: str
    syntax: Theme
    #: The window chrome: `appearance.qt_palette` maps these onto `QPalette` roles.
    window: str
    alternate_base: str
    tooltip_background: str
    tooltip_text: str
    highlight: str
    highlighted_text: str
    link: str
    bright_text: str
    placeholder: str
    disabled_text: str
    #: The editor's own bands and margin (see `editor.py`).
    error_background: str
    error_text: str
    trace_background: str
    trace_text: str
    search_match: str
    search_current: str
    current_line: str
    occurrence: str
    margin_background: str
    margin_text: str
    margin_current: str
    query_marker: str
    #: The colours of the output pane's kinds (`panels.kind_colors`).
    echo: str
    note: str
    error: str
    warning: str
    trace: str

    def readable_pairs(self) -> list[tuple[str, str, str]]:
        """`(what, text, background)` of every pair that has to be readable.

        `test_appearance.py` walks this against WCAG AA (4.5), for every palette —
        so a colour added to a palette is measured without the test being touched,
        which is the only way a dark theme stays honest.  Two pairs are
        deliberately *not* in it: the margin's inactive numbers and the
        placeholder text are chrome, quiet on purpose (the margin is 3.03 in the
        light theme), and forcing them to 4.5 would make the numbers shout as
        loudly as the code.
        """
        pairs = [("текст на странице", self.foreground, self.background)]
        for field in fields(self.syntax):
            pairs.append(
                (f"подсветка: {field.name}", getattr(self.syntax, field.name), self.background)
            )
        for name in ("echo", "note", "error", "warning", "trace"):
            pairs.append((f"вывод: {name}", getattr(self, name), self.background))
        pairs.append(("номер строки с ошибкой", self.error_text, self.error_background))
        pairs.append(("номер строки шага", self.trace_text, self.trace_background))
        pairs.append(("номер текущей строки", self.margin_current, self.margin_background))
        pairs.append(("подсказка", self.tooltip_text, self.tooltip_background))
        pairs.append(("выделенный текст", self.highlighted_text, self.highlight))
        return pairs


#: The light palette: exactly the colours the window had before task_29's dark
#: theme, so choosing `light` changes nothing for a user who liked it.
LIGHT = Palette(
    name="light",
    background="#ffffff",
    foreground="#1a1a1a",
    syntax=LIGHT_SYNTAX,
    window="#f0f0f0",
    alternate_base="#f7f7f7",
    tooltip_background="#ffffe1",
    tooltip_text="#1a1a1a",
    highlight="#0a5fd6",
    highlighted_text="#ffffff",
    link="#0a22d6",
    bright_text="#d40000",
    placeholder="#8a8a8a",
    disabled_text="#a0a0a0",
    error_background="#ffd9d9",
    error_text="#c00000",
    trace_background="#d8e6f7",
    trace_text="#1b4f86",
    search_match="#ffe9a8",
    search_current="#ffc14d",
    current_line="#f4f6f9",
    occurrence="#e8ecf5",
    margin_background="#f0f0f0",
    margin_text="#8a8a8a",
    margin_current="#0a22d6",
    query_marker="#0a22d6",
    echo="#0a22d6",
    note="#555555",
    error="#a00000",
    warning="#b35c00",
    # `#777777` was the trace colour of task_28 and is 4.48 on white — a hair
    # under WCAG AA, which the palette check of task_29 then found.  A step
    # darker keeps the stream quiet and clears the threshold (4.61).
    trace="#757575",
)

#: The dark palette (task_29).  The frame is the one dark desktops use
#: (`#1e1e1e` page, `#252526` window), the bands are darkened versions of the
#: light ones, and every colour in `readable_pairs` clears WCAG AA.
DARK = Palette(
    name="dark",
    background="#1e1e1e",
    foreground="#d4d4d4",
    syntax=DARK_SYNTAX,
    window="#252526",
    alternate_base="#2a2a2c",
    tooltip_background="#2d2d30",
    tooltip_text="#e6e6e6",
    highlight="#264f78",
    highlighted_text="#ffffff",
    link="#4fc1ff",
    bright_text="#ff8080",
    placeholder="#8a8a8a",
    disabled_text="#7a7a7a",
    error_background="#46262a",
    error_text="#ff9a9a",
    trace_background="#1f3b57",
    trace_text="#9ecbff",
    search_match="#5c4a00",
    search_current="#8a6d1f",
    current_line="#26262b",
    occurrence="#2d3038",
    margin_background="#252526",
    margin_text="#a6a6a6",
    margin_current="#4fc1ff",
    query_marker="#4fc1ff",
    echo="#4fc1ff",
    note="#a6a6a6",
    error="#ff9a9a",
    warning="#e2a13c",
    trace="#a6a6a6",
)

#: The palettes by name, in the order the settings dialog lists them.
PALETTES = (LIGHT, DARK)
PALETTE_BY_NAME = {palette.name: palette for palette in PALETTES}


def palette_for(name: str) -> Palette:
    """A palette by name; an unknown name (a hand-edited file) is the light one."""
    return PALETTE_BY_NAME.get(name, LIGHT)


def relative_luminance(color: str) -> float:
    """WCAG relative luminance of a `#rrggbb` colour."""

    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (int(color[index : index + 2], 16) / 255 for index in (1, 3, 5))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast_ratio(first: str, second: str) -> float:
    """WCAG contrast ratio between two colours, 1.0 (same) to 21.0 (black/white).

    Used to keep a palette readable: 4.5 is the WCAG AA threshold for body text,
    and it is the check that would have caught the dark-theme complaint before a
    user did — the syntax colours are only correct *against a white background*.
    """
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)
