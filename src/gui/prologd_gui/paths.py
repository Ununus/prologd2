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

import contextlib
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable

#: Variables PyInstaller and PySide set for the frozen window.  A desktop program
#: started with them loads the bundled Qt instead of its own and fails with a
#: plugin error, so they are removed for anything outside this process.
BUNDLED_ENVIRONMENT_VARIABLES = (
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "QT_PLUGIN_PATH",
    "QML2_IMPORT_PATH",
    "QT_QPA_PLATFORM",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
    "PYTHONHOME",
    "PYTHONPATH",
)


def external_environment() -> dict[str, str]:
    """The environment a program of the desktop should see, not the frozen one."""
    environment = dict(os.environ)
    for name in BUNDLED_ENVIRONMENT_VARIABLES:
        environment.pop(name, None)
    return environment


@contextlib.contextmanager
def without_bundled_environment():
    """Runs a Qt helper that starts another program without the bundled paths."""
    saved = {name: os.environ.pop(name, None) for name in BUNDLED_ENVIRONMENT_VARIABLES}
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def reveal_command(path: str) -> list[str]:
    """The command that shows a file where it lives (task_68).

    Windows' own file manager wants the switch and the path as *one* argument, and
    it reports a failure exit code even when it worked — so nothing checks it.
    The path is spelled natively: `explorer` reads `/select,C:/dir/файл.pld` as
    something other than a file to select, which is what a buffer saved from the
    dialog used to hand it (task_109).
    """
    path = os.path.normpath(str(path))
    if sys.platform == "win32":
        return ["explorer", f"/select,{path}"]
    if sys.platform == "darwin":
        return ["open", "-R", path]
    target = pathlib.Path(path)
    if target.is_dir():
        return ["xdg-open", str(target)]
    return ["xdg-open", str(target.parent)]


def reveal(path: str) -> None:
    """Shows `path` in the system's file manager."""
    subprocess.Popen(reveal_command(path), env=external_environment())


#: The interpreter of this repository inside a `data_root()`.
EXECUTABLE_NAME = "prologd.exe" if os.name == "nt" else "prologd"

#: The name for the user: the status bar and the «пределы» note.
ENGINE_TITLE = "Пролог-Д"

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


def inside_app_bundle() -> bool:
    """Whether a frozen build runs from `Foo.app/Contents/MacOS` (task_119).

    A macOS bundle is an *installed* copy even when the user owns it: the folder
    may be signed, and writing `gui.ini` beside the executable would change the
    bundle's contents and break the signature.  A copy of the same folder *outside*
    a `.app` is still portable, exactly like the Windows folder on a flash drive.
    """
    if sys.platform != "darwin" or not frozen():
        return False
    root = data_root()
    return (
        root.name == "MacOS"
        and root.parent.name == "Contents"
        and root.parent.parent.suffix == ".app"
    )


def resource(name: str) -> pathlib.Path:
    """Read-only data that travels with the program (the icons)."""
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return pathlib.Path(bundled) / name
    return source_root() / "src" / "gui" / name


def settings_path() -> pathlib.Path | None:
    """Where a *frozen* build keeps `gui.ini`; `None` lets Qt use AppData.

    task_61 made every packaged build keep its settings beside itself, which is what
    makes the folder portable.  An **installed** build (task_116, Inno Setup) must
    not: `%LOCALAPPDATA%\\Programs` is writable, so «can I write here?» cannot be the
    question, and a per-user settings file belongs in AppData where Qt puts it.  The
    folder a build runs from is the whole answer, in this order:

    * a folder that already holds a `gui.ini` keeps it — a portable copy the user
      has been running, whose settings must not move on an upgrade;
    * a build under `%LOCALAPPDATA%\\Programs`, `%ProgramFiles%` or
      `%ProgramFiles(x86)%` is an installed one, and answers AppData;
    * anything else — a flash drive, a network folder, or the installed folder
      copied somewhere else — is portable: beside itself.  That last case is what
      makes «скопировал установленную папку на флешку — она повела себя как
      переносимая» need no marker file and no switch.

    A folder it cannot write to at all (a CD, a share opened read-only) falls back to
    AppData as well: a `gui.ini` that fails at every close is worse than one away
    from the folder.

    A macOS `.app` is installed whatever its owner: writing beside the executable
    would change the bundle's contents and break its signature (task_119), so it
    answers AppData too — `~/Library/Application Support/PrologD/gui`, chosen by
    `settings.default_path`.
    """
    if not frozen():
        return None
    if inside_app_bundle():
        return None
    root = data_root()
    beside = root / SETTINGS_NAME
    if beside.is_file():
        return beside
    if any(inside(root, folder) for folder in install_roots()):
        return None
    return beside if writable(root) else None


