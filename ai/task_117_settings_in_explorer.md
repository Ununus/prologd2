# task_117 — «Показать в проводнике» beside the settings file

**Status:** done (2026-10-24) — part 189
**Depends on:** task_29 (the dialog and its «Вставки» page), task_68/task_109 (`paths.reveal`)
**Milestone:** 2.7.0

## What the owner asked for

A button «Показать в проводнике» next to «Открыть файл настроек» on the «Вставки»
page of «Правка → Настройки…», which opens the file manager at the settings file.

## What was done

* `settingsdialog.py`: the two file actions now stand in one row under the path label
  («Открыть файл настроек» | «Показать в проводнике»), and «Вернуть встроенную
  таблицу» stays on its own line below them.  Both have tooltips; before this only
  the labels explained themselves.
* `_reveal_settings_file` calls `paths.reveal` — the same platform-aware call the
  window makes for a document (Windows: `explorer /select,<path>`, so the file
  arrives selected; macOS: `open -R`; the rest: the folder).  A store that has not
  written its file yet (a dialog opened before anything was changed) reveals the
  *folder*: selecting a file that is not there would open some other folder and
  explain nothing.
* The status line of the dialog is given the path, as «Открыть файл настроек» does.

## Checks

* `test_settingsdialog.py` — a new check finds both buttons by their titles, replaces
  `paths.reveal` with a recorder and reads what it was handed: the file when it
  exists, its folder after it is deleted.
* The «Вставки» page was grabbed offscreen and looked at: the two buttons share a
  row under the path, the revert button is a line of its own.
* Manual (`doc/gui.typ` §8): the «Вставки» row of the table names both buttons, and
  a bullet says what each does — including the folder fallback.  Page 30 was looked
  at after the docs target.
* `src/gui/README.md`: the dialog section names the two ways to reach the ini.
* 30 window scripts and `protocol_smoke.py` are green.
