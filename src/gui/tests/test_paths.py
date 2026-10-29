"""Checks that the window finds its own files - in a checkout and in a package.

    python src/gui/tests/test_paths.py

task_61: a portable package has no repository around it.  The interpreter, the
icons, the documents and the settings file have to be found by the *layout*
(`prologd_gui.paths`) and not by counting levels up from `__file__` - three levels
up from a module of a frozen package is `_internal/`, and its neighbours are not the
ones the reader sees.  The three places that used to count are checked here with
`sys.frozen` / `sys._MEIPASS` faked, and the two answers that only make sense in a
checkout are checked as they are.

`packaged` is imported by `test_window.py`, which asks the window itself to open a
document from such a package.

Messages are ASCII: a piped run encodes stdout with the ANSI code page, where
Cyrillic cannot be encoded at all (see `ai/conventions.md`).
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import assets, paths  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]


@contextlib.contextmanager
def packaged(directory: pathlib.Path):
    """A window that believes PyInstaller froze it into `directory`.

    Exactly what PyInstaller sets: `sys.frozen`, `sys.executable` (the launcher the
    reader double-clicks) and `sys._MEIPASS` (where the bundled data was unpacked).
    All three are put back afterwards, because every other check expects a checkout.
    """
    saved = (getattr(sys, "frozen", None), sys.executable, getattr(sys, "_MEIPASS", None))
    sys.frozen = True
    sys.executable = str(directory / "prologd-gui.exe")
    sys._MEIPASS = str(directory / "_internal")
    try:
        yield
    finally:
        if saved[0] is None:
            del sys.frozen
        else:
            sys.frozen = saved[0]
        sys.executable = saved[1]
        if saved[2] is None:
            del sys._MEIPASS
        else:
            sys._MEIPASS = saved[2]


def make_package(directory: pathlib.Path, *, with_executable: bool = True) -> pathlib.Path:
    """A package folder holding the four things the window looks for."""
    directory.mkdir(parents=True, exist_ok=True)
    if with_executable:
        (directory / paths.EXECUTABLE_NAME).write_bytes(b"MZ")
    (directory / "examples" / "lib").mkdir(parents=True, exist_ok=True)
    (directory / "doc").mkdir(exist_ok=True)
    (directory / "doc" / "help.pdf").write_bytes(b"%PDF-1.4\n")
    (directory / "_internal" / "assets").mkdir(parents=True, exist_ok=True)
    return directory


@contextlib.contextmanager
def on_platform(name: str):
    """`sys.platform` faked for the rules that branch on it (task_119).

    Only the platform *name* is faked; Qt and the filesystem are the real ones.
    That is enough for `paths` (the `.app` rule) and `settings.default_location`,
    which is what these checks are about.
    """
    saved = sys.platform
    sys.platform = name
    try:
        yield
    finally:
        sys.platform = saved


def test_a_checkout_reads_its_own_tree() -> None:
    """With no `sys.frozen` the answers are the ones the sources always had."""
    assert paths.frozen() is False
    assert paths.data_root() == ROOT, paths.data_root()
    assert paths.resource("assets") == ROOT / "src" / "gui" / "assets"
    assert paths.settings_path() is None, "a checkout keeps its settings in AppData"
    assert paths.document("help") == ROOT / "doc" / "help.pdf"
    assert paths.builtins() == ROOT / "doc" / "builtins.json"
    assert paths.builtins().is_file(), "the built-in records are part of the tree"
    assert paths.example_library() == ROOT / "examples" / "lib"
    found = paths.interpreter()
    assert found.endswith(paths.EXECUTABLE_NAME), found
    if pathlib.Path(found).is_file():
        print(f"ok: a checkout resolves its own tree (interpreter: {pathlib.Path(found).name})")
    else:
        print("ok: a checkout resolves its own tree (nothing built, the first candidate stands)")


def test_a_package_finds_everything_beside_itself() -> None:
    with tempfile.TemporaryDirectory(prefix="prologd_package_") as name:
        package = make_package(pathlib.Path(name))
        with packaged(package):
            assert paths.frozen() is True
            assert paths.data_root() == package
            assert paths.interpreter() == str(package / paths.EXECUTABLE_NAME)
            assert paths.settings_path() == package / "gui.ini"
            assert paths.document("gui") == package / "doc" / "gui.pdf"
            assert paths.builtins() == package / "doc" / "builtins.json"
            assert paths.example_library() == package / "examples" / "lib"
            assert paths.resource("assets") == package / "_internal" / "assets"
    print("ok: a package finds its interpreter, settings, documents and icons beside itself")


def test_an_installed_copy_keeps_its_settings_in_appdata() -> None:
    """task_116: installed means AppData, and a copy taken elsewhere is portable.

    Inno Setup puts a per-user install in `%LOCALAPPDATA%\\Programs\\PrologD`, and
    that folder is writable — so "can I write here?" cannot be the question.  The
    folder is: under a programs folder means an installed copy and AppData, anywhere
    else means portable and `gui.ini` beside the window.  That is what makes a copy
    of the installed folder on a flash drive behave as a portable one without a
    marker file to look for.
    """
    names = ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)")
    saved = {name: os.environ.get(name) for name in names}
    with tempfile.TemporaryDirectory(prefix="prologd_install_") as name:
        base = pathlib.Path(name)
        local = base / "LocalAppData"
        installed = make_package(local / "Programs" / "PrologD")
        os.environ["LOCALAPPDATA"] = str(local)
        for other in names[1:]:
            os.environ.pop(other, None)
        try:
            with packaged(installed):
                assert paths.settings_path() is None, (
                    "an installed copy keeps its settings in AppData"
                )
            # The same folder copied to a flash drive: no install location above
            # it any more, so it is a portable copy and asks for the file again.
            copied = make_package(base / "флешка" / "PrologD")
            with packaged(copied):
                assert paths.settings_path() == copied / "gui.ini", paths.settings_path()
            # `%ProgramFiles%` is an install location as well, when a machine-wide
            # install ever comes back.
            machine = make_package(base / "Program Files" / "PrologD")
            os.environ["ProgramFiles"] = str(base / "Program Files")
            with packaged(machine):
                assert paths.settings_path() is None, "Program Files is an install location"
        finally:
            for other, value in saved.items():
                if value is None:
                    os.environ.pop(other, None)
                else:
                    os.environ[other] = value
    print("ok: an installed copy answers AppData, and a copy taken elsewhere is portable")


def test_an_installed_copy_under_opt_keeps_its_settings_in_xdg() -> None:
    """task_118: `/opt` and the system prefixes are install locations on Linux.

    The `.deb` installs into `/opt/prologd`, which is root-owned, so the settings
    must go to XDG — and they have to do so because the folder *is* an install
    location, not because a write happened to fail.
    """
    if os.name == "nt":
        print("ok: skipped on Windows, which has no /opt")
        return
    for folder in ("/opt/prologd", "/usr/lib/prologd", "/usr/local/lib/prologd"):
        with packaged(pathlib.Path(folder)):
            assert paths.settings_path() is None, folder
    print("ok: /opt and the system prefixes count as install locations on Linux")


def test_an_app_bundle_is_installed_and_a_loose_copy_is_portable() -> None:
    """task_119: a macOS `.app` must not keep `gui.ini` inside itself.

    The folder `Contents/MacOS` is writable for the user, so the old rule would
    put the settings beside the frozen window and change a signed bundle on the
    first close.  A plain copy outside any `.app` stays portable.
    """
    with tempfile.TemporaryDirectory(prefix="prologd_app_") as name:
        base = pathlib.Path(name)
        bundle = base / "PrologD.app" / "Contents" / "MacOS"
        bundle.mkdir(parents=True)
        with on_platform("darwin"), packaged(bundle):
            assert paths.inside_app_bundle() is True
            assert paths.settings_path() is None, "a bundle must not write gui.ini inside itself"

        loose = base / "копия" / "MacOS"
        loose.mkdir(parents=True)
        with on_platform("darwin"), packaged(loose):
            assert paths.inside_app_bundle() is False
            assert paths.settings_path() == loose / "gui.ini", paths.settings_path()
    print("ok: a .app is installed, and a copy outside the bundle is portable")


def test_a_macos_bundle_keeps_the_engine_in_bin() -> None:
    """task_119, part 221: `PrologD` and `prologd` are one name on a Mac.

    The window's own launcher is `Contents/MacOS/PrologD`; a copy of the engine
    beside it under the name `prologd` overwrites it, because the filesystem does
    not tell the two names apart — and then the icon double-clicked in Finder runs
    the engine, which prints a usage line and exits: a bounce in the dock and no
    window.  The engine therefore lives in `bin`, and that is where the window
    looks first.
    """
    with tempfile.TemporaryDirectory(prefix="prologd_app_") as name:
        base = pathlib.Path(name)
        bundle = base / "PrologD.app" / "Contents" / "MacOS"
        (bundle / "bin").mkdir(parents=True)
        # The launcher and the engine: two files that a Mac would read as one name.
        (bundle / "PrologD").write_bytes(b"the window")
        (bundle / "bin" / paths.EXECUTABLE_NAME).write_bytes(b"the engine")
        with on_platform("darwin"), packaged(bundle):
            sys.executable = str(bundle / "PrologD")
            assert paths.interpreter() == str(bundle / "bin" / paths.EXECUTABLE_NAME), (
                paths.interpreter()
            )

        # A package of the older layout — the engine beside the launcher, as on
        # Windows — is still found, so an existing folder keeps working.
        flat = base / "старая" / "MacOS"
        flat.mkdir(parents=True)
        (flat / "PrologD").write_bytes(b"the window")
        (flat / paths.EXECUTABLE_NAME).write_bytes(b"the engine")
        with on_platform("darwin"), packaged(flat):
            sys.executable = str(flat / "PrologD")
            assert paths.interpreter() == str(flat / paths.EXECUTABLE_NAME), paths.interpreter()
    print("ok: a .app looks for the engine in bin first, and a flat package still works")


def test_a_checkout_finds_the_macos_release_build() -> None:
    """task_119: the source tree's macOS build is one of the places `interpreter` looks."""
    with tempfile.TemporaryDirectory(prefix="prologd_macos_build_") as name:
        root = pathlib.Path(name)
        cli = root / "build" / "macos-release" / "src" / "cli"
        cli.mkdir(parents=True)
        (cli / paths.EXECUTABLE_NAME).write_bytes(b"MZ")
        saved = paths.source_root
        paths.source_root = lambda: root
        try:
            assert paths.interpreter() == str(cli / paths.EXECUTABLE_NAME)
        finally:
            paths.source_root = saved
    print("ok: a checkout finds build/macos-release/src/cli")


