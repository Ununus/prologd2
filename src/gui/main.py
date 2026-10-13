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
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402



def report_missing_interpreter(executable: str) -> int:
    """Says why the window cannot start, in the way the build can be heard.

    A checkout is started from a terminal, so printing is enough and the message
    names the command that builds the interpreter.  A **frozen** build is started
    by double-clicking an icon, with no console anywhere: printing there is
    printing into nothing, so the one thing that is wrong with the package gets a
    box instead.  The box is modal on purpose — it is the last thing the process
    does (task_61 §7.1).
    """
    if not paths.frozen():
        print(f"{paths.EXECUTABLE_NAME} not found: {executable}", file=sys.stderr)
        print(
            "build it first (cmake --preset windows-msvc && cmake --build build/windows-msvc --config Release)",
            file=sys.stderr,
        )
        return 1
    QApplication(sys.argv[:1])  # a box needs an application object first
    QMessageBox.critical(
        None,
        "Пролог-Д 2.0",
        f"Рядом с окном нет интерпретатора {paths.EXECUTABLE_NAME}.\n\n"
        f"Искали здесь: {executable}\n"
        f"Папка сборки: {paths.data_root()}\n\n"
        f"Сборка неполная: файл {paths.EXECUTABLE_NAME} должен лежать рядом с prologd-gui.exe.",
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PrologD graphical front-end")
    parser.add_argument("--exe", default=paths.interpreter(), help="path to the interpreter (prologu.exe)")
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

    # Which interpreter will actually run: the `execution/interpreter` row when it
    # names one, else the `--exe` of this launch (task_46).  The check follows
    # that path, so a teacher's machine that ships the binary next to the window
    # is not refused because the default build path does not exist there.
    executable = preferences.interpreter.strip() or arguments.exe
    if not pathlib.Path(executable).is_file():
        return report_missing_interpreter(executable)

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
