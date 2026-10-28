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
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_session import find_executable, pump  # noqa: E402
from test_paths import make_package, packaged  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication, QTextCursor
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - main() reports it
    QApplication = None  # type: ignore[assignment]

#: The repository's standard library — what the welcome program imports.
STDLIB = pathlib.Path(__file__).resolve().parents[3] / "stdlib"

EXAMPLE = pathlib.Path(__file__).resolve().parents[3] / "examples" / "problems" / "factorial.pld"
ANSWER = "Ф=720\n"

#: task_36's files: the lesson whose `?сумма(5, Сумма).` must answer `Сумма=15`
#: alone, and the lesson with a question parked in a comment (`% ?дед(иван,
#: анна).`) that only runs if someone asks for one.
LESSON_02 = pathlib.Path(__file__).resolve().parents[3] / "examples" / "lessons" / "lesson_02.pld"
LESSON_04 = pathlib.Path(__file__).resolve().parents[3] / "examples" / "lessons" / "lesson_04.pld"

#: A failing ground query: the interpreter answers `НЕТ` itself, so the window
#: must not answer a second time.  Kept as the user wrote it.
PRIMES = """\
делится(Х,У):-УМНОЖЕНИЕ(У,М,0,Х).
проверка(Х,1):-!.
проверка(Х,У):-НЕ(делится(Х,У)),проверка(Х,#У-1#).
простое(1):-!.
простое(Х):-проверка(Х,#Х//2#).

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


def make_window(executable: str, *, ready: bool = True, settings=None):
    """A window whose preferences live in a throw-away file.

    Without this the window would read (and, on zoom, write) the settings of the
    person running the tests.  `settings` of its own is the exception: a check that
    wants two windows over *one* file passes the same store to both.

    `ready=True` starts the interpreter the way the first run does, because most
    checks are about what happens afterwards — the reserved names, the
    highlighting, the output.  A window the user has only *opened* has nothing
    running at all, and `ready=False` is that window.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    if settings is None:
        directory = tempfile.TemporaryDirectory(prefix="prologd_gui_test_")
        _SETTINGS_DIRECTORIES.append(directory)
        settings = Settings(pathlib.Path(directory.name) / "gui.ini")
    window = MainWindow(executable, [], settings)
    if ready:
        window.session.start()
        assert pump(window, lambda: bool(window.session.keywords)), "the session never said ready"
    return window


def copied_build(directory: pathlib.Path, executable: str) -> pathlib.Path:
    """A folder with a copy of the interpreter the suite was pointed at.

    The window looks for the interpreter *beside* the binary of the launch, so the
    check of `--exe` needs one in a folder of its own.  A copy, not the build tree
    itself: `--exe` is the thing being checked, and a test must not run the tree it
    was built from.
    """
    folder = directory / "движок"
    folder.mkdir(exist_ok=True)
    name = pathlib.Path(executable).name
    shutil.copy2(executable, folder / name)
    return folder


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
    from PySide6.QtCore import QMimeData, QPointF, QUrl, Qt
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
                QPointF(4.0, 4.0),
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
        assert target.name in window.system_text(), "the file that failed is named"
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


def test_a_two_line_answer_answers_two_reads(executable: str) -> None:
    """task_54: an answer is a piece of the input stream, not one line.

    The interpreter splits what the console hands over, so two `ВВОДСТР` are
    answered by one `Ctrl+Enter` and the window is asked once.  The dialog is
    armed to fail loudly: a second question must not reach it.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("?ТИХО,ВВОДСТР(А),ВВОДСТР(Б),ВЫВОД(А,\"|\",Б),ПС.\n")
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or "нет"

        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()
        assert window._input_console.kind() == "line", window._input_console.kind()
        assert window._input_console._text.placeholderText() == "Строки — Ctrl+Enter"

        window._input_console._text.setPlainText("первая\nвторая")
        window._input_console.send()  # the same call `Ctrl+Enter` makes
        wait_for_result(window)

        assert asked == [], "the second read went to the dialog: the answer was split"
        assert window._input_console.waiting() is False, "the console stayed armed"
        assert "первая|вторая" in window.output_text(), ascii(window.output_text())
        print("ok: one answer, two lines, two reads and one question")
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
    """With the panel hidden there is nowhere to put a console, so a box asks.

    A run shows the panel by itself (part 92), so the panel is hidden *in the middle
    of* the run here — which is what pressing `F4` while a program waits does.  The
    first question still has its console (armed, and answered through it); the
    second one finds the panel gone and comes as a box.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText(READS_TWO)
        asked: list[str] = []

        def answer(kind: str) -> str:
            asked.append(kind)
            return "9"

        window._ask_input = answer
        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()

        # `F4` in the middle of the run: the panel goes, and the *next* question has
        # nowhere to put the console.  The one that is already armed still answers.
        window._actions["output"].setChecked(False)
        window._input_console._line.setText("9")
        window._input_console.send()
        wait_for_result(window)

        assert asked == ["token"], asked
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


def test_the_console_stays_one_field_high(executable: str) -> None:
    """task_50: the console under the goal line is a strip, never stretched.

    The editor column has room to spare, and the console used to take it all —
    its one field floating in the middle of a tall empty strip.  A fixed vertical
    size policy keeps it the height of one field.
    """
    from PySide6.QtWidgets import QApplication, QSizePolicy

    window = empty_window(executable)
    try:
        window.show()
        QApplication.processEvents()
        window.editor().setPlainText("?ВВОДЦЕЛ(А),ВЫВОД(А),ПС.\n")
        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()
        assert (
            window._input_console.sizePolicy().verticalPolicy()
            == QSizePolicy.Policy.Fixed
        ), "the console can still be stretched by the column"
        assert window._input_console.height() <= window._input_console.sizeHint().height() + 4, (
            window._input_console.height(),
            window._input_console.sizeHint().height(),
        )
        window._input_console._line.setText("5")
        window._input_console.send()
        wait_for_result(window)
    finally:
        discard_changes(window)
    print("ok: the console is one field high, never stretched by the column")


def test_a_request_keeps_the_panel_on_the_output(executable: str) -> None:
    """task_50: the per-request console is under the goal line, and the panel
    stays on Вывод — a question never pulls the eye off the output it belongs to."""
    window = empty_window(executable)
    try:
        window.editor().setPlainText("?ВВОДЦЕЛ(А),ВЫВОД(А),ПС.\n")
        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()

        # The question appears in the editor column, not in the Ввод tab — and
        # the panel stays where the run left it (Вывод).
        assert window._input_console.parent() is not window._input_tab, (
            "the console stayed inside the Ввод tab"
        )
        assert (
            window.panel_tabs().currentIndex()
            == window.panel_tabs().indexOf(window._output)
        ), "a request moved the panel off the Вывод tab"

        window._input_console._line.setText("5")
        window._input_console.send()
        wait_for_result(window)
        assert printed_lines(window) == ["5", "А=5"], printed_lines(window)
    finally:
        discard_changes(window)
    print("ok: a request shows the console under the goal line and leaves the panel on Вывод")


def test_the_panel_has_five_tabs_with_counts(executable: str) -> None:
    """task_50: Проблемы, Вывод, Система, Ввод and, since task_59, Таблица.

    The «Проблемы» word is painted by the state of the run: the ordinary colour
    with nothing, orange with warnings only, red once an error has arrived.  The
    «Ввод» count follows the prepared lines as they are typed, blank lines
    dropped; the «Таблица» count is the number of solutions in it.
    """
    window = empty_window(executable)
    bar = window.panel_tabs().tabBar()
    try:
        assert window.panel_tabs().count() == 5, window.panel_tabs().count()
        titles = [bar.tabText(i) for i in range(5)]
        assert titles == ["Проблемы:0", "Вывод:0", "Система:0", "Ввод:0", "Таблица:0"], titles
        problems = window.panel_tabs().indexOf(window._problems)
        assert not bar.tabTextColor(problems).isValid(), "no problems, no colour"

        # The «Ввод» count follows the prepared lines as they are typed.
        window.input_pane().setPlainText("7\n\n9\n")
        assert bar.tabText(window.panel_tabs().indexOf(window._input_tab)) == "Ввод:2", (
            bar.tabText(window.panel_tabs().indexOf(window._input_tab))
        )

        # A warning alone is orange, an error turns it red — and each diagnostic
        # brings the «Проблемы» tab up (task_50's focus rule).
        window._on_failed("runtime", "warning", "совет", None)
        window._flush_output()
        assert window.panel_tabs().currentIndex() == problems, "a warning did not focus Проблемы"
        assert bar.tabText(problems) == "Проблемы:1", bar.tabText(problems)
        assert bar.tabTextColor(problems).name() == window._settings.palette.warning

        window._on_failed("runtime", "error", "сбой", None)
        window._flush_output()
        assert bar.tabText(problems) == "Проблемы:2", bar.tabText(problems)
        assert bar.tabTextColor(problems).name() == window._settings.palette.error

        # «Очистить вывод» empties the problems and their colour with them.
        window.clear_output()
        assert bar.tabText(problems) == "Проблемы:0", bar.tabText(problems)
        assert not bar.tabTextColor(problems).isValid(), "the colour outlived the clear"
    finally:
        discard_changes(window)
    print("ok: five tabs, titled with counts, and «Проблемы» painted by its state")


def test_a_run_focuses_the_output_and_the_system_notes_the_time(executable: str) -> None:
    """task_50: a run brings up Вывод, and Система says how long the load took."""
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(1).\n")
        window.run_program()
        assert (
            window.panel_tabs().currentIndex()
            == window.panel_tabs().indexOf(window._output)
        ), "a run did not show the Вывод tab"
        assert pump(window, lambda: "решени" in window.status_text()), window.status_text()
        assert pump(window, lambda: "база знаний загружена (" in window.system_text()), (
            ascii(window.system_text())
        )
    finally:
        discard_changes(window)
    print("ok: a run shows the output, and the system pane times the load")


def test_cancelling_input_stops_the_run(executable: str) -> None:
    """«Отмена» stops the program and the run asks nothing else.

    The goal field is hidden, which is the third reason a question comes as a box
    (part 92): with that panel gone there is nowhere to put the console — and a run
    does not show it back, since only the output panel is revealed by a run.
    """
    window = empty_window(executable)
    try:
        window._actions["query"].setChecked(False)  # the dialog needs a reason to be used
        assert window.query_visible() is False
        window.editor().setPlainText(READS_TWO)
        asked: list[str] = []
        window._ask_input = lambda kind: asked.append(kind) or None

        window.run_program()
        assert pump(window, lambda: not window.session.is_running()), "the run was not stopped"

        assert len(asked) == 1, f"asked again after the cancellation: {asked}"
        assert "ввод отменён" in window.system_text(), ascii(window.system_text())
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
        program = EXAMPLE.read_text(encoding="utf-8").replace("(6, Ф)", "(5, Ф)")
        # The example's second query (20!) is dropped before running: `720` is a
        # piece of `2432902008176640000`, and the check below looks for it.
        program = program.replace("?факториал(20, Ф).", "%?факториал(20, Ф).")
        window.editor().setPlainText(program)
        window.run_program()
        assert pump(window, lambda: "Ф=120" in window.output_text()), ascii(window.output_text())
        assert "720" not in window.output_text(), "the other tab's program ran"
        print("ok: a run uses the current tab, not the first one")
    finally:
        discard_changes(window)


def test_the_output_panel_moves_and_hides(executable: str) -> None:
    """`Ctrl+F4` moves the output panel, `F4` hides it, and both are remembered.

    The panel is *one* widget — a tab widget with Проблемы, Вывод, Система and
    Ввод — inside a single splitter whose **orientation** is what changes: side
    by side when it is on the right, stacked when it is at the bottom.  The turn
    must not hide it and must not leave a pane dragged away to nothing.
    """
    from PySide6.QtCore import Qt

    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    window = empty_window(executable)
    path = window._settings.path
    try:
        assert window.output_position() == "bottom", "the panel defaults to the bottom"
        assert window._panel_splitter.orientation() == Qt.Orientation.Vertical
        assert window.output_visible() is True
        assert window._actions["output"].isChecked() is True

        window._actions["split_orientation"].trigger()
        assert window.output_position() == "right"
        assert window._panel_splitter.orientation() == Qt.Orientation.Horizontal
        assert window._panel_splitter.widget(1) is window._panel_tabs, "the editor moved"
        assert window._input_pane.parent() is window._input_tab, "the input queue did not travel"
        assert window._panel_tabs.isHidden() is False, "the turn hid the panel"

        # `F4`: checked means shown, and a hidden panel is *hidden*, not vanished.
        window._actions["output"].setChecked(False)
        assert window.output_visible() is False
        assert window._panel_tabs.isHidden() is True
        window._actions["output"].setChecked(True)
        assert window.output_visible() is True

        # A pane can be dragged small, but never to nothing.
        assert window._panel_splitter.childrenCollapsible() is False
        window._panel_splitter.setSizes([0, 0])
        assert all(size > 0 for size in window._panel_splitter.sizes()), window._panel_splitter.sizes()
    finally:
        discard_changes(window)

    stored = Settings(path)
    assert stored.output_position == "right", "the side of the panel was not remembered"
    assert len(stored.panel_sizes) == 2 and all(size > 0 for size in stored.panel_sizes)
    assert stored.output_visible is True

    reopened = MainWindow(executable, [], stored)
    try:
        assert reopened.output_position() == "right", "the panel did not come back"
        assert reopened._panel_splitter.orientation() == Qt.Orientation.Horizontal
        assert reopened._actions["output"].isChecked() is True
        print("ok: the panel moves with Ctrl+F4, hides with F4, and comes back")
    finally:
        discard_changes(reopened)


