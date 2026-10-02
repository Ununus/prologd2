# task_52 — инфиксные операторы: `=`, `<`, `>`, `>=`, `=<` (и решение про `=:=`)

**Status:** not started — the plan is written down (2026-10-02).  The user asked
for «он же + ISO-сравнения» (the `=` sugar *and* the comparison signs), the
non-associative rule («xfx, цепочка — синтаксическая ошибка») and the `=` insert
key in `src/gui/prologd_gui/shortcuts.py`; on the same day `=:=` was **decided
against** — `#…#` already evaluates, and the manual says so (see below)
**Depends on:** task_41 (the `,`/`;` precedence), task_31 (the shortcut table),
task_37/task_39 (`doc/builtins.json` and the alias table)
**Milestone:** post-M10

## Goal

Unification and comparison get the spellings a reader of ordinary Prolog expects,
as *sugar* over the predicates that already exist:

```prolog
?X = 1, Y = X.                 % ?РАВНО(X, 1), РАВНО(Y, X)
?X = #2 + 3 * 4#.              % ?РАВНО(X, #2 + 3 * 4#)
?2 > 1.   ?2 >= 2.   ?1 < 2.   ?2 =< 2.
дед(X, Y) :- родитель(X, Z), Y = Z.
```

`РАВНО`, `БОЛЬШЕ` and `МЕНЬШЕ` stay — that is the whole point: `=` is a second
spelling, not a replacement (47 calls of `РАВНО(` live in `examples/` and
`examples/lessons/`), and the Russian names stay the primary spelling in the
manual.

## Decisions taken (2026-10-02)

1. **Sugar, not new names.**  `=`, `<`, `>`, `>=`, `=<` desugar in the parser to
   `РАВНО/2`, `МЕНЬШЕ/2`, `БОЛЬШЕ/2`, `НЕ(МЕНЬШЕ(...))`, `НЕ(БОЛЬШЕ(...))`.  So
   the solver, the checker, `builtins.cpp`, `--list-keywords`, the protocol and
   `doc/builtins.json`'s arity data are untouched: the checker sees the same
   built-ins it sees today.
2. **Non-associative (`xfx`).**  `X = Y = Z` is a *syntax error* with a message of
   its own, not a silently nested `РАВНО(РАВНО(X, Y), Z)` (which would bind `Z` to
   the term `РАВНО(X, Y)` — nonsense no reader expects).
3. **One table, one priority level.**  ISO gives every comparison priority 700,
   tighter than `,` (1000) and `;` (1100) and looser than `#…#`.  The operators
   live in **one table** in the parser (token → functor/desugaring + priority), so
   the next operator is a row and not another `while (match(...))`.
4. **They work in any goal or argument position**, because the new layer sits in
   `parseTerm` — the place where `,`-groups for goal arguments are already built:
   `НЕ(X = 1)`, `НАЙТИВСЕ(X, (X = 1), L)`, `ВЫП((X = 1))`, `[X = Y]` (as data) all
   parse.
5. **A key in the GUI.**  The `= ` insertion joins the shortcut table next to
   `:-.` and `РАВНО(,)`.
6. **`\+` is not part of this table.**  The negation prefix was added on its own
   (task_55, 2026-10-02): it is a *prefix* at the term level in `parseTerm`, it
   desugars to `НЕ/1` with no two-argument call, and it needs no row here.
   Whoever writes this table should leave `\+` where it is.

## Semantics (verified 2026-10-02 with the built interpreter)

| spelling | sugar | note |
|---|---|---|
| `A = B` | `РАВНО(A, B)` | reversible, so `X = 1` binds; a `#…#` operand is evaluated: `?РАВНО(#1 + 1#, 2).` → ДА |
| `A < B` | `МЕНЬШЕ(A, B)` | numbers **and texts**, lexicographically: `?МЕНЬШЕ("а", "б").` → ДА — wider than ISO's arithmetic-only `<` |
| `A > B` | `БОЛЬШЕ(A, B)` | the same, mirrored |
| `A >= B` | `НЕ(МЕНЬШЕ(A, B))` | `?НЕ(МЕНЬШЕ(2, 3)).` → НЕТ |
| `A =< B` | `НЕ(БОЛЬШЕ(A, B))` | `?НЕ(БОЛЬШЕ(2, 3)).` → ДА |

