"""Checks of the engine table (task_79): the two programs, and what each can do.

    python src/gui/tests/test_engines.py

No window and no build needed: `engines` is a *table*, and the way a table goes
wrong is by disagreeing with the places that read it — a command that needs a
capability no engine has, a row gated by a capability that does not exist, a
capability that is documented as missing and then asked for by nobody.  The
window and the dialog are checked for behaviour elsewhere (`test_window.py` and
`test_settingsdialog.py`), and the pictures of the switch by `test_icons.py`.

The facts the table records about the original engine were measured in task_78:
`--list-keywords` is the one command both answer, and its protocol number answers
`13` for a subset of ours, so the number cannot be the thing that tells them
apart.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import actions, engines, paths  # noqa: E402
from prologd_gui import settings as settings_module  # noqa: E402


def test_the_two_engines_are_named_once() -> None:
    """One key, title, file and picture each, and one of them the default."""
    assert len(engines.ENGINES) == 2, engines.ENGINES
    for attribute in ("key", "title", "file_name", "icon"):
        values = [getattr(engine, attribute) for engine in engines.ENGINES]
        assert len(set(values)) == len(values), (attribute, values)
    assert engines.DEFAULT in engines.ENGINES
    assert engines.BY_KEY == {engine.key: engine for engine in engines.ENGINES}
    assert set(actions.ENGINE_ICONS) == {engine.icon for engine in engines.ENGINES}
    print("ok: two engines, one key/title/file/picture each, and a default")


def test_the_file_names_are_the_ones_the_build_makes() -> None:
    """The names must match what CMake produces, or nothing can start."""
    suffix = ".exe" if os.name == "nt" else ""
    assert engines.OURS.file_name == f"prologu{suffix}"
    assert engines.ORIGINAL.file_name == f"prologd{suffix}"
    assert paths.EXECUTABLE_NAME == engines.OURS.file_name, "`paths` and the table agree"
    print("ok: prologu and prologd, with the suffix of this platform")


def test_an_unknown_key_falls_back_and_a_path_picks_an_engine() -> None:
    assert engines.by_key("d") is engines.ORIGINAL
    assert engines.by_key(" D ") is engines.ORIGINAL, "read without case or spaces"
    for junk in ("", "   ", "нет такого", None, 7):
        assert engines.by_key(junk) is engines.DEFAULT, junk
    assert engines.other(engines.OURS) is engines.ORIGINAL
    assert engines.other(engines.ORIGINAL) is engines.OURS

    # A file name given by hand (`--exe`, and the removed «Интерпретатор» row)
    # names the engine it is, whatever the settings say.  Both separators count:
    # `of_path` splits on them itself, so a Windows path is read anywhere.
    assert engines.of_path("C:\\сборка\\" + engines.ORIGINAL.file_name) is engines.ORIGINAL
    assert engines.of_path("/tmp/" + engines.OURS.file_name) is engines.OURS
    assert engines.of_path(engines.ORIGINAL.file_name.upper()) is engines.ORIGINAL
    for junk in ("", "что-то.exe", engines.ORIGINAL.file_name + "x"):
        assert engines.of_path(junk) is None, junk
    print("ok: a stored key is tolerant, and a file name picks the engine it is")


def test_a_launch_answers_the_engine_and_the_folder() -> None:
    """`--exe` names a folder as well as an engine: the pair is built together."""
    assert engines.launch("", "d") == (engines.ORIGINAL, "")
    assert engines.launch("   ", "мусор") == (engines.DEFAULT, "")
    assert engines.launch("prologu.exe", "d") == (engines.OURS, ""), "a bare name is no folder"

    # A path in the style of the platform the tests run on: `/` is read by
    # Windows as well, so this is one check on both.
    folder = pathlib.Path("сборка")
    pinned = engines.launch(str(folder / engines.ORIGINAL.file_name), "u")
    assert pinned == (engines.ORIGINAL, str(folder)), pinned

    # A folder with a file name that is neither engine: the stored choice decides,
    # and the folder is still where the file will be looked for.
    unknown = engines.launch(str(folder / "движок.exe"), "d")
    assert unknown == (engines.ORIGINAL, str(folder)), unknown
    print("ok: the launch rule answers the engine and the folder beside it")


def test_every_capability_of_the_table_is_asked_about() -> None:
    """A difference nobody consults is a difference that is not held.

    Two directions, and both have to hold: a command that *needs* something must
    name a capability that exists, and a capability that an engine *lacks* must be
    asked about by a command of the table or by a row of the dialog — otherwise
    the table would be prose.
    """
    needed = {action.key: action.needs for action in actions.ACTIONS if action.needs}
    assert needed, "no command is gated at all"
    for key, capability in needed.items():
        assert capability in engines.ALL_FEATURES, (key, capability)

    asked = set(needed.values()) | set(settings_module.GATED_ROWS)
    assert asked == set(engines.ALL_FEATURES), sorted(set(engines.ALL_FEATURES) ^ asked)
    assert engines.OURS.features == engines.ALL_FEATURES, "our own engine answers everything"
    assert engines.ORIGINAL.features == frozenset(), (
        "the original answers none of them — measured in task_78, not guessed"
    )
    print(f"ok: {len(needed)} gated commands and {len(settings_module.GATED_ROWS)} gated "
          f"groups cover all {len(engines.ALL_FEATURES)} capabilities")


def test_a_gated_row_is_a_row_and_really_is_missing() -> None:
    for capability, keys in settings_module.GATED_ROWS.items():
        assert capability in engines.ALL_FEATURES, capability
        assert keys, capability
        assert not engines.ORIGINAL.has(capability), capability
        assert engines.OURS.has(capability), capability
        for key in keys:
            assert key in settings_module.BY_KEY, (capability, key)
    assert "execution/interpreter" not in settings_module.BY_KEY, (
        "the row task_79 removed is gone, not hidden"
    )
    print("ok: every gated key is a real row, and the engine that gates it lacks it")


def test_the_state_controls_are_the_last_thing_on_the_toolbar() -> None:
    """Two controls of the whole window, not commands of the program (task_79).

    The naming mode and, as the very last control, the engine switch: both are
    *states* of the window — in which dialect a file that declares none is read, and
    which program runs — so they stand apart at the right edge, after a separator,
    with the wider question last.
    """
    assert actions.TOOLBAR[-2:] == (actions.NAMING, actions.ENGINE), actions.TOOLBAR
    assert actions.SEPARATOR in actions.TOOLBAR, actions.TOOLBAR
    markers = (actions.SEPARATOR, actions.FORMAT_MODE, actions.ENGINE, actions.NAMING)
    assert actions.ENGINE not in actions.BY_KEY, "the switch is a control, not a command"
    assert actions.NAMING not in actions.BY_KEY, "and so is the naming mode"
    for key in actions.TOOLBAR:
        if key in markers:
            continue
        assert key in actions.BY_KEY, key
    print(f"ok: the toolbar ends with the two state controls ({len(actions.TOOLBAR)} entries)")


def main() -> int:
    test_the_two_engines_are_named_once()
    test_the_file_names_are_the_ones_the_build_makes()
    test_an_unknown_key_falls_back_and_a_path_picks_an_engine()
    test_a_launch_answers_the_engine_and_the_folder()
    test_every_capability_of_the_table_is_asked_about()
    test_a_gated_row_is_a_row_and_really_is_missing()
    test_the_state_controls_are_the_last_thing_on_the_toolbar()
    print("all engine checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
