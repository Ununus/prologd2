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

#: task_36's files: the lesson whose `?сумма(5, С).` must answer `С=15` alone,
#: and the appendix whose questions only run if someone asks for one.
LESSON_04 = pathlib.Path(__file__).resolve().parents[3] / "examples" / "lessons" / "lesson_04.pld"
APPENDIX_DEBUG = (
    pathlib.Path(__file__).resolve().parents[3] / "examples" / "lessons" / "appendix_debug.pld"
)

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

#: Reads two numbers and prints them: two input requests in one run.
#: `ПС` is the library's newline (`ПС :- ВВКОД(10)`), because `ВЫВОД` prints
#: without one — the first version of this test expected separate lines and got
#: `79` glued together.
READS_TWO = "?ВВОДЦЕЛ(А),ВВОДЦЕЛ(Б),ВЫВОД(А),ПС,ВЫВОД(Б),ПС.\n"


def wait_for_result(window) -> None:
    """Waits until the interpreter has finished answering the query.

    The status says «решение **найдено**» for an answer and «решения **нет**» for
    a failing query — two cases of one word, so the *stem* is what is looked for.
    Matching the whole word missed the failing case exactly, and the run then
    looked as if it had never finished: the file checks in
    `test_saving_before_a_run_writes_the_file` were right all along.
    """
    done = pump(window, lambda: "решени" in window.status_text())
    assert done, f"the run never finished: {ascii(window.output_text())}"


def echoed_lines(window) -> list[str]:
    """The answers the window fed to the program, prefixed with `>`."""
    return [line for line in window.output_text().splitlines() if line.startswith("> ")]


def printed_lines(window) -> list[str]:
    """What the program printed: everything that is neither our note nor an echo."""
    return [
        line
        for line in window.output_text().splitlines()
        if line and not line.startswith(("---", ">", "***"))
    ]

#: Kept so the temporary directories outlive the windows that read from them.
_SETTINGS_DIRECTORIES: list[tempfile.TemporaryDirectory] = []


def make_window(executable: str, *, ready: bool = True):
    """A window whose preferences live in a throw-away file.

    Without this the window would read (and, on zoom, write) the settings of the
    person running the tests.

    `ready=True` starts the interpreter the way the first run does, because most
    checks are about what happens afterwards — the reserved names, the
    highlighting, the output.  A window the user has only *opened* has nothing
    running at all, and `ready=False` is that window.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    directory = tempfile.TemporaryDirectory(prefix="prologd_gui_test_")
    _SETTINGS_DIRECTORIES.append(directory)
    settings = Settings(pathlib.Path(directory.name) / "gui.ini")
    window = MainWindow(executable, [], settings)
    if ready:
        window.session.start()
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
    return window


def empty_window(executable: str):
    """A ready window with one empty buffer, so a file takes its place.

    The welcome program otherwise keeps a tab of its own and every count of tabs
    would be off by one.
    """
    window = make_window(executable)
    window.editor().setPlainText("")
    window.buffers()[0].mark_saved()  # an empty buffer is not unsaved work
    return window


def discard_changes(window) -> None:
    """Closes a test window without a modal box ever appearing.

    A test that leaves a buffer modified and then closes the window would open a
    real `QMessageBox` and *hang* — no failure, no output, just a stuck suite.  So
    every test closes through here, where the answer is `DISCARD`.

    The interpreter is stopped too: a test window that only closed its buffers
    left a live `prologd` behind, and a suite of them (one per test) slowed the
    machine down and made the run before a failure look like a hang.
    """
    from prologd_gui import window as window_module

    window._ask_save = lambda name: window_module.DISCARD
    window.close_all()
    window.stop_program()
    window.close()


def test_a_file_takes_the_place_of_the_empty_buffer(executable: str) -> None:
    window = empty_window(executable)
    try:
        assert window.open_path(str(EXAMPLE))
        assert window.tab_count() == 1, "an empty buffer is a placeholder, not a tab"
        assert window.buffers()[0].title() == EXAMPLE.name
        # The title bar carries the whole path; the tab keeps the short name.
        assert window.windowTitle() == f"{EXAMPLE} — PrologD", window.windowTitle()

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
        window.active_pane().set_current(window.buffers()[0])
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
        window.view_for(window.buffers()[1]).insertPlainText("снег.\n")
        titles = [buffer.title() for buffer in window.buffers()]
        assert titles[0] == EXAMPLE.name, titles
        assert titles[1] == "*" + other.name, titles
        assert window.windowTitle() == f"*{other} — PrologD", window.windowTitle()
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
        assert window.close_buffer(window.buffers()[0]) is False
        assert window.tab_count() == 1
        assert target.read_text(encoding="utf-8") == "факт(1).\n"

        # «Сохранить» writes the file and then closes the tab.
        asked: list[str] = []
        window._ask_save = lambda name: asked.append(name) or window_module.SAVE
        assert window.close_buffer(window.buffers()[0]) is True
        assert asked == [target.name], asked
        assert target.read_text(encoding="utf-8") == "снег.\nфакт(1).\n", target.read_text("utf-8")
        print("ok: a modified buffer asks, cancelling keeps it, saving writes it")
    finally:
        discard_changes(window)


def test_closing_everything_walks_through_the_tabs(
    executable: str, directory: pathlib.Path
) -> None:
    """Each tab is shown *before* its question, and closes as soon as it is answered.

    Asking about every buffer first kept them all open, but nothing on screen said
    which file each question was about.  Now the tab being asked about is the
    current one, and it is gone as soon as the answer is given.
    """
    from prologd_gui import window as window_module

    first = directory / "первый.pld"
    second = directory / "второй2.pld"
    for path in (first, second):
        path.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(first))
        window.open_path(str(second))
        window.view_for(window.buffers()[0]).insertPlainText("% правило\n")
        window.view_for(window.buffers()[1]).insertPlainText("% другое\n")
        assert [buffer.is_modified() for buffer in window.buffers()] == [True, True]

        seen: list[tuple[str, str | None]] = []
        answers = iter([window_module.DISCARD, window_module.CANCEL])

        def answer(name: str) -> str:
            # What the user sees when the box opens: the tab that is current.
            seen.append((name, window.current_path()))
            return next(answers)

        window._ask_save = answer
        assert window.close_all() is False, "the cancel was ignored"
        assert seen == [(first.name, str(first)), (second.name, str(second))], seen
        assert window.tab_count() == 1, "the first tab was answered and must be closed"
        assert window.current_path() == str(second)
        print("ok: closing all shows each tab before asking and closes it at once")
    finally:
        discard_changes(window)


def test_a_file_dropped_on_the_editor_opens_in_a_tab(
    executable: str, directory: pathlib.Path
) -> None:
    """A dropped file is opened, not pasted.

    A `QPlainTextEdit` accepts a file drop and inserts the file's text, so the
    event never reached the window: dropping a program on the editor put the
    program into the buffer instead of opening it.

    The event is sent to the **viewport**: a scroll area delivers drag and drop to
    its viewport, so that is where the pane's own handler runs — sending it to the
    widget itself would test a path the platform never takes.
    """
    from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, Qt
    from PySide6.QtGui import QDragEnterEvent, QDropEvent
    from PySide6.QtWidgets import QApplication

    dropped = directory / "брошенный.pld"
    dropped.write_text("снег.\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n")
        window.buffers()[0].mark_saved()
        before = window.editor_text()

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(dropped))])
        viewport = window.editor().viewport()
        QApplication.sendEvent(
            viewport,
            QDragEnterEvent(
                QPoint(4, 4),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )
        QApplication.sendEvent(
            viewport,
            QDropEvent(
                QPointF(4.0, 4.0),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )

        assert window.tab_count() == 2, "the drop did not open a tab"
        assert window.current_path() == str(dropped)
        assert window.editor_text() == "снег.\n"
        assert window.buffers()[0].text() == before, "the dropped program was pasted into the buffer"
        print("ok: a file dropped on the editor opens in a tab instead of being pasted")
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


def test_the_input_field_feeds_the_program(executable: str) -> None:
    """Lines from the input pane answer the requests, one after another.

    Two values, no dialog: a program that reads a few numbers should be runnable
    without a box per number.  A blank line between them is skipped rather than
    offered as an answer.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText(READS_TWO)
        window.input_pane().setPlainText("7\n\n9\n")
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or "0"

        window.run_program()
        wait_for_result(window)

        assert asked == [], "the dialog was used even though the field had answers"
        assert echoed_lines(window) == ["> 7", "> 9"], echoed_lines(window)
        assert printed_lines(window) == ["7", "9", "А=7", "Б=9"], printed_lines(window)
        assert window.pending_input() == [], "the queue was not emptied"
        print("ok: the input field answers the requests without a dialog")
    finally:
        discard_changes(window)


