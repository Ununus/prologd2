# task_51 — `ПЕРВОЕ` принимает любое число целей (variadic from arity 1)

**Status:** done (2026-10-02).  Done as planned, with one correction found by a
probe: a one-goal `ПЕРВОЕ(Ц)` is *not* `ВЫП(Ц)` — it commits to the first solution
(`?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` → `L=[1]`, while `ВЫП(p(X))` gives `L=[1,2]`),
so the manual says «одна цель — фиксируется на первом решении».
**Depends on:** task_44 (the name `ПЕРВОЕ`), task_39 (the alias table), task_43
(`ВЫП/+` in the keyword table), task_37 (`doc/builtins.json`)
**Milestone:** post-M10

## Goal

`ПЕРВОЕ` stops being a two-argument predicate and becomes variadic, the way
`ВЫВОД` is:

```prolog
% как сейчас: Ц2 выполняется, только если Ц1 не решается
?ПЕРВОЕ(российский(X), иностранный(X)).

% первая успешная цель, её альтернативы отсечены, остальные не пробуются
?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).    % X=1
```

The user asked «сейчас `ПЕРВОЕ` у нас с двумя аргументами, сложно ли заменить на
любое количество, как у `ВЫВОД`?» on 2026-10-02; the sketch of the change (a loop,
one table of variadic names, the data and the docs) was given in that reply, and
this file records it as the plan.  The fork «от арности 1 или от арности 2» was
decided **in favour of arity 1**, because in the whole chain (dispatch, keyword
table, checker, `--list-keywords`, the protocol event, the GUI completion)
`variadic` already means *«one argument at least»*.  Keeping that meaning needs no
new field anywhere, and `ПЕРВОЕ(Ц)` gets a sensible reading: «первое решение этой
цели», i.e. `ВЫП(Ц)`.

## Semantics

* `ПЕРВОЕ(Ц1, …, Цn)` — «первая цель, у которой есть решение»: goals are tried in
  order, the first one that succeeds is **committed to** and the rest are not tried
  at all.  With a single argument it is «первое решение `Ц`» — the same as `ВЫП(Ц)`.
* Each goal is a *term*, exactly as with `ВЫП` and `НЕ`: `!` cannot be written
  inside an argument (the argument is a term, and `!` is allowed only at goal
  position — a parse error), and a cut *after* `ПЕРВОЕ(...)` acts on the caller as
  usual.
* This is not the disjunction: `;` (task_41) is backtrackable and yields the
  solutions of both branches; `ПЕРВОЕ` yields the first solution of the first
  branch that has one.  In SWI the same shape is written
  `(A -> true ; B -> true ; C)`.
* Nothing about the nested solver changes: `ПЕРВОЕ` runs every goal through
  `Engine::callOnce`, which already builds its own solver over its own environment
  chain and its own cut barrier, and undoes the bindings of a goal that fails.

## What already exists — the whole `ВЫВОД` machinery

| Thing | Where | State |
|---|---|---|
| the body to generalise | `builtins.cpp`, `builtinOr` — `callOnce(args[0]) \|\| callOnce(args[1])` | two arguments, hardcoded |
| `BuiltinFn` = `BuiltinResult(*)(Engine&, std::span<const Term>)` | `engine.hpp` | already takes any count |
| variadic lookup | `builtins.cpp`: `isVariadicBuiltin`, `findBuiltin` (`arity >= 1`), `builtinArities`, `builtinNames` | hardcoded to `ВЫВОД`/`write` |
| keyword table | `keywords.cpp`, `reservedKeywords` — takes `variadic` from `builtinArities` | nothing to do |
| the checker | `checks.cpp`, `hasArity` — `if (variadic) return arity >= 1;` | nothing to do |
| `--list-keywords` | `main.cpp` — prints `имя/+` for a variadic name | nothing to do |
| the protocol | `protocol.cpp` — the `keywords` list carries `variadic` | nothing to do |
| completion | `completion.py` — variadic inserts `имя()` with the caret inside | nothing to do at arity 1 |
| reference data | `doc/builtins.json` | one record to edit |

