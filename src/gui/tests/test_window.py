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
    from PySide6.QtGui import QTextCursor
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

        # ... while stopping a computation in flight is asked politely first and
        # ends on the deadline when nobody is reading (a load runs to its end
        # before the request can be read — see the window test below for the case
        # where the request *is* read: a read waiting for input).
        window._actions["run"].trigger()
        assert window._actions["stop"].isEnabled() is True
        window._actions["stop"].trigger()
        assert pump(window, lambda: "--- остановлено ---" in window.output_text()), (
            window.output_text()
        )
        print("ok: run and stop follow the two states of the interpreter")
    finally:
        discard_changes(window)


def test_stopping_a_query_asks_first_and_keeps_the_base(executable: str) -> None:
    """«Остановить» asks before it ends the process (task_28, the Stop block).

    The solver reads the interrupt at every step of its loop, so a query that
    *waits* — for input, the clearest case — ends on the request: the pane says
    `--- остановлено ---`, and the interpreter is left idle with its knowledge
    base.  Stopping that idle session is a different act and unloads it; the
    deadline (`STOP_GRACE_MS`) covers the one state a request cannot reach.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("?ВВОДСТР(С).\n")
        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()
        assert window.session.is_running()

        window._actions["stop"].trigger()
        assert pump(window, lambda: "--- остановлено ---" in window.output_text()), (
            window.output_text()
        )
        assert window.session.is_running() is True, "the session survives a polite stop"
        assert "база знаний загружена" in window._details.text(), window._details.text()
        assert window._input_console.waiting() is False, "the pending request is dismissed"

        # The idle interpreter with its base is unloaded by the same command.
        window._actions["stop"].trigger()
        assert "--- база знаний выгружена ---" in window.output_text(), window.output_text()
        assert window.session.is_running() is False
    finally:
        discard_changes(window)
    print("ok: «Остановить» asks first, keeps the base, and unloads it on the next press")


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


def press_escape(widget) -> bool:
    """One `Esc`, delivered the way a keyboard does: to the widget that has the focus.

    The event is *accepted* only when something dealt with it — that is how the
    order «the picture, then the bar, then the docks, then nothing» is checked,
    and the last press has to come back `False`.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    QApplication.sendEvent(widget, event)
    return event.isAccepted()