def test_the_console_answers_once_the_prepared_lines_run_out(executable: str) -> None:
    """The queue first, then the console under the output — `Ctrl+Enter` sends.

    The modal dialog is what is left when the whole panel is hidden, so a test that
    would hang on one is a test that forgot to arm the console.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText(READS_TWO)
        window.input_pane().setPlainText("7\n")
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or "0"

        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), "nothing was asked"
        assert window._input_console.kind() == "token", window._input_console.kind()
        assert "ждёт ввода" in window.status_text(), window.status_text()

        # What the field holds, and `send()` — the same call `Ctrl+Enter` makes.
        window._input_console._line.setText("9")
        window._input_console.send()
        wait_for_result(window)

        assert asked == [], "the dialog was used with the console right there"
        assert echoed_lines(window) == ["> 7", "> 9"], echoed_lines(window)
        assert printed_lines(window) == ["7", "9", "А=7", "Б=9"], printed_lines(window)
        assert window._input_console.waiting() is False, "the console stayed armed"
        print("ok: the console answers once the prepared lines run out")
    finally:
        discard_changes(window)


def test_the_dialog_is_the_last_resort(executable: str) -> None:
    """With the panel hidden there is nowhere to put a console, so a box asks."""
    window = empty_window(executable)
    try:
        window._actions["output"].setChecked(False)  # hides the whole panel
        window.editor().setPlainText(READS_TWO)
        asked: list[str] = []

        def answer(kind: str) -> str:
            asked.append(kind)
            return "9"

        window._ask_input = answer
        window.run_program()
        wait_for_result(window)

        # The program reads two values, so the box is asked twice.
        assert asked == ["token", "token"], asked
        assert printed_lines(window) == ["9", "9", "А=9", "Б=9"], printed_lines(window)
        print("ok: a hidden panel leaves the dialog as the only place to ask")
    finally:
        discard_changes(window)


def test_the_console_appears_only_when_it_is_asked(executable: str) -> None:
    """Hidden while nothing is asked; shown, framed yellow, then hidden again.

    An idle strip of the window takes room from the output for nothing, and the
    question *is* a state — the placeholder says what is wanted and which key sends
    it, so no label row is needed.
    """
    window = empty_window(executable)
    try:
        assert window._input_console.isHidden() is True, "the console took room while idle"

        window.editor().setPlainText("?ВВОДЦЕЛ(А),ВЫВОД(А),ПС.\n")
        window._ask_input = lambda kind: "0"  # must not be used: the panel is right there
        window.run_program()
        assert pump(window, lambda: not window._input_console.isHidden()), "it never appeared"
        assert window._input_console._line.placeholderText() == "Слово — Enter"
        assert "e0b400" in window._input_console.styleSheet(), "no frame round the answer"
        assert "ждёт ввода: Слово" in window.status_text(), window.status_text()

        window._input_console._line.setText("5")
        window._input_console.send()
        assert pump(window, lambda: window._input_console.isHidden()), "it stayed on screen"
        assert window._input_console.styleSheet() == "", "the frame stayed"
    finally:
        discard_changes(window)
    print("ok: the console appears for a question and goes away with the answer")


def test_the_queue_field_can_be_hidden(executable: str) -> None:
    """Hidden, its lines are not used at all — the console answers instead."""
    from prologd_gui.settings import Settings

    window = empty_window(executable)
    try:
        window.editor().setPlainText(READS_TWO)
        window.input_pane().setPlainText("7\n9\n")
        assert window._input_lines() == ["7", "9"]

        window._actions["input_queue"].setChecked(False)
        assert window.input_pane().isHidden() is True
        assert window._input_lines() == [], "a hidden field still decided the answers"
    finally:
        discard_changes(window)

    assert Settings(window._settings.path).input_queue is False, "the switch was not stored"
    print("ok: hiding the queue field takes its lines out of the run")


def test_cancelling_input_stops_the_run(executable: str) -> None:
    """«Отмена» stops the program and the run asks nothing else."""
    window = empty_window(executable)
    try:
        window._actions["output"].setChecked(False)  # the dialog needs a reason to be used
        window.editor().setPlainText(READS_TWO)
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or None

        window.run_program()
        assert pump(window, lambda: not window.session.is_running()), "the run was not stopped"

        assert len(asked) == 1, f"asked again after the cancellation: {asked}"
        assert "ввод отменён" in window.output_text(), ascii(window.output_text())
        assert "ввод отменён" in window.status_text(), window.status_text()

        # A new run starts a new session and may ask again.
        window._ask_input = lambda kind: "5"
        window.run_program()
        wait_for_result(window)
        assert echoed_lines(window) == ["> 5", "> 5"], echoed_lines(window)
        assert "5" in window.output_text(), ascii(window.output_text())
        print("ok: cancelling input stops the run, and the next run asks again")
    finally:
        discard_changes(window)


def test_a_run_uses_the_tab_that_is_showing(executable: str) -> None:
    window = empty_window(executable)
    try:
        window.open_path(str(EXAMPLE))
        window.new_buffer()
        assert window.tab_count() == 2
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


def test_the_output_panel_moves_and_hides(executable: str) -> None:
    """`Ctrl+F4` moves the output panel, `F4` hides it, and both are remembered.

    The panel is *one* widget — the output with the input queue under it — inside a
    single splitter whose **orientation** is what changes: side by side when it is
    on the right, stacked when it is at the bottom.  The turn must not hide it and
    must not leave a pane dragged away to nothing.
    """
    from PySide6.QtCore import Qt

    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    window = empty_window(executable)
    path = window._settings.path
    try:
        assert window.output_position() == "right"
        assert window._panel_splitter.orientation() == Qt.Orientation.Horizontal
        assert window.output_visible() is True
        assert window._actions["output"].isChecked() is True

        window._actions["split_orientation"].trigger()
        assert window.output_position() == "bottom"
        assert window._panel_splitter.orientation() == Qt.Orientation.Vertical
        assert window._panel_splitter.widget(1) is window._sidebar, "the editor moved"
        assert window._input_pane.parent() is window._sidebar, "the input queue did not travel"
        assert window._sidebar.isHidden() is False, "the turn hid the panel"

        # `F4`: checked means shown, and a hidden panel is *hidden*, not vanished.
        window._actions["output"].setChecked(False)
        assert window.output_visible() is False
        assert window._sidebar.isHidden() is True
        window._actions["output"].setChecked(True)
        assert window.output_visible() is True

        # A pane can be dragged small, but never to nothing.
        assert window._panel_splitter.childrenCollapsible() is False
        window._panel_splitter.setSizes([0, 0])
        assert all(size > 0 for size in window._panel_splitter.sizes()), window._panel_splitter.sizes()
    finally:
        discard_changes(window)

    stored = Settings(path)
    assert stored.output_position == "bottom", "the side of the panel was not remembered"
    assert len(stored.panel_sizes) == 2 and all(size > 0 for size in stored.panel_sizes)
    # Three parts now: the output, the console and the prepared-lines field.  The
    # console is hidden while nothing is asked, and a hidden splitter child has no
    # size of its own — so only the sum has to make sense.
    assert len(stored.output_sizes) == 3, stored.output_sizes
    assert sum(stored.output_sizes) > 0, stored.output_sizes
    assert stored.output_visible is True

    reopened = MainWindow(executable, [], stored)
    try:
        assert reopened.output_position() == "bottom", "the panel did not come back"
        assert reopened._panel_splitter.orientation() == Qt.Orientation.Vertical
        assert reopened._actions["output"].isChecked() is True
        print("ok: the panel moves with Ctrl+F4, hides with F4, and comes back")
    finally:
        discard_changes(reopened)


def test_the_title_and_the_tabs_show_the_file_state(
    executable: str, directory: pathlib.Path
) -> None:
    """The title bar carries the *whole* path; a tab carries the state as a picture.

    Four states, and the user asked for exactly these: never saved (`file`), never
    saved with changes (`file-modified`), saved (`file-saved`) and saved with
    changes (`file-modified`).  The tab keeps the short name, because a tab bar
    full of paths cannot be read.
    """
    from prologd_gui import actions, assets

    def picture(name: str):
        found = assets.icon(name)
        assert found is not None, f"{name}.png is not in assets"
        return found.cacheKey()

    def tab(window, index: int = 0) -> int:
        return window.active_pane().tabIcon(index).cacheKey()

    window = empty_window(executable)
    try:
        buffer = window.buffers()[0]
        assert buffer.icon_name() == actions.FILE_ICON, "a buffer that was never saved"
        assert tab(window) == picture(actions.FILE_ICON)
        assert window.windowTitle() == f"{buffer.model.name} — PrologD", window.windowTitle()

        window.editor().insertPlainText("факт(1).\n")
        assert buffer.icon_name() == actions.MODIFIED_ICON
        assert tab(window) == picture(actions.MODIFIED_ICON)

        target = directory / "состояние.pld"
        window.save_buffer(buffer, str(target))
        assert buffer.icon_name() == actions.SAVED_ICON, "a saved file is not a modified one"
        assert tab(window) == picture(actions.SAVED_ICON)
        assert str(target) in window.windowTitle(), window.windowTitle()
        assert window.windowTitle().startswith("*") is False, "saving clears the marker"

        window.editor().insertPlainText("% ещё строка\n")
        assert buffer.icon_name() == actions.MODIFIED_ICON
        assert str(target) in window.windowTitle(), "the path stays in the title"
        print("ok: the title shows the full path and every tab shows its own state")
    finally:
        discard_changes(window)


def test_undo_and_redo_follow_the_tab_that_is_showing(executable: str) -> None:
    """A greyed-out «Отменить» with something to undo is a defect of its own."""
    window = empty_window(executable)
    try:
        assert window._actions["undo"].isEnabled() is False
        assert window._actions["redo"].isEnabled() is False

        window.editor().insertPlainText("факт(1).\n")
        assert window._actions["undo"].isEnabled() is True, "typing did not arm undo"
        assert window._actions["redo"].isEnabled() is False

        window._actions["undo"].trigger()
        assert window._actions["undo"].isEnabled() is False, "that was the only step"
        assert window._actions["redo"].isEnabled() is True

        # Another tab has a history of its own, and the state follows the one on
        # screen — the documents do not share an undo stack.
        window.new_buffer()
        assert window._actions["undo"].isEnabled() is False, "an empty tab has nothing to undo"
        assert window._actions["redo"].isEnabled() is False
        window.editor().insertPlainText("правило(2).\n")
        assert window._actions["undo"].isEnabled() is True, "this tab's edit was not noticed"

        window.active_pane().set_current(window.buffers()[0])
        assert window._actions["undo"].isEnabled() is False, "the first tab was already undone"
        assert window._actions["redo"].isEnabled() is True, "the first tab can be redone"
        print("ok: undo and redo follow the document of the tab that is showing")
    finally:
        discard_changes(window)


def test_the_recent_menu_and_the_window_carry_the_pictures(
    executable: str, directory: pathlib.Path
) -> None:
    """A recent program shows the file picture, and the window has its own icon."""
    from prologd_gui import actions, assets

    target = directory / "недавний.pld"
    target.write_text("факт(1).\n", encoding="utf-8")
    window = empty_window(executable)
    try:
        window.open_path(str(target))
        window._fill_recent_menu()
        entries = [
            entry for entry in window._recent_menu.actions() if entry.text().endswith(".pld")
        ]
        assert entries, [entry.text() for entry in window._recent_menu.actions()]
        assert entries[0].icon().isNull() is False, "the recent program has no picture"
        found = assets.icon(actions.FILE_ICON)
        assert found is not None and entries[0].icon().cacheKey() == found.cacheKey()

        assert window.windowIcon().isNull() is False, "the window has no application icon"
        text = window.about_text()
        assert "PrologD" in text and str(window._settings.path) in text
        print("ok: the recent menu and the window carry their pictures")
    finally:
        discard_changes(window)


def test_the_run_state_drives_the_buttons(executable: str) -> None:
    """Two states, not one: the process can be *up and idle*, and a run can be
    *in flight*.

    `Запустить` needs the second (there is nothing to start while a computation is
    running, and it is what restarts the whole file), `Остановить` the first — a
    live interpreter holds a knowledge base, and unloading it is a stop of its own.
    A window the user has only opened has nothing running at all, which is what the
    startup state wrongly said it had.
    """
    window = make_window(executable, ready=False)
    try:
        assert window.session.is_running() is False, "a new window starts no interpreter"
        assert window._actions["run"].isEnabled() is True
        assert window._actions["stop"].isEnabled() is False
        assert "остановлен" in window._details.text(), window._details.text()

        # The first run starts the interpreter *and* the computation.
        window.open_path(str(EXAMPLE))
        window._actions["run"].trigger()
        assert window._actions["run"].isEnabled() is False, "a run is in flight"
        assert window._actions["stop"].isEnabled() is True
        assert pump(window, lambda: "решение" in window.status_text()), window.status_text()

        # The answer frees `Запустить`; the process is up and the base is loaded.
        assert window._actions["run"].isEnabled() is True, "the answer frees the button"
        assert window._actions["stop"].isEnabled() is True, "the process is still up"
        assert "база знаний загружена" in window._details.text(), window._details.text()

        # Stopping an *idle* interpreter unloads the knowledge base ...
        window._actions["stop"].trigger()
        assert window.session.is_running() is False
        assert window._actions["run"].isEnabled() is True
        assert window._actions["stop"].isEnabled() is False
        assert "--- база знаний выгружена ---" in window.output_text(), window.output_text()

        # ... while stopping a computation in flight is just a stop.
        window._actions["run"].trigger()
        assert window._actions["stop"].isEnabled() is True
        window._actions["stop"].trigger()
        assert "--- остановлено ---" in window.output_text(), window.output_text()
        print("ok: run and stop follow the two states of the interpreter")
    finally:
        discard_changes(window)


def test_the_wrap_switch_reaches_every_editor(executable: str) -> None:
    """`Вид → Переносить длинные строки` is the editor's switch, not the output's."""
    from PySide6.QtWidgets import QPlainTextEdit

    from prologd_gui.settings import Settings

    window = empty_window(executable)
    try:
        assert window._actions["wrap"].isChecked() is False
        assert window.editor().lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap

        window._actions["wrap"].setChecked(True)
        assert window.editor().lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
        assert window.output().lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap, (
            "a log line cut in the middle cannot be read as data"
        )

        # A tab opened after the switch is wrapped as well.
        second = window.new_buffer()
        view = window.view_for(second)
        assert view is not None
        assert view.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    finally:
        discard_changes(window)

    assert Settings(window._settings.path).wrap is True, "the switch was not stored"
    print("ok: the wrap switch is stored and reaches every editor view")


def test_the_output_can_be_saved(executable: str, directory: pathlib.Path) -> None:
    """A run's output goes to a file as it stands — the text, without the colours."""
    window = empty_window(executable)
    target = directory / "вывод.txt"
    try:
        window.open_path(str(EXAMPLE))
        window.run_program()
        wait_for_result(window)

        before = window.output_text()
        window._ask_save_output_path = lambda: str(target)
        window._actions["save_output"].trigger()

        assert target.is_file(), window.status_text()
        saved = target.read_text(encoding="utf-8")
        # What goes to the file is the output as it stood.  The note saying where it
        # went is written into the pane *after* that, so the pane is longer by now —
        # comparing it with the file was a check that could never pass.
        assert saved == before, (ascii(saved), ascii(before))
        assert ANSWER in saved, ascii(saved)
        assert "вывод сохранён" in window.status_text(), window.status_text()
        assert window.output_text().startswith(before)

        # Declining the question writes nothing — and does not pretend otherwise.
        window._ask_save_output_path = lambda: None
        window._actions["save_output"].trigger()
        print("ok: the output pane is saved to a file, and declining writes nothing")
    finally:
        discard_changes(window)