def test_the_goal_field_hides_and_a_run_shows_the_output_panel(executable: str) -> None:
    """part 92: «Вид → Панель ввода цели», and a run brings the output panel back.

    The goal field and the console under it are one panel, so the new switch hides
    both — and that panel is a *strip*: a plain `QWidget` has no vertical wish of its
    own, so it shared the column's spare height with the editor and the goal line
    floated in the middle of a tall empty panel (the defect the console had, cured
    the same way — part 93).  The output panel is the other half of the request: a
    run has output to show, so a panel the user hid appears for it — while the
    *preference* stays where the user put it and only their own act writes it (the
    rule the followed font size already follows, task_58).
    """
    from PySide6.QtWidgets import QApplication, QSizePolicy

    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    window = empty_window(executable)
    path = window._settings.path
    try:
        window.show()
        QApplication.processEvents()
        assert window.query_visible() is True, "the goal field is shown out of the box"
        assert window._actions["query"].isChecked() is True
        assert window._input_console.parent() is window.query_panel(), "one panel, two parts"

        # The strip takes the height of its contents and never the column's spare
        # room: the line alone when nothing is asked, the line and the console while
        # a question waits.
        panel = window.query_panel()
        assert (
            panel.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum
        ), "the goal panel can still be stretched by the column"
        assert panel.height() <= panel.sizeHint().height() + 4, (
            panel.height(),
            panel.sizeHint().height(),
        )

        # The switch itself: hidden means hidden, and it is stored.
        window._actions["query"].setChecked(False)
        assert window.query_visible() is False
        assert window.query_panel().isHidden() is True
        assert window._settings.query_visible is False, "the switch was not stored"
        window._actions["query"].setChecked(True)
        assert window.query_panel().isHidden() is False
        assert window._settings.query_visible is True

        # A run with the output panel hidden: it comes back for the run, the key is
        # left where the user put it, and the goal field stays as it was.
        window.editor().setPlainText("факт(1).\n")
        window._actions["query"].setChecked(False)
        window._actions["output"].setChecked(False)
        assert window._panel_tabs.isHidden() is True
        window.run_program()
        assert pump(window, lambda: not window._panel_tabs.isHidden()), (
            "the run left the panel hidden"
        )
        assert window._settings.output_visible is False, "the run wrote the preference"
        assert window.query_panel().isHidden() is True, "the run showed the goal field too"

        # A goal typed into the line asks into the output panel the same way.
        window._actions["output"].setChecked(False)
        window._query_line.setText("?факт(1).")
        window._query_line.returnPressed.emit()
        assert pump(window, lambda: not window._panel_tabs.isHidden()), (
            "the goal left the panel hidden"
        )
        assert window._settings.output_visible is False, "asking wrote the preference"
    finally:
        discard_changes(window)

    stored = Settings(path)
    assert stored.query_visible is False, "the goal field's state was not remembered"
    reopened = MainWindow(executable, [], stored)
    try:
        assert reopened.query_visible() is False, "the goal field did not stay hidden"
        assert reopened._actions["query"].isChecked() is False
    finally:
        discard_changes(reopened)
    print("ok: the goal field hides from the menu, and a run shows the hidden output panel")


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
        # task_58: the box names the system, the shell and the interpreter that
        # answers, and lists the people who wrote the previous implementation with
        # their roles.  The owner rewrote the wording on 2026-10-24: a role is
        # followed by a *tab*, which keeps the column straight where a run of
        # spaces does not (a proportional font is what broke the earlier version).
        assert text.startswith("Пролог-Д"), ascii(text)
        assert "учебная система" in text, ascii(text)
        assert "Графическая оболочка (PySide6)" in text, ascii(text)
        assert "Интерпретатор: " in text, ascii(text)
        credits = [
            (role, name.rstrip(",."))
            for role, name in (
                line.split("\t")
                for line in text.splitlines()
                if "\t" in line and line.split("\t")[0] in ("идеолог", "прораб", "кодер")
            )
        ]
        assert len(credits) == 5, credits
        for role, name in credits:
            assert name, credits
            assert role in ("идеолог", "прораб", "кодер"), credits
        listed = [name for _, name in credits]
        for name in (
            "Григорьев Сергей Георгиевич",
            "Алексеев Михаил Николаевич",
            "Балдин Виктор Михайлович",
            "Воронин Алексей Вячеславович",
            "Ахмеров Данил Адисонович",
        ):
            assert name in listed, (name, credits)
        assert "Панелей редактора" not in text and "Настройки:" not in text, ascii(text)
        print("ok: the recent menu and the window carry their pictures")
    finally:
        discard_changes(window)


def stop_picture(window) -> str | None:
    """Which picture «Остановить» carries, by the name of the asset it was made from.

    `assets.icon` keeps one `QIcon` per name, so the cache key identifies the file.
    """
    from prologd_gui import assets

    shown = window._actions["stop"].icon().cacheKey()
    for name in ("execution-abort", "execution-stop"):
        picture = assets.icon(name)
        if picture is not None and picture.cacheKey() == shown:
            return name
    return None


def test_the_run_state_drives_the_buttons(executable: str) -> None:
    """Three states: dark, red while a run is in flight, blue while the base waits.

    «Остановить» has two meanings and the picture says which one the click will
    perform (part 141): a run in flight is the red octagon — that click breaks a
    computation; an interpreter idle with its base is the blue stop — that click
    unloads the base, the one act that is immediate, and the only way out of a
    program that has loaded and is waiting.  A window the user has only opened has
    nothing to stop at all, and carries the greyed red octagon.
    """
    window = make_window(executable, ready=False)
    try:
        assert window.session.is_running() is False, "a new window starts no interpreter"
        assert window._actions["run"].isEnabled() is True
        assert window._actions["stop"].isEnabled() is False
        assert stop_picture(window) == "execution-abort", stop_picture(window)
        assert "остановлен" in window._details.text(), window._details.text()

        # The first run starts the interpreter *and* the computation: red.
        window.open_path(str(EXAMPLE))
        window._actions["run"].trigger()
        assert window._actions["run"].isEnabled() is False, "a run is in flight"
        assert window._actions["stop"].isEnabled() is True
        assert stop_picture(window) == "execution-abort", stop_picture(window)
        assert pump(window, lambda: "решение" in window.status_text()), window.status_text()

        # The answer frees `Запустить`; «Остановить» stays lit, now in blue: the base
        # is loaded and the click would unload it.
        assert window._actions["run"].isEnabled() is True, "the answer frees the button"
        assert window._actions["stop"].isEnabled() is True, "the base can be unloaded"
        assert stop_picture(window) == "execution-stop", stop_picture(window)
        assert "база знаний загружена" in window._details.text(), window._details.text()

        # The next start loads the base again, and the picture turns red with it.
        window._actions["run"].trigger()
        assert window._actions["stop"].isEnabled() is True, "a new run lights it again"
        assert stop_picture(window) == "execution-abort", stop_picture(window)

        # Stopping a computation in flight is asked politely first and ends on the
        # deadline when nobody is reading (a load runs to its end before the request
        # can be read — see the window test below for the case where the request *is*
        # read: a read waiting for input).
        window._actions["stop"].trigger()
        assert pump(window, lambda: "--- остановлено ---" in window.system_text()), (
            window.system_text()
        )
        print("ok: run and stop follow the three states of the interpreter")
    finally:
        discard_changes(window)


def test_stopping_a_query_asks_first_and_keeps_the_base(executable: str) -> None:
    """«Остановить» asks before it ends the process (task_28, the Stop block).

    The solver reads the interrupt at every step of its loop, so a query that
    *waits* — for input, the clearest case — ends on the request: the pane says
    `--- остановлено ---`, and the interpreter is left idle with its knowledge
    base.  That state leaves the button dark (task_87): there is no run left to
    stop, and the base is loaded again by the next start.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("?ВВОДСТР(С).\n")
        window.run_program()
        assert pump(window, lambda: window._input_console.waiting()), window.status_text()
        assert window.session.is_running()

        window._actions["stop"].trigger()
        assert pump(window, lambda: "--- остановлено ---" in window.system_text()), (
            window.system_text()
        )
        assert window.session.is_running() is True, "the session survives a polite stop"
        assert "база знаний загружена" in window._details.text(), window._details.text()
        assert window._input_console.waiting() is False, "the pending request is dismissed"

        # The run is over, and «Остановить» stays lit — in blue now: the base is
        # loaded, and that click unloads it (part 141).  That is the way out of a
        # program that has loaded and waits for input.
        assert window._actions["stop"].isEnabled() is True, "the base can be unloaded"
        assert stop_picture(window) == "execution-stop", stop_picture(window)
        window._actions["stop"].trigger()
        assert pump(window, lambda: "база знаний выгружена" in window.status_text()), (
            window.status_text()
        )
        assert window.session.is_running() is False, "the base went with the process"
        assert window._actions["stop"].isEnabled() is False, "nothing left to stop"
    finally:
        discard_changes(window)
    print("ok: «Остановить» asks first and leaves the base loaded")


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


def test_the_output_arrives_while_the_program_runs(executable: str) -> None:
    """task_49: a countdown counts — it does not arrive as one block at the end.

    `ВЫВОД`, `ЖДИ`, three times: the first line has to be in the pane *while* the
    program is still sleeping, and the third must not be there yet.  That is what
    the interpreter's output-line hook and the per-line `output` events are for;
    before them a lesson's animation was one jump at the end of the run.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText(
            '?ВЫВОД("one"), ПС, ЖДИ(400), ВЫВОД("two"), ПС, ЖДИ(400), ВЫВОД("three"), ПС.\n'
        )
        window._actions["run"].trigger()
        assert pump(window, lambda: "one" in window.output_text()), window.output_text()
        assert "three" not in window.output_text(), (
            "the last line was there before the program reached it: "
            + ascii(window.output_text())
        )
        assert window._actions["run"].isEnabled() is False, "the run is still going"
        assert pump(window, lambda: "three" in window.output_text()), window.output_text()
        # The run is over when `Запустить` comes back, whatever the last answer was
        # called («решение найдено» for a program whose query answers).
        assert pump(window, lambda: window._actions["run"].isEnabled()), window.status_text()
    finally:
        discard_changes(window)
    print("ok: the output arrives line by line while the program is still running")


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