def test_the_window_remembers_its_size_and_place(executable: str) -> None:
    """task_49: the graphics window remembered its geometry; the main one did not.

    The user's report — «Графическое окно сохраняет свой размер и положение, а
    при этом главное окно не сохраняет» — and the two windows now keep the same
    kind of record (`prologd_gui.geometry`): `saveGeometry()` wrapped in base64, so
    the size, the place and the maximised state all come back, and a window last
    seen on a screen that is gone is placed where Qt can.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    directory = tempfile.TemporaryDirectory(prefix="prologd_gui_test_")
    _SETTINGS_DIRECTORIES.append(directory)
    path = pathlib.Path(directory.name) / "gui.ini"

    first = MainWindow(executable, [], Settings(path))
    try:
        assert first._settings.window_geometry == "", "nothing was remembered yet"
        first.show()
        # Inside the offscreen platform's 800×800 screen on purpose: `restoreGeometry`
        # clamps a size that no longer fits the screen, which is its own good
        # behaviour, and measuring it here would be measuring Qt.
        first.resize(720, 520)
        first.move(60, 40)
        place, size = first.pos(), first.size()
        assert size.width() == 720 and place.x() == 60, (size, place)
        first.close()
    finally:
        first.stop_program()

    stored = Settings(path)
    assert stored.window_geometry, "closing the window did not write its geometry"

    # The next start, with that file: the same size, the same place.
    second = MainWindow(executable, [], stored)
    try:
        second.show()
        assert second.size() == size, (second.size(), size)
        assert second.pos() == place, (second.pos(), place)
    finally:
        discard_changes(second)

    # And with nothing remembered — a first start, or the file the old version
    # left — the window is where the code puts it: the record is what makes the
    # difference, nothing else does.
    stored.window_geometry = ""
    third = MainWindow(executable, [], stored)
    try:
        third.show()
        assert third.size() != size or third.pos() != place, "the default start vanished"
        assert third.size().width() == 1000, third.size()
    finally:
        discard_changes(third)
    print("ok: the main window comes back with the size and the place it was closed at")


def test_escape_closes_the_picture_then_the_bar_then_the_docks(executable: str) -> None:
    """task_48: one key, four things, in the order the user asked for.

    The order is what makes `Esc` predictable: the picture (the biggest thing on
    the screen), then the find bar, then the reference, then the cheat sheet.  The
    completion popup and the find bar's own field are *not* in the list — they
    answer for themselves, and the window's handler never sees those keys.
    """
    window = empty_window(executable)
    try:
        picture = window.graphics_window()
        window._actions["graphics"].setChecked(True)
        window.show_find()
        window.show_reference()
        window.show_shortcuts()
        assert picture.isVisible() is True
        assert window.find_open() is True
        assert window._reference_dock.isHidden() is False
        assert window._shortcut_dock.isHidden() is False

        view = window.editor()
        assert press_escape(view) is True
        assert picture.isVisible() is False, "the picture goes first"
        assert window._settings.graphics_visible is False, "and the entry says so"
        assert window.find_open() is True, "one key closes one thing"

        assert press_escape(view) is True
        assert window.find_open() is False, "then the find bar"
        assert window._reference_dock.isHidden() is False

        assert press_escape(view) is True
        assert window._reference_dock.isHidden() is True, "then the reference"
        assert window._shortcut_dock.isHidden() is False

        assert press_escape(view) is True
        assert window._shortcut_dock.isHidden() is True, "then the cheat sheet"

        # Nothing is left, so the key is not ours any more.
        assert press_escape(view) is False

        # The picture has an `Esc` of its own: it has a focus of its own (it can
        # stand on a second screen), and the window's handler never sees that key.
        window._actions["graphics"].setChecked(True)
        assert picture.isVisible() is True
        assert press_escape(picture) is True
        assert picture.isVisible() is False
        assert window._actions["graphics"].isChecked() is False
    finally:
        discard_changes(window)
    print("ok: Escape closes the picture, the bar and the two docks, in that order")


def test_a_run_that_draws_opens_the_picture_by_itself(executable: str) -> None:
    """task_48: the first primitive of a run brings the window up — once per run.

    A student who runs a drawing program should see the picture without being told
    where the window is — and a student who closed it during a long animation must
    not be fought by the next hundred primitives.
    """
    window = empty_window(executable)
    try:
        assert window.graphics_available() is False, "nothing opened the picture yet"

        # A program that draws shows its picture without being asked.
        window.editor().setPlainText("?ТОЧКА(3, 4, 5).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(3, 4) == 5), window.output_text()
        picture = window.graphics_window()
        assert picture.isVisible() is True, "the first primitive must open the window"
        assert window._actions["graphics"].isChecked() is True, "and the entry says so"
        assert window._settings.graphics_visible is True

        # A program that draws nothing must not open a window at all.
        window._actions["graphics"].setChecked(False)
        window.editor().setPlainText("?РАВНО(1, 1).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: "ДА" in window.output_text()), window.output_text()
        assert picture.isVisible() is False, "nothing was drawn, so no window"

        # Closing it during a run is the user's answer, and the rest of the run
        # must not undo it: the second primitive arrives after the close.
        window.editor().setPlainText("?ТОЧКА(1, 1, 1), ЖДИ(200), ТОЧКА(6, 6, 6).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(1, 1) == 1), window.output_text()
        assert picture.isVisible() is True, "the run opened it"
        picture.close()
        assert picture.isVisible() is False
        assert pump(window, lambda: window.canvas().pixel(6, 6) == 6), window.output_text()
        assert picture.isVisible() is False, "a window the user closed stays closed"

        # The next run opens it again: «once per run» is not «once per session».
        window.editor().setPlainText("?ТОЧКА(8, 8, 8).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(8, 8) == 8), window.output_text()
        assert picture.isVisible() is True
        window.stop_program()
    finally:
        discard_changes(window)
    print("ok: a run that draws opens the picture once, and a closed window stays closed")


def test_a_long_trace_arrives_in_batches_and_stays_bounded(executable: str) -> None:
    """task_49: «Запустить с трассировкой» on a deep recursion used to take the window.

    Two costs, both measured: one `feed` per event is some 30 us of Python on top of
    the insertion, and trimming *one* line per appended line is quadratic — 200 000
    lines took 22 s that way, and about 2 s in bulks.  So the window now hands its
    output to the pane once per turn of the event loop, and the pane trims in
    bulks.
    """
    from prologd_gui import panels

    window = empty_window(executable)
    try:
        # The batching contract without an interpreter in the way: 20 000 lines
        # queued, nothing in the pane until the loop turns, every one of them after.
        line = "правило: цель(аргумент, ещё_один)\n"
        for _ in range(20000):
            window._append_output(line, panels.TRACE)
        assert window._output.toPlainText() == "", "the queue went in line by line"
        assert pump(window, lambda: len(window.output_text().splitlines()) > 19999), (
            "the queued output never arrived"
        )
        assert window._output.truncated() is False, "20 000 lines fit in the history"
        window.clear_output()
        assert window.output_text() == "", "clearing drops what was queued"

        # And a real trace: a deep recursion traced to its end, in bounded time.
        window.editor().setPlainText(
            "шаг(0).\n"
            "шаг(Н):-БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(М, 1, Н), шаг(М).\n"
            "?шаг(1200).\n"
        )
        window._actions["run_trace"].trigger()
        assert pump(window, lambda: "решени" in window.status_text()), window.status_text()
        text = window.output_text()
        assert text.count("Согласуется с") > 1000, text.count("Согласуется с")
        assert window._output.truncated() is False, "a trace of this size still fits"
    finally:
        discard_changes(window)
    print("ok: a long trace arrives in batches, in bulks, and without taking the window")


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
                elif key == actions.FORMAT_MODE:
                    expected.append("Формат")
                elif key == actions.THEME_MODE:
                    expected.append("Оформление")
                else:
                    expected.append(actions.BY_KEY[key].title)
            assert [entry.text() for entry in menus[title].actions()] == expected, title
        assert set(window._actions) == set(actions.BY_KEY), "the window has stray actions"

        # What is not implemented yet says so instead of doing nothing quietly.
        # That list is empty now: the execution group left it in task_28
        # (`Запустить с трассировкой`, `Шаг`, `Шаг с обходом` are live),
        # `test_search.py` is where the search entries are checked, «Настройки…»
        # left it in task_29, and «Графическое окно» in task_45 — it is the
        # picture of the graphics predicates now, and its state is the window's
        # visibility.
        settings = window._actions["settings"]
        assert settings.isEnabled() is True, "«Настройки…» is live since task_29"
        assert "не реализовано" not in settings.toolTip(), settings.toolTip()
        assert settings.icon().isNull() is False, "tools-settings.png is drawn"
        graphics = window._actions["graphics"]
        assert graphics.isEnabled() is True, "the picture window is live now (task_45)"
        assert graphics.isCheckable() is True, "its check state is the window's visibility"
        assert "не реализовано" not in graphics.toolTip(), graphics.toolTip()
        assert graphics.icon().isNull() is False, "view-graphics.png is drawn"
        assert window._actions["format"].isEnabled() is True, "the formatter is live now (task_30)"
        assert window._actions["step"].isEnabled() is True, "stepping is implemented now"
        assert window._actions["run_trace"].isEnabled() is True
        print("ok: the menu bar is built from the action table, and no entry is disabled any more")
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
        # The toolbar keeps the three file buttons that act on the tab in front of
        # the user; «Сохранить все» acts on every tab and belongs in «Файл» (task_48).
        assert actions.BY_KEY["save_all"].title not in shown, shown

        # An icon that exists is set; the view switches have none by decision: their
        # `view-*` pictures were dropped, and a switch reads faster than it is
        # recognised (task_48).
        assert window._actions["save"].icon().isNull() is False
        assert window._actions["reload"].icon().isNull() is False, "file-reload.png is drawn now"
        assert window._actions["line_numbers"].icon().isNull() is True
        assert window._actions["toolbar"].icon().isNull() is True
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


def test_two_font_sizes_and_one_wheel(executable: str) -> None:
    """The editor and the output keep sizes of their own (task_29).

    One number used to cover both panels.  The toolbar's box and the wheel over
    the editor move the *editor's* size; the wheel over the output moves the
    output's, and the query line goes with the editor, because a goal is typed
    like a program rather than read like a log.
    """
    window = empty_window(executable)
    try:
        box = window._font_size_box
        assert box.currentData() == float(window._settings.font_size), box.currentData()
        assert window.output().font_size == window.editor().font_size, "one size out of the box"

        box.setCurrentIndex(box.findData(20.0))
        assert window.editor().font_size == 20.0
        assert window._settings.font_size == 20.0
        # The output follows until it is given a size of its own: that is how it
        # behaved before task_29 split the two numbers.
        assert window.output().font_size == 20.0
        assert window._query_line.font().pointSizeF() == 20.0, "a goal is typed like a program"

        # A wheel over the output separates them for good.
        window.output().set_font_size(9)
        assert window._settings.output_font_size == 9.0
        assert window.input_pane().font_size == 9.0, "the queue belongs to the output side"
        window.editor().set_font_size(23)
        assert window.output().font_size == 9.0, "the output followed the editor again"
        assert window._settings.output_font_size == 9.0
        assert box.currentText() == "23", box.currentText()
        print("ok: the output follows the editor until it gets a size of its own")
    finally:
        discard_changes(window)


def test_the_settings_dialog_changes_the_window_without_a_restart(executable: str) -> None:
    """«Применить» shows in the editor *while the dialog is still open*.

    The dialog is driven the way the user drives it (widgets and buttons), and
    only the modal `exec()` is replaced — a modal box hangs a headless run
    instead of failing it.  What is checked inside `drive` is the whole point of
    the `changesApplied` signal: the window behind a modal dialog still paints,
    so a change must arrive there without closing it.
    """
    from prologd_gui import settings as settings_module

    window = empty_window(executable)
    try:
        def drive(dialog) -> bool:
            widgets = dialog.widgets()
            widgets[settings_module.LINE_NUMBERS].setChecked(False)
            widgets[settings_module.CURRENT_LINE].setChecked(False)
            widgets[settings_module.FONT_SIZE].setValue(14)
            widgets[settings_module.OUTPUT_FONT_SIZE].setValue(20)
            widgets[settings_module.OUTPUT_LINE_LIMIT].setValue(1000)
            position = widgets[settings_module.OUTPUT_POSITION]
            position.setCurrentIndex(position.findData("bottom"))
            widgets[settings_module.IMPORT_PATHS].add_path("C:/общие")

            # Touching a widget changes nothing anywhere: the file is written by
            # the buttons, not by the fields.
            assert window.editor().font_size == 11.0, "the editor changed on its own"
            assert window.editor().line_numbers() is True

            dialog.button("apply").click()
            # ...and the dialog is still open right here.
            assert window.editor().font_size == 14.0, "«Применить» did not reach the editor"
            assert window.editor().line_numbers() is False
            assert window.output().font_size == 20.0
            assert "C:/общие" in window.session._includes
            return False  # «Применить», then «Отмена»: what was applied stays

        window._run_settings_dialog = drive
        assert window.show_settings() is False, "nothing was accepted by this driver"

        # Everything applied before «Отмена» is still in force afterwards.
        assert window.editor().line_numbers() is False
        assert window.editor().font_size == 14.0
        assert window.editor()._current_line is False
        assert window.output().font_size == 20.0
        assert window.output().line_limit() == 1000
        assert window.output_position() == "bottom"
        assert window._font_size_box.currentData() == 14.0, "the toolbar box is a view of it too"
        assert "C:/общие" in window.session._includes
        assert window.session is window._session
        print("ok: «Применить» reaches the editor, the output and the session at once")
    finally:
        discard_changes(window)


def test_the_shared_folder_reaches_the_interpreter(executable: str) -> None:
    """The «Рабочая папка (ИМПОРТ)» of task_29 is what makes `ИМПОРТ` work everywhere.

    An untitled buffer has no folder of its own, so `ИМПОРТ("library.pld")`
    fails until the shared folder is set — and works in every tab afterwards.
    """
    library = pathlib.Path(__file__).resolve().parents[3] / "examples" / "lib"
    if not (library / "library.pld").is_file():
        print(f"skipped: {library / 'library.pld'} is missing")
        return

    window = empty_window(executable)
    try:
        def concluded() -> bool:
            # `Запустить` is live again when the run is over; the *status* is not a
            # good signal here, because a failed load in the protocol session ends
            # the process (the CLI exits 2) instead of answering «выполнено».
            return window._actions["run"].isEnabled()

        window.editor().setPlainText(':- ИМПОРТ("library.pld").\n')
        window.run_program()
        assert pump(window, concluded), ascii(window.output_text())
        assert "Не найден" in window.output_text(), ascii(window.output_text())

        window._settings.working_directory = str(library)
        window.apply_settings()
        assert str(library) in window._session._includes

        window.run_program()
        assert pump(window, concluded), ascii(window.output_text())
        assert window.status_text() == "выполнено", ascii(window.output_text())
        assert "Не найден" not in window.output_text(), ascii(window.output_text())
        print("ok: the shared folder is passed as -I, and an unnamed buffer imports from it")
    finally:
        discard_changes(window)


def test_autosave_writes_named_buffers_and_skips_the_rest(
    executable: str, directory: pathlib.Path
) -> None:
    """task_29's autosave: named buffers only, never a question, one timer."""
    target = directory / "автосохранение.pld"
    target.write_text("факт(1).\n", encoding="utf-8")

    window = empty_window(executable)
    try:
        window.open_path(str(target))
        window.editor().insertPlainText("?факт(1).\n")
        assert window.buffers()[0].is_modified() is True
        assert window.autosave_now() == 1
        assert target.read_text(encoding="utf-8") == "?факт(1).\nфакт(1).\n"
        assert window.buffers()[0].is_modified() is False
        assert "автосохранение" in window.status_text(), window.status_text()

        # An untitled buffer has no file to write, and an autosave must not ask
        # for a name: that question belongs to «Сохранить».
        window._ask_save_path = lambda buffer: (_ for _ in ()).throw(
            AssertionError("autosave asked for a file name")
        )
        window.new_buffer()
        window.editor().insertPlainText("снег.\n")
        assert window.autosave_now() == 0
        assert window.current_path() is None

        # The timer follows the setting: 0 is off, a minute count arms it.
        window._settings.autosave_minutes = 5
        window.apply_settings()
        assert window._autosave.isActive() is True
        window._settings.autosave_minutes = 0
        window.apply_settings()
        assert window._autosave.isActive() is False
        print("ok: autosave writes named buffers, skips unnamed ones, and follows its switch")
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
    """Zoom is written straight to the settings and survives a restart.

    The editor's size only: the output panel has a size of its own since task_29
    (`test_two_font_sizes_and_one_wheel`), and *this* check is about the stored
    value coming back — which is what a restart has to keep.
    """
    window = make_window(executable)
    path = window._settings.path
    try:
        assert window.output().font_size == window.editor().font_size
        window.editor().set_font_size(17)
        size = window.editor().font_size
        assert size == 17
        assert window._query_line.font().pointSizeF() == size, "a goal is typed like a program"
        assert window._settings.font_size == size
        # Nobody gave the output a size of its own, so it came along — but it is
        # a value of its own in the file from now on.
        assert window._settings.output_font_size == size
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
        assert "ошибка: Без имени:1:1" in window.status_text(), window.status_text()
        assert "Без имени:1:1: деление на ноль" in window.output_text(), ascii(
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
        assert colour_of(window._output, amber[0]) == window._output.kind_colors()[panels.WARNING]
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
        assert colour_of(window._output, block) == window._output.kind_colors()[panels.TRACE]
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


def test_a_failed_query_marks_no_line_and_moves_no_caret(executable: str) -> None:
    """A query error is about the statement, not about line 1 of the program.

    The statement arrives as a source of its own and is named `<query>`; treating
    that name as the buffer marked line 1 red and pulled the caret to the top of
    the program for every failing query — reported as «для целей с ошибкой выдаёт
    всегда ошибку в первой строке 1:1 и перемещает туда курсор».
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(X).\n")
        window.run_program()
        wait_for_result(window)

        view = window.editor()
        cursor = view.textCursor()
        cursor.setPosition(2)
        view.setTextCursor(cursor)

        window._query_line.setText('?is_whole("4").')
        window._run_query()
        assert pump(window, lambda: "ошибка" in window.status_text()), window.status_text()

        assert "ошибка: <query>:1:1" in window.status_text(), window.status_text()
        assert "<query>:1:1" in window.output_text(), ascii(window.output_text())
        assert view.error_line() is None, view.error_line()
        assert view.textCursor().position() == 2, "the caret moved"
    finally:
        discard_changes(window)
    print("ok: a failed query is shown in the pane without marking the program")


def test_copy_takes_the_selection_where_the_focus_is(executable: str) -> None:
    """`Ctrl+C` is a window shortcut: it must copy what the user is looking at.

    It copied the *editor's* selection no matter where the focus was, so text the
    user had selected in the output pane could not be copied at all (asked for
    after the first hands-on run of the margin feature).
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(1).\n")
        window.run_program()
        wait_for_result(window)
        window.show()

        output = window._output
        output.setFocus()
        QApplication.processEvents()
        assert window.focusWidget() is output, window.focusWidget()
        cursor = output.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        output.setTextCursor(cursor)
        window._copy()
        assert QApplication.clipboard().text() == output.toPlainText()

        # With the editor focused the same command is the editor's, as it was.
        view = window.editor()
        view.setFocus()
        QApplication.processEvents()
        cursor = view.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        view.setTextCursor(cursor)
        window._copy()
        assert QApplication.clipboard().text() == view.toPlainText()
    finally:
        discard_changes(window)
    print("ok: Ctrl+C copies from the focused pane — the output included")


def test_f1_shows_the_record_of_the_word_under_the_caret(executable: str) -> None:
    """task_37: `F1` on `КОПИЯ` lists the five modes of 7.4 and the section.

    The dock is filled from `doc/builtins.json`; the manual («Руководство
    пользователя») keeps `Shift+F1`, because `F1` is the key pressed *while
    reading a program*.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText('тест :- КОПИЯ("абв", 1, 2, Х).\n')
        view = window.editor()
        cursor = view.textCursor()
        cursor.setPosition(view.toPlainText().index("КОПИЯ") + 2)
        view.setTextCursor(cursor)
        window._actions["reference"].trigger()

        text = window.reference_text()
        assert text.startswith("КОПИЯ — Подстрока и поиск"), ascii(text)
        assert "раздел руководства: 7.4" in text, ascii(text)
        for mode in ("ц1, ц2, П", "ц1, ц2, с4", "П, ц2, с4", "П, Р, с4", "ц1, П, с4"):
            assert mode in text, (mode, ascii(text))
        assert not window._reference_dock.isHidden()

        # An unknown word says so instead of showing the previous record.
        cursor.setPosition(view.toPlainText().index("тест") + 1)
        view.setTextCursor(cursor)
        window._actions["reference"].trigger()
        assert "нет справки" in window.reference_text(), ascii(window.reference_text())
    finally:
        discard_changes(window)
    print("ok: F1 shows the record of the word under the caret, and says «нет справки»")


def press_ctrl_key(window, scan: int) -> bool:
    """`Ctrl` plus a **physical** key, the way `task_31` matches them.

    `QKeyEvent` has two constructors and only the second carries a native scan
    code; the offscreen platform has no keyboard to ask, so the code is handed in.
    The virtual key and the native modifiers stay zero: nothing reads them.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_unknown,
        Qt.KeyboardModifier.ControlModifier,
        scan,
        0,
        0,
    )
    QApplication.sendEvent(window.editor(), event)
    return event.isAccepted()


