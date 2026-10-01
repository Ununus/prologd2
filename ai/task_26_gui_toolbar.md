# task_26 — GUI: menu bar, toolbar and icons

**Status:** done (2026-09-29)
**Depends on:** task_22 (actions exist), task_25 (file actions)
**Milestone:** M11

## Goal

Give every action a place in the menus and on the toolbar, and use the icons the
user copied from the previous project.  Report what is missing instead of
drawing a text-only button.

## Deliverables

- [x] `prologd_gui/assets.py` — load an icon by name from `src/gui/assets`,
      cached, with `--icons DIR` on `main.py` to point elsewhere; a missing file
      is a text-only action plus one warning in the log, never a crash.
- [x] Menu bar, structured like the reference GUI:
  * **Файл**: Новый, Открыть…, Последние, Сохранить, Сохранить как…, Сохранить
    все, Перечитать, Закрыть, Закрыть все, Выход;
  * **Правка**: Отменить, Повторить, Вырезать, Копировать, Вставить, Удалить,
    Выделить всё, Закомментировать `Ctrl+K`, Раскомментировать `Ctrl+U`,
    Форматировать `Ctrl+I`, Настройки…;
  * **Поиск**: Поиск/Замена `Ctrl+F`, Далее `F3`, Назад `Shift+F3`, Найти
    выделенное `Ctrl+F3`, Найти выделенное назад `Ctrl+Shift+F3` (the last two,
    with their pictures and their keys, left in `task_48_interface_cleanup.md`:
    the find bar takes its question from the selection anyway);
  * **Вид**: Панель инструментов, Панель вывода `F4`, Сменить ориентацию
    сплита `Ctrl+F4`, Номера строк, Разделить редактор, Масштаб (`Ctrl+±`),
    Полный экран `F11`, Тема;
  * **Выполнение**: Запуск `F5`, Запуск с трассировкой, Шаг `F10`, Остановить
    `Shift+F5`, Сохранять перед запуском;
  * **Справка**: Справка (`doc/help.typ` → PDF/HTML if present, else the
    `--help` text), О программе.
- [x] Toolbar grouped as in the reference GUI: file | run/stop/step |
      graphics/help | comment/uncomment/format | settings, plus the font-size
      control and a spacer; every action that exists in a menu and is useful
      (task_47 returned the formatter's **mode control** to the toolbar, right
      after «Форматировать», and task_48 took «Сохранить все» off it)
      while typing also appears on the toolbar.
- [x] Actions are created once (`actions.py`) and reused by the menus, the
      toolbar and the context menu of the editor, so shortcut, tooltip and
      enable/disable state cannot drift; view actions are checkable and their
      state is persisted (task_29).
- [x] An icon audit: a table in `src/gui/README.md` listing every icon name the
      code references, the file that provides it, and the entries that are
      expected to be missing until the user draws them (see below).
- [x] Tests: `src/gui/tests/test_icons.py` — every referenced icon exists in
      `assets/`, or is in the documented `MISSING` list in `assets.py`; this
      fails as soon as a name is misspelled.

## Icons: what exists and what is missing

**Superseded** by the drawings that arrived in task_27 and task_33: the current
audit is 48 referenced names, 42 drawn, and 6 left — `view-toolbar`,
`view-split-editor`, `view-output-right`, `view-output-bottom`,
`view-line-numbers` and `view-theme` — plus `execution-step-over` and
`execution-restart`, which are waiting for task_28.  `test_icons.py` and the
«Icon audit» section of `src/gui/README.md` are the live lists; the table below is
kept as the drawing plan of task_26.

Present (64 px tall PNG, `prologd2.ico` for the window): `file-new`,
`file-open`, `file-save`, `file-close`, `file-close-all`, `file-exit`,
`edit-undo`, `edit-redo`, `edit-cut`, `edit-copy`, `edit-paste`, `edit-comment`,
`edit-uncomment`, `edit-format`, `search-find`, `search-find-next`,
`search-find-prev`, `search-find-selected-next`, `search-find-selected-prev`,
`execution-execute`, `execution-abort`, `execution-tracing`, `view-full-screen`,
`view-graphics`, `tools-settings`, `help`.

Missing — to be drawn in the same style (64×64 PNG, transparent background):

| Name | Needed for |
|------|------------|
| `file-save-as` | Сохранить как… |
| `file-save-all` | Сохранить все |
| `file-reload` | Перечитать с диска |
| `edit-clear` | Очистить вывод |
| `edit-find-replace` | Поиск/Замена (сегодня только `search-find`) |
| `execution-step-into`, `execution-step-over` | пошаговое выполнение (task_28) |
| `execution-restart` | перезапуск сессии после **Остановить** |
| `view-split-editor` | Разделить редактор на два (task_26) |
| `view-output-bottom`, `view-output-right` | положение панели вывода (task_27) |
| `view-line-numbers` | номера строк в настройках/меню «Вид» |
| `view-zoom-in`, `view-zoom-out`, `view-zoom-reset` | масштаб шрифта |
| `view-toolbar` | показать/скрыть панель инструментов |
| `view-theme` | светлая/тёмная тема |
| `help-about` | О программе (в старом GUI использовался `prolog1.png`) |