def test_the_picture_takes_the_canvas_the_program_names(executable: str) -> None:
    """ADR-035: `:- ХОЛСТ(Высота, Ширина).` beats the size in the settings.

    The window names its screen before a run and draws on that canvas, but a
    program may name its own — and only the interpreter knows it.  The size rides
    with the picture, and the first primitive of a run asks for one, so the canvas
    becomes the program's size and the picture is not a corner of a bigger sheet.
    """
    window = empty_window(executable)
    try:
        window._settings.screen_size = (600, 600)
        window.editor().setPlainText(":- ХОЛСТ(30, 40).\n?ТОЧКА(4, 5, 7).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(4, 5) == 7), window.output_text()
        # The size is known before the first primitive — the `screen` event carries it
        # (protocol 14) — so the very first picture is laid out at its own size.
        assert (window.canvas().width, window.canvas().height) == (40, 30), (
            f"холст программы 40×30, а окно нарисовало "
            f"{window.canvas().width}×{window.canvas().height}"
        )
        window.stop_program()
    finally:
        discard_changes(window)
    print("ok: the picture takes the canvas the program names, not the setting")


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


def test_the_run_switches_are_in_the_menu_and_in_the_settings(executable: str) -> None:
    """task_58: «Выполнять вопросы» and «Печатать вопросы» are one switch in two
    places.

    The menu entry and the settings dialog read and write the same setting
    (`execution/run_questions`, `execution/print_questions`), so neither can say
    something the other does not: the menu writes the file, and `_sync_actions`
    puts the setting back into the check mark.
    """
    from prologd_gui import actions

    window = empty_window(executable)
    try:
        entries = dict(actions.MENUS)["Выполнение"]
        assert "run_questions" in entries and "print_questions" in entries, entries
        assert "save_before_run" not in entries, "the entry left the menu in task_58"
        assert dict(actions.MENUS)["Справка"][:2] == ("reference", "help_doc"), "Справка"

        run_questions = window._actions["run_questions"]
        print_questions = window._actions["print_questions"]
        assert run_questions.isCheckable() and print_questions.isCheckable()
        assert run_questions.isChecked() is True, "«Выполнять вопросы» is on by default"
        assert print_questions.isChecked() is False

        run_questions.setChecked(False)
        assert window._settings.run_questions is False, "the menu did not write the setting"
        print_questions.setChecked(True)
        assert window._settings.print_questions is True

        window._settings.run_questions = True
        window._sync_actions()
        assert run_questions.isChecked() is True, "the setting did not reach the menu"

        # «Сохранять перед запуском» is a setting without a menu entry now: it is
        # changed in the dialog, and it still works.
        window._settings.save_before_run = True
        assert window._settings.save_before_run is True
        print("ok: the two run switches are one setting each, in the menu and in the dialog")
    finally:
        discard_changes(window)


# -- the answer table (task_59) --------------------------------------------
#: Two facts and a question about both: one goal, two solutions.  Only a *single*
#: goal is tabulated — a whole run answers all of its questions into one stream of
#: text where nothing tells the answers apart (`answers.py` has the reason).
TWO_STUDENTS = "студент(вова, корчагин).\nстудент(данил, ахмеров).\n?студент(X, Y).\n"


def wait_for_the_run(window) -> None:
    """Waits until the interpreter is not computing any more.

    The status bar is not enough for a *second* question in one test: it keeps the
    word of the previous answer («решение найдено»), so the wait would return the
    moment the question is sent — the check would then read a table that is not
    there yet.  `_busy` is the state the window keeps for exactly this.
    """
    assert pump(window, lambda: not window._busy), "the run never finished"


def ask_from_the_margin(window, statement: str) -> None:
    """Clicks a question's margin marker and waits for its answer."""
    window.editor().queryRequested.emit(statement)
    wait_for_the_run(window)


def test_the_answer_table_switch_is_in_the_menu_and_in_the_settings(executable: str) -> None:
    """task_59: «Формировать таблицу» is one switch in two places, on by default.

    Like the two switches of a run (task_58), the menu entry and the settings row
    read and write the same key (`execution/answer_table`), and the entry stands
    above «Выполнять вопросы при запуске» — the order the user asked for.  On by
    default since 2026-10-03: a single goal's answer is read as a table unless the
    reader says otherwise (`ai/status.md`, part 73).
    """
    from prologd_gui import actions, settings as settings_module

    window = empty_window(executable)
    try:
        entries = dict(actions.MENUS)["Выполнение"]
        assert "answer_table" in entries, entries
        assert entries.index("answer_table") < entries.index("run_questions"), entries
        assert settings_module.ANSWER_TABLE == "execution/answer_table"

        switch = window._actions["answer_table"]
        assert switch.isCheckable() is True
        assert switch.isChecked() is True, "on by default: one goal is read as a table"
        assert window._settings.answer_table is True

        switch.setChecked(False)
        assert window._settings.answer_table is False, "the menu did not write the setting"
        window._settings.answer_table = True
        window._sync_actions()
        assert switch.isChecked() is True, "the setting did not reach the menu"
        print("ok: «Формировать таблицу» is one setting, in the menu and in the dialog")
    finally:
        discard_changes(window)


def test_a_marker_builds_the_answer_table(executable: str) -> None:
    """lesson_04's `?сумма(5, Сумма).` answers `Сумма=15`: one column, one row.

    The text answer stays in «Выводе» — the table is an addition, not a
    replacement — and the panel moves to the «Таблица» tab, because a table is
    what the switch was turned on for.
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        assert window.open_path(str(LESSON_04))
        view = window.editor()
        line = next(
            number
            for number, content in enumerate(view.toPlainText().splitlines(), 1)
            if content.strip() == "?сумма(5, Сумма)."
        )
        statement = view.query_statements().get(line)
        assert statement == "?сумма(5, Сумма).", (line, statement)

        ask_from_the_margin(window, statement)
        assert printed_lines(window) == ["Сумма=15"], ascii(window.output_text())
        assert window._table.column_titles() == ["Сумма"], window._table.column_titles()
        assert window._table.cells() == [["15"]], window._table.cells()
        bar = window.panel_tabs().tabBar()
        index = window.panel_tabs().indexOf(window._table)
        assert bar.tabText(index) == "Таблица:1", bar.tabText(index)
        assert window.panel_tabs().currentIndex() == index, "the table was not brought up"
    finally:
        discard_changes(window)
    print("ok: a question's answer becomes a table of its variables")


def test_the_table_separates_two_solutions(executable: str) -> None:
    """The user's example: two facts answer as two rows.

    In the text — `X=вова`, `Y=корчагин`, `X=данил`, `Y=ахмеров` — the solutions
    are told apart only by the name that repeats; the table says it in columns and
    rows, which is the whole point of the round.
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        window.editor().setPlainText(TWO_STUDENTS)
        ask_from_the_margin(window, "?студент(X, Y).")
        assert window._table.column_titles() == ["X", "Y"], window._table.column_titles()
        assert window._table.cells() == [
            ["вова", "корчагин"],
            ["данил", "ахмеров"],
        ], window._table.cells()
        assert window._table.solution_count() == 2
    finally:
        discard_changes(window)
    print("ok: two solutions of one goal are two rows of the table")


def test_the_table_shows_a_word_for_a_ground_query(executable: str) -> None:
    """`ДА`/`НЕТ`: a query without variables answers with a word, and a table
    needs a column — so the word gets one cell of its own, named «Ответ»."""
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        window.editor().setPlainText("факт(1).\n")
        ask_from_the_margin(window, "?факт(1).")
        assert window._table.column_titles() == ["Ответ"], window._table.column_titles()
        assert window._table.cells() == [["ДА"]], window._table.cells()

        ask_from_the_margin(window, "?факт(2).")
        assert window._table.cells() == [["НЕТ"]], window._table.cells()
    finally:
        discard_changes(window)
    print("ok: ДА and НЕТ are one cell, not an empty table")


def test_the_goal_line_builds_the_table_too(executable: str) -> None:
    """The other way to ask one goal: the query line under the editor.

    `F5` first, so the program is loaded and the file's own `?студент(X, Y).` has
    answered *before* the goal is typed — and that answer leaves no table behind:
    only a single goal is collected.
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        window.editor().setPlainText(TWO_STUDENTS)
        window.run_program()
        wait_for_the_run(window)
        assert window._table.cells() == [], "a whole run built a table"

        window._query_line.setText("?студент(X, Y).")
        window._run_query()
        wait_for_the_run(window)
        assert window._table.cells() == [
            ["вова", "корчагин"],
            ["данил", "ахмеров"],
        ], window._table.cells()
    finally:
        discard_changes(window)
    print("ok: a goal typed into the query line is tabulated the same way")


def test_the_table_is_not_built_when_it_is_switched_off(executable: str) -> None:
    """Switched off the answer stays text, and no tab moves (task_59, part 73).

    This is the *only* case left in which the table is not built: since 2026-10-03
    the switch starts **on**, so a reader who wants the plain text is the one who
    turns it off — and then nothing is collected at all (`_arm_answer_table`), the
    answer goes to «Вывод» as before, and the panel stays where it was.
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(False)
        assert window._settings.answer_table is False
        window.editor().setPlainText(TWO_STUDENTS)
        ask_from_the_margin(window, "?студент(X, Y).")
        assert "X=вова" in window.output_text(), ascii(window.output_text())
        assert window._table.cells() == [], window._table.cells()
        assert window._table.solution_count() == 0
        assert (
            window.panel_tabs().currentIndex()
            == window.panel_tabs().indexOf(window._output)
        ), "the panel moved off «Вывод» with the table switched off"
        bar = window.panel_tabs().tabBar()
        assert bar.tabText(window.panel_tabs().indexOf(window._table)) == "Таблица:0"
    finally:
        discard_changes(window)
    print("ok: with the switch off the answer stays text and no tab moves")


def test_a_diagnostic_keeps_the_panel_on_the_problems(executable: str) -> None:
    """A warning does not end the run, and it does not lose the panel either.

    The table is still built — the answer is there to read on its tab — but a
    diagnostic is what the user looks for after a run that said something about
    the program, so the table does not take the panel from «Проблемы».
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        # `мама(Лена, Таня).` is the porting trap: two warnings at load, and the
        # question still answers.
        window.editor().setPlainText(
            "студент(вова, корчагин).\nмама(Лена, Таня).\n?студент(X, Y).\n"
        )
        ask_from_the_margin(window, "?студент(X, Y).")
        assert window._table.cells() == [["вова", "корчагин"]], window._table.cells()
        assert window._warning_count == 2, window._warning_count
        assert (
            window.panel_tabs().currentIndex()
            == window.panel_tabs().indexOf(window._problems)
        ), "the table pushed the diagnostics aside"
    finally:
        discard_changes(window)
    print("ok: a diagnostic keeps the panel on «Проблемы», and the table is still built")


def test_a_new_run_empties_the_table(executable: str) -> None:
    """The table is a view of the last answer, not a history of answers.

    A new run starts with its own output, so it starts with an empty table — and
    «Очистить вывод», which clears the text the table was built from, clears it
    too (a table whose source is gone would be a lie).
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        window.editor().setPlainText(TWO_STUDENTS)
        ask_from_the_margin(window, "?студент(X, Y).")
        assert window._table.solution_count() == 2, window._table.cells()

        window.run_program()
        wait_for_the_run(window)
        assert window._table.cells() == [], "the previous answer outlived the run"

        ask_from_the_margin(window, "?студент(X, Y).")
        assert window._table.solution_count() == 2, window._table.cells()
        window.clear_output()
        assert window._table.cells() == [], "«Очистить вывод» left the table behind"
    finally:
        discard_changes(window)
    print("ok: a run and «Очистить вывод» empty the table with the text")


def test_the_table_follows_the_output_font(executable: str) -> None:
    """The table is read next to the log it came from, so it takes its size.

    A wheel over the table calls exactly this `set_font_size`, which is the path
    checked here: the pane reports `zoomChanged`, the window writes
    `output/font_size` and pushes the size into every pane — the table included.
    """
    window = empty_window(executable)
    try:
        assert window._table.font_size == window._output.font_size, "one size at the start"
        window.output().set_font_size(9)
        assert window._settings.output_font_size == 9.0
        assert window._table.font_size == 9.0, window._table.font_size

        window._settings.output_font_size = 13
        window._apply_output_font()
        assert window._table.font_size == 13.0, window._table.font_size
    finally:
        discard_changes(window)
    print("ok: the answer table takes the output's font size")


def test_copy_over_the_table_takes_the_cells(executable: str) -> None:
    """`Ctrl+C` over the table copies its cells, not the editor behind it.

    The command copies «from where the user is looking», and the table is a pane
    it did not know: without a case of its own it would have copied the editor's
    selection — text the user is not looking at (task_59).
    """
    window = empty_window(executable)
    try:
        window._actions["answer_table"].setChecked(True)
        window.editor().setPlainText(TWO_STUDENTS + "мусор(1).\n")
        window.editor().selectAll()
        ask_from_the_margin(window, "?студент(X, Y).")
        assert window._table.solution_count() == 2, window._table.cells()

        window.show()
        window._table.setFocus()
        QApplication.processEvents()
        assert window.focusWidget() is window._table, window.focusWidget()
        window._table.item(0, 0).setSelected(True)
        window._table.item(0, 1).setSelected(True)
        window._copy()
        copied = QApplication.clipboard().text()
        assert copied == "вова\tкорчагин", ascii(copied)

        # The whole table: rows separated by a newline, columns by a tab.
        window._table.selectAll()
        window._copy()
        copied = QApplication.clipboard().text()
        assert copied == "вова\tкорчагин\nданил\tахмеров", ascii(copied)
    finally:
        discard_changes(window)
    print("ok: Ctrl+C over the table copies the selected cells, tab-separated")


# -- asking a question: when the window sends it (task_60) ------------------
def test_a_clicked_question_is_asked_once_the_load_has_answered(executable: str) -> None:
    """The question goes out when the program has loaded, not together with it.

    `0 < 5 < 4` does not parse — chains are refused — and the line sits in the
    *file*, so the load reports it under the file's own name.  Asking at once, as
    the window used to, parsed the same line a second time as `<query>`: two
    diagnostics for one reason, and neither of them wrong.  Now the question waits
    for `loaded`, and a load that fails never gets asked (task_60).
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("?0 < 5 < 4.\n")
        window.editor().queryRequested.emit("?0 < 5 < 4.")
        wait_for_the_run(window)

        problems = window.problems_text()
        assert problems.count("*** parse:") == 1, ascii(problems)
        assert "Без имени:1:8" in problems, ascii(problems)
        assert "«<» — не цепочка" in problems, ascii(problems)
        assert "<query>" not in problems, "the same line was parsed a second time"
        assert window.editor().error_line() == 1, "the file's own line is not marked"
        assert "вопрос не выполнен" in window.system_text(), ascii(window.system_text())
        assert "НЕТ" not in window.output_text(), ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a clicked question waits for the load, so one bad line is reported once")


def test_a_question_is_not_asked_when_the_file_does_not_parse(executable: str) -> None:
    """A good question in a file with a syntax error is not asked at all.

    The loader parses the whole text before it adds anything, so a file that does
    not parse leaves an *empty* knowledge base — and the question was answered
    against it: «НЕТ», plus «не найдено: факт/1», which blamed the query for the
    file's error (task_60).
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("сломано(1.\nфакт(1).\n% ?факт(1).\n")
        window.editor().queryRequested.emit("?факт(1).")
        wait_for_the_run(window)

        assert "непарные скобки" in window.problems_text(), ascii(window.problems_text())
        assert "не найдено" not in window.problems_text(), ascii(window.problems_text())
        assert "НЕТ" not in window.output_text(), ascii(window.output_text())
        assert "вопрос не выполнен" in window.system_text(), ascii(window.system_text())
        assert window.editor().error_line() == 1, "the file's line is not marked"
    finally:
        discard_changes(window)
    print("ok: a question in a file that does not parse is dropped, and said so")


def test_a_parked_question_still_reports_its_own_parse_error(executable: str) -> None:
    """A question from a comment is not part of the text the parser saw.

    `% ?0 < 5 < 4.` is prose to the file's parser, so a clean load says nothing
    about it; the clicked statement is parsed on its own and reports itself once,
    as `<query>` — the two names exist so a front-end can tell «the error is in the
    file» from «the error is in the line I sent» (task_36).
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n% ?0 < 5 < 4.\n")
        window.editor().queryRequested.emit("?0 < 5 < 4.")
        wait_for_the_run(window)

        problems = window.problems_text()
        assert problems.count("*** parse:") == 1, ascii(problems)
        assert "<query>:1:8" in problems, ascii(problems)
        assert "Без имени" not in problems, "the clean file was blamed"
        assert window.output_text() == "", ascii(window.output_text())
    finally:
        discard_changes(window)
    print("ok: a parked question is parsed on its own, once, and named after the query")


def test_the_goal_line_loads_when_there_is_no_base(executable: str) -> None:
    """With nothing loaded, the goal line runs the program first (task_60).

    The program in the editor had never been run, so there was no base to ask: the
    answer used to be «НЕТ» and «не найдено: факт/1» — a fact about an empty
    interpreter rather than about the program.  Now the text is loaded quietly and
    the goal is asked afterwards, exactly as a click on a margin marker does.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n")
        window._query_line.setText("?факт(1).")
        window._run_query()
        wait_for_the_run(window)

        assert "ДА" in window.output_text(), ascii(window.output_text())
        assert "не найдено" not in window.problems_text(), ascii(window.problems_text())
        assert "--- база знаний загружена (" in window.system_text(), (
            ascii(window.system_text())
        )
    finally:
        discard_changes(window)
    print("ok: the goal line runs the program when there is nothing to ask")


def test_the_goal_line_does_not_reload_a_loaded_base(executable: str) -> None:
    """A goal asks the program that is *loaded*, not the text in the editor.

    One base, one load (the user's decision): reloading on every goal would be work
    for nothing, and the goal line is not a run.  So an edit changes nothing until
    the next `F5`, and the «загрузка базы знаний» line in «Системе» stays single.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n")
        window.run_program()
        wait_for_the_run(window)
        window.editor().setPlainText("факт(2).\n")

        window._query_line.setText("?факт(1).")
        window._run_query()
        wait_for_the_run(window)
        assert "ДА" in window.output_text(), ascii(window.output_text())

        window._query_line.setText("?факт(2).")
        window._run_query()
        wait_for_the_run(window)
        assert "НЕТ" in printed_lines(window), ascii(window.output_text())
        assert window.system_text().count("--- загрузка базы знаний ---") == 1, (
            ascii(window.system_text())
        )
    finally:
        discard_changes(window)
    print("ok: the goal line asks the loaded base and never reloads it")


def test_the_toolbar_reuses_the_actions(executable: str) -> None:
    from PySide6.QtWidgets import QWidgetAction

    from prologd_gui import actions

    window = empty_window(executable)
    try:
        toolbar = window._toolbar
        assert toolbar.iconSize().width() == 24, "icons are drawn at 24 px"
        shown = [entry.text() for entry in toolbar.actions() if not entry.isSeparator()]
        for key in ("new", "open", "save", "run", "stop", "comment"):
            assert actions.BY_KEY[key].title in shown, (key, shown)
        # task_58: «Очистить вывод» left the toolbar for the «Выполнение» menu, and
        # the size control left it too (see `test_two_font_sizes_and_one_wheel`).
        # The state control went with the naming modes (part 213), so the last entry
        # is «Настройки…» and the one empty-text entry is the formatter's mode
        # control, right after «Форматировать».
        labels = [entry.text() for entry in toolbar.actions() if not entry.isSeparator()]
        assert actions.BY_KEY["help_doc"].title not in labels, labels
        assert actions.BY_KEY["clear_output"].title not in labels, labels
        assert labels[-1] == actions.BY_KEY["settings"].title, labels
        widgets = [index for index, label in enumerate(labels) if not label]
        assert len(widgets) == 1, labels
        assert widgets[0] == labels.index(actions.BY_KEY["format"].title) + 1, labels
        # The only widget on the toolbar is the formatter's mode control: the state
        # control went with the naming modes (part 213).
        trailing = [entry.defaultWidget() for entry in toolbar.actions()
                    if isinstance(entry, QWidgetAction)]
        assert trailing == [window._format_action.defaultWidget()], trailing
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

    One number used to cover both panels.  The zoom commands and the wheel over the
    editor move the *editor's* size; the wheel over the output moves the output's,
    and the query line goes with the editor, because a goal is typed like a program
    rather than read like a log.  The toolbar kept a size box until task_58: the
    three commands and the wheel cover the everyday change, and an exact value is a
    row of the settings dialog.
    """
    window = empty_window(executable)
    try:
        from prologd_gui import settings as settings_module

        assert window.output().font_size == window.editor().font_size, "one size at the start"
        assert window._settings.font_size == window.editor().font_size

        for _ in range(9):
            window._actions["zoom_in"].trigger()
        assert window.editor().font_size == window._settings.font_size, "the setting lagged behind"
        assert window.output().font_size == window.editor().font_size
        assert window._query_line.font().pointSizeF() == window.editor().font_size, (
            "a goal is typed like a program"
        )
        size = window.editor().font_size
        window._actions["zoom_out"].trigger()
        assert window.editor().font_size == size - 1
        window._actions["zoom_reset"].trigger()
        assert window.editor().font_size == settings_module.DEFAULT_FONT_SIZE

        # A wheel over the output separates them for good.
        window.output().set_font_size(9)
        assert window._settings.output_font_size == 9.0
        assert window.input_pane().font_size == 9.0, "the queue belongs to the output side"
        window.editor().set_font_size(23)
        assert window.output().font_size == 9.0, "the output followed the editor again"
        assert window._settings.output_font_size == 9.0
        # The status bar is where the size is read now that the box is gone.
        window._actions["zoom_in"].trigger()
        assert window.editor().font_size == 24.0
        assert "24" in window.status_text(), window.status_text()
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

    # The row is typed the way a user types it; the session has to hear of it as a
    # real folder — the window hands the interpreter absolute paths (task_111), so
    # the comparison is by path and not by spelling.
    shared_import = os.path.abspath("C:/общие")

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
            assert shared_import in window.session._includes, window.session._includes
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
        assert window._actions["zoom_in"].isEnabled(), "the size commands are live"
        assert shared_import in window.session._includes, window.session._includes
        assert window.session is window._session
        print("ok: «Применить» reaches the editor, the output and the session at once")
    finally:
        discard_changes(window)


def test_the_shared_folder_reaches_the_interpreter(executable: str) -> None:
    """«Дополнительные каталоги ИМПОРТ» is what makes `ИМПОРТ` work everywhere.

    An untitled buffer has no folder of its own, so `ИМПОРТ("library.pld")`
    fails until a search folder is set — and works in every tab afterwards.
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
        assert pump(window, concluded), ascii(window.problems_text())
        assert "Не найден" in window.problems_text(), ascii(window.problems_text())

        window._settings.import_paths = [str(library)]
        window.apply_settings()
        assert str(library) in window._session._includes

        window.run_program()
        assert pump(window, concluded), ascii(window.output_text())
        assert window.status_text() == "выполнено", ascii(window.output_text())
        assert "Не найден" not in window.problems_text(), ascii(window.problems_text())
        print("ok: the import folder list is passed as -I, and an unnamed buffer imports from it")
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
            ("open_import", {"F12"}),
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


def test_every_declared_key_belongs_to_a_widget(executable: str) -> None:
    """A `QAction` fires its shortcut only while it belongs to a widget.

    `Ctrl+E` — «Показать в проводнике» (task_68) — was declared, connected, and did
    nothing: the action lives in the *tab* menu, which is built when it is opened,
    so the key had nowhere to fire while a click on the entry worked.  Exactly what
    made the defect quiet.  `_build_actions` now adds every action to the window as
    well, and this is the check that keeps it so.
    """
    window = empty_window(executable)
    try:
        owned = set(window.actions())
        missing = sorted(
            key
            for key, action in window._actions.items()
            if action.shortcuts() and action not in owned
        )
        assert not missing, f"actions that declare a key but belong to no widget: {missing}"
        assert window._actions["reveal"].shortcuts(), "the tab menu's command keeps its key"
        print(f"ok: all {len(owned)} window actions are reachable, keys included")
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
    """The colour of a line of a text pane, or of a row of the problems table.

    «Проблемы» is a table since part 88, so the colour of a diagnostic is the
    colour of its row — every cell of it — while the other panes keep a colour per
    line of their text.
    """
    from PySide6.QtGui import QTextCursor

    from prologd_gui import panels

    if isinstance(pane, panels.ProblemsPane):
        item = pane.item(block, 0)
        assert item is not None, f"no row {block}"
        return item.foreground().color().name()
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
        assert pump(window, lambda: "деление на ноль" in window.problems_text()), ascii(
            window.problems_text()
        )
        view = window.editor()
        assert view.error_line() == 1, view.error_line()
        assert view.textCursor().blockNumber() == 0, "the caret is not on the line"
        assert "ошибка: Без имени:1:1" in window.status_text(), window.status_text()
        assert "Без имени:1:1: деление на ноль" in window.problems_text(), ascii(
            window.problems_text()
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
        assert pump(window, lambda: "непарные скобки" in window.problems_text()), ascii(
            window.problems_text()
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
        lines = window.problems_text().splitlines()
        amber = [
            number for number, line in enumerate(lines) if line.startswith("*** предупреждение")
        ]
        assert len(amber) == 2, ascii(window.problems_text())
        assert colour_of(window._problems, amber[0]) == window._problems.kind_colors()[panels.WARNING]
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
        assert pump(window, lambda: "непарные скобки" in window.problems_text()), ascii(
            window.problems_text()
        )
        buffer = window._buffer_for_path(str(module))
        assert buffer is not None, [item.model.path for item in window.buffers()]
        assert any(view.error_line() is not None for view in buffer.views()), "no line marked"
        # The diagnostic names the file it came from, and the line in it.  The
        # interpreter writes its paths with forward slashes, so the file's name is
        # what is looked for here rather than the platform's own spelling, and the
        # position is the opening bracket (task_40), not the token the parser
        # happened to stop at.
        assert "модуль.pld:2:15" in window.problems_text(), ascii(window.problems_text())
    finally:
        discard_changes(window)
    print("ok: a diagnostic from an imported file opens that file and marks its line")


def test_a_runtime_error_in_an_imported_file_opens_it(executable: str, directory) -> None:
    """part 89: a *runtime* error in an `ИМПОРТ`ed file marks the line there too.

    The check above covers a file that does not parse; this is the other half of
    the same promise.  The engine keeps the clause being solved next to its
    environment, so the diagnostic names the *imported* file rather than the one
    that asked the question — and the window, which marks the line of whatever
    file a diagnostic names, opens it.
    """
    module = directory / "модуль.pld"
    module.write_text("ок(1).\nдели(Х) :- БОЛЬШЕ(1, #1/0#).\n", encoding="utf-8")
    main = directory / "главная.pld"
    main.write_text(':- ИМПОРТ("модуль.pld").\n?дели(1).\n', encoding="utf-8")

    window = empty_window(executable)
    try:
        assert window.open_path(str(main)), "the main file did not open"
        window.run_program()
        assert pump(window, lambda: "деление на ноль" in window.problems_text()), ascii(
            window.problems_text()
        )
        assert "модуль.pld:2:" in window.problems_text(), ascii(window.problems_text())
        buffer = window._buffer_for_path(str(module))
        assert buffer is not None, [item.model.path for item in window.buffers()]
        assert any(view.error_line() == 2 for view in buffer.views()), [
            view.error_line() for view in buffer.views()
        ]
        # Opening a file shows it, so the run left the module's tab in front; the tab
        # that is *already* open is what the click on the row is for (part 90).
        assert window.current_buffer() is buffer, "the module's tab is not showing"
    finally:
        discard_changes(window)
    print("ok: a runtime error in an imported file opens it and marks its line")


def test_the_problems_are_a_table_a_double_click_opens_the_line(
    executable: str, directory
) -> None:
    """part 88: «Проблемы» is a table, and a row is the way to its line.

    A diagnostic arrives as fields — kind, severity, message, position — so the tab
    shows one row per diagnostic, names the place as `…/файл.pld:12:5` (the path in
    front of the name is what pushes the message off the screen, and the whole of it
    is in the cell's tooltip), and wraps a long message instead of cutting it.  A
    double-click on the row takes the editor to that line: the row remembers the
    position it came with, so nothing has to be parsed out of the message.
    """
    from prologd_gui import panels

    module = directory / "модуль.pld"
    module.write_text("ок(1).\nсломано(1.\n", encoding="utf-8")
    main = directory / "главная.pld"
    main.write_text(':- ИМПОРТ("модуль.pld").\n?ок(1).\n', encoding="utf-8")

    window = empty_window(executable)
    try:
        assert isinstance(window._problems, panels.ProblemsPane), type(window._problems)
        titles = [
            window._problems.horizontalHeaderItem(column).text()
            for column in range(window._problems.columnCount())
        ]
        assert titles == ["Тип", "Место", "Сообщение"], titles
        assert window._problems.wordWrap() is True, "a long message must wrap"

        assert window.open_path(str(main)), "the main file did not open"
        window.run_program()
        assert pump(window, lambda: "непарные скобки" in window.problems_text()), ascii(
            window.problems_text()
        )

        rows = window._problems.problems()
        assert len(rows) == 1, rows
        kind, severity, message, position = rows[0]
        assert (kind, severity) == ("parse", "error"), (kind, severity)
        assert "непарные скобки" in message, message

        # The place: the file name, the line and the column — not the whole path.
        place = window._problems.item(0, 1).text()
        assert place == "…" + os.sep + "модуль.pld:2:15", place
        assert str(module) not in place, place
        assert window._problems.item(0, 1).toolTip() == position.where()
        assert window._problems.item(0, 0).text() == "parse", window._problems.item(0, 0).text()

        # A double-click on the row marks that line and puts the caret on it.
        buffer = window._buffer_for_path(str(module))
        assert buffer is not None, [item.model.path for item in window.buffers()]
        for view in buffer.views():
            view.clear_marks()
        # The diagnostic opened the file, and it is showing: showing what it opens is
        # what opening a file does.  What the click has to cover is the other case —
        # the tab that already exists with another file in front of it.
        assert window.current_buffer() is buffer, "the module was not opened"
        window._problems.itemDoubleClicked.emit(window._problems.item(0, 0))
        assert any(view.error_line() is not None for view in buffer.views()), (
            "the double-click marked no line"
        )
        assert "модуль.pld:2:15" in window.status_text(), window.status_text()

        # The same row with the module's tab hidden behind the program's: the file is
        # not opened a second time, and the click brings its tab to the front.
        program = window._buffer_for_path(str(main))
        assert window.active_pane().set_current(program), "the program's tab did not come back"
        opened = len(window.buffers())
        window._problems.itemDoubleClicked.emit(window._problems.item(0, 0))
        assert window.current_buffer() is buffer, "the click did not raise the open tab"
        assert len(window.buffers()) == opened, [item.model.path for item in window.buffers()]

        # A long message takes several lines of its own row.
        window._on_failed("parse", "error", "длинное сообщение " * 20, None)
        assert window._problems.rowCount() == 2, window._problems.rowCount()
        one = window._problems.fontMetrics().height()
        assert window._problems.rowHeight(1) > one * 2, (
            window._problems.rowHeight(1),
            one,
        )

        # A right click on a row offers «Копировать» (`Ctrl+C` works too), and what
        # lands on the clipboard is the diagnostic in the shape a bug report wants:
        # `файл:строка:столбец: сообщение`, not just the words.
        window._problems.selectRow(0)
        assert window._problems.copy_action.text() == "Копировать", "no copy entry"
        window._problems.copy_action.trigger()
        copied = QGuiApplication.clipboard().text()
        assert "непарные скобки" in copied, ascii(copied)
        assert ":2:" in copied, ascii(copied)
        assert "модуль.pld" in copied, ascii(copied)
        # A row without a place is copied as its message, and nothing selected
        # means nothing copied.
        window._problems.selectRow(1)
        window._problems.copy_action.trigger()
        assert QGuiApplication.clipboard().text().startswith("длинное сообщение"), (
            ascii(QGuiApplication.clipboard().text())
        )
        window._problems.clearSelection()
        window._problems.copy_action.trigger()
        assert QGuiApplication.clipboard().text().startswith("длинное сообщение"), (
            "a trigger without a selected row must not empty the clipboard"
        )
    finally:
        discard_changes(window)
    print("ok: the problems are a table, its rows wrap, and a double-click opens the line")


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
    """task_36: lesson_04's `?сумма(5, Сумма).` answers `Сумма=15` and nothing else.

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
            if content.strip() == "?сумма(5, Сумма)."
        )
        statement = view.query_statements().get(line)
        assert statement == "?сумма(5, Сумма).", (line, statement)

        view.queryRequested.emit(statement)
        wait_for_result(window)
        assert printed_lines(window) == ["Сумма=15"], ascii(window.output_text())
        assert window._query_line.text() == "?сумма(5, Сумма).", "the question stays visible"
    finally:
        discard_changes(window)
    print("ok: a marker answers one question alone (Сумма=15 from lesson_04)")


def test_a_question_parked_in_a_comment_runs_from_the_margin(executable: str) -> None:
    """`%   ?дед(иван, анна).` in lesson 2: the file never runs it, a click does."""
    window = empty_window(executable)
    try:
        assert window.open_path(str(LESSON_02))
        view = window.editor()
        assert "?дед(иван, анна)." in view.query_statements().values()
        view.queryRequested.emit("?дед(иван, анна).")
        wait_for_result(window)
        printed = printed_lines(window)
        # A ground question: the answer of the parked line is the same `ДА` any
        # other question with no variables gets.
        assert printed == ["ДА"], ascii(window.output_text())
        # task_58: the quiet load says so in «Система», like `F5` does.  The line
        # used to be swallowed by the early return that waits for the answer.
        assert "--- база знаний загружена (" in window.system_text(), ascii(window.system_text())
        assert " мс) ---" in window.system_text(), ascii(window.system_text())
    finally:
        discard_changes(window)
    print("ok: a question parked in a comment answers from the margin (lesson 2)")


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
        assert "<query>:1:1" in window.problems_text(), ascii(window.problems_text())
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
        assert "английское имя" not in text, ascii(text)
        for mode in ("Ц1, Ц2, Пер", "Ц1, Ц2, Стр4", "Пер, Ц2, Стр4", "Пер, Ц, Стр4", "Ц1, Пер, Стр4"):
            assert mode in text, (mode, ascii(text))
        assert not window._reference_dock.isHidden()

        # An unknown word says so instead of showing the previous record.
        cursor.setPosition(view.toPlainText().index("тест") + 1)
        view.setTextCursor(cursor)
        window._actions["reference"].trigger()
        assert "нет справки" in window.reference_text(), ascii(window.reference_text())

        # The reference of the *original* engine's repository (the one the 1.27
        # package ships) has no `section` and no `aliases`: `F1` must show what the
        # record has rather than nothing at all (part 146 — indexing `section` raised
        # inside the slot, and the dock never opened).
        from prologd_gui import reference as reference_module

        window._reference = reference_module.Reference(
            [
                {
                    "name": "БОЛЬШЕ",
                    "kind": "predicate",
                    "arities": [2],
                    "group": "compare",
                    "summary": "Сравнение на больше",
                    "variants": ["БОЛЬШЕ(А, Б) — истинно, если А больше Б"],
                }
            ]
        )
        window.editor().setPlainText("тест :- БОЛЬШЕ(1, 2).\n")
        view = window.editor()
        cursor = view.textCursor()
        cursor.setPosition(view.toPlainText().index("БОЛЬШЕ") + 2)
        view.setTextCursor(cursor)
        window._actions["reference"].trigger()
        text = window.reference_text()
        assert text.startswith("БОЛЬШЕ — Сравнение на больше"), ascii(text)
        assert "раздел руководства" not in text, ascii(text)
        assert "БОЛЬШЕ(А, Б)" in text, ascii(text)
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
                    "C:/Users/vasla/source/projects/examples/hanoi.pld", 2, 1
                ),
            ),
            ["hanoi(6)"],
        )
        assert pane.where_text().endswith("hanoi.pld:2:1"), ascii(pane.where_text())
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