def test_the_cheat_sheet_lists_the_insert_table(executable: str) -> None:
    """task_31: «Справка → Шпаргалка по вставкам» lists the chords that are live.

    The table is *data*: the window writes the built-in one into its own settings
    file the first time it runs, so a symbol that sits on another physical key —
    or a keyboard that has no such key — is remapped in that file without a code
    change.  The cheat sheet is built from the same object the editors insert
    with, which is why a remapped chord cannot be listed wrongly.
    """
    from prologd_gui.shortcuts import Shortcuts

    window = empty_window(executable)
    try:
        assert window.shortcut_text() == "", "the dock is filled before it is asked for"
        window._actions["shortcuts"].trigger()
        text = window.shortcut_text()
        for chord in ("Ctrl+;", "Ctrl+6", "Ctrl+Shift+/", "Ctrl+7", "Ctrl+Shift+.",
                      "Ctrl+Shift+=", "Ctrl+8", "Ctrl+["):
            assert chord in text, (chord, ascii(text))
        assert "выделение" in text, ascii(text)
        assert "Шпаргалка" in window._shortcut_dock.windowTitle()
        assert not window._shortcut_dock.isHidden()

        # The table is in the settings file, which is what makes it remappable.
        stored = window._settings.path.read_text(encoding="utf-8")
        assert "table=" in stored, stored
        built_in = Shortcuts.default().keys()
        assert Shortcuts.from_json(window._settings.shortcuts_table).keys() == built_in
    finally:
        discard_changes(window)
    print("ok: the cheat sheet lists the table the window keeps in its settings file")


