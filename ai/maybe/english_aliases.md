# Parked idea: English aliases for the Russian built-ins

**Status:** not scheduled.  Written down on 2026-09-30 so a task file can be cut
from it when the user decides.
**Related:** `ai/task_36_gui_query_markers.md`, `ai/task_37_gui_builtin_reference.md`
(both are independent of this idea, but a decision here changes the reference
data of task 37).

## What was asked

Add the standard English name of every Russian built-in as an alias
(`НАЙТИВСЁ` → `findall`, and so on), so that the language can be learned in a
standardised spelling as well.

## The user's decision on the one real risk

The mechanism's only serious cost is that a built-in *shadows* a user clause of
the same name: `Solver::unifyGoal` consults `findBuiltin` **before** the
database (`src/prlib/src/engine.cpp:282`), so a program that defines its own
`length/2` or `member/2` would silently stop calling it.

**Accepted**: the user's answer on 2026-09-30 is that backward compatibility is
not a blocker — the variable syntax was already changed once, the program is
used by a small circle, and the lessons (`examples/lessons`, 204 queries in
13 files) are the corpus that actually matters.  So the alias list may use names
that a user program could plausibly define, and no fallback machinery is needed.

That removes option (b) (alias resolves only when the program has no clause of
that name) and option (c) (`--english` flag) from consideration.  What remains is
a plain table of aliases.

## Why the mechanism itself is cheap

* Registration is one call site: `add("НАЙТИВСЁ", 3, builtinFindAll)` in
  `src/prlib/src/builtins.cpp:248-321` (60 registrations, ~57 names).
* The *reserved* set is a second, hand-written list in
  `src/prlib/src/lexer.cpp:11-35`.  It is needed for the Russian names because
  `НАЙТИВСЁ` as a bare word would otherwise be a variable; for lowercase English
  names reserved-ness is only about highlighting and completion.  Tests already
  enforce the two lists agree: `src/tests/test_keywords.cpp` — *reserved names
  match the lexer's set*, *every registered built-in is reserved*, *reserved
  names are classified*.
* Three names live outside the dispatch table and need their own place:
  `ВЫП/1` (`kEngineCallables` in `src/prlib/src/keywords.cpp`), `ИМПОРТ`
  (`kReservedDirectives` there **and** `kImportName` in
  `src/prlib/src/parser.cpp:10`), `mod`/`div` (`kReservedOperators`, already
  English).
* The GUI needs **no** change: highlighting, completion and the cheat-sheet read
  the reserved names from the `ready` event (`prologd/src/gui/prologd_gui/keywords.py`;
  the same list is what `prologd --list-keywords` prints), so a registered alias
  appears everywhere by itself.

## What an alias cannot fix

An English name does not turn this dialect into ISO Prolog.  Arithmetic and
comparison are *callable predicates with free variables* (`СЛОЖЕНИЕ(A, B, C)`,
`БОЛЬШЕ(A, B)`), not operators, so `is/2`, `<`, `>` and `=:=` stay out of reach
until the grammar grows infix arithmetic (a separate, much larger task; it is
already listed as an optional item in `ai/status.md`).  `findall` is the one
name where the alias is exactly ISO — `НАЙТИВСЁ(Шаблон, Цель, Список)` already
has the ISO argument order (`doc/help.typ` §12).

## Draft mapping

Lowercase with underscores, which is how the language already spells its two
English conversion built-ins (`int`, `float`) and the two operators (`mod`,
`div`).  Everything below is a proposal, not a decision.