A free operand is a runtime error, not a failure — `?НЕ(БОЛЬШЕ(X, 3)).` ends the
query with `БОЛЬШЕ: Недопустимый тип аргументов` and exit code 3, which is exactly
ISO's instantiation error for a comparison, and `НЕ` does not swallow it.

## Decision — `=:=` is not added (2026-10-02)

Verified with the built interpreter: `?РАВНО(#1 + 1#, 2).` → ДА,
`?РАВНО(#1 + 1#, #2#).` → ДА, `?РАВНО(6, 6.0).` → ДА.  So «сравнить два
вычисленных выражения» is **already** `=` with a `#…#` on either side — `#1 + 1# = 2`
is the Пролог-Д spelling of ISO's `1 + 1 =:= 2`.  The ISO form itself is different
in one way only (it never binds and it errors on a free operand), and that would
be a **new predicate** with its own Russian name, alias, record and tests — not
worth it when the same thing can be said with `#…#`.

The user decided on 2026-10-02: **`=:=` is not introduced, the manual explains it.**
What that means for this task:

* `=:=` goes into the hint table with a message that names the replacement —
  «`=:=` — в Пролог-Д вычисляет `#…#`: `#1 + 1# = 2`» — the same shape as the
  retired-spelling advice (`retiredNameMessage` in `checks.cpp`).
* `doc/help.typ` §4.7 gains the sentence: an operand written as `#…#` is evaluated
  by `=` itself, so the dialect has no separate arithmetic comparison;
  `doc/prologd-diff.typ` says the same beside its `is/2` note («Оператора `is/2`
  не было»).
* Nothing else changes: five operators, one table, no new predicate.

## Deliverables

- [ ] **Lexer** (`lexer.hpp`, `lexer.cpp:300-360`): tokens for the operators, the
      longest match first — `=<`, `>=`, `=:=` before `=`, and `<-`/`:-` before `<`/`:`
      (the pair handling already exists).  `=` and the comparison signs stop being
      «недопустимый символ» (`ErrorCode::InvalidCharacter`, `diagnostics.cpp:14`).
      Decide and write down the shape: one `TokenKind::Operator` carrying the text
      (tidiest with a table) or a kind per sign (the existing style for `,`/`;`).
- [ ] **A hint for the ISO spellings the dialect does not have** (a table of text →
      advice, like `retiredNameMessage` in `checks.cpp`): `==`, `\==`, `\=`, `=:=`,
      `=\=`, `@<`, `@>`, `@=<`, `@>=`, `->`, `\+`, `is` — «такого оператора в
      Пролог-Д нет; для унификации — `=`» and the like.  The `default:` branch keeps
      «недопустимый символ» for anything else.
- [ ] **Parser**: the operator table and one layer between `parsePrimary`/`#…#` and
      everything above, in `parseTerm`; a chain (`X = Y = Z`) reported at the second
      operator with its own message; the desugaring in one function so a row of the
      table is data.
- [ ] **Formatter**: no code expected (goal boundaries are still `,`/`;` by token
      kind, `formatter.cpp:346,617,787`) — pin it with a test that a program with the
      short forms formats and round-trips.
- [ ] **GUI**:
      * `tokens.py` — classify the operator signs as `OPERATOR`, so the «Подсветка»
        role colours them alongside `mod`/`div` (`theme.py:61-68` maps
        `KEYWORD`/`DIRECTIVE`/`OPERATOR` to the keyword colour).  This changes
        `src/gui/tests/test_tokens.py:120`, which pins `=` as `PUNCTUATION` today.
      * `shortcuts.py` — the `= ` insertion next to `:-.` and `РАВНО(,)`, plus its
        row in «Шпаргалка по вставкам»; check it does not fight the keypad zoom.