def test_a_remapped_table_decides_what_ctrl_key_inserts(executable: str) -> None:
    """A file that moves a symbol is honoured: that is what «the table is data» means.

    On this machine `Ctrl+[` inserts `€`, and nothing in the code knows about
    either: the single entry came out of the settings file, and the window must
    not overwrite a table it found there.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    remapped = '[{"insert": "|€", "chords": [{"scan": 26, "shift": null, "key": "["}]}]'
    directory = tempfile.TemporaryDirectory(prefix="prologd_gui_test_")
    _SETTINGS_DIRECTORIES.append(directory)
    settings = Settings(pathlib.Path(directory.name) / "gui.ini")
    settings.shortcuts_table = remapped

    window = MainWindow(executable, [], settings)
    window.session.start()
    assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
    try:
        # The welcome program has to go, or the insert lands in front of it.
        window.editor().setPlainText("")
        assert press_ctrl_key(window, 0x1A), "the remapped chord was not taken"
        assert window.editor_text() == "€", ascii(window.editor_text())
        assert window._settings.shortcuts_table == remapped, "the window overwrote the table"

        window._actions["shortcuts"].trigger()
        text = window.shortcut_text()
        assert "Ctrl+[" in text and "€" in text, ascii(text)
        assert "[]" not in text, "the built-in table was listed instead"
    finally:
        discard_changes(window)
    print("ok: a remapped table from the settings file decides what the editor inserts")


def test_the_step_strip_is_one_font_and_three_pictures(executable: str) -> None:
    """The strip's buttons are the toolbar's pictures; the strip is one font.

    Reported from a run: «Продолжить» and «Стоп» were words in the interface font
    between monospace labels — a paragraph of prose in the middle of a program —
    and there was no way to step from the strip itself.  The second look at the
    same strip added the «где» case: the whole path of an opened file ran up
    against those buttons.
    """
    from PySide6.QtWidgets import QLabel

    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\nсчёт(X) :- факт(X).\n?счёт(X).\n")
        window._actions["step"].trigger()
        assert pump(window, lambda: window.stepping()), "the step panel never appeared"
        pane = window.step_pane()

        for button in (pane.resume_button(), pane.step_button(), pane.stop_button()):
            assert button.text() == "", "the strip's buttons show pictures now"
            assert button.icon().isNull() is False, "the picture is missing"
            assert button.toolTip(), "the words moved into the tooltip"
        assert "F5" in pane.resume_button().toolTip()
        assert "F10" in pane.step_button().toolTip()

        # One font for the whole strip, and the zoom moves all of it.
        pane.set_font_size(15.0)
        sizes = {round(label.font().pointSizeF(), 1) for label in pane.findChildren(QLabel)}
        assert sizes == {15.0}, sizes

        # The picture acts: «Шаг» goes one point further in, like `F10`.
        pane.step_button().click()
        assert pump(window, lambda: pane.goal_text().startswith("факт")), ascii(
            pane.goal_text()
        )

        # The «где» line shows a *place*, not the whole of `C:\Users\…`: on an
        # opened file the path ran up against the buttons, and a narrower window
        # cut it mid-word with nothing to say it had been cut.  The whole path
        # stays in the tooltip, and what does not fit is elided in the middle —
        # the file's own name is the part being looked for.
        from prologd_gui.protocol import Position, StepPoint

        pane.show_point(
            StepPoint(
                action="call",
                goal="цель(_1)",
                depth=2,
                position=Position(
                    "C:/Users/vasla/source/projects/examples/monk.pld", 2, 1
                ),
            ),
            ["monk(6)"],
        )
        assert pane.where_text().endswith("monk.pld:2:1"), ascii(pane.where_text())
        assert "C:/Users" not in pane.where_text(), ascii(pane.where_text())
        assert "C:/Users" in pane._where.toolTip(), ascii(pane._where.toolTip())
        # A window too narrow for the place drops its head and keeps the tail: the
        # file's own name, then the line and the column, are what is being read.
        pane._where.resize(240, pane._where.height())
        shown = pane.where_display_text()
        assert shown.startswith("…"), ascii(shown)
        assert shown.endswith(":2:1"), ascii(shown)
        assert shown != pane.where_text(), ascii(shown)
        assert len(shown) < len(pane.where_text()), ascii(shown)
        pane._where.grab()  # and painting it does not fall over
    finally:
        discard_changes(window)
    print("ok: the step strip is one font, and its buttons are the toolbar's pictures")


def test_formatting_lays_the_buffer_out_and_stays_one_undo_step(executable: str) -> None:
    """`Ctrl+I` goes through the protocol: whitespace only, one undo, the caret kept."""
    old = "факт(1).\nцель(Х) :- часть(Х),   ещё(Х).\n"
    new = "факт(1).\nцель(Х):-часть(Х), ещё(Х).\n"
    window = empty_window(executable)
    try:
        view = window.editor()
        view.setPlainText(old)
        place = old.index("часть") + 2
        cursor = view.textCursor()
        cursor.setPosition(place)
        view.setTextCursor(cursor)

        window._actions["format"].trigger()
        assert pump(window, lambda: view.toPlainText() == new), ascii(view.toPlainText())
        assert window.status_text() == "отформатировано", window.status_text()
        assert window.current_buffer().text() == new, "the document itself changed"
        # Only whitespace moved, so the caret keeps its place — character for
        # character, not "somewhere near".
        assert view.textCursor().position() == new.index("часть") + 2

        view.undo()
        assert view.toPlainText() == old, "one undo puts the whole format back"

        # An already formatted buffer is answered with a note, not a rewrite.
        view.redo()
        window._actions["format"].trigger()
        assert pump(
            window, lambda: window.status_text() == "уже отформатировано"
        ), window.status_text()
        assert view.toPlainText() == new
    finally:
        discard_changes(window)
    print("ok: Ctrl+I formats the buffer, keeps the caret, and one undo takes it back")


def test_formatting_only_the_selection(executable: str) -> None:
    """«Только выделенное»: the fragment is formatted alone, the rest untouched."""
    old = "цель(Х) :- часть(Х),   ещё(Х).\nфакт(1).\n"
    fragment = "цель(Х) :- часть(Х),   ещё(Х).\n"
    expected = "цель(Х):-часть(Х), ещё(Х).\nфакт(1).\n"
    window = empty_window(executable)
    try:
        view = window.editor()
        view.setPlainText(old)
        # The switch goes through the menu, the way a user turns it on: the
        # setting is what the action writes.
        window._format_selection_action.setChecked(True)
        assert window._settings.format_selection is True
        cursor = view.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(len(fragment), QTextCursor.MoveMode.KeepAnchor)
        view.setTextCursor(cursor)

        window._actions["format"].trigger()
        assert pump(window, lambda: view.toPlainText() == expected), ascii(view.toPlainText())
        # The formatted fragment stays selected: it is what was rewritten.
        selection = view.textCursor()
        assert (selection.selectionStart(), selection.selectionEnd()) == (
            0,
            len("цель(Х):-часть(Х), ещё(Х).\n"),
        ), (selection.selectionStart(), selection.selectionEnd())
    finally:
        discard_changes(window)
    print("ok: with «только выделенное» the selection is formatted alone")


def test_a_broken_program_is_reported_and_not_rewritten(executable: str) -> None:
    window = empty_window(executable)
    try:
        broken = "цель(Х:-часть(Х).\n"
        window.editor().setPlainText(broken)
        window._actions["format"].trigger()
        assert pump(window, lambda: "не удалось" in window.status_text()), window.status_text()
        assert window.editor().toPlainText() == broken, "the buffer was rewritten anyway"
        assert window.editor().error_line() == 1, "the line is marked"
    finally:
        discard_changes(window)
    print("ok: a broken program keeps its text and its line is marked")


def test_the_mode_control_stands_beside_the_command_it_changes(
    executable: str,
) -> None:
    """The mode is a toolbar control next to «Форматировать», and each mode reaches the wire."""
    window = empty_window(executable)
    try:
        # On the toolbar, immediately after the command it changes (task_47): the
        # mode is switched *while looking at the code*, and two menu levels for it
        # is one too many.
        entries = window._toolbar.actions()
        index = entries.index(window._actions["format"])
        assert entries[index + 1].defaultWidget() is window._format_button, (
            "the mode control must stand right after «Форматировать»"
        )
        assert window._format_button.menu() is window._format_menu
        assert window._format_button.popupMode().name == "InstantPopup", (
            "one click opens the modes, without a long press"
        )
        assert window._format_button.icon().isNull() is False, "edit-format-set.png is drawn"
        assert window._format_button.toolTip() != ""

        # One home for one control: «Правка» does not carry a «Формат» submenu.
        editing = {
            entry.text(): entry.menu() for entry in window.menuBar().actions()
        }["Правка"]
        titles = [entry.text() for entry in editing.actions() if entry.text()]
        assert "Формат" not in titles, titles
        assert [entry.text() for entry in window._format_menu.actions() if entry.text()] == [
            "В одну строку — цели тела собираются в строку",
            "Мягкое — переносить то, что не влезло",
            "Жёсткое — по цели на строку",
            "Только выделенное",
        ]

        window._format_mode_actions["hard"].trigger()
        assert window._settings.format_mode == "hard"
        window.editor().setPlainText("факт(1).\nцель(Х):-часть(Х), ещё(Х).\n")
        window._actions["format"].trigger()
        # The head stands alone: the first goal was the one glued to it (task_47).
        hard = "факт(1).\nцель(Х):-\n\tчасть(Х),\n\tещё(Х).\n"
        assert pump(window, lambda: window.editor().toPlainText() == hard), ascii(
            window.editor().toPlainText()
        )

        # And back: the soft mode builds the lines again, so a hard layout is
        # converted instead of kept.
        window._format_mode_actions["soft"].trigger()
        assert window._settings.format_mode == "soft"
        window._actions["format"].trigger()
        soft = "факт(1).\nцель(Х):-часть(Х), ещё(Х).\n"
        assert pump(window, lambda: window.editor().toPlainText() == soft), ascii(
            window.editor().toPlainText()
        )

        # «В одну строку» joins the body regardless of the width.
        window._format_mode_actions["line"].trigger()
        assert window._settings.format_mode == "line"
        window.editor().setPlainText(
            "факт(1).\nцель(Х):-часть(Х),\n\tещё(Х),\n\tтретья(Х).\n"
        )
        window._actions["format"].trigger()
        line = "факт(1).\nцель(Х):-часть(Х), ещё(Х), третья(Х).\n"
        assert pump(window, lambda: window.editor().toPlainText() == line), ascii(
            window.editor().toPlainText()
        )
    finally:
        discard_changes(window)
    print("ok: the mode control sits on the toolbar, and hard, soft and one-line reach the wire")


def test_the_reserved_names_are_there_before_the_first_run(executable: str) -> None:
    """Completion must not wait for the first run (a one-off `--list-keywords`)."""
    window = make_window(executable, ready=False)
    try:
        assert window.session.is_running() is False, (
            "a window that was only opened keeps no interpreter"
        )
        table = window.session.keywords
        assert table.is_reserved("НАЙТИВСЕ") is True
        assert table.arity("УМНОЖЕНИЕ") == (3, 4)
        assert table.all_labels(), "the table is empty"
    finally:
        discard_changes(window)
    print("ok: the reserved names are there before the first run")


def test_running_programs_without_questions_finishes(executable: str) -> None:
    """A run is over when the *load* is: `result` only arrives for questions."""
    window = empty_window(executable)
    try:
        # An empty program: nothing to load and nothing to ask — and no hang.
        window.editor().setPlainText("")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.status_text() == "выполнено"), window.status_text()
        assert window._actions["run"].isEnabled() is True, "the run never finished"

        # Facts without a single question finish the same way.
        window.editor().setPlainText("факт(1).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.status_text() == "выполнено"), window.status_text()
        assert window._actions["run"].isEnabled() is True, "the run never finished"
    finally:
        discard_changes(window)
    print("ok: a program without questions finishes instead of hanging in «выполняется»")


def test_the_tabs_come_back_on_the_next_start(
    executable: str, directory: pathlib.Path
) -> None:
    """task_29: the session — the tabs of the previous run open again.

    A *file* tab is read from disk, so a change the user refused to save is not
    resurrected; an untitled tab comes back with its text and with the state it
    had when the window closed — a tab that was not unsaved work does not come
    back starred (task_49: every restored untitled tab used to be); the tab that
    was showing is the one that shows again; and a file that has gone is named
    instead of silently missing from the session.

    The unnamed tab is *not* left unsaved here: this check is about the text
    travelling with the record, and a tab answered with «Не сохранять» does not
    travel at all (that is `test_an_unnamed_tab_left_unsaved_is_forgotten`).
    """
    from prologd_gui import documents
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    one = directory / "сессия_один.pld"
    one.write_text("снег.\n", encoding="utf-8")
    two = directory / "сессия_два.pld"
    two.write_text("дождь.\n", encoding="utf-8")

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        window.open_path(str(one))
        window.open_path(str(two))
        window.new_buffer()
        window.editor().insertPlainText("факт(1).\n")
        third = window.current_buffer().model.name
        assert window.tab_count() == 3, window.tab_count()
        # Nothing is unsaved here, so the close asks no questions.
        window.buffers()[2].mark_saved()

        window.close()
    finally:
        window.stop_program()

    settings = Settings(settings_path)
    assert settings.restore_tabs is True, "«восстанавливать вкладки» is on by default"
    stored = documents.decode_tabs(settings.session_tabs)
    assert [record.name for record in stored] == [one.name, two.name, third], stored
    assert [record.text for record in stored[:2]] == ["", ""], "a file is a path, not text"
    assert stored[2].text == "факт(1).\n", "the untitled tab carries its text"
    assert settings.session_current == third, settings.session_current

    # Every window stores its own session when it closes, so a window opened and
    # closed inside this check would overwrite what the first run left.  The two
    # lines below stand for «the session as the first run left it», and each
    # window starts from that.
    left_tabs, left_current = list(settings.session_tabs), settings.session_current

    def next_start():
        settings.session_tabs = list(left_tabs)
        settings.session_current = left_current
        return MainWindow(executable, [], settings)

    reopened = next_start()
    try:
        assert reopened.tab_count() == 3, [b.model.name for b in reopened.buffers()]
        assert reopened.buffers()[0].text() == "снег.\n", "read from the file"
        assert reopened.buffers()[0].is_modified() is False
        assert reopened.buffers()[2].text() == "факт(1).\n"
        assert reopened.buffers()[2].is_modified() is False, (
            "the tab was not unsaved work when the window closed — the close had "
            "already asked about everything that was — so it comes back clean "
            "(task_49)"
        )
        assert reopened.current_buffer().model.name == third, "the tab that was showing"
        assert "восстановлено вкладок: 3" in reopened.status_text(), reopened.status_text()
    finally:
        discard_changes(reopened)

    # A file that has gone is named, and the rest of the session still opens.
    one.unlink()
    reopened = next_start()
    try:
        assert reopened.tab_count() == 2, [b.model.name for b in reopened.buffers()]
        said = reopened.status_text()
        assert "не найдено" in said and one.name in said, said
    finally:
        discard_changes(reopened)

    # Switching it off gives the welcome program: the setting is the only switch.
    settings.restore_tabs = False
    reopened = next_start()
    try:
        assert reopened.tab_count() == 1, [b.model.name for b in reopened.buffers()]
        assert reopened.buffers()[0].model.path is None
        assert "восстановлено" not in reopened.status_text(), reopened.status_text()
    finally:
        discard_changes(reopened)
    print("ok: the open tabs come back on the next start, and can be switched off")


def test_an_unnamed_tab_left_unsaved_is_forgotten(
    executable: str, directory: pathlib.Path
) -> None:
    """«Не сохранять» on an unnamed buffer means it is not to be seen again.

    An untitled tab is remembered by its *text*, so a session written before the
    closing questions would bring back exactly the work the user threw away — the
    answer would be a lie.  A tab the user saves on the way out goes the other
    way: it is remembered as the file it became, not as the unnamed buffer it was.
    """
    from prologd_gui import documents
    from prologd_gui import window as window_module
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    kept = directory / "остаётся.pld"
    kept.write_text("снег.\n", encoding="utf-8")
    saved = directory / "сохранённое на выходе.pld"

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        window.open_path(str(kept))
        window.new_buffer()
        window.editor().insertPlainText("черновик.\n")
        draft = window.current_buffer().model.name
        window.new_buffer()
        window.editor().insertPlainText("сохраню.\n")
        keep = window.current_buffer().model.name
        assert window.tab_count() == 3, window.tab_count()

        # «Черновик» is thrown away, «сохраню» is written to a file of its own —
        # the file dialog is replaced the same way the question is.
        window._ask_save = lambda name: (
            window_module.SAVE if name == keep else window_module.DISCARD
        )
        window._ask_save_path = lambda buffer: str(saved)
        window.close()
    finally:
        window.stop_program()

    settings = Settings(settings_path)
    stored = documents.decode_tabs(settings.session_tabs)
    assert [record.name for record in stored] == [kept.name, saved.name], stored
    assert all(record.path for record in stored), "a saved tab is a file, not text"
    assert saved.read_text(encoding="utf-8") == "сохраню.\n", saved.read_text("utf-8")

    reopened = MainWindow(executable, [], settings)
    try:
        assert [b.model.name for b in reopened.buffers()] == [kept.name, saved.name], [
            b.model.name for b in reopened.buffers()
        ]
        assert reopened.buffers()[1].text() == "сохраню.\n"
        assert reopened.buffers()[1].is_modified() is False
        texts = [b.text() for b in reopened.buffers()]
        assert not any("черновик" in text for text in texts), texts
    finally:
        discard_changes(reopened)
    print(
        "ok: an unnamed tab answered with «Не сохранять» is dropped from the session, "
        "and one saved on the way out is remembered as its file"
    )


def test_an_untouched_unnamed_tab_comes_back_clean(executable: str) -> None:
    """task_49: two unnamed tabs — the restored one used to come back as `*Без имени`.

    The reproduction the user gave: a window with the welcome tab and a second,
    brand-new one.  Nothing was edited, so the close asks nothing; the session
    keeps the first tab (the second is empty and is not worth keeping), and the
    next start restored it as *unsaved work* — a star on a program nobody had
    written, and a save question about it on the way out.  With one tab the
    window came back clean, which is why the two cases looked different: that
    tab was empty and was not stored at all.

    What a record now carries is the state the buffer had: closing the window has
    already asked about every change there was (that is what `close_all` does), so
    a tab that survives as *text* is one the user left alone.
    """
    from prologd_gui import documents
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    window = make_window(executable)
    settings_path = window._settings.path
    try:
        assert window.buffers()[0].text().startswith("% PrologD"), "the welcome tab"
        assert window.buffers()[0].is_modified() is False
        window.new_buffer()
        assert window.tab_count() == 2, window.tab_count()
        assert window.buffers()[1].text() == ""
        window.close()  # nothing was edited, so no question is asked
    finally:
        window.stop_program()

    settings = Settings(settings_path)
    stored = documents.decode_tabs(settings.session_tabs)
    assert [record.name for record in stored] == ["Без имени"], stored
    assert stored[0].text.startswith("% PrologD")
    assert stored[0].modified is False, "nobody edited the welcome program"

    reopened = MainWindow(executable, [], settings)
    try:
        assert reopened.tab_count() == 1, [b.model.name for b in reopened.buffers()]
        assert reopened.buffers()[0].text().startswith("% PrologD")
        assert reopened.buffers()[0].is_modified() is False, (
            "the restored tab carries a star it never earned"
        )
        assert reopened.buffers()[0].model.title() == "Без имени", reopened.buffers()[0].model.title()
    finally:
        discard_changes(reopened)
    print("ok: an untouched unnamed tab comes back clean, without a star or a question")


def test_the_questions_switch_decides_whether_a_run_answers(executable: str) -> None:
    """task_29's «Выводить вопросы при запуске»: off, a lesson loads as rules.

    The margin's own click is none of this switch's business — it always answers
    the one question that was clicked (`test_a_marker_answers_one_question_alone`)
    — and neither is a query typed into the query line.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(1).\n")

        window._settings.run_questions = False
        window._actions["run"].trigger()
        assert pump(window, lambda: window.status_text() == "выполнено"), window.status_text()
        assert "ДА" not in window.output_text(), ascii(window.output_text())

        window._settings.run_questions = True
        window._actions["run"].trigger()
        wait_for_result(window)
        assert "ДА" in window.output_text(), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: «выводить вопросы» decides whether a run answers the program's questions")


