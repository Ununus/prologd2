"""Where the program keeps its own files - in a checkout and in a frozen package.

Until task_61 every path was derived from `__file__`: a fixed number of levels up
from a module is the repository root, and `build/`, `doc/`, `examples/` and
`src/gui/assets` hang off it.  A frozen package (PyInstaller, `--onedir`) has no
repository at all - the code sits inside `_internal/` and the data the packer was
told to add ends up under `sys._MEIPASS` - so the two questions a front-end asks
must be answered by the *layout*, not by where this file happens to lie:

* `data_root()` - the folder the user sees: beside `prologd-gui.exe` in a package,
  the repository root in a checkout.  The interpreter (`prologd.exe`), the settings
  file (`gui.ini`), `doc/` and `examples/` all live there;
* `resource(name)` - read-only data the package carries (today only `assets`):
  under `sys._MEIPASS` in a package, `src/gui/<name>` in a checkout.

Nothing here imports Qt, so a check of this module needs no display and no PySide6.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterable

#: The interpreter inside a `data_root()`.
EXECUTABLE_NAME = "prologd.exe" if os.name == "nt" else "prologd"

#: The settings file of a packaged build: beside the window, so the folder stays
#: portable (task_61).  A checkout keeps its settings in AppData, as before.
SETTINGS_NAME = "gui.ini"


def frozen() -> bool:
    """Whether this is a package rather than a checkout.

    PyInstaller sets `sys.frozen`; nothing else in the project does, so the flag is
    also what tells the two layouts apart in the checks.
    """
    return bool(getattr(sys, "frozen", False))


def source_root() -> pathlib.Path:
    """The repository root: `src/gui/prologd_gui/paths.py` is four levels below it."""
    return pathlib.Path(__file__).resolve().parents[3]


def data_root() -> pathlib.Path:
    """The folder the user sees: beside the executable in a package, else the sources."""
    if frozen():
        return pathlib.Path(sys.executable).resolve().parent
    return source_root()


def resource(name: str) -> pathlib.Path:
    """Read-only data that travels with the program (the icons)."""
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return pathlib.Path(bundled) / name
    return source_root() / "src" / "gui" / name


def settings_path() -> pathlib.Path | None:
    """The settings file of a package, or `None` to let Qt pick the usual place."""
    return data_root() / SETTINGS_NAME if frozen() else None


def interpreter() -> str:
    """The interpreter to run, as the string `--exe` wants.

    A package carries one beside the window and that is the whole point: the
    machine it is copied to has no `build/` directory.  A checkout keeps exactly
    the search it always had, so working from the sources is unchanged.
    """
    candidates = [data_root() / EXECUTABLE_NAME]
    if not frozen():
        candidates += [
            source_root() / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe",
            source_root() / "build" / "linux-release" / "src" / "cli" / "prologd",
            source_root() / "build" / "src" / "cli" / "Release" / "prologd.exe",
            source_root() / "build" / "src" / "cli" / "prologd",
        ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return str(candidates[0])


def example_library() -> pathlib.Path:
    """`examples/lib` of the package: the import directory lesson 11 needs."""
    return data_root() / "examples" / "lib"


def document(name: str) -> pathlib.Path:
    """A built PDF of the package: `doc/help.pdf`, `doc/gui.pdf` and the rest."""
    return data_root() / "doc" / f"{name}.pdf"


def builtins() -> pathlib.Path:
    """The records behind the `F1` dock and the completion summaries (`doc/builtins.json`).

    Found while doing the fourth of the source-tree paths (task_61 §4): the file is
    data the window *reads*, so it travels with the documents and is looked for in
    `doc/` beside them.
    """
    return data_root() / "doc" / "builtins.json"


def import_directories(configured: Iterable[str]) -> list[str]:
    """The `ИМПОРТ` search directories of a run, in the order the engine tries them.

    What the user configured comes first (the launcher's `--include`, then the row
    of the settings dialog) and a **package** appends its own `examples/lib` last:
    the portable folder carries the library its own lesson 11 imports, so a student
    runs it without being told anything, while their own folder — the importing
    file's is tried before any of these — still wins over a same-named file there.

    Nothing absolute is *written down* for it, and that is the point: this folder is
    copied around (a flash drive, a second machine, back again) and a path recorded
    on the first run would either point at the old copy or at a drive letter that
    has changed.  The directory is derived from where the window is *now*.
    """
    result: list[str] = []
    wanted = list(configured)
    if frozen():
        wanted.append(str(example_library()))
    for directory in wanted:
        text = str(directory).strip()
        if not text or text in result:
            continue
        result.append(text)
    return result
