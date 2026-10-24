# task_109 — a saved buffer's path, and a tab the window filled itself

**Status:** done (2026-10-24) — part 176 (fixes of task_68/task_101/task_108)
**Depends on:** task_68 («Показать в проводнике»), task_101 (`_show_converted`),
task_108 (the closing question)
**Milestone:** 2.6.0

## The owner's reports

1. After saving a «Без имени» buffer to disk, «Показать в проводнике» does not work
   on that file.
2. The asymmetry between a file the user edits and a program a script writes showed
   up as a bug: the edited buffer is marked changed and is offered a save; a script
   tab is not marked at all, so even a text too big for the session closed without a
   question (checked with a picture converted at full detail — one pixel, 32
   colours — and saved aside as `_ref/too_big_to_fit.pld`).

## What was wrong

**1. Two spellings of one path.**  `QFileDialog` answers with forward slashes
(`C:/dir/файл.pld`), and `Document.rename` stored the string as it came.  A file
*opened* from the same dialog went through `str(pathlib.Path(path))` in `open_path`
and was native, which is why only a saved buffer went wrong.  Two consequences: the
title bar showed a path no other tab had, and the file manager got
`/select,C:/dir/файл.pld` — `explorer` reads that as neither a switch nor a file.
Fixed in `Document.rename` (`os.path.normpath`), and `paths.reveal_command`
normalises too, so the command cannot be built from a non-native spelling again.

**2. `setPlainText` clears the «unsaved» flag.**  A tab filled by the window
(`_show_converted`, `convert_image`) went through `setPlainText`, so Qt considered
it untouched: no star, and — the real harm — `_confirm_close` skipped it before even
looking at the size, because its first question is `is_modified()`.  A converted
program is unsaved work by definition: it exists in the tab and nowhere else.
`Buffer.mark_modified()` is the counterweight to `mark_saved()` and both places use
it.

**3. The entry was never refreshed.**  `reveal` was enabled only while a tab's
context menu was being built, so it could stay enabled for a «Без имени» (doing
nothing) or stay disabled for a file saved a moment ago.  `_refresh_file_actions`
now answers for the current tab and is called from `_update_details` (every caret
move and tab switch) and from `save_buffer` (the command that gives a buffer its
file); the tab menu uses the same method.

## Checks

- `test_paths.py` — the command is built from the native spelling (spaces and
  forward slashes in the input).
- `test_window.py` — «a saved buffer is named the way the file manager wants»: the
  entry is off for «Без имени», saving through the dialog's spelling leaves the
  native path and the title bar agrees, and the entry is on right after the save.
  «a converted program is unsaved work»: `_show_converted` leaves a starred tab, and
  a text over the session's budget is asked about at close.
- 29 GUI suites and `protocol_smoke.py` green; `ctest` 423/423; the manual builds
  and pages 31–32 were looked at.

## The question that came with the report

«Может стоит сделать Показать в проводнике для Без имени в место где лежит буфер?»
— No, and the reason is in the answer: an unnamed buffer "lives" in the remembered
session, which is an INI key with escaped JSON in it, not a file a reader should be
sent to.  What the entry can honestly say is that there is no file yet, and the
disabled state says it.  A separate command («Открыть папку для сохранения»,
starting where the save dialog would) is possible, but it answers a different
question and nobody has asked for it.
