"""Offscreen checks of the window's file handling (needs PySide6 and a build).

    python src/gui/tests/test_window.py [path-to-prologd]

The defect this pins down: **Открыть** used to push the file into the running
interpreter, so opening it a second time — or running the buffer and then opening
the file — left two copies of the program in one session.  Duplicated recursive
clauses multiply the solutions, so the factorial example then answered 64 times
instead of once, which looks like an endless loop.  Opening fills the editor and
nothing else; running is F5, into a fresh session.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_session import find_executable, pump  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - main() reports it
    QApplication = None  # type: ignore[assignment]

EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / "factorial.pld"
ANSWER = "Ф=720\n"

#: Kept so the temporary directories outlive the windows that read from them.
_SETTINGS_DIRECTORIES: list[tempfile.TemporaryDirectory] = []


def make_window(executable: str):
    """A window whose preferences live in a throw-away file.

    Without this the window would read (and, on zoom, write) the settings of the
    person running the tests.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    directory = tempfile.TemporaryDirectory(prefix="prologd_gui_test_")
    _SETTINGS_DIRECTORIES.append(directory)
    settings = Settings(pathlib.Path(directory.name) / "gui.ini")
    return MainWindow(executable, [], settings)


def test_opening_does_not_run(executable: str) -> None:
    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"

        window.open_path(str(EXAMPLE))
        assert window.current_path() == str(EXAMPLE)
        # The editor works in lines, so the file's CRLF becomes LF here.
        expected = EXAMPLE.read_text(encoding="utf-8").replace("\r\n", "\n")
        assert window.editor_text() == expected
        assert EXAMPLE.name in window.windowTitle()

        # Opening it again must be harmless: nothing has been executed, so there
        # is nothing to duplicate in the session.
        window.open_path(str(EXAMPLE))
        assert window.output_text() == "", f"opening ran the program: {window.output_text()!r}"
        print("ok: opening fills the editor and does not run anything")
    finally:
        window.stop_program()
        window.close()


def test_the_editor_remembers_the_font_size(executable: str) -> None:
    """Zoom is written straight to the settings, so it survives a restart."""
    window = make_window(executable)
    path = window._settings.path
    try:
        window.editor().zoom_by(3)
        size = window.editor().font_size
        assert window._settings.font_size == size
    finally:
        window.stop_program()
        window.close()

    from prologd_gui.settings import Settings

    assert Settings(path).font_size == size, "the stored font size did not survive a reopen"
    print(f"ok: a zoom of {size:.0f} pt is stored in {path.name}")


def test_a_run_is_repeatable(executable: str) -> None:
    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"

        window.open_path(str(EXAMPLE))
        window.run_program()
        assert pump(window, lambda: ANSWER in window.output_text()), window.output_text()
        assert window.output_text().count(ANSWER) == 1, window.output_text()

        # A second run starts from a clean slate: one answer again, not two and
        # not the 2^n explosion a duplicated recursive clause would give.
        window.run_program()
        assert pump(window, lambda: ANSWER in window.output_text()), window.output_text()
        assert window.output_text().count(ANSWER) == 1, window.output_text()
        print("ok: two runs answer once each (fresh session, cleared pane)")
    finally:
        window.stop_program()
        window.close()


def test_the_documented_shortcuts_are_bound(executable: str) -> None:
    """A key that the plan documents must actually be bound to the action.

    **Запустить** was bound to `Ctrl+R` while the plan promised `F5`, so pressing
    the documented key did nothing at all.
    """
    from PySide6.QtWidgets import QToolBar

    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
        actions = {
            action.text(): action
            for bar in window.findChildren(QToolBar)
            for action in bar.actions()
        }
        bound = {action: {key.toString() for key in actions[action].shortcuts()} for action in actions}
        for text, expected in (
            ("Запустить", {"F5", "Ctrl+R"}),
            ("Остановить", {"Shift+F5", "Ctrl+."}),
            ("Открыть…", {"Ctrl+O"}),
            ("Очистить вывод", {"Ctrl+L"}),
        ):
            assert text in actions, f"no {text} action, got {sorted(actions)}"
            assert expected <= bound[text], f"{text} is bound to {sorted(bound[text])}"

        # Editing commands live on the window rather than on the toolbar, which
        # task_26 fills with the real set of buttons.
        window_actions = {action.text(): action for action in window.actions()}
        for text, expected in (
            ("Закомментировать", "Ctrl+K"),
            ("Раскомментировать", "Ctrl+U"),
            ("Сбросить масштаб", "Ctrl+0"),
        ):
            assert text in window_actions, f"no {text} action, got {sorted(window_actions)}"
            keys = {key.toString() for key in window_actions[text].shortcuts()}
            assert keys == {expected}, f"{text} is bound to {sorted(keys)}"

        # The key press runs the action: trigger is the same path a shortcut takes.
        window.open_path(str(EXAMPLE))
        actions["Запустить"].trigger()
        assert pump(window, lambda: ANSWER in window.output_text()), window.output_text()
        print("ok: F5/Shift+F5, Ctrl+K/U and Ctrl+0 are bound and the action runs the program")
    finally:
        window.stop_program()
        window.close()


def main(argv: list[str]) -> int:
    if QApplication is None:
        print("skipped: PySide6 is not installed")
        return 0
    if not EXAMPLE.exists():
        print(f"skipped: {EXAMPLE} is missing")
        return 0
    executable = find_executable(argv)
    if executable is None:
        print("skipped: no prologd build found, pass its path to check the window")
        return 0

    application = QApplication(sys.argv[:1])
    print(f"interpreter: {executable}")
    test_opening_does_not_run(executable)
    test_the_editor_remembers_the_font_size(executable)
    test_a_run_is_repeatable(executable)
    test_the_documented_shortcuts_are_bound(executable)
    print("all window checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
