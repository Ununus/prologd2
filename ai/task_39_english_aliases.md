# task_39 — English aliases for the built-ins

**Status:** not started
**Depends on:** nothing; it *changes* the data of task_37 (the reference), so the
two are best done in that order, or the `aliases` field is added to
`doc/builtins.json` in the same pass
**Milestone:** M14
**Supersedes:** the parked note `ai/maybe/english_aliases.md` (removed with this
task, its analysis kept here)

## Goal

Spell every built-in two ways: the Russian name the course teaches, and the
name a reader of ordinary Prolog expects (`НАЙТИВСЁ`/`findall`).  The mechanism
touches two lists in the interpreter and nothing in the GUI — highlighting,
completion, `--list-keywords` and the cheat-sheet all read the reserved names
from the interpreter's `ready` event (`src/gui/prologd_gui/keywords.py`), so a
registered alias appears everywhere by itself.

## Decisions taken by the user on 2026-09-30

1. **Type tests and conversions are split by spelling**: `integer/1` and
   `float/1` are the *tests* (aliases of `ЦЕЛ`/`ВЕЩ`), `to_int/1` and
   `to_float/1` are the *conversions*.  This is the one place where a name
   changes meaning: today `int(X)`/`float(X)` convert, and after this task they
   are gone — `int/1` too, for symmetry with `float/1`, which *cannot* stay a
   conversion because the test takes the name.
2. `ДЛИНА/2` becomes `strlen/2` — **not** `length/2`, which in ISO is the length
   of a *list* while this one measures a string in characters.
3. **All English names are lowercase**, including the ones that are uppercase
   today: `ABS`, `SQRT`, `SIN`, `COS`, `TAN`, `EXP` become `abs`, `sqrt`, `sin`,
   `cos`, `tan`, `exp`.  The old uppercase spellings stay as aliases, because the
   programs ported from the original PrologD use them and they cost nothing.
4. **The course stays Russian.**  The English surface is documented in an
   appendix, not in the lessons.

## The alias table

Lowercase with underscores, matching `mod`/`div` and the new conversions.  The
table is *data* in the interpreter (one map, `aliasOf`), so a name cannot be
registered without its Russian original and completeness is structural rather
than a matter of remembering.

| Russian | Arities | Alias | Note |
|---|---|---|---|
| `ЛОЖЬ` | 0 | `fail` | |
| `ТРАССА` | 0 | `trace` | |
| `НЕТ_ТРАССЫ` | 0 | `no_trace` | |
| `ТИХО` | 0 | `quiet` | |
| `ВЕРСИЯ` | 0 | `version` | |
| `НЕ` | 1 | `not` | |
| `ИЛИ` | 2 | `or` | keeps its documented committed behaviour (see task_41) |
| `РАВНО` | 2 | `equal` | **not** `=`, not `==`: it compares, it does not unify |
| `ПС` | 0 | `nl` | |
| `ЖДИ` | 1 | `wait` | |
| `ВЫП` | 1 | `call` | engine-level (`kEngineCallables`), not the dispatch table |
| `ПЕР` | 1 | `var` | ISO `var/1` |
| `ЦЕЛ` | 1 | `integer` | ISO `integer/1` |
| `ВЕЩ` | 1 | `float` | ISO `float/1` |
| `СИМВ` | 1 | `is_text` | true for an atom *and* a string, unlike ISO `atom/1` |
| `СПИСОК` | 1 | `is_list` | ISO `is_list/1` |
| `НАЙТИВСЁ` | 3 | `findall` | argument order already ISO |
| `БОЛЬШЕ` | 2 | `greater` | ISO spells it `>` (an operator — not this task) |
| `МЕНЬШЕ` | 2 | `less` | ISO spells it `<` |
| `СЛОЖЕНИЕ` | 3 | `plus` | `plus/3` exists in several systems |
| `УМНОЖЕНИЕ` | 3, 4 | `mul` | |
| `ABS`/`SQRT`/`SIN`/`COS`/`TAN`/`EXP` | 2 | `abs`/… | lowercase becomes canonical |
| `СЛУЧ` | 1, 3 | `random` | |
| `ЦЕЛВЕЩ` | 2 | `num_to_float` | int ↔ float, either direction |
| `СТРЦЕЛ` | 2 | `str_to_int` | string ↔ int |
| `СТРВЕЩ` | 2 | `str_to_float` | string ↔ float |
| `СТРСПИС` | 2 | `str_to_list` | string ↔ list of code points |
| `БУКВА` | 2 | `is_letter` | |
| `ЦИФРА` | 2 | `is_digit` | |
| `СЦЕП` | 3 | `concat` | ISO `atom_concat/3` |
| `КОПИЯ` | 4 | `substring` | **not** `copy`: five argument modes, §7.4 |
| `ДЛИНА` | 2 | `strlen` | decision 2 |
| `ВЫВОД` | 1+ | `write` | variadic |
| `ВВКОД` | 1 | `put_code` | writes one code point |
| `ВВОДЦЕЛ` | 1, 2 | `read_int` | |
| `ВВОДВЕЩ` | 1, 2 | `read_float` | |
| `ВВОДСИМВ` | 1, 2 | `read_char` | |
| `ВВОДСТР` | 1, 2 | `read_string` | |
| `ЧТЕНИЕ_ИЗ` | 1 | `see` | ISO `see/1` |
| `ЗАПИСЬ_В` | 1 | `tell` | ISO `tell/1` |
| `СКОЛЬКО` | 2 | `clause_count` | no ISO counterpart |
| `ПРЕДЛ` | 4 | `clause_at` | ISO `clause/2` goes by head, this one by number |
| `ТЕРМ` | 2 | `univ` | ISO `=..` |
| `ДОБ` | 3 | `assert` | ISO `assertz/1`, here with a position |
| `УДАЛЕНИЕ` | 2 | `retract` | |
| `ТОЧКА`/`ЛИНИЯ`/`ОКРУЖНОСТЬ`/`ЗАКРАСКА` | 3/5/4/3 | `point`/`line`/`circle`/`fill` | graphics |
| `ИМПОРТ` | directive | `import` | lexer + `keywords.cpp` + `parser.cpp` |

