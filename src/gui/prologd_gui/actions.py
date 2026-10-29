"""Every command in one place: its title, icon, keys and state.

Menu bar, toolbar and context menus are built from these tables, so a shortcut, a
tooltip or an enabled state cannot exist in two versions and drift apart: the window
makes one `QAction` per entry and finds it by key.

`implemented=False` stays visible but disabled, its tooltip saying what it waits for
— a menu that silently lacks half the feature list is worse than one that admits it.

**The ellipsis means «the command asks for something first»** (`Открыть…`,
`Настройки…`, `Поиск и замена…`).  A command that acts at once gets none, even when
it opens a window of its own: the ellipsis promises a question, not a window.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The recent-files entry is a submenu, not a command: it is built by the window
#: and named here so the icon audit sees it.
RECENT_ICON = "file-recent"

#: The lens of the find bar (task_33): the picture at the left of the field and,
#: since 2026-10-01, the picture of «Поиск и замена…» itself (it was
#: `edit-find-replace` — a magnifier over an `R`, which reads as «замена» rather
#: than as «поиск»).  Not an action of its own: the bar is built by the window.
FIND_ICON = "search-find"

#: The picture of «замена» — a magnifier over an `R`: the «Замена» triangle of
#: the find bar, the control that opens the replacement half.  The other four
#: «Поиск» commands carry their own search pictures.
REPLACE_ICON = "edit-find-replace"

#: The picture of the format *mode* control (task_47): one shape on the toolbar
#: whose menu carries the mode and the «только выделенное» switch.  It is not an
#: action, so it is named here for the audit like the other pictures that belong
#: to a control rather than to a command.
FORMAT_ICON = "edit-format-set"

#: Names that belong to no action: the tab picture of a buffer (never saved,
#: saved, modified) and the application icon.  They live here because
#: `ICON_NAMES` is the list `test_icons.py` holds the code to.
FILE_ICON = "file"
SAVED_ICON = "file-saved"
MODIFIED_ICON = "file-modified"
APPLICATION_ICON = "prologd2"

#: The picture of the appearance (`view-theme`).  The theme is a submenu now, so
#: the name belongs to no action — but it stays in the audit: it is the picture the
#: reference front-end used for exactly this, and it is still not drawn.
THEME_ICON = "view-theme"

#: The two buttons beside the «Дополнительные каталоги ИМПОРТ» list (the settings
#: dialog's `dirs` row): «Добавить…» and «Убрать».  They are controls, not
#: actions, so they are named here for the audit like the other control pictures.
ADD_ICON = "settings-add"
REMOVE_ICON = "settings-remove"

#: A menu entry that is a separator or a submenu rather than an action.
SEPARATOR = "-"
RECENT = "recent"

#: The formatter's mode (task_30, on the toolbar since task_47): the mode and the
#: «только выделенное» switch, next to the command they change — a mode is switched
#: *while looking at the code*.
FORMAT_MODE = "#format-mode"

#: The appearance (task_29's dark theme): a submenu of «Вид», because a *set* of
#: three themes is not something one checkable entry can say.  It used to be a
#: checkable «Системная тема (иначе светлая)», which had exactly two states — and a
#: third one would have made the title a lie.
THEME_MODE = "#theme-mode"

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
    # The one navigation command the editor has, and the reason the engine's search
    # order lives in `paths.resolve_import` — the window must open what the run would
    # load.  On an `ИМПОРТ` line it opens the file the directive names (task_69); on
    # any other name it goes to the first clause of that name, in this file or in an
    # import (task_103).  One key for one question: «где это».
    Action("open_import", "Перейти к определению", "file-open", ("F12",)),
    # The output pane as a file: a log of the run, written as plain text.
    Action("save_output", "Сохранить вывод…", "file-save-as"),
    Action("close", "Закрыть вкладку", "file-close", ("Ctrl+W",)),
    Action("close_all", "Закрыть все", "file-close-all"),
    # The context menu of a tab (task_68), with «Открыть…»'s picture.  The keys are a
    # plain `Ctrl`+letter: `Shift+Alt+R` never arrived — the Windows layout switch eats
    # Alt chords and the editor typed an `R`.
    Action("reveal", "Показать в проводнике", "file-open", ("Ctrl+E",)),
    Action("exit", "Выход", "file-exit", ("Ctrl+Q",)),
    # -- edit
    Action("undo", "Отменить", "edit-undo", ("Ctrl+Z",)),
    Action("redo", "Повторить", "edit-redo", ("Ctrl+Y", "Ctrl+Shift+Z")),
    Action("cut", "Вырезать", "edit-cut", ("Ctrl+X",)),
    Action("copy", "Копировать", "edit-copy", ("Ctrl+C",)),
    Action("paste", "Вставить", "edit-paste", ("Ctrl+V",)),
    Action("delete", "Удалить", "edit-del", ("Del",)),
    # `Shift+Del` takes the whole line, not the tail of it: the command says
    # «строка», and it is what every editor with this key does.  No picture: the
    # `edit-del` drawing belongs to «Удалить» above, and two commands in one menu
    # wearing the same picture read as one command.
    Action("delete_line", "Удалить строку", None, ("Shift+Del",)),
    Action("select_all", "Выделить всё", "select-all", ("Ctrl+A",)),
    Action("comment", "Закомментировать", "edit-comment", ("Ctrl+K",)),
    Action("uncomment", "Раскомментировать", "edit-uncomment", ("Ctrl+U",)),
    # The picture is `execution-clear` (task_71): the first try, `edit-clear`, was
    # drawn and thrown away in task_58 — it read as something other than «clear the
    # output» — so the command went word-only until a glyph of its own arrived.
    Action("clear_output", "Очистить вывод", "execution-clear", ("Ctrl+L",)),
    Action("format", "Форматировать", "edit-format", ("Ctrl+I",)),
    # «Настройки…» was the last disabled entry that named a task file (task_29).
    # No key of its own: the menu is where it is looked for, and every `Ctrl`
    # chord on the main row belongs to the insert table of task_31.
    Action("settings", "Настройки…", "tools-settings"),
    # -- search
    Action(
        "find",
        "Поиск и замена…",
        FIND_ICON,
        ("Ctrl+F",),
    ),
    Action(
        "find_next",
        "Далее",
        "search-find-next",
        ("F3",),
    ),
    Action(
        "find_prev",
        "Назад",
        "search-find-prev",
        ("Shift+F3",),
    ),
    # -- view
    # Both switches are text-only on purpose: a checkable entry of «Вид» says what
    # it does in words, and the two pictures (`view-toolbar`, `view-line-numbers`)
    # were never drawn — asking for them was a to-do that kept the audit noisy
    # (task_48).
    Action("toolbar", "Панель инструментов", None, checkable=True),
    # The output panel: `F4` shows and hides it, `Ctrl+F4` moves it between the
    # right side and the bottom (`split_orientation` keeps the reference's name
    # for the command; the icon hints at the *other* position).
    Action("output", "Панель вывода", "view-output", ("F4",), checkable=True),
    # The goal field and the console under it.  No key of its own: a run shows the
    # output panel by itself (part 92), and hiding the goal field is an act in the
    # menu rather than something that happens while a question is typed.
    Action("query", "Панель ввода цели", None, checkable=True),
    Action("split", "Разделить редактор", "view-split-editor", ("Ctrl+\\",)),
    Action("merge", "Объединить редакторы", "view-unite-editor", ("Ctrl+Shift+\\",)),
    Action("next_tab", "Следующая вкладка", None, ("Ctrl+Tab",)),
    Action("previous_tab", "Предыдущая вкладка", None, ("Ctrl+Shift+Tab",)),
    Action("split_orientation", "Сменить ориентацию сплита", "view-output-change-orient", ("Ctrl+F4",)),
    Action("line_numbers", "Номера строк", None, checkable=True),
    # Long clauses are easier to read wrapped, but a log line cut in the middle is
    # not — so this switch is the *editor's*, and the output stays as it is.
    Action("wrap", "Переносить длинные строки", None, checkable=True),
    # The zoom keys are the *keypad* ones: `Ctrl+=`, `Ctrl+-` and `Ctrl+Shift+=`
    # sit on the main row, where task_31 puts the insertions (`РАВНО(,)`,
    # `СЛОЖЕНИЕ(,,)`, `-`, `_`).  Qt spells the keypad `+` as `Num++` (it is a
    # different combination from `+`: the keypad modifier is part of the sequence).
    Action("zoom_in", "Увеличить шрифт", "view-zoom-in", ("Ctrl+Num++",)),
    Action("zoom_out", "Уменьшить шрифт", "view-zoom-out", ("Ctrl+Num+-",)),
    Action("zoom_reset", "Обычный размер шрифта", "view-zoom-reset", ("Ctrl+0",)),
    Action("full_screen", "Полный экран", "view-full-screen", ("F11",), checkable=True),
    # -- execution
    Action("run", "Запустить", "execution-execute", ("F5", "Ctrl+R")),
    Action("run_trace", "Запустить с трассировкой", "execution-tracing"),
    Action("step", "Шаг", "execution-step-into", ("F10",)),
    Action("step_over", "Шаг с обходом", "execution-step-over", ("Shift+F10",)),
    Action("stop", "Остановить", "execution-abort", ("Shift+F5",)),
    Action("save_before_run", "Сохранять перед запуском", None, checkable=True),
    # The answer table (task_59): the answer of a *single* goal — a goal typed into
    # the query line or a click on a question's margin marker — is shown as a grid
    # in the «Таблица» tab as well: columns are the goal's variables, rows are the
    # solutions.  Text-only, like the two switches under it: a checkable entry says
    # what it does in words, and a picture would have to say «table» twice.
    Action("answer_table", "Формировать таблицу", None, checkable=True),
    # The two switches of a run (task_46): run the program's own `?`-statements, and
    # print each before its answer.  Settings with the same titles — the menu is the
    # second door, because these are flipped *while working* (task_58).  «Сохранять
    # перед запуском» stayed a setting: it is decided once.
    Action("run_questions", "Выполнять вопросы при запуске", None, checkable=True),
    Action("print_questions", "Печатать вопросы при запуске", None, checkable=True),
    # The window the graphics predicates draw into (task_45): a window of its own,
    # so the picture can go to a second screen and does not take space from the
    # code.  Checkable, like the output panel: its state is the window's
    # visibility, and both survive a restart (`view/graphics_visible`).
    Action("graphics", "Графическое окно", "view-graphics", checkable=True),
    # -- scripts
    # The window's own tools (ADR-036): «Сконвертировать картинку…» runs
    # `tools/image_to_pld.py` and puts what it printed into a new tab.  It is not
    # part of running a program, so it gets a menu of its own.
    Action("script_image", "Сконвертировать картинку…", None),
    # -- help
    # The reference of a predicate (task_37): the same picture as «справка», the answer
    # coming from `doc/builtins.json` in the window.  `F1` answers what is needed
    # *while reading a program*; the manual keeps `Shift+F1`.
    Action("reference", "Справка по предикату", "help", ("F1",)),
    Action("help_doc", "Руководство пользователя", "help", ("Shift+F1",)),
    # What `Ctrl`+key inserts, listed from the table itself (task_31): the table
    # is data in the settings file, so the list has to be read from it.
    Action("shortcuts", "Шпаргалка по вставкам", None),
    Action("help_gui", "Справка по окну", None),
    # «О программе» wears the application icon: it *is* the same picture, and two
    # files for one drawing is a file that goes stale (task_48).
    Action("about", "О программе", APPLICATION_ICON),
)

BY_KEY: dict[str, Action] = {action.key: action for action in ACTIONS}

#: Every icon name the code can ask for — what `test_icons.py` checks against the
#: files in `assets/` and against the documented `MISSING` list.
ICON_NAMES: frozenset[str] = frozenset(
    [action.icon for action in ACTIONS if action.icon]
    + [RECENT_ICON, FIND_ICON, REPLACE_ICON, FORMAT_ICON, FILE_ICON,
       SAVED_ICON, MODIFIED_ICON, APPLICATION_ICON, THEME_ICON, ADD_ICON, REMOVE_ICON]
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
            "save_output",
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
            "delete_line",
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
    ("Поиск", ("find", "find_next", "find_prev")),
    (
        "Вид",
        (
            "toolbar",
            SEPARATOR,
            "output",
            "query",
            SEPARATOR,
            "split",
            "merge",
            "split_orientation",
            SEPARATOR,
            "next_tab",
            "previous_tab",
            SEPARATOR,
            "line_numbers",
            "wrap",
            "zoom_in",
            "zoom_out",
            "zoom_reset",
            SEPARATOR,
            THEME_MODE,
            "full_screen",
        ),
    ),
    (
        "Выполнение",
        (
            "run",
            "run_trace",
            "step",
            "step_over",
            "stop",
            SEPARATOR,
            "answer_table",
            "run_questions",
            "print_questions",
            SEPARATOR,
            "clear_output",
            "graphics",
        ),
    ),
    (
        "Скрипты",
        ("script_image",),
    ),
    (
        "Справка",
        ("reference", "help_doc", SEPARATOR, "shortcuts", SEPARATOR, "help_gui", "about"),
    ),
)

#: The toolbar: files, run/stop/step, editing (with the format mode right after
#: «Форматировать»), then the tools and the size control — it acts on the text, not on
#: the run (task_58).  No «Руководство» (a PDF nobody opens mid-run), no «Сохранить
#: все» (a command on every tab belongs in «Файл», task_48).
TOOLBAR: tuple[str, ...] = (
    "new",
    "open",
    "save",
    SEPARATOR,
    "run",
    "stop",
    "step",
    SEPARATOR,
    "comment",
    "uncomment",
    "format",
    FORMAT_MODE,
    SEPARATOR,
    "graphics",
    SEPARATOR,
    "settings",
)

#: The context menu of an editor *tab* (task_68), built from the same table as
#: the menu bar and the editor's own menu.  One command for now: the tab knows its
#: file, and showing it where it lives is what a right click on a tab most often
#: wants.
TAB_CONTEXT: tuple[str, ...] = ("reveal",)

#: The context menu of the panel's own tab bar (task_71).  Only the «Вывод» tab has
#: a command of its own: the other tabs show what the interpreter said, and there is
#: nothing to do *to* them, so a right click elsewhere in that bar offers no menu at
#: all — an empty one would be a puzzle.
PANEL_TAB_CONTEXT: tuple[str, ...] = ("clear_output",)

#: The editor's context menu, built from the same actions.
CONTEXT: tuple[str, ...] = (
    "open_import",
    SEPARATOR,
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
    "format",
    SEPARATOR,
    "select_all",
)
