# task_13 — `НАЙТИВСЁ/3` (findall)

**Status:** done
**Depends on:** task_07, task_12
**Milestone:** M5 (key user-visible goal)

## Goal

Implement the predicate required for this rewrite, matching the stated
requirement exactly (its example is quoted below).

## Required behaviour

```
студент(вова,корчагин).
студент(данил,ахмеров).
студент(ваня,петров).

?НАЙТИВСЕ(И,студент(И,Ф),А).
А=[вова,данил,ваня]

?НАЙТИВСЕ([И,Ф],студент(И,Ф),А).
А=[[вова,корчагин],[данил,ахмеров],[ваня,петров]]
```

That is standard `findall/3`:

* `НАЙТИВСЁ(Template, Goal, List)`;
* enumerate every solution of `Goal`;
* for each solution, take `Template` with the current bindings applied and
  copy it so the collected term shares no variables with the caller or with
  other solutions;
* build a list in solution order;
* undo every binding made by executing `Goal`;
* `List` is unified with the result (so `НАЙТИВСЁ` is deterministic: exactly one
  solution, and it always succeeds).

## Deliverables

- [ ] `src/builtins_findall.cpp`
  * native `НАЙТИВСЁ/3` built-in, registered in the dispatch table.
  * Implementation: `TrailMark m = bindings.mark();` run a nested engine over a
    copy of the goal with a solution callback that resolves+copies `Template`
    into a collector; on completion `bindings.unwind(m)`; then unify `List`
    with the collected list **after** unwinding so the result is ground w.r.t.
    the goal's variables.
  * Solution cap option (`kFindAllLimit`, default e.g. 1'000'000) → error 44
    (`TooLongList`) to prevent runaway memory.
- [ ] Register `НАЙТИВСЁ` in the reserved-name set so it lexes as an atom.
- [ ] Optional alias `FINDALL` if the reserved-name mechanism makes it cheap;
  otherwise document only `НАЙТИВСЁ`.

## Design notes

* `НАЙТИВСЁ` must work even when `Template` contains variables not in `Goal`
  (they become fresh variables in each copy, per standard `findall`: actually
  `findall` requires them to be unbound and each collected copy gets a fresh
  variable).
* Ordering must be the engine's natural solution order.
* The goal's execution must see the caller's current bindings (standard).
* Interaction with `!` inside `Goal`: cut is local to the nested solve.

## Tests

- [ ] `test_builtins_findall.cpp`
  * the two required examples verbatim (expected output above);
  * `НАЙТИВСЁ(X, member(X,[1,2,3]), L)` → `L=[1,2,3]`;
  * empty goal solutions → `L=[]`;
  * template with a free variable: `НАЙТИВСЁ([X,Y], member(X,[1,2]), L)` →
    `L=[[1,_],[2,_]]` with distinct fresh variables;
  * outer bindings are restored: `?РАВНО(Z,0),НАЙТИВСЁ(X,member(X,[1,2]),L)` →
    `Z=0, L=[1,2]`, and any variable bound inside `Goal` is unbound after;
  * nested `НАЙТИВСЁ` calls;
  * interaction with cut inside the goal;
  * solution cap triggers error 44 on an infinite generator with the cap
    lowered for the test.
- [ ] A golden test running a program equivalent to the requirement example
      (`examples/findall_demo.pld`-equivalent data) with the two queries and
      comparing the exact output.

## Acceptance

The required example output is byte-for-byte reproduced (modulo the new
variable-printing rule) and all findall tests pass.
