# task_29 — GUI: settings dialog and persistence

**Status:** done (round B, 2026-10-01) — the dialog, the described table, reset,
import/export and the "almost ready" new keys; the two items that grew into
`task_45_gui_graphics_window.md` and `task_46_interpreter_options_and_limits.md` are named
below, and **RU/EN was dropped by decision** (2026-10-01, ADR-021: the window stays Russian).
**Depends on:** task_22 (font, line numbers), task_26 (view actions), task_27 (panels)
**Milestone:** M11

## Goal

One place for everything the user can configure, with the values surviving a restart.  The
requested settings are the line numbers and the font size; the rest of the list is what the
surrounding features make necessary or obviously worth having.

## Storage

* `prologd_gui/settings.py` — a Qt-free description of every setting (name, type, default,
  bounds) plus a `QSettings`-backed store using `QSettings.IniFormat` in
  `QStandardPaths.AppConfigLocation` (`%APPDATA%\PrologD\gui.ini`), with `--settings FILE` on
  `main.py` to point somewhere else (a portable install, a test).
* Unknown keys are preserved (a newer version's settings must not be dropped by an older
  one), broken values fall back to the default and are reported in the log, and
  «Настройки → Сбросить» restores the defaults.
* Import/export to a file, so a configuration can be moved between machines; «Экспорт…»
  writes the whole file and «Импорт…» reads it, unknown keys and all.

## Settings

**Editor** — line numbers on/off (the requested one) and "highlight the current line"
(`editor/current_line`); font family (monospaced first, Cyrillic-capable) and size 6…72,
with the current scale on `Ctrl`+wheel; tab width, "tabs or spaces", auto-indent — since
2026-10-01 `Enter`'s indent is the switch `editor/auto_indent` (on, the behaviour it always
had, but switchable), while the indent *unit* stays with `Tab`; word wrap on/off;
completion on/off, after how many letters, case-sensitive
(`editor/completion_match_case`); autosave (an interval, `files/autosave_minutes`).

**Highlighting** — colours per token kind, with **Latin** and **Cyrillic** separately
(task_22), light/dark and "use the system colours".  `light` and `system` already existed
(`--theme`, task_22); a **dark** theme is not a switch but a second syntax palette — bright
colours for a dark background — and the palette must keep WCAG contrast 4.5 against its own
background (`theme.contrast_ratio`).  Done 2026-10-01: `theme.Palette` is one record per
theme ("page + highlighting + bands + line-number band + output colours"), `LIGHT` and
`DARK`; `appearance.qt_palette` turns it into a widget palette, and the editor fields, the
bands and the output pane read the same record.  The 4.5 contrast is checked for **both**
palettes over the list `Palette.readable_pairs`, against the page each colour is drawn on
(`test_appearance.py`); that check also found that the trace colour of the light theme was
4.48 — a shade too dark — and made it clean (4.61).  "Use the system colours" was done in
the same round: "as in the system" takes the desktop's colours for the widgets *and* for the
highlighting.

**Formatting** — the mode (`в одну строку` / `мягкое` / `жёсткое`, task_30; "не менять"
became "в одну строку" on 2026-10-01), the line width for the soft mode, the indent (in
tabs, 2 by default) and "format the selection only".

**Output** — the pane at the bottom or on the right, the output font size (separate from the
editor), a line limit (`output/line_limit`, applied at once: a smaller limit trims),
"print questions" and "follow the output" (`view/follow_output`).  Until
`output/font_size` is set, the pane follows the editor as before; the wheel over the pane
separates it for good.  The font family stays one for the whole window — the output pane is
monospaced and a second family buys nothing.

**Execution** — the interpreter path (still `--exe`), save before running, the request
timeout and the `НАЙТИВСЕ` cap; the limits were done in `task_46` — four rows under
"Выполнение" (`execution/max_steps`, `max_depth`, `max_findall`, `timeout_seconds`) and the
`limits` key of `load` (protocol 9).  The **working folder** is the one directory the user
keeps shared sources in: it is passed as `-I` on every session, so `ИМПОРТ("library.pld")`
works from any program, saved or untitled, and pointing it at `examples/lib` is the
out-of-the-box example.  It is a *search* directory, not the working directory of the
process, and it is appended after the importing file's own directory, so a local `lib/x.pld`
always wins over a same-named file in the shared folder.  Beside it:
**additional import directories** (`-I`, repeatable, `execution/import_paths`) and the
**process working directory** (`execution/working_directory`) — `каталог файла` (the default
for a saved file) or `рабочая папка` (the default for «Без имени»).  The process working
directory is what `ЗАПИСЬ_В("out.txt")` and `ЧТЕНИЕ_ИЗ` are relative to, and it is shown in
the status bar so the two are not confused; it needed a *session* key, not another dialog
row, so it stayed where it was.  Input is answered in the panel or in dialogs
(`view/input_mode`: "в панели" by default or "в диалоге"), independently of whether the
panel is visible — before 2026-10-01 only the panel's visibility decided that.

