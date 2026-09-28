"""Entry point: `python src/gui/main.py [--exe PATH] [--include DIR]`."""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import appearance, assets  # noqa: E402
from prologd_gui.settings import Settings  # noqa: E402
from prologd_gui.window import MainWindow  # noqa: E402

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def default_executable() -> str:
    """The binary this checkout most likely built."""
    root = pathlib.Path(__file__).resolve().parents[2]
    candidates = [
        root / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "linux-release" / "src" / "cli" / "prologd",
        root / "build" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "src" / "cli" / "prologd",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PrologD graphical front-end")
    parser.add_argument("--exe", default=default_executable(), help="path to the prologd executable")
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

    if not pathlib.Path(arguments.exe).exists():
        print(f"prologd not found: {arguments.exe}", file=sys.stderr)
        print("build it first (cmake --preset windows-msvc && cmake --build build/windows-msvc --config Release)", file=sys.stderr)
        return 1

    # The settings path is derived from these names, so they are set before the
    # first `Settings()` call rather than left to Qt's defaults.
    QCoreApplication.setOrganizationName(Settings.organization)
    QCoreApplication.setApplicationName(Settings.application)
    preferences = Settings(arguments.settings)

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
