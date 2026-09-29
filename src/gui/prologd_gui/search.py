"""Plain-text search: where the matches are, and what a replacement does.

The programs are written in Russian and are full of `#…#`, `?` and parentheses, so
the search is by *text* and not by pattern: a regular expression would surprise more
often than it helps, and `Ctrl+F` must not need escaping in an editor of all things.

Qt-free on purpose.  What goes wrong in a search is arithmetic: where the next match
starts, whether it wraps, whether the same offset is found twice, and whether
«Заменить всё» manages to find its own output again.  `test_search.py` hammers exactly
that.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Characters that count as "inside a word" for the whole-word switch.  Letters and
#: digits of any alphabet, plus the underscore — `факт_1` is one word.
_WORD_EXTRA = "_"


def is_word_character(character: str) -> bool:
    return bool(character) and (character.isalnum() or character in _WORD_EXTRA)


@dataclass(frozen=True)
class Options:
    """What the switches on the search bar mean."""

    #: Compare `Факт` and `факт` as the same text.
    match_case: bool = False
    #: The match must not touch a word character on either side.
    whole_word: bool = False
    #: Search only inside `[start, end)`; `None` means the whole text.
    span: tuple[int, int] | None = None


def _limits(text: str, options: Options) -> tuple[int, int]:
    if options.span is None:
        return 0, len(text)
    start, end = options.span
    return max(0, start), min(len(text), end)


def _is_whole_word(text: str, start: int, length: int) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[start + length] if start + length < len(text) else ""
    return not is_word_character(before) and not is_word_character(after)


def matches(text: str, needle: str, options: Options | None = None) -> list[int]:
    """Every start offset where `needle` occurs, left to right.

    Offsets are into `text` itself, even when the case is ignored: the folding is
    done on a *slice* of the original (`str.casefold()`, so Cyrillic and `ß` fold
    too), never on a whole folded copy of the text.  A fold that changes a string's
    length could not shift the offsets of the matches after it that way.
    """
    settings = options or Options()
    if not needle:
        return []
    start, end = _limits(text, settings)
    wanted = needle if settings.match_case else needle.casefold()
    length = len(needle)
    found: list[int] = []
    position = start
    while position <= end - length:
        chunk = text[position : position + length]
        hit = chunk == wanted if settings.match_case else chunk.casefold() == wanted
        if hit and (not settings.whole_word or _is_whole_word(text, position, length)):
            found.append(position)
            position += length  # matches never overlap
        else:
            position += 1
    return found


def count(text: str, needle: str, options: Options | None = None) -> int:
    return len(matches(text, needle, options))


def match_at(
    text: str, needle: str, position: int, options: Options | None = None
) -> int | None:
    """The match that *covers* `position`, if there is one.

    `Ctrl+F` with the caret in the middle of `факт` must land on that `факт`, not on
    the one after it: a word the caret is inside is the word being looked for.
    Stepping with `F3` is unaffected, because a step continues *after* the match it
    just found.
    """
    for offset in matches(text, needle, options):
        if offset <= position < offset + len(needle):
            return offset
    return None


def next_match(
    text: str, needle: str, position: int, options: Options | None = None
) -> int | None:
    """The first match at or after `position`, wrapping round the end.

    Wrapping is what `F3` does at the end of a file, and the bar reports it rather
    than letting the user think the search is over.
    """
    found = matches(text, needle, options)
    if not found:
        return None
    for offset in found:
        if offset >= position:
            return offset
    return found[0]


def previous_match(
    text: str, needle: str, position: int, options: Options | None = None
) -> int | None:
    """The last match at or before `position`, wrapping round the beginning."""
    found = matches(text, needle, options)
    if not found:
        return None
    for offset in reversed(found):
        if offset <= position:
            return offset
    return found[-1]


def replace_all(
    text: str, needle: str, replacement: str, options: Options | None = None
) -> tuple[str, int]:
    """`text` with every match replaced, and how many were replaced.

    Replacements are never scanned again: the cursor continues after what was just
    written, so replacing `а` with `аа` cannot run away.
    """
    settings = options or Options()
    found = matches(text, needle, settings)
    if not found:
        return text, 0
    pieces: list[str] = []
    written = 0
    for offset in found:
        pieces.append(text[written:offset])
        pieces.append(replacement)
        written = offset + len(needle)
    pieces.append(text[written:])
    return "".join(pieces), len(found)
