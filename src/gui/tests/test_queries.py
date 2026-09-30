"""Checks of the rule that says which lines are questions (Qt-free).

    python src/gui/tests/test_queries.py [--print]

Two kinds of check, like `test_tokens.py`:

* a table of lines — the ones task_36 was written from, plus the traps the rule
  has to survive: prose that begins like a query, a recorded answer, a `.` inside
  a number, a statement split across lines;
* a sweep over every example program pinning how many statements the margin
  offers in each file.  The numbers are what a change to the rule moves; a count
  that moves while no lesson was edited means the rule drifted.  The sweep takes
  the reserved names from a real interpreter session (`ready`), so a built-in
  renamed on the C++ side that the rule would then refuse fails here.

`--print` prints the sweep's counts as a Python dict — how `PINNED` below is
refreshed after a lesson is edited on purpose.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.keywords import Keywords  # noqa: E402
from prologd_gui.queries import find_statements, statement_at  # noqa: E402

from protocol_smoke import check_default_executable, find, run_session  # noqa: E402

# The reserved names these rows need, trimmed the way `test_tokens.py` trims its
# table; the sweep uses the interpreter's real one.
TABLE = Keywords(
    [
        {"name": "сумма", "kind": "predicate", "arities": [2]},
        {"name": "цена", "kind": "predicate", "arities": [2]},
        {"name": "БОЛЬШЕ", "kind": "predicate", "arities": [2]},
        {"name": "длина", "kind": "predicate", "arities": [2]},
        {"name": "ВЕРСИЯ", "kind": "predicate", "arities": [0]},
        {"name": "is_whole", "kind": "predicate", "arities": [1]},
        {"name": "ВЫВОД", "kind": "predicate", "arities": [], "variadic": True},
    ]
)

#: The document the rows are read in: it is where the bare names come from that
#: are not reserved (`хлеб`, `monk`) and where the refused names are absent
#: (`идиотизм`, `int`).
DOCUMENT = "цена(хлеб, 40).\nmonk(14).\nis_whole(4).\nдлина(Х, 2).\n"

#: (line, expected statement) — every row is a rule that could drift.
CASES: list[tuple[str, str | None]] = [
    # The table task_36 was written from, in its own words.
    ("?сумма(5, С).", "?сумма(5, С)."),
    ("%   ?ВЕРСИЯ.", "?ВЕРСИЯ."),
    (
        "% ?цена(хлеб, Ц1), БОЛЬШЕ(#Ц1 + 1#, 40). - см. раздел 7.",
        "?цена(хлеб, Ц1), БОЛЬШЕ(#Ц1 + 1#, 40).",
    ),
    ("% ?длина(Х, 2) не завершится.  Проверка длины стоит в правиле *после* рекурсии,", None),
    ('% ?is_whole("4").', '?is_whole("4").'),
    ("%! С=15", None),
    ("% Деление: 5 / 2 — это 2.", None),
    # `?int("4").` was a question of lesson_03 once; `int` is a retired spelling
    # now, so the margin must not offer it — the call would fail at run time.
    ('% ?int("4").', None),
    # `%?` with no space at all: `monk.pld` writes its questions this way.
    ("%?monk(14).", "?monk(14)."),
    # The sentence ends at the first free `.`; prose after it stays outside.
    ("?цена(хлеб, Ц1). Проверьте, что скажет интерпретатор.", "?цена(хлеб, Ц1)."),
    # A `.` inside brackets belongs to the number, not to the sentence.
    ("?сумма(1.5, С).", "?сумма(1.5, С)."),
    # A `?` inside a string is just text.
    ('?ВЫВОД("?сумма(5, С).").', '?ВЫВОД("?сумма(5, С).").'),
    # An unknown bare word makes prose *in a comment*.  In a live line the same
    # word is a name the document uses (the line is part of it), which is right:
    # a run executes that line, so it is a question by construction.
    ("% ?сумма(5, идиотизм).", None),
    ("?сумма(5, идиотизм).", "?сумма(5, идиотизм)."),
    # A question the rule cannot read to the end is no question at all.
    ("?сумма(5, С", None),
    ("?сумма[5, С).", None),
]

#: Counts of `find_statements` per example program (posix separators), refreshed
#: with `--print` when a lesson gains or loses a question on purpose.
PINNED: dict[str, int] = {
    "diamond/base.pld": 0,
    "diamond/left.pld": 0,
    "diamond/main.pld": 5,
    "diamond/right.pld": 0,
    "drawing.pld": 1,
    "factorial.pld": 1,
    "file_io.pld": 3,
    "findall_demo.pld": 2,
    "import_demo.pld": 2,
    "lessons/_old/lesson_1.pld": 15,
    "lessons/_old/lesson_2.pld": 6,
    "lessons/_old/lesson_3.pld": 1,
    "lessons/_old/lesson_4.pld": 3,
    "lessons/_old/lesson_5.pld": 3,
    "lessons/_old/lesson_6.pld": 2,
    "lessons/_old/lesson_8.pld": 3,
    "lessons/_old/lesson_9.pld": 5,
    "lessons/appendix_debug.pld": 7,
    "lessons/lesson_01.pld": 9,
    "lessons/lesson_02.pld": 12,
    "lessons/lesson_03.pld": 34,
    "lessons/lesson_04.pld": 24,
    "lessons/lesson_05.pld": 22,
    "lessons/lesson_06.pld": 37,
    "lessons/lesson_07.pld": 19,
    "lessons/lesson_08.pld": 8,
    "lessons/lesson_09.pld": 10,
    "lessons/lesson_10.pld": 18,
    "lessons/lesson_11.pld": 5,
    "lessons/lesson_12.pld": 10,
    "lib/library.pld": 0,
    "monk.pld": 2,
    "monkd.pld": 1,
}


def test_the_table_of_lines() -> None:
    for line, expected in CASES:
        found = find_statements(f"{DOCUMENT}{line}\n", TABLE)
        got = found[0][1] if found else None
        assert got == expected, f"{line!r}: expected {expected!r}, got {got!r}"
    print(f"ok: {len(CASES)} lines, from a parked question to prose and a recorded answer")


def test_find_statements_keeps_document_order() -> None:
    text = f"?сумма(5, С).\n% ?ВЕРСИЯ.\n{DOCUMENT}факт(1).\n"
    assert find_statements(text, TABLE) == [(1, "?сумма(5, С)."), (2, "?ВЕРСИЯ.")]
    print("ok: statements come back in document order with their line numbers")


def test_a_statement_split_across_lines_gets_no_marker() -> None:
    # Running half a statement would be worse than not offering it: the rule is
    # line-local, and so is the margin.
    assert find_statements("?сумма(5,\n С).\n", TABLE) == []
    print("ok: a statement split across two lines is left alone")


def test_statement_at_finds_one_line() -> None:
    text = "?сумма(5, С).\n%   ?ВЕРСИЯ.\n% текст\n"
    assert statement_at(text, 1, TABLE) == "?сумма(5, С)."
    assert statement_at(text, 2, TABLE) == "?ВЕРСИЯ."
    assert statement_at(text, 3, TABLE) is None
    assert statement_at(text, 0, TABLE) is None
    assert statement_at(text, 99, TABLE) is None
    print("ok: statement_at answers for one line and refuses what does not exist")


def interpreter_keywords() -> Keywords:
    """The reserved names of the built interpreter, as `ready` reports them."""
    code, events = run_session(check_default_executable(), [])
    assert code == 0, f"exit code {code}"
    return Keywords(find(events, "ready")["keywords"])


def example_counts() -> dict[str, int]:
    root = pathlib.Path(__file__).resolve().parents[3] / "examples"
    files = sorted(root.rglob("*.pld"))
    assert files, f"no example programs under {root}"
    keywords = interpreter_keywords()
    return {
        path.relative_to(root).as_posix(): len(
            find_statements(path.read_text(encoding="utf-8"), keywords)
        )
        for path in files
    }


def test_every_example_program_has_the_pinned_number_of_questions() -> None:
    counts = example_counts()
    if counts != PINNED:
        missing = {name: count for name, count in counts.items() if PINNED.get(name) != count}
        raise AssertionError(
            "the statement counts moved — if a lesson changed on purpose, refresh"
            f" PINNED with `--print`; now: {missing}"
        )
    total = sum(counts.values())
    print(f"ok: {total} questions in {len(counts)} example programs, as pinned")


def test_the_acceptance_lesson_lines_carry_a_marker() -> None:
    """The two files task_36 names by hand: the lesson and the appendix."""
    root = pathlib.Path(__file__).resolve().parents[3] / "examples" / "lessons"
    keywords = interpreter_keywords()
    lesson = (root / "lesson_04.pld").read_text(encoding="utf-8")
    assert "?сумма(5, С)." in [text for _line, text in find_statements(lesson, keywords)]
    appendix = (root / "appendix_debug.pld").read_text(encoding="utf-8")
    assert "?ВЕРСИЯ." in [text for _line, text in find_statements(appendix, keywords)]
    print("ok: lesson_04 and appendix_debug offer their questions to the margin")


def test_no_live_question_is_left_without_a_marker() -> None:
    """Every line a run would execute as a question is offered by the margin.

    This is the half of the rule that costs when it is wrong: a *refused* live
    question is a marker missing where the user can see the question run.  (The
    other half — a marker on prose — is a click that fails visibly, and the
    table above pins where the rule refuses.)
    """
    root = pathlib.Path(__file__).resolve().parents[3] / "examples"
    keywords = interpreter_keywords()
    refused = []
    for path in sorted(root.rglob("*.pld")):
        text = path.read_text(encoding="utf-8")
        accepted = {line for line, _statement in find_statements(text, keywords)}
        for number, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("?") and number not in accepted:
                refused.append(f"{path.relative_to(root).as_posix()}:{number}")
    assert not refused, f"live questions with no marker: {refused}"
    print("ok: every live ?-line of every example program has a marker")


def main(argv: list[str]) -> int:
    if "--print" in argv[1:]:
        print("PINNED = {")
        for name, count in example_counts().items():
            print(f'    "{name}": {count},')
        print("}")
        return 0
    test_the_table_of_lines()
    test_find_statements_keeps_document_order()
    test_a_statement_split_across_lines_gets_no_marker()
    test_statement_at_finds_one_line()
    test_every_example_program_has_the_pinned_number_of_questions()
    test_the_acceptance_lesson_lines_carry_a_marker()
    test_no_live_question_is_left_without_a_marker()
    print("all question checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