def test_formatting_a_selection_keeps_its_lines(executable: str) -> None:
    """task_114: a selected line grows no blank one, and its comment survives.

    Two reports, one shape.  The formatter answers with a *program*, which ends
    with a line terminator, while a selection need not include one — so
    `?length([1, 2, 3], Д).` came back with a newline and an empty line appeared
    under it.  And a text whose last line has no newline lost that line: the
    end-of-file marker was counted as a statement, so everything after the last
    dot was a gap *between* statements, and the formatter reads the last line of
    such a gap as the indentation in front of the next statement.
    """
    window = empty_window(executable)
    try:
        view = window.editor()
        window._format_selection_action.setChecked(True)
        assert window._settings.format_selection is True

        def formatted(text: str, start: int, end: int) -> str:
            view.setPlainText(text)
            cursor = view.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            view.setTextCursor(cursor)
            window._actions["format"].trigger()
            assert pump(
                window, lambda: window.status_text() != "форматирование…"
            ), window.status_text()
            return view.toPlainText()

        # A query with its trailing comment, selected without the line break: the
        # answer must not bring a line of its own.
        line = "?length([1, 2, 3], Д). % выделена эта строка\n"
        assert formatted(line, 0, line.index("\n")) == line, ascii(view.toPlainText())
        assert formatted(line, 0, line.index("\n") + 1) == line, ascii(view.toPlainText())

        # Two comments, the last one without a newline after it: both stay, and
        # the trailing spaces of the first are trimmed.
        comments = "% первый \n% второй\n"
        for end in (len(comments) - 1, len(comments)):
            assert formatted(comments, 0, end) == "% первый\n% второй\n", (
                ascii(view.toPlainText())
            )

        # What was rewritten stays selected, and it is the *fragment*: the caret
        # of a selection is not mapped through `map_positions`, which reads its
        # offsets from the whole buffer (task_115).
        formatted("% первый  \n% второй\n", 0, len("% первый  "))
        selection = view.textCursor()
        assert (selection.selectionStart(), selection.selectionEnd()) == (
            0,
            len("% первый"),
        ), (selection.selectionStart(), selection.selectionEnd())
    finally:
        discard_changes(window)
    print("ok: a formatted selection keeps its lines, and a last comment without a newline")


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


