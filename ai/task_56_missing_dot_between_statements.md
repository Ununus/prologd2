# task_56 — a missing dot is visible in the middle of a file too

Status: done (2026-10-02).

## Why

The user wrote two lines

```prolog
студент(вова, корчагин)
студент(данил, ахмеров).
```

and got

```
pld:2:1: error: ошибка при разборе предложения
```

— a message that says nothing, at the position of the *start of the second* statement,
although the missing dot is at the end of the first.  The useful wording ("a statement
must end with a dot") was printed only when the dot was missing after the last statement
in the file, because that is the only place where the parser reaches the end of the
input.

The cause: a newline ends nothing in this dialect (as before), so the lexer glues the two
statements into one.  Parsing the first term succeeds and the parser stumbles on the name
of the second (`parseClause`, the last branch of `if (!check(TokenKind::Dot))` → the
generic `InvalidSentence` with no text).

## The fix

A new helper in the anonymous namespace of `parser.cpp`:

```cpp
bool beginsStatement(TokenKind kind);   // Identifier, Variable, Integer, Float,
                                        // String, QuotedAtom, Hash, Question,
                                        // NotGoal, LParen, LBracket
```

When a statement is *complete* (the head, and after `:-`/`<-` the body, are parsed) and
the next token is from that list, a new statement begins and the dot is what is missing:
`reportMissingDot()` prints "предложение должно заканчиваться точкой" with the position of
`previous().location` — at the end of *its own* statement.  The branch is in `parseClause`
and in `parseQueryOrDirective` (the latter through
`check(EndOfFile) || beginsStatement(peek().kind)`).

The list is deliberately narrow: `,`, `)`, `]`, the operator signs and `!` keep their
earlier, precise messages ("непарные скобки", "неверное использование !", …), because a
new statement cannot begin with them.

## Runs (the built interpreter)

| program | before | after |
|---|---|---|
| `студент(вова, корчагин)` + `студент(данил, ахмеров).` | `2:1: ошибка при разборе предложения` | `1:42: предложение должно заканчиваться точкой` |
| `a(X) :- b(X)` + `a(2).` | `2:1: ошибка при разборе предложения` | `1:12: предложение должно заканчиваться точкой` |
| `?- a(1)` + `b(2).` | `2:1: ошибка при разборе предложения` | `1:7: предложение должно заканчиваться точкой` |
| `a(1) b(2).` (one line) | `1:4: ошибка при разборе предложения` | `1:4: предложение должно заканчиваться точкой` |
| `студент(вова, корчагин).` + `студент(данил, ахмеров).` | — | no diagnostics |
| `a(1), b(2).` | `1:5: ошибка при разборе предложения` | unchanged (`,` does not begin a statement) |
| `p :- f(a "b").` | "непарные скобки", then the generic one | unchanged (the precise diagnostic comes first) |

Columns are counted in **bytes** (as everywhere in this dialect, see the test "an unclosed
bracket is reported at the opening bracket"): `студент(вова, корчагин)` is 41 bytes, so
`)` is in column 42.

## What was done

* `parser.cpp`: `beginsStatement` plus the branch in `parseClause` and
  `parseQueryOrDirective`.
* `test_parser.cpp`: the case "a statement that lost its dot is told where the dot
  belongs" — four sections (a fact before a fact, a rule before a fact, a query before a
  fact, "the dot is everywhere") and a guard section for the generic wording.
* `test_diagnostics.cpp`: the same case through the module loader (the `1:42` position).

Checks: `prlib_tests` and `ctest` — **276/276** (was 274).