| Russian | Arities | Proposed alias | Note |
|---------|---------|----------------|------|
| `ЛОЖЬ` | 0 | `fail` | |
| `ТРАССА` | 0 | `trace` | |
| `НЕТ_ТРАССЫ` | 0 | `no_trace` | |
| `ТИХО` | 0 | `quiet` | |
| `ВЕРСИЯ` | 0 | `version` | |
| `НЕ` | 1 | `not` | |
| `ИЛИ` | 2 | `or` | |
| `РАВНО` | 2 | `equal` | **not** `=`, not `==`: it compares, it does not unify |
| `ПС` | 0 | `nl` | |
| `ЖДИ` | 1 | `wait` | |
| `ВЫП` | 1 | `call` | engine-level, not in the dispatch table |
| `ПЕР` | 1 | `var` | ISO `var/1` |
| `ЦЕЛ` | 1 | `integer` | ISO `integer/1` — see the `float` clash below |
| `ВЕЩ` | 1 | `float` | **clash**: `float/1` is already the conversion |
| `СИМВ` | 1 | `is_text` | true for an atom *and* for a string, unlike ISO `atom/1` |
| `СПИСОК` | 1 | `is_list` | ISO `is_list/1` |
| `НАЙТИВСЁ` | 3 | `findall` | argument order already ISO |
| `БОЛЬШЕ` | 2 | `greater` | ISO spells it `>` (operator, other task) |
| `МЕНЬШЕ` | 2 | `less` | ISO spells it `<` |
| `СЛОЖЕНИЕ` | 3 | `plus` | `plus/3` exists in several systems |
| `УМНОЖЕНИЕ` | 3, 4 | `mul` | |
| `ABS` | 2 | `abs` | already English, uppercase |
| `SQRT` | 2 | `sqrt` | already English, uppercase |
| `SIN`, `COS`, `TAN`, `EXP` | 2 | lowercase forms | already English, uppercase |
| `int` | 1 | `to_int` | **rename** if `integer/1` is to mean the test |
| `float` | 1 | `to_float` | **rename** if `float/1` is to mean the test |
| `СЛУЧ` | 1, 3 | `random` | |
| `ЦЕЛВЕЩ` | 2 | `to_float`/`num_to_float` | int ↔ float, either direction |
| `СТРЦЕЛ` | 2 | `str_to_int` | string ↔ int |
| `СТРВЕЩ` | 2 | `str_to_float` | string ↔ float |
| `СТРСПИС` | 2 | `str_to_list` | string ↔ list of code points |
| `БУКВА` | 2 | `is_letter` | |
| `ЦИФРА` | 2 | `is_digit` | |
| `СЦЕП` | 3 | `concat` | ISO `atom_concat/3` |
| `КОПИЯ` | 4 | `substring` | **not** `copy`: five argument modes, §7.4 |
| `ДЛИНА` | 2 | `strlen` | **not** `length`: it is a *string* length, `length/2` is a list |
| `ВЫВОД` | 1+ | `write` | variadic |
| `ВВКОД` | 1 | `put_code` | writes one code point |
| `ВВОДЦЕЛ` | 1, 2 | `read_int` | |
| `ВВОДВЕЩ` | 1, 2 | `read_float` | |
| `ВВОДСИМВ` | 1, 2 | `read_char` | |
| `ВВОДСТР` | 1, 2 | `read_string` | |
| `ЧТЕНИЕ_ИЗ` | 1 | `see` | ISO `see/1` |
| `ЗАПИСЬ_В` | 1 | `tell` | ISO `tell/1` |
| `СКОЛЬКО` | 2 | `clause_count` | no ISO counterpart |
| `ПРЕДЛ` | 4 | `clause_at` | ISO `clause/2` is by head, this one by number |
| `ТЕРМ` | 2 | `univ` | ISO `=..` for the term ↔ list conversion |
| `ДОБ` | 3 | `assert` | ISO `assertz/1`, here with a position |
| `УДАЛЕНИЕ` | 2 | `retract` | |
| `ТОЧКА` | 3 | `point` | graphics |
| `ЛИНИЯ` | 5 | `line` | graphics |
| `ОКРУЖНОСТЬ` | 4 | `circle` | graphics |
| `ЗАКРАСКА` | 3 | `fill` | graphics |
| `ИМПОРТ` | directive | `import` | lexer + keywords + parser |

The one real tangle is `int`/`float` against `ЦЕЛ`/`ВЕЩ`:

* **Option A (no rename)**: keep `int/1` and `float/1` as conversions, alias the
  tests `is_int`/`is_float`.  Nothing breaks; the English surface is not ISO.
* **Option B (ISO-aligned)**: make `integer/1` and `float/1` the *tests* (as in
  every ISO system) and rename the conversions to `to_int`/`to_float`, keeping
  `int`/`float` as deprecated aliases of the conversions.  One name changes
  meaning, which is the only place where this plan can silently break a program
  that already uses English names.

Recommendation when it is scheduled: **Option B**, because the point of the work
is to make the English surface look like Prolog.

## What the change touches

* `src/prlib/src/builtins.cpp` — the alias registrations (or an `addAliases`
  helper taking one Russian name and a list of spellings).
* `src/prlib/src/lexer.cpp` — the reserved set.
* `src/prlib/src/keywords.cpp` and `src/prlib/src/parser.cpp` — `call`, `import`.
* `doc/help.typ` — a correspondence table, and a correction of §1.2 / §2 where
  the text says the Russian names *are* the language.
* `doc/prologd-diff.typ` — this is an addition, not a divergence from the
  original, but it belongs in the list.
* `--list-keywords` and the GUI completion simply grow (57 → ~110 names); no GUI
  edit, but `src/gui/tests/test_keywords.py` has expectations to extend.
* The lessons stay Russian.  Nothing in `examples/` has to change, and
  `src/tests/test_lessons.cpp` is untouched — but a *tutorial* place for the
  correspondence table might be worth adding to the course later.

## Tests

* A table-driven equivalence test: a small program written with the Russian name
  and the same program with the English one must produce the same output.  One
  row per alias, so a missing registration fails a named test instead of passing
  unnoticed.
* `test_keywords.cpp` already fails if a registration is missing from the lexer's
  reserved set, and `reserved names are classified` fails if a name has neither
  arities nor a kind.
* A "no alias without a Russian original" check: every name in the table must
  exist, so a typo cannot add a dead name.

## Effort

* Core (25–30 names: control, `findall`, type tests, I/O, strings) — 2–3 hours
  with tests.
* All 57 names, the `int`/`float` decision, the two documents and the GUI test
  expectations — about a day.

## Open questions for the user

1. Option A or Option B for `int`/`float` (see above).
2. `strlen` for `ДЛИНА` (my proposal) versus `string_length` or `length` — the
   last one is the trap, because ISO `length/2` works on lists.
3. Whether the *Russian* names stay the ones taught in the course (my
   assumption), with the English table as an appendix.
4. Whether the uppercase English spellings (`ABS`, `SQRT`, `SIN`, `COS`, `TAN`,
   `EXP`) get lowercase aliases as well, so the English surface is one style.
