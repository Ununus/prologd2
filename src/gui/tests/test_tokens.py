"""Checks of the highlighting tokenizer (Qt-free, no interpreter needed).

    python src/gui/tests/test_tokens.py

Two kinds of check:

* a table of tricky lines with the tokens each must produce — the rules mirror
  `src/prlib/src/lexer.cpp`, so every row is a rule that could drift;
* a sweep over every example program asserting that the tokens cover the line
  exactly once, in order.  A scanner bug shows up as overlapping or skipped
  spans, which is precisely what makes highlighting look "almost right".
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.keywords import Keywords  # noqa: E402
from prologd_gui.tokens import (  # noqa: E402
    ATOM,
    COMMENT,
    CYRILLIC,
    DIRECTIVE,
    EXPRESSION,
    FLOAT,
    INTEGER,
    KEYWORD,
    LATIN,
    MIXED,
    OPERATOR,
    PUNCTUATION,
    QUERY,
    QUOTED_ATOM,
    STRING,
    VARIABLE,
    tokenize,
)

# The reserved names the interpreter reports, trimmed to the ones these tests
# name.  `keywords.py` decodes the real table; here a small one is enough.
TABLE = Keywords(
    [
        {"name": "НАЙТИВСЁ", "kind": "predicate", "arities": [3]},
        {"name": "ВЫВОД", "kind": "predicate", "arities": [], "variadic": True},
        {"name": "ВЫП", "kind": "predicate", "arities": [1]},
        {"name": "ПС", "kind": "predicate", "arities": [0]},
        {"name": "ИМПОРТ", "kind": "directive", "arities": []},
        {"name": "mod", "kind": "operator", "arities": []},
        {"name": "div", "kind": "operator", "arities": []},
    ]
)


def kinds(line: str, table: Keywords | None = TABLE) -> list[tuple[str, str]]:
    return [(token.kind, token.text) for token in tokenize(line, table)]


def alphabets(line: str) -> list[tuple[str, str]]:
    return [
        (token.text, token.alphabet)
        for token in tokenize(line, TABLE)
        if token.alphabet
    ]


def test_comments_and_clause_terminators() -> None:
    assert kinds("факт(1). % привет") == [
        (ATOM, "факт"),
        (PUNCTUATION, "("),
        (INTEGER, "1"),
        (PUNCTUATION, ")"),
        (PUNCTUATION, "."),
        (COMMENT, "% привет"),
    ]
    # A comment swallows the rest of the line whole, quotes included.
    assert kinds("цель(X). % не '\"строка")[-1] == (COMMENT, "% не '\"строка")
    print("ok: comments and terminators")


def test_strings_and_quoted_atoms() -> None:
    assert kinds('ВЫВОД("а\\"б")') == [
        (KEYWORD, "ВЫВОД"),
        (PUNCTUATION, "("),
        (STRING, '"а\\"б"'),
        (PUNCTUATION, ")"),
    ]
    # An unterminated string is coloured to the end of its own line: the lexer
    # rejects it, so there is no state to carry into the next line.
    assert kinds('ВЫВОД("аб') == [(KEYWORD, "ВЫВОД"), (PUNCTUATION, "("), (STRING, '"аб')]
    # A doubled quote is the escape inside a quoted atom.
    assert kinds("'Иван''ы'") == [(QUOTED_ATOM, "'Иван''ы'")]
    print("ok: strings and quoted atoms")


def test_numbers() -> None:
    assert kinds("12") == [(INTEGER, "12")]
    assert kinds("12.5") == [(FLOAT, "12.5")]
    assert kinds("1e3") == [(FLOAT, "1e3")]
    assert kinds("2.5E-2") == [(FLOAT, "2.5E-2")]
    # `1.` is a float only when the dot is not the clause terminator.
    assert kinds("факт(1).") == [
        (ATOM, "факт"),
        (PUNCTUATION, "("),
        (INTEGER, "1"),
        (PUNCTUATION, ")"),
        (PUNCTUATION, "."),
    ]
    assert kinds("а=1. ") == [(ATOM, "а"), (PUNCTUATION, "="), (FLOAT, "1.")]
    print("ok: numbers, including the trailing-dot float")


def test_reserved_names_variables_and_atoms() -> None:
    assert kinds("НАЙТИВСЁ(X,цель(X),L)") == [
        (KEYWORD, "НАЙТИВСЁ"),
        (PUNCTUATION, "("),
        (VARIABLE, "X"),
        (PUNCTUATION, ","),
        (ATOM, "цель"),
        (PUNCTUATION, "("),
        (VARIABLE, "X"),
        (PUNCTUATION, ")"),
        (PUNCTUATION, ","),
        (VARIABLE, "L"),
        (PUNCTUATION, ")"),
    ]
    # Reserved matches exactly: `Вып` is just a name that starts upper-case.
    assert kinds("Вып(X)") == [
        (VARIABLE, "Вып"),
        (PUNCTUATION, "("),
        (VARIABLE, "X"),
        (PUNCTUATION, ")"),
    ]
    assert kinds("_") == [(VARIABLE, "_")]
    assert kinds("_Хвост")[0][0] == VARIABLE
    # The three kinds of reserved word are told apart.
    assert kinds("mod") == [(OPERATOR, "mod")]
    assert kinds("div") == [(OPERATOR, "div")]
    assert kinds(":- ИМПОРТ(\"a.pld\").") == [
        (PUNCTUATION, ":-"),
        (DIRECTIVE, "ИМПОРТ"),
        (PUNCTUATION, "("),
        (STRING, '"a.pld"'),
        (PUNCTUATION, ")"),
        (PUNCTUATION, "."),
    ]
    # Without a table (an interpreter older than protocol 2) nothing is reserved,
    # so a built-in name is just a variable — the documented fallback.
    assert kinds("НАЙТИВСЁ", None) == [(VARIABLE, "НАЙТИВСЁ")]
    print("ok: reserved names, variables and atoms")


def test_expression_query_and_arrows() -> None:
    assert kinds("факториал(#Н-1#,Х)") == [
        (ATOM, "факториал"),
        (PUNCTUATION, "("),
        (EXPRESSION, "#"),
        (VARIABLE, "Н"),
        (PUNCTUATION, "-"),
        (INTEGER, "1"),
        (EXPRESSION, "#"),
        (PUNCTUATION, ","),
        (VARIABLE, "Х"),
        (PUNCTUATION, ")"),
    ]
    assert kinds("?факт(X).") == [
        (QUERY, "?"),
        (ATOM, "факт"),
        (PUNCTUATION, "("),
        (VARIABLE, "X"),
        (PUNCTUATION, ")"),
        (PUNCTUATION, "."),
    ]
    assert kinds("A<-B") == [(VARIABLE, "A"), (PUNCTUATION, "<-"), (VARIABLE, "B")]
    assert kinds("A:-B") == [(VARIABLE, "A"), (PUNCTUATION, ":-"), (VARIABLE, "B")]
    print("ok: #…#, ? and the two rule arrows")


def test_alphabet_of_identifiers() -> None:
    assert alphabets("член(X)") == [("член", CYRILLIC), ("X", LATIN)]
    assert alphabets("member(X)") == [("member", LATIN), ("X", LATIN)]
    assert alphabets("Член") == [("Член", CYRILLIC)]
    assert alphabets("Ф_x") == [("Ф_x", MIXED)]
    assert alphabets("X1") == [("X1", LATIN)]
    # A number or a quoted atom carries no alphabet; only names are coloured by
    # script, because that is what a reader confuses at a glance.
    assert alphabets("'Иван' 12") == []
    print("ok: latin, cyrillic and mixed identifiers")


def test_tokens_cover_every_example_line() -> None:
    """Every non-whitespace character is inside exactly one token.

    A scanner bug shows up as a gap or an overlap, which is precisely what makes
    highlighting look "almost right".
    """
    root = pathlib.Path(__file__).resolve().parents[3] / "examples"
    files = sorted(root.rglob("*.pld"))
    assert files, f"no example programs under {root}"
    checked = 0
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.rstrip("\r")
            where = f"{path.name}:{number}"
            previous_end = 0
            covered = [False] * len(line)
            for token in tokenize(line, TABLE):
                assert token.start >= previous_end, f"{where}: overlap at {token!r}"
                assert line[token.start : token.end] == token.text, f"{where}: {token!r}"
                for index in range(token.start, token.end):
                    covered[index] = True
                previous_end = token.end
            for index, character in enumerate(line):
                if not covered[index]:
                    assert character.isspace(), (
                        f"{where}: {character!r} at {index} is in no token"
                    )
            checked += 1
    print(f"ok: {checked} lines of {len(files)} example programs are covered exactly once")


def main() -> int:
    test_comments_and_clause_terminators()
    test_strings_and_quoted_atoms()
    test_numbers()
    test_reserved_names_variables_and_atoms()
    test_expression_query_and_arrows()
    test_alphabet_of_identifiers()
    test_tokens_cover_every_example_line()
    print("all tokenizer checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
