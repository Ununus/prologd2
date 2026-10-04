# task_51 — `ПЕРВОЕ` takes any number of goals (variadic from arity 1)

**Status:** done (2026-10-02).  Done as planned, with one correction found by a probe: a
one-goal `ПЕРВОЕ(Ц)` is *not* `ВЫП(Ц)` — it commits to the first solution
(`?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` → `L=[1]`, while `ВЫП(p(X))` gives `L=[1,2]`), so the
manual says «одна цель — фиксируется на первом решении».
**Depends on:** task_44 (the name `ПЕРВОЕ`), task_39 (the alias table), task_43 (`ВЫП/+`
in the keyword table), task_37 (`doc/builtins.json`)
**Milestone:** post-M10

## Goal

`ПЕРВОЕ` stops being a two-argument predicate and becomes variadic, the way `ВЫВОД` is:

```prolog
% as before: Ц2 is run only if Ц1 has no solution
?ПЕРВОЕ(российский(X), иностранный(X)).

% the first goal that succeeds, its alternatives cut, the rest not tried
?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).    % X=1
```

The user asked on 2026-10-02 whether a two-argument `ПЕРВОЕ` could take any number of
arguments, like `ВЫВОД`; the sketch of the change (a loop, one table of variadic names, the
data and the docs) was given in that reply, and this file records it as the plan.  The fork
"from arity 1 or from arity 2" was decided **in favour of arity 1**, because in the whole
chain (dispatch, keyword table, checker, `--list-keywords`, the protocol event, the GUI
completion) `variadic` already means "one argument at least".  Keeping that meaning needs
no new field anywhere, and `ПЕРВОЕ(Ц)` gets a sensible reading: "the first solution of this
goal".

## Semantics

* `ПЕРВОЕ(Ц1, …, Цn)` — "the first goal that has a solution": goals are tried in order,
  the first one that succeeds is **committed to**, and the rest are not tried at all.
  With a single argument it is "the first solution of `Ц`" — a committed once, see Notes.
* Each goal is a *term*, exactly as with `ВЫП` and `НЕ`: `!` cannot be written inside an
  argument (the argument is a term, and `!` is allowed only at goal position — a parse
  error), and a cut *after* `ПЕРВОЕ(...)` acts on the caller as usual.
* This is not the disjunction: `;` (task_41) is backtrackable and yields the solutions of
  both branches; `ПЕРВОЕ` yields the first solution of the first branch that has one.  In
  SWI the same shape is written `(A -> true ; B -> true ; C)`.
* Nothing about the nested solver changes: `ПЕРВОЕ` runs every goal through
  `Engine::callOnce`, which already builds its own solver over its own environment chain
  and its own cut barrier, and undoes the bindings of a goal that fails.

## What already existed — the whole `ВЫВОД` machinery

| Thing | Where | State |
|---|---|---|
| the body to generalise | `builtins.cpp`, `builtinOr` — `callOnce(args[0]) \|\| callOnce(args[1])` | two arguments, hardcoded |
| `BuiltinFn` = `BuiltinResult(*)(Engine&, std::span<const Term>)` | `engine.hpp` | already takes any count |
| variadic lookup | `builtins.cpp`: `isVariadicBuiltin`, `findBuiltin` (`arity >= 1`), `builtinArities`, `builtinNames` | hardcoded to `ВЫВОД`/`write` |
| keyword table | `keywords.cpp`, `reservedKeywords` — takes `variadic` from `builtinArities` | nothing to do |
| the checker | `checks.cpp`, `hasArity` — `if (variadic) return arity >= 1;` | nothing to do |
| `--list-keywords` | `main.cpp` — prints `имя/+` for a variadic name | nothing to do |
| the protocol | `protocol.cpp` — the `keywords` list carries `variadic` | nothing to do |
| completion | `completion.py` — variadic inserts `имя()` with the caret inside | nothing at arity 1 |
| reference data | `doc/builtins.json` | one record to edit |

This is small for the same reason it was small for `ВЫВОД`: `ПЕРВОЕ` is a *dispatch-table
builtin*, looked up by name and arity, unlike `ВЫП`, which the solver answers because it
constructs a new goal term.

## What was done

* `builtins.cpp`: `builtinFirst` (renamed from `builtinOr` — that was the last place the
  retired `ИЛИ`/`or` survived) loops over `args`: for every goal, `callOnce(goal)`; on
  success `BuiltinResult::Continue`, otherwise `BuiltinResult::Fail` at the end.
* `builtins.cpp`: `isVariadicBuiltin(name)` became the table `kVariadicNames` — variadic
  name → function — `ВЫВОД`/`write` → `builtinWrite`, `ПЕРВОЕ`/`first` → `builtinFirst`,
  read by `findBuiltin`, `builtinArities` and `builtinNames` (the last one no longer
  carries two names in its own body).  The row `add("ПЕРВОЕ", 2, builtinOr)` is gone.
* Comments that enumerate the variadic names: `kVariadicNames` itself, `kEnglishNames`,
  `BuiltinArities` in `engine.hpp`, the comment of `builtinNames`, `hasArity` in
  `checks.cpp` (`ВЫВОД/+`, `ПЕРВОЕ/+`, `ВЫП/+`).
* `doc/builtins.json`, the `ПЕРВОЕ` record: `"arities": []`, `"variadic": true`, and the
  general form among the variants.
