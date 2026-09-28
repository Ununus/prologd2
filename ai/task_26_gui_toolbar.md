# task_26 — GUI: menu bar, toolbar and icons

**Status:** not started
**Depends on:** task_22 (actions exist), task_25 (file actions)
**Milestone:** M11

## Goal

Give every action a place in the menus and on the toolbar, and use the icons the
user copied from the previous project.  Report what is missing instead of
drawing a text-only button.

## Deliverables

- [ ] `prologd_gui/assets.py` — load an icon by name from `src/gui/assets`,
      cached, with `--icons DIR` on `main.py` to point elsewhere; a missing file
      is a text-only action plus one warning in the log, never a crash.
- [ ] Menu bar, structured like the reference GUI:
  * **Файл**: Новый, Открыть…, Последние, Сохранить, Сохранить как…, Сохранить
    все, Перечитать, Закрыть, Закрыть все, Выход;
  * **Правка**: Отменить, Повторить, Вырезать, Копировать, Вставить, Удалить,
    Выделить всё, Закомментировать `Ctrl+K`, Раскомментировать `Ctrl+U`,
    Форматировать `Ctrl+I`, Настройки…;
  * **Поиск**: Поиск/Замена `Ctrl+F`, Далее `F3`, Назад `Shift+F3`, Найти
    выделенное `Ctrl+F3`, Найти выделенное назад `Ctrl+Shift+F3`;
  * **Вид**: Панель инструментов, Панель вывода `F4`, Сменить ориентацию
    сплита `Ctrl+F4`, Номера строк, Разделить редактор, Масштаб (`Ctrl+±`),
    Полный экран `F11`, Тема;
  * **Выполнение**: Запуск `F5`, Запуск с трассировкой, Шаг `F10`, Остановить
    `Shift+F5`, Сохранять перед запуском;
  * **Справка**: Справка (`doc/help.typ` → PDF/HTML if present, else the
    `--help` text), О программе.
- [ ] Toolbar grouped as in the reference GUI: file | run/stop/step |
      graphics/help | comment/uncomment/format | settings, plus the font-size
      control and a spacer; every action that exists in a menu and is useful
      while typing also appears on the toolbar.
- [ ] Actions are created once (`actions.py`) and reused by the menus, the
      toolbar and the context menu of the editor, so shortcut, tooltip and
      enable/disable state cannot drift; view actions are checkable and their
      state is persisted (task_29).
- [ ] An icon audit: a table in `src/gui/README.md` listing every icon name the
      code references, the file that provides it, and the entries that are
      expected to be missing until the user draws them (see below).
- [ ] Tests: `src/gui/tests/test_icons.py` — every referenced icon exists in
      `assets/`, or is in the documented `MISSING` list in `assets.py`; this
      fails as soon as a name is misspelled.

## Icons: what exists and what is missing

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