- [ ] **Documentation**:
      * `doc/help.typ` §4.7 (`=` and the reversible reading), §5.1 (`<`, `>`, `>=`,
        `=<` and what each desugars to), and one sentence that `#…#` is the
        «вычисли» marker (that is why there is no `=:=`).
      * The comparison table at the top of `doc/help.typ` — the rows «Унификация»
        and «Сравнение чисел» now read `РАВНО(X, Y)` / `X = Y` and
        `БОЛЬШЕ` / `X > Y`; a note that `<`/`>` also compare texts.
      * `doc/prologd-diff.typ` (a short subsection: the new spellings and what they
        desugar to), `doc/technical.typ` (the grammar paragraph), and the
        `variants` of `РАВНО`, `БОЛЬШЕ`, `МЕНЬШЕ` in `doc/builtins.json` (arities
        do not change, so `src/gui/tests/test_reference.py` stays green).
      * Lessons are **not** rewritten; optionally one gets a `%?` example with the
        short form.

## Tests

- `test_lexer.cpp`: the new tokens; longest match (`=<`, `>=`, `<-`, `:-`); the
  hints for `==`/`=:=`/`is`; `X = Y` is no longer a lexical error.
- `test_parser.cpp`: desugaring (`X = 1` → `РАВНО/2`); priority against `,`, `;`
  and `#…#`; the chain is an error with the pinned message; operators inside
  arguments (`НЕ(X = 1)`, `НАЙТИВСЕ(X, (X = 1), L)`, `[X = Y]`).
- `test_builtins_control.cpp` / `test_engine.cpp`: `?X = 1, Y = X.` → both bound;
  `?1 = 2.` → НЕТ; the sugar and the long form reach the same predicate.
- `test_builtins_arith.cpp`: `?2 > 1.` ДА, `?2 >= 2.` ДА, `?2 =< 1.` НЕТ,
  `?X > 1.` → exit 3 with `БОЛЬШЕ: Недопустимый тип аргументов`.
- `test_formatter.cpp`: `--format` of a program with the short forms, round-trip.
- GUI: `test_tokens.py` (`=` → `OPERATOR`), `test_shortcuts.py`,
  `test_highlighter.py`, `test_queries.py` (a query with `=` runs).

## What must not change

- `РАВНО`, `БОЛЬШЕ`, `МЕНЬШЕ`: names, arities, semantics.  No new reserved names,
  so `--list-keywords`, the protocol's `keywords` event and the appendix table of
  `help.typ` are unchanged.
- `builtins.cpp`, `checks.cpp`, `engine.cpp`: untouched — the desugaring happens
  before any of them sees the goal.
- Existing programs: `=` is a lexical error today, and in `examples/` it appears
  only inside comments (`====` banners, `Н1 + 1 = Н` in prose) and in `%!` output
  lines, so nothing changes meaning.

## Verification

1. `cmake --build build/windows-msvc --config Release` and
   `ctest --test-dir build/windows-msvc -C Release`.
2. By hand with `build\windows-msvc\src\cli\Release\prologd.exe`:
   `?X = 1, Y = X.`; `?X = #1 + 1#.`; `?2 >= 2.`; `?2 =< 2.`; `?X >= 1.` (error 3);
   `?X = Y = 1.` (parse error about the chain); `?НЕ(X = 1).` → НЕТ;
   `?НАЙТИВСЕ(X, (X = 1), L).`
3. `--format` round-trip on a file that uses the short forms.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`), then
   `cmake --build build/windows-msvc --config Release --target docs` and a look at
   the pages that carry §4.7 and the comparison table.

## Notes

- `>=`/`=<` become `НЕ(МЕНЬШЕ/БОЛЬШЕ)`: it works, it errors exactly once and it
  errors with the right predicate name, but the trace and the checker see the
  desugared goal.  If a trace that says `A >= B` is wanted later, *that* is the
  moment to add two real built-ins (`НЕ_БОЛЬШЕ`, `НЕ_МЕНЬШЕ`) — a separate change
  with its own names and rows.
- The chain message must be its own report at the second operator; the ordinary
  «не закрыта скобка» diagnostics must not be reworded for it.
- Every later operator (`->`, `\+`, …) is a row in the same table; the priority
  lives there too, which is why the table is a deliverable and not an accident.