def test_an_imported_file_reaches_the_popup(executable: str, files: pathlib.Path) -> None:
    """task_102: the predicates an `ИМПОРТ` line names are offered while typing.

    The names live in another file, and only the window knows how the interpreter
    would find it (the «Дополнительные каталоги ИМПОРТ» row and `stdlib`).  This is
    the check of that seam: the row is filled, the directive is typed, and the popup
    offers the library's predicate and says which file it came from.
    """
    library = files / "библиотека.pld"
    library.write_text(
        "% Принадлежность элемента списку\nчлен_списка(X, [X|_]).\n", encoding="utf-8"
    )
    window = empty_window(executable)
    try:
        window._settings.import_paths = [str(files)]
        # The same door the dialog uses: the session has to be told about the
        # folder before a run, or the interpreter never hears of `-I` (task_61).
        window.apply_settings()
        view = window.editor()
        view.setPlainText(':- ИМПОРТ("библиотека.pld").\nчлен_с')
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        view.setTextCursor(cursor)
        view._maybe_complete(force=True)
        try:
            labels = view.completion_labels()
            # The word being typed is in the buffer, so the document offers it too;
            # the library's predicate is the one only the import could know.
            assert "член_списка/2" in labels, labels
            row = labels.index("член_списка/2")
            view._completer.popup().setCurrentIndex(view._offer_list.index(row, 0))
            view._update_detail()
            detail = view.completion_detail()
            assert detail.startswith("импорт: библиотека.pld"), detail
            # And the comment above the clause is read from the file into the label
            # (task_103): the note a library keeps for its predicates.
            assert "Принадлежность элемента списку" in detail, detail
        finally:
            view._hide_completion()

        # The same offer has to survive a run (task_111): the `ready` event brings
        # the *kinds* of the reserved names, and `ИМПОРТ` becomes a `directive`
        # instead of a plain keyword.  Once the directive stopped being recognised
        # there, the popup lost every imported name — the owner saw `length` vanish
        # from it after the first `F5`.
        view.setPlainText(':- ИМПОРТ("библиотека.pld").\n?член_списка(1, [1]).\n')
        assert window.run_program() is True
        wait_for_result(window)
        assert window.problems_text() == "", window.problems_text()
        view.setPlainText(':- ИМПОРТ("библиотека.pld").\nчлен_с')
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        view.setTextCursor(cursor)
        view._maybe_complete(force=True)
        try:
            labels = view.completion_labels()
            assert "член_списка/2" in labels, labels
        finally:
            view._hide_completion()
    finally:
        discard_changes(window)
    print("ok: the popup offers what an imported file defines, with its comment and file")


def test_f12_goes_to_the_first_clause_of_a_name(
    executable: str, directory: pathlib.Path
) -> None:
    """`F12` on a name opens where it starts — here or in an import (task_103).

    The caret goes to the first clause head: the buffer in front of the user is
    searched first, then the files its `ИМПОРТ` lines bring in — the same list the
    popup reads.  On an `ИМПОРТ` line the directive still wins (task_69), and a name
    that is nowhere says so instead of moving the caret at random.
    """
    from PySide6.QtGui import QTextCursor

    library = directory / "библиотека.pld"
    library.write_text("член(1, [1]).\nчлен(X, [_|Хвост]) :- член(X, Хвост).\n",
                       encoding="utf-8", newline="\n")
    window = empty_window(executable)
    try:
        program = directory / "программа.pld"
        program.write_text(
            ':- ИМПОРТ("библиотека.pld").\n'
            "цель :- член(2, [1, 2]), правило(1).\n"
            "\n"
            "% Правило ниже определено в этом же файле\n"
            "правило(X) :- ВЫВОД(X).\n"
            "?нетакого(1).\n",
            encoding="utf-8",
            newline="\n",
        )
        assert window.open_path(str(program))
        program_buffer = window.current_buffer()
        view = window.active_pane().current_view()
        action = window._actions["open_import"]

        def caret_on(line_number: int, needle: str) -> None:
            """Puts the caret inside the first `needle` of that line."""
            text = view.document().findBlockByNumber(line_number).text()
            cursor = view.textCursor()
            cursor.setPosition(
                view.document().findBlockByNumber(line_number).position() + text.index(needle) + 1
            )
            view.setTextCursor(cursor)
            window._update_details()

        # A name of this file: the caret goes to its head, not to the call.
        caret_on(1, "правило")
        assert action.isEnabled(), "the caret is on a name"
        action.trigger()
        assert view.textCursor().blockNumber() == 4, view.textCursor().blockNumber()
        assert "этом файле" in window.status_text(), window.status_text()

        # A name the library defines: the library opens, and the caret lands on the
        # first clause there.
        caret_on(1, "член")
        action.trigger()
        opened = window.current_buffer()
        assert opened is not None and opened.model.path == str(library), opened
        assert opened.views()[0].textCursor().blockNumber() == 0, (
            opened.views()[0].textCursor().blockNumber()
        )
        assert "библиотека.pld" in window.status_text(), window.status_text()

        # Back to the program for the last two cases.
        window.active_pane().set_current(program_buffer)
        window._update_details()

        # A built-in has no clause: the status points at the reference instead.
        caret_on(4, "ВЫВОД")
        action.trigger()
        assert "встроенный" in window.status_text(), window.status_text()

        # And a name nothing defines says so rather than moving the caret.
        caret_on(5, "нетакого")
        action.trigger()
        assert "не найдено" in window.status_text(), window.status_text()
    finally:
        discard_changes(window)
    print("ok: F12 goes to the first clause, in this file or in an import")


def test_the_import_string_completes_to_a_file_name(
    executable: str, files: pathlib.Path
) -> None:
    """Inside `ИМПОРТ("…")` the popup offers files, not predicates (task_104).

    The one string in the language that is a path: the folders are the ones the
    run would search, a name is offered after one letter, and accepting writes the
    name into the quotes — the folder part typed before it stays.
    """
    from PySide6.QtGui import QTextCursor

    (files / "iso.pld").write_text("member(X, [X|_]).\n", encoding="utf-8")
    (files / "иное.pld").write_text("факт(1).\n", encoding="utf-8")
    window = empty_window(executable)
    try:
        window._settings.import_paths = [str(files)]
        view = window.editor()
        view.setPlainText(':- ИМПОРТ("is").\n')
        cursor = view.textCursor()
        cursor.setPosition(view.toPlainText().index("is") + 2)
        view.setTextCursor(cursor)
        # One letter is enough here: a file name is not a word.
        view._maybe_complete()
        try:
            labels = view.completion_labels()
            assert "iso.pld" in labels, labels
            assert "иное.pld" not in labels, labels
            assert view._accept_completion() is True
            assert view.toPlainText() == ':- ИМПОРТ("iso.pld").\n', ascii(view.toPlainText())
            # The caret stays inside the quotes, right after the name.
            assert view.textCursor().position() == view.toPlainText().index('").'), (
                view.textCursor().position()
            )
        finally:
            view._hide_completion()

        # An ordinary string gets nothing, as before — the exception is one string.
        view.setPlainText(':- ВЫВОД("is").\n')
        cursor = view.textCursor()
        cursor.setPosition(view.toPlainText().index("is") + 2)
        view.setTextCursor(cursor)
        view._maybe_complete()
        assert view.completion_labels() == [], view.completion_labels()
    finally:
        discard_changes(window)
    print("ok: the ИМПОРТ string completes to a file name, and only that string does")


def test_the_directive_is_inserted_as_a_whole_statement(executable: str) -> None:
    """`ИМ` on a line of its own gives `:- ИМПОРТ("").` (task_105).

    A directive is a statement, not a goal: the popup offers the text that has to
    be written, with the caret between the quotes — where the file name goes, and
    where the string's own completion takes over (task_104).  Inside a body it is
    not offered at all: a directive there is a syntax error.  `ХОЛСТ` and the names
    marker come whole too (task_106), and the marker — being a file's first line —
    only there.
    """
    from PySide6.QtGui import QTextCursor

    def complete_from(text: str) -> list[str]:
        view.setPlainText(text)
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        view.setTextCursor(cursor)
        view._maybe_complete(force=True)
        return view.completion_labels()

    window = empty_window(executable)
    try:
        view = window.editor()
        labels = complete_from("ИМ")
        try:
            assert not any(label.startswith(":- ИМЕНА") for label in labels), labels
            row = next(
                (index for index, label in enumerate(labels) if label.startswith(":- ИМПОРТ(")),
                None,
            )
            assert row is not None, labels
            view._completer.popup().setCurrentIndex(view._offer_list.index(row, 0))
            assert view._accept_completion() is True
            assert view.toPlainText() == ':- ИМПОРТ("").', ascii(view.toPlainText())
            assert view.textCursor().position() == len(':- ИМПОРТ("'), (
                view.textCursor().position()
            )
        finally:
            view._hide_completion()

        # `ХОЛСТ` names the height and the width, so the statement arrives with its
        # comma and the caret before it.
        labels = complete_from("ХОЛ")
        assert labels and labels[0] == ":- ХОЛСТ(, ).", labels
        try:
            assert view._accept_completion() is True
            assert view.toPlainText() == ":- ХОЛСТ(, ).", ascii(view.toPlainText())
            assert view.textCursor().position() == len(":- ХОЛСТ("), (
                view.textCursor().position()
            )
        finally:
            view._hide_completion()

        # A directive is a statement wherever a statement can start, first line or
        # not.
        labels = complete_from("цель.\nИМ")
        assert any(label.startswith(":- ИМПОРТ(") for label in labels), labels
        view._hide_completion()

        # The same word inside a body: ordinary names are still offered, but the
        # directive itself is not — a statement cannot start here.
        labels = complete_from("цель :- ИМ")
        assert not any(label.startswith(":- ") for label in labels), labels
    finally:
        discard_changes(window)
    print("ok: a directive comes as its whole statement, and only where one can start")


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


