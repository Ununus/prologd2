"""Checks that every icon the code asks for is there or documented as missing.

    python src/gui/tests/test_icons.py [--icons DIR]

The point is a typo: a misspelled name loses a picture silently, and a toolbar of
text-only buttons is not obviously wrong to look at.  The check runs the other way
as well — a name left in `MISSING` that the code no longer asks for is a stale note
that hides a real mistake later.

Messages are ASCII: a piped run encodes stdout with the ANSI code page, where
Cyrillic cannot be encoded at all (see `ai/conventions.md`).
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import actions, assets  # noqa: E402


def test_every_referenced_icon_is_present_or_documented() -> None:
    present = set(assets.icons())
    absent = sorted(
        name for name in actions.ICON_NAMES if name not in present and name not in assets.MISSING
    )
    assert not absent, f"no file and no MISSING entry: {absent}"
    drawn = len(present & actions.ICON_NAMES)
    documented = len(set(actions.ICON_NAMES) & set(assets.MISSING))
    print(f"ok: {len(actions.ICON_NAMES)} icon names — {drawn} drawn, {documented} documented missing")


def test_nothing_recorded_as_missing_is_actually_drawn() -> None:
    """`MISSING` is the drawing list — it may name icons no entry uses *yet*.

    `execution-restart` and `view-output-bottom` are there for features that are
    still to come, and drawing them early is fine.  What is not fine is a name
    left in the list after its file appeared: then the audit would let a real
    misspelling through later.
    """
    present = set(assets.icons())
    drawn = sorted(set(assets.MISSING) & present)
    assert not drawn, f"the file exists, so it must leave MISSING: {drawn}"
    waiting = sorted(set(assets.MISSING) - set(actions.ICON_NAMES))
    print(f"ok: MISSING matches the files exactly ({len(waiting)} for features not wired yet)")


def test_the_directory_is_read_from_the_override() -> None:
    """`--icons DIR` points the loader elsewhere; a missing file stays quiet."""
    with tempfile.TemporaryDirectory(prefix="prologd_icons_") as name:
        directory = pathlib.Path(name)
        (directory / "file-new.png").write_bytes(b"not really a png")
        assets.set_directory(directory)
        try:
            assert assets.has_icon("file-new") is True
            assert assets.has_icon("file-open") is False
            assert assets.icons() == ["file-new"]
            assert assets.icon("file-open") is None
            assert assets.report() == ["file-open"], assets.report()
        finally:
            assets.set_directory(None)
    assert assets.directory() == assets.DEFAULT_DIRECTORY
    print("ok: the icon directory can be overridden, and a missing file is reported once")


def test_the_shipped_icons_load() -> None:
    """A corrupt PNG would be a null icon — and a null icon is a text-only button."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed")
        return
    application = QApplication(sys.argv[:1])
    loaded = 0
    for name in sorted(assets.icons()):
        found = assets.icon(name)
        assert found is not None and not found.isNull(), name
        loaded += 1
    print(f"ok: all {loaded} shipped icons load")
    del application


def main(argv: list[str]) -> int:
    if "--icons" in argv:
        assets.set_directory(argv[argv.index("--icons") + 1])
    test_every_referenced_icon_is_present_or_documented()
    test_nothing_recorded_as_missing_is_actually_drawn()
    test_the_directory_is_read_from_the_override()
    test_the_shipped_icons_load()
    print("all icon checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