**General** — "report where an import was searched for" (`task_32`, on by default; done
there, and it has no switch on purpose: the message appears only on an error, where silence
is the worst answer); how many recent files to remember (`files/recent_limit`); restoring
the tabs at start (`files/restore_tabs`, on by default); and "check for updates" — off, this
is a local tool.  **`язык интерфейса RU/EN` was dropped on 2026-10-01** (ADR-021): the
window stays Russian, English stays with the *language*, not the interface.

## Proposed beyond the request

* **Session restore**: reopen the tabs of the previous run, including untitled buffers (kept
  in the settings store, with a size cap) — **done** (below).
* **Layout check**: a warning when a Latin identifier is used as a predicate name or vice
  versa — the mistake the two-colour highlighting exists to prevent.  Not done.
* **Interpreter profiles**: named sets of `-I` directories and options, so a lesson and a
  project do not fight over the search path — **done in `task_46`**.
* **Sandbox/limits** as settings rather than constants: run time, output lines, the
  `НАЙТИВСЕ` cap — the three ways a student program can hang the GUI — **done** (the four
  rows of "Выполнение").
* **Exporting settings for a class**: one ini file the teacher can hand out — **done**
  («Экспорт…»/«Импорт…»).

## Tests

* `src/gui/tests/test_settings.py` (Qt-free): defaults, round trip through the ini file,
  clamping of out-of-range values, preservation of unknown keys, reset to defaults — plus,
  in round B, that *every* key the module defines is either described in the dialog or listed
  as machine-managed, and that every row round-trips, clamps and resets.
* `src/gui/tests/test_settingsdialog.py` (offscreen): a page per section and a widget per
  row, «Применить» writes and «Отмена» does not, «Сбросить» needs applying, «Импорт…» stages
  a file (unknown keys and all) and «Экспорт…» writes one.
* `src/gui/tests/test_documents.py` (Qt-free) for the session records: the round trip
  through one ini line, the budget that drops whole buffers, the empty «Без имени» that is
  not stored, and a broken line that costs nothing;
  `test_window.py::test_the_tabs_come_back_on_the_next_start` closes a window over three
  tabs and opens the next one over the same settings file — the file read from disk, the
  untitled tab modified, the showing tab, a file that has gone, and the switch off;
  `test_an_unnamed_tab_left_unsaved_is_forgotten` closes one over two unnamed tabs — «Не
  сохранять» on one, «Сохранить» (into a file) on the other — and finds only the second one
  in the session.
* Manual checklist: change the font size, the line numbers and the output side, restart,
  confirm the values are back.

## Acceptance

Every setting listed above is changeable from the dialog and takes effect without a restart
where that is feasible (font, colours, line numbers, output side), the values persist, and a
settings file written by a newer version does not lose its unknown keys.

## What was built (2026-10-01)

This round was run as **option B**: the dialog, the description table and the "almost ready"
new keys — no new machinery in the interpreter, no second theme beyond the palette above.

* `settings.SETTINGS` — one `Setting` record per preference (key, label, section, kind,
  default, bounds, suffix, hint).  The *same* record drives the dialog's row,
  `value_of`/`set_value` validation and «Сбросить», so a preference cannot be editable
  without being stored or stored without being documented; `test_settings.py` proves that
  every key the module defines is either in the table or on `MACHINE_KEYS`, and the dialog
  test proves every row has a widget.
* `settingsdialog.SettingsDialog` — sections on the left (`Редактор`, `Вид`, `Формат`,
  `Выполнение`, `Файлы`, `Вставки`), rows on the right,
  «ОК»/«Применить»/«Отмена»/«Сбросить»/«Импорт…»/«Экспорт…».  «Применить» writes only the
  rows that actually differ, which keeps a fresh file fresh and keeps the one preference that
  *follows* another (`output/font_size`) from being frozen by a no-op apply.
* The window applies everything without a restart (`apply_settings`), and the menu entry is
  live — «Настройки…» was the last command to leave the disabled list except «Графическое
  окно».
* Follow-up on the first hands-on run: **«Применить» is visible while the dialog is still
  open**.  The dialog announces what it wrote (`changesApplied`) and the window answers by
  re-reading the store — the parent of a modal dialog is blocked for input but keeps
  painting, so the change was otherwise only visible after closing the box, which made
  «Применить» and «ОК» look like the same button.  The same signal fixed a second gap it
  exposed: the insert table of task_31 is data in the same file, so «Вернуть встроенную
  таблицу» now reaches the editors of an open window too.
