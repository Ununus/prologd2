"""Where a name is defined, and which name the caret is on (task_103).

Two questions about a text and a caret, and nothing else: `name_at` answers «what
word is here», `first_definition` answers «where is the first clause of that
name».  F12 is the caller — together with the `ИМПОРТ` lookup of task_69, which
still wins when the caret is on a directive.

Qt-free, and deliberately line-based like the completion scan: a file being edited
may not parse at all, and a jump must work in it anyway.  A clause *head* is
recognised by the shape every program has — the first token of the line is the
name and the next one is `(`, `.` or `:-` — so a goal, a query and a comment can
never be mistaken for a definition.

    python src/gui/tests/test_definitions.py
"""

from __future__ import annotations

from . import tokens

#: A name in the document: the characters the tokenizer counts as one.
_NAME_KINDS = (tokens.ATOM, tokens.KEYWORD, tokens.QUOTED_ATOM)


def name_at(text: str, position: int) -> str | None:
    """The name the caret sits in, or touches on either side.

    A caret is put *between* characters, so both sides are read: F12 with the
    caret at the start of `член`, in the middle of it and right after it are the
    same command.  `None` when the caret touches no name at all (a bracket, a
    space, the end of a sentence).  A quoted atom is handed back without its
    quotes when the caret is inside it, which is how the callers compare it.
    """
    if position < 0 or position > len(text):
        return None
    start = position
    while start > 0 and tokens.is_name_character(text[start - 1]):
        start -= 1
    end = position
    while end < len(text) and tokens.is_name_character(text[end]):
        end += 1
    if start == end:
        return None
    return text[start:end]


def first_definition(
    text: str, name: str, keywords=None, mode: int = tokens.MODE_ISO
) -> tuple[int, int] | None:
    """The line (0-based) and column of the first clause head of `name`.

    A head is the first token of its line and the next token opens its arguments,
    ends the sentence or starts the body: `факт(1).`, `дождь.`, `правило(X):-…`.
    A line that begins with a directive (`:-`) or a question (`?`) is skipped, and
    so is a comment — a name mentioned in prose is not a definition.  A quoted
    head (`'Вася'(15, …)`) matches its unquoted spelling.
    """
    if not name:
        return None
    for number, line in enumerate(text.splitlines()):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.startswith((":-", "?")):
            continue
        line_tokens = tokens.tokenize(line, keywords, mode)
        if len(line_tokens) < 2:
            continue
        head = line_tokens[0]
        if head.kind not in _NAME_KINDS:
            continue
        spelled = (
            tokens.literal_text(head.text)
            if head.kind == tokens.QUOTED_ATOM
            else head.text
        )
        if spelled != name:
            continue
        if line_tokens[1].text in ("(", ".", ":-"):
            return number, head.start
    return None