Nice-to-have: `file-recent`, `edit-indent`/`edit-unindent`,
`execution-stop-all`, an application icon in 256 px for the installer.

## Design notes

* The reference project embedded icons through `res.qrc` (`:/images/…`).  In
  Python there is no resource compiler, so the assets stay a plain directory and
  `assets.py` resolves it; a frozen build would use `sys._MEIPASS` — noted, not
  implemented.
* Toolbar icons are 64 px and Qt scales them down; set
  `QToolBar.setIconSize(QSize(24, 24))` explicitly so the layout does not depend
  on the style, and check the result on a high-DPI display.

## Acceptance

Every action of the requested feature list is reachable from the menu and, where
useful, from the toolbar; the toolbar shows the icons that exist and text-only
buttons for those that do not, and `test_icons.py` proves the referenced names
match the files.

## Result

`prologd_gui/actions.py` holds one `Action` per command — **48** entries, each with
its title, icon, shortcuts, whether it is checkable and whether it is implemented,
plus `waiting_for` — and `MENUS`, `TOOLBAR` and `CONTEXT` are three views of that
one table.  `window.py` makes one `QAction` per entry (`_build_actions`), wires it
through `_slot_for`, and builds the menu bar (`_build_menus`), the toolbar
(`_build_toolbar`: icons at 24 px, the font-size combo inserted where the table
says `#font`) and the editor's context menu (`_apply_context_actions`, guarded so
the same action is never added twice) from them — so a command cannot exist in two
versions.  **12** entries are present but disabled.

* View switches are checkable and persisted (`view/toolbar`, `editor/line_numbers`,
  `view/theme`, `execution/save_before_run`).  The toolbar's visibility is read
  with `isHidden()`: `isVisible()` is false for a window that was never shown, and
  the first start would have written a wrong preference.
* The «Последние» submenu is refilled when it opens: entries whose file is gone
  are pruned, an empty list says «(пока пусто)», «Очистить список» empties it.
* The size control is an *editable* combo with a `QIntValidator(6, 72)`: a size
  from the wheel (17 pt, 23 pt) need not be in the list, and a non-editable combo
  would silently show another number.
* The icon audit lives in `src/gui/README.md`: 41 referenced names, 25 with a file
  in `assets/`, 16 still to draw, 19 names in `assets.MISSING` (three of them for
  features that are not wired yet, which the test allows), 28 files in the
  directory — three of which nothing refers to (`file`, `prologd2`, `search-find`;
  `setWindowIcon` is still not called).

### Deliberately not built

| Entry | Why |
|-------|-----|
| `format` (`Ctrl+I`) | task_30 — no formatter in prlib yet |
| `settings` | task_29 — values are edited in `gui.ini` |
| `find`, `find_next`, `find_prev`, `find_selected`, `find_selected_prev` | **no task file exists for search/replace at all** — the feature list of task_21 asks for it and no task_22–32 covers it.  Worth opening one |
| `output` (`F4`), `split_orientation` (`Ctrl+F4`), `graphics` | task_27 |
| `run_trace`, `step` (`F10`) | task_28 — needs an engine seam and protocol events |
| `zoom_in`/`zoom_out` keyless | task_31 owns `Ctrl+=`/`Ctrl+-` (they insert `РАВНО`/`СЛОЖЕНИЕ`/`ВЫЧИТАНИЕ`) |

### Also in this session

* Closing the window now stops the interpreter (`closeEvent` → `stop_program()`):
  before that, a close left a live `prologd` behind, and the headless suite
  collected one process per test (~27 by the end of a run).
* The user approved the shared document set — two panes, one text per buffer, an
  edit in either pane is the same edit (`doc/gui.typ`, §2.1).
* A *test* bug cost an hour and is worth remembering: the status line says
  `решение найдено` for an answer and `решения нет` for a failing one, so waiting
  for the whole word `решение` never matched a failing query and the finished run
  looked like a hang for the full 15 s timeout.  `wait_for_result` matches the
  stem `решени` now.

### Tests

`test_icons.py` (referenced-vs-present audit, a `MISSING` name must have no file,
`--icons DIR` override, all 28 shipped files load) and the new checks in
`test_window.py` (menu structure, toolbar reuse, view switches, the recent menu,
the context menu, the size control, save-before-run, split panes).  All twelve GUI
scripts pass.
