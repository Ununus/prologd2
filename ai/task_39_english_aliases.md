# task_39 — English aliases for the built-ins

**Status:** done (2026-09-30)
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

1. **Type tests and conversions were split by spelling — and the split changed
   the plan**: `integer/1` and `float/1` are the *tests* (aliases of `ЦЕЛ`/`ВЕЩ`,
   so they answer about a *type*: `integer(5.0)` is false).  The plan then
   assumed that `int(X)`/`float(X)` convert and that `to_int/1`/`to_float/1`
   should take their place; reading the implementation showed that they never
   converted — they *check* whether a value can be read as an integer or as any
   number (`is_whole(4.0)` is true, `is_whole(4.5)` is false, `number(4)` is
   true).  A conversion already exists and is `ЦЕЛВЕЩ/num_to_float`, so the two
   are `is_whole(X)` and `number(X)` now, and the planned `to_int`/`to_float`
   were dropped: a second conversion with no caller would be a name without a
   use.  `int/1` and `float/1` are gone.
2. `ДЛИНА/2` becomes `strlen/2` — **not** `length/2`, which in ISO is the length
   of a *list* while this one measures a string in characters.
3. **All English names are lowercase**, including the ones that are uppercase
   today: `ABS`, `SQRT`, `SIN`, `COS`, `TAN`, `EXP` become `abs`, `sqrt`, `sin`,
   `cos`, `tan`, `exp`.  The upper-case spellings were *not* kept (the user
   settled this on 2026-09-30): one spelling per name, and the lessons, the
   examples and the manual were updated in the same change.
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

## Result

The table is `constexpr std::pair<std::string_view, std::string_view>
kEnglishNames[]` in `builtins.cpp` (47 rows) with two helpers, `englishName()` and
`isVariadicBuiltin()`.  Everything else follows from it: `registerOne`/`add`
register both spellings, `builtinAliases()` exposes the pairs, `findBuiltin`,
`builtinArities` and `builtinNames` treat `ВЫВОД`/`write` as the variadic one, the
lexer's reserved set lists the English names section by section, and `ВЫП`/`call`
plus `ИМПОРТ`/`import` are handled where they live (the engine's meta-call check,
`kEngineCallables`, `kReservedDirectives`, `isImportName()` in the parser).  The
GUI needed nothing: it reads the reserved names from the `ready` event, and
`test_keywords.py` shows 108 names agreed on by the CLI and the protocol.

Tests: `test_aliases.cpp` (four cases) walks the table — every alias reaches the
same function as its Russian original, the variadic built-in is variadic under
both names, every Russian built-in has a row, and one program is run in English
and compared with its whole output.  The renamed arithmetic is pinned in
`test_builtins_arith.cpp` and `test_keywords.cpp`; `lesson_03.pld` was rewritten
for `is_whole`/`number` (the lesson checker runs every lesson's output, so the
rename could not pass unnoticed).

Documentation: `doc/help.typ` §5.5/5.6/5.7 use the new spellings, §9 points at
the English type tests and warns that `ЦЕЛ(5.0)` is false where `is_whole(5.0)`
is true, and appendix 17 carries the whole table (generated from
`kEnglishNames`, so it cannot disagree with the interpreter).  `prologd-diff.typ`
§15 explains the aliases and the two renames in the «что перенести» form, and
`ai/conventions.md` gained the rule that the table is the one place a pair is
written.

Left for a follow-up: the course appendix file (`examples/lessons/appendix_english.pld`
and its registration in `test_lessons.cpp`, `examples/lessons/README.md` and
`doc/lessons.typ`) — the manual's appendix covers the reference meanwhile, and
the lessons themselves stay Russian as decided.

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
