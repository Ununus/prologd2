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
      (2026-10-01: отступ после `Enter` стал переключателем
      `editor/auto_indent`, включён — поведение то же, что и было, но его можно
      выключить; единица отступа при этом остаётся за `Tab`.)
- [x] перенос длинных строк (word wrap) вкл/выкл;
- [x] автодополнение: вкл/выкл, после скольких букв, учитывать регистр;
- [x] автосохранение (интервал или "перед запуском").

Highlighting

- [x] цвета по видам токенов, отдельно **цвет латиницы** и **цвет кириллицы**
      (task_22), светлая/тёмная тема, "использовать системные цвета".  `light`
      and `system` exist already (`--theme`, task_22); a **dark** theme is not a
      switch but a second syntax palette — bright colours for a dark background —
      and the palette must keep WCAG contrast 4.5 against its own background
      (there is a helper for that: `theme.contrast_ratio`).
      (Тёмная тема сделана 2026-10-01: `theme.Palette` — запись «страница +
      подсветка + полосы + полоса номеров + цвета вывода» на каждую тему,
      `LIGHT` и `DARK`; `appearance.qt_palette` переводит её в палитру виджетов,
      а поля редактора, полосы и панель вывода читают цвета из той же записи.
      Контраст 4.5 проверяется для **обеих** палитр по списку
      `Palette.readable_pairs` против той страницы, на которой цвет рисуется
      (`test_appearance.py`); та же проверка нашла, что цвет трассы светлой темы
      был 4.48 — на шаг темнее, и он чистый (4.61).  Тогда же сделан и
      «использовать системные цвета»: выбор «как в системе» берёт цвета рабочего
      стола и для виджетов, и для подсветки.  Пункт закрыт целиком.)

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
      и второй семейство ничего не покупает.  Тогда же — `view/follow_output` и
      `execution/run_questions`: «следить за выводом» и «выводить вопросы» стали
      переключателями над поведением, которое уже было.)

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
- [x] вход: панель вывода или диалоги (task_27) — ключ `view/input_mode`:
      «в панели» (по умолчанию) или «в диалоге», независимо от того, видна ли
      панель (2026-10-01).  Раньше это решала только видимость панели.

General

- [x] язык интерфейса RU/EN (the reference GUI was Russian only),
      восстанавливать открытые вкладки при старте, недавние файлы (сколько
      помнить), проверять обновления — off, this is a local tool.
      (Сделано «сколько помнить» (`files/recent_limit`) и восстановление
      вкладок (`files/restore_tabs`, 2026-10-01, см. «What was built»); RU/EN и
      «проверять обновления» — отдельные задачи.)

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
- [x] `src/gui/tests/test_documents.py` (Qt-free) for the session records: the
      round trip through one ini line, the budget that drops whole buffers, the
      empty «Без имени» that is not stored, and a broken line that costs nothing;
      `test_window.py::test_the_tabs_come_back_on_the_next_start` closes a window
      over three tabs and opens the next one over the same settings file — the
      file read from disk, the untitled tab modified, the showing tab, a file
      that has gone, and the switch off;
      `test_an_unnamed_tab_left_unsaved_is_forgotten` closes one over two unnamed
      tabs — «Не сохранять» on one, «Сохранить» (into a file) on the other — and
      finds only the second one in the session.
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
* 2026-10-01, the session: **the tabs of the previous run come back**
(`files/restore_tabs`, on by default).  A file tab is stored by **path** and an
untitled one by its **text** (`documents.TabRecord`), and the two new keys are
machine rows the window writes for itself (`session/tabs`, `session/current`).
The rules, and why: a *file* is read from disk on the next start, so a change the
user refused to save is not resurrected; an *untitled* buffer spends a budget of
`documents.SESSION_TEXT_BUDGET` (256 KiB), and a record that does not fit is
dropped whole and counted — a tab that comes back with half of its text is worse
than one that does not come back — while an empty untitled tab is not stored at
all, being the placeholder the first opened file replaces; a stored path whose
file has gone is skipped and **named** in the status line, because a session that
is quietly one tab short is worse than one that says so; and a restored untitled
tab is **unsaved work**, so the next close asks about it.  An *untitled* tab that
is answered with «Не сохранять» is not stored at all — the answer means the text is
not to be seen again, and a session written before the questions would make it a
lie; a tab saved on the way out is remembered as the file it became.  The session
is therefore written only once `close_all()` has succeeded, from the tab list taken
before it: «Отмена» leaves the window open, and a session written on the way out
would describe a window that never closed.  Unticking the box opens the welcome
program instead — the setting is the only switch.

* 2026-10-01, the four switches that were left over,
all of them switches over behaviour that already existed: «Редактор → Автоотступ»
(`editor/auto_indent`), «Вид → Следить за выводом» (`view/follow_output`),
«Вид → Спрашивать ввод» (`view/input_mode`) and «Выполнение → Выводить вопросы
при запуске» (`execution/run_questions`).  Nothing else changed shape: `Enter`
either continues the line's indentation or starts at the margin (the indent *unit*
stays — `Tab` is not affected); the output pane either keeps the end in sight or
holds still (it already stopped following when the reader scrolled up; the switch is
the other direction, «не уводите взгляд»); a program's input question is answered in
the console under the output or in a box, whatever is on screen; and a run either
answers the program's own `?`-statements or loads it for its clauses only —
`run_program`'s `questions` argument now defaults to the setting, while the margin's
click still asks its one question explicitly.  Checked by
`test_editor.py::test_auto_indent_can_be_switched_off`,
`test_output.py::test_following_the_end_can_be_forbidden`,
`test_window.py::test_the_questions_switch_decides_whether_a_run_answers`,
`test_window.py::test_the_input_switch_chooses_where_to_ask` and the defaults in
`test_settings.py`.  251/251 ctest, 20 headless-скриптов GUI, пять PDF.

The working folder and the `-I` list reach the engine as `-I` arguments on every
session (`PrologSession.set_includes`), after the command line's own ones; the
importing file's directory still wins inside the engine.

**Still open, and why** (each is its own feature, not a dialog row):

- [x] «использовать системные цвета» — сделано 2026-10-01 вместе с тёмной темой:
      выбор «как в системе» возвращает палитру *и* стиль рабочего стола, а цвета
      подсветки берёт те, что подходят его схеме (`appearance.system_is_dark()` по
      `QStyleHints.colorScheme()`, с запасным чтением палитры платформы).  Раньше
      это была половина темы — тёмные виджеты и светлая подсветка на них.
- [ ] the colours of Latin vs Cyrillic are *done* (task_22: separate fields, and
      the dark palette keeps the split);
- [ ] **RU/EN** — the reference front-end was Russian only, and translating the
      window is a task of its own;
- [ ] the interpreter profiles, the sandbox limits (run time, `НАЙТИВСЕ` cap),
      the query timeout and the path to the interpreter (still `--exe`), and the
      working directory of the process (`ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` are relative to
      it) — all of them need engine options that do not exist yet;
- [ ] «сообщать, где искался импорт» (task_32) and the switches that are left
      need the engine, not a dialog row: where the import search looked is
      something only the interpreter can say;
- [ ] «проверять обновления» stays off by decision — this is a local tool.
