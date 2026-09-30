# task_29 — GUI: settings dialog and persistence

**Status:** done (round B, 2026-10-01) — the dialog, the described table, reset,
import/export, and the «почти готовые» new keys; the rest of the list is named
under «What was built» and still open
**Depends on:** task_22 (font, line numbers), task_26 (view actions), task_27 (panels)
**Milestone:** M11

## Goal

One place for everything the user can configure, with the values surviving a
restart.  The requested settings are the line numbers and the font size; the
rest of this list is what the surrounding features make necessary or obviously
worth having.

## Storage

- [x] `prologd_gui/settings.py` — a Qt-free description of every setting (name,
      type, default, bounds) plus a `QSettings`-backed store using
      `QSettings.IniFormat` in `QStandardPaths.AppConfigLocation`
      (`%APPDATA%\PrologD\gui.ini`), with `--settings FILE` on `main.py` to
      point somewhere else (a portable install, a test).
- [x] Unknown keys are preserved (a newer version's settings must not be dropped
      by an older one), broken values fall back to the default and are reported
      in the log, and **Настройки → Сбросить** restores the defaults.
- [x] Import/export to a file, so a configuration can be moved between machines.

## Settings

Editor

- [x] номера строк: вкл/выкл (the requested one), plus "подсвечивать текущую
      строку";
- [x] шрифт семейства (monospaced first, Cyrillic-capable), размер (6…72),
      текущий масштаб `Ctrl`+wheel;
- [x] ширина табуляции, "табы или пробелы", автоотступ;
- [x] перенос длинных строк (word wrap) вкл/выкл;
- [x] автодополнение: вкл/выкл, после скольких букв, учитывать регистр;
- [x] автосохранение (интервал или "перед запуском").

Highlighting

- [ ] цвета по видам токенов, отдельно **цвет латиницы** и **цвет кириллицы**
      (task_22), светлая/тёмная тема, "использовать системные цвета".  `light`
      and `system` exist already (`--theme`, task_22); a **dark** theme is not a
      switch but a second syntax palette — bright colours for a dark background —
      and the palette must keep WCAG contrast 4.5 against its own background
      (there is a helper for that: `theme.contrast_ratio`).

Formatting

- [x] режим: `не менять` / `мягкое` / `жёсткое` (task_30), ширина строки для
      мягкого режима, отступ (в табах, по умолчанию 2), "форматировать только
      выделенное".  (Режимы с 2026-10-01: `в одну строку` / `мягкое` /
      `жёсткое` — «не менять» стал «в одну строку», см. task_30.)

Output

- [x] панель вывода снизу/справа, шрифт и размер вывода (отдельно от
      редактора), лимит строк, "выводить вопросы", "следить за выводом".
      **Сейчас размер один на редактор, вывод и строку запроса** (ключ
      `editor/font_size`): так масштаб, который пользователь поставил колесом,
      переживает перезапуск и в панели вывода.  Раздельные размеры — это первые
      два пункта здесь, и делать их надо вместе с диалогом, а не раньше.
      (Сделано 2026-10-01: `output/font_size` — пока его не задали, панель идёт
      за редактором, как раньше; колесо над панелью отделяет её навсегда.
      Семейство шрифта осталось одно на всё окно — панель вывода моноширинная,
      и второй семейство ничего не покупает.)

Execution

- [ ] путь к интерпретатору (`--exe` today), сохранять перед запуском,
      таймаут запроса, лимит числа решений `НАЙТИВСЕ`;
- [x] **рабочая папка** — the one directory the user keeps shared sources in
      ("общие функции для стандартной реализации").  It is passed as `-I` on
      every session, so `ИМПОРТ("library.pld")` works from any program, saved or
      untitled — pointing it at `examples/lib` is the out-of-the-box example.
      It is a *search* directory, not the working directory of the process, and
      it is appended after the importing file's own directory, so a local
      `lib/x.pld` always wins over a same-named file in the shared folder;
- [x] дополнительные каталоги `ИМПОРТ` (`-I`, repeatable) и **рабочий каталог
      процесса**: `каталог файла` (default for a saved file) or `рабочая папка`
      (default for «Без имени»).  The working directory is what `ЗАПИСЬ_В("out.txt")`
      and `ЧТЕНИЕ_ИЗ` are relative to, and it is shown in the status bar so the
      two are not confused;
      (Сделаны `-I` и рабочая папка; рабочий каталог *процесса* остался: это
      отдельная вещь — `ЗАПИСЬ_В` считается от него, — и ей нужен ключ сессии, а
      не ещё одна строка в диалоге.)
- [ ] «сообщать, где искался импорт» — task_32, on by default.
- [ ] вход: панель вывода или диалоги (task_27).

General

- [x] язык интерфейса RU/EN (the reference GUI was Russian only),
      восстанавливать открытые вкладки при старте, недавние файлы (сколько
      помнить), проверять обновления — off, this is a local tool.
      (Сделано только «сколько помнить» (`files/recent_limit`); RU/EN и
      восстановление вкладок — отдельные задачи, см. «What was built».)

## Proposed beyond the request

* **Восстановление сессии**: reopen the tabs of the previous run, including
  untitled buffers (kept in the settings store, with a size cap).
* **Проверка раскладки** — a warning when a Latin identifier is used as a
  predicate name or vice versa; that is the mistake the two-colour highlighting
  exists to prevent, and a warning is the natural next step.
