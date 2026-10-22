"""Entry point: `python src/gui/main.py [--exe PATH] [--include DIR]`.

Where the engines, the icons, the documents and the settings file live is
decided by `prologd_gui.paths`: a checkout keeps the layout it always had, a
frozen package (task_61) finds all four beside its own executable.

There are two engines since task_79 — our own «Пролог-У» and the original
«Пролог-Д» — and the window is a host of both.  Which one this *launch* starts is
`engines.launch`'s answer from `--exe` and the stored choice; the check below is
the same answer, so a window is never opened on a file that is not there.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import appearance, assets, engines, paths  # noqa: E402
from prologd_gui.settings import Settings  # noqa: E402
from prologd_gui.window import MainWindow  # noqa: E402

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402



def report_missing_interpreter(
    executable: str, engine: engines.Engine, folder: str = ""
) -> int:
    """Says why the window cannot start, in the way the build can be heard.

    A checkout is started from a terminal, so printing is enough and the message
    names the command that builds the interpreter — with the switch that adds the
    *second* one when that is what is missing (task_78).  A **frozen** build is
    started by double-clicking an icon, with no console anywhere: printing there is
    printing into nothing, so the one thing that is wrong with the package gets a
    box instead.  The box is modal on purpose — it is the last thing the process
    does (task_61 §7.1).

    Both engine files are named when neither is there (part 143): the window can
    start on whichever one a build carries, so a folder with none of them is a
    broken copy, and the reader should see both names rather than the default one.
    """
    name = engine.file_name
    other = engines.other(engine)
    other_path = paths.engine_executable(other, folder=folder)
    also_missing = not pathlib.Path(other_path).is_file()
    if not paths.frozen():
        print(f"{name} not found: {executable}", file=sys.stderr)
        if also_missing:
            print(f"{other.file_name} not found either: {other_path}", file=sys.stderr)
        print(
            "build it first (cmake --preset windows-msvc && cmake --build build/windows-msvc --config Release)",
            file=sys.stderr,
        )
        if engine is engines.ORIGINAL or also_missing:
            print("the original engine is optional: configure with -DBUILD_WITH_PROLOGD=ON (task_78)",
                  file=sys.stderr)
        return 1
    QApplication(sys.argv[:1])  # a box needs an application object first
    wanted = f"{name}"
    if also_missing:
        wanted = f"{name} и {other.file_name}"
    QMessageBox.critical(
        None,
        "Пролог-Д 2.0",
        f"Рядом с окном нет интерпретатора {name}.\n\n"
        f"Искали здесь: {executable}\n"
        f"Папка сборки: {paths.data_root()}\n\n"
        f"Сборка неполная: файл {wanted} должен лежать рядом с prologd-gui.exe.",
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PrologD graphical front-end")
    parser.add_argument(
        "--exe",
        default=None,
        help="the engine of this launch: its folder is where both engines are looked "
             "for, and a name that is one of them picks it (default: search beside the "
             "window)",
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

    # Which engine runs this time, and where its file is looked for (task_79).  The
    # rule is `engines.launch`'s: `--exe`, then task_46's «Интерпретатор» row — the
    # one that is still read from the file, so a machine that named another build
    # keeps running it — then the stored choice.  The check follows that path, so a
    # teacher's machine that ships the binaries next to the window is not refused
    # because the default build path does not exist there.
    launch = (arguments.exe or "").strip() or preferences.legacy_interpreter
    engine, folder = engines.launch(launch, preferences.engine)
    # A build may carry one engine only (part 143 — the package of the original
    # «Пролог-Д»): the choice whose file is not there gives way to the one that is,
    # and the window says so in the pane.  A package with one engine answers it
    # whatever the settings say (part 144), so a `gui.ini` copied from another
    # machine cannot point the window at an engine the folder does not have.
    # `starting_engine` answers the choice itself when *neither* file is there, and
    # the report below names what is missing.
    engine, folder, _ = paths.starting_engine(engine, folder=folder)
    executable = paths.engine_executable(engine, folder=folder)
    if not pathlib.Path(executable).is_file():
        return report_missing_interpreter(executable, engine, folder)

    # Qt must not see our own options: it parses the arguments it is given and
    # would complain about `--theme`.
    application = QApplication(sys.argv[:1])
    appearance.apply_theme(application, arguments.theme or preferences.theme)
    if arguments.theme:
        # An explicit choice sticks for the next start.
        preferences.theme = arguments.theme
    window = MainWindow(launch, arguments.include, preferences)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
