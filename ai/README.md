# AI working folder

This folder is the single source of truth for the AI agent working on the
`prologd` project. Everything an agent needs to continue the work without the
original conversation lives here.

## Contents

| File | Purpose |
|------|---------|
| `README.md` | This index: how to navigate the folder and what the workflow is. |
| `plan.md` | Master plan: goals, architecture, milestones, risks. |
| `conventions.md` | Coding, testing, error and documentation conventions. |
| `reference_notes.md` | Distilled semantics of the original PrologD (predicates, types, quirks). |
| `decisions.md` | Architecture decision records (ADR) with rationale. |
| `status.md` | Living progress tracker (updated after each work session). |
| `task_*.md` | One file per task: scope, deliverables, tests, acceptance criteria. |
| `maybe/*.md` | Ideas that are researched but not scheduled: the analysis, the decision taken so far, and what a task file would have to say.  Empty at the moment — the English-alias idea lived here and became `task_39_english_aliases.md`; the next parked idea goes in the same place. |

The folder itself is under version control, like the rest of the repository: only
`ai/_ref/` (the local reference copy) and `ai/_venv/` are ignored.  Notes are
therefore committed together with the work they describe.

## Task workflow

1. Read `plan.md` and `status.md`.
2. Pick the next `task_NN_*.md` that is not `done`.
3. Read its **Depends on** section; do not start before dependencies are `done`.
4. Implement, add tests, run the full test suite.
5. Update `status.md` and the task status line.
6. Record any non-obvious choice in `decisions.md`.

## Source material

No copy of the reference material is kept in `ai/`. The previous implementation
of PrologD — the original CP1251 sources, the user help, the lesson examples,
the regression corpus and the Qt GUI — is published at
<https://github.com/Ununus/prologd>; consult it there.

* `prologd-help.txt` – plain-text user help (English filenames, Russian text)
  describing the language and every built-in predicate.
* `prlib/*` – the original CP1251 interpreter (terms, scanner, control machine,
  built-ins).
* `examples/lessons/*.pld` – example programs, written in the *old*
  single-letter-variable dialect.
* `prologd_test/test.txt` – original test corpus (`TEST`/`INPUT`/`EXPECTED`/`END`).
* the Qt GUI – the boundary kept for the future front-end (`task_20`).

`НАЙТИВСЁ/3` (`findall/3`) is the one predicate that did not exist in the
original; it was an explicit requirement of this rewrite. Its examples are
quoted in `task_13_findall.md` and in `examples/findall_demo.pld`.

`_ref/` is a local, git-ignored copy of parts of that implementation, kept for
reference while porting — today mainly the previous front-end
(`_ref/prolog/src/gui/`, see task_22–task_31).  It is *not* part of the
repository: do not link to it from anything that ships, and do not edit it.

## Language rules for this project

* Markdown and AI docs: **English**.
* Code comments and CLI strings: **English**.
* User documentation (`doc/*.typ`): **Russian**.
* Language surface syntax: standard Prolog, with Russian built-in predicate
  names (see `decisions.md` and `prologd-diff.typ`).
