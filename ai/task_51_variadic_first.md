# task_51 — `ПЕРВОЕ` принимает любое число целей (variadic from arity 1)

**Status:** not started — the plan is written down (2026-10-02); the user chose
«с одной» (one goal at least, any number after)
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

## Deliverables

- [ ] `builtins.cpp`: `builtinOr` loops over `args`
      (`for (const Term& goal : args) { if (engine.callOnce(goal)) return
      BuiltinResult::Continue; } return BuiltinResult::Fail;`).
- [ ] `builtins.cpp`: `isVariadicBuiltin(name)` becomes one small table — variadic
      name → function — `ВЫВОД`/`write` → `builtinWrite`, `ПЕРВОЕ`/`first` →
      `builtinOr`, read by `findBuiltin`, `builtinArities` and `builtinNames` (the
      last one stops carrying two names in its own body).  Delete the row
      `add("ПЕРВОЕ", 2, builtinOr)`.
- [ ] Comments that enumerate the variadic names: `builtinTable`'s neighbours,
      `BuiltinArities` in `engine.hpp` («`ВЫВОД` accepts any positive arity»),
      `hasArity` in `checks.cpp` («`ВЫВОД/+` and `ВЫП/+`» → add `ПЕРВОЕ/+`).
- [ ] Optional, but it finishes task_44: rename `builtinOr` → `builtinFirst` —
      `builtinOr` is the last place the retired `ИЛИ`/`or` survives.
- [ ] `doc/builtins.json`, the `ПЕРВОЕ` record: `"arities": []`, `"variadic": true`,
      and a summary/variants with the general form (`ПЕРВОЕ(Цель1, …, Цельn) —
      первая успешная цель, её альтернативы отсечены`).
- [ ] `doc/help.typ` §4.6: the signature `ПЕРВОЕ(Цель1, …, Цельn)` and one sentence
      that any number of goals is allowed (one at least); §4.5's «это `ПЕРВОЕ/2`» →
      «это `ПЕРВОЕ`».
- [ ] `doc/technical.typ` (`ПЕРВОЕ(Ц1, Ц2)`), `doc/prologd-diff.typ` (§18 and the
      table row around line 230), `ai/porting_notes.md` (the `ИЛИ` → `ПЕРВОЕ` row),
      `src/gui/README.md` (the sentence that `ВЫВОД` is *the* variadic name).
- [ ] The retired-name advice (`checks.cpp`: «`ИЛИ` переименовано: теперь это
      `ПЕРВОЕ(Ц1, Ц2)`», and the `or` spelling beside it): decide whether it keeps
      the two-argument shape (the common one) or becomes `ПЕРВОЕ(Ц1, Ц2, …)`.
      `test_diagnostics.cpp` pins that text, so the two move together.
- [ ] Tests:
      * `test_builtins_control.cpp` — the pinned case «`ПЕРВОЕ` не имеет арности 3
        (есть 2)» **must change** (arity 3 is legal now); add the new cases: three
        and more goals, commitment to the first successful one, `ПЕРВОЕ(Ц)` as
        «once», and `?ПЕРВОЕ.` still being a load error.
      * `test_keywords.cpp` — `first->arities == {2}` becomes `variadic` with an
        empty arity list (the `ВЫВОД` case is the model).
      * `test_aliases.cpp` — the `ВЫВОД`-only skip becomes
        `builtinArities(name).variadic`, and `first` joins the
        variadic-under-both-names case.
      * optionally, a `ПЕРВОЕ/+` expectation in the CLI keyword test
        (`src/tests/CMakeLists.txt`, next to `ВЫВОД/+`).
      * `src/gui/tests/test_reference.py` (json ↔ `--list-keywords` ↔ the manual),
        `test_completion.py` and `test_keywords.py` — run them once the flag starts
        coming out for `ПЕРВОЕ`.

## What must not change

- Two-argument calls keep answering exactly as before: `ПЕРВОЕ(Ц1, Ц2)` is still
  «если Ц1 решается — фиксируемся на ней, иначе Ц2», and `;` is still the
  disjunction.
- The solver (`resolveGoal`, `callOnce`), the lexer's reserved set and the parser
  need no edit at all.
- `ВЫП`/`call` stay outside the table (`kEngineCallables`), so nothing about
  `call/N` is touched by this task.

## Verification

1. `cmake --build build/windows-msvc --config Release` and
   `ctest --test-dir build/windows-msvc -C Release`.
2. `prologd --list-keywords` → `ПЕРВОЕ/+` and `first/+`, and no `ПЕРВОЕ/2`.
3. By hand, with `build\windows-msvc\src\cli\Release\prologd.exe`:
   * `?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).` → `X=1`;
   * `?ПЕРВОЕ(ЛОЖЬ, РАВНО(Y, 2)).` → `Y=2` (unchanged);
   * `п(1). п(2). ?ПЕРВОЕ(п(X), ЛОЖЬ).` → `X=1` (commitment, unchanged);
   * `?ПЕРВОЕ(ЛОЖЬ).` → `НЕТ`; `?ПЕРВОЕ.` → a load error naming the arity.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`): `test_reference.py`,
   `test_completion.py`, `test_keywords.py`, `test_window.py`, `test_queries.py`.
5. `cmake --build build/windows-msvc --config Release --target docs` (the five
   PDFs, `help.typ` §4.6 among them).

## Notes

- `ПЕРВОЕ(Ц)` is deliberately allowed: it is `ВЫП(Ц)` without the extra-argument
  machinery.  Forbidding it would need a second notion of «variadic» — a minimum
  arity — through `BuiltinArities`, `KeywordInfo`, `hasArity`, `--list-keywords`
  and the completion skeleton, and would make one flag mean two things.  If the
  one-goal form ever looks like a mistake, the cheap fix is to reject arity 1 in
  `checks.cpp` alone; that is not proposed now.
- The retired-name advice and this change meet in one place (see the deliverables):
  the message names the *signature* of the replacement, so a variadic `ПЕРВОЕ`
  may want `ПЕРВОЕ(Ц1, Ц2, …)` there.
- `ПЕРВОЕ` in the manual is §4.6; the appendix table (§17) is built from
  `doc/builtins.json` and carries the pair `ПЕРВОЕ`/`first` without arities, so it
  needs no edit beyond the record itself.
