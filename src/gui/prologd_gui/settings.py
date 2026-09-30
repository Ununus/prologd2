"""Persisted preferences.

Small on purpose: this holds what the window already uses (font, line numbers,
indent, theme) and nothing more.  Task_29 adds the dialog, the rest of the list
and the "unknown keys are preserved" rule — which `QSettings` gives for free, as
long as values are read through here rather than written over the whole file.

A value that cannot be read (a hand-edited file, or a string where a number used
to be) falls back to the default instead of taking the window down with it.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

ORGANIZATION = "PrologD"
APPLICATION = "gui"

FONT_FAMILY = "editor/font_family"
FONT_SIZE = "editor/font_size"
LINE_NUMBERS = "editor/line_numbers"
WRAP = "editor/wrap"
INDENT_CHARACTER = "editor/indent_character"
INDENT_WIDTH = "editor/indent_width"
COMPLETION = "editor/completion"
AUTO_COMPLETE_AFTER = "editor/auto_complete_after"
THEME = "view/theme"
RECENT_FILES = "files/recent"
LAST_DIRECTORY = "files/last_directory"
SPLIT_EDITOR = "view/split"
SPLIT_SIZES = "view/split_sizes"
RESTORE_SPLIT = "view/restore_split"
TOOLBAR = "view/toolbar"
OUTPUT_POSITION = "view/output_position"
OUTPUT_VISIBLE = "view/output_visible"
INPUT_QUEUE = "view/input_queue"
OUTPUT_SIZES = "view/output_sizes"
PANEL_SIZES = "view/panel_sizes"
SAVE_BEFORE_RUN = "execution/save_before_run"
FORMAT_MODE = "format/mode"
FORMAT_WIDTH = "format/width"
FORMAT_INDENT = "format/indent"
FORMAT_UNIT = "format/unit"
FORMAT_SELECTION = "format/selection"

DEFAULT_FONT_FAMILY = "Cascadia Mono"
DEFAULT_FONT_SIZE = 11.0
DEFAULT_THEME = "light"

#: Where the output (with the input queue under it) sits: to the right of the
#: editor or under it.  `Ctrl+F4` moves it, `F4` hides it.
DEFAULT_OUTPUT_POSITION = "right"
OUTPUT_POSITIONS = ("right", "bottom")

MINIMUM_FONT_SIZE = 6.0
MAXIMUM_FONT_SIZE = 72.0

#: How many characters are typed before the popup appears by itself.
DEFAULT_AUTO_COMPLETE_AFTER = 2
MINIMUM_AUTO_COMPLETE_AFTER = 1
MAXIMUM_AUTO_COMPLETE_AFTER = 10

#: The formatter (task_30): the three shapes the «Правка → Формат» menu offers —
#: «в одну строку», «мягкое» (цели собираются до ширины) и «жёсткое» (по цели
#: на строку).  «Не менять» ушёл: ненажатая команда и есть «не менять», а
#: из жёсткого обратно в мягкое теперь можно — мягкое строит строки заново.
DEFAULT_FORMAT_MODE = "soft"
FORMAT_MODES = ("line", "soft", "hard")
DEFAULT_FORMAT_WIDTH = 80
MINIMUM_FORMAT_WIDTH = 20
MAXIMUM_FORMAT_WIDTH = 1000
DEFAULT_FORMAT_INDENT = 1
MINIMUM_FORMAT_INDENT = 1
MAXIMUM_FORMAT_INDENT = 8
DEFAULT_FORMAT_UNIT = "tab"
FORMAT_UNITS = ("tab", "spaces")

_TRUE = ("1", "true", "yes", "y", "да")


def default_path() -> Path:
    """`%LOCALAPPDATA%\\PrologD\\gui\\gui.ini` on Windows, the XDG equivalent elsewhere.

    `AppConfigLocation` is `AppLocalDataLocation` on Windows (the *local*, not the
    roaming directory) and is derived from the organisation and application name,
    so `main.py` sets both on `QCoreApplication` before the first call here.
    """
    directory = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(directory or ".") / "gui.ini"


class Settings:
    """Typed access to the ini file, with the bounds applied on read."""

    #: Also the names `main.py` sets on `QCoreApplication`, because `default_path`
    #: is derived from them.
    organization = ORGANIZATION
    application = APPLICATION

    def __init__(self, filename: str | Path | None = None) -> None:
        self.path = Path(filename) if filename is not None else default_path()
        self._store = QSettings(str(self.path), QSettings.Format.IniFormat)

    # -- reading helpers ----------------------------------------------------
    def _text(self, key: str, default: str) -> str:
        value = self._store.value(key, default)
        return default if value is None else str(value)

    def _flag(self, key: str, default: bool) -> bool:
        value = self._store.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in _TRUE
        return bool(value)

    def _number(self, key: str, default: float, low: float, high: float) -> float:
        try:
            value = float(self._store.value(key, default))
        except (TypeError, ValueError):
            return default
        if value != value:  # NaN, which compares false against everything
            return default
        return min(high, max(low, value))

    def _write(self, key: str, value: object) -> None:
        self._store.setValue(key, value)
        # Written straight away rather than on destruction: a crashed or killed
        # window would otherwise lose the settings the user just changed, and
        # there are few enough of them for the write to cost nothing.
        self._store.sync()

    def raw_value(self, key: str, default: object = None) -> object:
        """A value this class has no property for (task_29's dialog reads these)."""
        return self._store.value(key, default)

    def all_keys(self) -> list[str]:
        """Every key in the file, known to this class or not."""
        return list(self._store.allKeys())

    # -- editor -------------------------------------------------------------
    @property
    def font_family(self) -> str:
        return self._text(FONT_FAMILY, DEFAULT_FONT_FAMILY)

    @font_family.setter
    def font_family(self, value: str) -> None:
        self._write(FONT_FAMILY, str(value))

    @property
    def font_size(self) -> float:
        return self._number(FONT_SIZE, DEFAULT_FONT_SIZE, MINIMUM_FONT_SIZE, MAXIMUM_FONT_SIZE)

    @font_size.setter
    def font_size(self, value: float) -> None:
        self._write(FONT_SIZE, min(MAXIMUM_FONT_SIZE, max(MINIMUM_FONT_SIZE, float(value))))

    @property
    def line_numbers(self) -> bool:
        return self._flag(LINE_NUMBERS, True)

    @line_numbers.setter
    def line_numbers(self, value: bool) -> None:
        self._write(LINE_NUMBERS, bool(value))

    @property
    def wrap(self) -> bool:
        """Wrap long lines in the editor.  Off by default: a program line is read
        as a whole, and a wrapped one hides where the line really ends."""
        return self._flag(WRAP, False)

    @wrap.setter
    def wrap(self, value: bool) -> None:
        self._write(WRAP, bool(value))

    @property
    def indent_character(self) -> str:
        character = self._text(INDENT_CHARACTER, "\t")
        return character if character in ("\t", " ") else "\t"

    @indent_character.setter
    def indent_character(self, value: str) -> None:
        self._write(INDENT_CHARACTER, "\t" if value == "\t" else " ")

    @property
    def indent_width(self) -> int:
        return int(self._number(INDENT_WIDTH, 1, 1, 16))

    @indent_width.setter
    def indent_width(self, value: int) -> None:
        self._write(INDENT_WIDTH, int(min(16, max(1, value))))

    @property
    def completion(self) -> bool:
        return self._flag(COMPLETION, True)

    @completion.setter
    def completion(self, value: bool) -> None:
        self._write(COMPLETION, bool(value))

    @property
    def auto_complete_after(self) -> int:
        return int(
            self._number(
                AUTO_COMPLETE_AFTER,
                DEFAULT_AUTO_COMPLETE_AFTER,
                MINIMUM_AUTO_COMPLETE_AFTER,
                MAXIMUM_AUTO_COMPLETE_AFTER,
            )
        )

    @auto_complete_after.setter
    def auto_complete_after(self, value: int) -> None:
        self._write(
            AUTO_COMPLETE_AFTER,
            int(min(MAXIMUM_AUTO_COMPLETE_AFTER, max(MINIMUM_AUTO_COMPLETE_AFTER, value))),
        )

    # -- view ---------------------------------------------------------------
    @property
    def theme(self) -> str:
        return self._text(THEME, DEFAULT_THEME)

    @theme.setter
    def theme(self, value: str) -> None:
        self._write(THEME, str(value))

    # -- files -------------------------------------------------------------
    @property
    def recent_files(self) -> list[str]:
        """Newest first.  A single value comes back as a string, not a list."""
        value = self._store.value(RECENT_FILES, [])
        if isinstance(value, str):
            value = [value] if value else []
        return [str(item) for item in value or [] if str(item)]

    @recent_files.setter
    def recent_files(self, paths) -> None:
        self._write(RECENT_FILES, [str(path) for path in paths])

    @property
    def last_directory(self) -> str:
        """Where the open/save dialogs start; empty means "the current one"."""
        return self._text(LAST_DIRECTORY, "")

    @last_directory.setter
    def last_directory(self, value: str) -> None:
        self._write(LAST_DIRECTORY, str(value))

    # -- the split editor ---------------------------------------------------
    @property
    def split_editor(self) -> bool:
        """Whether the second editor pane was open."""
        return self._flag(SPLIT_EDITOR, False)

    @split_editor.setter
    def split_editor(self, value: bool) -> None:
        self._write(SPLIT_EDITOR, bool(value))

    @property
    def split_sizes(self) -> list[int]:
        """The widths of the two editor panes, as last seen."""
        value = self._store.value(SPLIT_SIZES, [])
        if isinstance(value, (int, str)):  # a single value is not a list
            value = [value] if value != "" else []
        sizes: list[int] = []
        for item in value or []:
            try:
                sizes.append(int(item))
            except (TypeError, ValueError):
                continue
        return sizes

    @split_sizes.setter
    def split_sizes(self, sizes) -> None:
        self._write(SPLIT_SIZES, [int(size) for size in sizes])

    @property
    def restore_split(self) -> bool:
        """Reopen the split editor on the next start.

        Named apart from the «восстанавливать вкладки» switch of task_29: this one
        only decides the panes, because the documents themselves are not reopened
        yet.
        """
        return self._flag(RESTORE_SPLIT, True)

    @restore_split.setter
    def restore_split(self, value: bool) -> None:
        self._write(RESTORE_SPLIT, bool(value))

    @property
    def toolbar_visible(self) -> bool:
        return self._flag(TOOLBAR, True)

    @toolbar_visible.setter
    def toolbar_visible(self, value: bool) -> None:
        self._write(TOOLBAR, bool(value))

    # -- the output panel ---------------------------------------------------
    @property
    def output_position(self) -> str:
        """`right` or `bottom`; anything else in the file reads as the default."""
        value = self._text(OUTPUT_POSITION, DEFAULT_OUTPUT_POSITION).strip().lower()
        return value if value in OUTPUT_POSITIONS else DEFAULT_OUTPUT_POSITION

    @output_position.setter
    def output_position(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(OUTPUT_POSITION, text if text in OUTPUT_POSITIONS else DEFAULT_OUTPUT_POSITION)

    @property
    def output_visible(self) -> bool:
        """Whether the output panel is shown at all (`F4` switches this)."""
        return self._flag(OUTPUT_VISIBLE, True)

    @output_visible.setter
    def output_visible(self, value: bool) -> None:
        self._write(OUTPUT_VISIBLE, bool(value))

    @property
    def input_queue(self) -> bool:
        """Whether the field of prepared answers is shown under the output.

        Hidden, its lines are not used at all: the point of hiding it is to answer
        from the console instead, and a field nobody can see must not decide what
        the program is told.
        """
        return self._flag(INPUT_QUEUE, True)

    @input_queue.setter
    def input_queue(self, value: bool) -> None:
        self._write(INPUT_QUEUE, bool(value))

    @property
    def output_sizes(self) -> list[int]:
        """The heights of the output and of the input queue inside the panel."""
        return self._sizes(OUTPUT_SIZES)

    @output_sizes.setter
    def output_sizes(self, sizes) -> None:
        self._write(OUTPUT_SIZES, [int(size) for size in sizes])

    @property
    def panel_sizes(self) -> list[int]:
        """The editor and the output panel as last seen — widths or heights,
        depending on which side the panel is on."""
        return self._sizes(PANEL_SIZES)

    @panel_sizes.setter
    def panel_sizes(self, sizes) -> None:
        self._write(PANEL_SIZES, [int(size) for size in sizes])

    def _sizes(self, key: str) -> list[int]:
        """A stored list of sizes, tolerating a hand-edited file.

        A single value comes back as a string rather than a list, and a value that
        is not a number is dropped instead of stopping the window from starting.
        """
        value = self._store.value(key, [])
        if isinstance(value, (int, str)):
            value = [value] if value != "" else []
        sizes: list[int] = []
        for item in value or []:
            try:
                sizes.append(int(item))
            except (TypeError, ValueError):
                continue
        return sizes

    # -- execution ----------------------------------------------------------
    @property
    def save_before_run(self) -> bool:
        """Write the current file before running it (the «Выполнение» switch)."""
        return self._flag(SAVE_BEFORE_RUN, False)

    @save_before_run.setter
    def save_before_run(self, value: bool) -> None:
        self._write(SAVE_BEFORE_RUN, bool(value))

    # -- the formatter (task_30) ---------------------------------------------
    @property
    def format_mode(self) -> str:
        """`line`, `soft` or `hard`; anything else in the file reads as `soft`.

        An ini written by an earlier build may say `none` (the retired «не
        менять»); the fallback turns that into the soft mode.
        """
        value = self._text(FORMAT_MODE, DEFAULT_FORMAT_MODE).strip().lower()
        return value if value in FORMAT_MODES else DEFAULT_FORMAT_MODE

    @format_mode.setter
    def format_mode(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(FORMAT_MODE, text if text in FORMAT_MODES else DEFAULT_FORMAT_MODE)

    @property
    def format_width(self) -> int:
        """What has to fit on one line in the soft mode, in code points."""
        return int(
            self._number(FORMAT_WIDTH, DEFAULT_FORMAT_WIDTH, MINIMUM_FORMAT_WIDTH,
                         MAXIMUM_FORMAT_WIDTH)
        )

    @format_width.setter
    def format_width(self, value: int) -> None:
        self._write(FORMAT_WIDTH, int(value))

    @property
    def format_indent(self) -> int:
        """How many indent units a continuation line starts with."""
        return int(
            self._number(FORMAT_INDENT, DEFAULT_FORMAT_INDENT, MINIMUM_FORMAT_INDENT,
                         MAXIMUM_FORMAT_INDENT)
        )

    @format_indent.setter
    def format_indent(self, value: int) -> None:
        self._write(FORMAT_INDENT, int(value))

    @property
    def format_unit(self) -> str:
        """`tab` or `spaces` — one tab is one unit, four spaces are one unit."""
        value = self._text(FORMAT_UNIT, DEFAULT_FORMAT_UNIT).strip().lower()
        return value if value in FORMAT_UNITS else DEFAULT_FORMAT_UNIT

    @format_unit.setter
    def format_unit(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(FORMAT_UNIT, text if text in FORMAT_UNITS else DEFAULT_FORMAT_UNIT)

    @property
    def format_selection(self) -> bool:
        """«Форматировать только выделенное»: with a selection, only it is sent."""
        return self._flag(FORMAT_SELECTION, False)

    @format_selection.setter
    def format_selection(self, value: bool) -> None:
        self._write(FORMAT_SELECTION, bool(value))