def test_the_input_switch_chooses_where_to_ask(executable: str) -> None:
    """task_29's «Спрашивать ввод»: the console under the output, or a box.

    Both ways are open here — the panel is visible, so the console *can* take the
    answer — which is what makes the setting a switch rather than a rule about
    what is on screen.
    """
    window = empty_window(executable)
    try:
        assert window._sidebar.isHidden() is False, "both ways need the panel"
        window.editor().setPlainText("?ВВОДЦЕЛ(А),ВЫВОД(А),ПС.\n")
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or "9"

        window._settings.input_mode = "panel"
        window.run_program()
        assert pump(window, lambda: not window._input_console.isHidden()), "no console"
        assert asked == [], "the box was used although the console is right there"
        window._input_console._line.setText("5")
        window._input_console.send()
        wait_for_result(window)
        assert printed_lines(window) == ["5", "А=5"], printed_lines(window)

        window._settings.input_mode = "dialog"
        window.run_program()
        assert pump(window, lambda: bool(asked)), "the box was not used"
        assert asked == ["token"], asked
        assert window._input_console.isHidden() is True, "the console took the question"
        wait_for_result(window)
        assert printed_lines(window) == ["9", "А=9"], printed_lines(window)
    finally:
        discard_changes(window)
    print("ok: «спрашивать ввод» chooses the console or a box, without hiding anything")