def install_roots() -> list[pathlib.Path]:
    """The folders an *installed* copy can live in, empty ones left out.

    Read from the environment every time rather than once at import: a check that
    fakes an install puts these in place itself, and nothing here is worth a cache.

    Windows answers from `%LOCALAPPDATA%`, `%ProgramFiles%` and
    `%ProgramFiles(x86)%`.  A Debian package installs into `/opt` (task_118), and
    the system prefixes are install locations as well; on Windows these POSIX
    paths cannot match a real `data_root()`.
    """
    roots: list[pathlib.Path] = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        # `Programs` and not the whole of `%LOCALAPPDATA%`: a portable copy unzipped
        # into `%LOCALAPPDATA%\\Temp` is still a portable copy.
        roots.append(pathlib.Path(local) / "Programs")
    for name in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(name)
        if value:
            roots.append(pathlib.Path(value))
    if os.name != "nt":
        roots.extend(pathlib.Path(name) for name in ("/opt", "/usr", "/usr/local"))
    return roots


def inside(path: pathlib.Path | str, folder: pathlib.Path | str) -> bool:
    """Whether `path` is `folder` or lies under it, compared the Windows way.

    Letters are folded the way Windows folds them, because `%LOCALAPPDATA%` may
    arrive spelled either way and the folder below it is not the one to blame.
    """
    try:
        path, folder = pathlib.Path(path).resolve(), pathlib.Path(folder).resolve()
    except OSError:  # pragma: no cover - a path the system refuses to resolve
        return False
    one, other = os.path.normcase(str(path)), os.path.normcase(str(folder))
    return one == other or one.startswith(other + os.sep)


def writable(directory: pathlib.Path | str) -> bool:
    """Whether a file can be written there.

    A probe file and not `os.access`: on Windows that answers from the read-only
    attribute of the *folder*, not from its permissions, so a shared folder that
    refuses writes would pass and every close would then fail to remember the
    session.  The file is removed at once; a process killed mid-probe leaves one
    empty file behind, which is a smaller price than a wrong answer.
    """
    probe = pathlib.Path(directory) / f".prologd-write-test-{os.getpid()}"
    try:
        probe.write_bytes(b"")
    except OSError:
        return False
    try:
        probe.unlink()
    except OSError:  # pragma: no cover - writing worked, removing may still not
        pass
    return True


def interpreter(folder: str = "") -> str:
    """The interpreter to run, as the string `--exe` wants.

    A package carries the interpreter beside the window and that is the whole
    point: the machine it is copied to has no `build/` directory.  A checkout
    keeps exactly the search it always had, so working from the sources is
    unchanged.  `folder` is what `--exe` (or the `execution/interpreter` key of a
    file written by an older window) named: «here is my build», which is looked
    for there and nowhere else.
    """
    if folder:
        return str(pathlib.Path(folder) / EXECUTABLE_NAME)
    if frozen():
        places = [data_root()]
    else:
        root = source_root()
        places = [
            data_root(),
            root / "build" / "windows-msvc" / "src" / "cli" / "Release",
            root / "build" / "linux-release" / "src" / "cli",
            root / "build" / "macos-release" / "src" / "cli",
            root / "build" / "src" / "cli" / "Release",
            root / "build" / "src" / "cli",
        ]
    candidates = [place / EXECUTABLE_NAME for place in places]
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