* **Профиль интерпретатора**: named sets of `-I` directories and options, so a
  lesson and a project do not fight over the search path.
* **Песочница/лимиты** as settings rather than constants: run time, output
  lines, `НАЙТИВСЕ` cap — the three ways a student program can hang the GUI.
* **Экспорт настроек для класса**: one ini file the teacher can hand out.

## Tests

- [x] `src/gui/tests/test_settings.py` (Qt-free): defaults, round trip through
      the ini file, clamping of out-of-range values, preservation of unknown
      keys, reset to defaults — plus, in round B, that *every* key the module
      defines is either described in the dialog or listed as machine-managed, and
      that every row round-trips, clamps and resets.
- [x] `src/gui/tests/test_settingsdialog.py` (offscreen): a page per section and
      a widget per row, «Применить» writes and «Отмена» does not, «Сбросить»
      needs applying, «Импорт…» stages a file (unknown keys and all) and
      «Экспорт…» writes one.
- [ ] Manual checklist: change the font size, the line numbers and the output
      side, restart, confirm the values are back.

## Acceptance

Every setting listed above is changeable from the dialog and takes effect
without a restart where that is feasible (font, colours, line numbers, output
side), the values persist, and a settings file written by a newer version does
not lose its unknown keys.

## What was built (2026-10-01)

This round was run as **option B**: the dialog, the description table and the
"almost ready" new keys — no new machinery in the interpreter, no second theme.

* `settings.SETTINGS` — one `Setting` record per preference (key, label,
section, kind, default, bounds, suffix, hint).  The *same* record drives the
dialog's row, `value_of`/`set_value` validation and «Сбросить», so a preference
cannot be editable without being stored or stored without being documented;
`test_settings.py` also proves that every key the module defines is either in the
table or on `MACHINE_KEYS`, and the dialog test proves every row has a widget.
* `settingsdialog.SettingsDialog` — sections on the left (`Редактор`, `Вид`,
`Формат`, `Выполнение`, `Файлы`, `Вставки`), rows on the right, «ОК»/«Применить»/
«Отмена»/«Сбросить»/«Импорт…»/«Экспорт…».  «Применить» writes only the rows that
actually differ, which keeps a fresh file fresh and keeps the one preference
that *follows* another (below) from being frozen by a no-op apply.
* The window applies everything without a restart (`apply_settings`), and the
menu entry is live — «Настройки…» is the last command that left the disabled
list except «Графическое окно».
* 2026-10-01, follow-up on the first hands-on run: **«Применить» is visible while
the dialog is still open**.  The dialog announces what it wrote
(`changesApplied`) and the window answers by re-reading the store — the parent of
a modal dialog is blocked for input but keeps painting, so the change was
otherwise only visible after closing the box, which made «Применить» and «ОК»
look like the same button.  The same signal fixed a second gap it exposed: the
insert table of task_31 is data in the same file, so «Вернуть встроенную
таблицу» now reaches the editors of an open window too.
* 2026-10-01, same run, the layout: the buttons are built by hand in the order
«Сбросить», «Импорт…», «Экспорт…» | «ОК», «Отмена», «Применить» — a
`QDialogButtonBox` orders its buttons by role and by the style, which cannot
express that.  Every page also shares one label column now: a `QFormLayout`
sizes its first column to the longest label *on its own page*, so the fields
started at a different x on every section; the labels get the width of the widest
one in the dialog (PySide6's `QFormLayout` has no column width to set) and the
values fill their column.  Both are checked in `test_settingsdialog.py`
(`button_order`, `label_column_width`).
* New keys of this round: `output/font_size` (unset = follow the editor, exactly
as before), `output/line_limit` (applied at once: a smaller limit trims),
`editor/completion_match_case`, `editor/current_line`,
`execution/working_directory`, `execution/import_paths`, `files/autosave_minutes`,
`files/recent_limit`.  The wheel over the output panel now zooms that panel, the
wheel over the editor the editor; `Ctrl+Num±`/`Ctrl+0` and the toolbar's box stay
the editor's.
* Autosave writes only buffers that have a **name** — a timer must never open a
question — reports in the status line, and a failure goes to the output pane
instead of a modal box.

The working folder and the `-I` list reach the engine as `-I` arguments on every
session (`PrologSession.set_includes`), after the command line's own ones; the
importing file's directory still wins inside the engine.

**Still open, and why** (each is its own feature, not a dialog row):

- [ ] the token colours and the **dark theme** — a dark palette is a second
      syntax palette that has to keep WCAG 4.5 against its own background;
- [ ] the colours of Latin vs Cyrillic, «использовать системные цвета»;
- [ ] **RU/EN** — the reference front-end was Russian only, and translating the
      window is a task of its own;
- [ ] session restore (reopening the tabs of the previous run, untitled buffers
      included);
- [ ] the interpreter profiles, the sandbox limits (run time, `НАЙТИВСЕ` cap),
      the query timeout and the path to the interpreter (still `--exe`), and the
      working directory of the process (`ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` are relative to
      it) — all of them need engine options that do not exist yet;
- [ ] «выводить вопросы», «следить за выводом», «сообщать, где искался импорт»
      (task_32) and the input mode as switches — behaviour exists, the switches
      do not;
- [ ] автоотступ as a switch; «проверять обновления» stays off by decision.
