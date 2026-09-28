# task_29 — GUI: settings dialog and persistence

**Status:** not started
**Depends on:** task_22 (font, line numbers), task_26 (view actions), task_27 (panels)
**Milestone:** M11

## Goal

One place for everything the user can configure, with the values surviving a
restart.  The requested settings are the line numbers and the font size; the
rest of this list is what the surrounding features make necessary or obviously
worth having.

## Storage

- [ ] `prologd_gui/settings.py` — a Qt-free description of every setting (name,
      type, default, bounds) plus a `QSettings`-backed store using
      `QSettings.IniFormat` in `QStandardPaths.AppConfigLocation`
      (`%APPDATA%\PrologD\gui.ini`), with `--settings FILE` on `main.py` to
      point somewhere else (a portable install, a test).
- [ ] Unknown keys are preserved (a newer version's settings must not be dropped
      by an older one), broken values fall back to the default and are reported
      in the log, and **Настройки → Сбросить** restores the defaults.
- [ ] Import/export to a file, so a configuration can be moved between machines.

## Settings

Editor

- [ ] номера строк: вкл/выкл (the requested one), plus "подсвечивать текущую
      строку";
- [ ] шрифт семейства (monospaced first, Cyrillic-capable), размер (6…72),
      текущий масштаб `Ctrl`+wheel;
- [ ] ширина табуляции, "табы или пробелы", автоотступ;
- [ ] перенос длинных строк (word wrap) вкл/выкл;
- [ ] автодополнение: вкл/выкл, после скольких букв, учитывать регистр;
- [ ] автосохранение (интервал или "перед запуском").

Highlighting

- [ ] цвета по видам токенов, отдельно **цвет латиницы** и **цвет кириллицы**
      (task_22), светлая/тёмная тема, "использовать системные цвета".  `light`
      and `system` exist already (`--theme`, task_22); a **dark** theme is not a
      switch but a second syntax palette — bright colours for a dark background —
      and the palette must keep WCAG contrast 4.5 against its own background
      (there is a helper for that: `theme.contrast_ratio`).

Formatting

- [ ] режим: `не менять` / `мягкое` / `жёсткое` (task_30), ширина строки для
      мягкого режима, отступ (в табах, по умолчанию 2), "форматировать только
      выделенное".

Output

- [ ] панель вывода снизу/справа, шрифт и размер вывода (отдельно от
      редактора), лимит строк, "выводить вопросы", "следить за выводом".
      **Сейчас размер один на редактор, вывод и строку запроса** (ключ
      `editor/font_size`): так масштаб, который пользователь поставил колесом,
      переживает перезапуск и в панели вывода.  Раздельные размеры — это первые
      два пункта здесь, и делать их надо вместе с диалогом, а не раньше.

Execution

- [ ] путь к интерпретатору (`--exe` today), сохранять перед запуском,
      таймаут запроса, лимит числа решений `НАЙТИВСЁ`;
- [ ] **рабочая папка** — the one directory the user keeps shared sources in
      ("общие функции для стандартной реализации").  It is passed as `-I` on
      every session, so `ИМПОРТ("library.pld")` works from any program, saved or
      untitled — pointing it at `examples/lib` is the out-of-the-box example.
      It is a *search* directory, not the working directory of the process, and
      it is appended after the importing file's own directory, so a local
      `lib/x.pld` always wins over a same-named file in the shared folder;
- [ ] дополнительные каталоги `ИМПОРТ` (`-I`, repeatable) и **рабочий каталог
      процесса**: `каталог файла` (default for a saved file) or `рабочая папка`
      (default for «Без имени»).  The working directory is what `ЗАПИСЬ_В("out.txt")`
      and `ЧТЕНИЕ_ИЗ` are relative to, and it is shown in the status bar so the
      two are not confused;
- [ ] «сообщать, где искался импорт» — task_32, on by default.
- [ ] вход: панель вывода или диалоги (task_27).

General

- [ ] язык интерфейса RU/EN (the reference GUI was Russian only),
      восстанавливать открытые вкладки при старте, недавние файлы (сколько
      помнить), проверять обновления — off, this is a local tool.

## Proposed beyond the request

* **Восстановление сессии**: reopen the tabs of the previous run, including
  untitled buffers (kept in the settings store, with a size cap).
* **Проверка раскладки** — a warning when a Latin identifier is used as a
  predicate name or vice versa; that is the mistake the two-colour highlighting
  exists to prevent, and a warning is the natural next step.
* **Профиль интерпретатора**: named sets of `-I` directories and options, so a
  lesson and a project do not fight over the search path.
* **Песочница/лимиты** as settings rather than constants: run time, output
  lines, `НАЙТИВСЁ` cap — the three ways a student program can hang the GUI.
* **Экспорт настроек для класса**: one ini file the teacher can hand out.

## Tests

- [ ] `src/gui/tests/test_settings.py` (Qt-free): defaults, round trip through
      the ini file, clamping of out-of-range values, preservation of unknown
      keys, reset to defaults.
- [ ] Manual checklist: change the font size, the line numbers and the output
      side, restart, confirm the values are back.

## Acceptance

Every setting listed above is changeable from the dialog and takes effect
without a restart where that is feasible (font, colours, line numbers, output
side), the values persist, and a settings file written by a newer version does
not lose its unknown keys.
