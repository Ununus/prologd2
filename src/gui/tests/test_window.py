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

#: A failing ground query: the interpreter answers `НЕТ` itself, so the window
#: must not answer a second time.  Kept as the user wrote it.
PRIMES = """\
делится(Х,У):-УМНОЖЕНИЕ(У,М,0,Х).
проверка(Х,1):-!.
проверка(Х,У):-НЕ(делится(Х,У)),проверка(Х,#У-1#).
простое(1):-!.
простое(Х):-проверка(Х,#Х/2#).

?простое(3).
?простое(4).
"""

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

def empty_window(executable: str):
    """A ready window with one empty buffer, so a file takes its place.

    The welcome program otherwise keeps a tab of its own and every count of tabs
    would be off by one.
    """
    window = make_window(executable)
    assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
    window.editor().setPlainText("")
    window.buffers()[0].mark_saved()  # an empty buffer is not unsaved work
    return window


def discard_changes(window) -> None:
    """Closes a test window without a modal box ever appearing.

    A test that leaves a buffer modified and then closes the window would open a
    real `QMessageBox` and *hang* — no failure, no output, just a stuck suite.  So
    every test closes through here, where the answer is `DISCARD`.
    """
    from prologd_gui import window as window_module

    window._ask_save = lambda name: window_module.DISCARD
    window.close_all()
    window.close()


def test_a_file_takes_the_place_of_the_empty_buffer(executable: str) -> None:
    window = empty_window(executable)
    try:
        assert window.open_path(str(EXAMPLE))
        assert window.tab_count() == 1, "an empty buffer is a placeholder, not a tab"
        assert window.buffers()[0].title() == EXAMPLE.name
        assert window.windowTitle() == f"{EXAMPLE.name} — PrologD"

        # Opening the same file again shows its tab instead of a second copy.
        assert window.open_path(str(EXAMPLE))
        assert window.tab_count() == 1
        print("ok: an opened file replaces the empty buffer and never opens twice")
    finally:
        discard_changes(window)


def test_two_files_open_in_two_tabs(executable: str, directory: pathlib.Path) -> None:
    other = directory / "другой.pld"
    other.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        assert window.open_path(str(EXAMPLE))
        assert window.open_path(str(other))
        assert window.tab_count() == 2
        assert [buffer.title() for buffer in window.buffers()] == [EXAMPLE.name, other.name]
        assert window.current_path() == str(other), "the new tab is current"

        # Switching tabs switches the buffer, and the text with it.
        window._tabs.setCurrentIndex(0)
        assert window.current_path() == str(EXAMPLE)
        assert "факториал" in window.editor_text()
        window._next_tab()
        assert window.current_path() == str(other)
        assert window.editor_text() == "факт(1).\n"
        print("ok: two files, two tabs, and the current one follows the tab bar")
    finally:
        discard_changes(window)


def test_an_edit_marks_only_its_own_tab(executable: str, directory: pathlib.Path) -> None:
    other = directory / "второй.pld"
    other.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(EXAMPLE))
        window.open_path(str(other))
        assert window.editor_text() == "факт(1).\n"

        # Typing marks this buffer, not the other one.
        window.editor().insertPlainText("снег.\n")
        titles = [buffer.title() for buffer in window.buffers()]
        assert titles[0] == EXAMPLE.name, titles
        assert titles[1] == "*" + other.name, titles
        assert window.windowTitle() == f"*{other.name} — PrologD"
        print("ok: the modified marker is on the tab that changed, not on every tab")
    finally:
        discard_changes(window)


def test_closing_a_modified_tab_asks_first(executable: str, directory: pathlib.Path) -> None:
    from prologd_gui import window as window_module

    target = directory / "правки.pld"
    target.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(target))
        window.editor().insertPlainText("снег.\n")

        # «Отмена» keeps the buffer, and nothing is written.
        window._ask_save = lambda name: window_module.CANCEL
        assert window.close_buffer(0) is False
        assert window.tab_count() == 1
        assert target.read_text(encoding="utf-8") == "факт(1).\n"

        # «Сохранить» writes the file and then closes the tab.
        asked: list[str] = []
        window._ask_save = lambda name: asked.append(name) or window_module.SAVE
        assert window.close_buffer(0) is True
        assert asked == [target.name], asked
        assert target.read_text(encoding="utf-8") == "снег.\nфакт(1).\n", target.read_text("utf-8")
        print("ok: a modified buffer asks, cancelling keeps it, saving writes it")
    finally:
        discard_changes(window)