The reason this is small is the same reason it was small for `ВЫВОД`: `ПЕРВОЕ` is a
*dispatch-table builtin*, looked up by name and arity, unlike `ВЫП`, which the
solver answers because it constructs a new goal term.

## What was done

- [x] `builtins.cpp`: `builtinFirst` (renamed from `builtinOr` — that was the last
      place the retired `ИЛИ`/`or` survived) loops over `args`
      (`for (const Term& goal : args) { if (engine.callOnce(goal)) return
      BuiltinResult::Continue; } return BuiltinResult::Fail;`).
- [x] `builtins.cpp`: `isVariadicBuiltin(name)` is now the table
      `kVariadicNames` — variadic
      name → function — `ВЫВОД`/`write` → `builtinWrite`, `ПЕРВОЕ`/`first` →
      `builtinFirst`, read by `findBuiltin`, `builtinArities` and `builtinNames` (the
      last one no longer carries two names in its own body).  The row
      `add("ПЕРВОЕ", 2, builtinOr)` is gone.
- [x] Comments that enumerate the variadic names: `kVariadicNames` itself,
      `kEnglishNames`, `BuiltinArities` in `engine.hpp`, `builtinNames`'s comment,
      `hasArity` in `checks.cpp` (`ВЫВОД/+`, `ПЕРВОЕ/+`, `ВЫП/+`).
- [x] `doc/builtins.json`, the `ПЕРВОЕ` record: `"arities": []`, `"variadic": true`,
      and the general form among the variants.
- [x] `doc/help.typ` §4.6: the signature is `ПЕРВОЕ(Цель, ...)` (the shape
      `ВЫП(Цель, ...)` and `ВЫВОД(Аргумент, ...)` use) with the number of goals and
      the example; §4.5's «это `ПЕРВОЕ/2`» became «это `ПЕРВОЕ`».
- [x] `doc/technical.typ`, `doc/prologd-diff.typ` (its «`ПЕРВОЕ` вместо `ИЛИ`»
      section and the table row), `ai/porting_notes.md` (the `ИЛИ` → `ПЕРВОЕ` row),
      `src/gui/README.md` (the sentence about the variadic names).
- [x] `examples/lessons/lesson_04.pld`: the section that teaches `ПЕРВОЕ` says
      `ПЕРВОЕ(Цель, ...)` and shows a three-goal query
      (`?ПЕРВОЕ(БОЛЬШЕ(1, 2), цена(Т, 500), цена(Т, 40)).` → `Т=сыр`), pinned by
      the `%!` line that `test_lessons.cpp` checks.
- [x] The retired-name advice keeps the two-argument shape: an old call can only be
      `ИЛИ/2`, so the message mirrors it one to one and mentions the disjunction.
      `test_diagnostics.cpp` pins that text and needed no change.
- [x] Tests:
      * `test_builtins_control.cpp` — the pinned «`ПЕРВОЕ` не имеет арности 3» case
        changed (arity 3 is legal now and answers `НЕТ`, `?ПЕРВОЕ.` is the arity-0
        load error), and the new case «the choice form takes any number of goals»
        pins the variadic form, the commitment and the non-predicate argument.
      * `test_keywords.cpp` — `first->arities == {2}` became `variadic` with an
        empty arity list, in both the arity test and the retired-name test.
      * `test_aliases.cpp` — the `ВЫВОД`-only skip became
        `builtinArities(name).variadic`, and the case is now «the variadic
        built-ins are variadic under both spellings» over `ВЫВОД` and `ПЕРВОЕ`.
      * `src/tests/CMakeLists.txt` — the CLI test
        `cli_list_keywords_variadic_first` expects `ПЕРВОЕ/\+`.
      * `src/gui/tests/test_reference.py`, `test_completion.py`,
        `test_keywords.py`, `test_queries.py`, `test_tokens.py`,
        `test_queryline.py` — all green with the flag coming out for `ПЕРВОЕ`.