def test_a_settings_file_that_is_already_there_is_kept() -> None:
    """The file decides before the folder does: an upgrade must not move settings.

    A `gui.ini` beside the window is a portable copy the user has been running, and
    even inside an install location that file is the one to keep — the alternative
    is a window that silently starts over in AppData on top of a settings file the
    user can see.
    """
    saved = os.environ.get("LOCALAPPDATA")
    with tempfile.TemporaryDirectory(prefix="prologd_install_") as name:
        base = pathlib.Path(name)
        package = make_package(base / "LocalAppData" / "Programs" / "PrologD")
        (package / "gui.ini").write_text("[files]\n", encoding="utf-8")
        os.environ["LOCALAPPDATA"] = str(base / "LocalAppData")
        try:
            with packaged(package):
                assert paths.settings_path() == package / "gui.ini", paths.settings_path()
        finally:
            if saved is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = saved
    print("ok: a gui.ini that is already beside the window is the one it keeps")


def test_a_folder_that_cannot_be_written_falls_back_to_appdata() -> None:
    """A CD or a read-only share: a `gui.ini` there would fail at every close."""
    with tempfile.TemporaryDirectory(prefix="prologd_readonly_") as name:
        missing = pathlib.Path(name) / "нет-такой-папки"
        with packaged(missing):
            assert paths.data_root() == missing
            assert paths.settings_path() is None, "no folder to write to means AppData"
    print("ok: a package in a folder it cannot write to falls back to AppData")