def test_a_file_named_on_the_command_line_opens(executable: str) -> None:
    """task_116: a `.pld` handed to the window is the document it opens *on*.

    The shell passes the path when a `.pld` is double-clicked, which is what the
    installer's association is for.  The file must be the window's only document:
    the welcome program is for a window with no session *and* no file to show, so
    it must not stand beside the file as a second tab.  A file that has gone in the
    meantime leaves the window as it always opens — welcome program and a note in
    the pane — because a start must not come up empty.
    """
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    directory = tempfile.TemporaryDirectory(prefix="prologd_gui_start_")
    _SETTINGS_DIRECTORIES.append(directory)
    settings = Settings(pathlib.Path(directory.name) / "gui.ini")
    program = pathlib.Path(directory.name) / "первый.pld"
    program.write_text("снег.\n", encoding="utf-8")

    window = MainWindow(executable, [], settings, path=str(program))
    try:
        assert window.tab_count() == 1, [b.model.name for b in window.buffers()]
        assert window.current_buffer().model.path == str(program), window.current_buffer().model
        assert window.editor().toPlainText() == "снег.\n"
        assert "открыт" in window.status_text(), window.status_text()
    finally:
        window.stop_program()

    gone = pathlib.Path(directory.name) / "нет-такого.pld"
    window = MainWindow(executable, [], settings, path=str(gone))
    try:
        assert window.tab_count() == 1, "a start with no file must not come up empty"
        # The window's own words go to «Система», not to «Вывод» (task_50).
        assert "не могу открыть" in window.system_text(), ascii(window.system_text())
        assert window.current_buffer().model.path is None, "the welcome program"
    finally:
        window.stop_program()
    print("ok: a file named on the command line is the document the window opens on")


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

    An untitled tab is remembered by its *text*, so a session written after the
    answer would bring back exactly the work the user threw away — the answer
    would be a lie.  Since task_108 the window's close does not ask about unnamed
    tabs at all: the question belongs to the *tab* (`Ctrl+W`, «Закрыть вкладку»),
    where nothing else can keep the text.  The answer still has to reach the
    session, which is what this checks.
    """
    from prologd_gui import documents
    from prologd_gui import window as window_module
    from prologd_gui.settings import Settings
    from prologd_gui.window import MainWindow

    kept = directory / "остаётся.pld"
    kept.write_text("снег.\n", encoding="utf-8")

    window = empty_window(executable)
    settings_path = window._settings.path
    try:
        window.open_path(str(kept))
        window.new_buffer()
        window.editor().insertPlainText("черновик.\n")
        draft = window.current_buffer()
        window.new_buffer()
        window.editor().insertPlainText("остаётся.\n")
        keep = window.current_buffer().model.name
        assert window.tab_count() == 3, window.tab_count()

        # «Черновик» is thrown away by closing its own tab; «остаётся» is not asked
        # about at all and rides into the session as text.
        window._ask_save = lambda name: window_module.DISCARD
        assert window.close_buffer(draft) is True
        asked: list[str] = []
        window._ask_save = lambda name: asked.append(name) or window_module.DISCARD
        window.close()
        assert asked == [], asked
    finally:
        window.stop_program()

    settings = Settings(settings_path)
    stored = documents.decode_tabs(settings.session_tabs)
    assert [record.name for record in stored] == [kept.name, keep], stored
    assert stored[0].path, "a file tab is remembered by its path"
    assert stored[1].text == "остаётся.\n", stored[1]

    reopened = MainWindow(executable, [], settings)
    try:
        assert [b.model.name for b in reopened.buffers()] == [kept.name, keep], [
            b.model.name for b in reopened.buffers()
        ]
        texts = [b.text() for b in reopened.buffers()]
        assert not any("черновик" in text for text in texts), texts
        assert reopened.buffers()[1].text() == "остаётся.\n"
        assert reopened.buffers()[1].is_modified() is True, "unsaved work stays unsaved"
    finally:
        discard_changes(reopened)
    print(
        "ok: an unnamed tab answered with «Не сохранять» is dropped from the session, "
        "and the window close asks nothing about the rest"
    )


def test_the_window_close_asks_only_about_files(
    executable: str, directory: pathlib.Path
) -> None:
    """task_108: the closing question is about a file, not about a scratch pad.

    An unnamed buffer used to be asked about like a file, and «Сохранить» there
    meant a file dialog for a program that had no name yet — while the session was
    already keeping its text.  Now the window asks about buffers with a file (the
    session keeps only their path, so an edit that was not written is gone) and
    passes unnamed ones to the session without a word.  Two things bring the
    question back: the session switched off (there is no store then) and a text
    too big for the budget of one buffer.
    """
    from prologd_gui import documents
    from prologd_gui import window as window_module

    draft = "факт(1).\n"
    asked: list[str] = []

    def closing_window():
        window = empty_window(executable)
        window._ask_save = lambda name: asked.append(name) or window_module.DISCARD
        return window

    # An unnamed buffer: no question, and the text is in the session afterwards.
    window = closing_window()
    try:
        window.editor().insertPlainText(draft)
        assert window.current_buffer().is_modified()
        window.close()
        assert asked == [], asked
        stored = window.session_tabs()
        assert [record.text for record in stored] == [draft], stored
        assert stored[0].modified is True, "unsaved work stays unsaved"
    finally:
        window.stop_program()

    # A buffer with a file: the question is the whole point of asking.
    asked.clear()
    window = closing_window()
    try:
        program = directory / "вопрос при закрытии.pld"
        program.write_text("снег.\n", encoding="utf-8")
        window.open_path(str(program))
        window.editor().insertPlainText("дождь.\n")
        assert window.current_buffer().is_modified()
        window.close()
        assert asked == [program.name], asked
        assert window.session_tabs() == [], "«Не сохранять» keeps the tab out as well"
    finally:
        window.stop_program()

    # The session switched off is no store at all, so the unnamed buffer is asked
    # about — its text would otherwise go nowhere.
    asked.clear()
    window = closing_window()
    try:
        window._settings.restore_tabs = False
        window.editor().insertPlainText(draft)
        window.close()
        assert asked == ["Без имени"], asked
    finally:
        window.stop_program()

    # And so is a text the session cannot hold.
    asked.clear()
    window = closing_window()
    try:
        window.editor().insertPlainText("я" * (documents.SESSION_TEXT_BUDGET + 1))
        window.close()
        assert asked == ["Без имени"], asked
    finally:
        window.stop_program()
    print(
        "ok: the window close asks about files, and about an unnamed tab only when "
        "the session cannot keep it"
    )


def test_a_session_that_cannot_be_written_is_named(
    executable: str, directory: pathlib.Path
) -> None:
    """task_108: silence about an unnamed tab is a promise; a failed write is a lie.

    The window keeps an unnamed tab by writing its text into the settings file and
    asks nothing about it on the way out.  When the store cannot be written — here
    the folder it should live in is a plain file — the window has to say so before
    it goes, or the user finds out by not finding the tab.
    """
    from prologd_gui.settings import Settings

    blocked = directory / "занято"
    blocked.write_text("не папка", encoding="utf-8")
    settings = Settings(blocked / "gui.ini")

    window = make_window(executable, settings=settings)
    warned: list[str] = []
    try:
        window._warn_not_remembered = warned.append
        window.editor().insertPlainText("факт(1).\n")
        assert window.current_buffer().is_modified()
        window.close()
    finally:
        window.stop_program()
    assert settings.write_failed is True, "the store cannot be written at all"
    assert warned, "the window closed without a word about the lost session"
    assert "сесси" in warned[0], warned
    print("ok: a session that cannot be written is named before the window goes")


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
    from prologd_gui.window import WELCOME_TEXT, MainWindow

    window = make_window(executable)
    settings_path = window._settings.path
    try:
        assert window.buffers()[0].text() == WELCOME_TEXT, "the welcome tab"
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
    assert stored[0].text == WELCOME_TEXT
    assert stored[0].modified is False, "nobody edited the welcome program"

    reopened = MainWindow(executable, [], settings)
    try:
        assert reopened.tab_count() == 1, [b.model.name for b in reopened.buffers()]
        assert reopened.buffers()[0].text() == WELCOME_TEXT
        assert reopened.buffers()[0].is_modified() is False, (
            "the restored tab carries a star it never earned"
        )
        assert reopened.buffers()[0].model.title() == "Без имени", reopened.buffers()[0].model.title()
    finally:
        discard_changes(reopened)
    print("ok: an untouched unnamed tab comes back clean, without a star or a question")


def test_the_questions_switch_decides_whether_a_run_answers(executable: str) -> None:
    """task_29's «Выполнять вопросы при запуске»: off, a lesson loads as rules.

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
    print("ok: «выполнять вопросы» decides whether a run answers the program's questions")


def test_print_questions_echoes_the_question_line(executable: str) -> None:
    """task_46: «Печатать вопросы» writes the `?цель.` line before its answer."""
    window = empty_window(executable)
    try:
        window.editor().setPlainText("факт(1).\n?факт(1).\n")

        window.run_program()
        wait_for_result(window)
        assert "?факт(1)." not in window.output_text(), ascii(window.output_text())

        window._settings.print_questions = True
        window.run_program()
        wait_for_result(window)
        text = window.output_text()
        assert "?факт(1)." in text, ascii(text)
        assert text.index("?факт(1).") < text.index("ДА"), ascii(text)
    finally:
        discard_changes(window)
    print("ok: «печатать вопросы» writes the question line before its answer")


def test_the_input_switch_chooses_where_to_ask(executable: str) -> None:
    """task_29's «Спрашивать ввод»: the console under the output, or a box.

    Both ways are open here — the panel is visible, so the console *can* take the
    answer — which is what makes the setting a switch rather than a rule about
    what is on screen.
    """
    window = empty_window(executable)
    try:
        assert window._panel_tabs.isHidden() is False, "both ways need the panel"
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
        assert colour_of(window._problems, 0) == panels.KIND_COLORS[panels.ERROR]

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
        assert window._problems.kind_colors()[panels.ERROR] == theme.DARK.error
        assert colour_of(window._problems, 0) == theme.DARK.error, "the history kept its colours"

        # Stored, and the menu says which one is on.
        assert Settings(settings_path).theme == "dark"
        assert window._theme_actions["dark"].isChecked() is True
        assert window._theme_actions["light"].isChecked() is False

        # «Системное»: the widgets come from the desktop *and* so do the colours
        # of the text — the palette its colour scheme implies (on this machine the
        # offscreen platform answers «light», so this is a real question and not a
        # shortcut through one palette).
        window._settings.theme = appearance.SYSTEM
        window.apply_settings()
        expected = appearance.theme_palette(appearance.SYSTEM)
        assert window.buffers()[0].highlighter.theme is expected.syntax
        assert window.editor().palette() is expected
        assert window._problems.kind_colors()[panels.ERROR] == expected.error
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
        window._settings.timeout_milliseconds = 2000
        window._actions["run"].trigger()

        notes = window.system_text()
        assert "пределы: «Предел шагов» 5000" in notes, notes
        # A limit left at the shipped number is not a choice the user made.
        assert "Предел глубины» 1000000" not in notes, notes
        assert window._timeout.isActive() is True, "the deadline was not armed"
        said = pump(window, lambda: "предел шагов" in window.problems_text())
        assert said, f"the run never stopped: {ascii(window.problems_text())}"
        text = window.problems_text()
        assert "Превышен предел шагов выполнения: 5000" in text, ascii(text)
        assert window._timeout.isActive() is False, "the deadline outlived its run"

        # «Предел времени»: the run is asked to stop, and the pane says by what.
        window.editor().setPlainText("?ВВОДЦЕЛ(А).\n")
        window._settings.timeout_milliseconds = 1000
        window.run_program()
        assert pump(window, lambda: window.status_text().startswith("ждёт ввода")), \
            window.status_text()
        assert window._timeout.isActive() is True
        window._on_timeout()
        assert "остановлено по времени" in window.status_text(), window.status_text()
        assert "предел времени: 1000 мс" in window.system_text(), ascii(window.system_text())
        window.stop_program()
    finally:
        discard_changes(window)
    assert Settings(settings_path).max_steps == 5000, "the setting was not stored"
    print("ok: the limits reach the run, name themselves, and the deadline is the window's")


def test_the_time_limit_ends_a_run_that_cannot_be_interrupted(executable: str) -> None:
    """task_64: a run that is *solving* ends on «Предел времени», and not for ever.

    The request the deadline sends is dispatched between two requests of the session,
    so a query that is solving never reads it: the limit used to write its note and
    leave the run alive.  What follows the request is the deadline of «Остановить» —
    the process goes, and the pane says both things happened.
    """
    window = empty_window(executable)
    try:
        # A program that is *solving* for longer than the limit, and bounded: a
        # hundred sleeps of 50 ms end on their own, so this test cannot hang the
        # suite even if the deadline it checks never fires.
        window.editor().setPlainText(
            "спать(0) :- !.\n"
            "спать(Н) :- ЖДИ(50), СЛОЖЕНИЕ(П, 1, Н), спать(П).\n"
            "?спать(100).\n"
        )
        window._settings.timeout_milliseconds = 300
        window._actions["run"].trigger()
        assert window._timeout.isActive() is True, "the deadline was not armed"
        assert "предел времени: 300 мс" not in window.system_text(), "fired before the run"

        gone = pump(window, lambda: window.session.is_running() is False)
        assert gone, f"the run outlived its limit: {ascii(window.system_text())}"
        assert "предел времени: 300 мс" in window.system_text(), ascii(window.system_text())
        assert "--- остановлено ---" in window.system_text(), ascii(window.system_text())
    finally:
        discard_changes(window)
    print("ok: a solving run ends on the time limit, and the pane says by what")