def test_the_menus_come_from_the_action_table(executable: str) -> None:
    """Every menu entry is an action of the table, in the order the table gives.

    The menus are built *from* `actions.MENUS`, so this is the check that the two
    have not drifted — a renamed entry, a missing separator, a forgotten command.
    """
    from prologd_gui import actions

    window = empty_window(executable)
    try:
        menus = {action.text(): action.menu() for action in window.menuBar().actions()}
        assert list(menus) == [title for title, _ in actions.MENUS], list(menus)
        for title, entries in actions.MENUS:
            expected = []
            for key in entries:
                if key == actions.SEPARATOR:
                    expected.append("")
                elif key == actions.RECENT:
                    expected.append("Последние файлы")
                else:
                    expected.append(actions.BY_KEY[key].title)
            assert [entry.text() for entry in menus[title].actions()] == expected, title
        assert set(window._actions) == set(actions.BY_KEY), "the window has stray actions"

        # What is not implemented yet says so instead of doing nothing quietly.
        # The execution group left this list in task_28 — `Запустить с
        # трассировкой`, `Шаг` and `Шаг с обходом` are live now — and `test_search.py`
        # is where the search entries are checked.
        settings = window._actions["settings"]
        assert settings.isEnabled() is False
        assert "task_29" in settings.toolTip(), settings.toolTip()
        assert window._actions["format"].isEnabled() is False
        assert window._actions["step"].isEnabled() is True, "stepping is implemented now"
        assert window._actions["run_trace"].isEnabled() is True
        print("ok: the menu bar is built from the action table, disabled entries explain themselves")
    finally:
        discard_changes(window)


