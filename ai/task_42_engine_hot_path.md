# task_42 — the hot path: allocations per goal, clause indexing, term weight

**Status:** not started
**Depends on:** task_38 (`tools/bench_engine.py` is the instrument this task
measures with; it also owns the depth/memory work that must land first, or the
numbers here will be measured against a crashing engine)
**Milestone:** M14

## Goal

The engine is not slow — 5 µs per resolution step, measured — but it pays a
constant tax that a WAM-based Prolog does not, and the review of 2026-09-30
listed where.  This task removes the tax *that the benchmark shows* and nothing
else: every change here must be justified by a before/after number, and a change
whose win is inside the noise gets written down as "not worth it" instead of
landing as code.

## Where the tax is (from the review, all verified by reading the code)

1. **A string per built-in call.**  `findBuiltin` builds
   `BuiltinKey{std::string(name), arity}` for every goal that is not a user
   predicate (`builtins.cpp`).  In a tight arithmetic loop this is a heap
   allocation and a string hash per step.  The names are static string literals,
   so a table keyed by `(std::string_view, arity)` costs nothing.
2. **A string per predicate call.**  `Database::key` is
   `std::string(name) + '/' + std::to_string(arity)` (`program.cpp`), built for
   every lookup, which includes every user-predicate goal.  A two-level map
   (name → small vector of `(arity, list)`) or a heterogeneous lookup removes it.
3. **No clause indexing.**  `clausesFor` returns one list per `(name, arity)` and
   the solver scans it linearly.  Measured on 100 000 facts: the first fact
   0.26 s, the last 0.31 s — so at this size the win is small and the *honest*
   answer may be that indexing is not worth it until programs get bigger or
   clauses get more expensive.  First-argument indexing (the SWI-style
   just-in-time index, built once a predicate is called often enough, keyed on
   atom / integer / structure / unbound) is the standard answer.
4. **Term weight.**  `Term` carries a `std::string text` even when it is an
   integer; `CompoundTerm` carries a `std::string name` rather than an interned
   atom id; a `Binding` is a `bool` plus a whole `Term`.  Interning atoms and
   splitting the payload by kind is the real fix — and the real refactor: it
   touches `term.hpp` and everything that names a term.  It belongs to *stage 2*
   of this task and only after stages 1 and 3 have been measured, because the
   numbers will decide whether the churn is justified.

## Deliverables

- [ ] Stage 1 — no allocations per goal: the two lookups above.  Behaviour must
      not change at all (same clauses in the same order, same diagnostics).
- [ ] Stage 2 — measure, then decide on clause indexing: the bench script must
      include a program with many facts *and* a program with a few expensive
      clauses (a river crossing or a puzzle from the lessons), because indexing
      wins where the clause body is heavy.  The deliverable is either the index
      with numbers, or a paragraph in `ai/decisions.md` saying it was measured
      and deferred, with the numbers that made the case.
- [ ] Stage 3 — atom interning and the term layout, only if measured and only
      with the whole suite green at every commit: `Term` gains an atom id
      (a `CompoundTerm` stores ids, not names), comparison of functor names
      becomes an integer compare, and the `std::string` leaves the common cases.
      This is the one change in the task that can ripple into `term_print`,
      `big_int` conversions and the tests' expectations, so it is planned as a
      sequence of mechanical steps, not a rewrite of the engine.
- [ ] `tools/bench_engine.py` grows the two indexing workloads and prints a
      before/after table; the numbers of every stage go into `ai/status.md` and
      into `doc/technical.typ` where the design is described.
- [ ] No behaviour change anywhere: the lessons' `%!` output, the CLI
      diagnostics and the GUI tests must be identical, which the suite proves.

## Acceptance criteria

1. Each landed stage shows a measured before/after from the same script on the
   same machine, and the summary is written into the task file and
   `ai/status.md`.
2. Any stage that turns out to be a wash is written down as such — with the
   measurement — instead of being kept "because it is obviously better".
3. `ctest` and the headless GUI scripts are green; `examples/` is untouched.

## Risks and notes

* The tempting big win is a different engine (bytecode or WAM).  It is out of
  scope on purpose: the programs this interpreter runs are lessons and puzzles,
  the measured time is already small, and a rewrite would put the language's
  *semantics* at risk — the one thing that is currently right.
* Indexing interacts with the copy-on-write snapshot of the database: a choice
  point keeps the `ClauseListPtr` it saw, so the index has to live in the same
  snapshot (or be rebuilt per snapshot) before a running enumeration can use it.
* Interning changes `Term` equality in ways the tests rely on (`structurallyEqual`
  compares text today).  Do it behind the existing helpers, not by rewriting
  every call site, and keep a `text` fallback for atoms that came from the user's
  source until the last step.
