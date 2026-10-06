"""Syntax highlighting for the editor: the tokenizer plus a palette.

`tokens.py` decides *what* each piece of a line is; this module only maps that to
a `QTextCharFormat`.  Keeping the split means the rules are testable without Qt
(the interesting part) and the Qt half stays trivial.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from .keywords import Keywords
from .theme import Theme
from .tokens import MODE_ISO, tokenize


def _has_astral(text: str) -> bool:
    return any(ord(character) > 0xFFFF for character in text)


def _utf16_offsets(text: str) -> list[int]:
    """Code-point index → UTF-16 offset, for lines with astral characters.

    `QTextDocument` counts UTF-16 code units while Python counts code points, so
    the two agree for every character PrologD accepts (all BMP: Latin, Cyrillic,
    digits, punctuation) and differ only from an astral character on — an emoji
    in a comment, say.  Rather than mis-colouring the rest of such a line, the
    offsets are mapped.
    """
    offsets = [0] * (len(text) + 1)
    offset = 0
    for index, character in enumerate(text):
        offsets[index] = offset
        offset += 2 if ord(character) > 0xFFFF else 1
    offsets[len(text)] = offset
    return offsets


class PrologHighlighter(QSyntaxHighlighter):
    """Colours a document line by line, using the interpreter's keyword table."""

    def __init__(
        self,
        document,
        keywords: Keywords | None = None,
        theme: Theme | None = None,
        mode: int = MODE_ISO,
    ) -> None:
        super().__init__(document)
        self._keywords = keywords or Keywords()
        self._theme = theme or Theme()
        self._mode = mode
        self._formats: dict[tuple[str, bool], QTextCharFormat] = {}

    # -- configuration ------------------------------------------------------
    def set_keywords(self, keywords: Keywords) -> None:
        """Replaces the reserved names; called when `ready` arrives."""
        self._keywords = keywords
        self.rehighlight()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._formats.clear()
        self.rehighlight()

    def set_mode(self, mode: int) -> None:
        """How this document's names are read (task_67).

        A colouring decision and nothing else: the interpreter reads the file's own
        `:- ИМЕНА(N).` line when it runs or formats it.  The window settles the
        value — the file's first line, or its own row for a file that says nothing —
        and a change means the colours have to be worked out again.
        """
        if mode == self._mode:
            return
        self._mode = mode
        self.rehighlight()

    @property
    def mode(self) -> int:
        """The mode in force, as the numbers of `tokens.MODES`."""
        return self._mode

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def keywords(self) -> Keywords:
        """The reserved names in force — a new view needs them for its popup too."""
        return self._keywords

    # -- QSyntaxHighlighter -------------------------------------------------
    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt spelling
        offsets = _utf16_offsets(text) if _has_astral(text) else None
        for token in tokenize(text, self._keywords, self._mode):
            char_format = self._format_for(token.kind, token.alphabet)
            if char_format is None:
                continue
            start = offsets[token.start] if offsets is not None else token.start
            end = offsets[token.end] if offsets is not None else token.end
            self.setFormat(start, end - start, char_format)

    def _format_for(self, kind: str, alphabet: str) -> QTextCharFormat | None:
        color = self._theme.color_for(kind, alphabet)
        if not color:
            return None
        key = (color, self._theme.is_bold(kind))
        char_format = self._formats.get(key)
        if char_format is None:
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color))
            if key[1]:
                char_format.setFontWeight(QFont.Weight.Bold)
            self._formats[key] = char_format
        return char_format