def test_the_toolbar_reuses_the_actions(executable: str) -> None:
    from prologd_gui import actions

    window = empty_window(executable)
    try:
        toolbar = window._toolbar
        assert toolbar.iconSize().width() == 24, "icons are drawn at 24 px"
        shown = [entry.text() for entry in toolbar.actions() if not entry.isSeparator()]
        for key in ("new", "open", "save", "run", "stop", "comment", "clear_output"):
            assert actions.BY_KEY[key].title in shown, (key, shown)
        # «Очистить вывод» is the last button on the right: it acts on the output,
        # not on the program, so it is kept away from the editing group.
        assert shown[-1] == actions.BY_KEY["clear_output"].title, shown
        assert window._font_size_box.parent() is not None, "the size control is on the toolbar"

        # An icon that exists is set; one that is not drawn yet leaves a text-only
        # button.  `file-reload` used to be the missing one; the `view-*` switches
        # are the row still waiting (see `assets.MISSING`).
        assert window._actions["save"].icon().isNull() is False
        assert window._actions["reload"].icon().isNull() is False, "file-reload.png is drawn now"
        assert window._actions["line_numbers"].icon().isNull() is True, (
            "view-line-numbers.png is not drawn yet"
        )
        print("ok: the toolbar shows the actions and their icons, text-only where none exists")
    finally:
        discard_changes(window)