## What must not change

- Two-argument calls keep answering exactly as before: `ПЕРВОЕ(Ц1, Ц2)` is still
  «если Ц1 решается — фиксируемся на ней, иначе Ц2», and `;` is still the
  disjunction.
- The solver (`resolveGoal`, `callOnce`), the lexer's reserved set and the parser
  need no edit at all.
- `ВЫП`/`call` stay outside the table (`kEngineCallables`), so nothing about
  `call/N` is touched by this task.

## Verification (done)

1. Build: exit 0, no compiler errors or warnings.  `ctest --test-dir
   build/windows-msvc -C Release`: **278/278** (276 before: +1 Catch2 case, +1 CLI
   test).
2. `prologd --list-keywords` → `ПЕРВОЕ/+`, `first/+`, `ВЫВОД/+`, `write/+`,
   `ВЫП/+`, `call/+`; no `ПЕРВОЕ/2`.
3. By hand, with `build\windows-msvc\src\cli\Release\prologd.exe`:
   * `?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).` → `X=1`;
   * `?ПЕРВОЕ(ЛОЖЬ, РАВНО(Y, 2)).` → `Y=2` (unchanged);
   * `п(1). п(2). ?ПЕРВОЕ(п(Z), ЛОЖЬ).` → `Z=1` (commitment, unchanged);
   * `?first(ЛОЖЬ, ЛОЖЬ, РАВНО(W, 1)).` → `W=1` (the English spelling);
   * `?ПЕРВОЕ(ЛОЖЬ).` → `НЕТ`; `?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, ЛОЖЬ).` → `НЕТ`;
   * `?ПЕРВОЕ.` → `1:2: error: ПЕРВОЕ не имеет арности 0`, exit 2;
   * `?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` → `L=[1]`, while `ВЫП(p(X))` → `L=[1,2]`.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`): `test_reference.py`
   (the JSON ↔ `--list-keywords` ↔ the manual), `test_completion.py`,
   `test_keywords.py` (108 reserved names), `test_queries.py`, `test_tokens.py`,
   `test_queryline.py` — all green.
5. `typst compile` of `help.typ` (32 pages), `prologd-diff.typ` (22 pages) and
   `technical.typ` — exit 0; §4.6 of the manual and the «`ПЕРВОЕ` вместо `ИЛИ`»
   section of the diff document were read on the rendered pages.

## Notes

* A one-goal `ПЕРВОЕ(Ц)` is «the first solution of `Ц`», which is a *committed*
  once: `?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` answers `L=[1]` where `ВЫП(p(X))` answers
  `L=[1,2]`.  The reading «i.e. `ВЫП(Ц)`» in the plan above was wrong; the manual
  (`help.typ` §4.6) says «фиксируется на первом решении», and the probe is
  recorded here.
* The retired-name advice keeps the two-argument shape
  (««ИЛИ» переименовано: теперь это «ПЕРВОЕ(Ц1, Ц2)»…»): an old call can only be
  `ИЛИ/2`, so the message mirrors it one to one, and the variadic freedom belongs
  in the manual, not in a message about a rename.  `test_diagnostics.cpp` pins
  that text and did not have to change.
* `ПЕРВОЕ(Ц)` is deliberately allowed: it is «once» without the extra-argument
  machinery.  Forbidding it would need a second notion of «variadic» — a minimum
  arity — through `BuiltinArities`, `KeywordInfo`, `hasArity`, `--list-keywords`
  and the completion skeleton, and would make one flag mean two things.  If the
  one-goal form ever looks like a mistake, the cheap fix is to reject arity 1 in
  `checks.cpp` alone; that is not proposed now.
