"""Icons: a plain directory of PNG files, loaded by name and cached.

The reference front-end embedded them through `res.qrc` (`:/images/…`).  Python
has no resource compiler, so the assets stay a directory next to the package and
this module resolves them; a frozen build would look inside `sys._MEIPASS`, which
is noted rather than implemented.

A name with no file is not an error: the action is built without an icon (a
text-only button) and the name is reported once.  `MISSING` lists the icons that
are known to be missing, which is what `test_icons.py` holds the code to — a
misspelled name fails that test instead of quietly losing a picture.
"""

from __future__ import annotations

import pathlib
import sys

from PySide6.QtGui import QIcon

#: Where the icons live: beside the package, so a source checkout just works.
DEFAULT_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent / "assets"

#: Referenced by the code, not drawn yet.  Task_26 lists the set and the sizes
#: they should be drawn in; until then those actions show their title only.  The
#: first two are for features that are not wired at all (task_27, task_28), and
#: the `view-*` row is the switches of the «Вид» menu.
MISSING = frozenset(
    {
        "execution-restart",
        "execution-step-over",
        "view-line-numbers",
        "view-output-bottom",
        "view-output-right",
        "view-split-editor",
        "view-theme",
        "view-toolbar",
    }
)

_directory = DEFAULT_DIRECTORY
_cache: dict[str, QIcon | None] = {}
_reported: set[str] = set()


def set_directory(directory: str | pathlib.Path | None) -> None:
    """Points the loader somewhere else (`--icons`); `None` restores the default."""
    global _directory
    _directory = pathlib.Path(directory) if directory else DEFAULT_DIRECTORY
    _cache.clear()
    _reported.clear()


def directory() -> pathlib.Path:
    return _directory


def path_for(name: str) -> pathlib.Path:
    return _directory / f"{name}.png"


def has_icon(name: str) -> bool:
    """Whether the file is there — without loading it."""
    return path_for(name).is_file()


def icons() -> list[str]:
    """Every icon name the directory provides, sorted."""
    if not _directory.is_dir():
        return []
    return sorted(path.stem for path in _directory.glob("*.png"))


def icon(name: str) -> QIcon | None:
    """The icon, or `None` when the file is missing (reported once per name).

    Cached, including the empty answer: a toolbar asks for the same names on every
    rebuild, and a missing file should not be looked for again and again.
    """
    if name in _cache:
        return _cache[name]
    path = path_for(name)
    if not path.is_file():
        if name not in _reported:
            _reported.add(name)
            # English and ASCII on purpose: this is a note for whoever builds the
            # toolbar, it lands in the terminal, and a piped log may encode with
            # the ANSI code page.
            print(f"icons: no {path.name} — the action will have no picture", file=sys.stderr)
        _cache[name] = None
        return None
    found = QIcon(str(path))
    _cache[name] = found
    return found


def report() -> list[str]:
    """The names asked for that had no file — for the tests and the audit."""
    return sorted(_reported)