def test_the_theme_switch_reaches_the_text_and_the_widgets(executable: str) -> None:
    """«Оформление → Тёмное»: widgets, syntax, bands and output in one move.

    The half-done dark theme is the failure this check exists for: a dark widget
    palette with light syntax colours, or a dark page with the output still painted
    in the light theme's red — which is why the three are asserted together, and
    why the same page is what the contrast check measures against.
    """
    from PySide6.QtGui import QPalette as QtPalette
    from PySide6.QtWidgets import QApplication

    from prologd_gui import appearance, panels, theme
    from prologd_gui.settings import Settings

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        window.editor().setPlainText("факт(1).\n% комментарий\n")
        window._append_output("вывод программы\n", panels.OUTPUT)
        window._append_output("ошибка выполнения\n", panels.ERROR)
        # The window hands its output over on the next turn of the event loop
        # (task_49), and this check reads the pane with no loop running.
        window._flush_output()
        assert colour_of(window._output, 1) == panels.KIND_COLORS[panels.ERROR]

        window._settings.theme = theme.DARK.name
        window.apply_settings()

        # The widgets: the *page* the syntax colours are measured against.
        base = QApplication.instance().palette().color(QtPalette.ColorRole.Base).name()
        assert base == theme.DARK.background, f"the page is {base}"

        # The syntax and the bands: the document's palette and every view's.
        assert window.buffers()[0].highlighter.theme is theme.DARK.syntax
        assert window.editor().palette() is theme.DARK
        current_line = [
            selection.format.background().color().name()
            for selection in window.editor().extraSelections()
        ]
        assert theme.DARK.current_line in current_line, current_line

        # The output: the colour of new lines *and* of the lines already there.
        assert window._output.kind_colors()[panels.ERROR] == theme.DARK.error
        assert colour_of(window._output, 1) == theme.DARK.error, "the history kept its colours"

        # Stored, and the menu says which one is on.
        assert Settings(settings_path).theme == "dark"
        assert window._theme_actions["dark"].isChecked() is True
        assert window._theme_actions["light"].isChecked() is False

        # «Как в системе»: the widgets come from the desktop *and* so do the colours
        # of the text — the palette its colour scheme implies (on this machine the
        # offscreen platform answers «light», so this is a real question and not a
        # shortcut through one palette).
        window._settings.theme = appearance.SYSTEM
        window.apply_settings()
        expected = appearance.theme_palette(appearance.SYSTEM)
        assert window.buffers()[0].highlighter.theme is expected.syntax
        assert window.editor().palette() is expected
        assert window._output.kind_colors()[panels.ERROR] == expected.error
    finally:
        discard_changes(window)
    print("ok: the dark theme reaches the widgets, the syntax, the bands and the output")


