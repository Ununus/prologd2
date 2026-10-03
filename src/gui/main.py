"""Entry point: `python src/gui/main.py [--exe PATH] [--include DIR]`.

Where the interpreter, the icons, the documents and the settings file live is
decided by `prologd_gui.paths`: a checkout keeps the layout it always had, a
frozen package (task_61) finds all four beside its own executable.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import appearance, assets, paths  # noqa: E402
from prologd_gui.settings import Settings  # noqa: E402
from prologd_gui.window import MainWindow  # noqa: E402

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def seed_import_paths(preferences: Settings) -> bool:
    """Gives a package the import directory its own course needs (task_61).

    A portable build carries `examples/`, and lesson 11 imports `lib/` from there,
    so on the **first** start — while the settings file does not exist yet — the
    row is filled in.  Afterwards it is an ordinary preference: whoever deletes it
    keeps it deleted.  A checkout is not `frozen` and is never touched.
    """
    if not paths.frozen() or preferences.path.exists():
        return False
    library = paths.example_library()
    if not library.is_dir():
        return False
    preferences.import_paths = [str(library)]
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PrologD graphical front-end")
    parser.add_argument("--exe", default=paths.interpreter(), help="path to the prologd executable")
    parser.add_argument("--include", action="append", default=[], help="import search directory (repeatable)")
    parser.add_argument(
        "--theme",
        default=None,
        choices=appearance.THEMES,
        help="window appearance: light (default — the syntax colours need a light background) or system",
    )
    parser.add_argument(
        "--settings",
        default=None,
        # `%%` because argparse formats the help string: a lone `%` is an error.
        help="settings file (default: %%LOCALAPPDATA%%\\PrologD\\gui\\gui.ini)",
    )
    parser.add_argument(
        "--icons",
        default=None,
        help="directory with the toolbar icons (default: src/gui/assets)",
    )
    arguments = parser.parse_args(argv)
    assets.set_directory(arguments.icons)

    # The settings path is derived from these names, so they are set before the
    # first `Settings()` call rather than left to Qt's defaults.
    QCoreApplication.setOrganizationName(Settings.organization)
    QCoreApplication.setApplicationName(Settings.application)
    # A package keeps its settings beside the window (task_61); in a checkout the
    # argument stays empty and Qt computes the usual AppData path.
    preferences = Settings(arguments.settings or paths.settings_path())
    seed_import_paths(preferences)

    # Which interpreter will actually run: the `execution/interpreter` row when it
    # names one, else the `--exe` of this launch (task_46).  The check follows
    # that path, so a teacher's machine that ships the binary next to the window
    # is not refused because the default build path does not exist there.
    executable = preferences.interpreter.strip() or arguments.exe
    if not pathlib.Path(executable).is_file():
        print(f"prologd not found: {executable}", file=sys.stderr)
        if paths.frozen():
            print(
                "the package is incomplete: prologd.exe must sit beside prologd-gui.exe",
                file=sys.stderr,
            )
        else:
            print("build it first (cmake --preset windows-msvc && cmake --build build/windows-msvc --config Release)", file=sys.stderr)
        return 1

    # Qt must not see our own options: it parses the arguments it is given and
    # would complain about `--theme`.
    application = QApplication(sys.argv[:1])
    appearance.apply_theme(application, arguments.theme or preferences.theme)
    if arguments.theme:
        # An explicit choice sticks for the next start.
        preferences.theme = arguments.theme
    window = MainWindow(arguments.exe, arguments.include, preferences)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