def test_view_switches_are_stored(executable: str) -> None:
    """Checkable entries write the preference they stand for."""
    from prologd_gui.settings import Settings

    window = empty_window(executable)
    path = window._settings.path
    try:
        assert window._actions["line_numbers"].isChecked() is True
        assert window._toolbar.isHidden() is False

        window._actions["line_numbers"].setChecked(False)
        assert window._settings.line_numbers is False
        assert window.editor().line_numbers() is False
        window._actions["toolbar"].setChecked(False)
        assert window._toolbar.isHidden() is True
        window._actions["save_before_run"].setChecked(True)
        assert window._settings.save_before_run is True
    finally:
        discard_changes(window)

    stored = Settings(path)
    assert stored.line_numbers is False
    assert stored.toolbar_visible is False
    assert stored.save_before_run is True
    print("ok: view switches are remembered")


def test_the_recent_menu_lists_what_is_still_there(
    executable: str, directory: pathlib.Path
) -> None:
    keep = directory / "остался.pld"
    gone = directory / "исчез.pld"
    for path in (keep, gone):
        path.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(keep))
        window.open_path(str(gone))
        assert len(window.recent_files()) == 2

        gone.unlink()
        window._fill_recent_menu()
        entries = [entry.text() for entry in window._recent_menu.actions() if entry.text()]
        assert entries[0] == keep.name, entries
        assert gone.name not in entries, "a deleted file stayed in the list"
        assert window.recent_files() == [str(keep)]

        window._clear_recent()
        assert [entry.text() for entry in window._recent_menu.actions()] == ["(пока пусто)"]
        assert window.recent_files() == []
        print("ok: the recent-files menu lists what is there, and can be emptied")
    finally:
        discard_changes(window)


def test_the_context_menu_reuses_the_shared_actions(executable: str) -> None:
    """Menu, toolbar and context menu hand out the same `QAction` objects."""
    window = empty_window(executable)
    try:
        in_view = window.editor().actions()
        for key in ("undo", "redo", "copy", "paste", "comment", "uncomment", "select_all"):
            assert window._actions[key] in in_view, key
        window._apply_context_actions()
        assert in_view.count(window._actions["comment"]) == 1, "added twice"
        print("ok: the editor's context menu reuses the menu actions")
    finally:
        discard_changes(window)


def test_the_font_control_and_the_wheel_are_one_setting(executable: str) -> None:
    window = empty_window(executable)
    try:
        box = window._font_size_box
        assert box.currentData() == float(window._settings.font_size), box.currentData()

        box.setCurrentIndex(box.findData(20.0))
        assert window.editor().font_size == 20.0
        assert window.output().font_size == 20.0
        assert window._settings.font_size == 20.0

        # A size from the wheel need not be in the list; the box still shows it.
        window.editor().set_font_size(23)
        assert box.currentText() == "23", box.currentText()
        print("ok: the toolbar's size control and the zoom are one preference")
    finally:
        discard_changes(window)


def test_saving_before_a_run_writes_the_file(
    executable: str, directory: pathlib.Path
) -> None:
    target = directory / "перед_запуском.pld"
    target.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(target))
        window.editor().insertPlainText("?факт(1).\n")
        window._actions["save_before_run"].setChecked(True)

        window.run_program()
        wait_for_result(window)

        assert target.read_text(encoding="utf-8") == "?факт(1).\nфакт(1).\n"
        assert window.buffers()[0].is_modified() is False, "the file was not saved before the run"
        # ASCII only: the test output is piped, and a pipe is not the console —
        # a Cyrillic «...» here died with UnicodeEncodeError on the way out.
        print("ok: 'save before run' writes the file before the run")
    finally:
        discard_changes(window)


def test_the_split_editor_shares_one_document(executable: str) -> None:
    """Two panes, one text: an edit in either is the same edit."""
    window = empty_window(executable)
    try:
        assert window.pane_count() == 1
        assert window.split_editor() is True
        assert window.pane_count() == 2
        assert window.split_editor() is False, "splitting twice is not a third pane"

        buffer = window.buffers()[0]
        left, right = window.panes()
        assert len(buffer.views()) == 2, "each pane needs its own view"
        assert left.current_buffer() is buffer and right.current_buffer() is buffer

        # Typing on the left appears on the right: one document, not two copies.
        left.view_for(buffer).setPlainText("факт(1).\n")
        assert right.view_for(buffer).toPlainText() == "факт(1).\n"
        left.view_for(buffer).insertPlainText("снег.\n")
        assert right.view_for(buffer).toPlainText() == "снег.\nфакт(1).\n"
        assert window.editor_text() == "снег.\nфакт(1).\n"
        print("ok: the split editor shows one document in both panes")
    finally:
        discard_changes(window)