def test_a_package_without_the_interpreter_names_the_expected_place() -> None:
    """The message a broken package prints must point at the file, not at a build."""
    with tempfile.TemporaryDirectory(prefix="prologd_package_") as name:
        package = make_package(pathlib.Path(name), with_executable=False)
        with packaged(package):
            assert paths.interpreter() == str(package / paths.EXECUTABLE_NAME)
    print("ok: a package missing its interpreter still names the expected path")


def test_the_icons_come_from_the_same_answer() -> None:
    """The constant the icon loader uses is `paths.resource`, computed once."""
    assert assets.DEFAULT_DIRECTORY == paths.resource("assets")
    assert assets.directory() == assets.DEFAULT_DIRECTORY
    print("ok: the icon directory is `paths.resource('assets')`")


def test_the_reference_reads_the_same_document() -> None:
    """`F1` and the completion summaries read `doc/builtins.json` of the package."""
    from prologd_gui import reference

    assert reference.DEFAULT_PATH == paths.builtins(), reference.DEFAULT_PATH
    loaded = reference.Reference.load()
    assert len(loaded) > 0, "the checkout has the records, so the reference is not empty"
    print(f"ok: the built-in reference is `paths.builtins()` ({len(loaded)} records)")


def test_a_package_searches_only_what_the_student_added() -> None:
    """No directory is added behind the reader's back (2026-10-03).

    A package *carries* `examples/lib` — `test_a_package_finds_everything_beside_itself`
    checks that — but the window does not search it.  Lesson 11 asks the student to add
    the folder by hand, so the row of the settings dialog is the whole truth, and a
    folder copied to another machine leaves no remembered path behind.
    """
    with tempfile.TemporaryDirectory(prefix="prologd_package_") as name:
        package = make_package(pathlib.Path(name))
        library = str(package / "examples" / "lib")
        assert pathlib.Path(library).is_dir(), "the package does carry the library"
        with packaged(package):
            mine = str(package / "мои" / "модули")
            assert paths.import_directories([mine]) == [mine]
            assert paths.import_directories([]) == []
    print("ok: a package searches what the student added, and nothing of its own")