def test_a_flood_of_output_leaves_the_window_alive(executable: str) -> None:
    """task_65: a program that floods the pane cannot take the window with it.

    The interpreter is a separate process, but its events are handled in the
    window's own thread, and a whole flood used to be handed over in one call:
    a click on «Остановить» and the «Предел времени» timer waited behind all of
    it, so a program that kept writing could not be stopped at all.  The events
    are now handed over in slices, and this pins the difference the only way a
    test can — a timer that must keep ticking *while* the flood is dispatched.
    """
    from prologd_gui import session as session_module
    from PySide6.QtCore import QTimer

    window = empty_window(executable)
    ticks: list[int] = []
    beat = QTimer()
    beat.setInterval(20)
    beat.timeout.connect(lambda: ticks.append(1))
    try:
        # The guard is deterministic — it counts events, not seconds — so it is
        # checked directly instead of hoping that a program writes fast enough.
        flooded: list[int] = []
        window._session.flooded.connect(flooded.append)
        window._session._note_flood(session_module.FLOOD_EVENTS)
        assert flooded == [session_module.FLOOD_EVENTS], flooded

        # A flood, but a bounded one: 60 000 lines are far more than the pane and
        # the event loop can show at once, and the program ends by itself.  The
        # loop must keep turning *while* they are dispatched (task_65).
        window.editor().setPlainText(
            "строка(0) :- !.\n"
            'строка(Н) :- ВЫВОДПС("строка"), СЛОЖЕНИЕ(П, 1, Н), строка(П).\n'
            "?строка(60000).\n"
        )
        # This case is about the slices, not the cap: the shipped «Предел вывода»
        # would end this flood early.
        window._settings.max_output_events = 0
        window._actions["run"].trigger()
        assert pump(window, lambda: window._busy), "the run never started"

        beat.start()
        ticks.clear()
        turned = pump(window, lambda: len(ticks) >= 5, timeout=5.0)
        beat.stop()
        assert turned, f"the event loop stopped turning: {len(ticks)} ticks"

        # And the run can be stopped while it is still writing — or has finished,
        # which is the same promise: the run must not stay busy for ever.  A stop
        # that lands after the program ended is a *polite* one (the session stays,
        # the base too), so the promise is the run's end, not the process's.
        window._actions["stop"].trigger()
        assert pump(window, lambda: not window._busy), ascii(window.system_text())
    finally:
        beat.stop()
        discard_changes(window)
    print("ok: a flooding program leaves the event loop turning, and «Остановить» works")


def test_the_output_limit_stops_a_flood(executable: str) -> None:
    """task_66: «Предел вывода» ends a program that floods the panes by itself.

    The interpreter cannot be asked to stop a query that is solving (task_64), so
    a program that prints in a loop used to be stoppable only by hand.  The cap
    counts what the window receives and fires the same escalation as the
    deadline: the request, then the process after the grace.
    """
    window = empty_window(executable)
    try:
        # The flood is bounded, so a broken cap cannot hang the suite; the sleep
        # then keeps the query solving past the stop's grace.  Without it a fast
        # machine can print the whole flood before the deadline (Linux does), the
        # query ends by itself, and the escalation this test is about never runs:
        # the `interrupt` request is dispatched only between requests.
        window.editor().setPlainText(
            "строка(0) :- !.\n"
            'строка(Н) :- ВЫВОДПС("строка"), СЛОЖЕНИЕ(П, 1, Н), строка(П).\n'
            "?строка(2000), ЖДИ(5000).\n"
        )
        window._settings.max_output_events = 1000
        window._actions["run"].trigger()
        assert pump(window, lambda: window.session.is_running() is False), (
            ascii(window.system_text())
        )
        assert "предел вывода: 1000 событий" in window.system_text(), ascii(window.system_text())
        assert "--- остановлено ---" in window.system_text(), ascii(window.system_text())
    finally:
        discard_changes(window)
    print("ok: the output limit stops a flooding program by itself")


def test_stop_silences_the_panes_during_a_flood(executable: str) -> None:
    """task_66: once «Остановить» is asked, the panes are fed no more.

    A program that keeps printing would keep the event loop busy repainting the
    panes — in a visible window that is exactly what starves the «Остановить»
    deadline (the request first, the process after the grace).  The pane must
    freeze the moment the stop is asked, so the loop is free for the timer.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText('петля :- ВЫВОДПС("строка"), петля.\n?петля.\n')
        # The cap is off: this case is about what a *stop* silences.
        window._settings.max_output_events = 0
        window._actions["run"].trigger()
        assert pump(window, lambda: "строка" in window.output_text(), timeout=5.0), (
            ascii(window.output_text())
        )
        window._actions["stop"].trigger()
        assert pump(window, lambda: not window.session.is_running(), timeout=5.0), (
            ascii(window.system_text())
        )
        frozen = window.output_text()
        pump(window, lambda: False, timeout=1.0)
        assert window.output_text() == frozen, "the pane kept growing after the stop"
    finally:
        discard_changes(window)
    print("ok: stopping a flood silences the panes, and the process goes")


def test_a_run_after_a_stop_prints_again(executable: str) -> None:
    """task_66: a stop must not leak its `_stopping` into the next run.

    The `ended` of the killed process is deferred until its queued events are
    dispatched; a run started before that delivery used to keep `_stopping` set,
    and the panes were fed no more — the next run printed nothing.  `start()` now
    delivers the pending `ended` before the new process, so the flag is cleared
    and the next run prints again.
    """
    window = empty_window(executable)
    try:
        window.editor().setPlainText('петля :- ВЫВОДПС("строка"), петля.\n?петля.\n')
        # The cap is off: the stop, not a limit, must end this run.
        window._settings.max_output_events = 0
        window._actions["run"].trigger()
        assert pump(window, lambda: "строка" in window.output_text(), timeout=5.0), (
            ascii(window.output_text())
        )
        window._actions["stop"].trigger()
        assert pump(window, lambda: not window.session.is_running(), timeout=5.0), (
            ascii(window.system_text())
        )

        window.editor().setPlainText('?ВЫВОДПС("снова").\n')
        window._actions["run"].trigger()
        assert pump(window, lambda: "снова" in window.output_text(), timeout=5.0), (
            ascii(window.output_text())
        )
    finally:
        discard_changes(window)
    print("ok: a run after a stop prints again")


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

        # Reopening shows the same canvas: the picture lives in the window, and
        # hiding the window never threw it away.  The run's own snapshot has
        # already caught up with what was drawn before the canvas existed, so a
        # second one would say the same thing (that is what `_picture_asked` is
        # for) — the status still names the last thing the window did.
        window._actions["graphics"].setChecked(True)
        assert picture.isVisible() is True
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


def test_the_launch_binary_names_the_build_folder(
    executable: str, directory: pathlib.Path
) -> None:
    """task_79: `--exe` replaces the «Интерпретатор» row task_46 added.

    The path is not only a file: it is the *folder* the build lies in, and that is
    where the interpreter is looked for — nowhere else.  The status bar names both,
    because what the command line chose is invisible otherwise.
    """
    from prologd_gui import paths

    folder = copied_build(directory, executable)
    pinned = folder / pathlib.Path(executable).name
    window = empty_window(str(pinned))
    try:
        assert window.session.executable() == str(pinned)
        details = window._details.text()
        assert f"движок: {paths.ENGINE_TITLE}" in details, details
        assert str(pinned) in details, details

        window.editor().setPlainText('?ВЫВОД("ok"),ПС.\n')
        window.run_program()
        wait_for_result(window)
        assert "ok" in window.output_text(), ascii(window.output_text())
        print("ok: the launch names the build folder, and the run works")
    finally:
        discard_changes(window)


def test_a_missing_interpreter_is_reported_not_half_started(
    executable: str, directory: pathlib.Path
) -> None:
    """task_46's promise kept under task_79's rule: a launch that points at nothing.

    The row that could name a missing file is gone, but the gate is still needed:
    a build folder that was cleaned, or a `--exe` typed from memory, must be
    reported in the pane before a process is asked to start.
    """
    from prologd_gui import paths

    missing = directory / "нет" / paths.EXECUTABLE_NAME

    window = make_window(str(missing), ready=False)
    try:
        assert window.session.executable() == str(missing)

        window.editor().setPlainText('?ВЫВОД("ok"),ПС.\n')
        assert window.run_program() is False
        assert (
            "не удалось запустить интерпретатор" in window.problems_text()
        ), ascii(window.problems_text())
        assert window.session.is_running() is False, "a missing binary must not start a session"
        print("ok: a missing interpreter is reported in the pane, and no session starts")
    finally:
        discard_changes(window)


def test_the_welcome_program_runs(executable: str) -> None:
    """task_112: the first tab holds a program that answers on the engine of this build.

    The text is what a reader sees before doing anything, so the one thing it must
    do is run: it loads `iso.pld` and asks `length/2` from it.
    """
    from prologd_gui.window import WELCOME_TEXT

    window = make_window(executable, ready=False)
    try:
        assert window.buffers()[0].text() == WELCOME_TEXT, "the first tab holds it"
        # The standard library has to be on the import path: a build tree has no
        # `stdlib` beside the executable (the package does), which is why the row is
        # filled here.
        window._settings.import_paths = [str(STDLIB)]
        window.apply_settings()
        window.run_program()
        wait_for_result(window)
        assert not window.problems_text().strip(), ascii(window.problems_text())
        # The questions of the welcome text: the library's `length/2` first, then the
        # program's own two.
        output = window.output_text()
        assert output == ("Д=3\nИ=вова\nФ=корчагин\nИ=данил\nФ=ахмеров\n"), ascii(output)
        print("ok: the welcome program loads the library and answers")
    finally:
        discard_changes(window)


def test_the_settings_dialog_opens_where_the_launch_points(
    executable: str, directory: pathlib.Path
) -> None:
    """The dialog's choosers open at the folder of *this* window's interpreter (task_80).

    A launch can pin another build (`--exe`, and the value of the removed
    «Интерпретатор» row), and the dialog has to describe the window in front of it
    rather than the one a plain search would find.
    """
    window = make_window(executable, ready=False)
    try:
        def drive(dialog) -> bool:
            assert dialog.windowTitle() == "Настройки", dialog.windowTitle()
            assert dialog._engine_directory == str(
                pathlib.Path(window._interpreter_path()).parent
            ), dialog._engine_directory
            return False

        window._run_settings_dialog = drive
        assert window.show_settings() is False, "nothing was accepted by this driver"
        print("ok: the dialog opens where this launch looks for the interpreter")
    finally:
        discard_changes(window)


def test_the_process_directory_is_where_files_go(
    executable: str, directory: pathlib.Path
) -> None:
    """task_46: `ЗАПИСЬ_В` writes into the chosen folder, relative paths and all.

    The two answers that matter for a lesson: a fixed folder («свой каталог»)
    for an unnamed buffer, and the running file's own folder («каталог файла»).
    """
    window = empty_window(executable)
    try:
        fixed = directory / "туда"
        fixed.mkdir()
        window._settings.process_directory = "custom"
        window._settings.process_directory_path = str(fixed)
        window.apply_settings()
        assert window.session.working_directory() == str(fixed)

        window.editor().setPlainText('?ЗАПИСЬ_В("данные.txt"), ВЫВОД("ок"), ПС, ЗАПИСЬ_В("").\n')
        window.run_program()
        assert pump(window, lambda: "решени" in window.status_text()), ascii(window.output_text())
        written = fixed / "данные.txt"
        assert written.is_file(), "the program wrote next to nothing"
        assert written.read_text(encoding="utf-8") == "ок\n"

        # A saved program writes next to itself under «каталог файла программы».
        program_dir = directory / "программа"
        program_dir.mkdir()
        program = program_dir / "пишет.pld"
        program.write_text(
            '?ЗАПИСЬ_В("файл.txt"), ВЫВОД("файл"), ПС, ЗАПИСЬ_В("").\n', encoding="utf-8"
        )
        window._settings.process_directory = "file"
        window.apply_settings()
        window.open_path(str(program))
        window.run_program()
        assert pump(window, lambda: "решени" in window.status_text()), ascii(window.output_text())
        beside = program_dir / "файл.txt"
        assert beside.is_file(), "the program did not write next to itself"
        assert beside.read_text(encoding="utf-8") == "файл\n"
        print("ok: the process directory decides where a program's files go")
    finally:
        discard_changes(window)


def test_a_saved_buffer_is_named_the_way_the_file_manager_wants(
    executable: str, directory: pathlib.Path
) -> None:
    """task_109: «Показать в проводнике» on a buffer saved from «Без имени».

    The save dialog answers with forward slashes («C:/dir/файл.pld»), and the buffer
    used to keep them: the title bar named a path no other tab had, and the file
    manager was handed `/select,C:/dir/файл.pld` — neither a switch nor a file to
    select.  A file *opened* from the same dialog went through `pathlib` and was
    native, which is why only a saved buffer went wrong.

    The entry itself follows the current tab now: off while the buffer has no file,
    on the moment it has one.
    """
    target = directory / "сохранённый буфер.pld"
    typed = str(target).replace(os.sep, "/")  # what `QFileDialog` answers

    window = empty_window(executable)
    try:
        assert window._actions["reveal"].isEnabled() is False, (
            "an unnamed buffer has no file to show"
        )

        window.editor().insertPlainText("факт(1).\n")
        assert window.save_buffer(path=typed) is True
        buffer = window.current_buffer()
        assert buffer.model.path == str(target), (
            f"{buffer.model.path!r} is not the native {str(target)!r}"
        )
        assert window.windowTitle() == f"{target} — PrologD", window.windowTitle()
        assert window._actions["reveal"].isEnabled() is True, (
            "the file exists now, so the entry has to be offered"
        )
    finally:
        discard_changes(window)
    print("ok: a saved buffer keeps the native path, and the tab menu knows it has a file")


def test_a_converted_program_is_unsaved_work(executable: str) -> None:
    """task_109: a tab the window filled itself carries the «unsaved» mark.

    A conversion answers with `setPlainText`, which clears Qt's flag, so the new tab
    looked like a file nobody had touched: no star, and — the real harm — no
    question when its text was about to be lost.  The owner found it with a
    picture converted at full detail: the generated program was bigger than the
    session can keep, and the window still closed without a word.
    """
    from PySide6.QtWidgets import QDialog

    from prologd_gui import documents
    from prologd_gui import window as window_module

    class Accepted:
        """The converter's dialog, answered at once with «ОК»."""

        def __init__(self, _parent: object) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def arguments(self) -> list[str]:
            return []

        def name(self) -> str:
            return "проба"

    window = empty_window(executable)
    asked: list[str] = []
    dialog = window_module.scriptdialog.ImageToPldDialog
    run = window_module.scripts.run
    try:
        # The converter itself has its own script (test_scripts.py); what is under
        # test here is the tab its answer lands in.
        window_module.scriptdialog.ImageToPldDialog = Accepted
        window_module.scripts.run = lambda _arguments: "факт(1).\n"
        assert window.convert_image() is True
        buffer = window.current_buffer()
        assert buffer.model.path is None, "a conversion opens an unnamed tab"
        assert buffer.is_modified() is True, "the generated text is in the tab only"
        assert buffer.model.title().startswith("*"), buffer.model.title()

        # And that is what makes the over-budget question possible at all: a text
        # the session cannot keep is asked about instead of vanishing.
        window._ask_save = lambda name: asked.append(name) or window_module.DISCARD
        window.editor().setPlainText("я" * (documents.SESSION_TEXT_BUDGET + 1))
        window.current_buffer().mark_modified()
        window.close()
        assert asked == [buffer.model.name], asked
    finally:
        window_module.scriptdialog.ImageToPldDialog = dialog
        window_module.scripts.run = run
        window.stop_program()
    print("ok: a generated program is unsaved work, and too big a one is asked about")


