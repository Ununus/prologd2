# task_12 — Built-ins: program database

**Status:** done
**Depends on:** task_07, task_09
**Milestone:** M5

## Goal

Implement runtime inspection and modification of the clause database:
`СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`.

## Deliverables

- [ ] `src/builtins_database.cpp`
  * `СКОЛЬКО(Name,N)`: `Name` must be an atom; count clauses whose head functor
    matches; `N` bound → compare; unbound → bind. Wrong types → error with the
    original message `СКОЛЬКО: Недопустимый тип аргументов`.
  * `ПРЕДЛ(Name,Idx,Head,Goals)`: 1-based clause access, reversible per the
    documented four cases; `Goals` is a list of body goals (empty list for a
    fact); wrong types → fail/error as in the original.
  * `ТЕРМ(Term,List)`: term ↔ `[Functor|Args]` conversion; `[example]` ⇒ atom
    `example`; `[]` is an error; the list head must be an atom or a bound
    variable when building.
  * `ДОБ(Head,Goals,Pos)`: assert a clause at position `Pos`
    (`Pos < 2` or missing clause ⇒ first); `Goals=[]` ⇒ fact; variables in the
    asserted clause are renumbered; inserting into the middle must not corrupt
    enumeration of already-running choice points (use stable clause ids and let
    running enumerations see the snapshot they started with, documenting the
    semantics).
  * `УДАЛЕНИЕ(Name,Idx)`: remove the `Idx`-th clause (`Idx < 0` ⇒ first,
    out of range ⇒ last, as documented).
- [ ] Database changes must be visible to subsequent calls and to `СКОЛЬКО`.

## Design notes

* Clauses are stored in a per-`(name,arity)` vector with stable ids and a
  monotonically increasing generation counter. A choice point records the
  generation it was created in; a retract that invalidates a pending clause
  must either skip it (retract semantics) or keep a snapshot. Choose the
  simplest correct behaviour and document it: **clause vectors are copied on
  write (copy-on-write)**, so running enumerations keep a consistent view.
* `ПРЕДЛ`/`ТЕРМ`/`ДОБ` must use `copyTermResolved` so that terms stored in the
  database share no variables with the caller.

## Tests

- [ ] `test_builtins_database.cpp`
  * `СКОЛЬКО(пример,N)` with the help example (`2`), bound comparison;
  * `ПРЕДЛ(пример,1,X,Y)` → `X=пример(1)`, `Y=[пример(3)]`, and clause 2 →
    `Y=[]`;
  * `ТЕРМ(T,[КОПИЯ,"ПРОЛОГ",X,Y,"ЛОГ"])` → `T=КОПИЯ("ПРОЛОГ",X,Y,"ЛОГ")`,
    reverse direction, `[пример]` → `пример`, `[]` error;
  * `ДОБ` insertion at the front/middle/end, then query order;
  * `УДАЛЕНИЕ` first/last/numbered, then query order;
  * the original `Dob`, `TermDob`, `123` scenarios (after renaming) reproduce.

## Acceptance

All database predicates have passing tests, and asserting/retracting during a
running query behaves as documented.