def test_the_import_list_is_trimmed_and_deduplicated() -> None:
    """Only what the user configured reaches `-I` (task_61 §4)."""
    assert paths.import_directories([]) == []
    assert paths.import_directories(["", "   "]) == []
    assert paths.import_directories(["examples/lib", " examples/lib "]) == ["examples/lib"]
    assert paths.import_directories(["a", "b", "a"]) == ["a", "b"]
    print("ok: the import list is what it was told, trimmed and once each")


def test_the_file_manager_is_called_the_way_its_platform_wants() -> None:
    """«Показать в проводнике» (task_68): one argument, and no exit code checked.

    Windows' own file manager wants the switch and the path glued into one
    argument — `explorer /select, "path"` opens the default folder instead — and it
    reports a failure code even when it worked, which is why nobody waits for it.
    The path is native whatever the caller had (task_109): the save dialog answers
    with forward slashes, and `explorer` reads `/select,C:/dir/файл.pld` as neither
    a switch nor a file.
    """
    path = "C:/example/file with space.pld"
    native = os.path.normpath(path)
    command = paths.reveal_command(path)
    if sys.platform == "win32":
        assert command == ["explorer", f"/select,{native}"], command
        assert "\\" in command[1], "the file manager gets the native spelling"
    elif sys.platform == "darwin":
        assert command == ["open", "-R", native], command
    else:
        assert command[:1] == ["xdg-open"], command
        assert command[1] == str(pathlib.Path(native).parent)
        with tempfile.TemporaryDirectory(prefix="prologd_reveal_") as folder:
            assert paths.reveal_command(folder) == ["xdg-open", folder]
    print("ok: the file manager is called the way its platform wants")


