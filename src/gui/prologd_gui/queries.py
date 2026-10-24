"""The lines of a program that are questions, as the editor's margin needs them.

    >>> find_statements("?сумма(5, С).\\n", keywords)
    [(1, '?сумма(5, С).')]

A lesson is read top to bottom with `Enter` on the console: every `?Цель.` line
is a question, and loading the file runs it.  A lesson also *talks* about its
questions, in comments:

    %   ?ВЕРСИЯ.                       - a question parked in a comment
    % ?длина(Х, 2) не завершится. ... - prose that only starts like one
    %! С=15                            - a recorded answer, not a question

The margin draws a run marker next to the first kind and the parked questions,
and none next to the prose.  The rule, in one sentence: the first non-blank
characters of the line are `?` or `%` followed by blanks and `?`, the sentence
ends at the first `.` outside `"..."`, `'...'` and `#...#` and outside every
bracket, and every bare word inside it is a variable (upper case or `_`), a
reserved name, or a name the document itself uses.  A `'` opens `'атом'` only
where a token may start: after a name it is the old dialect's suffix (`Ф'`,
`Сумма'`), exactly as `tokens.scan_line` reads it — one apostrophe must not
swallow the sentence's own `.` (part 149).

The last clause is what separates a *commented* question from prose, and it is
deliberately shallow: `?длина(Х, 2) не завершится.` is refused because `не` is a
bare word that is neither reserved nor used anywhere in the document.  A live
line needs no such defence — a line beginning with `?` is executed by the run
itself, so it is a question by construction (and its own words count as used,
because the line is part of the document).  This is not a parser and must not
become one — an unaccepted name means *no marker*, and no marker is a small
loss, while a marker that runs the wrong text is a wrong program.  The scan is
line-local, so a statement split across lines gets no marker: running half of it
would be worse than not offering it.
"""

from __future__ import annotations

from .completion import collect_names
from .keywords import Keywords
from .tokens import is_letter, is_name_character, is_upper_letter

#: What a word may be to belong to a sentence (beyond a variable or a reserved
#: name): the names the document itself spells out — its predicates and atoms.
Names = set[str]


def find_statements(text: str, keywords: Keywords | None = None) -> list[tuple[int, str]]:
    """Every runnable statement of the document, as `(line, statement)`.

    Lines are 1-based, as the margin counts them, and appear in document order.
    `statement` is the text from `?` to the closing `.`, exactly as written, so
    what the margin runs is what the reader sees.  Without `keywords` only the
    document's own names are accepted (a program can still question its own
    predicates); with them the reserved names count too.
    """
    names = _document_names(text, keywords)
    found: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        statement = _statement_in_line(line, keywords, names)
        if statement is not None:
            found.append((number, statement))
    return found


def statement_at(text: str, line: int, keywords: Keywords | None = None) -> str | None:
    """The statement of one 1-based line, or None — `find_statements` for a line."""
    lines = text.splitlines()
    if line < 1 or line > len(lines):
        return None
    return _statement_in_line(lines[line - 1], keywords, _document_names(text, keywords))


def _document_names(text: str, keywords: Keywords | None) -> Names:
    """The bare words the document itself uses — its predicates and atoms."""
    calls, atoms, _quoted, _notes = collect_names(text, keywords)
    return set(calls) | set(atoms)


def _statement_in_line(line: str, keywords: Keywords | None, names: Names) -> str | None:
    start = _question_start(line)
    if start is None:
        return None
    for end in _candidate_ends(line, start):
        candidate = line[start : end + 1]
        if _is_sentence(candidate, keywords, names):
            return candidate
    return None


def _question_start(line: str) -> int | None:
    """Where the question begins, or None when the line cannot hold one.

    Only the very start of the line counts — `?…` or `% ?…` (any amount of
    blank space, `%?` included).  `%!` and every other comment are prose.
    """
    index = 0
    while index < len(line) and line[index] in " \t":
        index += 1
    if index < len(line) and line[index] == "%":
        index += 1
        while index < len(line) and line[index] in " \t":
            index += 1
        if index >= len(line) or line[index] != "?":
            return None
    elif index >= len(line) or line[index] != "?":
        return None
    return index


def _starts_quoted_atom(line: str, index: int) -> bool:
    """Whether the `'` at `index` opens `'атом'` rather than ending a name.

    The old dialect writes a long name with a trailing apostrophe (`Ф'`, `Сумма'`),
    and the tokenizer reads such a quote as part of the name: a quoted atom starts
    only where a token starts (`tokens.scan_line`).  Reading `Ф'` as the opening of
    an unterminated atom swallowed the sentence's own `.`, so a live question with
    one apostrophe in it got no margin marker while two of them did (part 149).
    """
    return index == 0 or not is_name_character(line[index - 1])


def _candidate_ends(line: str, start: int):
    """The positions a sentence could end at, left to right.

    A `.` outside `"..."`, `'...'` and `#...#` and outside every bracket is
    where the scan *tries* to end; the caller decides whether what came before
    it is a sentence.  A `.` inside a bracket belongs to that bracket's content
    — `?факт(1.5).` must not end inside the number.  A `%` ends the scan:
    nothing after a comment can still be part of the question.
    """
    closing = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    in_string = in_quoted = in_expr = False
    index = start
    while index < len(line):
        char = line[index]
        if in_string:
            if char == '"':
                in_string = False
        elif in_quoted:
            if char == "'":
                in_quoted = False
        elif in_expr:
            if char == "#":
                in_expr = False
        elif char == '"':
            in_string = True
        elif char == "'" and _starts_quoted_atom(line, index):
            in_quoted = True
        elif char == "#":
            in_expr = True
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if not stack or stack[-1] != closing[char]:
                # A closing bracket that matches nothing: `?факт[1).` is a typo,
                # and a marker on a typo runs text that cannot run.
                return
            stack.pop()
        elif char == "%":
            return
        elif char == "." and not stack:
            yield index
        index += 1


def _is_sentence(text: str, keywords: Keywords | None, names: Names) -> bool:
    """Is the candidate a runnable sentence, or is it prose?

    Balance is settled by construction — `_candidate_ends` only offers ends it
    has counted to — so what is left is the words.  Anything quoted is skipped:
    an atom or a string may contain any text at all.
    """
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == '"' or (char == "'" and _starts_quoted_atom(text, index)):
            index += 1
            while index < length and text[index] != char:
                index += 1
            index += 1
        elif char.isdigit():
            index += 1
            while index < length and (is_name_character(text[index]) or text[index] == "."):
                index += 1
        elif is_letter(char) or char == "_":
            start = index
            while index < length and is_name_character(text[index]):
                index += 1
            if not _accepts(text[start:index], keywords, names):
                return False
        else:
            index += 1
    return True


def _accepts(word: str, keywords: Keywords | None, names: Names) -> bool:
    """A variable, a reserved name, or a name the document uses — and nothing else."""
    if word[0] == "_" or is_upper_letter(word[0]):
        return True
    if keywords is not None and keywords.is_reserved(word):
        return True
    return word in names
