# task_50 — the output panel with tabs: Проблемы, Вывод, Система, Ввод

**Status:** in progress
**Depends on:** task_29 (settings dialog), task_46 (limits), task_49 (batched output)
**Milestone:** post-M10

## Goal

The output panel becomes a *tabbed* panel.  One splitter on the side of the
editor, with four tabs inside it:

1. **Проблемы** — the interpreter's diagnostics: errors and warnings.
2. **Вывод** — the program's own output (with the `>` echo and the trace).
3. **Система** — the window's own notes: «загрузка базы знаний», the limits,
   «остановлено», «база знаний загружена (N мс)».
4. **Ввод** — the prepared answers (the old input queue), with the per-request
   console *under* it, in the same tab.

## What this replaces

- The panel is one `QSplitter` holding the output, the request console and the
  input queue.  It becomes one `QTabWidget`; the console and the queue share the
  «Ввод» tab (queue on top, console under it).
- The setting «Поле очереди ввода» (`view/input_queue`) is gone: the queue is a
  tab now, always there.  The action «Поле очереди ввода» and its menu row go
  with it.
- The panel defaults to the **bottom** (`view/output_position` = `bottom`),
  not the right.

## New behaviour

- Each tab's title carries the count of what it holds: `Вывод:5`, `Проблемы:0`,
  `Система:3`, `Ввод:2` (Ввод counts the prepared lines).  The «Проблемы» word
  is painted by state: the ordinary colour with 0 problems, orange with warnings
  only, red when there is an error.
- On run, the panel shows «Вывод».  A diagnostic (warning or error) switches it
  to «Проблемы».
- A run that loads a file to the end writes one more system line:
  `--- база знаний загружена (334 мс) ---`, measured by the GUI clock from the
  press of «Запустить» to the `loaded` event (protocol 8).

## Mapping of kinds to tabs

`panels` keeps the kinds; the window routes them:

| kind      | tab       |
|-----------|-----------|
| `OUTPUT`  | Вывод     |
| `ECHO`    | Вывод     |
| `TRACE`   | Вывод     |
| `NOTE`    | Система   |
| `ERROR`   | Проблемы  |
| `WARNING` | Проблемы  |

## Deliverables

- [ ] `panels.py`: the routing table (kind → tab) and a `PanelTabs` widget that
      builds the four tabs and names them (`Проблемы`, `Вывод`, `Система`, `Ввод`).
- [ ] `window.py`: the tab widget replaces the output `QSplitter`; `_append_output`
      routes by kind; `_refresh_panel_tabs` keeps the `name:count` titles and the
      «Проблемы» colour; run focus = Вывод, diagnostics focus = Проблемы.
- [ ] `settings.py`: `view/input_queue` removed; `view/output_position` defaults
      to `bottom`.
- [ ] `actions.py`: the «Поле очереди ввода» action and menu row removed.
- [ ] The `loaded` timing note («база знаний загружена (N мс)») in Система.
- [ ] Tests: `test_window.py` (tabs, counts, colour, focus, timing), `test_settings.py`,
      `test_settingsdialog.py` (no input_queue row), `test_output.py` untouched.

## Notes

- «Сохранить вывод» keeps writing the Вывод tab (the log of the run).  The
  problems and system tabs are views, not logs to save.
- The Ввод tab's queue is user data: a run never clears it, only its *copy* is
  consumed (`_queued_input`), exactly as before.