* `doc/help.typ` §4.6: the signature is `ПЕРВОЕ(Цель, ...)` (the shape `ВЫП(Цель, ...)` and
  `ВЫВОД(Аргумент, ...)` use) with the number of goals and the example; §4.5's "это
  `ПЕРВОЕ/2`" became "это `ПЕРВОЕ`".
* `doc/technical.typ`; `doc/prologd-diff.typ` (its "«ПЕРВОЕ» вместо «ИЛИ»" section and the
  table row); `ai/porting_notes.md` (the `ИЛИ` → `ПЕРВОЕ` row); `src/gui/README.md` (the
  sentence about the variadic names).
* `examples/lessons/lesson_04.pld`: the section that teaches `ПЕРВОЕ` says
  `ПЕРВОЕ(Цель, ...)` and shows a three-goal query (`?ПЕРВОЕ(БОЛЬШЕ(1, 2), цена(Т, 500),
  цена(Т, 40)).` → `Т=сыр`), pinned by the `%!` line `test_lessons.cpp` checks.
* The retired-name advice keeps the two-argument shape: an old call can only be `ИЛИ/2`,
  so the message mirrors it one to one and mentions the disjunction;
  `test_diagnostics.cpp` pins that text and needed no change.
* Tests: `test_builtins_control.cpp` — the pinned case "«ПЕРВОЕ» не имеет арности 3"
  changed (arity 3 is legal now and answers `НЕТ`, `?ПЕРВОЕ.` is the arity-0 load error),
  and the new case "the choice form takes any number of goals" pins the variadic form, the
  commitment and the non-predicate argument; `test_keywords.cpp` — `first->arities == {2}`
  became `variadic` with an empty arity list, in both the arity test and the retired-name
  test; `test_aliases.cpp` — the `ВЫВОД`-only skip became
  `builtinArities(name).variadic`, and the case is now "the variadic built-ins are variadic
  under both spellings" over `ВЫВОД` and `ПЕРВОЕ`; `src/tests/CMakeLists.txt` — the CLI test
  `cli_list_keywords_variadic_first` expects `ПЕРВОЕ/\+`; and
  `src/gui/tests/test_reference.py`, `test_completion.py`, `test_keywords.py`,
  `test_queries.py`, `test_tokens.py`, `test_queryline.py` — all green with the flag coming
  out for `ПЕРВОЕ`.

## What must not change

* Two-argument calls keep answering exactly as before: `ПЕРВОЕ(Ц1, Ц2)` is still "if Ц1 has
  a solution, commit to it, otherwise Ц2", and `;` is still the disjunction.
* The solver (`resolveGoal`, `callOnce`), the lexer's reserved set and the parser need no
  edit at all.
* `ВЫП`/`call` stay outside the table (`kEngineCallables`), so nothing about `call/N` is
  touched by this task.

## Verification (done)

1. Build: exit 0, no compiler errors or warnings.  `ctest --test-dir build/windows-msvc -C
   Release`: **278/278** (276 before: +1 Catch2 case, +1 CLI test).
2. `prologd --list-keywords` → `ПЕРВОЕ/+`, `first/+`, `ВЫВОД/+`, `write/+`, `ВЫП/+`,
   `call/+`; no `ПЕРВОЕ/2`.
3. By hand, with `build\windows-msvc\src\cli\Release\prologd.exe`:
   `?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).` → `X=1`;
   `?ПЕРВОЕ(ЛОЖЬ, РАВНО(Y, 2)).` → `Y=2` (unchanged); `п(1). п(2). ?ПЕРВОЕ(п(Z), ЛОЖЬ).` →
   `Z=1` (commitment, unchanged); `?first(ЛОЖЬ, ЛОЖЬ, РАВНО(W, 1)).` → `W=1` (the English
   spelling); `?ПЕРВОЕ(ЛОЖЬ).` → `НЕТ`; `?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, ЛОЖЬ).` → `НЕТ`; `?ПЕРВОЕ.` →
   `1:2: error: ПЕРВОЕ не имеет арности 0`, exit 2; `?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` →
   `L=[1]`, while `ВЫП(p(X))` → `L=[1,2]`.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`): `test_reference.py` (the JSON
   ↔ `--list-keywords` ↔ the manual), `test_completion.py`, `test_keywords.py` (108
   reserved names), `test_queries.py`, `test_tokens.py`, `test_queryline.py` — all green.
5. `typst compile` of `help.typ` (32 pages), `prologd-diff.typ` (22 pages) and
   `technical.typ` — exit 0; §4.6 of the manual and the "«ПЕРВОЕ» вместо «ИЛИ»" section of
   the diff document were read on the rendered pages.

## Notes

* A one-goal `ПЕРВОЕ(Ц)` is "the first solution of `Ц`", a *committed* once:
  `?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` answers `L=[1]` where `ВЫП(p(X))` answers `L=[1,2]`.
  The reading "i.e. `ВЫП(Ц)`" in the plan above was wrong; the manual (`help.typ` §4.6)
  says «фиксируется на первом решении», and the probe is recorded here.
* `ПЕРВОЕ(Ц)` is deliberately allowed: it is "once" without the extra-argument machinery.
  Forbidding it would need a second notion of "variadic" — a minimum arity — through
  `BuiltinArities`, `KeywordInfo`, `hasArity`, `--list-keywords` and the completion
  skeleton, and would make one flag mean two things.  If the one-goal form ever looks like
  a mistake, the cheap fix is to reject arity 1 in `checks.cpp` alone; that is not proposed
  now.
