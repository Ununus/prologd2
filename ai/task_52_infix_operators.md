# task_52 — инфиксные операторы: `=`, `<`, `>`, `>=`, `=<` (и решение про `=:=`)

**Status:** done (2026-10-02).  Done as planned — five signs, one table in the
parser, `xfx`, the advice table, no new names — with five decisions taken while
doing it (the first one is the only change to the language that no plan
foresaw):

1. **The `1.` number rule changed with it.**  The ported trailing-dot float
   (`1.` = 1.0) *swallowed the sentence terminator*, so `?2 > 1.` could not be
   written at all: the lexer read `1.` as a real and the statement never ended.
   The user decided on the ISO rule — `1.` is the integer `1` and the dot, a
   real needs `1.0` — which is also what SWI and GNU Prolog do.  Documented in
   `help.typ` §3.2 and `prologd-diff.typ`; `#1.#` no longer loads.
2. **The GUI part is highlighting only.**  The user decided to keep `Ctrl+=` for
   `РАВНО(`: the signs take the `OPERATOR` kind in `tokens.py` (the colour was
   already mapped for `mod`/`div`), and `shortcuts.py` is untouched — the
   `= ` insertion of the plan is dropped.
3. **The ISO spellings are refused by the *lexer*, not by the parser.**  The
   table lives in `lexer.cpp` (`kForeignOperators`) because that is where the
   characters are: the hint carries the sign's own position, and the parser then
   sees one bad character instead of three good ones.  That is why the advice is
   the first line of the report instead of the old «Цель не может быть
   переменной», which still follows it (the cascade is the same as for `:`).
4. **`\+` stays a prefix** (task_55) and is not a row of the table, and `is`
   keeps its two hints where they were (`checks.cpp`, `parser.cpp`).
5. **The operand layer is `parseOperand`.**  The tests found that `parseTerm`
   returned `parseArithmetic()` early on `#`, so `r(#1 + 1# = 2)` failed with
   «непарные скобки»: an expression is an *operand* of a comparison, and the
   early return is gone.
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

- [x] **Lexer** (`lexer.hpp`, `lexer.cpp`): one kind per sign (`Equal`, `Less`,
      `Greater`, `LessEqual`, `GreaterEqual`) — the existing style for `,`/`;`,
      and it keeps `infixOperator(TokenKind)` a table lookup.  The longest match
      is the pair branch (`=<`, `>=` before `<`, `>`, and `<-`/`:-` before
      `<`/`:`); `=`, `<` and `>` stopped being «недопустимый символ».  Dead code
      note: `Lexer::reported_error_` is still unused — left alone.
- [x] **A hint for the ISO spellings** — in `lexer.cpp`, see decision 3:
      `kForeignOperators`, longest first (`=:=`, `=\=`, `\==`, `\=`, `==`,
      `@=<`, `@>=`, `@<`, `@>`, `->`, `<=`), each with the Пролог-Д spelling of
      the same thing; `@`-signs share one sentence about the standard order.
- [x] **Parser**: `InfixOperator`/`kInfixOperators` (`=`→`РАВНО`, `<`→`МЕНЬШЕ`,
      `>`→`БОЛЬШЕ`, `=<`→`НЕ(БОЛЬШЕ)`, `>=`→`НЕ(МЕНЬШЕ)`), the layer in
      `parseTerm`/`parseComparison`, the chain reported once at the second sign
      (`skipToTerminator` keeps it from reporting a second time), operands via
      `parseOperand` (decision 5).
- [x] **Formatter**: no code, as expected — `test_formatter.cpp` gained a case
      that the short forms survive formatting (and the idempotency sweep now
      skips `examples/lessons/_old`, which the ported originals need).
- [x] **GUI**:
      * `tokens.py` — the signs are `OPERATOR`, the pair wins over its first
        character; the *number* rule follows the lexer too (`1.` is an integer
        and a dot), which `_scan_number` needed.  `test_tokens.py:120` now pins
        the new shape and a new case walks all five signs.
      * `shortcuts.py` — **dropped by decision** (see 2).
