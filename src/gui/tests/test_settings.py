"""Checks of the settings store and of the table the dialog is built from.

    python src/gui/tests/test_settings.py

Every test uses a file of its own, so running them cannot touch the real
configuration — and the default path is checked separately without writing.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import settings as settings_module  # noqa: E402
from prologd_gui.settings import (  # noqa: E402
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    SETTINGS,
    Settings,
    default_path,
)

from PySide6.QtCore import QSettings  # noqa: E402


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


def test_the_retired_naming_mode_reads_as_the_old_dialect(
    directory: pathlib.Path,
) -> None:
    """A stored or hand-written `2` is the old dialect, not the ISO default.

    `2` was a naming mode of its own until task_77, when it became a spelling of `1`.
    The row does not offer it any more, so without a deliberate answer `set_value`
    would take it for an unknown choice and write the setting's *default* — moving a
    reader who asked for the old dialect into ISO without a word.
    """
    path = directory / "legacy_mode.ini"
    settings = Settings(path)
    settings.variable_mode = "2"
    assert settings.variable_mode == "1"
    assert settings.variable_mode_number == 1

    # And the same value found in a file somebody edited by hand.
    path.write_text("[execution]\nvariable_mode=2\n", encoding="utf-8")
    hand = Settings(path)
    assert hand.variable_mode == "1"
    assert hand.variable_mode_number == 1
    print("ok: a retired `2` is read as the old dialect, not as the default")


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


def test_every_key_is_described_or_written_by_the_window() -> None:
    """Nothing may be stored without being classified (task_29).

    A key this module defines but nobody lists is either a preference the dialog
    has forgotten or a value the window writes for itself — and the difference
    matters: the first is a bug, the second is fine as long as it is named.  The
    keys are found by *shape* (`section/name`, lower case), so a new constant
    cannot slip through by being unused.
    """
    defined = {
        value
        for name, value in vars(settings_module).items()
        if name.isupper()
        and isinstance(value, str)
        and "/" in value
        and value == value.lower()
    }
    described = {setting.key for setting in SETTINGS}
    machine = set(settings_module.MACHINE_KEYS)
    assert not (described & machine), sorted(described & machine)
    forgotten = sorted(defined - described - machine)
    assert not forgotten, f"these keys are stored but nowhere described: {forgotten}"
    print(f"ok: {len(defined)} keys — {len(described)} in the dialog, {len(machine)} machine-managed")


def test_the_table_describes_usable_rows() -> None:
    """Every record is a row the dialog can build and the store can validate."""
    keys = [setting.key for setting in SETTINGS]
    assert len(keys) == len(set(keys)), "two rows for one key"
    for setting in SETTINGS:
        assert setting.section in settings_module.SECTIONS, setting.key
        assert setting.label and setting.label[0].isupper(), setting.key
        if setting.kind in ("int", "float"):
            assert setting.low is not None and setting.high is not None, setting.key
            assert setting.low <= float(setting.default) <= setting.high, setting.key
        if setting.kind == "choice":
            values = [value for value, _ in setting.choices]
            assert len(values) >= 2, setting.key
            assert setting.default in values, setting.key
            assert all(text for _, text in setting.choices), setting.key
        if setting.kind == "bool":
            assert isinstance(setting.default, bool), setting.key
    print(f"ok: {len(SETTINGS)} described settings, every one inside its own bounds")


def test_every_row_round_trips_and_resets(directory: pathlib.Path) -> None:
    """What the dialog writes is what it reads back — and «Сбросить» comes back."""
    settings = Settings(directory / "rows.ini")

    def is_default(setting) -> bool:
        value = settings.value_of(setting)
        # `dirs` keeps an empty *tuple* as its default (a frozen record cannot
        # hold a list), while the store always answers with a list.
        return list(value) == list(setting.default) if setting.kind == "dirs" else value == setting.default

    for setting in SETTINGS:
        assert is_default(setting), setting.key
    for setting in SETTINGS:
        if setting.kind == "bool":
            changed: object = not bool(setting.default)
        elif setting.kind in ("int", "float"):
            changed = setting.high
        elif setting.kind == "choice":
            changed = [value for value, _ in setting.choices if value != setting.default][0]
        elif setting.kind == "dirs":
            changed = ["/tmp/один", "C:/общие"][:1]
        else:
            changed = "что-то другое"
        settings.set_value(setting, changed)
        assert settings.value_of(setting) == changed, (setting.key, settings.value_of(setting))

    written = settings.reset()
    assert written == len(SETTINGS)
    for setting in SETTINGS:
        assert is_default(setting), setting.key
    print("ok: every described setting round-trips, and «Сбросить» restores the defaults")


def test_set_value_clamps_and_survives_junk(directory: pathlib.Path) -> None:
    settings = Settings(directory / "clamps.ini")
    for setting in SETTINGS:
        if setting.kind == "int":
            settings.set_value(setting, setting.high + 1000)
            assert settings.value_of(setting) == int(setting.high), setting.key
            settings.set_value(setting, "ерунда")
            assert settings.value_of(setting) == int(setting.default), setting.key
        elif setting.kind == "float":
            settings.set_value(setting, -100)
            assert settings.value_of(setting) == float(setting.low), setting.key
        elif setting.kind == "choice":
            settings.set_value(setting, "нет-такого")
            assert settings.value_of(setting) == setting.default, setting.key
    print("ok: out-of-range and unreadable values are clamped or replaced, never stored")


def test_reset_touches_only_described_settings(directory: pathlib.Path) -> None:
    """The recent list and the window geometry are not a preference to reset."""
    path = directory / "reset.ini"
    settings = Settings(path)
    settings.recent_files = ["C:/один.pld"]
    settings.panel_sizes = [500, 300]
    settings.font_size = 20.0
    settings.reset()
    assert settings.recent_files == ["C:/один.pld"], "«Сбросить» threw the recent list away"
    assert settings.panel_sizes == [500, 300]
    assert settings.font_size == DEFAULT_FONT_SIZE
    print("ok: reset restores the preferences, not the window's own records")


def test_export_and_import_carry_everything(directory: pathlib.Path) -> None:
    """A configuration moves between machines whole — unknown keys included."""
    source = Settings(directory / "export.ini")
    source.font_size = 17.0
    source.import_paths = ["C:/общие", "C:/курс"]
    target = directory / "для_класса.ini"
    assert source.export_to(target) > 0, "an empty store is exported with its defaults"

    read = Settings(target)
    assert read.font_size == 17.0
    assert read.import_paths == ["C:/общие", "C:/курс"]

    # A file from a newer build: the unknown key must survive the import *and*
    # live on next to what this version writes.
    foreign = directory / "новые.ini"
    foreign.write_text(
        "[editor]\nfont_size=9\n[будущее]\nthing=42\n", encoding="utf-8"
    )
    staged = source.read_keys(foreign)
    assert "будущее/thing" in staged, staged
    source.write_keys(staged)
    assert source.font_size == 9.0
    assert source.raw_value("будущее/thing") == "42"
    source.font_size = 10.0
    assert source.raw_value("будущее/thing") == "42", "a later write dropped the unknown key"

    try:
        source.read_keys(directory / "нет-такого.ini")
    except ValueError:
        pass
    else:  # pragma: no cover - the message is the point
        raise AssertionError("a missing file was read as a configuration")
    print("ok: export and import carry the whole file, unknown keys included")


def test_the_new_keys_have_the_documented_defaults(directory: pathlib.Path) -> None:
    """The defaults of task_29, one by one — they are the out-of-the-box window."""
    settings = Settings(directory / "new.ini")
    assert settings.output_font_size == settings.font_size, "the output starts at the editor's size"
    assert settings.output_line_limit == settings_module.DEFAULT_OUTPUT_LINE_LIMIT
    assert settings.current_line is True
    assert settings.completion_match_case is True
    assert settings.autosave_minutes == 0, "autosave is off until it is asked for"
    assert settings.recent_limit == settings_module.DEFAULT_RECENT_LIMIT
    assert settings.import_paths == []
    assert settings.auto_indent is True, "the editor indents until told otherwise"
    assert settings.follow_output is True, "the pane followed the end before the switch"
    assert settings.output_position == "bottom", "the panel sits at the bottom since task_50"
    assert settings.input_mode == settings_module.DEFAULT_INPUT_MODE == "panel"
    assert settings.run_questions is True, "a lesson is run to see its questions answered"
    assert settings.print_questions is False, "the question line is not echoed until asked"
    # task_46's guards: the engine itself has no limits at all, and the window
    # ships numbers a lesson cannot notice but a runaway cannot outlive — no step
    # cap, a million frames, a million solutions and no clock.  A limit nobody
    # asked for is left *off* the wire, so an engine that knows nothing about the
    # record sees exactly the traffic it saw before.
    assert settings_module.DEFAULT_MAX_STEPS == 0, "no step cap out of the box"
    assert settings_module.DEFAULT_MAX_DEPTH == 1_000_000
    assert settings_module.DEFAULT_MAX_FINDALL == 1_000_000
    assert settings_module.DEFAULT_TIMEOUT_MILLISECONDS == 0, "no clock out of the box"
    assert settings.max_steps == 0, "no step limit until one is asked for"
    assert settings.timeout_milliseconds == 0, "no deadline until one is asked for"
    assert settings.max_depth == settings_module.DEFAULT_MAX_DEPTH
    assert settings.max_findall == settings_module.DEFAULT_MAX_FINDALL
    assert settings.limits() == {
        "maxDepth": settings_module.DEFAULT_MAX_DEPTH,
        "maxFindall": settings_module.DEFAULT_MAX_FINDALL,
    }, settings.limits()
    settings.max_steps = 5000
    assert settings.limits()["maxSteps"] == 5000
    settings.max_steps = -5
    assert settings.max_steps == 0, "a negative limit is not a limit"
    settings.timeout_milliseconds = 99_999_999
    assert settings.timeout_milliseconds == settings_module.MAXIMUM_TIMEOUT_MILLISECONDS
    settings.input_mode = "диалог"
    assert settings.input_mode == settings_module.DEFAULT_INPUT_MODE, "junk falls back"
    settings.output_font_size = 100
    assert settings.output_font_size == settings_module.MAXIMUM_FONT_SIZE
    settings.autosave_minutes = -5
    assert settings.autosave_minutes == 0
    # task_46's row for the interpreter is gone (task_79): the engine is chosen by
    # the button on the toolbar, and the value an old file holds is still read —
    # `legacy_interpreter` — while the choice itself is `view/engine`.
    assert settings.engine == "u", "our own engine runs until the button says otherwise"
    assert settings.legacy_interpreter == "", "no old row in a fresh file"
    assert settings.process_directory == "file"
    assert settings.process_directory_path == ""
    print("ok: the new preferences start where the task says they start")


def test_the_engine_and_process_directory_round_trip(directory: pathlib.Path) -> None:
    path = directory / "interp.ini"
    settings = Settings(path)
    settings.engine = "d"
    settings.process_directory = "custom"
    settings.process_directory_path = "C:/курс"

    reopened = Settings(path)
    assert reopened.engine == "d"
    assert reopened.process_directory == "custom"
    assert reopened.process_directory_path == "C:/курс"

    # A choice the rows do not know falls back like every other choice, and the
    # setter writes the fallback rather than a value the switch could not show.
    settings.process_directory = "каталог"
    assert settings.process_directory == "file", "an unknown answer reads as `file`"
    settings.engine = "D"
    assert settings.engine == "d", "the key is read without case"
    settings.engine = "марсианский"
    assert settings.engine == "u", "an engine this build does not know is our own"

    # The row of task_46 that the button replaced: its value is read as the build
    # folder of this launch, and emptied once the button answers (task_79).  The
    # key has no record any more, so the file is written the way a hand edit
    # would — which is also the case the reader exists for.
    raw = QSettings(str(path), QSettings.Format.IniFormat)
    raw.setValue("execution/interpreter", "C:/старый/prologu.exe")
    raw.sync()
    assert Settings(path).legacy_interpreter == "C:/старый/prologu.exe"
    reopened.clear_legacy_interpreter()
    assert Settings(path).legacy_interpreter == "", "the press of the button outlives the row"
    print("ok: the engine choice, the old row and the process directory round-trip")


def test_syntax_overrides_round_trip_and_reach_the_palette(directory: pathlib.Path) -> None:
    """The changed syntax colours survive a new instance and paint the palette."""
    from prologd_gui import theme

    settings = Settings(directory / "syntax.ini")
    assert settings.syntax_overrides("light") == {}
    assert settings.syntax_overrides("dark") == {}

    settings.set_syntax_overrides(
        "light", {"comment": "#112233", "string": "NOT-HEX", "unknown": "#000000"}
    )
    settings.set_syntax_overrides("dark", {"keyword": "#ABCDEF"})

    reopened = Settings(directory / "syntax.ini")
    assert reopened.syntax_overrides("light") == {"comment": "#112233"}, (
        reopened.syntax_overrides("light")
    )
    assert reopened.syntax_overrides("dark") == {"keyword": "#abcdef"}, (
        reopened.syntax_overrides("dark")
    )

    # The palette layers the override over the shipped syntax, and nothing else.
    settings.theme = "light"
    palette = settings.palette
    assert palette.syntax.comment == "#112233"
    assert palette.syntax.string == theme.LIGHT_SYNTAX.string, "an untouched field moved"
    assert palette.background == theme.LIGHT.background, "the chrome is not the syntax"

    settings.theme = "dark"
    assert settings.palette.syntax.keyword == "#abcdef"
    print("ok: syntax overrides round-trip, are cleaned, and reach the palette")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="prologd_gui_settings_") as name:
        directory = pathlib.Path(name)
        test_defaults_are_used_on_an_empty_file(directory)
        test_values_survive_a_new_instance(directory)
        test_broken_values_fall_back_instead_of_breaking_the_window(directory)
        test_setters_clamp(directory)
        test_unknown_keys_survive(directory)
        test_the_retired_naming_mode_reads_as_the_old_dialect(directory)
        test_the_new_keys_have_the_documented_defaults(directory)
        test_the_engine_and_process_directory_round_trip(directory)
        test_syntax_overrides_round_trip_and_reach_the_palette(directory)
        test_every_row_round_trips_and_resets(directory)
        test_set_value_clamps_and_survives_junk(directory)
        test_reset_touches_only_described_settings(directory)
        test_export_and_import_carry_everything(directory)
    test_every_key_is_described_or_written_by_the_window()
    test_the_table_describes_usable_rows()
    test_the_default_path_is_under_the_user_configuration()
    print("all settings checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
