# task_105 — a directive completes as the whole statement

**Status:** done (2026-10-24) — ADR-043, part 172
**Depends on:** task_24 (the popup and the insertion), task_104 (the string right
after it completes to a file)
**Milestone:** 2.6.0

## Goal

The owner asked for a "unique" completion of the directive: `ИМ|` should become
`:- ИМПОРТ("|").` — the whole statement, with the caret inside the quotes.

Today `ИМПОРТ` is in the keyword table as a *directive* (no arities), and the popup
offered the bare name: accepting wrote `ИМПОРТ` and nothing else, which is a
sentence that does not parse.

## Decision

A directive is a statement of its own, so it is offered as one:

- `completion.DIRECTIVE_TEMPLATES` — a small table, `ИМПОРТ`/`import` → the text
  and where the caret goes (`:- ИМПОРТ("").`, 11).  The table is the place where a
  future directive with a skeleton of its own goes.
- `Candidate` gained `display` (what the popup shows — the whole statement),
  `skeleton` (what accepting inserts) and `directive` (that it is one).  Matching
  is still by the *name* (`ИМ` matches `ИМПОРТ`), so nothing about the ranking
  changed.
- The editor offers a directive only where a statement can start:
  `completion.at_statement_start(text, position, prefix)` — only whitespace before
  the typed word on that line.  Inside a body the directive candidate is dropped;
  ordinary names are still offered there.
- The caret lands between the quotes, so the very next keystroke is the string
  completion of task_104: `ИМ` → the statement → `iso` → `iso.pld`.

## Checks

- `test_completion.py`: «a directive is offered as the whole statement» — the
  label, the inserted text and the caret, the English spelling, and the
  statement-start rule (a line's start yes, a body no).
- `test_window.py`: the end-to-end case — `ИМ` on an empty line offers the
  statement, accepting writes `:- ИМПОРТ("").` and puts the caret after the opening
  quote; the same word inside a body offers ordinary names only.
- `doc/gui.typ` §5 — the bullet.

29 GUI suites and `protocol_smoke.py` are green; `ctest` untouched (422/422).

## What was deliberately not done

- `ХОЛСТ`/`canvas` keep the bare-name candidate: a canvas template would be a
  different shape (`:- ХОЛСТ(, ).`) and nobody asked for it — the table makes it a
  one-line addition.
- the template has no trailing newline: the statement is inserted where the user
  is typing, and the line end is theirs to decide.
