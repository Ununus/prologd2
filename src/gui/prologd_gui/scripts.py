"""The external tools the window runs.

One so far: `tools/image_to_pld.py`, which turns a picture into `картинка/6` facts —
and without `--out` into a whole little program.  «Скрипты → Сконвертировать
картинку…» fills in its arguments, runs it under the *same* interpreter (the tool
imports PySide6, so it is the venv's Python, not `python` from `PATH`), and puts the
answer into an unnamed tab.

A packaged build has no sources beside it, so `tool_path()` decides whether the entry
can work at all: the caller asks first and says so.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

from . import paths

#: The tool, relative to the folder the user sees (`data_root()`).
TOOL_NAME = "image_to_pld.py"


class ScriptError(RuntimeError):
    """The tool refused the work: carries its own message (its stderr)."""


def words(detail: str) -> str:
    """The tool's own words rather than the Python noise around them.

    A refusal (`--cell 100: 1..64 only`) is already one sentence and is passed through.
    A crash arrives as a traceback, and the window has one box for it: the traceback is
    reduced to the exception that ended it, which is the part that says what broke.
    The whole of it stays where the tool was started by hand.
    """
    lines = [line.strip() for line in detail.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    if any(line.startswith("Traceback (most recent call last)") for line in lines):
        return f"конвертер упал: {lines[-1]}"
    return detail.strip()


def tool_path() -> pathlib.Path:
    """Where the converter is, or a path that does not exist when it is not shipped."""
    return paths.data_root() / "tools" / TOOL_NAME


def image_arguments(
    image: str,
    name: str,
    *,
    cell: int = 16,
    canvas_cell: int | str = "auto",
    drop_background: bool = True,
    colors: int = 6,
    tolerance: int = 24,
    coverage: float = 0.30,
    background: str = "auto",
) -> list[str]:
    """The command line the dialog's fields become.

    `cell` is how many pixels of the picture one cell holds — the grid follows from it
    and the picture's own size, so there is no «сетка» key.  `canvas_cell` is the same
    cell on the canvas, and `auto` sizes the drawing to the engine's canvas.

    `drop_background` is the checkbox (the tool leaves the page out by default, and
    `--keep-background` says not to); `background` is `auto` or an `R,G,B` triple, the
    tool's own spelling — the window does not invent a second one.
    """
    arguments = [
        "--image", f"{name}={image}",
        "--cell", str(int(cell)),
        "--canvas-cell", str(canvas_cell),
        "--colors", str(int(colors)),
        "--tolerance", str(int(tolerance)),
        "--coverage", str(float(coverage)),
    ]
    if drop_background:
        arguments += ["--background", background or "auto"]
    else:
        # The tool refuses both keys together: a colour to drop is a page to drop.
        arguments.append("--keep-background")
    return arguments


def run(
    arguments: list[str],
    *,
    python: str | None = None,
    tool: pathlib.Path | None = None,
    timeout: float = 300.0,
    base_env: dict[str, str] | None = None,
) -> str:
    """Runs the converter and returns the text it printed.

    Without `--out` the tool prints a program and sends its summary to stderr, so the
    answer is the text to put into a tab; a failure is a `ScriptError` carrying the
    tool's own words, not a traceback.

    The child's stdout is a pipe, and a Windows process without a console writes a pipe
    in the *system ANSI code page* — the facts are Cyrillic and the tool died on
    `print`.  So the environment says UTF-8 outright, and the tool does the same for
    itself.
    """
    executable = pathlib.Path(tool if tool is not None else tool_path())
    if not executable.is_file():
        raise ScriptError(f"нет конвертера: {executable}")
    interpreter = python or sys.executable
    if not interpreter:
        raise ScriptError("не знаю, каким питоном запускать скрипт")
    environment = dict(os.environ if base_env is None else base_env)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    try:
        finished = subprocess.run(
            [interpreter, str(executable), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=environment,
        )
    except OSError as error:
        raise ScriptError(f"не удалось запустить конвертер: {error}") from error
    except subprocess.TimeoutExpired as slow:
        raise ScriptError(f"конвертер не ответил за {timeout:.0f} с") from slow
    if finished.returncode != 0:
        detail = words(finished.stderr or finished.stdout or "")
        raise ScriptError(detail or f"конвертер завершился с кодом {finished.returncode}")
    text = finished.stdout
    if not text.strip():
        raise ScriptError("конвертер ничего не напечатал")
    return text
