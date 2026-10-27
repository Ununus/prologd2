"""Entry point: `python src/gui/main.py [--exe PATH] [--include DIR] [FILE]`.

Where the interpreter, the icons, the documents and the settings file live is
decided by `prologd_gui.paths`: a checkout keeps the layout it always had, a
frozen package (task_61) finds all four beside its own executable.  `--exe` pins
one launch to a build of its own; the check below is the same answer the window
runs with, so a window is never opened on a file that is not there.
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
    name = paths.EXECUTABLE_NAME
    if not paths.frozen():
        print(f"{name} not found: {executable}", file=sys.stderr)
        print(
            "build it first (cmake --preset <preset> && cmake --build --preset <preset>)",
            file=sys.stderr,
        )
        return 1
    QApplication(sys.argv[:1])  # a box needs an application object first
    QMessageBox.critical(
        None,
        "Пролог-Д",
        f"Рядом с окном нет интерпретатора {name}.\n\n"
        f"Искали здесь: {executable}\n"
        f"Папка сборки: {paths.data_root()}\n\n"
        f"Сборка неполная: файл {name} должен лежать рядом с prologd-gui.exe.",
    )
    return 1


class WindowParser(argparse.ArgumentParser):
    """Says what is wrong in a box rather than exiting into nothing (task_116).

    A packaged window is started by a double-click and has no console: `argparse`'s
    own `error` prints to stderr and exits with code 2, which is exactly what a
    broken file association looked like on 2026-10-24 — the right icon, no window,
    no message.  A checkout keeps the plain behaviour: it is started from a terminal
    and its stderr is read by a person.
    """

    def error(self, message: str) -> None:  # noqa: D401 - argparse's own name
        if not paths.frozen():
            super().error(message)
            return
        QApplication(sys.argv[:1])  # a box needs an application object first
        QMessageBox.critical(
            None,
            "Пролог-Д",
            f"Не понимаю аргументы командной строки:\n{message}",
        )
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = WindowParser(description="PrologD graphical front-end")
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        metavar="FILE",
        help="a program to open in the window; the shell passes one when a .pld file "
             "is double-clicked (task_116)",
    )
    parser.add_argument(
        "--exe",
        default=None,
        help="the interpreter of this launch: the file itself or its folder, looked "
             "for there and nowhere else (default: search beside the window)",
    )
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

    # Where the interpreter is looked for: `--exe`, then task_46's «Интерпретатор»
    # row — still read from the file, so a machine that named another build keeps
    # running it — and otherwise the usual places.  The check follows that path, so
    # a teacher's machine that ships the binary next to the window is not refused
    # because the default build path does not exist there.
    launch = (arguments.exe or "").strip() or preferences.legacy_interpreter
    folder = ""
    if launch:
        parent = str(pathlib.Path(launch).parent)
        folder = "" if parent in ("", ".") else parent
    executable = paths.interpreter(folder)
    if not pathlib.Path(executable).is_file():
        return report_missing_interpreter(executable)

    # Qt must not see our own options: it parses the arguments it is given and
    # would complain about `--theme`.
    application = QApplication(sys.argv[:1])
    appearance.apply_theme(application, arguments.theme or preferences.theme)
    if arguments.theme:
        # An explicit choice sticks for the next start.
        preferences.theme = arguments.theme
    # The shell hands over an absolute path, one typed into a terminal need not
    # be; the tab, the recent list and the session all want the file named one
    # way (task_116).  A path that is not there still becomes absolute — the
    # note the window writes reads better with a full name.
    start = str(pathlib.Path(arguments.file).resolve()) if arguments.file else None
    window = MainWindow(launch, arguments.include, preferences, path=start)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
