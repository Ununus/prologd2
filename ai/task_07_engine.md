# task_07 — Resolution engine: backtracking, cut, meta-call, negation

**Status:** done
**Depends on:** task_05, task_06
**Milestone:** M3

## Goal

Implement the search engine with deterministic, standard cut semantics and
nested solves.

## Deliverables

- [ ] `include/prlib/engine.hpp`, `src/engine.cpp`
  * `Engine` owning `Database`, `Bindings`, symbol table, I/O streams, options.
  * `Solution` enumeration API:
    ```cpp
    using SolutionHandler = std::function<bool()>;  // return false to stop
    bool Engine::solveGoals(std::span<const Term> goals, const SolutionHandler&);
    ```
    Callback-based so callers can stop early (needed by `НЕ`, `ВЫП`).
  * Environment stack and choice-point stack per ADR-004.
  * Built-in dispatch table: `(name, arity) -> BuiltinFn`, checked before user
    clauses.
- [ ] `src/engine_control.cpp`
  * `!` cut, `ЛОЖЬ`, `ВЫП/1` (transparent), `НЕ/1` (nested solve + unwind),
    `ИЛИ/2` (library clauses), `РАВНО/2` (library clause or native unify).
  * Clause order: source order per functor/arity; first-argument indexing may
    be added later behind a flag, but must not change solution order.
- [ ] `include/prlib/trace.hpp`, `src/trace.cpp` — optional trace sink for
  `ТРАССА`/`НЕТ_ТРАССЫ` (`Согласуется с`, `Успех`, `Неудача`, `Переделка.
  Цель`, `Цель`, `Неудачна`), printable through the I/O layer.
- [ ] `src/query.cpp` — running a parsed query, printing solutions and
  `ДА`/`НЕТ`, respecting `ТИХО`.

## Design notes

* Each environment stores: goal vector, current index, choice-point barrier and
  `committed`. Choice points store: environment depth, environment goal index
  for each level down to the call, next clause index, trail mark.
  Simplest correct implementation: a choice point copies the *suffix* of the
  environment stack it needs; document the complexity and optimise later if
  needed.
* Fresh variables for a clause attempt are created when the clause is selected
  and trailed so that they become unbound again on backtracking.
* Deep recursion must not overflow the C++ stack: the main loop is iterative.
  Nested solves (`НЕ`, `НАЙТИВСЕ`) do recurse; impose a configurable depth
  limit with `ErrorCode::StackOverflow` (28).
* Execution budget/interrupt hook: a `std::function<bool()>` `shouldStop` checked
  periodically, mapped to `ExecutionInterrupted` (27); used by the CLI for
  Ctrl+C and by tests to avoid hangs.

## Tests

- [ ] `test_engine_basic.cpp`: facts, rules, conjunction, queries, `ДА`/`НЕТ`,
      variable reporting order.
- [ ] `test_engine_backtracking.cpp`:
      * multiple solutions in clause order;
      * nested goals re-enumerated;
      * failing goal forces backtracking;
      * `соединить(x,y,[1,2])` yields exactly 3 solutions
        (`x=[];y=[1,2]`, `x=[1];y=[2]`, `x=[1,2];y=[]`);
      * `member/2` over `[1,2,3]` yields 3 solutions.
- [ ] `test_engine_cut.cpp`:
      * cut commits to the clause (`фактор(7,ф)` == 5040 via `!`);
      * cut blocks alternatives of earlier goals in the same call;
      * cut inside `ВЫП` affects the caller;
      * green cut leaves solution order intact.
- [ ] `test_engine_negation.cpp`: `НЕ` succeeds when the goal fails, fails when
      it succeeds, leaves no bindings, and is transparent with `РАВНО`.
- [ ] `test_engine_deep.cpp`: recursion depth 100000-tail-like loop does not
      crash (bounded by the interrupt hook).

## Acceptance

All engine tests pass; the `соединить` example from the original help produces
exactly the documented three solutions, and the `!` example produces only one.
