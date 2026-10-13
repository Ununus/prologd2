"""Checks of the naming modes of a file (task_67, Qt-free).

    python src/gui/tests/test_variable_modes.py [path-to-prologu]

The window works out the mode of a document itself — the file's own
`:- ИМЕНА(N).` first line, or its own settings row — because the highlighter cannot
ask the interpreter on every keystroke.  That makes this module a second
implementation of `readVariableMarker` in `src/prlib/src/lexer.cpp`, and this file
is what keeps the two together: the rule is checked on its own, and then against
the *interpreter's* own reading of the same texts, asked by behaviour
(`?РАВНО(д, 1).` answers differently in the three modes).
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.keywords import Keywords  # noqa: E402
from prologd_gui.tokens import (  # noqa: E402
    ATOM,
    KEYWORD,
    MODE_ISO,
    MODE_SINGLE_LETTER,
    MODE_SINGLE_LETTER_APOSTROPHE,
    PUNCTUATION,
    QUOTED_ATOM,
    STRING,
    VARIABLE,
    mode_from_first_line,
    tokenize,
)

TABLE = Keywords([{"name": "ВЫВОД", "kind": "predicate", "arities": []}])


def kinds(line: str, mode: int = MODE_ISO) -> list[tuple[str, str]]:
    return [(token.kind, token.text) for token in tokenize(line, TABLE, mode)]


def test_mode_one_reads_the_old_dialect() -> None:
    assert kinds("голова(д)", MODE_SINGLE_LETTER) == [
        (ATOM, "голова"),
        (PUNCTUATION, "("),
        (VARIABLE, "д"),
        (PUNCTUATION, ")"),
    ]
    # A variable is one letter, either case, with at most one `_` after it.
    for name in ("д", "Б", "A", "A_", "x_"):
        assert kinds(f"голова({name})", MODE_SINGLE_LETTER)[2] == (VARIABLE, name)
    # A bare capitalised name is a string constant; a lowercase one stays an atom.
    assert kinds("голова(Молоко)", MODE_SINGLE_LETTER)[2] == (STRING, "Молоко")
    assert kinds("голова(молоко)", MODE_SINGLE_LETTER)[2] == (ATOM, "молоко")
    assert kinds("голова(_д)", MODE_SINGLE_LETTER)[2] == (VARIABLE, "_д")
    # The reserved table wins over the mode, exactly as it does in the lexer.
    assert kinds("ВЫВОД(д)", MODE_SINGLE_LETTER)[0] == (KEYWORD, "ВЫВОД")
    # Mode 0 is untouched by all of this.
    assert kinds("голова(д)", MODE_ISO)[2] == (ATOM, "д")
    assert kinds("голова(Молоко)", MODE_ISO)[2] == (VARIABLE, "Молоко")


def test_mode_two_adds_the_apostrophe_names() -> None:
    assert kinds("голова(Сумма')", MODE_SINGLE_LETTER_APOSTROPHE)[2] == (
        VARIABLE,
        "Сумма'",
    )
    # In mode 1 that name is the error the interpreter explains; here the name keeps
    # the mode-1 reading and the apostrophe stays a quote — a malformed literal is
    # coloured as the text it looks like (see the tokenizer's docstring).
    assert kinds("голова(Сумма')", MODE_SINGLE_LETTER)[2] == (STRING, "Сумма")
    # At the start of a token the apostrophe is still the quote of an atom.
    assert kinds("голова('Сумма')", MODE_SINGLE_LETTER_APOSTROPHE)[2] == (
        QUOTED_ATOM,
        "'Сумма'",
    )


def test_the_first_line_names_the_mode() -> None:
    assert mode_from_first_line(":- ИМЕНА(0).\nдлинное:-истина.\n") == MODE_ISO
    assert mode_from_first_line(":- ИМЕНА(1).\n") == MODE_SINGLE_LETTER
    assert mode_from_first_line(":-ИМЕНА( 2 ).") == MODE_SINGLE_LETTER_APOSTROPHE
    assert (
        mode_from_first_line(":- ИМЕНА(1). % так писали в старом курсе\n")
        == MODE_SINGLE_LETTER
    )
    assert mode_from_first_line(":- ИМЕНА(1).\r\n") == MODE_SINGLE_LETTER
    # Not the first line, so not the marker: the file keeps the mode of the run.
    assert mode_from_first_line("% комментарий\n:- ИМЕНА(1).\n") is None
    assert mode_from_first_line("\n:- ИМЕНА(1).\n") is None
    # Anything else on the line, a name that is not the marker's, a mode outside
    # 0…2 — every one of them means «the file says nothing».
    assert mode_from_first_line(":- ИМЕНА(1), ИМЕНА(2).\n") is None
    assert mode_from_first_line(":- ИМЕНА(1). :- ВЫВОД(1).\n") is None
    assert mode_from_first_line(":- имена(1).\n") is None
    assert mode_from_first_line(":- ИМЕНА(3).\n") is None
    assert mode_from_first_line(":- ИМЕНА().\n") is None
    assert mode_from_first_line(":- ИМЕНА(1)\n") is None
    assert mode_from_first_line("") is None


def ask(executable: str, program: str, statement: str, mode: int | None) -> list[str]:
    """Loads a program quietly and asks one statement, with or without `vars`."""
    request: dict = {"cmd": "query", "text": statement}
    if mode is not None:
        request["vars"] = mode
    payload = "\n".join(
        [
            json.dumps(
                {"cmd": "load", "text": program, "name": "<buffer>", "questions": False}
            ),
            json.dumps(request),
            json.dumps({"cmd": "quit"}),
        ]
    )
    done = subprocess.run(
        [executable, "--protocol", "json"], input=payload.encode(), capture_output=True,
        timeout=60,
    )
    events = [json.loads(line) for line in done.stdout.decode("utf-8", "replace").splitlines()]
    return [str(event["text"]).strip() for event in events if event.get("event") == "output"]


def test_a_question_of_a_mode_one_file_keeps_its_names(executable: str) -> None:
    """A question asked on its own arrives without the file's first line.

    That is the margin marker and the goal line: the program is loaded quietly and
    one statement is asked afterwards, so the mode has to travel with the question.
    Without it `Вова` of a mode-1 program is read as a free variable and the
    question matches the first student instead of the one the file means — the bug
    the user found in the window (task_67).
    """
    program = ":- ИМЕНА(1).\nстудент(Вова).\nстудент(Данил).\n"
    assert ask(executable, program, "?студент(Вова).", MODE_SINGLE_LETTER) == ["ДА"]
    misread = ask(executable, program, "?студент(Вова).", None)
    assert misread and misread[0].startswith("Вова="), misread


def check_default_executable() -> str | None:
    """The engine the window itself would run (`prologd_gui.paths`, task_75)."""
    from prologd_gui import paths

    executable = paths.interpreter()
    return executable if pathlib.Path(executable).is_file() else None


def run_probe(executable: str, text: str, workdir: pathlib.Path):
    """Runs `text` (a first line plus one question) and returns its output."""
    path = workdir / "probe.pld"
    path.write_text(text, encoding="utf-8", newline="\n")
    done = subprocess.run([executable, "-s", str(path)], capture_output=True, timeout=60)
    return (
        done.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
        done.stderr.decode("utf-8", "replace"),
    )


def interpreter_mode(executable: str, text: str, workdir: pathlib.Path) -> int:
    """The mode the interpreter reads `text` in, asked by behaviour.

    Two questions, one per run, because a file that stops at a lexer error prints
    nothing at all: `д` is a variable in modes 1 and 2 (the answer is `д=1`) and an
    atom in mode 0 (`НЕТ`), and `Сумма'` is a variable in mode 2 alone — mode 1
    explains the apostrophe, mode 0 reads it as the opening quote of an atom that
    never closes.  A marker that is not on the first line never becomes a mode: the
    load stops with the built-in's own message instead.
    """
    out, err = run_probe(executable, text + "?РАВНО(д, 1).\n", workdir)
    if "режим имён" in err or "д=1" not in out:
        return MODE_ISO
    apostrophe, _ = run_probe(executable, text + "?РАВНО(Сумма', 5).\n", workdir)
    return (
        MODE_SINGLE_LETTER_APOSTROPHE if "Сумма'" in apostrophe else MODE_SINGLE_LETTER
    )


def test_the_python_rule_matches_the_interpreter(executable: str) -> None:
    texts = [
        ":- ИМЕНА(0).\n",
        ":- ИМЕНА(1).\n",
        ":- ИМЕНА(2).\n",
        "",
        "истина.\n",
        "% комментарий\n:- ИМЕНА(1).\n",
        "\n:- ИМЕНА(1).\n",
    ]
    with tempfile.TemporaryDirectory() as folder:
        workdir = pathlib.Path(folder)
        for text in texts:
            declared = mode_from_first_line(text)
            expected = MODE_ISO if declared is None else declared
            assert interpreter_mode(executable, text, workdir) == expected, text


def main() -> int:
    executable = sys.argv[1] if len(sys.argv) > 1 else check_default_executable()
    test_mode_one_reads_the_old_dialect()
    test_mode_two_adds_the_apostrophe_names()
    test_the_first_line_names_the_mode()
    print("ok: the naming modes of a file")
    if executable is None:
        print("skipped: no prologu build found, the cross-check did not run")
        return 0
    test_the_python_rule_matches_the_interpreter(executable)
    print("ok: the window's rule agrees with the interpreter")
    test_a_question_of_a_mode_one_file_keeps_its_names(executable)
    print("ok: a question of its own carries the mode of the file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