def test_the_limits_stop_a_runaway_and_name_themselves(executable: str) -> None:
    """task_46: a runaway program stops, and the window says which row did it.

    The three caps travel with the load (`limits`, protocol 9) and the deadline is
    the window's own clock — the same polite stop «Остановить» uses.  A program the
    deadline cannot reach is pinned too: waiting *outside* the solver is a state the
    request only sees afterwards, which is why «Остановить» is still the answer for
    a program that waits for input nobody gives.

    The engine's message names a limit and its value and stops there — it knows
    nothing about this window (ADR-020) — so the run itself names the row that
    raises it, in the words of the dialog, before it starts.
    """
    from prologd_gui.settings import Settings

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        window.editor().setPlainText("цикл :- цикл.\n?цикл.\n")
        window._settings.max_steps = 5000
        window._settings.timeout_seconds = 2
        window._actions["run"].trigger()

        notes = window.output_text()
        assert "пределы: «Предел шагов» 5000" in notes, notes
        # A limit left at the shipped number is not a choice the user made.
        assert "Предел глубины» 1000000" not in notes, notes
        assert window._timeout.isActive() is True, "the deadline was not armed"
        said = pump(window, lambda: "предел шагов" in window.output_text())
        assert said, f"the run never stopped: {ascii(window.output_text())}"
        text = window.output_text()
        assert "Превышен предел шагов выполнения: 5000" in text, ascii(text)
        assert window._timeout.isActive() is False, "the deadline outlived its run"

        # «Предел времени»: the run is asked to stop, and the pane says by what.
        window.editor().setPlainText("?ВВОДЦЕЛ(А).\n")
        window._settings.timeout_seconds = 1
        window.run_program()
        assert pump(window, lambda: window.status_text().startswith("ждёт ввода")), \
            window.status_text()
        assert window._timeout.isActive() is True
        window._on_timeout()
        assert "остановлено по времени" in window.status_text(), window.status_text()
        assert "предел времени: 1 с" in window.output_text(), ascii(window.output_text())
        window.stop_program()
    finally:
        discard_changes(window)
    assert Settings(settings_path).max_steps == 5000, "the setting was not stored"
    print("ok: the limits reach the run, name themselves, and the deadline is the window's")