def test_the_document_opens_from_the_package(executable: str) -> None:
    """task_61: `Shift+F1` finds `doc/` beside the window, not inside the bundle.

    The path used to be counted up from `__file__`, and in a frozen package that
    is `_internal/prologd_gui/` - a folder whose neighbours are not the ones the
    reader sees.  Asked here of the window itself, with a package that exists on
    disk, and with the desktop service replaced by a list: opening a real PDF in
    a browser during a test would be as bad as the missing-file box it avoids.
    """
    from prologd_gui import window as window_module

    window = make_window(executable)
    try:
        with tempfile.TemporaryDirectory(prefix="prologd_package_") as name:
            package = make_package(pathlib.Path(name))
            manual = package / "doc" / "help.pdf"
            opened: list[str] = []

            class Opener:
                @staticmethod
                def openUrl(url) -> None:
                    opened.append(url.toLocalFile())

            real_service = window_module.QDesktopServices
            window_module.QDesktopServices = Opener
            try:
                with packaged(package):
                    window._open_document("help")
            finally:
                window_module.QDesktopServices = real_service
            # `QUrl.toLocalFile` answers with forward slashes on Windows, so the
            # two are compared as paths and not as text.
            assert [pathlib.Path(one) for one in opened] == [manual], opened
    finally:
        discard_changes(window)
    print("ok: the manual is opened from the package's own doc folder")


def test_the_tab_menu_shows_the_clicked_file(executable: str, directory: pathlib.Path) -> None:
    """A right click on a tab offers «Показать в проводнике» for *that* tab (task_68).

    The menu is built and not shown — `exec` waits for a click no test can make —
    and the seam that would open a file manager is replaced, so nothing but the
    window is exercised.  A right click does not switch tabs in Qt, so the tab the
    user pointed at has to become current first; otherwise the command would act on
    the tab that happened to be in front.
    """
    from prologd_gui import paths

    shown: list[str] = []
    original = paths.reveal
    # Patched *before* the window is built: the window takes the seam when it is
    # constructed, and assigning the attribute afterwards hid a missing one —
    # `_reveal_path` was never defined and the command crashed at the first click.
    paths.reveal = shown.append
    window = empty_window(executable)
    try:
        first = directory / "first.pld"
        second = directory / "second.pld"
        first.write_text("факт(1).\n", encoding="utf-8", newline="\n")
        second.write_text("факт(2).\n", encoding="utf-8", newline="\n")
        assert window.open_path(str(first))
        assert window.open_path(str(second))
        pane = window.active_pane()

        pane.setCurrentIndex(1)
        menu = window._prepare_tab_menu(pane, 0)
        assert pane.currentIndex() == 0, "the pointed-at tab is the one the menu acts on"
        assert [entry.text() for entry in menu.actions()] == ["Показать в проводнике"]
        assert menu.actions()[0].isEnabled(), "a saved file can be shown"
        menu.actions()[0].trigger()
        assert shown == [str(first)], shown

        # An unnamed buffer has no file to show, and the entry says so.
        window.new_buffer()
        anonymous = window._prepare_tab_menu(pane, pane.currentIndex())
        assert not anonymous.actions()[0].isEnabled()
        print("ok: the tab menu shows the clicked tab's file in the file manager")
    finally:
        paths.reveal = original
        discard_changes(window)


def test_the_output_tab_offers_clear(executable: str) -> None:
    """A right click on the «Вывод» tab offers «Очистить», and there alone (task_71).

    The titles of the panel's tabs carry a counter (`Вывод:5`), so the menu is built
    for the pane the tab shows and not for its text.  The entry is the shared
    `QAction` of the action table — the same one `Ctrl+L` reaches — and the other
    tabs have no command of their own, where a menu with nothing in it would be a
    puzzle.
    """
    window = empty_window(executable)
    try:
        tabs = window.panel_tabs()
        output = tabs.indexOf(window._output)
        assert output >= 0, "the panel carries the Вывод tab"
        window._append_output("строка вывода\n")
        assert window.output_text(), "there is something to clear"

        menu = window._prepare_panel_tab_menu(output)
        assert menu is not None
        assert [entry.text() for entry in menu.actions()] == ["Очистить вывод"]
        menu.actions()[0].trigger()
        assert window.output_text() == "", "the entry clears the pane"

        elsewhere = [index for index in range(tabs.count()) if index != output]
        assert window._prepare_panel_tab_menu(elsewhere[0]) is None, (
            "only the Вывод tab has a menu of its own"
        )
        print("ok: the output tab's menu clears the pane")
    finally:
        discard_changes(window)


def test_the_screen_size_setting_reaches_the_picture(executable: str) -> None:
    """«Ширина/высота графического экрана» decide the buffer a run draws on (task_73).

    The pair travels with the load, the interpreter makes its buffer that size, and
    the picture that comes back is that size as well: a cell inside it is drawn, and
    what the program asked for outside it is cut — a smaller screen crops the
    picture instead of moving it.
    """
    window = empty_window(executable)
    try:
        window._settings.screen_size = (40, 30)
        window.editor().setPlainText("?ТОЧКА(35, 25, 4), ТОЧКА(45, 25, 9).\n")
        window._actions["run"].trigger()
        assert pump(window, lambda: window.canvas().pixel(35, 25) == 4), window.output_text()
        canvas = window.canvas()
        assert (canvas.width, canvas.height) == (40, 30), (canvas.width, canvas.height)
        assert canvas.pixel(39, 29) == 0, "the screen is 40 × 30, and the rest is cut"
        print("ok: the screen size setting decides the size of the picture")
    finally:
        discard_changes(window)


def test_f12_opens_the_file_of_an_import_directive(executable: str, directory: pathlib.Path) -> None:
    """`F12` on an `ИМПОРТ` line opens the file it names, in a tab (task_69).

    The entry is enabled only where there is something to open, and the name is
    looked for the way the engine looks: beside the importing file first, then the
    `-I` directories, then `stdlib` beside the interpreter.
    """
    from PySide6.QtGui import QTextCursor

    window = empty_window(executable)
    try:
        library = directory / "library.pld"
        library.write_text("факт(1).\n", encoding="utf-8", newline="\n")
        program = directory / "program.pld"
        program.write_text(':- ИМПОРТ("library.pld").\n?факт(1).\n', encoding="utf-8",
                           newline="\n")
        assert window.open_path(str(program))
        view = window.active_pane().current_view()
        action = window._actions["open_import"]

        # Away from the directive there is nothing to open, and the entry says so.
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        view.setTextCursor(cursor)
        window._update_details()
        assert not action.isEnabled()

        # On the directive the key is offered and opens the library beside the program.
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        view.setTextCursor(cursor)
        window._update_details()
        assert action.isEnabled(), "the caret is on the ИМПОРТ line"
        action.trigger()
        opened = [buffer.model.path for buffer in window.buffers()]
        assert str(library) in opened, opened
        print("ok: F12 opens the file an ИМПОРТ directive names")
    finally:
        discard_changes(window)


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
    test_every_declared_key_belongs_to_a_widget(executable)
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
        test_print_questions_echoes_the_question_line(executable)
        test_the_input_switch_chooses_where_to_ask(executable)
        test_the_limits_stop_a_runaway_and_name_themselves(executable)
        test_the_time_limit_ends_a_run_that_cannot_be_interrupted(executable)
        test_a_flood_of_output_leaves_the_window_alive(executable)
        test_the_output_limit_stops_a_flood(executable)
        test_stop_silences_the_panes_during_a_flood(executable)
        test_a_run_after_a_stop_prints_again(executable)
        test_the_console_appears_only_when_it_is_asked(executable)
        test_the_console_stays_one_field_high(executable)
        test_a_request_keeps_the_panel_on_the_output(executable)
        test_the_panel_has_five_tabs_with_counts(executable)
        test_a_run_focuses_the_output_and_the_system_notes_the_time(executable)
        test_cancelling_input_stops_the_run(executable)
        test_a_run_uses_the_tab_that_is_showing(executable)
        test_the_split_editor_shares_one_document(executable)
        test_each_pane_has_its_own_current_tab(executable, files)
        test_merging_the_editor_keeps_the_documents(executable, files)
        test_the_split_survives_a_restart(executable)
        test_split_and_merge_follow_the_pane_count(executable)
        test_the_output_panel_moves_and_hides(executable)
        test_the_goal_field_hides_and_a_run_shows_the_output_panel(executable)
        test_the_graphics_window_follows_the_program(executable)
        test_a_run_that_draws_opens_the_picture_by_itself(executable)
        test_the_picture_takes_the_canvas_the_program_names(executable)
        test_escape_closes_the_picture_then_the_bar_then_the_docks(executable)
        test_the_menus_come_from_the_action_table(executable)
        test_the_toolbar_reuses_the_actions(executable)
        test_the_run_switches_are_in_the_menu_and_in_the_settings(executable)
        test_the_answer_table_switch_is_in_the_menu_and_in_the_settings(executable)
        test_a_marker_builds_the_answer_table(executable)
        test_the_table_separates_two_solutions(executable)
        test_the_table_shows_a_word_for_a_ground_query(executable)
        test_the_goal_line_builds_the_table_too(executable)
        test_the_table_is_not_built_when_it_is_switched_off(executable)
        test_a_diagnostic_keeps_the_panel_on_the_problems(executable)
        test_a_new_run_empties_the_table(executable)
        test_the_table_follows_the_output_font(executable)
        test_copy_over_the_table_takes_the_cells(executable)
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
        test_a_runtime_error_in_an_imported_file_opens_it(executable, files)
        test_the_problems_are_a_table_a_double_click_opens_the_line(executable, files)
        test_stepping_shows_the_goal_the_stack_and_the_line(executable)
        test_the_trace_is_coloured_apart_from_the_output(executable)
        test_a_long_trace_arrives_in_batches_and_stays_bounded(executable)
        test_the_window_remembers_its_size_and_place(executable)
        test_the_output_arrives_while_the_program_runs(executable)
        test_a_marker_answers_one_question_alone(executable)
        test_a_clicked_question_is_asked_once_the_load_has_answered(executable)
        test_a_question_is_not_asked_when_the_file_does_not_parse(executable)
        test_a_parked_question_still_reports_its_own_parse_error(executable)
        test_the_goal_line_loads_when_there_is_no_base(executable)
        test_the_goal_line_does_not_reload_a_loaded_base(executable)
        test_a_question_parked_in_a_comment_runs_from_the_margin(executable)
        test_a_marker_while_a_step_is_paused_starts_a_fresh_quiet_run(executable)
        test_a_failed_query_marks_no_line_and_moves_no_caret(executable)
        test_stopping_a_query_asks_first_and_keeps_the_base(executable)
        test_copy_takes_the_selection_where_the_focus_is(executable)
        test_the_step_strip_is_one_font_and_three_pictures(executable)
        test_formatting_lays_the_buffer_out_and_stays_one_undo_step(executable)
        test_formatting_only_the_selection(executable)
        test_formatting_a_selection_keeps_its_lines(executable)
        test_a_broken_program_is_reported_and_not_rewritten(executable)
        test_the_mode_control_stands_beside_the_command_it_changes(executable)
        test_the_reserved_names_are_there_before_the_first_run(executable)
        test_an_imported_file_reaches_the_popup(executable, files)
        test_f12_goes_to_the_first_clause_of_a_name(executable, files)
        test_the_import_string_completes_to_a_file_name(executable, files)
        test_the_directive_is_inserted_as_a_whole_statement(executable)
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
        test_the_launch_binary_names_the_build_folder(executable, files)
        test_a_missing_interpreter_is_reported_not_half_started(executable, files)
        test_the_welcome_program_runs(executable)
        test_the_settings_dialog_opens_where_the_launch_points(executable, files)
        test_the_process_directory_is_where_files_go(executable, files)
        test_autosave_writes_named_buffers_and_skips_the_rest(executable, files)
        test_saving_before_a_run_writes_the_file(executable, files)
        test_a_file_named_on_the_command_line_opens(executable)
        test_the_tabs_come_back_on_the_next_start(executable, files)
        test_an_unnamed_tab_left_unsaved_is_forgotten(executable, files)
        test_the_window_close_asks_only_about_files(executable, files)
        test_a_session_that_cannot_be_written_is_named(executable, files)
        test_a_saved_buffer_is_named_the_way_the_file_manager_wants(executable, files)
        test_a_converted_program_is_unsaved_work(executable)
        test_an_untouched_unnamed_tab_comes_back_clean(executable)
        test_the_document_opens_from_the_package(executable)
        test_the_tab_menu_shows_the_clicked_file(executable, files)
        test_the_output_tab_offers_clear(executable)
        test_the_screen_size_setting_reaches_the_picture(executable)
        test_f12_opens_the_file_of_an_import_directive(executable, files)
    print("all window checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
