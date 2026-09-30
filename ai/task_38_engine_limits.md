# task_38 — engine limits: recursion depth, long runs and their memory

**Status:** not started
**Depends on:** nothing (task_34's branch sweep is done)
**Milestone:** M14

## Goal

Two limits of the current engine are not limits but failures.  A correct program
can kill the process, and a long search grows memory linearly with no way to see
it.  This task turns the first into a diagnostic, removes the cause of the
second where that is safe, and pins both with tests — today such a test would
take the whole test runner down with it, which is why the suite says nothing
about either.

## What was measured on 2026-09-30 (before doing anything)

Program: the lesson's `сумма/2` tail recursion, `?сумма(N, С).`  Numbers from
`build/windows-msvc/src/cli/Release/prologd.exe`.

| N | time | peak working set | exit code |
|---|---|---|---|
| 50 000 | 0.27 s | — | 3221225725 (0xC00000FD) |
| 100 000 | 0.55 s | 280 MB | 3221225725 |
| 200 000 | 1.06 s | — | 3221225725 |
| 400 000 | 2.05 s | 1 241 MB | 3221225725 |

* The **answer is printed correctly first** and the process dies afterwards:
  0xC00000FD is `STATUS_STACK_OVERFLOW`.
* The threshold is between 16 000 (fine) and 32 000 (dead) levels.
* It is not the solver loop: the same crash happens with a `!` after the guard
  (so no choice point is kept) and with a 32 000-element list built the same way.
  The cause is that a deep `EnvNode` chain is released *recursively* — each frame
  holds a `shared_ptr` to its parent, so the destructors go down the whole chain
  when the last reference to a deep frame dies (a popped choice point or the
  solver's final environment).
* Memory grows without bound because `Bindings::freshVar` only appends:
  `bindings_` and `names_` are never trimmed (`Bindings::clear` has no caller
  outside tests), so every clause *instantiation* of the whole run leaves its
  variables behind.  ≈ 2.8 KB per recursion step; a search that tries 10^7
  clauses would need gigabytes.
* Time itself is fine: ~5 µs per step, linear — the interpreter is not slow, it
  is *hungry*, and it has no ceiling.

## Deliverables

- [ ] `EngineOptions::maxDepth` (default 10 000 — a lesson needs hundreds, so
      this is generous) checked where the frame depth is already known
      (`EnvNode::depth`, next to the existing `maxSteps` check in
      `Solver::run`), raising `ErrorCode::StackOverflow` with a message that
      names the limit («Превышена глубина рекурсии (лимит 10000)»).  A crash
      becomes a diagnostic with exit code 3, in line with `maxSteps` and
      `maxNestedDepth`.  Optional: `--max-depth`/`--max-steps` on the CLI, next
      to the other limits, and a paragraph in `doc/help.typ` §15.
- [ ] **Iterative release** of a deep chain and of a deep term, so that the
      depth the *stack* can survive stops being a crash: a small `EnvRef`
      wrapper (or a `releaseChain` helper) that keeps a local reference to the
      parent while the child dies, and the same trick for compound terms — for
      a term the walk has to *collect* the path first (the nodes are immutable
      `shared_ptr<const CompoundTerm>`, so nothing can be unlinked in place),
      then let every level go while the worklist still holds the others.
      Use it wherever a deep reference can be dropped: popped choice points, the
      solver's final environment, `Engine` destruction.
- [ ] **Variable growth**: investigate a safe reuse scheme and either implement
      it or write down why not, with numbers.  A safe scheme has a hard
      constraint: a term may outlive the trail mark it was created under (the
      query's own variables, a clause copy that a binding still refers to), so
      plain id recycling is wrong.  Options to weigh: a variable *stack* with
      per-frame marks and reuse only below the frame's mark; owning a clause
      copy's variables in the frame and freeing them with the frame; or, if a
      safe scheme needs the terms to be owned by the frame (a real refactor),
      leaving the growth in place but making it *visible* (a diagnostic past a
      threshold, a `variableCount()` line in the bench output) and documented as
      a known ceiling in `doc/technical.typ`.
- [ ] Tests:
  * a **ctest** case (a separate process, so a stack overflow cannot abort the
    suite) running the CLI on a generated 100 000-deep program and expecting the
    right answer, exit code 0 and empty stderr;
  * the same for a 100 000-element list (term release, not just frames);
  * a ctest case for the limit: depth above `maxDepth` → the diagnostic text,
    exit code 3, no crash;
  * in-process Catch2 tests at a depth the default stack survives (5 000) for
    the answer and for `variableCount()` staying under a bound *if* the reuse is
    implemented;
  * a regression test that the existing lessons still pass unchanged.
- [ ] `tools/bench_engine.py`: the instrument this task measured with, made
  permanent — generates the programs, runs the interpreter, prints time and peak
  working set (ASCII only, like the GUI test scripts), and is what task_42
  measures its optimisations with.  It must not live in `src/tests` (those are
  Catch2 and the GUI scripts); `tools/` already holds `port_lessons.py`.
- [ ] Docs: `doc/technical.typ` gains a section on the environment chain, its
  release, the memory a step costs and the reason there is a depth ceiling;
  `doc/help.typ` documents the limit if the CLI flags are added; `ai/status.md`
  carries the new numbers.

## Acceptance criteria

1. `?сумма(100000, С).` answers and exits 0; `?сумма(400000, С).` too, with the
   peak working set reported by the bench script (it will still grow — the
   *crash* is what must be gone).
2. A 100 000-element list is released without a crash.
3. Depth past the limit prints one clear diagnostic and exits 3.
4. The full suite is green and the bench script reproduces the table above, with
   the "after" column added.

## Risks and notes

* Raising the stack instead (`/STACK:64MB`, or running the solver in a thread
  with a big stack) is a legitimate *second* half of the fix and moves the
  ceiling by an order of magnitude, but it must not replace the diagnostic:
  Windows-specific knobs age badly, and a program that dies silently is worse
  than one that says what it ran into.
* Do not "fix" the memory by clearing `Bindings` between queries: the GUI session
  and the REPL run many queries in one process over one database, and the
  bindings of a finished query are gone only in the sense that nothing refers to
  them.
* Recording a *usage* number (`variableCount()`, peak depth) in the error
  message of the depth limit would make the failure self-explaining; the engine
  already has the counter.
