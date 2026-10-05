# task_62 — `СОРТИРОВКА/2`, `ПОЛНЫЙ/1`, `ДЛЯВСЕХ/2`

**Status:** done (2026-10-05)
**Depends on:** task_11 (the `ВВОД*`/`ВЫВОД` built-ins and the type tests),
task_12 (`ДОБ`, which `ПОЛНЫЙ` guards), task_13 (`НАЙТИВСЕ`, whose collecting
machinery the analysis leaned on), task_39 (English aliases), task_52 (the
comparison signs and the refusal of the ISO operators), task_35 (the lessons),
ADR-016 (what a built-in does when it cannot answer), ADR-025 (the decision)
**Milestone:** the language surface after M16; asked for directly by the user

## Goal

The user asked two questions — «Как думаешь, мы можем добавить bagof / setof?» and
«Какие ещё предикаты полезно было бы добавить?» — and, after the analysis, chose
three predicates to implement.  This file is the record of that choice's
implementation.

## Why `bagof`/`setof` are not among them

Recorded in full as ADR-025; the short version, because it is what shaped the three:

* a built-in returns `Continue`/`Fail`/`Handled` — one verdict, no choice point of
  its own, so `bagof` cannot yield one list per witness group;
* `setof` sorts by the standard order of terms, which this dialect deliberately
  does not have (`БОЛЬШЕ`/`МЕНЬШЕ` compare two numbers or two text constants, the
  `@<`-family is rejected with a hint);
* the grouping needs `^`, one more ISO operator the dialect says no to.

## What was built

| Predicate | ISO name | Semantics |
|---|---|---|
| `СОРТИРОВКА(Список, Результат)` | `sort/2` | ascending, repeats dropped, second argument unified with the result |
| `ПОЛНЫЙ(Терм)` | `ground/1` | no free variable anywhere in the term; a term containing itself is ground |
| `ДЛЯВСЕХ(Условие, Следствие)` | `forall/2` | `НЕ((Условие, НЕ(Следствие)))`, in the words of the affirmative form |

* `builtins_lists.cpp` is new: `builtinSort` walks the list with the tail
  dereferenced, refuses an improper or cyclic list, checks every element *before*
  sorting, sorts with `std::stable_sort` and drops equal neighbours with
  `std::unique`.
* `detail::compareOrder` (in `builtins_arith.cpp`) is the one order: extracted from
  `compareGreater`, so `БОЛЬШЕ`/`МЕНЬШЕ` and `СОРТИРОВКА` cannot drift apart.
* `Engine::hasCounterexample` (in `engine.cpp`, next to `hasSolution`) is what
  `ДЛЯВСЕХ` is two lines on top of.
* `builtinIsGround` walks with the printer's path guard, so a cyclic term answers
  `ДА` instead of walking forever.

## Every place a built-in has to appear

- [x] the dispatch table with its English alias (`builtins.cpp`);
- [x] the lexer's reserved set, both spellings (`lexer.cpp`);
- [x] `checks.cpp` — the *both* arguments of `ДЛЯВСЕХ` are goals and are walked, so
      a misspelled name inside is a warning (pinned by a test);
- [x] `doc/builtins.json` (63 records, group `lists` is new);
- [x] `help.typ` — §3.7 `СОРТИРОВКА`, §4.8 `ДЛЯВСЕХ`, a line in §9 for `ПОЛНЫЙ`,
      four rows in the SWI/GNU table;
- [x] `prologd-diff.typ` — rows in the short table and a section with было/стало;
- [x] `technical.typ` — the cycle guard of `ПОЛНЫЙ`, the nested solve of
      `ДЛЯВСЕХ`, the order shared by `БОЛЬШЕ` and `СОРТИРОВКА`;
- [x] lessons: `lesson_05` §9 «Готовая сортировка», `lesson_10` §5 «Полный ли
      терм» and §6 «Для всех», plus the course tables in `doc/lessons.typ` and
      `examples/lessons/README.md`.

## Tests

- `test_builtins_lists.cpp` (new): ordering numbers and text, the `1`/`1.0` case,
  the unification of the second argument, and six refusals — mixed types, a
  compound, `[1 | 2]`, a non-list, a free variable, and a list containing itself.
- `test_builtins_control.cpp`: `forall` in five shapes, its bindings being undone,
  "a number is not a goal", and the call-site warning inside its arguments.
- `test_builtins_types.cpp`: `ground` over the term kinds, and the cyclic term.
- `test_lessons.cpp` checks the new lesson sections by their own `%!` lines.
- `src/gui/tests/test_reference.py` (63 records, 10 groups) and `test_keywords.py`
  (116 reserved names) pass unchanged.

## Acceptance

`ctest` 316/316, the GUI checks green, `docs` exit 0.  No name collided with the
course: the lessons sort with `вставсорт/2` and `быстрсорт/2`.

## Left for later

`bagof`/`setof` need a decision this round did not take: a built-in with
alternatives (a new frame in the machine) plus a designed order over all term
kinds, this dialect's separate string type included.  Until then the composition
`НАЙТИВСЕ` + `СОРТИРОВКА` covers the sorting half, and the grouping half is a good
student exercise rather than a built-in.
