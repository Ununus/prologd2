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
from prologd_gui.settings import Settings  # noqa: E402

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
    if with_executable:
        (directory / paths.EXECUTABLE_NAME).write_bytes(b"MZ")
    (directory / "examples" / "lib").mkdir(parents=True, exist_ok=True)
    (directory / "doc").mkdir(exist_ok=True)
    (directory / "doc" / "help.pdf").write_bytes(b"%PDF-1.4\n")
    (directory / "_internal" / "assets").mkdir(parents=True, exist_ok=True)
    return directory


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


def test_the_first_start_of_a_package_fills_the_import_row() -> None:
    import main  # the entry point, for the one start-up policy it owns

    with tempfile.TemporaryDirectory(prefix="prologd_package_") as name:
        package = make_package(pathlib.Path(name))
        with packaged(package):
            preferences = Settings(package / "gui.ini")
            assert main.seed_import_paths(preferences) is True
            wanted = str(package / "examples" / "lib")
            assert preferences.import_paths == [wanted], preferences.import_paths
            # The file exists now: the row is the user's from here on, so even
            # emptying it must not put the directory back.
            assert main.seed_import_paths(preferences) is False
            preferences.import_paths = []
            assert main.seed_import_paths(preferences) is False
            assert preferences.import_paths == []
    print("ok: lesson 11's import row is filled on the first start and never again")


def test_a_checkout_never_gets_that_row() -> None:
    import main

    with tempfile.TemporaryDirectory(prefix="prologd_checkout_") as name:
        file = pathlib.Path(name) / "gui.ini"
        preferences = Settings(file)
        assert main.seed_import_paths(preferences) is False
        assert preferences.import_paths == [], preferences.import_paths
        assert not file.exists(), "a checkout must not be written to"
    print("ok: a checkout is left alone")


def main(argv: list[str]) -> int:
    test_a_checkout_reads_its_own_tree()
    test_a_package_finds_everything_beside_itself()
    test_a_package_without_the_interpreter_names_the_expected_place()
    test_the_icons_come_from_the_same_answer()
    test_the_reference_reads_the_same_document()
    test_the_first_start_of_a_package_fills_the_import_row()
    test_a_checkout_never_gets_that_row()
    print("all path checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
