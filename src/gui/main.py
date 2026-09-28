"""Entry point: `python src/gui/main.py [--exe PATH] [--include DIR]`."""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui.window import MainWindow  # noqa: E402

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
    arguments = parser.parse_args(argv)

    if not pathlib.Path(arguments.exe).exists():
        print(f"prologd not found: {arguments.exe}", file=sys.stderr)
        print("build it first (cmake --preset windows-msvc && cmake --build build/windows-msvc --config Release)", file=sys.stderr)
        return 1

    application = QApplication(sys.argv)
    window = MainWindow(arguments.exe, arguments.include)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
