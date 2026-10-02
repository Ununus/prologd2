# task_55 — `\+` как вторая запись `НЕ` и подсказки вместо `is/2`

**Status:** done (2026-10-02).  The user asked to settle the two items the
comparison table still showed as divergences from ISO: «Осталось 2 существенных
пункта, где Пролог-Д расходится с другими: `is` и `\+ Ц`.»  Decision the same
day: `\+` is added, `is` is **not** — and both spellings of `is` get a message
that names the Пролог-Д way of writing the same thing.
**Depends on:** task_41 (the `,`/`;` precedence), task_44 (the wording of the
retired-name messages), task_52 (the infix operators — which stay the home of
`=`/`<`/`>`; `\+` is **not** theirs, see below)
**Milestone:** post-M10

## `\+` — a second spelling of `НЕ`, not a new name

- **Lexer** (`lexer.hpp`, `lexer.cpp`): one token, `TokenKind::NotGoal`, for the
  two characters `\+`.  A lone `\` stays the character the language does not know
  (the `default` branch reports it exactly as before) — nothing else changes.
- **Parser** (`parseTerm`): a prefix at the **term** level, so it reaches every
  place a goal is written — a clause body, a query, a directive, the argument of
  `НЕ`, and the goal arguments of `ВЫП`/`НАЙТИВСЕ` — and desugars to the compound
  `НЕ/1`.  Precedence is ISO's: `,` and `;` bind looser, so `\+ A, B` is
  `(\+ A), B`, `\+ (A, B)` negates the whole conjunction, and `\+ \+ Ц` is the
  double negation.
- **Not in task_52's operator table.**  That table is for *infix* operators that
  desugar to a two-argument call; `\+` is a prefix and needs no row.  Whoever
  does task_52 should leave `\+` alone.
- **Nothing else moves.**  `НЕ` stays the primary name (Russian, in the manual
  and in the tests); the solver, the checker, `builtins.cpp`,
  `--list-keywords`, `doc/builtins.json` and the protocol are untouched — `\+` is
  a spelling, and the checker sees the same `НЕ/1` call it saw before
  (`walkGoal` already opens `НЕ/1`).
- **Formatter**: it works on tokens, so `\+` is copied as written and never
  broken in two; a test pins that the author's space after `\+` survives in every
  mode.
- **GUI** (`tokens.py`): `\+` lexes as one punctuation token, like `:-`, so the
  editor never shows a stray backslash.

## `is/2` — a hint, not an operator

Two messages, both naming the same replacement:

| written | what happens |
|---|---|
| `?is(X, #2+3#).` | warning `не найдено: is/2; «is» — не предикат: в Пролог-Д это «РАВНО(X, #2+3#)»`.  The name is **not** reserved: a program may define its own `is/2` |
| `?X is 2+3.` | parse error `«is» — не оператор: выражение помечают «#…#», например «РАВНО(X, #2+3#)»` — without it the reader is told only «Цель не может быть переменной» |

Home: `kForeignSpellings` in `checks.cpp` (appended to the unknown-predicate
warning, after the spelling suggestion) and `kInfixIsHint` in `parser.cpp` (a
variable goal followed by the atom `is`).

**Why not the operator itself.**  `#…#` is not decoration but the *marker* of an
expression: it evaluates wherever a number is needed, and unification is
reversible — verified `?РАВНО(X, #2+3#).` → `X=5`, `?РАВНО(5, #2+3#).` → `ДА`,
`?РАВНО(X, #Y#).` → «Нечисловой операнд арифметического выражения» (ISO's
instantiation error, in the same place).  A real `is` would add a second
arithmetic — bare `2+3` in goals — which would then have to be given to the
comparisons as well (`X < 2+1`, `=:=`), and those were already rejected
(`task_52`).

## Verified with the built interpreter (2026-10-02)

| written | answer |
|---|---|
| `?\+ РАВНО(1, 2).` | ДА |
| `?\+ РАВНО(1, 1).` | НЕТ |
| `?\+ \+ ЛОЖЬ.` | НЕТ (double negation is negation) |
| `?\+ (ЛОЖЬ ; ЛОЖЬ).` | ДА |
| `?\+ (ЛОЖЬ ; РАВНО(A, 1)), ПЕР(A).` | НЕТ — the whole disjunction is negated |
| `?\+ (ЛОЖЬ, РАВНО(B, 1)), ПЕР(B).` | `B=_1` — the binding made inside `\+` is undone |
| `?НАЙТИВСЕ(1, \+ РАВНО(1, 2), L).` | `L=[1]` — `\+` parses as a goal argument |
| `?НАЙТИВСЕ(1, \+ РАВНО(1, 1), L).` | `L=[]` |
| `?is(X, #2+3#).` | НЕТ + the warning above (exit 0) |
| `?X is 2+3.` | parse error above (exit 2) |

`--format` keeps `\+ часть(Х)` whole; a glued `\+часть(Х)` stays glued, because
the formatter changes line breaks and separators, not the space between two
ordinary tokens.

## Checks

- `prlib_tests`: **260 cases, 3901 assertions, all green** — new cases in
  `test_lexer.cpp` (`\+` is one token; a lone `\` is still an error),
  `test_parser.cpp` (`\+` desugars, `,` binds looser, `\+ (A, B)`, `\+ \+ q`, and
  the `is` message), `test_builtins_control.cpp` (`\+` is `НЕ`, including the
  undone binding), `test_formatter.cpp` (`\+` is never split) and
  `test_diagnostics.cpp` (the `is/2` warning text).
- GUI: `test_tokens.py` (the new pair plus the 3140-line sweep),
  `test_highlighter.py`, `test_reference.py` — green; `--list-keywords` is
  unchanged, so the reference table and `doc/builtins.json` need no new record.
- Docs: `doc/help.typ` §3.3 (the `is` note), §4.4 (heading and the `\+` spelling
  with its precedence), the comparison table («Арифметика» now names `РАВНО`, the
  «Отрицание» cell names both spellings), the appendix (`\+` is not a name);
  `doc/prologd-diff.typ` §14 (two rows), §19 and §20.
