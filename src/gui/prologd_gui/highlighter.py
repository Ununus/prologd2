"""Syntax highlighting for the editor: the tokenizer plus a palette.

`tokens.py` decides *what* each piece of a line is; this module only maps that to
a `QTextCharFormat`.  Keeping the split means the rules are testable without Qt
(the interesting part) and the Qt half stays trivial.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from .keywords import Keywords
from .theme import Theme
from .tokens import scan_line


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

    #: The block state that means «this line begins inside a `/* … */`
    #: comment» (task_132).  Qt hands a block its predecessor's state, so a
    #: comment of several lines is coloured whole, not line by line.
    _BLOCK_COMMENT = 1

    def __init__(
        self,
        document,
        keywords: Keywords | None = None,
        theme: Theme | None = None,
        flag_mixed: bool = True,
    ) -> None:
        super().__init__(document)
        self._keywords = keywords or Keywords()
        self._theme = theme or Theme()
        #: «Выделять имя из двух алфавитов» (part 226): the checkbox on the
        #: «Подсветка» page.  It is a switch, not a colour, so it lives beside the
        #: palette rather than in it.
        self._flag_mixed = flag_mixed
        self._formats: dict[tuple[str, str, str, bool], QTextCharFormat] = {}

    # -- configuration ------------------------------------------------------
    def set_keywords(self, keywords: Keywords) -> None:
        """Replaces the reserved names; called when `ready` arrives."""
        self._keywords = keywords
        self.rehighlight()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._formats.clear()
        self.rehighlight()

    def set_flag_mixed(self, flag: bool) -> None:
        """Turns the red flag on mixed-alphabet names on or off (part 226)."""
        if bool(flag) == self._flag_mixed:
            return
        self._flag_mixed = bool(flag)
        self._formats.clear()
        self.rehighlight()

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def flag_mixed(self) -> bool:
        return self._flag_mixed

    @property
    def keywords(self) -> Keywords:
        """The reserved names in force — a new view needs them for its popup too."""
        return self._keywords

    # -- QSyntaxHighlighter -------------------------------------------------
    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt spelling
        offsets = _utf16_offsets(text) if _has_astral(text) else None
        tokens, still_open = scan_line(
            text,
            self._keywords,
            block_comment=self.previousBlockState() == self._BLOCK_COMMENT,
        )
        self.setCurrentBlockState(self._BLOCK_COMMENT if still_open else 0)
        for token in tokens:
            char_format = self._format_for(token.kind, token.alphabet)
            if char_format is None:
                continue
            start = offsets[token.start] if offsets is not None else token.start
            end = offsets[token.end] if offsets is not None else token.end
            self.setFormat(start, end - start, char_format)

    def _format_for(self, kind: str, alphabet: str) -> QTextCharFormat | None:
        color = self._theme.color_for(kind, alphabet)
        background = self._theme.background_for(kind, alphabet, flag_mixed=self._flag_mixed)
        underline = self._theme.underline_for(kind, alphabet, flag_mixed=self._flag_mixed)
        if not color:
            return None
        key = (color, background, underline, self._theme.is_bold(kind))
        char_format = self._formats.get(key)
        if char_format is None:
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color))
            if background:
                # A band, not a colour of the text: `#highlight[…]` in a word
                # processor.  The name keeps the colour of its role, so it is
                # still an atom or a variable — the band is what catches the eye.
                char_format.setBackground(QColor(background))
            if underline:
                # The current line is painted over the text's background, so the
                # band is hidden on the line the caret stands on; a wavy line is
                # drawn with the text and stays visible there (part 228).
                char_format.setUnderlineColor(QColor(underline))
                char_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            if key[3]:
                char_format.setFontWeight(QFont.Weight.Bold)
            self._formats[key] = char_format
        return char_format
