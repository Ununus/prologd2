# task_43 — the rest of the standard surface

**Status:** not started
**Depends on:** task_39 (the English spellings: `call/N` and the module warning
are the same "looks like ordinary Prolog" work), task_40 (the module-collision
report is a warning, and warnings are what task_40 introduces)
**Milestone:** M14

## Goal

Three small gaps the review of 2026-09-30 found between this dialect and what a
reader of ordinary Prolog expects, none of them a language-semantics change of
the size task_41 has.

## Deliverables

- [ ] **`ВЫП/2..N` (`call/N`).**  Today only `ВЫП/1` exists
      (`kEngineCallables`, answered by the engine, transparent to the cut).
      `call(P, A1, A2)` must append the extra arguments to the goal `P`
      (an atom becomes a compound; a compound gets the arguments added; the
      result must be a callable goal, otherwise the usual «Цель должна быть
      предикатом»).  Tests: `call/2` on a user predicate, `call/3`, a module
      qualifier-shaped use (`ВЫП(член(Х), [1, 2])` is still arity 1 — the
      argument order of `call/N` is the goal *first*), a non-callable first
      argument, cut transparency (`call((!, ...))` — decide and pin it), and the
      `step`/`trace` hooks reporting the expanded goal, not `call` itself.
      Docs: `doc/help.typ` §4.3 (its `ВЫП` section) and the alias table in
      task_39 (`call`, arities 1..N).
- [ ] **A warning when two imported files define the same predicate.**  `ИМПОРТ`
      merges everything into one global database, so a name clash between two
      files silently becomes one predicate with more clauses — this is exactly
      what made the old lessons 8–9 unrunnable, and the diamond example
      (`examples/diamond/`) shows the *wanted* case of one module loaded once.
      A clause knows its file (`Clause::location`), so after loading, a predicate
      whose clauses come from two different files can be reported with both
      paths and the clause count.  Tests: two files defining `член/2` → one
      warning naming both; the same file imported twice (the diamond) → silence;
      a file adding clauses to an imported predicate (the intended extension
      pattern — decide whether that is a warning or a note) → pinned behaviour.
      Docs: `doc/help.typ` §8 (modules) and `src/gui/README.md` is untouched
      (diagnostics travel as `error` events with a severity).
- [ ] **Remove the dead library.**  `Engine::initialize()` loads six clauses
      into the database (`НЕ`, `РАВНО`, `МЕНЬШЕ`, `СЛОЖЕНИЕ`, `ПС`, `ДЛИНА`; the
      two `ИЛИ` clauses left with the rename, task_44), and *every* one of those
      names is also in the dispatch table.
      `Solver::resolveGoal` consults `findBuiltin` first, so they can never be
      selected: they only show up where the database is read directly.  Measured:
      `?СКОЛЬКО(НЕ, А)` answers `А=2` and `?СКОЛЬКО(ДЛИНА, В)` answers `В=1`,
      while the calls themselves are answered by the built-ins — a learner
      asking «сколько предложений у НЕ» gets a number that does not describe
      anything callable.  Delete the library (the built-ins are the definitions)
      and pin it with a test that those predicates now report no clauses;
      `ai/decisions.md` records the one-line reason.  If a bootstrap is wanted
      for a future build without a dispatch table, it belongs in a file with a
      comment saying exactly that and must not be loaded by default.
- [ ] Optional, if the three above go quickly: what `ТРАССА` should call the
      frame a `;` branch runs in (a redo across the disjunction prints the whole
      `(A ; B)` as the goal today) --- decide together with task_41's cross
      reference.  The library halves of the old `ИЛИ` left with task_44, so
      nothing in the trace says `ИЛИ` any more.

## Acceptance criteria

1. `call/2..N` works for atoms and compounds, refuses non-callables with the
   existing diagnostic, and does not change the cut behaviour of `call/1`.
2. Two imported files with a clashing predicate produce one warning that names
   both files and the predicate; the diamond example stays silent.
3. `?СКОЛЬКО(НЕ, А)` no longer reports clauses nobody can call, and no test
   depends on the removed library (the full suite is green).
4. Every deliverable carries its tests and its documentation line in the same
   change, as `ai/conventions.md` requires.

## Risks and notes

* `call/N` is a *language addition*, not a rewrite: the expansion can be done in
  `Solver::resolveGoal` next to the existing `ВЫП/1` case, and the arity list has
  to appear in the keyword table (`kEngineCallables`) so the GUI offers and
  colours it, exactly like `ВЫП/1`.
* The module-collision warning must not fire for the common, wanted pattern of a
  file that *extends* an imported predicate; if the line between "extension" and
  "clash" cannot be drawn cheaply, report it as a note that names both files and
  lets the reader decide, which is still far better than today's silence.
* Deleting the library is a small change with a user-visible effect on
  `СКОЛЬКО`/`ПРЕДЛ`; it is listed here with the measurement so nobody has to
  re-derive why it was there.
