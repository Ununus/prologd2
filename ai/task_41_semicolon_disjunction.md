# task_41 — `;` as disjunction

**Status:** done (2026-09-30)
**Depends on:** task_40 (the diagnostic for a `;` written as a sentence
terminator is what makes the change safe to land)
**Milestone:** M14

## Goal

Make `;` mean what it means in every other Prolog: a *backtrackable disjunction*
of goals, `(A ; B)` — try A, and on backtracking try B, with both branches
producing all their solutions.  Today `;` is not an operator at all: it is the
second *sentence terminator* (`.`, `;`), inherited from the original PrologD.

## What the change collides with, measured

* **In code**, a `;` terminator appears exactly once in the repository:
  `examples/factorial.pld` (lines 1–3, ported from the original).  The course,
  the examples and `_old/` use `.` only; the many other hits are C++ semicolons
  and prose in comments.
* **In documentation**, `doc/help.typ` §1.1 states the rule ("предложение
  завершается точкой `.` или точкой с запятой `;`") and §1.1's example uses it.
* **`ИЛИ/2` is not a disjunction.**  Measured today:
  `?ИЛИ(p(X), q(X)).` with `p(1). p(2). q(3).` answers `X=1` — one solution.
  `?ИЛИ(РАВНО(X,1), РАВНО(X,2)).` answers `X=1`.  It commits to the first
  solution of its first goal (the library definition `ИЛИ(X, _) :- ВЫП(X), !.`),
  which is if-then-else behaviour, documented as such in §4.5.  A standard `;`
  must give `X=1, X=2, X=3` for the first query, so `;` **cannot** be sugar for
  `ИЛИ/2`.

## Design

* `;` becomes an operator between goals, with `,` binding tighter:
  `A, B ; C, D` is `(A, B) ; (C, D)` — the same precedence as ISO.
* The sentence terminator becomes `.` alone.  A `;` at the end of a statement is
  then a *syntax* error, and the task_40 machinery turns it into a message that
  says what changed («`;` — дизъюнкция; предложение не заканчивается точкой»).
  Keeping the old meaning *only* at the end of a line was considered and
  rejected: it is line-sensitive, and it would silently keep two contradictory
  meanings alive.
* Implementation sketch:
  * parser — `parseGoalList` keeps building the conjunction (it already does,
    `parser.cpp:353`), and a new level parses `;` between those lists, producing
    a `;/2` compound; `(A, B)` as a single goal already works this way (the
    solver expands `,`/2 in place, `Solver::resolveGoal`);
  * solver — a `;/2` goal expands in place to its left operand and pushes the
    right one as an *alternative*; `ChoicePoint` today holds a clause list, so
    this needs either a second kind of choice point or a small
    `pushAlternative(goal)` path.  Both branches must respect the cut barrier of
    the environment they were written in (a cut inside a branch is local to that
    branch), which is the one subtle part.
  * `ИЛИ/2` stays as it is — committed, documented — and gains a cross-reference
    in `doc/help.typ` §4.5 explaining that `;` is the disjunction and `ИЛИ` is
    the if-then-else-like form.  Renaming `ИЛИ` is *not* part of this task.
* `ВЫП((A ; B))` works for free if the meta-call path goes through the same goal
  resolution.

## Deliverables

- [x] Parser: the `;` level, with the same `InvalidGoal` checks the conjunction
      has; `(A ; B)` inside argument lists stays what it is today (an error, as
      in ISO).
- [x] Solver: the alternative choice point, with cut-barrier semantics and the
      step/trace hooks firing for both branches (`step(Redo, …)` on the second).
- [x] `examples/factorial.pld`: terminators changed to `.`; `ai/porting_notes.md`
      records it; `doc/prologd-diff.typ` gets the entry with a before/after
      example.
- [x] `doc/help.typ`: §1.1 rewritten (the terminator is `.`), a new §4.x for `;`
      with the precedence, three examples (both branches, all solutions, a cut
      inside a branch), and the cross-reference from §4.5.
- [x] `ai/conventions.md` if any style follows from it (nothing expected —
      nothing followed).
- [x] Tests: `src/tests/test_parser.cpp` — `a ; b`, `a, b ; c`, `a ; b, c`,
      `(a ; b), c`, a `;` inside a list (an error), a `;` at the end of a clause
      (the diagnostic from task_40); `src/tests/test_engine.cpp` — all solutions
      of both branches in order, failure of both branches, backtracking *into*
      the second branch, a `!` inside one branch not cutting the other, `;`
      under `НЕ` and inside `ВЫП`, and the whole thing through a lesson-style
      query with `%!` expectations.  (The solver cases live in
      `test_builtins_control.cpp`, next to the `ИЛИ` ones, and the two
      diagnostics in `test_diagnostics.cpp`.)
- [x] The GUI needs nothing: `;` is a token it already highlights, and the
      lexer's token kind does not change.
- [x] If the user wants a *runnable* demonstration in the course: a short section
      in an existing lesson (5, lists, or 4, control) rather than a new lesson —
      the course's numbering and the check's list are stable, and adding a query
      to a lesson is a one-line change plus its `%!` lines.  (Lesson 4's section
      on `ИЛИ` became «Дизъюнкция: точка с запятой и ИЛИ» and shows the two
      answers of `;` beside the one answer of `ИЛИ`.)

## Acceptance criteria

1. `?член(Х, [1, 2]) ; Х = 3.`-shaped programs behave as in ISO: every solution
   of the left branch, then every solution of the right.
2. `p(X) :- (a(X) ; b(X)).` with three clauses across `a` and `b` answers three
   times.
3. A `;` as a sentence terminator fails the parse with the task_40 message, not
   with a wrong parse.
4. The whole suite is green and the lessons that do not use `;` are untouched.

## Risks and notes

* This is a **syntax change for a ported dialect**, so `prologd-diff.typ` is the
  contract: the change is deliberate and must be visible in one place.
* The one subtle part is the cut barrier of a branch; the tests above exist to
  pin exactly that, and the stepping hooks must not report a branch as an
  `Exit` of the clause (a branch is a goal, not a clause body — the frames
  already distinguish the two with `EnvNode::goalFrame`).
* Out of scope: `->` (if-then-else) and `*->`.  `ИЛИ/2` covers the committed
  form, and a second operator would need its own decision.

## Result

The syntax change landed as planned, with one deviation and two notes.

* The parser gained a `;` level that swallows the conjunction collected so far
  (`A, B ; C ; D` builds a left-nested `;`/2), and the parenthesised group now
  parses `(A ; B)` the way it already parsed `(A, B)`.  **Deviation:** the plan
  said a `;` inside an argument list stays an error; a *parenthesised*
  `(A ; B)` is allowed there after all, because `ВЫП` and `НАЙТИВСЁ` take their
  goals as arguments and the parser cannot tell a goal argument from data — the
  same line `,`/2 already crosses.  A bare `;` in an argument list is still an
  error, with its own message (`заключите её в скобки: (A ; B)`), as is a `;`
  inside a list (`элементы списка разделяются запятой`).
* The solver expands `;`/2 in place and pushes the right operand as an
  `Alternative` choice point (the struct gained a `Kind`).  A branch runs in a
  frame of its own whose cut barrier sits *above* the alternative, so a cut in a
  branch prunes only what the branch created, and `step(Redo, …)` fires when the
  right branch is entered.
* A `;` where the dialect used to end a sentence is an error with the message
  from task_40's machinery, at the `;` itself.
* `examples/factorial.pld` was the only file in the repository that used the old
  terminator; it now ends its three statements with `.`.
* `doc/help.typ` §1.1, a new §4.5 (`;`) with §4.6/§4.7 renumbered, §4.6's own
  text now calling `ИЛИ` the «если-то» form, lesson 4's section 5 rewritten
  around both forms, `doc/prologd-diff.typ` §16 and the summary table, and
  `ai/porting_notes.md`.
* Tests: six parse shapes, the solver's semantics (both branches and all their
  solutions, the right branch entered only after the left one, both failing,
  the local cut, `;` under `НЕ`, `ВЫП` and `НАЙТИВСЁ`, the comma precedence) and
  two diagnostics (the retired terminator with its position, both branches of a
  disjunction checked for undefined predicates).
* A follow-up made the printer write `,`/2 and `;`/2 infix (`(A ; B)`): a query
  echo, a trace line and a step point used to show `;(a,b)`, which is not what
  the program says.
