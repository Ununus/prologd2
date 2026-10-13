"""Where the program keeps its own files - in a checkout and in a frozen package.

Until task_61 every path was derived from `__file__`: a fixed number of levels up
from a module is the repository root, and `build/`, `doc/`, `examples/` and
`src/gui/assets` hang off it.  A frozen package (PyInstaller, `--onedir`) has no
repository at all - the code sits inside `_internal/` and the data the packer was
told to add ends up under `sys._MEIPASS` - so the two questions a front-end asks
must be answered by the *layout*, not by where this file happens to lie:

* `data_root()` - the folder the user sees: beside `prologd-gui.exe` in a package,
  the repository root in a checkout.  The interpreter (`prologu.exe`), the settings
  file (`gui.ini`), `doc/` and `examples/` all live there;
* `resource(name)` - read-only data the package carries (today only `assets`):
  under `sys._MEIPASS` in a package, `src/gui/<name>` in a checkout.

Nothing here imports Qt, so a check of this module needs no display and no PySide6.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
from collections.abc import Iterable

from . import engines

def reveal_command(path: str) -> list[str]:
    """The command that shows a file where it lives (task_68).

    Windows' own file manager wants the switch and the path as *one* argument, and
    it reports a failure exit code even when it worked — so nothing checks it.
    """
    if sys.platform == "win32":
        return ["explorer", f"/select,{path}"]
    if sys.platform == "darwin":
        return ["open", "-R", path]
    return ["xdg-open", str(pathlib.Path(path).parent)]


def reveal(path: str) -> None:
    """Shows `path` in the system's file manager."""
    subprocess.Popen(reveal_command(path))


#: The engine of this repository inside a `data_root()`: «Пролог-У» (task_75).
#: The two names, their titles and their pictures live in `engines`, which is
#: where the *choice* between them is described (task_79); this is only where a
#: file is looked for.
EXECUTABLE_NAME = engines.OURS.file_name

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


def interpreter(file_name: str = EXECUTABLE_NAME) -> str:
    """The file `file_name` to run, as the string `--exe` wants.

    A package carries the engines beside the window and that is the whole point:
    the machine it is copied to has no `build/` directory.  A checkout keeps
    exactly the search it always had, so working from the sources is unchanged.

    The search is by **one** file name at a time, deliberately.  Until task_78
    the original engine was a tempting fallback — a tree built before task_75 has
    a `prologd.exe` in every one of these folders, so falling back to it would run
    the wrong engine without saying so.  Which engine to start is the user's
    choice now (`view/engine`, and the button on the toolbar), and
    `engine_executable` resolves the file of *that* engine.
    """
    if frozen():
        places = [data_root()]
    else:
        root = source_root()
        places = [
            data_root(),
            root / "build" / "windows-msvc" / "src" / "cli" / "Release",
            root / "build" / "linux-release" / "src" / "cli",
            root / "build" / "src" / "cli" / "Release",
            root / "build" / "src" / "cli",
        ]
    candidates = [place / file_name for place in places]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return str(candidates[0])


def engine_executable(engine: engines.Engine, *, folder: str = "") -> str:
    """The file of `engine` the next run starts (task_79).

    Two answers, and the difference matters.  `folder` is the folder `--exe` (or
    task_46's removed «Интерпретатор» row) named — «here are my builds»: the
    engines were built together, so the chosen one is looked for **there and
    nowhere else**, and a file that is missing is reported in the pane by
    `window._start_session` rather than quietly answered by another build tree.
    Without a folder, `interpreter` searches the usual places for that engine.
    """
    if folder:
        return str(pathlib.Path(folder) / engine.file_name)
    return interpreter(engine.file_name)


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

    Exactly what the user configured: the launcher's `--include` first, then the row
    of the settings dialog (`window._import_directories` passes both).  The folder of
    the importing file itself is tried before any of these, by the engine.

    A **package** used to append its own `examples/lib` here, so that lesson 11 ran
    out of the box.  That was dropped on 2026-10-03 at the reader's request: the
    lesson now tells the student to add the directory by hand, which is transparent —
    they see the row they filled and the path they chose — and nothing is recorded
    behind their back that could go stale when the folder moves to another machine.
    The library still travels in the package (`example_library()`), it is simply not
    searched until the student says so.
    """
    result: list[str] = []
    for directory in configured:
        text = str(directory).strip()
        if not text or text in result:
            continue
        result.append(text)
    return result


def resolve_import(name: str, *, source_dir: pathlib.Path | None,
                   directories: Iterable[str], interpreter_path: str | None) -> str | None:
    """The file an `ИМПОРТ("…")` names, searched the way the interpreter searches it.

    The engine's own order (ADR-026): an absolute name is itself; otherwise the
    folder of the *importing* file first, then every `-I` directory, then `stdlib`
    beside the interpreter — the engine finds its own library last, and the window
    has to agree with it, or `F12` would open a different file than the one the run
    actually loads.  `None` means nothing of that name exists in any of them.
    """
    path = pathlib.Path(name)
    if path.is_absolute():
        return str(path) if path.is_file() else None
    candidates: list[pathlib.Path] = []
    if source_dir is not None:
        candidates.append(pathlib.Path(source_dir) / name)
    candidates += [pathlib.Path(directory) / name for directory in directories]
    if interpreter_path:
        candidates.append(pathlib.Path(interpreter_path).parent / "stdlib" / name)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None
