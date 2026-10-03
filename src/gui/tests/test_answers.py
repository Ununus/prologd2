"""Checks of the answer table's rules (Qt-free).

    python src/gui/tests/test_answers.py

The rules come from `engine.cpp::runQuery`: one query answers either with a word
(`ДА`/`НЕТ`, when it has no variables) or with a run of `Имя=значение` lines, one
block per solution, every variable of the query in the order the query spells
them.  A repeated name is therefore the beginning of the next solution, and that
one rule is what turns the run into rows.

The cases below are the ones the round was written from — the user's two-query
example, a ground query, a failing one — plus the traps: a program printing its
own lines inside an answer, a value that holds `=`, an empty value, an unbound
variable (`X=_1`), CRLF, and lines that only look like bindings (`x=5`, `=5`).
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.answers import Answer, parse  # noqa: E402


def check(text: str, expected: Answer, what: str) -> None:
    """One case: the answer of a text is exactly what was expected."""
    found = parse(text)
    assert found == expected, f"{what}: {found!r} instead of {expected!r}"


def test_one_solution_makes_one_row() -> None:
    """lesson_04's `?сумма(5, Сумма).` answers `Сумма=15`: one column, one row."""
    check(
        "Сумма=15\n",
        Answer(columns=("Сумма",), rows=(("15",),)),
        "one binding",
    )


def test_a_repeat_of_a_name_starts_the_next_solution() -> None:
    """The user's example: two facts, two solutions, two rows."""
    check(
        "X=вова\nY=корчагин\nX=данил\nY=ахмеров\n",
        Answer(
            columns=("X", "Y"),
            rows=(("вова", "корчагин"), ("данил", "ахмеров")),
        ),
        "two solutions",
    )


def test_one_variable_answers_three_rows() -> None:
    """`?член(X, [1,2,3]).` answers `X=1\nX=2\nX=3` — three rows, one column."""
    check(
        "X=1\nX=2\nX=3\n",
        Answer(columns=("X",), rows=(("1",), ("2",), ("3",))),
        "three solutions",
    )


def test_three_variables_keep_the_order_of_the_answer() -> None:
    """Columns come in the order the interpreter printed them, not sorted."""
    check(
        "Y=3\nX=2\nZ=_1\n",
        Answer(columns=("Y", "X", "Z"), rows=(("3", "2", "_1"),)),
        "three columns",
    )


def test_a_word_is_the_answer_of_a_ground_query() -> None:
    """`ДА` and `НЕТ`: no rows at all, one word — the tab shows one cell."""
    check("ДА\n", Answer(verdict="ДА"), "a ground query")
    check("НЕТ\n", Answer(verdict="НЕТ"), "a failing query")
    assert parse("ДА\n").is_empty() is False, "a word is an answer"
    assert parse("").is_empty() is True, "no text is no answer"
    assert parse("").solution_count() == 0


def test_a_word_next_to_bindings_is_not_the_answer() -> None:
    """A program's own `ДА` inside a solution must not replace the table."""
    check(
        "ДА\nX=1\nX=2\n",
        Answer(columns=("X",), rows=(("1",), ("2",))),
        "a printed word",
    )


def test_a_program_line_inside_the_answer_is_ignored() -> None:
    """`ВЫВОД` of a rule prints between the blocks; the table drops it."""
    check(
        "считаю…\nX=1\nготово\nX=2\n",
        Answer(columns=("X",), rows=(("1",), ("2",)), ignored=("считаю…", "готово")),
        "printed lines",
    )


def test_lines_that_only_look_like_bindings_are_ignored() -> None:
    """A lower-case name, a missing name, a space: none of them is a variable."""
    for line in ("x=5", "=5", "цена = 40", "X 5", "1=2"):
        check(line + "\n", Answer(ignored=(line,)), line)


def test_the_value_is_taken_verbatim() -> None:
    """The value is the rest of the line: spaces, `=`, brackets and all."""
    check("X=a=b\n", Answer(columns=("X",), rows=(("a=b",),)), "an `=` in the value")
    check("X=\n", Answer(columns=("X",), rows=(("",),)), "an empty value")
    check(
        "X=Ёё[1,2]_1\n",
        Answer(columns=("X",), rows=(("Ёё[1,2]_1",),)),
        "a list, printed as it is",
    )
    check("X=_1\n", Answer(columns=("X",), rows=(("_1",),)), "an unbound variable")
    check(
        "С=аб вг\n",
        Answer(columns=("С",), rows=(("аб вг",),)),
        "a space inside a value",
    )


def test_carriage_returns_and_blank_lines_are_not_data() -> None:
    """A chunk may arrive with CRLF; a blank line is not a row of its own."""
    check(
        "X=1\r\n\r\nX=2\r\n",
        Answer(columns=("X",), rows=(("1",), ("2",))),
        "CRLF and a blank line",
    )


def test_an_underscore_name_is_a_variable() -> None:
    """`_` opens a variable name in the lexer, so the table accepts it too."""
    check(
        "_1=7\nX_2=8\n",
        Answer(columns=("_1", "X_2"), rows=(("7", "8"),)),
        "underscore names",
    )


def test_the_table_of_the_example_programs_the_lessons_show() -> None:
    """The two-query text `F5` produces is *not* one table — a reminder in code.

    Two questions in one run answer with no separator at all, which is why only a
    single goal gets a table (task_59, §5).  Parsed as one text, the second
    question's first name repeats and looks like a third solution of the first —
    the shape of the input is all the parser can see, and it is right to say so.
    """
    found = parse("X=вова\nY=корчагин\nX=молоток\nY=40\n")
    assert found.rows == (("вова", "корчагин"), ("молоток", "40")), found.rows


def main(argv: list[str]) -> int:
    test_one_solution_makes_one_row()
    test_a_repeat_of_a_name_starts_the_next_solution()
    test_one_variable_answers_three_rows()
    test_three_variables_keep_the_order_of_the_answer()
    test_a_word_is_the_answer_of_a_ground_query()
    test_a_word_next_to_bindings_is_not_the_answer()
    test_a_program_line_inside_the_answer_is_ignored()
    test_lines_that_only_look_like_bindings_are_ignored()
    test_the_value_is_taken_verbatim()
    test_carriage_returns_and_blank_lines_are_not_data()
    test_an_underscore_name_is_a_variable()
    test_the_table_of_the_example_programs_the_lessons_show()
    print("all answer-table checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
