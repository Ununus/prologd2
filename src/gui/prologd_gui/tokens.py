"""Lexical rules of PrologD for highlighting, mirroring `src/prlib/src/lexer.cpp`.

Qt-free on purpose: the rules are worth testing without a display, and the
highlighter (`highlighter.py`) is then only a mapping from token kind to format.

The interpreter owns the language, so this module is *not* authoritative — it is
a second implementation of the same rules, kept small and table-driven.  It never
influences execution: the worst a bug here can do is colour something wrong.

Differences from the lexer, both deliberate:

* diagnostics are ignored — a malformed literal is highlighted as the text it
  looks like rather than reported;
* there is no carried state between lines.  Neither a string nor `#…#` may span
  lines in PrologD (the lexer rejects an unterminated one), so a line-local pass
  is enough and typing stays cheap: an unterminated string is simply coloured to
  the end of its own line;
* whitespace is not a token.  There is nothing to colour in it, and the sweep
  test asserts the stronger property anyway: every other character of a line is
  inside exactly one token.
"""

from __future__ import annotations

from dataclasses import dataclass

from .keywords import DIRECTIVE, OPERATOR, PREDICATE, Keywords

# -- token kinds ------------------------------------------------------------
COMMENT = "comment"
STRING = "string"
QUOTED_ATOM = "quoted_atom"
KEYWORD = "keyword"  # a reserved name that is a predicate
DIRECTIVE = "directive"  # ИМПОРТ
OPERATOR = "operator"  # mod, div
VARIABLE = "variable"
ATOM = "atom"
INTEGER = "integer"
FLOAT = "float"
PUNCTUATION = "punctuation"
QUERY = "query"  # `?`
QUERY_COMMENT = "query_comment"  # a question parked in a comment: `% ?…`
EXPRESSION = "expression"  # the `#` of `#… #`

# -- alphabets --------------------------------------------------------------
LATIN = "latin"
CYRILLIC = "cyrillic"
MIXED = "mixed"

_KIND_OF_KEYWORD = {
    PREDICATE: KEYWORD,
    OPERATOR: OPERATOR,
    DIRECTIVE: DIRECTIVE,
}

_CYRILLIC_FIRST = 0x0400
_CYRILLIC_LAST = 0x04FF
_LATIN_EXTENDED_FIRST = 0x00C0
_LATIN_EXTENDED_LAST = 0x024F


@dataclass(frozen=True)
class Token:
    """One highlighted span of a single line.

    `start` and `end` are code-point offsets into that line (Python string
    indices), so a highlighter can hand them to `setFormat` unchanged.
    """

    kind: str
    text: str
    start: int
    end: int
    alphabet: str = ""


def is_ascii_digit(ch: str) -> bool:
    return "0" <= ch <= "9"


def is_ascii_letter(ch: str) -> bool:
    return ("A" <= ch <= "Z") or ("a" <= ch <= "z")


def is_upper_letter(ch: str) -> bool:
    return ("A" <= ch <= "Z") or ("А" <= ch <= "Я") or ch == "Ё"


