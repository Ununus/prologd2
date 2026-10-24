# task_106 — every statement names its own skeleton

**Status:** done (2026-10-24) — ADR-044, part 173
**Depends on:** task_105 (the table and the statement-start rule), task_104 (the
file name after `ИМПОРТ("…")`)
**Milestone:** 2.6.0

## Goal

The owner asked for the rest of the directives after `ИМПОРТ`:

- `ХО|` → `:- ХОЛСТ(|, ).` — the canvas takes the height and the width;
- `ИМ|` → `:- ИМЕНА(|).` — the names marker.

## What was wrong

`ИМПОРТ` was the only name with a template, so `ХОЛСТ` fell through to the bare-name
candidate: accepting it wrote `ХОЛСТ`, a statement that does not parse.  `ИМЕНА` is
not a directive at all in the keyword table — it is the *callable* builtin
`ИМЕНА/1`, so the popup offered `ИМЕНА/1`, and calling it is an error: the builtin
exists only to say «режим имён задаётся первой строкой файла: `:- ИМЕНА(0|1|2).`».

## Decision

`DIRECTIVE_TEMPLATES` became `STATEMENT_TEMPLATES`, keyed by name and consulted
*before* the arities, so a name in it has no call form to offer.  An entry is a
`Statement(template, first_line)` whose template marks the caret with `|`:
`':- ИМПОРТ("|").'`, `':- ХОЛСТ(|, ).'`, `':- ИМЕНА(|).'`, and the English
`import`/`canvas`.  The mark is read once at import time, so the caret needs no
arithmetic.

`ИМЕНА` is `first_line`: `completion.at_file_start(text, position, prefix)` asks
whether the word opens the file, and the editor drops the marker candidate below the
first line.  That is the loader's own rule — `readVariableMarker` reads the first
line and nothing else — and it also keeps `ИМ` meaning `ИМПОРТ` everywhere below.

## Checks

- `test_completion.py`: the four skeletons and their carets, the `first_line` flag,
  `at_statement_start` vs `at_file_start` on the same word.
- `test_window.py`: `ХОЛ` inserts `:- ХОЛСТ(, ).` with the caret before the comma;
  `ИМ` on one line offers the marker, `ИМ` on the second line does not, while the
  directive does; a body still offers neither.
- `doc/gui.typ` §5 — the bullet rewritten.

29 GUI suites and `protocol_smoke.py` are green; `ctest` untouched (422/422).

## What was deliberately not done

- `variables` gets no template: the marker reader knows `ИМЕНА` only.  Checked on
  the engine — `:- variables(0).` on the first line fails with the marker's own
  error (exit 3), `:- ИМЕНА(0).` loads.  The alias is still offered as a call, which
  belongs to the alias table, not this one.
- the template still writes no newline: the line end is the user's.