- [x] **Documentation**:
      * `help.typ` §3.2 (the `1.` rule), §3.3 (`X = #выражение#`, why there is no
        `=:=`), §4.7 (`=` and the reversible reading), §5.1 (the four signs and
        the desugaring table, the chain, `=:=`), the two rows of the comparison
        table at the top, and the appendix needs no change (no new names).
      * `prologd-diff.typ`: §9 «`=`, `<`, `>`, `>=`, `=<` — короткая запись
        сравнений» (before/after, the desugaring table, what was *not* added
        with the ISO row for each), three rows of «Краткая таблица», and the
        `is/2` section's «почему не добавить» now says the signs *are* sugar over
        the built-ins while bare `2+3` still needs `#…#`.
      * `technical.typ`: the number paragraph and the grammar
        (`Сравнение ::= Операнд Знак Операнд`) with the priority sentence.
      * `doc/builtins.json`: the `variants` of `РАВНО`, `БОЛЬШЕ`, `МЕНЬШЕ` name
        the sign (arities unchanged, so `test_reference.py` stays green).
      * Lessons: not rewritten — two of them *gained* an example with the short
        form, on the user's choice (2026-10-02): lesson 3 «Арифметика»
        (`?Х = #2 + 3 * 4#.` beside `?РАВНО(Х, #2 + 3 * 4#).`, and `?5 > 3.`,
        `?3 =< 5.` in its comparison section) and lesson 4 «Рекурсия, отсечение и
        отрицание» (`?НЕ(Х = 1).`, `?Х = 1 ; Х = 2.`).  Both files carry their own
        golden output in `%!` lines, so `test_lessons.cpp` needed no edit — it
        checks them as they stand — and the statement counts of
        `test_queries.py` moved (03: 34 → 37, 04: 25 → 27).

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

*Written:* all of the above, seven new Catch2 cases (285/285).  The lexer file
pins the tokens, the longest match and every row of the advice table; the parser
file has four sections (the desugaring, the desugaring wherever a term stands,
`, `/`;` still binding looser, the chain and its exact message);
`test_builtins_control.cpp` pins `=` as the unification predicate and
`test_builtins_arith.cpp` the four signs over the long forms.  `test_engine.cpp`
needed nothing: both spellings reach the same predicate, which is what the
control file asserts.  `test_lessons.cpp` lost the trailing-dot case (the rule it
pinned is gone) and gained one for the new rule, and the formatter's idempotency
sweep skips `examples/lessons/_old`, where the ported originals keep `;`
terminators and `1.`.  `test_tokens.py` gained a case for all five signs and the
new number rule; `test_highlighter.py` pins the colour of `=`.

## What the round found

* **`parseTerm` returned too early on `#`** — decision 5 above.  Found by the new
  parser test (`r(#1 + 1# = 2)`), not by a probe: the probe of `X = #1 + 1#`
  passes on its own because a *bare* expression is not an operand of anything.
* **The chain was reported twice**, the second report about an unclosed bracket.
  `skipToTerminator()` now leaves the dot to the caller, and the pinned message is
  the only diagnostic.
* **`test_queries.py`'s pinned counts were already stale at HEAD.**  task_51
  edited `examples/lessons/lesson_04.pld` (the `ПЕРВОЕ` examples) and the sweep was
  not run again, so that script was red before this round started.  Refreshed with
  `--print` (`24` → `25`, and then `03: 34` → `37`, `04: 25` → `27` for the lesson
  examples of this round); the rule is now in `ai/conventions.md` — the GUI scripts
  are run after any edit under `examples/`.
* **`X < 2+1` reports only «ошибка при разборе предложения».**  The ISO habit gets
  a careful hint in the `is` case (`kInfixIsHint`) but not in the sign case; a
  «выражение помечают `#…#`» hint could be added the same way.  Deliberately left
  out of this round, and the manual says `X < #2+1#` instead.
* **The `1.` rule is a breaking change** for a program that leaned on the
  trailing-dot float — the only one in this task.  It is called out in
  `prologd-diff.typ`'s quick table and in `help.typ` §3.2, and lesson/example
  corpus needed no change (`test_lessons.cpp` and the formatter sweep agree).

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
