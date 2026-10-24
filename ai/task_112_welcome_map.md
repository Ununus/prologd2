# task_112 — the welcome is a map of the window

**Status:** done (2026-10-24) — ADR-048, part 178
**Depends on:** task_79 (two engines), task_105/task_106 (the statement forms the
text shows), task_111 (the kinds bug that hid them after the first run)
**Milestone:** 2.6.0

## Goal

The first tab used to hold a bare example program.  The owner wanted it to be a
short map of the *window*: the most useful commands, one line each, and a program
whose every line shows something.  Their draft is `ai/_ref/intro_draft.pld`; a
build with the original engine alone must not show the part it cannot run.

## The text

`WELCOME_OURS` = four lines of our engine's own features (the standard library,
`ИМПОРТ`, `F12` over both, the ISO `length` asked with a variable answer), then
`WELCOME_COMMON` — the window's commands (`F5`/`Ctrl+R`, `Shift+F5` and its two
colours, `Ctrl+N`, `Ctrl+E`, `Ctrl+\`), the completion hint, the comment that shows
up in the popup, and two questions: the students, and the one clicked in the margin
whose answer lands in the table.

`welcome_text(ours_present)` chooses: `paths.engine_present(engines.OURS, folder=
self._engine_folder)` is what the window already uses for «is our engine in this
build», so the package `d` gets the common text without a flag in the packaging
script.

## Edits to the owner's draft

- `—` replaced with `-` everywhere, comments included: the original dialect refuses
  `—` even inside a comment, and the text is a `.pld` program a reader may save.
- «подключет» → «подключает».
- the tab-aligned continuation line became two spaces.
- `Д` kept as a one-letter variable: it is one in both readings, so the text needs
  no `:- ИМЕНА(0).` and does not depend on the «Имена переменных» row.

## Where the standard library has to come from

`ИМПОРТ("iso.pld")` works in a portable package (the engine looks for `stdlib`
beside its executable) and in a checkout needs that folder on the import path — a
build-tree `prologu.exe` has no `stdlib` beside it.  The check therefore fills
`import_paths` with the repository's `stdlib` before running the full text; the
common text runs with nothing filled in.

## Checks

- `test_window.py`: the common text is run on **both** engines and the outputs are
  compared (unchanged promise), the whole text is run on ours with the library on
  the path (`Д=3`), and a folder holding only `prologd.exe` shows the common text —
  no `ИМПОРТ` in it, but the window's own hints still there.
- `doc/gui.typ` §2: the program is no longer quoted (the owner's call — the manual
  describes the features already); the paragraph says what the first tab holds and
  why a `d` package shows less.

29 GUI suites and `protocol_smoke.py` green; `ctest` 423/423.
