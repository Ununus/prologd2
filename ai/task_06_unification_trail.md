# task_06 — Unification, bindings and trail

**Status:** done
**Depends on:** task_02, task_03
**Milestone:** M3

## Goal

Implement dereferencing, binding, the trail and unification with the exact
PrologD semantics, including arithmetic-expression evaluation.

## Deliverables

- [ ] `include/prlib/bindings.hpp`, `src/bindings.cpp`
  * `Bindings` owning `std::vector<Binding>` indexed by `VarId` and a
    `std::vector<VarId> trail_`.
  * `const Term* deref(const Term&) const`, `Term resolve(Term) const`.
  * `bool bind(VarId, const Term&)` — binds and trails; fails if already bound
    to a different value (should not happen after deref).
  * `TrailMark mark()`, `void unwind(TrailMark)`.
  * `VarId freshVar(std::string name)`.
- [ ] `include/prlib/unify.hpp`, `src/unify.cpp`
  * `bool unify(const Term& a, const Term& b, Bindings&, const ArithEvaluator&)`.
  * Iterative work-list to avoid deep C++ recursion on long lists.
  * Rules:
    * var/anything → bind (no occurs-check, ADR/notes);
    * atom/atom, int/int, float/float, string/string → identity/equality;
    * int/float → numeric equality with the original tolerance rule;
    * list/list → head and tail;
    * compound/compound → same name and arity, then arguments;
    * expression vs int/float/expression → evaluate and compare per
      `reference_notes.md` §2;
    * `[]` only unifies with `[]`/var.
  * `unifyWithOccursCheck` provided for optional use and for `НАЙТИВСЁ`
    diagnostics (not enabled globally).
- [ ] `include/prlib/copy_term.hpp`, `src/copy_term.cpp`
  * `Term copyTermResolved(const Term&, const Bindings&, Bindings& target)` —
    applies current bindings and renumbers remaining variables fresh; used by
    `НАЙТИВСЁ`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`.

## Design notes

* A binding maps a variable to a term that may itself contain variables; chains
  are resolved by `deref` with path following.
* The trail records only variables that became bound; `unwind` restores them to
  unbound in reverse order.
* Unification performs no side effects outside `Bindings`; callers use
  `TrailMark`/`unwind` to backtrack.
* Numeric comparison of int and float: follow the original expression
  `f - 1 < i && f == (float)i` (document it, even if odd).

## Tests

- [ ] `test_unify.cpp`
  * var binds, repeated var, var-var aliasing, chains;
  * atoms, ints, floats, int/float equality, strings vs atoms;
  * compounds: name/arity mismatch, nested;
  * lists: `[H|T]` with `[1,2,3]`, partial lists, `[]`;
  * expressions evaluated on demand: `#1+1#` unifies with `2`;
  * failure leaves `Bindings` unchanged after `unwind`;
  * `copyTermResolved` produces ground copies and fresh variables.
- [ ] property test: `unify(a,b)` then `unify(b,a)` gives symmetric
      results on generated ground/variable terms.

## Acceptance

All unification tests pass and `НАЙТИВСЁ`'s variable-copy requirement is
satisfied by `copyTermResolved`.