* Same run, the layout: the buttons are built by hand in the order «Сбросить», «Импорт…»,
  «Экспорт…» | «ОК», «Отмена», «Применить» — a `QDialogButtonBox` orders its buttons by role
  and by the style, which cannot express that.  Every page also shares one label column now:
  a `QFormLayout` sizes its first column to the longest label *on its own page*, so the
  fields started at a different x on every section; the labels get the width of the widest
  one in the dialog (PySide6's `QFormLayout` has no column width to set) and the values fill
  their column.  Both are checked in `test_settingsdialog.py` (`button_order`,
  `label_column_width`).
* New keys of this round: `output/font_size` (unset = follow the editor, exactly as before),
  `output/line_limit`, `editor/completion_match_case`, `editor/current_line`,
  `execution/working_directory`, `execution/import_paths`, `files/autosave_minutes`,
  `files/recent_limit`.  The wheel over the output panel now zooms that panel, the wheel over
  the editor the editor; `Ctrl+Num±`/`Ctrl+0` and the toolbar's box stay the editor's.
* Autosave writes only buffers that have a **name** — a timer must never open a question —
  reports in the status line, and a failure goes to the output pane instead of a modal box.
* The session: **the tabs of the previous run come back** (`files/restore_tabs`).  A file tab
  is stored by **path** and an untitled one by its **text** (`documents.TabRecord`), and the
  two new keys are machine rows the window writes for itself (`session/tabs`,
  `session/current`).  The rules, and why: a *file* is read from disk on the next start, so a
  change the user refused to save is not resurrected; an *untitled* buffer spends a budget of
  `documents.SESSION_TEXT_BUDGET` (256 KiB), and a record that does not fit is dropped whole
  and counted — a tab that comes back with half of its text is worse than one that does not
  come back — while an empty untitled tab is not stored at all, being the placeholder the
  first opened file replaces; a stored path whose file has gone is skipped and **named** in
  the status line, because a session that is quietly one tab short is worse than one that
  says so; and a restored untitled tab is **unsaved work**, so the next close asks about it.
  An untitled tab answered with «Не сохранять» is not stored at all — the answer means the
  text is not to be seen again, and a session written before the questions would make it a
  lie; a tab saved on the way out is remembered as the file it became.  The session is
  therefore written only once `close_all()` has succeeded, from the tab list taken before it:
  «Отмена» leaves the window open, and a session written on the way out would describe a
  window that never closed.  Unticking the box opens the welcome program instead — the
  setting is the only switch.
* The four switches that were left over, all of them over behaviour that already existed:
  «Редактор → Автоотступ» (`editor/auto_indent`), «Вид → Следить за выводом»
  (`view/follow_output`), «Вид → Спрашивать ввод» (`view/input_mode`) and «Выполнение →
  Выводить вопросы при запуске» (`execution/run_questions`).  Nothing else changed shape:
  `Enter` either continues the line's indentation or starts at the margin (the indent *unit*
  stays — `Tab` is not affected); the output pane either keeps the end in sight or holds
  still (it already stopped following when the reader scrolled up; the switch is the other
  direction); a program's input question is answered in the console under the output or in a
  box, whatever is on screen; and a run either answers the program's own `?`-statements or
  loads it for its clauses only — `run_program`'s `questions` argument now defaults to the
  setting, while the margin's click still asks its one question explicitly.  Checked by
  `test_editor.py::test_auto_indent_can_be_switched_off`,
  `test_output.py::test_following_the_end_can_be_forbidden`,
  `test_window.py::test_the_questions_switch_decides_whether_a_run_answers`,
  `test_window.py::test_the_input_switch_chooses_where_to_ask` and the defaults in
  `test_settings.py`.  251/251 ctest, 20 headless GUI scripts, five PDFs.

The working folder and the `-I` list reach the engine as `-I` arguments on every session
(`PrologSession.set_includes`), after the command line's own ones; the importing file's
directory still wins inside the engine.

## Still open, and why

Each of these is a feature of its own, not a row in this dialog:

* **"Use the system colours"** — done on 2026-10-01 with the dark theme: "as in the system"
  returns the desktop's palette *and* style and takes the highlighting colours that fit its
  scheme (`appearance.system_is_dark()` over `QStyleHints.colorScheme()`, with a fallback
  reading of the platform palette).  Before that it was half a theme — dark widgets with
  light highlighting on them.
* **Latin vs Cyrillic colours** — done (task_22: separate fields, and the dark palette keeps
  the split).
* **RU/EN — dropped on 2026-10-01 (ADR-021).**  The window stays Russian: the interface needs
  no translation, and half a translation is worse than none.  The English names of the
  built-ins and the English sections of the manual have nothing to do with this and stay
  (task_39).
* **Moved to tasks of their own (2026-10-01)**: "the interpreter path, profiles, limits and
  the timeout" is `task_46_interpreter_options_and_limits.md`, and "the graphics window" is
  `task_45_gui_graphics_window.md`.  Neither is a row in this dialog: the limits need a
  session key (`load` carries only `step`/`trace`/`questions` today, although `maxSteps`,
  `maxDepth` and `maxFindAllSolutions` are in the engine already) and the graphics needs
  protocol events.  The *process* working directory (`ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` are relative to
  it) belongs there too.
* **"Check for updates"** stays off by decision — this is a local tool.
