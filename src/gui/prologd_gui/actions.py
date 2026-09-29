"""Every command in one place: its title, icon, keys and state.

The menu bar, the toolbar and the editor's context menu are all built from these
tables, so a shortcut, a tooltip or an enabled/disabled state cannot exist in two
versions and drift apart: the window makes one `QAction` per entry and finds it by
key.

Entries with `implemented=False` stay visible but disabled, and their tooltip says
what they wait for.  The feature list is long, and a menu that silently lacks half
of it is worse than one that admits it — `doc/gui.typ`, section 9, has the same
list in prose.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The recent-files entry is a submenu, not a command: it is built by the window
#: and named here so the icon audit sees it.
RECENT_ICON = "file-recent"

#: A menu entry that is a separator or a submenu rather than an action.
SEPARATOR = "-"
RECENT = "recent"

#: The font-size control, not an action either: the window puts it here.
FONT_SIZE = "#font"


@dataclass(frozen=True)
class Action:
    """One command."""

    key: str
    title: str
    icon: str | None = None
    shortcuts: tuple[str, ...] = ()
    checkable: bool = False
    implemented: bool = True
    #: What a disabled entry waits for, verbatim in its tooltip.
    waiting_for: str = ""

    def tooltip(self) -> str:
        """The whole tooltip: the title, its keys, and why it may be disabled."""
        if not self.implemented:
            return f"{self.title} — ещё не реализовано ({self.waiting_for})"
        if self.shortcuts:
            return f"{self.title} ({self.shortcuts[0]})"
        return self.title


ACTIONS: tuple[Action, ...] = (
    # -- file
    Action("new", "Новый", "file-new", ("Ctrl+N",)),
    Action("open", "Открыть…", "file-open", ("Ctrl+O",)),
    Action("save", "Сохранить", "file-save", ("Ctrl+S",)),
    Action("save_as", "Сохранить как…", "file-save-as", ("Ctrl+Shift+S",)),
    Action("save_all", "Сохранить все", "file-save-all"),
    Action("reload", "Перечитать с диска", "file-reload", ("Ctrl+Shift+R",)),
    Action("close", "Закрыть вкладку", "file-close", ("Ctrl+W",)),
    Action("close_all", "Закрыть все", "file-close-all"),
    Action("exit", "Выход", "file-exit", ("Ctrl+Q",)),
    # -- edit
    Action("undo", "Отменить", "edit-undo", ("Ctrl+Z",)),
    Action("redo", "Повторить", "edit-redo", ("Ctrl+Y", "Ctrl+Shift+Z")),
    Action("cut", "Вырезать", "edit-cut", ("Ctrl+X",)),
    Action("copy", "Копировать", "edit-copy", ("Ctrl+C",)),
    Action("paste", "Вставить", "edit-paste", ("Ctrl+V",)),
    Action("delete", "Удалить", None, ("Del",)),
    Action("select_all", "Выделить всё", None, ("Ctrl+A",)),
    Action("comment", "Закомментировать", "edit-comment", ("Ctrl+K",)),
    Action("uncomment", "Раскомментировать", "edit-uncomment", ("Ctrl+U",)),
    Action("clear_output", "Очистить вывод", "edit-clear", ("Ctrl+L",)),
    Action(
        "format",
        "Форматировать",
        "edit-format",
        ("Ctrl+I",),
        implemented=False,
        waiting_for="task_30",
    ),
    Action(
        "settings",
        "Настройки…",
        "tools-settings",
        implemented=False,
        waiting_for="task_29 — значения правятся в файле настроек",
    ),
    # -- search
    Action(
        "find",
        "Поиск и замена…",
        "edit-find-replace",
        ("Ctrl+F",),
        implemented=False,
        waiting_for="task_33",
    ),
    Action(
        "find_next",
        "Далее",
        "search-find-next",
        ("F3",),
        implemented=False,
        waiting_for="task_33",
    ),
    Action(
        "find_prev",
        "Назад",
        "search-find-prev",
        ("Shift+F3",),
        implemented=False,
        waiting_for="task_33",
    ),
    Action(
        "find_selected",
        "Найти выделенное",
        "search-find-selected-next",
        ("Ctrl+F3",),
        implemented=False,
        waiting_for="task_33",
    ),
    Action(
        "find_selected_prev",
        "Найти выделенное назад",
        "search-find-selected-prev",
        ("Ctrl+Shift+F3",),
        implemented=False,
        waiting_for="task_33",
    ),
    # -- view
    Action("toolbar", "Панель инструментов", "view-toolbar", checkable=True),
    Action(
        "output",
        "Панель вывода",
        "view-output-right",
        ("F4",),
        implemented=False,
        waiting_for="task_27",
    ),
    Action("split", "Разделить редактор", "view-split-editor", ("Ctrl+\\",)),
    Action("merge", "Объединить редакторы", None, ("Ctrl+Shift+\\",)),
    Action("next_tab", "Следующая вкладка", None, ("Ctrl+Tab",)),
    Action("previous_tab", "Предыдущая вкладка", None, ("Ctrl+Shift+Tab",)),
    Action(
        "split_orientation",
        "Сменить ориентацию сплита",
        None,
        ("Ctrl+F4",),
        implemented=False,
        waiting_for="task_27",
    ),
    Action("line_numbers", "Номера строк", "view-line-numbers", checkable=True),
    # The zoom keys are the *keypad* ones: `Ctrl+=` and `Ctrl+-` sit on the main
    # row, where task_31 puts the `РАВНО`/`СЛОЖЕНИЕ`/`ВЫЧИТАНИЕ` skeletons.  Qt
    # spells the keypad `+` as `Num++` (it is a different combination from `+`:
    # the keypad modifier is part of the sequence).
    Action("zoom_in", "Увеличить шрифт", "view-zoom-in", ("Ctrl+Num++",)),
    Action("zoom_out", "Уменьшить шрифт", "view-zoom-out", ("Ctrl+Num+-",)),
    Action("zoom_reset", "Обычный размер шрифта", "view-zoom-reset", ("Ctrl+0",)),
    Action("theme", "Системная тема (иначе светлая)", "view-theme", checkable=True),
    Action("full_screen", "Полный экран", "view-full-screen", ("F11",), checkable=True),
    # -- execution
    Action("run", "Запустить", "execution-execute", ("F5", "Ctrl+R")),
    Action(
        "run_trace",
        "Запустить с трассировкой",
        "execution-tracing",
        implemented=False,
        waiting_for="task_28",
    ),
    Action(
        "step",
        "Шаг",
        "execution-step-into",
        ("F10",),
        implemented=False,
        waiting_for="task_28",
    ),
    Action("stop", "Остановить", "execution-abort", ("Shift+F5", "Ctrl+.")),
    Action("save_before_run", "Сохранять перед запуском", None, checkable=True),
    Action(
        "graphics",
        "Графическое окно",
        "view-graphics",
        implemented=False,
        waiting_for="task_27",
    ),
    # -- help
    Action("help_doc", "Руководство пользователя", "help", ("F1",)),
    Action("help_gui", "Справка по окну", None),
    Action("about", "О программе", "help-about"),
)

BY_KEY: dict[str, Action] = {action.key: action for action in ACTIONS}

#: Every icon name the code can ask for — what `test_icons.py` checks against the
#: files in `assets/` and against the documented `MISSING` list.
ICON_NAMES: frozenset[str] = frozenset(
    [action.icon for action in ACTIONS if action.icon] + [RECENT_ICON]
)

#: The menu bar: (title, entries).  `-` is a separator, `recent` the submenu of
#: last-opened files, `FONT_SIZE` the size control that only the toolbar has.
MENUS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Файл",
        (
            "new",
            "open",
            RECENT,
            SEPARATOR,
            "save",
            "save_as",
            "save_all",
            "reload",
            SEPARATOR,
            "close",
            "close_all",
            SEPARATOR,
            "exit",
        ),
    ),
    (
        "Правка",
        (
            "undo",
            "redo",
            SEPARATOR,
            "cut",
            "copy",
            "paste",
            "delete",
            SEPARATOR,
            "select_all",
            SEPARATOR,
            "comment",
            "uncomment",
            "format",
            SEPARATOR,
            "settings",
        ),
    ),
    ("Поиск", ("find", "find_next", "find_prev", SEPARATOR, "find_selected", "find_selected_prev")),
    (
        "Вид",
        (
            "toolbar",
            SEPARATOR,
            "output",
            SEPARATOR,
            "split",
            "merge",
            "split_orientation",
            SEPARATOR,
            "next_tab",
            "previous_tab",
            SEPARATOR,
            "line_numbers",
            "zoom_in",
            "zoom_out",
            "zoom_reset",
            SEPARATOR,
            "theme",
            "full_screen",
        ),
    ),
    (
        "Выполнение",
        ("run", "run_trace", "step", "stop", SEPARATOR, "save_before_run", SEPARATOR, "graphics"),
    ),
    ("Справка", ("help_doc", "help_gui", "about")),
)

#: The toolbar, grouped as the reference front-end had it: files, run/stop/step,
#: editing, then the size control, then the tools — and, at the far right,
#: «Очистить вывод», which acts on the output rather than on the program.
TOOLBAR: tuple[str, ...] = (
    "new",
    "open",
    "save",
    "save_all",
    SEPARATOR,
    "run",
    "stop",
    "step",
    SEPARATOR,
    "comment",
    "uncomment",
    "format",
    SEPARATOR,
    FONT_SIZE,
    SEPARATOR,
    "graphics",
    SEPARATOR,
    "settings",
    "help_doc",
    SEPARATOR,
    "clear_output",
)

#: The editor's context menu, built from the same actions.
CONTEXT: tuple[str, ...] = (
    "undo",
    "redo",
    SEPARATOR,
    "cut",
    "copy",
    "paste",
    "delete",
    SEPARATOR,
    "comment",
    "uncomment",
    SEPARATOR,
    "select_all",
)
