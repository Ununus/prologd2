"""Checks of `definitions.py`: the name under the caret and where it starts (task_103).

Qt-free: both questions are about a text and a position.

    python src/gui/tests/test_definitions.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import definitions  # noqa: E402

DOCUMENT = """\
% член(Элемент, Список) — истина, если Элемент входит в Список
член(X, [X|_]).
член(X, [_|Хвост]) :- член(X, Хвост).

дождь.
мокро :-член(1, [1]).

:- ВЫВОД("привет").

?член(2, [1, 2]).
"""


def test_the_caret_finds_the_name_on_either_side_of_it() -> None:
    """A caret stands *between* characters, so both sides count."""
    line = 'цель(X):-член(X, Л).'
    start = line.index("член")
    assert definitions.name_at(line, start) == "член"
    assert definitions.name_at(line, start + 2) == "член"
    # Right after the last letter, before the bracket: still the name.
    assert definitions.name_at(line, start + 4) == "член"
    # In the whitespace, at the end of a sentence and before anything: no name.
    assert definitions.name_at(line, line.index(" ")) is None
    assert definitions.name_at("факт(1).", 8) is None
    assert definitions.name_at("", 0) is None
    # A quoted atom is handed back without its quotes.
    quoted = "факт('Вася')."
    assert definitions.name_at(quoted, quoted.index("В")) == "Вася"
    print("ok: the name under the caret is read from either side of it")


def test_the_first_clause_is_found_by_its_shape() -> None:
    """A head is the first token of a line; goals, queries and prose are not."""
    assert definitions.first_definition(DOCUMENT, "член") == (1, 0), (
        definitions.first_definition(DOCUMENT, "член")
    )
    # A predicate of no arguments: `дождь.` is a head, `мокро :-` too.
    assert definitions.first_definition(DOCUMENT, "дождь") == (4, 0)
    assert definitions.first_definition(DOCUMENT, "мокро") == (5, 0)
    # `ВЫВОД` appears in a directive and `член` in the query — neither is a head,
    # so both answer with what the document really defines, or with nothing.
    assert definitions.first_definition(DOCUMENT, "ВЫВОД") is None
    assert definitions.first_definition(DOCUMENT, "нетакого") is None
    print("ok: a clause head is told from a goal, a query and a comment")


def test_a_quoted_head_and_a_space_before_the_bracket_count() -> None:
    text = "'Вася'(15, задунайский).\nправило (X):-цель(X).\n"
    assert definitions.first_definition(text, "Вася") == (0, 0)
    assert definitions.first_definition(text, "правило") == (1, 0)
    print("ok: a quoted head matches its unquoted spelling, a space does not hurt")


def main(argv: list[str]) -> int:
    test_the_caret_finds_the_name_on_either_side_of_it()
    test_the_first_clause_is_found_by_its_shape()
    test_a_quoted_head_and_a_space_before_the_bracket_count()
    print("all definitions checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
