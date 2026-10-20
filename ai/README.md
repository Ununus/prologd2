# AI working folder

**This folder is the working folder of the AI agent, not user documentation.**
It is the single source of truth for the agent working on the `prologd` project:
everything the agent needs to continue the work without the original
conversation lives here.  Users read `doc/` instead — five Typst documents in
Russian; this folder is the record *behind* them: decisions, task breakdown,
measurements, and the journal of what was done and why.

If you are a human reading this folder for the first time, read it in this
order:

1. `plan.md` — goals, architecture, milestones, risks;
2. `decisions.md` — architecture decision records, numbered, with rationale;
3. `conventions.md` — coding, testing, error and documentation conventions;
4. `reference_notes.md` — distilled semantics of the original PrologD;
5. `status.md` — living progress tracker: the task table first, then the
   journal in parts, oldest first (the tail is the current state);
6. `task_NN_*.md` — one file per task (scope, deliverables, tests, acceptance
   criteria); `porting_notes.md` maps the old lesson files to the new ones.

The folder itself is under version control, like the rest of the repository:
only `ai/_ref/` (the local reference copy) and `ai/_venv/` are ignored, so notes
are committed together with the work they describe.

## Task workflow

1. Read `plan.md` and `status.md`.
2. Pick the next `task_NN_*.md` that is not `done`, and read its **Depends on**
   section first; never start before the dependencies are `done`.
3. Implement, add tests, run the full suite (`ctest --test-dir build/windows-msvc
   -C Release`; the Python suites need `QT_QPA_PLATFORM=offscreen` and
   `PYTHONIOENCODING=utf-8`).
4. Update `status.md` with a journal part and the task status line.
5. Record any non-obvious choice in `decisions.md`.

## Source material

No copy of the reference material is kept in `ai/`.  The previous implementation
of PrologD — the original CP1251 sources (`prlib/*`: terms, scanner, control
machine, built-ins), the plain-text user help, the lesson examples, the
`TEST`/`INPUT`/`EXPECTED`/`END` regression corpus and the Qt GUI — is published
at <https://github.com/Ununus/prologd>; consult it there.  The Qt GUI is the
boundary kept for the front-end (`task_20`).

`НАЙТИВСЕ/3` (`findall/3`) is the one predicate that did not exist in the
original; it was an explicit requirement of this rewrite (`task_13_findall.md`,
`examples/findall.pld`).

`_ref/` is a local, git-ignored copy of parts of that implementation, kept for
reference while porting — today mainly the previous front-end
(`_ref/prolog/src/gui/`, task_22–task_31).  It is *not* part of the repository:
do not link to it from anything that ships, do not commit it, do not edit it.

## Language rules for this project

* Everything in `ai/`: **English** — prose, headings, journal parts, notes.
* Code comments and CLI strings: **English**.
* User documentation (`doc/*.typ`), lesson texts and diagnostics: **Russian**.
* Language surface syntax: standard Prolog, with Russian built-in predicate
  names (see `decisions.md` and `prologd-diff.typ`).

Russian therefore still appears inside this folder, but only as *quoted data* of
the language under test, never as prose:

* built-in predicate names and operators: `НАЙТИВСЕ`, `ВЫП`, `НЕ`, `mod`;
* interpreter and compiler messages quoted in a test: `непарные скобки`,
  `Превышен предел решений НАЙТИВСЕ: 50`;
* file and test names: `lesson_07_данные.txt`, `test_queries.py`;
* the words the CLI prints and the keywords `--list-keywords` reports.

Such spellings are the subject matter and must not be translated.  Everything
else — including the journal parts written before this rule existed — is being
translated into English file by file.
