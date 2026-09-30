# task_00 — Reconnaissance and plan

**Status:** done
**Depends on:** —
**Milestone:** M0

## Goal

Study the original PrologD interpreter and produce the working plan and task
breakdown in `ai/`.

## Deliverables

- [x] `ai/README.md`
- [x] `ai/plan.md`
- [x] `ai/conventions.md`
- [x] `ai/reference_notes.md`
- [x] `ai/decisions.md`
- [x] `ai/task_*.md`
- [x] Previous PrologD implementation reviewed (<https://github.com/Ununus/prologd>)

## Evidence collected

- `prlib` structure: terms (`pstructs`), scanner (`scaner`, `functions`),
  control machine (`control`), built-ins (`extfunc`).
- Full user help studied (original `prologd-help.txt`).
- Lesson programs and original test corpus reviewed.
- The `НАЙТИВСЕ/3` requirement reviewed.
- Toolchain: GCC 15.2, CMake 4.2, Ninja 1.13, Python 3.14, network available.
- Boost not installed; Boost.Multiprecision standalone build fails (needs
  Boost.Config) → own `BigInt` (ADR-003).

## Acceptance

The task files together form an executable plan: every requirement of the
original request maps to at least one task, and dependencies are stated.