## What a name does not buy

An English spelling does not make the dialect ISO Prolog, and the paperwork
should say so once, in `prologd-diff.typ`: arithmetic and comparison stay
*callable predicates with free variables* (`plus(A, B, C)`, `greater(A, B)`),
so `is/2`, `<`, `>` and `=:=` remain out of reach until the grammar grows infix
arithmetic (a separate task; it is already an optional item in `ai/status.md`).
`findall` is the single name where the alias is exactly ISO.  Two more dialect
facts belong next to it: `6` unifies with `6.0` (ISO fails), and an atom and a
string are interchangeable (in SWI they are different types).

## Deliverables

- [ ] `src/prlib/src/builtins.cpp`: the alias table plus `addAliases`, or `add`
      taking the Russian name and the alias list.
- [ ] `src/prlib/src/lexer.cpp`: the reserved set — needed for the *uppercase*
      Russian names and for highlighting/completion of the new ones.
- [ ] `src/prlib/src/keywords.cpp`: `call` joins `kEngineCallables`; `import`
      joins `kReservedDirectives`; `parser.cpp`'s `kImportName` learns it too.
- [ ] The renaming of decision 1: `int/1` and `float/1` stop being conversions,
      `to_int/1` and `to_float/1` take over; `integer/1` and `float/1` become
      the tests.
- [ ] Existing users of the old spellings updated: `examples/lessons/lesson_03.pld`
      (`?int(3).`, `?int(3.5).`, `?float(3).` — the `%!` expectations do not
      change, only the names) and `src/tests/test_builtins_arith.cpp` (`ABS(...)`
      calls, which keep one test case of their own as alias coverage).
- [ ] `doc/help.typ`: an appendix with the correspondence table (Russian ↔
      English, one row per name, generated from the same data if that turns out
      to be natural — task_37's `doc/builtins.json` would carry an `aliases`
      field), plus corrections in §1.2/§2 where the text says the Russian names
      *are* the language.
- [ ] `examples/lessons/appendix_english.pld`: the appendix in the course's own
      form — a runnable program that shows the same small task in both
      spellings, with `%!` lines, checked by `test_lessons.cpp` like every other
      lesson, and listed in `examples/lessons/README.md`.  It is the one place a
      reader sees the two surfaces side by side.
- [ ] `doc/prologd-diff.typ`: the addition recorded (not a divergence, but it
      changes the language's surface and the `int`/`float` meaning).
- [ ] Tests: a table-driven equivalence test — for each row of the table, the
      same tiny program with the Russian name and with the alias must produce
      the same output; a completeness test (every name in `builtinNames()` has a
      row); `src/gui/tests/test_keywords.py`'s expectations extended (the list
      roughly doubles: ~57 → ~110 names).
- [ ] The GUI needs no code change; verify that by running one GUI test and by
      eye in the completion popup (both spellings are offered, both are
      coloured as built-ins).

## Acceptance criteria

1. `?findall(X, член(X, [а, б]), список).` and `?НАЙТИВСЁ(X, член(X, [а, б]), список).`
   behave identically, for every row of the table.
2. `integer(3)` is true and `integer(3.0)` is false; `to_int(3.7, X)` converts;
   `float(3)` is false (it is a test now) — the two meaning changes are the ones
   the appendix makes visible.
3. Every name from `prologd --list-keywords` has an English spelling, and every
   alias is in the lexer's reserved set (the existing keyword tests enforce the
   second half).
4. The course still teaches Russian, and `appendix_english.pld` passes the
   lesson check.
5. The full suite is green.

## Risks and notes

* A built-in shadows a user clause of the same name (`findBuiltin` runs before
  the database in `Solver::resolveGoal`).  The user's decision is that this is
  acceptable: the syntax was already changed once, the program has a small
  audience, and the lessons are the corpus that matters.  Do not build fallback
  machinery.
* `equal` vs `РАВНО`: `РАВНО` is unification (`РАВНО(X, X).`), not a comparison.
  The alias must not be `=`, and the help text for it should say "unifies" in so
  many words.
* Keep `mod`/`div` as they are: they are already English infix operators and no
  Russian spelling exists or is wanted.