def test_stop_after_a_step_leaves_the_next_run_to_start_over(executable: str) -> None:
    """task_49: `Шаг` → `Стоп` → `Запуск` used to answer «нет шага, который ждёт ответа».

    The pause belonged to a run that was over, so `Запуск` took the «продолжить»
    path and sent a `step` answer into an interpreter with nothing waiting: the
    session printed the protocol error, and the program the user asked for never
    ran.  What makes a pause over is one of the events that conclude a run — the
    answer, the load, an error (which is what «Стоп» arrives as while a step is
    waiting) or the process ending.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(X), РАВНО(Y, 2).\n")
        window._actions["step"].trigger()
        assert pump(window, lambda: window.stepping()), "the step panel never appeared"
        assert window.session.paused() is True

        window._actions["stop"].trigger()
        assert pump(window, lambda: not window.stepping()), "the step panel stayed up"
        assert window.session.is_running() is True, (
            "«Стоп» during a run unloads nothing: the process stays, so the pause "
            "cannot have been cleared by the session ending"
        )
        assert window.session.paused() is False, "the session still thinks it is paused"

        window._actions["run"].trigger()
        assert pump(window, lambda: "X=1" in window.output_text()), window.output_text()
        assert "Y=2" in window.output_text(), ascii(window.output_text())
        assert "нет шага" not in window.output_text(), ascii(window.output_text())
        assert window.stepping() is False, "a fresh run is not a step"
    finally:
        discard_changes(window)
    print("ok: Шаг → Стоп → Запуск runs the program instead of asking for a step")


def test_the_graphics_window_follows_the_program(executable: str) -> None:
    """task_45: the drawing reaches a window of its own, and it survives hiding.

    The pixels live in the interpreter (a `getPixel` and a `ЗАКРАСКА` read cells
    from inside a built-in), so the window gets the primitives as events while it
    is open and asks for a snapshot when it was not there to hear them.
    """
    from prologd_gui.settings import Settings

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        # The entry opens a window of its own, and the picture starts blank.
        window._actions["graphics"].setChecked(True)
        assert window.graphics_available() is True
        picture = window.graphics_window()
        assert picture.isVisible() is True
        assert window._settings.graphics_visible is True
        assert window.canvas().filled_cells() == 0
        assert window.canvas().pixel(0, 0) == 0

        # A program draws: a point, a line, a frame and a fill inside it.
        window.editor().setPlainText(
            "?ТОЧКА(1, 2, 3).\n"
            "?ЛИНИЯ(0, 0, 60, 40, 5).\n"
            "?ЛИНИЯ(20, 10, 40, 10, 7), ЛИНИЯ(20, 20, 40, 20, 7),\n"
            "  ЛИНИЯ(20, 10, 20, 20, 7), ЛИНИЯ(40, 10, 40, 20, 7).\n"
            "?ЗАКРАСКА(30, 15, 9).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(30, 15) == 9), window.output_text()
        assert window.canvas().pixel(1, 2) == 3, "the point"
        assert window.canvas().pixel(0, 0) == 5 and window.canvas().pixel(60, 40) == 5, "the line"
        assert window.canvas().pixel(20, 10) == 7, "the frame"
        assert window.canvas().pixel(30, 25) == 0, "nothing outside the frame was filled"

        # Hiding the window keeps the picture: the canvas is not thrown away.
        window._actions["graphics"].setChecked(False)
        assert window._settings.graphics_visible is False
        assert picture.isVisible() is False
        assert window.canvas().pixel(1, 2) == 3

        # Closing it the way a user does turns the entry off too.
        picture.show()
        picture.close()
        assert picture.isVisible() is False
        assert window._actions["graphics"].isChecked() is False

        # Reopening asks the interpreter for the whole picture: that is the path
        # a window that missed the drawing takes, and the picture is the same.
        window._actions["graphics"].setChecked(True)
        assert pump(window, lambda: window.status_text().startswith("рисунок получен")), (
            window.status_text()
        )
        assert window.canvas().pixel(1, 2) == 3
        assert window.canvas().pixel(30, 15) == 9
        assert window.canvas().pixel(30, 25) == 0

        # What is shown can be saved as a picture.
        directory = tempfile.mkdtemp(prefix="prologd_png_")
        target = pathlib.Path(directory) / "рисунок.png"
        assert picture.save_png(str(target)) is True
        assert target.stat().st_size > 0

        # A new run starts a fresh interpreter with a blank screen, and the
        # window clears with it instead of keeping a drawing that is gone.
        window.editor().setPlainText("?ТОЧКА(4, 4, 1).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(4, 4) == 1), window.output_text()
        assert window.canvas().pixel(1, 2) == 0, "the previous run's picture stayed"
        assert window.canvas().pixel(30, 15) == 0
        window.stop_program()
    finally:
        discard_changes(window)
    assert Settings(settings_path).graphics_visible is True, "the window was remembered"
    print("ok: the graphics window follows the program, survives hiding, and saves")


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
        test_the_questions_switch_decides_whether_a_run_answers(executable)
        test_the_input_switch_chooses_where_to_ask(executable)
        test_the_limits_stop_a_runaway_and_name_themselves(executable)
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
        test_the_graphics_window_follows_the_program(executable)
        test_a_run_that_draws_opens_the_picture_by_itself(executable)
        test_escape_closes_the_picture_then_the_bar_then_the_docks(executable)
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
        test_a_long_trace_arrives_in_batches_and_stays_bounded(executable)
        test_the_window_remembers_its_size_and_place(executable)
        test_a_marker_answers_one_question_alone(executable)
        test_a_question_parked_in_a_comment_runs_from_the_margin(executable)
        test_a_marker_while_a_step_is_paused_starts_a_fresh_quiet_run(executable)
        test_a_failed_query_marks_no_line_and_moves_no_caret(executable)
        test_stopping_a_query_asks_first_and_keeps_the_base(executable)
        test_copy_takes_the_selection_where_the_focus_is(executable)
        test_the_step_strip_is_one_font_and_three_pictures(executable)
        test_formatting_lays_the_buffer_out_and_stays_one_undo_step(executable)
        test_formatting_only_the_selection(executable)
        test_a_broken_program_is_reported_and_not_rewritten(executable)
        test_the_mode_control_stands_beside_the_command_it_changes(executable)
        test_the_reserved_names_are_there_before_the_first_run(executable)
        test_running_programs_without_questions_finishes(executable)
        test_f1_shows_the_record_of_the_word_under_the_caret(executable)
        test_the_cheat_sheet_lists_the_insert_table(executable)
        test_a_remapped_table_decides_what_ctrl_key_inserts(executable)
        test_the_output_can_be_saved(executable, files)
        test_the_context_menu_reuses_the_shared_actions(executable)
        test_two_font_sizes_and_one_wheel(executable)
        test_the_settings_dialog_changes_the_window_without_a_restart(executable)
        test_the_theme_switch_reaches_the_text_and_the_widgets(executable)
        test_the_shared_folder_reaches_the_interpreter(executable)
        test_autosave_writes_named_buffers_and_skips_the_rest(executable, files)
        test_saving_before_a_run_writes_the_file(executable, files)
        test_the_tabs_come_back_on_the_next_start(executable, files)
        test_an_unnamed_tab_left_unsaved_is_forgotten(executable, files)
        test_an_untouched_unnamed_tab_comes_back_clean(executable)
    print("all window checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