def test_the_file_manager_does_not_inherit_the_frozen_qt_environment() -> None:
    """task_118: a frozen window must not hand its bundled Qt to Dolphin.

    PyInstaller puts its own libraries first through `LD_LIBRARY_PATH` (and its
    plugins through `QT_PLUGIN_PATH`).  A child file manager inherits them and
    fails to start, so `reveal` builds a copy of the environment without them.
    """
    names = paths.BUNDLED_ENVIRONMENT_VARIABLES
    saved = {name: os.environ.get(name) for name in names}
    calls: list[tuple[list[str], dict[str, str] | None]] = []

    class FakePopen:
        def __init__(self, command: list[str], env: dict[str, str] | None = None) -> None:
            calls.append((command, env))

    saved_popen = paths.subprocess.Popen
    try:
        for name in names:
            os.environ[name] = "/bundle"
        paths.subprocess.Popen = FakePopen
        paths.reveal("/tmp/reveal.pld")
        environment = paths.external_environment()
        assert all(name not in environment for name in names), environment
        assert "PATH" in environment, environment
        with paths.without_bundled_environment():
            assert all(name not in os.environ for name in names), os.environ
        assert all(os.environ.get(name) == "/bundle" for name in names), os.environ
    finally:
        paths.subprocess.Popen = saved_popen
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    assert len(calls) == 1, calls
    assert calls[0][1] is not None, calls
    assert all(name not in calls[0][1] for name in names), calls
    print("ok: the desktop program gets an environment without the bundled paths")


def test_the_import_name_is_resolved_the_way_the_interpreter_resolves_it() -> None:
    """`F12` must open the file the run would load, or it is worse than nothing.

    The engine tries the importing file's folder, then every `-I` directory, then
    `stdlib` beside the interpreter (ADR-026); `resolve_import` repeats that order
    (task_69).
    """
    with tempfile.TemporaryDirectory(prefix="prologd_import_") as name:
        folder = pathlib.Path(name)
        for child in ("near", "shared", "stdlib"):
            (folder / child).mkdir()
        (folder / "near" / "lib.pld").write_text("факт(1).\n", encoding="utf-8")
        (folder / "shared" / "other.pld").write_text("факт(2).\n", encoding="utf-8")
        (folder / "stdlib" / "lists.pld").write_text("факт(3).\n", encoding="utf-8")
        side = str(folder / paths.EXECUTABLE_NAME)

        found = paths.resolve_import("lib.pld", source_dir=folder / "near",
                                    directories=[str(folder / "shared")],
                                    interpreter_path=side)
        assert found == str(folder / "near" / "lib.pld"), found
        found = paths.resolve_import("other.pld", source_dir=folder / "near",
                                    directories=[str(folder / "shared")],
                                    interpreter_path=None)
        assert found == str(folder / "shared" / "other.pld"), found
        found = paths.resolve_import("lists.pld", source_dir=None, directories=[],
                                    interpreter_path=side)
        assert found == str(folder / "stdlib" / "lists.pld"), found

        # A file of the importing folder wins over a same-named one it searches: the
        # order is the engine's, and `F12` has to open what the run would load.
        (folder / "shared" / "lib.pld").write_text("факт(4).\n", encoding="utf-8")
        found = paths.resolve_import("lib.pld", source_dir=folder / "near",
                                    directories=[str(folder / "shared")],
                                    interpreter_path=None)
        assert found == str(folder / "near" / "lib.pld"), found

        absolute = folder / "shared" / "other.pld"
        assert paths.resolve_import(str(absolute), source_dir=None, directories=[],
                                    interpreter_path=None) == str(absolute)
        assert paths.resolve_import("nowhere.pld", source_dir=folder, directories=[],
                                    interpreter_path=None) is None
    print("ok: an import name resolves in the order the engine uses")


def main(argv: list[str]) -> int:
    test_a_checkout_reads_its_own_tree()
    test_a_package_finds_everything_beside_itself()
    test_a_package_without_the_interpreter_names_the_expected_place()
    test_an_installed_copy_keeps_its_settings_in_appdata()
    test_an_installed_copy_under_opt_keeps_its_settings_in_xdg()
    test_an_app_bundle_is_installed_and_a_loose_copy_is_portable()
    test_a_macos_bundle_keeps_the_engine_in_bin()
    test_a_checkout_finds_the_macos_release_build()
    test_a_settings_file_that_is_already_there_is_kept()
    test_a_folder_that_cannot_be_written_falls_back_to_appdata()
    test_the_icons_come_from_the_same_answer()
    test_the_reference_reads_the_same_document()
    test_a_package_searches_only_what_the_student_added()
    test_the_import_list_is_trimmed_and_deduplicated()
    test_the_file_manager_is_called_the_way_its_platform_wants()
    test_the_file_manager_does_not_inherit_the_frozen_qt_environment()
    test_the_import_name_is_resolved_the_way_the_interpreter_resolves_it()
    print("all path checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
