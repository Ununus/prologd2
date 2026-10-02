"""The answer of one goal seen as a table: variables become columns (task_59).

The interpreter answers one query with either a word or a run of `Имя=значение`
lines (`engine.cpp::runQuery`): every variable of the query is printed, in the
order the query spells them, once per solution, and `ДА`/`НЕТ` is printed only
when there are no variables at all.  So the two forms never mix inside one query,
and a *repeat* of a name is exactly where the next solution begins.

    >>> parse("X=вова\\nY=корчагин\\nX=данил\\nY=ахмеров\\n").rows
    (('вова', 'корчагин'), ('данил', 'ахмеров'))
    >>> parse("X=1\\nX=2\\nX=3\\n").columns
    ('X',)
    >>> parse("X=1\\nX=2\\nX=3\\n").rows
    (('1',), ('2',), ('3',))
    >>> parse("ДА\\n").verdict
    'ДА'
    >>> parse("НЕТ\\n").verdict
    'НЕТ'
    >>> parse("цена 40\\nX=15\\n").ignored
    ('цена 40',)

Qt-free on purpose: this is a rule about text, and a rule about text is worth
testing without a display (the pane and the window only carry the result).

What it deliberately does not do:

* it does not parse values — a value is the rest of the line, exactly as the
  interpreter printed it (`абвг`, `-а`, `Ёё[1,2]_1`, `_1`);
* it does not guess: a line of any other shape is *ignored*, which is what a
  program's own output inside an answer looks like.  The price is that a program
  printing a line whose shape is exactly `Имя=значение` counts as a solution —
  the text in «Выводе» stays the exact record either way;
* it knows nothing about the goal that was asked: the window gives it one
  query's answer and nothing else, which is what makes the table exact.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tokens import is_name_character, is_upper_letter

#: The two words the interpreter answers a query without variables with.  They
#: are recognised as an answer only when the text holds no bindings at all.
VERDICTS = ("ДА", "НЕТ")


@dataclass(frozen=True)
class Answer:
    """One answer, as a table: the columns, the rows, and what was left over."""

    #: The variable names, in the order the answer printed them.
    columns: tuple[str, ...] = ()
    #: One tuple per solution, aligned with `columns`; a cell is the printed value.
    rows: tuple[tuple[str, ...], ...] = ()
    #: `ДА` or `НЕТ` — set only when the answer holds no bindings.
    verdict: str = ""
    #: Lines that are neither a binding nor a verdict, verbatim (the program's
    #: own output, which the table shows nowhere).
    ignored: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        """True when there is nothing to show: no rows and no word."""
        return not self.rows and not self.verdict

    def solution_count(self) -> int:
        """How many rows the table has — the count in the tab's title."""
        return len(self.rows)


def parse(text: str) -> Answer:
    """Builds the table of one answer; see the module docstring for the rules."""
    columns: list[str] = []
    rows: list[dict[str, str]] = [{}]
    ignored: list[str] = []
    word = ""
    seen_binding = False
    for raw in text.splitlines():
        # A chunk of the protocol may arrive with CRLF; the value itself is kept
        # verbatim, so only the carriage return of the line ending goes.
        line = raw[:-1] if raw.endswith("\r") else raw
        if not line.strip():
            continue
        binding = _binding(line)
        if binding is None:
            stripped = line.strip()
            if stripped in VERDICTS:
                word = stripped
            else:
                ignored.append(line)
            continue
        seen_binding = True
        name, value = binding
        if name in rows[-1]:
            # The same name twice: the answer moved on to the next solution.
            rows.append({})
        if name not in columns:
            columns.append(name)
        rows[-1][name] = value

    if not seen_binding:
        # A word, and nothing else: no rows to align, so none are made.
        return Answer(
            verdict=word if word in VERDICTS else "",
            ignored=tuple(ignored),
        )
    table = tuple(tuple(row.get(name, "") for name in columns) for row in rows)
    return Answer(columns=tuple(columns), rows=table, ignored=tuple(ignored))


def _binding(line: str) -> tuple[str, str] | None:
    """`(name, value)` when the line is `Имя=значение`, else None.

    The name is checked with the *lexer's* rule, mirrored in `tokens.py`: a name
    that starts with `_`, or with an upper-case letter and is not reserved
    (`lexer.cpp::lexIdentifier`).  The value is everything after the first `=`,
    untrimmed — `X=` is what an empty string prints as.
    """
    position = line.find("=")
    if position <= 0:
        return None
    name = line[:position]
    if not (name.startswith("_") or is_upper_letter(name[0])):
        return None
    if not all(is_name_character(ch) for ch in name[1:]):
        return None
    return name, line[position + 1 :]
