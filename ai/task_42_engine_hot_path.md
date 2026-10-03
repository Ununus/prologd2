# task_42 — the hot path: allocations per goal, clause indexing, term weight

**Status:** done — stage 1 landed; stages 2 (indexing) and 3 (interning)
measured/deferred with numbers (see the Result below and ADR-017).
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

- [x] Stage 1 — no allocations per goal: the two lookups above.  Behaviour must
      not change at all (same clauses in the same order, same diagnostics).
      Landed; the interleaved before/after is in the Result.
- [x] Stage 2 — measure, then decide on clause indexing: the bench script must
      include a program with many facts *and* a program with a few expensive
      clauses (a river crossing or a puzzle from the lessons), because indexing
      wins where the clause body is heavy.  The deliverable is either the index
      with numbers, or a paragraph in `ai/decisions.md` saying it was measured
      and deferred, with the numbers that made the case.  Deferred — ADR-017.
- [ ] Stage 3 — atom interning and the term layout, only if measured and only
      with the whole suite green at every commit: `Term` gains an atom id
      (a `CompoundTerm` stores ids, not names), comparison of functor names
      becomes an integer compare, and the `std::string` leaves the common cases.
      This is the one change in the task that can ripple into `term_print`,
      `big_int` conversions and the tests' expectations, so it is planned as a
      sequence of mechanical steps, not a rewrite of the engine.  Left
      unticked on purpose: not attempted, and the Result records the measurement
      that bounds what it could buy.
- [x] `tools/bench_engine.py` grows the two indexing workloads and prints a
      before/after table; the numbers of every stage go into `ai/status.md` and
      into `doc/technical.typ` where the design is described.
- [x] No behaviour change anywhere: the lessons' `%!` output, the CLI
      diagnostics and the GUI tests must be identical, which the suite proves.

## Result (2026-09-30)

**Stage 1 — landed.**  `findBuiltin` no longer builds a `BuiltinKey{std::string,
arity}` per goal (the table is keyed by `string_view`; every name in it is a
string literal), and `Database` no longer builds a `"name/arity"` string per
lookup: it is a two-level map (`name -> (arity -> clause list)`, looked up with
`std::less<>`, so a `std::string_view` finds a `std::string` key in place) and the
`key_order_` prefix scans went with it.  Interleaved runs (six pairs; the old
binary built from HEAD with the change stashed; same script, same machine):

| workload | before | after |
|---|---|---|
| dispatch 100 000 steps | 1.45 s (1.43–1.47) | 1.40 s (1.35–1.43) |

Every pair came out faster, by 0–7 %, median ≈ 4 %.  The workload is 14 trivial
built-in goals plus one user goal per step — the most dispatch-bound program in
the suite — and the saving is the ~40–70 ns of string work per goal.  On every
other workload the difference is inside the run-to-run spread (recursion
400 000 steps 1.59 s, 100 000 0.45 s; a list of 60 000 cells 0.25 s; 100 000 facts
0.31 s first / 0.33 s last; structured facts 0.25 s; queens 8 0.29 s).

**Stage 2 — measured, deferred.**  See ADR-017: a full scan of 100 000 clauses
costs ≈ 20 ms (≈ 0.1–0.3 µs per failed head attempt), lesson-scale predicates
have a handful of clauses, and the queens workload is the shape an index cannot
prune (heavy bodies behind shallow-matching heads).  *The scan figure is wrong
and was corrected on 2026-10-03: both quoted runs scanned the whole list, so their
difference was noise; isolated with a cut the scan costs ≈ 50 ms (≈ 0.5 µs per
attempt).  See ADR-017.*

**Stage 3 — not attempted, and the numbers say why.**  The whole per-goal lookup
class was worth ≈ 4 % on the most favourable program in the suite; interning
atoms and splitting the `Term` payload attacks a fraction of that (name
comparisons inside unification), while touching `term.hpp`, the printer, the
`ДОБ`/`НАЙТИВСЕ` copy path and every test that names a term.  Revisit when a
profile shows string comparison or term copying as a hotspot — no workload in the
suite does today.

**Instrument.**  `tools/bench_engine.py` grew the `dispatch`, `structured` and
`queens` workloads and an `--only` filter.  A before/after needs the old binary:
`git stash push -- src/prlib`, build, copy `prologd.exe` aside, `git stash pop`,
build again — and then *interleave* the runs: the machine drifts between sessions
by more than the effect being measured (the first attempt compared runs from two
sessions and saw nothing).

**Behaviour.**  223/223 ctest, 210 Catch2 cases / 3 276 assertions, the headless
GUI suite and the lessons' `%!` output unchanged; `examples/` untouched.

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
