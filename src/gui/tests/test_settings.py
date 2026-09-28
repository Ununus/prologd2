"""Checks of the settings store (no display, no interpreter).

    python src/gui/tests/test_settings.py

Every test uses a file of its own, so running them cannot touch the real
configuration — and the default path is checked separately without writing.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui.settings import (  # noqa: E402
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    Settings,
    default_path,
)


def test_defaults_are_used_on_an_empty_file(directory: pathlib.Path) -> None:
    settings = Settings(directory / "gui.ini")
    assert settings.font_family == DEFAULT_FONT_FAMILY
    assert settings.font_size == DEFAULT_FONT_SIZE
    assert settings.line_numbers is True
    assert settings.indent_character == "\t"
    assert settings.indent_width == 1
    assert settings.theme == "light"
    print("ok: defaults")


def test_values_survive_a_new_instance(directory: pathlib.Path) -> None:
    path = directory / "gui.ini"
    settings = Settings(path)
    settings.font_family = "Consolas"
    settings.font_size = 14.0
    settings.line_numbers = False
    settings.indent_character = " "
    settings.indent_width = 4
    settings.theme = "system"
    assert path.exists(), "the file is written as soon as a value is set"

    reopened = Settings(path)
    assert reopened.font_family == "Consolas"
    assert reopened.font_size == 14.0
    assert reopened.line_numbers is False
    assert reopened.indent_character == " "
    assert reopened.indent_width == 4
    assert reopened.theme == "system"
    print("ok: values are persisted and read back")


def test_broken_values_fall_back_instead_of_breaking_the_window(
    directory: pathlib.Path,
) -> None:
    path = directory / "gui.ini"
    path.write_text(
        "[editor]\n"
        "font_size=огромный\n"
        "line_numbers=не знаю\n"
        "indent_character=x\n"
        "indent_width=1000\n"
        "[view]\n"
        "theme=\n",
        encoding="utf-8",
    )
    settings = Settings(path)
    assert settings.font_size == DEFAULT_FONT_SIZE
    assert settings.line_numbers is False  # not a truthy spelling
    assert settings.indent_character == "\t"
    assert settings.indent_width == 16  # clamped, not accepted
    print("ok: unreadable values fall back, out-of-range values are clamped")


def test_setters_clamp(directory: pathlib.Path) -> None:
    settings = Settings(directory / "gui.ini")
    settings.font_size = 1000
    assert settings.font_size == 72
    settings.font_size = 1
    assert settings.font_size == 6
    settings.indent_width = 0
    assert settings.indent_width == 1
    print("ok: what is written is already inside the bounds")


def test_unknown_keys_survive(directory: pathlib.Path) -> None:
    """A newer version's keys must not be dropped by an older one (task_29)."""
    path = directory / "gui.ini"
    path.write_text("[editor]\nfont_size=12\n[future]\nthing=42\n", encoding="utf-8")
    settings = Settings(path)
    settings.font_size = 13.0

    text = path.read_text(encoding="utf-8")
    assert "font_size=13" in text, text
    assert "thing=42" in text, text
    # The file is rewritten whole on every change, so what matters is that a key
    # this version does not understand is still there afterwards.  (QSettings
    # writes `future/thing` as `future\thing` — the separator is its own.)
    assert settings.raw_value("future/thing") == "42"
    assert "future/thing" in settings.all_keys()
    print("ok: keys this version does not know are preserved")


def test_the_default_path_is_under_the_user_configuration() -> None:
    """The default path is derived from the application name, so check the whole path.

    `main.py` sets these names before it builds the window; if it stopped doing
    that, the settings would silently move to a nameless directory.
    """
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.setOrganizationName(Settings.organization)
    QCoreApplication.setApplicationName(Settings.application)
    path = default_path()
    assert path.name == "gui.ini", path
    assert Settings.organization in path.parts, path
    assert Settings.application in path.parts, path
    print(f"ok: default settings path is {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="prologd_gui_settings_") as name:
        directory = pathlib.Path(name)
        test_defaults_are_used_on_an_empty_file(directory)
        test_values_survive_a_new_instance(directory)
        test_broken_values_fall_back_instead_of_breaking_the_window(directory)
        test_setters_clamp(directory)
        test_unknown_keys_survive(directory)
    test_the_default_path_is_under_the_user_configuration()
    print("all settings checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