def test_closing_everything_asks_before_closing_anything(
    executable: str, directory: pathlib.Path
) -> None:
    """A cancel must leave *all* the buffers open, not just the last one."""
    from prologd_gui import window as window_module

    first = directory / "первый.pld"
    second = directory / "второй2.pld"
    for path in (first, second):
        path.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(first))
        window.open_path(str(second))
        window.buffers()[0].editor.insertPlainText("% правило\n")
        window.buffers()[1].editor.insertPlainText("% другое\n")
        assert [buffer.is_modified() for buffer in window.buffers()] == [True, True]

        answers = iter([window_module.DISCARD, window_module.CANCEL])
        asked: list[str] = []

        def answer(name: str) -> str:
            asked.append(name)
            return next(answers)

        window._ask_save = answer
        assert window.close_all() is False, "the cancel was ignored"
        assert window.tab_count() == 2, "a cancelled close must not have closed anything"
        assert asked == [first.name, second.name], asked
        print("ok: cancelling a close-all leaves every buffer open")
    finally:
        discard_changes(window)


def test_saving_clears_the_marker_and_keeps_the_file_shape(
    executable: str, directory: pathlib.Path
) -> None:
    """A CRLF file with Cyrillic stays CRLF cp1251 after a save."""
    target = directory / "cp1251.pld"
    target.write_bytes("факт(1).\r\n".encode("cp1251"))

    window = empty_window(executable)
    try:
        # Text that is not UTF-8 is never decoded by guesswork: the window asks,
        # and the answer is what opens the file.
        asked: list[str] = []
        window._ask_encoding = lambda path: asked.append(path) or "cp1251"
        assert window.open_path(str(target)) is True
        assert asked == [str(target)], asked
        assert window.editor_text() == "факт(1).\n"
        window.editor().insertPlainText("снег.\n")
        assert window.buffers()[0].title().startswith("*")

        assert window.save_buffer() is True
        # The whole file is written in the line ending it came with, including the
        # line that was just typed, and in its own encoding.
        from prologd_gui import documents

        expected = documents.with_eol("снег.\nфакт(1).\n", "\r\n").encode("cp1251")
        assert target.read_bytes() == expected, ascii(str(target.read_bytes()))
        assert window.buffers()[0].title() == target.name, "the marker must be gone"
        print("ok: save keeps the line ending and the encoding, and clears the marker")
    finally:
        discard_changes(window)


def test_cancelling_the_encoding_question_opens_nothing(
    executable: str, directory: pathlib.Path
) -> None:
    target = directory / "не-utf8.pld"
    target.write_bytes("факт(1).\n".encode("cp1251"))

    window = empty_window(executable)
    try:
        window._ask_encoding = lambda path: None  # the user closed the box
        assert window.open_path(str(target)) is False
        assert window.tab_count() == 1 and window.current_path() is None
        assert target.name in window.output_text(), "the file that failed is named"
        print("ok: a cancelled encoding question opens nothing and says why")
    finally:
        discard_changes(window)


def test_a_run_uses_the_tab_that_is_showing(executable: str) -> None:
    window = empty_window(executable)
    try:
        window.open_path(str(EXAMPLE))
        index = window.new_buffer()
        assert index == 1
        # The same program with a different goal: if the run used the *first*
        # tab, the answer would be 720.
        program = EXAMPLE.read_text(encoding="utf-8").replace("(6,Ф)", "(5,Ф)")
        window.editor().setPlainText(program)
        window.run_program()
        assert pump(window, lambda: "Ф=120" in window.output_text()), ascii(window.output_text())
        assert "720" not in window.output_text(), "the other tab's program ran"
        print("ok: a run uses the current tab, not the first one")
    finally:
        discard_changes(window)

