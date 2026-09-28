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
INDENT_CHARACTER = "editor/indent_character"
INDENT_WIDTH = "editor/indent_width"
THEME = "view/theme"

DEFAULT_FONT_FAMILY = "Cascadia Mono"
DEFAULT_FONT_SIZE = 11.0
DEFAULT_THEME = "light"

MINIMUM_FONT_SIZE = 6.0
MAXIMUM_FONT_SIZE = 72.0

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

    # -- view ---------------------------------------------------------------
    @property
    def theme(self) -> str:
        return self._text(THEME, DEFAULT_THEME)

    @theme.setter
    def theme(self, value: str) -> None:
        self._write(THEME, str(value))
