"""Checks of the entry point's command line (task_116): a file becomes a document.

    python src/gui/tests/test_main.py [path-to-prologu]

No window is built and no interpreter is run.  `main()` is called with the two
pieces that would make it a real start replaced by recorders: the application
object — whose `exec()` would otherwise enter an event loop and never return — and
the window.  What is left to check is the wiring between the command line and the
window, which is exactly what the installer's `.pld` association depends on: the
shell starts `prologd-gui.exe "<file>"`, and that path has to arrive as the
document the window opens on.

The behaviour itself — the file is the only tab, and a missing one falls back to
the welcome program — is checked in `test_window.py`, where a real window exists.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import main as main_module  # noqa: E402
from test_session import find_executable  # noqa: E402


def run_main(argv: list[str]) -> list[object]:
    """`main.main(argv)`, with the application and the window replaced."""
    made: list[object] = []

    class Recorder:
        """Stands in for `MainWindow`: keeps what it was handed."""

        def __init__(self, executable, includes=None, settings=None, path=None):
            self.executable = executable
            self.includes = includes
            self.settings = settings
            self.path = path
            self.shown = False
            made.append(self)

        def show(self) -> None:
            self.shown = True

    class Application:
        """Stands in for `QApplication`: `exec()` returns instead of looping."""

        def __init__(self, argv):
            self.argv = list(argv)
            self.ran = False

        def exec(self) -> int:
            self.ran = True
            return 0

    saved = (main_module.MainWindow, main_module.QApplication, main_module.appearance)
    main_module.MainWindow = Recorder
    main_module.QApplication = Application
    # The table of themes is read while the parser is built; only the applying is
    # replaced, because it wants a real application object to paint.
    main_module.appearance = types.SimpleNamespace(
        THEMES=main_module.appearance.THEMES,
        apply_theme=lambda application, theme: None,
    )
    try:
        code = main_module.main(list(argv))
    finally:
        main_module.MainWindow, main_module.QApplication, main_module.appearance = saved
    assert code == 0, code
    return made


def test_the_file_on_the_command_line_reaches_the_window(
    executable: str, directory: pathlib.Path
) -> None:
    """task_116: `prologd-gui.exe <file>` opens *that* file, named absolutely.

    An absolute name is what the shell passes and what the session, the recent
    list and the status line all store; a path typed into a terminal is spelled
    relative to it, and the window is not the one that should resolve it.
    """
    program = directory / "программа.pld"
    program.write_text("снег.\n", encoding="utf-8")
    settings = directory / "gui.ini"

    made = run_main(["--exe", executable, "--settings", str(settings), str(program)])
    assert len(made) == 1, made
    window = made[0]
    assert window.shown is True, "the window is shown before the loop runs"
    assert window.path == str(program.resolve()), window.path
    assert window.executable == executable, window.executable
    assert window.includes == [], window.includes

    made = run_main([str(program), "--exe", executable, "--settings", str(settings)])
    assert made[0].path == str(program.resolve()), "an option after the file still parses"
    print("ok: a file named on the command line reaches the window, named absolutely")


def test_without_a_file_the_window_gets_none(
    executable: str, directory: pathlib.Path
) -> None:
    """No positional argument means no document — and options still arrive.

    The check exists for the shape of the parser: a positional that swallowed the
    options, or a default that invented a file name, would show up here and
    nowhere else.
    """
    settings = directory / "gui.ini"

    made = run_main(["--exe", executable, "--settings", str(settings)])
    assert made[0].path is None, made[0].path
    assert made[0].includes == []

    made = run_main(
        ["--exe", executable, "--settings", str(settings),
         "--include", "один", "--include", "два"]
    )
    assert made[0].path is None, made[0].path
    assert made[0].includes == ["один", "два"], made[0].includes
    print("ok: no file means no document, and --include still reaches the window")


def main(argv: list[str]) -> int:
    executable = find_executable(argv)
    assert executable is not None, "point the check at a build (PROLOGD_TEST_EXE)"
    with tempfile.TemporaryDirectory(prefix="prologd_gui_main_") as name:
        directory = pathlib.Path(name)
        test_the_file_on_the_command_line_reaches_the_window(executable, directory)
        test_without_a_file_the_window_gets_none(executable, directory)
    print("all entry point checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