def is_lower_letter(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("а" <= ch <= "я") or ch == "ё"


def is_letter(ch: str) -> bool:
    if is_ascii_letter(ch) or is_upper_letter(ch) or is_lower_letter(ch):
        return True
    return _LATIN_EXTENDED_FIRST <= ord(ch) <= _LATIN_EXTENDED_LAST


def is_name_character(ch: str) -> bool:
    return is_letter(ch) or is_ascii_digit(ch) or ch == "_"


def alphabet_of(text: str) -> str:
    """Which alphabet the letters of `text` are written in.

    This is what lets the editor colour `член` and `member` differently — the
    whole point of telling the two scripts apart while typing.
    """
    latin = False
    cyrillic = False
    for ch in text:
        code = ord(ch)
        if _CYRILLIC_FIRST <= code <= _CYRILLIC_LAST:
            cyrillic = True
        elif is_ascii_letter(ch) or _LATIN_EXTENDED_FIRST <= code <= _LATIN_EXTENDED_LAST:
            latin = True
    if latin and cyrillic:
        return MIXED
    if latin:
        return LATIN
    if cyrillic:
        return CYRILLIC
    return ""


def tokenize(line: str, keywords: Keywords | None = None) -> list[Token]:
    """Splits one line into highlightable tokens, in source order.

    Without `keywords` no reserved name is recognised, which is what an
    interpreter older than protocol 2 leaves us with: everything is then an atom
    or a variable, and the GUI cannot tell a built-in from a user name.
    """
    tokens: list[Token] = []
    index = 0
    length = len(line)
    while index < length:
        ch = line[index]

        if ch.isspace():
            index += 1
            continue
        if ch == "%":
            # A question parked in a comment (`%   ?ВЕРСИЯ.`) is a question all the
            # same — the margin marks it and runs it (task_36) — so it is coloured
            # as one.  Only a comment that *starts* the line can be one: the rule
            # the margin uses is `%`, blanks and `?` where the line begins.
            rest = line[index:]
            if not line[:index].strip() and rest[1:].lstrip(" \t").startswith("?"):
                tokens.append(Token(QUERY_COMMENT, rest, index, length))
            else:
                tokens.append(Token(COMMENT, rest, index, length))
            break
        if ch == '"':
            end = _scan_delimited(line, index, '"', doubled=False, backslash=True)
            tokens.append(Token(STRING, line[index:end], index, end))
            index = end
            continue
        if ch == "'":
            end = _scan_delimited(line, index, "'", doubled=True, backslash=False)
            tokens.append(Token(QUOTED_ATOM, line[index:end], index, end))
            index = end
            continue
        if ch in ("#", "?"):
            kind = EXPRESSION if ch == "#" else QUERY
            tokens.append(Token(kind, ch, index, index + 1))
            index += 1
            continue
        if is_ascii_digit(ch):
            end = _scan_number(line, index)
            text = line[index:end]
            kind = FLOAT if any(mark in text for mark in ".eE") else INTEGER
            tokens.append(Token(kind, text, index, end))
            index = end
            continue
        if is_name_character(ch):
            end = index
            while end < length and is_name_character(line[end]):
                end += 1
            text = line[index:end]
            tokens.append(_identifier(text, index, end, keywords))
            index = end
            continue

        pair = line[index : index + 2]
        if pair in (":-", "<-", "\\+"):
            tokens.append(Token(PUNCTUATION, pair, index, index + 2))
            index += 2
            continue
        tokens.append(Token(PUNCTUATION, ch, index, index + 1))
        index += 1
    return tokens


def _identifier(text: str, start: int, end: int, keywords: Keywords | None) -> Token:
    # A reserved name wins over the variable rule: `ВЫП` starts with an
    # upper-case letter but is an atom, and the lexer decides that the same way.
    if keywords is not None:
        keyword = keywords.get(text)
        if keyword is not None:
            kind = _KIND_OF_KEYWORD.get(keyword.kind, KEYWORD)
            return Token(kind, text, start, end, alphabet_of(text))
    kind = VARIABLE if text.startswith("_") or is_upper_letter(text[0]) else ATOM
    return Token(kind, text, start, end, alphabet_of(text))


def _scan_delimited(
    line: str, start: int, quote: str, *, doubled: bool, backslash: bool
) -> int:
    """End offset of a `"…"` string or a `'…'` atom, never crossing the line."""
    index = start + 1
    length = len(line)
    while index < length:
        ch = line[index]
        if ch == quote:
            if doubled and index + 1 < length and line[index + 1] == quote:
                index += 2
                continue
            return index + 1
        if backslash and ch == "\\" and index + 1 < length and line[index + 1] in ('"', "\\"):
            index += 2
            continue
        if ch == "\n":
            break
        index += 1
    return length


def _scan_number(line: str, start: int) -> int:
    """End offset of a number, following `Lexer::lexNumber`.

    The interesting case is the dot: `12.3` and `12.` are floats, while the dot
    that ends a clause in `факт(1).` is not part of the number.
    """
    index = start
    length = len(line)
    has_dot = False
    has_exponent = False
    while index < length:
        ch = line[index]
        if is_ascii_digit(ch):
            index += 1
            continue
        if ch == "." and not has_dot and not has_exponent:
            following = line[index + 1] if index + 1 < length else ""
            if is_ascii_digit(following):
                has_dot = True
                index += 1
                continue
            if following not in ("", "."):
                has_dot = True
                index += 1
            break
        if ch in ("e", "E") and not has_exponent:
            sign = line[index + 1] if index + 1 < length else ""
            digit = line[index + 2] if sign in ("+", "-") and index + 2 < length else sign
            if is_ascii_digit(digit):
                has_exponent = True
                index += 1
                if sign in ("+", "-"):
                    index += 1
                continue
        break
    return index