def test_opening_does_not_run(executable: str) -> None:
    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"

        window.open_path(str(EXAMPLE))
        assert window.current_path() == str(EXAMPLE)
        # The editor works in lines, so the file's CRLF becomes LF here.
        expected = EXAMPLE.read_text(encoding="utf-8").replace("\r\n", "\n")
        got = window.editor_text()
        assert got == expected, (
            f"the editor holds {len(got)} characters, the file {len(expected)}: "
            f"{ascii(got[:60])} vs {ascii(expected[:60])}"
        )
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
    """Zoom is written straight to the settings and reaches every pane.

    The output pane is read-only but it is read next to the program, so it grows
    with the editor; storing the size once is what makes it survive a restart in
    both places.
    """
    window = make_window(executable)
    path = window._settings.path
    try:
        assert window.output().font_size == window.editor().font_size
        window.editor().set_font_size(17)
        size = window.editor().font_size
        assert size == 17
        assert window.output().font_size == size, "the output must zoom with the editor"
        assert window._query_line.font().pointSizeF() == size, "and so must the query line"
        assert window._settings.font_size == size
    finally:
        window.stop_program()
        window.close()

    from prologd_gui.settings import Settings

    assert Settings(path).font_size == size, "the stored font size did not survive a reopen"
    print(f"ok: a zoom of {size:.0f} pt reaches every pane and is stored in {path.name}")


def test_a_query_is_answered_once(executable: str) -> None:
    """The answer's text comes from the interpreter, never from the window.

    `result` only says the query is over.  A failing `?простое(4).` used to print
    `НЕТ` twice, which reads as a bug in the user's program: the second one was
    appended by the window, and the program was correct all along.
    """
    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
        window.editor().setPlainText(PRIMES)
        window.run_program()
        answer = pump(window, lambda: "НЕТ" in window.output_text())
        assert answer, f"no answer yet: {ascii(window.output_text())}"
        # `ascii()` on purpose: a failure is printed by a *piped* process, whose
        # stdout is the ANSI code page here, and a raw Cyrillic message cannot be
        # encoded at all — the crash would hide the failure it reports.
        text = window.output_text()
        assert text.count("ДА") == 1, f"expected one yes: {ascii(text)}"
        assert text.count("НЕТ") == 1, f"the answer is printed twice: {ascii(text)}"
        print("ok: a failed query is answered once (by the interpreter, not the window)")
    finally:
        window.stop_program()
        window.close()


def test_a_run_is_repeatable(executable: str) -> None:
    window = make_window(executable)
    try:
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"

        window.open_path(str(EXAMPLE))
        window.run_program()
        assert pump(window, lambda: ANSWER in window.output_text()), ascii(window.output_text())
        assert window.output_text().count(ANSWER) == 1, ascii(window.output_text())

        # A second run starts from a clean slate: one answer again, not two and
        # not the 2^n explosion a duplicated recursive clause would give.
        window.run_program()
        assert pump(window, lambda: ANSWER in window.output_text()), ascii(window.output_text())
        assert window.output_text().count(ANSWER) == 1, ascii(window.output_text())
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
        assert pump(window, lambda: ANSWER in window.output_text()), ascii(window.output_text())
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
    test_a_query_is_answered_once(executable)
    test_a_run_is_repeatable(executable)
    test_the_documented_shortcuts_are_bound(executable)
    with tempfile.TemporaryDirectory(prefix="prologd_gui_files_") as name:
        files = pathlib.Path(name)
        test_a_file_takes_the_place_of_the_empty_buffer(executable)
        test_two_files_open_in_two_tabs(executable, files)
        test_an_edit_marks_only_its_own_tab(executable, files)
        test_closing_a_modified_tab_asks_first(executable, files)
        test_closing_everything_asks_before_closing_anything(executable, files)
        test_saving_clears_the_marker_and_keeps_the_file_shape(executable, files)
        test_cancelling_the_encoding_question_opens_nothing(executable, files)
        test_a_run_uses_the_tab_that_is_showing(executable)
    print("all window checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