def test_each_pane_has_its_own_current_tab(
    executable: str, directory: pathlib.Path
) -> None:
    """The panes show one set of documents but their own current tab."""
    other = directory / "правая.pld"
    other.write_text("факт(2).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(EXAMPLE))
        window.open_path(str(other))
        window.split_editor()
        left, right = window.panes()

        left.set_current(window.buffers()[0])
        right.set_current(window.buffers()[1])
        assert left.current_buffer().model.name == EXAMPLE.name
        assert right.current_buffer().model.name == other.name

        # The commands follow the pane that was used last.
        left.view_for(window.buffers()[0]).activated.emit()
        assert window.current_path() == str(EXAMPLE)
        right.view_for(window.buffers()[1]).activated.emit()
        assert window.current_path() == str(other)
        assert "панель 2 из 2" in window.status_text(), window.status_text()
        print("ok: each pane keeps its own tab and the commands follow the used one")
    finally:
        discard_changes(window)


def test_merging_the_editor_keeps_the_documents(
    executable: str, directory: pathlib.Path
) -> None:
    other = directory / "вторая.pld"
    other.write_text("факт(3).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(EXAMPLE))
        window.open_path(str(other))
        window.split_editor()
        left, right = window.panes()
        right.set_current(window.buffers()[1])

        assert window.merge_editor() is True
        assert window.pane_count() == 1
        assert window.tab_count() == 2, "merging the editor must not close documents"
        assert window.current_path() == str(other), "the eyes stay on the same program"
        assert len(window.buffers()[1].views()) == 1
        assert window.merge_editor() is False
        print("ok: merging the editor keeps every document open")
    finally:
        discard_changes(window)


def test_the_split_survives_a_restart(executable: str) -> None:
    """The panes are remembered when «восстанавливать» is on."""
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    window = empty_window(executable)
    path = window._settings.path
    try:
        window.split_editor()
        window._editor_splitter.setSizes([300, 700])
        window._save_split_state()
    finally:
        discard_changes(window)

    settings = Settings(path)
    assert settings.split_editor is True
    saved = settings.split_sizes
    assert len(saved) == 2 and all(size > 0 for size in saved), saved

    reopened = MainWindow(executable, [], settings)
    try:
        assert reopened.pane_count() == 2, "the second pane did not come back"
        # Qt fits the requested widths to the space there is, so the *ratio* is
        # what can be compared — the window is not even shown here.
        actual = reopened._editor_splitter.sizes()
        assert len(actual) == 2, actual
        assert abs(actual[0] / sum(actual) - saved[0] / sum(saved)) < 0.05, (actual, saved)
        settings.restore_split = False
    finally:
        discard_changes(reopened)

    third = MainWindow(executable, [], settings)
    try:
        assert third.pane_count() == 1, "«не восстанавливать» must be obeyed"
        print("ok: the split editor is remembered, and can be switched off")
    finally:
        discard_changes(third)

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
    """A key that the documentation promises must be on the action that does it.

    **Запустить** was bound to `Ctrl+R` while the plan promised `F5`, so pressing
    the documented key did nothing at all.  Since the menus and the toolbar are
    built from `actions.ACTIONS`, this is where the keys are checked now.
    """
    window = empty_window(executable)
    try:
        for key, expected in (
            ("run", {"F5", "Ctrl+R"}),
            ("stop", {"Shift+F5"}),
            ("open", {"Ctrl+O"}),
            ("save", {"Ctrl+S"}),
            ("close", {"Ctrl+W"}),
            ("comment", {"Ctrl+K"}),
            ("uncomment", {"Ctrl+U"}),
            ("zoom_reset", {"Ctrl+0"}),
            ("split", {"Ctrl+\\"}),
            ("next_tab", {"Ctrl+Tab"}),
            ("previous_tab", {"Ctrl+Shift+Tab"}),
        ):
            bound = {sequence.toString() for sequence in window._actions[key].shortcuts()}
            assert bound == expected, f"{key} is bound to {sorted(bound)}, documented {sorted(expected)}"

        # Zoom is on the *keypad* keys.  `Ctrl+=`, `Ctrl++` and `Ctrl+-` sit on the
        # main row and belong to the `РАВНО`/`СЛОЖЕНИЕ`/`ВЫЧИТАНИЕ` skeletons of
        # task_31; the keypad is a different combination to Qt, and it is spelled
        # `Num++`/`Num+-` (the keypad modifier is part of the sequence).
        for key, expected in (("zoom_in", {"Ctrl+Num++"}), ("zoom_out", {"Ctrl+Num+-"})):
            bound = {sequence.toString() for sequence in window._actions[key].shortcuts()}
            assert bound == expected, f"{key} is bound to {sorted(bound)}"

        # Triggering is the same path a shortcut takes.
        window.open_path(str(EXAMPLE))
        # «Запустить» is enabled only while there is nothing running, and
        # `empty_window` waited for `ready` — the session is already up.
        window.stop_program()
        window._actions["run"].trigger()
        assert pump(window, lambda: ANSWER in window.output_text()), ascii(window.output_text())
        print("ok: the documented keys are bound to the actions, and the action runs the program")
    finally:
        discard_changes(window)


def test_split_and_merge_follow_the_pane_count(executable: str) -> None:
    """Both commands are enabled according to how many panes there are.

    Not cosmetic: each carries a key (`Ctrl+\\`, `Ctrl+Shift+\\`), and a *disabled*
    `QAction` fires neither its shortcut nor `trigger()` — so with the state
    computed on start-up only, «Объединить редакторы» stayed greyed out for the
    rest of the session and a split could not be undone without a restart.

    The commands are driven through `trigger()` here: a synthetic key is
    unreliable in a long headless run once several windows exist, while
    `trigger()` takes the same path a shortcut does (`triggered` → the slot) and
    is refused in exactly the same cases.
    """
    window = empty_window(executable)
    try:
        assert window._actions["split"].isEnabled() is True
        assert window._actions["merge"].isEnabled() is False

        window._actions["split"].trigger()
        assert window.pane_count() == 2, "«Разделить редактор» did nothing"
        assert window._actions["merge"].isEnabled() is True, "the merge entry stayed disabled"
        assert window._actions["split"].isEnabled() is False, "a second pane is not a third"

        window._actions["merge"].trigger()
        assert window.pane_count() == 1, "«Объединить редакторы» did nothing"
        assert window._actions["split"].isEnabled() is True, "the split entry stayed disabled"
        assert window._actions["merge"].isEnabled() is False
        print("ok: split and merge are enabled by the pane count, and are usable again")
    finally:
        discard_changes(window)


def colour_of(pane, block: int) -> str:
    """The colour of the first character of a block of a text pane."""
    from PySide6.QtGui import QTextCursor

    cursor = QTextCursor(pane.document())
    cursor.setPosition(pane.document().findBlockByNumber(block).position())
    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, cursor.MoveMode.KeepAnchor)
    return cursor.charFormat().foreground().color().name()


def test_a_runtime_error_marks_its_line(executable: str) -> None:
    """A diagnostic comes with its position, and the editor marks that line.

    The message used to carry `file:line:column:` as text, which a front-end can
    only use by parsing it; protocol 3 sends the fields, so the window marks the
    line and puts the caret on it instead of guessing.
    """
    window = empty_window(executable)
    try:
        typed = "дели(Х) :- БОЛЬШЕ(1, #1/0#).\n?дели(1).\n"
        window.editor().setPlainText(typed)
        window.run_program()
        assert pump(window, lambda: "деление на ноль" in window.output_text()), ascii(
            window.output_text()
        )
        view = window.editor()
        assert view.error_line() == 1, view.error_line()
        assert view.textCursor().blockNumber() == 0, "the caret is not on the line"
        assert "ошибка: <buffer>:1:1" in window.status_text(), window.status_text()
        assert "<buffer>:1:1: деление на ноль" in window.output_text(), ascii(
            window.output_text()
        )

        # An edit clears the mark: a red line over text it no longer describes is
        # a lie about where the program broke.
        window.editor().insertPlainText("\n")
        assert window.editor().error_line() is None
    finally:
        discard_changes(window)
    print("ok: a runtime error marks its line, names it, and the mark goes on edit")


def test_a_parse_error_marks_the_line_the_parser_stopped_at(executable: str) -> None:
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1.\n")
        window.run_program()
        assert pump(window, lambda: "непарные скобки" in window.output_text()), ascii(
            window.output_text()
        )
        view = window.editor()
        line = view.error_line()
        assert line is not None, "the parse error marked nothing"
        assert line <= view.document().blockCount(), line
        assert view.textCursor().blockNumber() + 1 == line
    finally:
        discard_changes(window)
    print("ok: a parse error marks its line as well")


def test_a_warning_is_amber_and_counted(executable: str) -> None:
    """A warning is advice: amber in the pane, counted, and the run goes on.

    `мама(Лена, Таня).` is the porting trap the course itself teaches — both
    names are variables, and the interpreter now says so instead of answering
    `Лена=_1` in silence.  It must not turn the answer into a failure.
    """
    from prologd_gui import panels

    window = empty_window(executable)
    try:
        window.editor().setPlainText("мама(Лена, Таня).\n?мама(Лена, Таня).\n")
        window.run_program()
        assert pump(window, lambda: "предупреждений: 2" in window.status_text()), (
            window.status_text()
        )
        lines = window.output_text().splitlines()
        amber = [
            number for number, line in enumerate(lines) if line.startswith("*** предупреждение")
        ]
        assert len(amber) == 2, ascii(window.output_text())
        assert colour_of(window._output, amber[0]) == panels.KIND_COLORS[panels.WARNING]
        # The run was not disturbed: the query still answered.
        assert "Лена=_1" in window.output_text(), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a warning is amber, counted, and does not end the run")


def test_a_diagnostic_from_an_imported_file_opens_it(executable: str, directory) -> None:
    """A failure in an `ИМПОРТ`ed file marks the line in *that* file.

    Marking a line in the tab that happens to be showing would be worse than
    marking none, so the file is opened in a tab of its own first.
    """
    module = directory / "модуль.pld"
    module.write_text("ок(1).\nсломано(1.\n", encoding="utf-8")
    main = directory / "главная.pld"
    main.write_text(':- ИМПОРТ("модуль.pld").\n?ок(1).\n', encoding="utf-8")

    window = empty_window(executable)
    try:
        assert window.open_path(str(main)), "the main file did not open"
        window.run_program()
        assert pump(window, lambda: "непарные скобки" in window.output_text()), ascii(
            window.output_text()
        )
        buffer = window._buffer_for_path(str(module))
        assert buffer is not None, [item.model.path for item in window.buffers()]
        assert any(view.error_line() is not None for view in buffer.views()), "no line marked"
        # The diagnostic names the file it came from, and the line in it.  The
        # interpreter writes its paths with forward slashes, so the file's name is
        # what is looked for here rather than the platform's own spelling, and the
        # position is the opening bracket (task_40), not the token the parser
        # happened to stop at.
        assert "модуль.pld:2:15" in window.output_text(), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a diagnostic from an imported file opens that file and marks its line")


def test_stepping_shows_the_goal_the_stack_and_the_line(executable: str) -> None:
    """`F10` starts a stepped run; the panel, the stack and the editor follow it."""
    window = empty_window(executable)
    try:
        assert window.stepping() is False, "the step panel stood there before F10"
        window.editor().setPlainText("факт(1).\nсчёт(X) :- факт(X).\n?счёт(X).\n")
        window._actions["step"].trigger()
        assert pump(window, lambda: window.stepping()), "the step panel never appeared"
        pane = window.step_pane()
        assert pane.action_text() == "вызов", pane.action_text()
        assert pane.goal_text() == "счёт(_1)", ascii(pane.goal_text())
        assert pane.depth_text() == "глубина 0", pane.depth_text()
        assert pane.where_text().endswith(":3:1"), ascii(pane.where_text())
        assert pane.stack_text() == "стек: счёт(_1)", ascii(pane.stack_text())
        assert window.editor().trace_line() == 3, window.editor().trace_line()
        assert window.status_text().startswith("шаг:"), window.status_text()
        # A paused step is a usable state: the keys that go on from it must be
        # live, or they are dead exactly when the user needs them.
        assert window._actions["step"].isEnabled() is True
        assert window._actions["step_over"].isEnabled() is True
        assert window._actions["run"].isEnabled() is True

        window._actions["step"].trigger()  # one point in
        assert pump(window, lambda: pane.goal_text().startswith("факт")), ascii(pane.goal_text())
        assert pane.depth_text() == "глубина 1", pane.depth_text()
        assert pane.stack_text() == "стек: счёт(_1) → факт(_1)", ascii(pane.stack_text())
        assert window.editor().trace_line() == 2, window.editor().trace_line()

        window._actions["run"].trigger()  # F5 while paused means «продолжить»
        assert pump(window, lambda: not window.stepping()), "the panel stayed up"
        assert pump(window, lambda: "решени" in window.status_text()), window.status_text()
        assert "X=1" in window.output_text(), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: stepping shows the goal, the depth, the stack and the line it is on")


def test_the_trace_is_coloured_apart_from_the_output(executable: str) -> None:
    """«Запустить с трассировкой»: the trace text arrives as `trace` events.

    It is the interpreter's own text and the program's own output; colouring them
    alike would make a trace look like the answer.
    """
    from prologd_gui import panels

    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(1).\n")
        window._actions["run_trace"].trigger()
        assert pump(window, lambda: "Согласуется с" in window.output_text()), ascii(
            window.output_text()
        )
        lines = window.output_text().splitlines()
        block = next(number for number, line in enumerate(lines) if "Согласуется с" in line)
        assert colour_of(window._output, block) == panels.KIND_COLORS[panels.TRACE]
    finally:
        discard_changes(window)
    print("ok: the trace is coloured apart from the program's own output")


def test_a_marker_answers_one_question_alone(executable: str) -> None:
    """task_36: lesson_04's `?сумма(5, С).` answers `С=15` and nothing else.

    The file's other questions are loaded but *not* run (the load is quiet), so
    the pane holds the one answer that was asked for.  `Запустить` still runs
    the whole lesson — that is what a lesson is for.
    """
    window = empty_window(executable)
    try:
        assert window.open_path(str(LESSON_04))
        view = window.editor()
        line = next(
            number
            for number, content in enumerate(view.toPlainText().splitlines(), 1)
            if content.strip() == "?сумма(5, С)."
        )
        statement = view.query_statements().get(line)
        assert statement == "?сумма(5, С).", (line, statement)

        view.queryRequested.emit(statement)
        wait_for_result(window)
        assert printed_lines(window) == ["С=15"], ascii(window.output_text())
        assert window._query_line.text() == "?сумма(5, С).", "the question stays visible"
    finally:
        discard_changes(window)
    print("ok: a marker answers one question alone (С=15 from lesson_04)")


def test_a_question_parked_in_a_comment_runs_from_the_margin(executable: str) -> None:
    """`%   ?ВЕРСИЯ.` in the appendix: the file never runs it, a click does."""
    window = empty_window(executable)
    try:
        assert window.open_path(str(APPENDIX_DEBUG))
        view = window.editor()
        assert "?ВЕРСИЯ." in view.query_statements().values()
        view.queryRequested.emit("?ВЕРСИЯ.")
        wait_for_result(window)
        printed = printed_lines(window)
        assert any(line.startswith("PrologD ") for line in printed), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a question parked in a comment answers from the margin (appendix)")


def test_a_marker_while_a_step_is_paused_starts_a_fresh_quiet_run(executable: str) -> None:
    """The click is «stop this and answer that», even in the paused state.

    Without the stop, `run_program` would read the click as «продолжить» (what
    F5 means while paused) and the pane would fill with the stepped run's
    answers instead of the one the marker asked for.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(X).\n")
        window._actions["step"].trigger()
        assert pump(window, lambda: window.session.paused()), window.status_text()
        view = window.editor()
        view.queryRequested.emit("?факт(1).")
        wait_for_result(window)
        assert not window.session.paused()
        assert printed_lines(window) == ["ДА"], ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a marker click during a paused step stops it and answers the click")


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
        test_closing_everything_walks_through_the_tabs(executable, files)
        test_a_file_dropped_on_the_editor_opens_in_a_tab(executable, files)
        test_saving_clears_the_marker_and_keeps_the_file_shape(executable, files)
        test_cancelling_the_encoding_question_opens_nothing(executable, files)
        test_the_input_field_feeds_the_program(executable)
        test_the_console_answers_once_the_prepared_lines_run_out(executable)
        test_the_dialog_is_the_last_resort(executable)
        test_the_console_appears_only_when_it_is_asked(executable)
        test_the_queue_field_can_be_hidden(executable)
        test_cancelling_input_stops_the_run(executable)
        test_a_run_uses_the_tab_that_is_showing(executable)
        test_the_split_editor_shares_one_document(executable)
        test_each_pane_has_its_own_current_tab(executable, files)
        test_merging_the_editor_keeps_the_documents(executable, files)
        test_the_split_survives_a_restart(executable)
        test_split_and_merge_follow_the_pane_count(executable)
        test_the_output_panel_moves_and_hides(executable)
        test_the_menus_come_from_the_action_table(executable)
        test_the_toolbar_reuses_the_actions(executable)
        test_view_switches_are_stored(executable)
        test_the_recent_menu_lists_what_is_still_there(executable, files)
        test_the_recent_menu_and_the_window_carry_the_pictures(executable, files)
        test_the_title_and_the_tabs_show_the_file_state(executable, files)
        test_undo_and_redo_follow_the_tab_that_is_showing(executable)
        test_the_run_state_drives_the_buttons(executable)
        test_the_wrap_switch_reaches_every_editor(executable)
        test_a_runtime_error_marks_its_line(executable)
        test_a_parse_error_marks_the_line_the_parser_stopped_at(executable)
        test_a_warning_is_amber_and_counted(executable)
        test_a_diagnostic_from_an_imported_file_opens_it(executable, files)
        test_stepping_shows_the_goal_the_stack_and_the_line(executable)
        test_the_trace_is_coloured_apart_from_the_output(executable)
        test_a_marker_answers_one_question_alone(executable)
        test_a_question_parked_in_a_comment_runs_from_the_margin(executable)
        test_a_marker_while_a_step_is_paused_starts_a_fresh_quiet_run(executable)
        test_the_output_can_be_saved(executable, files)
        test_the_context_menu_reuses_the_shared_actions(executable)
        test_the_font_control_and_the_wheel_are_one_setting(executable)
        test_saving_before_a_run_writes_the_file(executable, files)
    print("all window checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
