"""Lexical rules of PrologD for highlighting, mirroring `src/prlib/src/lexer.cpp`.

Qt-free on purpose: the rules are worth testing without a display, and the
highlighter (`highlighter.py`) is then only a mapping from token kind to format.

The interpreter owns the language, so this module is *not* authoritative — it is
a second implementation of the same rules, kept small and table-driven.  It never
influences execution: the worst a bug here can do is colour something wrong.

Differences from the lexer, both deliberate:

* diagnostics are ignored — a malformed literal is highlighted as the text it
  looks like rather than reported;
* there is no carried state between lines for *strings* and `#…#`: neither may
  span lines in PrologD (the lexer rejects an unterminated one), so a line-local
  pass is enough and typing stays cheap: an unterminated string is simply coloured
  to the end of its own line.  One thing *does* span lines — the standard's
  `/* … */` comment (task_92) — so its state is carried explicitly: `scan_line`
  takes it in and gives it back, and the highlighter keeps it per text block;
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
OPERATOR = "operator"  # mod, div, and the comparison signs: =, <, >, >=, =<
VARIABLE = "variable"
ATOM = "atom"
INTEGER = "integer"
FLOAT = "float"
PUNCTUATION = "punctuation"
QUERY = "query"  # `?`
QUERY_COMMENT = "query_comment"  # a question parked in a comment: `% ?…`
EXPRESSION = "expression"  # the `#` of `#… #`

# -- naming modes (task_67, merged in task_77) -------------------------------
#: The two ways a name is read, with the numbers the marker `:- ИМЕНА(N).` and
#: `--vars` use.  Mode 0 is the port's own ISO reading; mode 1 is the old dialect,
#: where any single letter is a variable, a bare capitalised name is a string
#: constant, and a long name ends with an apostrophe (`Сумма'`).
#:
#: `2` was a mode of its own until task_77 and is a *spelling* of `1` now: the
#: original reads apostrophe names in a file that declares nothing, so the two
#: were one dialect all along.  `MODE_NUMBERS` is the only place a spelling is
#: turned into a mode, and a file that says `2` colours exactly as one that says
#: `1` — the mirror of `variableModeFromNumber` in `src/prlib/src/lexer.cpp`.
MODE_ISO = 0
MODE_OLD = 1
MODES = (MODE_ISO, MODE_OLD)
MODE_NUMBERS = {0: MODE_ISO, 1: MODE_OLD, 2: MODE_OLD}

#: What `:- ИМЕНА(N).` looks like when it is written down.
MARKER_NAME = "ИМЕНА"

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


#: The two Unicode separators Qt can put into a text, measured against the editor
#: and against `prologu` on 2026-10-03: `U+2028` is drawn as a new line but *not*
#: counted by `blockCount()`, so the line numbers and the question markers of the
#: margin end up on the wrong lines (the report that started this), and `U+2029` is
#: counted by the widget while the lexer rejects it outright.  A Prolog source has
#: exactly one line break, and it is `\n`.
LINE_SEPARATORS = ("\u2028", "\u2029")


def plain_newlines(text: str) -> str:
    """Folds the Unicode line separators back into a plain newline."""
    for separator in LINE_SEPARATORS:
        text = text.replace(separator, "\n")
    return text


def tokenize(line: str, keywords: Keywords | None = None, mode: int = MODE_ISO) -> list[Token]:
    """Splits one line into highlightable tokens, in source order.

    A line taken on its own: a block comment that does not close here ends with
    the line.  For a document, use `scan_line`, which also reports whether the
    line ends *inside* a comment.

    Without `keywords` no reserved name is recognised, which is what an
    interpreter older than protocol 2 leaves us with: everything is then an atom
    or a variable, and the GUI cannot tell a built-in from a user name.

    `mode` is how the file's names are read (task_67): 0 is the ISO reading, 1 the
    old dialect.  It is *one line's* rule and nothing more — the mode itself comes
    from the file's first line (see `mode_from_first_line`).
    """
    return scan_line(line, keywords, mode)[0]


def scan_line(
    line: str,
    keywords: Keywords | None = None,
    mode: int = MODE_ISO,
    block_comment: bool = False,
) -> tuple[list[Token], bool]:
    """Splits one line into tokens, and says whether it ends inside `/* … */`.

    `block_comment` is the state on the way in: True means the line begins inside
    a block comment, so everything up to `*/` (or to the end of the line) is one
    comment token.  The second half of the answer is the state on the way out, to
    be handed to the next line — that is how a comment of several lines is
    coloured by a highlighter that sees one line at a time (task_132).
    """
    tokens: list[Token] = []
    index = 0
    length = len(line)
    if block_comment:
        closer = line.find("*/")
        if closer < 0:
            # Still inside: the whole line is comment, and so is the next one.
            return ([Token(COMMENT, line, 0, length)] if line else []), True
        tokens.append(Token(COMMENT, line[: closer + 2], 0, closer + 2))
        index = closer + 2
    while index < length:
        ch = line[index]

        if ch.isspace():
            index += 1
            continue
        if ch == "%":
            # A question parked in a comment (`%   ?ВЕРСИЯ.`) is a question all the
            # same — the margin marks it and runs it (task_36) — so it is coloured
            # as one.  Only a comment that *starts* the line can be one: the rule
            # the margin uses is `%`, blanks and `?` where the line begins.  A `%`
            # inside a block comment never reaches here: the block is one token.
            rest = line[index:]
            if not line[:index].strip() and rest[1:].lstrip(" \t").startswith("?"):
                tokens.append(Token(QUERY_COMMENT, rest, index, length))
            else:
                tokens.append(Token(COMMENT, rest, index, length))
            break
        if line.startswith("/*", index):
            # The standard's block comment (task_92).  A line is tokenized on its
            # own, so an opener without its closer here colours the rest of the
            # line and tells the caller the comment is still open.
            closer = line.find("*/", index + 2)
            if closer < 0:
                tokens.append(Token(COMMENT, line[index:], index, length))
                return tokens, True
            end = closer + 2
            tokens.append(Token(COMMENT, line[index:end], index, end))
            index = end
            continue
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
            # The old dialect's long variable names: a name followed by an
            # apostrophe, and the apostrophe is a *suffix* — at the start of a token
            # it is still the quote of `'атом'`.  The one old mode reads it as one
            # name (task_77); in mode 0 the apostrophe is left where it is, the way
            # any malformed literal is (see the module docstring).
            if mode == MODE_OLD and end < length and line[end] == "'":
                end += 1
                text = line[index:end]
                tokens.append(Token(VARIABLE, text, index, end, alphabet_of(text)))
                index = end
                continue
            tokens.append(_identifier(text, index, end, keywords, mode))
            index = end
            continue

        pair = line[index : index + 2]
        if pair in (":-", "<-", "->", "\\+"):
            # `->` is a sign of its own since task_85 (ISO's if-then): without this
            # line the tokenizer would read `-` and `>`, and every front-end rule
            # built on the tokens would see two signs where the language has one.
            tokens.append(Token(PUNCTUATION, pair, index, index + 2))
            index += 2
            continue
        # The comparison signs are one token each, as in the lexer (task_52),
        # and the two-character forms win over their first character: `X >= 1`
        # must not read as `>` followed by `=`.
        if pair in (">=", "=<"):
            tokens.append(Token(OPERATOR, pair, index, index + 2))
            index += 2
            continue
        # The four standard-order signs (task_90) are three and two characters
        # long, and the longest wins: `@>=` is not `@>` followed by `=`, and
        # `@=<` is not `@` plus `=<`.
        triple = line[index : index + 3]
        if triple in ("@=<", "@>="):
            tokens.append(Token(OPERATOR, triple, index, index + 3))
            index += 3
            continue
        if pair in ("@<", "@>"):
            tokens.append(Token(OPERATOR, pair, index, index + 2))
            index += 2
            continue
        # The ISO arithmetic signs (task_92): `=:=` and `=\=` are three characters
        # and must be read before the `=` they start with, exactly as in the lexer.
        if triple in ("=:=", "=\\="):
            tokens.append(Token(OPERATOR, triple, index, index + 3))
            index += 3
            continue
        # `\=` (`\(A) = B`, «не унифицируется») is one sign, not `\` and `=`.
        if pair == "\\=":
            tokens.append(Token(OPERATOR, pair, index, index + 2))
            index += 2
            continue
        if ch in "=<>":
            tokens.append(Token(OPERATOR, ch, index, index + 1))
            index += 1
            continue
        tokens.append(Token(PUNCTUATION, ch, index, index + 1))
        index += 1
    return tokens, False


def literal_text(text: str) -> str:
    """What a `"…"` or `'…'` literal *says*, without its quotes.

    The tokenizer keeps every literal as it was written — the highlighter colours the
    characters on the line — while the interpreter's lexer hands out the decoded text.
    A caller that wants the *value* unwraps it here: the outer quotes go, `\\` and
    `\"` unfold, and a doubled `''` becomes one quote.  `task_69` reads the file name
    of an `ИМПОРТ` directive with this, and it must agree with the lexer or the window
    would look for a file called `"library.pld"`.
    """
    if len(text) < 2 or text[0] != text[-1] or text[0] not in "\"'":
        return text
    inner = text[1:-1]
    if text[0] == '"':
        return inner.replace("\\\\", "\\").replace('\\"', '"')
    return inner.replace("''", "'")


def mode_from_first_line(text: str, keywords: Keywords | None = None) -> int | None:
    """The naming mode a file declares in its first line, or `None` (task_67).

    A mirror of the interpreter's `readVariableMarker`, and the *only* thing the
    window works out for itself: the marker is the first line and nothing else —
    a comment above it, or anything on the line beyond the marker itself, means the
    file says nothing and the run's own mode stands.  A trailing comment is fine
    (`%` ends the line for the lexer, and for this), and `ИМЕНА` must be written
    exactly like that: the interpreter reserves the name, so it never lexes as a
    variable.

    `None` means «no marker», which is not the same as mode 0: a caller that has a
    mode of its own (the window's row, `--vars`) uses it in that case.  The answer
    is always a *mode*: a marker of `2` comes back as `1`, its own spelling
    (task_77), so no caller has to know about the two numbers.
    """
    first_line = plain_newlines(text).split("\n", 1)[0]
    parts = [token for token in tokenize(first_line, keywords)
             if token.kind not in (COMMENT, QUERY_COMMENT)]
    if len(parts) != 6:
        return None
    texts = [part.text for part in parts]
    if texts[0] != ":-" or texts[1] != MARKER_NAME:
        return None
    if texts[2] != "(" or texts[4] != ")" or texts[5] != ".":
        return None
    digit = parts[3]
    if digit.kind != INTEGER or len(digit.text) != 1 or not digit.text.isdigit():
        return None
    return MODE_NUMBERS.get(int(digit.text))


def _is_old_variable_name(text: str) -> bool:
    """One letter with at most one `_` after it — the old dialect's variable
    (`д`, `Б`, `A_`), the rule `isOldVariableName` applies in the lexer."""
    if not text or not is_letter(text[0]):
        return False
    return len(text) == 1 or (len(text) == 2 and text[1] == "_")


def _identifier(text: str, start: int, end: int, keywords: Keywords | None,
                mode: int = MODE_ISO) -> Token:
    if text.startswith("_"):
        return Token(VARIABLE, text, start, end, alphabet_of(text))
    # A reserved name wins over the variable rule: `ВЫП` starts with an
    # upper-case letter but is an atom, and the lexer decides that the same way —
    # in every mode, because the mode is only a way of reading names.
    if keywords is not None:
        keyword = keywords.get(text)
        if keyword is not None:
            kind = _KIND_OF_KEYWORD.get(keyword.kind, KEYWORD)
            return Token(kind, text, start, end, alphabet_of(text))
    if mode != MODE_ISO:
        # The old dialect: a variable is one letter (`isOldVariableName`), a bare
        # capitalised name is a string constant, everything else is an atom.
        if _is_old_variable_name(text):
            return Token(VARIABLE, text, start, end, alphabet_of(text))
        kind = STRING if is_upper_letter(text[0]) else ATOM
        return Token(kind, text, start, end, alphabet_of(text))
    kind = VARIABLE if is_upper_letter(text[0]) else ATOM
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

    The interesting case is the dot: it belongs to the number only when a digit
    follows it.  `12.3` is a real; the dot in `факт(1).` and in `X = 1.` ends the
    sentence.  The trailing-dot real of the original PrologD (`1.` for 1.0) is
    gone with the ISO rule of task_52.
    """
    index = start
    length = len(line)
    has_exponent = False
    while index < length:
        ch = line[index]
        if is_ascii_digit(ch):
            index += 1
            continue
        if ch == "." and not has_exponent:
            following = line[index + 1] if index + 1 < length else ""
            if is_ascii_digit(following):
                index += 1
                continue
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
