"""Main window: panes of programs, a query line, the output and the input queue.

One program is one `Buffer` (a model, a text document and its views).  The window
owns the open documents; a `Pane` shows them in tabs, and the split editor is two
panes over the same set of documents — so the left pane can show one program while
the right shows another, and both views edit the same text.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QElapsedTimer, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QKeySequence,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import (
    actions,
    answers,
    appearance,
    assets,
    documents,
    findbar,
    formatter,
    geometry,
    graphics,
    graphicswindow,
    panels,
    reference,
    search,
    settings,
    settingsdialog,
    shortcuts,
)
from .buffers import Buffer
from .editor import CodeEditor, QueryLine, ZoomablePlainTextEdit
from .panes import Pane
from .session import PrologSession, read_keywords
from .settings import OUTPUT_FONT_SIZE, Settings

#: How long «Остановить» waits for the interpreter to end its query by itself
#: before the process is taken down (`stop_program`).
STOP_GRACE_MS = 500

WELCOME = """% PrologD — пример программы
студент(вова, корчагин).
студент(данил, ахмеров).

?студент(X, Y).
"""

#: The three answers to "save before closing?".
SAVE = "save"
DISCARD = "discard"
CANCEL = "cancel"


class MainWindow(QMainWindow):
    def __init__(
        self,
        executable: str,
        includes: list[str] | None = None,
        settings: Settings | None = None,
    ):
        super().__init__()
        self.setWindowTitle("PrologD")
        self.resize(1000, 700)

        #: Preferences; tests pass a file of their own so a run cannot touch the
        #: user's real settings.
        self._settings = settings if settings is not None else Settings()
        #: The interpreter `main.py` gave the window — the fallback `_interpreter_path`
        #: uses when the `execution/interpreter` row is empty (task_46).
        self._default_executable = executable
        #: The built-in reference (`doc/builtins.json`), read once for the whole
        #: window: the popup's detail label and `F1` read the same object, and a
        #: checkout without the file is an empty reference, not a failure.
        self._reference = reference.Reference.load()
        #: The `Ctrl`+key insertions (task_31).  The table is *data*: it is kept
        #: in the settings file (`shortcuts/table`), so a symbol on another
        #: physical key — or a keyboard without that key — is remapped without a
        #: code change.  A file that has no table gets the default written into
        #: it, which is what makes the table readable and editable at all.
        if not self._settings.shortcuts_table:
            self._settings.shortcuts_table = shortcuts.Shortcuts.default().to_json()
        self._shortcuts = shortcuts.Shortcuts.from_json(self._settings.shortcuts_table)
        #: The `-I` directories exactly as they arrived on the command line; the
        #: ones from the dialog (task_29) are added to them by
        #: `_import_directories`, since what the launcher was told is not a
        #: preference the dialog may quietly replace.
        self._command_line_includes = list(includes or [])

        self._session = PrologSession(self._interpreter_path(), self._import_directories(), self)
        # Completion, colouring and the cheat sheet need the reserved names
        # *before* anything is run — waiting for the first `ready` is why
        # autocompletion used to work only after the first run.  A window that
        # has only been opened must not keep an interpreter alive, so the table
        # is fetched once with `--list-keywords` (the same query the CLI answers)
        # and the first real session replaces it with the `ready` event's copy
        # of the same data.
        self._session.keywords = read_keywords(self._interpreter_path())
        self._session.ready.connect(self._on_ready)
        self._session.output.connect(self._append_output)
        self._session.result.connect(self._on_result)
        self._session.input_request.connect(self._on_input_request)
        self._session.failed.connect(self._on_failed)
        self._session.trace.connect(self._on_trace)
        self._session.stepped.connect(self._on_stepped)
        self._session.loaded.connect(self._on_loaded)
        self._session.formatted.connect(self._on_formatted)
        self._session.drawn.connect(self._on_drawn)
        self._session.bitmap.connect(self._on_bitmap)
        self._session.ended.connect(self._on_ended)

        #: Warnings seen in the current run, shown beside the answer; reset when
        #: the interpreter comes up, because every run starts a fresh one.
        self._warning_count = 0
        #: Errors seen in the current run (task_50).  Together with
        #: `_warning_count` they decide what the «Проблемы» tab says and how its
        #: title is painted — orange for warnings only, red once an error arrived.
        self._error_count = 0
        #: The clock of a run, started by «Запустить» and read by `_on_loaded`
        #: for the «база знаний загружена (N мс)» line (task_50).
        self._run_clock = QElapsedTimer()

        #: The open documents, in the order every pane shows them.  A pane has its
        #: own *current* tab, but the set and the order are shared: a tab dragged in
        #: one pane has to move in the other as well.
        self._buffers: list[Buffer] = []
        #: True while the whole window is closing, so closing the last document does
        #: not open a fresh one on the way out.
        self._closing = False
        #: Buffers the user refused to save («Не сохранять»), collected while the
        #: window closes.  An untitled one of these is left out of the session: the
        #: answer means the text is not to be seen again, and bringing it back on
        #: the next start would make the question a lie.
        self._discarded: list[Buffer] = []
        #: Answers taken from the input field, one per request; refilled by every
        #: run (see `run_program`).
        self._queued_input: list[str] = []
        #: Set when the user cancelled an input question: the run is stopped and
        #: nothing else is asked during it.
        self._stopped_input = False
        self._recent = documents.RecentFiles(
            self._settings.recent_files, max_size=self._settings.recent_limit
        )
        #: What the interpreter announced in `ready`, for «О программе».
        self._version = ""
        #: The exit code of the last run, shown in the status bar until the next one.
        self._exit_code: int | None = None
        #: True while a stop of our own is in flight, so the exit code it produces
        #: (a termination status, not an exit code) is not reported as one.
        self._stopping = False
        #: The deadline of a polite stop: the interpreter is asked to end its
        #: query first, and the process goes only if it does not (`stop_program`).
        self._stop_grace = QTimer(self)
        self._stop_grace.setSingleShot(True)
        self._stop_grace.timeout.connect(self._stop_expired)
        #: The deadline of a *run* (task_46): `execution/timeout_milliseconds`
        #: measured by the window, because the engine's hot loop must stay
        #: clock-free.  When it fires the run is asked to stop the same way the
        #: button asks.
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._on_timeout)
        #: The autosave timer (task_29).  Minutes in the settings, so the interval
        #: is re-armed by `_apply_autosave` whenever they change; a test drives
        #: `autosave_now` directly instead of waiting for it.
        self._autosave = QTimer(self)
        self._autosave.timeout.connect(self.autosave_now)
        #: Two states, not one: the interpreter is a process that can be *up* and
        #: idle, and a computation can be *in flight* in it.  `Запустить` needs the
        #: second (there is nothing to start while one is running) and `Остановить`
        #: the first (an idle interpreter still holds a knowledge base).
        self._busy = False
        #: Whether a program was loaded into the running interpreter (`run_program`).
        self._loaded = False
        #: How many questions of the current load have answered, whether an error
        #: concluded it, and whether a question is still to be sent after a quiet
        #: load (the margin's click).  Together with the `loaded` event they tell
        #: «the run is over» from «the answers are over», which used to be the
        #: same thing (protocol 8).
        self._results_in_load = 0
        self._failed_in_load = False
        self._awaiting_query = False
        #: The text of the answer being collected for the table (task_59), as the
        #: chunks arrived; `None` unless a single goal is being answered.  A chunk
        #: may end in the middle of a line, so splitting belongs to `answers.parse`
        #: and not here — the list holds what the interpreter sent, verbatim.
        self._answer_text: list[str] | None = None
        #: A question that is waiting for its load to answer (task_60): a margin
        #: marker and a goal typed into an empty window both send the program first
        #: and the question only once the load has succeeded.  Asking earlier meant
        #: answering against an empty knowledge base — «НЕТ» and a «не найдено»
        #: warning for a predicate that never loaded — and reporting one broken line
        #: twice, as the buffer's and as the query's.
        self._pending_query: str | None = None
        #: The picture of the graphics predicates (task_45).  The interpreter
        #: keeps its own pixels, so this canvas mirrors the screen: it is created
        #: the first time the graphics window is opened, and what happened before
        #: that is fetched as a snapshot — drawing 1024×768 cells for a reader who
        #: never opens the window would be work nobody asked for.
        self._canvas: graphics.Canvas | None = None
        self._graphics_window: graphicswindow.GraphicsWindow | None = None
        #: Whether this run has already had its say about the picture window
        #: (task_48).  A run that draws shows its picture by itself — the first
        #: primitive opens the window — but only once per run, so a 250-frame
        #: animation cannot reopen the window the user just closed.  `run_program`
        #: clears it; `show_graphics_window` sets it, whoever asked.
        self._graphics_shown = False
        #: The `format` request that is in flight (task_30): what was sent, where
        #: it came from and where the caret stood.  The answer arrives as an
        #: event, so this state outlives the call that started it.
        self._format_pending: dict | None = None

        #: Output that the current turn has produced and the pane has not been
        #: given yet (task_49), as `(kind, text)` in arrival order.  A trace of a
        #: deep recursion arrives as hundreds of thousands of small events, and one
        #: `feed` per event costs some 30 us of Python on top of the insertion —
        #: enough to starve the window.  `_flush_output` joins the neighbours of one
        #: kind, which is the whole trace, into a single call.
        self._output_pending: list[tuple[str, str]] = []
        self._output_timer = QTimer(self)
        self._output_timer.setSingleShot(True)
        self._output_timer.setInterval(0)
        self._output_timer.timeout.connect(self._flush_output)

        self._build_ui()
        # The window's own size and place come back too (task_49): the graphics
        # window has remembered its own since task_45, and the main window — the one
        # the user moves first — did not, which is what the user ran into.  Restored
        # *after* the widgets exist: `restoreGeometry` needs a window to put back.
        self.restore_window_geometry()
        # The autosave interval the settings ask for; a change in the dialog
        # re-arms it through `apply_settings`.
        self._apply_autosave()
        # The picture window comes back where it was (task_45): it is a window of
        # its own and can stand on a second screen, so where it stood is part of
        # what the settings file remembers.
        if self._settings.graphics_visible:
            self.show_graphics_window(True)
        # The split editor comes back if it was left open, and before the first
        # document, so the welcome program is shown in both panes on that start.
        if self._settings.restore_split and self._settings.split_editor:
            self.split_editor(remember=False, sizes=self._settings.split_sizes)
        # The tabs of the previous run (task_29) come back before anything else;
        # the welcome program is for a window with no session to show.
        if self._settings.restore_tabs:
            self._restore_session()
        if not self._buffers:
            # The welcome program goes into the first tab and is *not* unsaved work
            # — the flag is left clear, so closing it asks nothing.
            welcome = documents.Document.untitled(documents.untitled_name([]))
            welcome.text = WELCOME
            self._add_buffer(welcome)
        # No interpreter yet: it is started by the first run (or by a query typed
        # into the query line).  A window that has been opened but not used has
        # nothing running, and saying otherwise made `Остановить` look live.

    # -- construction ------------------------------------------------------
    def _build_ui(self) -> None:
        # The editor area holds one pane, or two after «Разделить редактор».  The
        # panes themselves are made at the end of this method, when the status bar
        # they report to exists.
        self._panes: list[Pane] = []
        self._active_pane = 0
        self._editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        # The output panel (task_50): three read-only panes — Проблемы, Вывод,
        # Система — and the Ввод tab with the prepared answers and, under them,
        # the per-request console.  All three are `OutputPane`, so the bounded
        # history, the colours per kind and the tail they hold reach every tab
        # the same way.
        self._problems = panels.OutputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
            line_limit=self._settings.output_line_limit,
        )
        self._problems.set_palette(self._settings.palette)
        self._problems.setPlaceholderText("ошибки и предупреждения интерпретатора")
        self._problems.zoomChanged.connect(self._on_output_zoom)
        self._problems.fileDropped.connect(self.open_path)

        self._output = panels.OutputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
            line_limit=self._settings.output_line_limit,
        )
        self._output.set_follow_output(self._settings.follow_output)
        self._output.set_palette(self._settings.palette)
        self._output.setPlaceholderText("вывод интерпретатора")
        self._output.zoomChanged.connect(self._on_output_zoom)
        # A dropped program opens in a tab wherever it lands (see `dropEvent`).
        self._output.fileDropped.connect(self.open_path)

        self._system = panels.OutputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
            line_limit=self._settings.output_line_limit,
        )
        self._system.set_palette(self._settings.palette)
        self._system.setPlaceholderText("сообщения окна: загрузка, пределы, остановка")
        self._system.zoomChanged.connect(self._on_output_zoom)
        self._system.fileDropped.connect(self.open_path)

        # The input queue: one line per answer the program will ask for, fed
        # automatically until the list runs out (`_input_lines`).  It is user
        # data, so a run never clears it — only its copy is consumed.
        self._input_pane = ZoomablePlainTextEdit(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
        )
        self._input_pane.setPlaceholderText("ввод: по строке на каждый запрос")
        self._input_pane.setToolTip(
            "Строки для ВВКОД, ВВОДСТР, ВВОДСИМВ и подобных: по одной на каждый запрос.\n"
            "Пустые строки пропускаются. Когда строки кончатся, окно спросит в диалоге."
        )
        self._input_pane.zoomChanged.connect(self._on_output_zoom)
        self._input_pane.fileDropped.connect(self.open_path)
        # The «Ввод:N» tab title follows the prepared lines as they are typed.
        self._input_pane.textChanged.connect(self._refresh_panel_tabs)

        # The console: what the program asks once the prepared lines run out.
        # It sits under the goal field (task_50: moved out of the Ввод tab, so
        # a request appears without leaving the Вывод tab).  `Ctrl+Enter` sends;
        # «Остановить» is how a run that waits for an answer is abandoned.
        self._input_console = panels.InputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
        )
        self._input_console.submitted.connect(self._send_input)

        # The answer table (task_59): a grid of the answer to a *single* goal —
        # columns are the goal's variables, rows are the solutions.  It is not a
        # view of the text (no `kind` reaches it), but it is read next to the log
        # it came from, so it takes the output's font and the same wheel.
        self._table = panels.TablePane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
        )
        self._table.setToolTip(
            "Таблица ответа: столбцы — переменные цели, строки — решения.\n"
            "Строится для отдельного запроса: цели в строке запроса или клика по маркеру."
        )
        self._table.set_palette(self._settings.palette)
        self._table.zoomChanged.connect(self._on_output_zoom)

        # The goal field (task_50): its own history (Up/Down, twenty commands)
        # and the editor's completion — the reserved names and the current
        # document's predicates, with the same call-form insertion.
        self._query_line = QueryLine(document_text=lambda: self._current_document_text())
        # The same face as the program, because a goal is typed like one;
        # `_sync_query_line_font` keeps it in step with the editor's size.
        self._sync_query_line_font()
        self._query_line.setPlaceholderText(
            "?цель(X). — Enter: выполнить · ↑/↓: история · Ctrl+Пробел: подсказки"
        )
        self._query_line.set_completion_keywords(self._session.keywords)
        self._query_line.set_auto_complete_after(self._settings.auto_complete_after)
        self._query_line.set_completion_match_case(self._settings.completion_match_case)
        self._query_line.returnPressed.connect(self._run_query)

        # The step pane (task_28): what a stepped run is doing, where it stands and
        # the call stack the window rebuilds from the points the interpreter
        # reports.  Hidden while nothing is stepped through, like the console.
        self._step_stack: list[str] = []
        self._step_pane = panels.StepPane(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._step_pane.resumed.connect(self.step_continue)
        self._step_pane.stepped.connect(self.step_into)
        self._step_pane.stopped.connect(self.stop_program)

        # The reference of a predicate (task_37, `F1`): a dock, not a modal box —
        # the manual is read *next to* the code, and a modal cannot be driven
        # from a headless test.  It zooms with everything else and starts hidden.
        self._reference_pane = ZoomablePlainTextEdit(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._reference_pane.setReadOnly(True)
        self._reference_pane.setPlaceholderText("Справка по предикату: F1 на имени")
        self._reference_pane.zoomChanged.connect(self._on_zoom_changed)
        self._reference_dock = QDockWidget("Справка по предикату", self)
        self._reference_dock.setObjectName("referenceDock")
        self._reference_dock.setWidget(self._reference_pane)
        self._reference_dock.setVisible(False)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._reference_dock)

        # The cheat sheet of the insert chords (task_31): the same shape as the
        # reference dock, and it zooms with everything else.
        self._shortcut_pane = ZoomablePlainTextEdit(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._shortcut_pane.setReadOnly(True)
        self._shortcut_pane.setPlaceholderText("Шпаргалка: Справка → Шпаргалка по вставкам")
        self._shortcut_pane.zoomChanged.connect(self._on_zoom_changed)
        self._shortcut_dock = QDockWidget("Шпаргалка по вставкам", self)
        self._shortcut_dock.setObjectName("shortcutDock")
        self._shortcut_dock.setWidget(self._shortcut_pane)
        self._shortcut_dock.setVisible(False)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._shortcut_dock)

        # The find bar (task_33): a strip above the editor, hidden until `Ctrl+F`.
        # Not a dialog — a modal box covers the text being searched and cannot be
        # driven from a headless test.
        self._find_bar = findbar.FindBar()
        self._find_bar.changed.connect(self._on_find_changed)
        self._find_bar.stepRequested.connect(self._find_step_from_bar)
        self._find_bar.replaceRequested.connect(self.replace_current)
        self._find_bar.replaceAllRequested.connect(self.replace_all)
        self._find_bar.closeRequested.connect(self.close_find)
        self._find_bar.spanToggled.connect(self._on_find_span_toggled)

        #: What the last search found, and which of those the caret is on.  Where
        #: the next step starts from is derived from that match, not stored: the
        #: step continues *after* the match forwards and *before* it backwards.
        self._find_matches: list[int] = []
        self._find_current: int | None = None
        #: The span «Только в выделении» was switched on over — taken once, because
        #: the search moves the selection it would otherwise be read from.
        self._find_span: tuple[int, int] | None = None
        #: The buffer whose views carry the highlight, so the previous one is cleared.
        self._find_highlighted: Buffer | None = None
        #: The view whose text changes keep the matches fresh while the bar is open.
        self._find_bound: CodeEditor | None = None

        editor_area = QWidget()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._find_bar)
        editor_layout.addWidget(self._editor_splitter)
        editor_layout.addWidget(self._step_pane)
        editor_layout.addWidget(self._query_line)
        # The per-request console lives under the goal line: it appears where the
        # question is answered, without moving the panel off the Вывод tab.
        editor_layout.addWidget(self._input_console)

        # The tabbed output panel (task_50): one `QTabWidget` with the three
        # read-only panes, the Ввод tab and, since task_59, the answer table.
        # `F4` hides the whole panel, `Ctrl+F4` moves it — the pair of commands the
        # reference front-end had, now arranged as "one splitter with two
        # orientations" around a tab widget.
        self._editor_area = editor_area
        self._input_tab = QWidget()
        input_layout = QVBoxLayout(self._input_tab)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(2)
        input_layout.addWidget(self._input_pane, 1)

        self._panel_tabs = QTabWidget()
        self._panel_tabs.setDocumentMode(True)
        self._panel_tabs.addTab(self._problems, "Проблемы")
        self._panel_tabs.addTab(self._output, "Вывод")
        self._panel_tabs.addTab(self._system, "Система")
        self._panel_tabs.addTab(self._input_tab, "Ввод")
        self._panel_tabs.addTab(self._table, "Таблица")
        self._refresh_panel_tabs()

        # One splitter, two orientations: side by side when the panel is on the
        # right, stacked when it is at the bottom.  The order (editor first) is the
        # same either way, so the turn is only an orientation change.
        self._panel_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._panel_splitter.addWidget(self._editor_area)
        self._panel_splitter.addWidget(self._panel_tabs)
        # A pane may not be dragged away to nothing: an output panel squeezed to
        # zero pixels looks like a lost window rather than a hidden one.
        self._panel_splitter.setChildrenCollapsible(False)
        self._editor_area.setMinimumWidth(240)
        self._panel_tabs.setMinimumWidth(200)
        self._panel_tabs.setMinimumHeight(120)
        self.setCentralWidget(self._panel_splitter)
        self._apply_output_position(remember=False)
        self._panel_tabs.setVisible(self._settings.output_visible)
        # The application picture: the title bar and the taskbar, and the icon any
        # Qt-made dialog asks for (the about box sets its own).
        picture = assets.icon(actions.APPLICATION_ICON)
        if picture is not None:
            self.setWindowIcon(picture)
        # A dropped program opens in its own tab; see `dropEvent`.
        self.setAcceptDrops(True)

        self._build_actions()
        self._build_toolbar()
        self._build_menus()

        self._status = QLabel("запуск…")
        self.statusBar().addWidget(self._status)
        # The right-hand side of the status bar: what the interpreter is doing, where
        # the caret is, and how the current file is written.
        self._details = QLabel("")
        self.statusBar().addPermanentWidget(self._details)

        # The first pane, always: the window never has no place to edit in.
        self._add_pane()
        self._sync_actions()
        self._update_details()

    # -- the interpreter and its working directory (task_46) ---------------
    def _interpreter_path(self) -> str:
        """The `prologd` a run starts: the row, or the one the window was given."""
        row = self._settings.interpreter.strip()
        return row or self._default_executable

    def _process_working_directory(self) -> str:
        """Where the child process starts; `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` are relative to it.

        `file` is the folder of the running file (a new, unsaved buffer has none
        and falls through to `window`), `window` is the window's own folder — the
        old behaviour — and `custom` is the `execution/process_directory_path` row.
        `""` means «inherit», which `QProcess` reads as the calling process's own.
        """
        mode = self._settings.process_directory
        if mode == "custom":
            return self._settings.process_directory_path.strip()
        if mode == "file":
            buffer = self.current_buffer()
            path = buffer.model.path if buffer is not None else None
            if path:
                return str(pathlib.Path(path).parent)
        return ""

    def _start_session(self) -> bool:
        """Starts the interpreter with the current path and working directory.

        One gate for every place a fresh session begins (a run, a query, a
        format): the rows of task_46 change *which* interpreter starts and *where*
        its files go, and a missing path is reported here — in the pane, before
        the process is asked to start at all — instead of by a silent half-started
        process.
        """
        executable = self._interpreter_path()
        self._session.set_executable(executable)
        self._session.set_working_directory(self._process_working_directory())
        if not pathlib.Path(executable).is_file():
            self._append_output(
                f"*** не удалось запустить интерпретатор: {executable}\n", panels.ERROR
            )
            self._status.setText(
                f"интерпретатор не найден: {pathlib.Path(executable).name}"
            )
            return False
        self._session.start()
        return True

    # -- commands ----------------------------------------------------------
    def _build_actions(self) -> None:
        """One `QAction` per entry of `actions.ACTIONS`, kept by key.

        Built once and reused by the menus, the toolbar and the editor's context
        menu: that is what keeps a shortcut, a tooltip and an enabled state from
        existing in three versions.  An entry whose icon file is missing becomes a
        text-only button (`assets.icon` returns `None` and reports it once).
        """
        self._actions: dict[str, QAction] = {}
        for spec in actions.ACTIONS:
            action = QAction(spec.title, self)
            if spec.icon:
                found = assets.icon(spec.icon)
                if found is not None:
                    action.setIcon(found)
            if spec.shortcuts:
                action.setShortcuts([QKeySequence(key) for key in spec.shortcuts])
            action.setCheckable(spec.checkable)
            action.setEnabled(spec.implemented)
            hint = spec.tooltip()
            action.setToolTip(hint)
            action.setStatusTip(hint)
            if spec.implemented:
                slot = self._slot_for(spec.key)
                if spec.checkable:
                    action.toggled.connect(slot)
                else:
                    action.triggered.connect(slot)
            self._actions[spec.key] = action

    def _slot_for(self, key: str):
        """The method an action runs — one place, so nothing is wired twice."""
        return {
            "new": lambda: self.new_buffer(),
            "open": self._open_file,
            "save": lambda: self.save_buffer(),
            "save_as": self._save_as,
            "save_all": self._save_all,
            "save_output": self._save_output,
            "reload": self.reload_buffer,
            "close": self._close_current,
            "close_all": self._close_all_tabs,
            "exit": self.close,
            "undo": self._undo,
            "redo": self._redo,
            "cut": self._cut,
            "copy": self._copy,
            "paste": self._paste,
            "delete": self._delete,
            "delete_line": self._delete_line,
            "select_all": self._select_all,
            "comment": self._comment,
            "uncomment": self._uncomment,
            "format": self.format_document,
            "settings": self.show_settings,
            "shortcuts": self.show_shortcuts,
            "reference": self.show_reference,
            "clear_output": self.clear_output,
            "find": lambda: self.show_find(),
            "find_next": lambda: self.find_step(False),
            "find_prev": lambda: self.find_step(True),
            "toolbar": self._toggle_toolbar,
            "output": self._toggle_output,
            "graphics": self.show_graphics_window,
            "split": self.split_editor,
            "merge": self.merge_editor,
            "next_tab": self._next_tab,
            "previous_tab": self._previous_tab,
            "split_orientation": self.flip_output_position,
            "line_numbers": self._toggle_line_numbers,
            "wrap": self._toggle_wrap,
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "zoom_reset": self._reset_zoom,
            "full_screen": self._toggle_full_screen,
            "run": lambda: self.run_program(),
            "run_trace": lambda: self.run_program(trace=True),
            "step": self.step_into,
            "step_over": self.step_over,
            "stop": self.stop_program,
            "save_before_run": self._toggle_save_before_run,
            "run_questions": self._toggle_run_questions,
            "print_questions": self._toggle_print_questions,
            "answer_table": self._toggle_answer_table,
            "help_doc": lambda: self._open_document("help"),
            "help_gui": lambda: self._open_document("gui"),
            "about": self._about,
        }[key]

    def _build_toolbar(self) -> None:
        """The toolbar, from `actions.TOOLBAR`.

        The icons are 64 px files drawn at 24: the size is set explicitly so the
        layout does not depend on the style or the display's scaling.
        """
        self._toolbar = QToolBar("Управление", self)
        self._toolbar.setIconSize(QSize(24, 24))
        for key in actions.TOOLBAR:
            if key == actions.SEPARATOR:
                self._toolbar.addSeparator()
            elif key == actions.FORMAT_MODE:
                self._toolbar.addWidget(self._build_format_button())
            else:
                self._toolbar.addAction(self._actions[key])
        self._toolbar.setVisible(self._settings.toolbar_visible)
        self.addToolBar(self._toolbar)

    def _build_format_button(self) -> QToolButton:
        """The formatter's mode, on the toolbar beside «Форматировать» (task_47).

        A `QToolButton` with a menu of its own: the three modes and «только
        выделенное», the same values the settings dialog edits.  It lived in the
        «Правка» submenu since task_30, and before that it was a toolbar button —
        the mode is changed *while looking at the code*, so it stands next to the
        command it changes.  The picture (`edit-format-set`) is the one the
        reference front-end used for exactly this.
        """
        button = QToolButton(self)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        found = assets.icon(actions.FORMAT_ICON)
        if found is not None:
            button.setIcon(found)
        button.setToolTip("Режим форматирования")
        button.setMenu(self._build_format_menu("Формат"))
        self._format_button = button
        return button

    def _build_format_menu(self, title: str) -> QMenu:
        """The formatter's mode and its «только выделенное» switch (task_30, task_47).

        The modes themselves are a preference (the settings dialog edits the same
        keys), so this menu is a *view* of those values — and the only place they
        are changed besides the dialog, which is why it hangs off the toolbar
        button rather than sitting two levels deep in a menu.
        """
        menu = QMenu(title, self)
        self._format_menu = menu
        group = QActionGroup(self)
        group.setExclusive(True)
        self._format_mode_actions: dict[str, QAction] = {}
        for value, entry_title in (
            ("line", "В одну строку — цели тела собираются в строку"),
            ("soft", "Мягкое — переносить то, что не влезло"),
            ("hard", "Жёсткое — по цели на строку"),
        ):
            entry = menu.addAction(entry_title)
            entry.setCheckable(True)
            entry.setActionGroup(group)
            entry.triggered.connect(
                lambda _checked=False, mode=value: self._set_format_mode(mode)
            )
            self._format_mode_actions[value] = entry
        menu.addSeparator()
        self._format_selection_action = menu.addAction("Только выделенное")
        self._format_selection_action.setCheckable(True)
        self._format_selection_action.toggled.connect(self._set_format_selection)
        self._sync_format_menu()
        return menu

    def _sync_format_menu(self) -> None:
        """Shows the stored mode without answering for it."""
        if not hasattr(self, "_format_menu"):
            return
        mode = self._settings.format_mode
        for value, entry in self._format_mode_actions.items():
            entry.blockSignals(True)
            entry.setChecked(value == mode)
            entry.blockSignals(False)
        self._format_selection_action.blockSignals(True)
        self._format_selection_action.setChecked(self._settings.format_selection)
        self._format_selection_action.blockSignals(False)

    def _set_format_mode(self, mode: str) -> None:
        self._settings.format_mode = mode
        self._sync_format_menu()

    def _set_format_selection(self, flag: bool) -> None:
        self._settings.format_selection = bool(flag)
        self._sync_format_menu()

    def _build_theme_menu(self, title: str) -> QMenu:
        """The appearance: light, dark or the platform's own (task_29).

        Three choices need a menu of their own — one checkable entry could only say
        «system or not», which was true while there were two themes.  Each entry is
        a promise about *all* of the window: the widget palette
        (`appearance.qt_palette`), the syntax colours and the bands of the editor,
        and the colours of the output pane, all from one `theme.Palette`.
        """
        menu = QMenu(title, self)
        self._theme_menu = menu
        group = QActionGroup(self)
        group.setExclusive(True)
        self._theme_actions: dict[str, QAction] = {}
        for value, entry_title in (
            (appearance.LIGHT, "Светлое"),
            (appearance.DARK, "Тёмное"),
            (appearance.SYSTEM, "Системное"),
        ):
            entry = menu.addAction(entry_title)
            entry.setCheckable(True)
            entry.setActionGroup(group)
            entry.triggered.connect(lambda _checked=False, name=value: self._set_theme(name))
            self._theme_actions[value] = entry
        self._sync_theme_menu()
        return menu

    def _sync_theme_menu(self) -> None:
        """Shows the stored theme without answering for it."""
        if not hasattr(self, "_theme_menu"):
            return
        for value, entry in self._theme_actions.items():
            entry.blockSignals(True)
            entry.setChecked(value == self._settings.theme)
            entry.blockSignals(False)

    def _set_theme(self, name: str) -> None:
        """Writes the theme and shows it at once — widgets *and* text."""
        self._settings.theme = name
        self._sync_theme_menu()
        self.apply_settings()

    def _build_menus(self) -> None:
        """The menu bar, from `actions.MENUS`."""
        bar = self.menuBar()
        for title, entries in actions.MENUS:
            menu = bar.addMenu(title)
            for key in entries:
                if key == actions.SEPARATOR:
                    menu.addSeparator()
                elif key == actions.RECENT:
                    found = assets.icon(actions.RECENT_ICON)
                    self._recent_menu = (
                        menu.addMenu(found, "Последние файлы")
                        if found is not None
                        else menu.addMenu("Последние файлы")
                    )
                    self._recent_menu.aboutToShow.connect(self._fill_recent_menu)
                elif key == actions.FORMAT_MODE:
                    # On the toolbar now (task_47): the menus walk past it.
                    continue
                elif key == actions.THEME_MODE:
                    menu.addMenu(self._build_theme_menu("Оформление"))
                else:
                    menu.addAction(self._actions[key])

    def _apply_context_actions(self) -> None:
        """Gives every view the shared editing actions as its context menu."""
        for pane in self._panes:
            for buffer in pane.buffers():
                view = pane.view_for(buffer)
                if view is None or view.property("prologdContext"):
                    continue
                view.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
                for key in actions.CONTEXT:
                    if key == actions.SEPARATOR:
                        separator = QAction(self)
                        separator.setSeparator(True)
                        view.addAction(separator)
                    else:
                        view.addAction(self._actions[key])
                view.setProperty("prologdContext", True)

    def _sync_undo_actions(self) -> None:
        """Undo and redo say whether there is anything to undo *in the tab that
        is showing*.

        The commands are in a menu and on the keyboard, so a greyed-out «Отменить»
        with something to undo is a lie the user notices immediately — and an
        enabled one that does nothing is just as bad.
        """
        buffer = self.current_buffer()
        document = buffer.document if buffer is not None else None
        self._actions["undo"].setEnabled(document is not None and document.isUndoAvailable())
        self._actions["redo"].setEnabled(document is not None and document.isRedoAvailable())

    def _on_tab_changed(self, _index: int) -> None:
        """The tab that is showing decides the title and what can be undone.

        A plain tab click used to leave both stale: only an edit refreshed them.
        The handler is called while a pane is being dismantled as well — a tab
        being removed raises it — and there the window is between states.
        """
        if not self._panes or self._active_pane >= len(self._panes):
            return
        self._refresh_titles()
        self._sync_undo_actions()
        self._update_details()
        # The find bar follows the tab that is showing: another tab is another text.
        self._refollow_find()

    def _sync_run_actions(self) -> None:
        """Two states, two buttons.

        `Запустить` is for a computation that is not in flight — it restarts the
        whole file, whether the interpreter is idle with a base loaded or gone
        altogether.  `Остановить` is for a live process: stopping an idle one is
        how the knowledge base is unloaded, which is what its message says.

        The deadline of a run (task_46) is dropped here as well: every path that
        ends a run comes through this method, and a timer that outlived its run
        would stop the *next* one.
        """
        if not self._busy:
            self._timeout.stop()
        # A *paused* step is a usable state, not a busy one: «Запустить» then
        # means «продолжить», and «Шаг», «Шаг с обходом» and the traced run have
        # to be live, or their keys are dead exactly when the user needs them — a
        # disabled `QAction` fires no shortcut.  A run actually in flight is the
        # blocked state.  (The paused case is written out here on purpose: it
        # used to work only because the status of a *restart* cleared the busy
        # flag, which the flag ordering of `run_program` then fixed.)
        free = not self._busy or self._session.paused()
        self._actions["run"].setEnabled(free)
        self._actions["stop"].setEnabled(self._session.is_running())
        self._actions["run_trace"].setEnabled(free)
        self._actions["step"].setEnabled(free)
        self._actions["step_over"].setEnabled(free)

    def _update_details(self) -> None:
        """The right-hand side of the status bar: state, caret, file shape."""
        if not self._session.is_running():
            state = "интерпретатор остановлен"
        elif self._session.paused():
            state = "остановлен на шаге"
        elif self._busy:
            state = "выполняется"
        elif self._loaded:
            state = "база знаний загружена"
        else:
            state = "интерпретатор запущен"
        parts = [state]
        # The interpreter a run will actually start, when the rows named a
        # different build (task_46): what the command line chose is invisible, so
        # a window that runs another `prologd` has to say so.
        row = self._settings.interpreter.strip()
        if row:
            parts.append(f"prologd: {row}")
        buffer = self.current_buffer()
        if buffer is not None:
            view = self.view_for(buffer)
            if view is not None:
                cursor = view.textCursor()
                parts.append(
                    f"строка {cursor.blockNumber() + 1}, столбец {cursor.positionInBlock() + 1}"
                )
            parts.append("CRLF" if buffer.model.eol == documents.EOL_CRLF else "LF")
            parts.append(buffer.model.encoding)
        if self._exit_code is not None:
            parts.append(f"код {self._exit_code}")
        self._details.setText(" · ".join(parts))

    def _sync_pane_actions(self) -> None:
        """`split` and `merge` follow the number of panes.

        Not cosmetic: both carry a key (`Ctrl+\\` and `Ctrl+Shift+\\`), and a
        *disabled* `QAction` does not fire its shortcut — so without this call
        right after a split or a merge the key that undoes it goes dead, and the
        menu entry stays greyed out.  That is exactly how «Разделить и объединить»
        broke: the state was only ever computed on start-up.
        """
        self._actions["split"].setEnabled(len(self._panes) < 2)
        self._actions["merge"].setEnabled(len(self._panes) > 1)

    def _sync_actions(self) -> None:
        """Makes the checkable entries agree with the settings and the panes."""
        # `isHidden`, not `isVisible`: a toolbar of a window that was never shown
        # is not visible either, and reading that as "the user hid it" would write
        # the wrong preference on the first start.
        self._actions["toolbar"].setChecked(not self._toolbar.isHidden())
        self._actions["line_numbers"].setChecked(self._settings.line_numbers)
        self._actions["wrap"].setChecked(self._settings.wrap)
        self._actions["save_before_run"].setChecked(self._settings.save_before_run)
        self._actions["run_questions"].setChecked(self._settings.run_questions)
        self._actions["print_questions"].setChecked(self._settings.print_questions)
        self._actions["answer_table"].setChecked(self._settings.answer_table)
        self._actions["full_screen"].setChecked(self.isFullScreen())
        self._actions["output"].setChecked(self.output_visible())
        self._actions["graphics"].setChecked(self._settings.graphics_visible)
        self._sync_pane_actions()
        self._sync_undo_actions()
        self._sync_run_actions()

    # -- editing commands of the current view ------------------------------
    def _undo(self) -> None:
        self.editor().undo()

    def _redo(self) -> None:
        self.editor().redo()

    def _cut(self) -> None:
        self.editor().cut()

    def _copy(self) -> None:
        """`Ctrl+C` copies the selection of wherever the user is looking.

        The command is a window-wide shortcut, so it fires while the *output*
        pane has the focus — and copying the editor's selection there copied text
        the user was not looking at, or nothing at all.  The output is read-only,
        so copying out of it is the one operation it owes beside reading.  The
        answer table (task_59) is the same case with another shape: its cells are
        not a document, so its selection is turned into text here — columns with
        `Tab`, rows with a newline, which is what a spreadsheet reads.
        """
        focused = QApplication.focusWidget()
        if isinstance(focused, panels.TablePane):
            # Nothing selected, nothing copied — like the panes, and unlike the
            # editor, whose `copy()` would then copy *its* selection.
            text = focused.copy_selection()
            if text:
                QApplication.clipboard().setText(text)
            return
        if focused is not None and focused is not self.editor() and isinstance(
            focused, (ZoomablePlainTextEdit, QLineEdit)
        ):
            focused.copy()
            return
        self.editor().copy()

    def _paste(self) -> None:
        self.editor().paste()

    def _delete(self) -> None:
        self.editor().textCursor().removeSelectedText()

    def _delete_line(self) -> None:
        self.editor().delete_lines()

    def _select_all(self) -> None:
        self.editor().selectAll()

    def _zoom_in(self) -> None:
        self.editor().zoom_by(1)

    def _zoom_out(self) -> None:
        self.editor().zoom_by(-1)

    # -- view switches -----------------------------------------------------
    def _toggle_toolbar(self, checked: bool) -> None:
        self._toolbar.setVisible(checked)
        self._settings.toolbar_visible = checked

    def _toggle_line_numbers(self, checked: bool) -> None:
        self._settings.line_numbers = checked
        for buffer in self._buffers:
            buffer.set_line_numbers(checked)

    def _toggle_wrap(self, checked: bool) -> None:
        """Wraps long lines in the editor; the output pane never wraps."""
        self._settings.wrap = checked
        for buffer in self._buffers:
            buffer.set_wrap(checked)

    def _toggle_save_before_run(self, checked: bool) -> None:
        self._settings.save_before_run = checked

    def _toggle_run_questions(self, checked: bool) -> None:
        """The menu switch of «Выполнять вопросы при запуске» (task_58).

        It writes the same setting the dialog shows (`execution/run_questions`),
        so the two are one switch in two places and cannot drift: the dialog
        re-reads the file when it is opened, and `_sync_actions` puts the setting
        back into the menu.
        """
        self._settings.run_questions = checked

    def _toggle_print_questions(self, checked: bool) -> None:
        """The menu switch of «Печатать вопросы при запуске» (task_58)."""
        self._settings.print_questions = checked

    def _toggle_answer_table(self, checked: bool) -> None:
        """The menu switch of «Формировать таблицу» (task_59).

        Like its two neighbours, it writes the setting the dialog shows
        (`execution/answer_table`), so the two doors cannot drift apart.  The
        switch changes what the *next* single goal does: the table of the answer
        already on the screen is left as it is — it is a record of what happened,
        not a view that has to agree with a preference.
        """
        self._settings.answer_table = checked

    def _toggle_full_screen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def about_text(self) -> str:
        """What «О программе» says.  Separate from the box so a test can read it
        without a modal window it cannot close.

        The title names the shell, not the interpreter: the window is one of the
        front-ends of Пролог-Д, and which interpreter answers is the line below it
        (`ready`'s version, so it is the live one).  The names are the people who
        wrote the previous implementation — «АБВГД» is their five initials — and
        they are printed as they were given; the `--` column is padded with spaces,
        which is as straight as a proportional font allows (task_58).
        """
        return (
            "Графическая оболочка Пролог-Д 2.0\n"
            f"Интерпретатор: {self._version or 'ещё не ответил'}\n\n"
            "Эту реализацию Пролога-Д разработали АБВГД:\n"
            "Алексеев Михаил Николаевич   – прораб,\n"
            "Балдин Виктор Михайлович     – топкодер до 2008,\n"
            "Воронин Алексей Вячеславович – топкодер с 2017,\n"
            "Григорьев Сергей Георгиевич  – идеолог,\n"
            "Данил Адисонович Ахмеров     – топкодер с 2023."
        )

    def _about(self) -> None:
        """A box of our own rather than `QMessageBox.about`: the reference
        front-end's picture is what belongs in that corner."""
        box = QMessageBox(self)
        box.setWindowTitle("О программе")
        picture = assets.icon(actions.APPLICATION_ICON)
        if picture is not None:
            box.setIconPixmap(picture.pixmap(64, 64))
        box.setText(self.about_text())
        box.exec()

    def _open_document(self, name: str) -> None:
        """Opens a built PDF, or says where it should be.

        The PDFs are written into `doc/` by the `docs` target and are not in
        version control, so a fresh checkout has none — the message names both the
        file and the command that builds it.
        """
        pdf = pathlib.Path(__file__).resolve().parents[3] / "doc" / f"{name}.pdf"
        if pdf.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
            return
        QMessageBox.information(
            self,
            "PrologD",
            f"Файл {pdf} не найден.\n\n"
            "Документация собирается командой:\n"
            "cmake --build build --target docs",
        )

    # -- the recent-files submenu ------------------------------------------
    def _fill_recent_menu(self) -> None:
        """Rebuilds the submenu; files that no longer exist are dropped."""
        menu = self._recent_menu
        menu.clear()
        paths = self._recent.prune()
        self._settings.recent_files = paths
        if not paths:
            empty = menu.addAction("(пока пусто)")
            empty.setEnabled(False)
            return
        for path in paths:
            entry = menu.addAction(pathlib.Path(path).name)
            entry.setToolTip(path)
            if pathlib.Path(path).suffix.lower() == ".pld":
                # «Последние» lists programs, and a program gets the picture of a
                # file; anything else in the list shows its name only.
                picture = assets.icon(actions.FILE_ICON)
                if picture is not None:
                    entry.setIcon(picture)
            entry.triggered.connect(lambda _checked=False, path=path: self.open_path(path))
        menu.addSeparator()
        menu.addAction("Очистить список", self._clear_recent)

    def _clear_recent(self) -> None:
        self._recent.clear()
        self._settings.recent_files = []
        self._fill_recent_menu()

    # -- panes -------------------------------------------------------------
    def _add_pane(self) -> Pane:
        """Adds a pane on the right, showing every open document."""
        pane = Pane(self._settings, self)
        # The pane is passed along instead of its index: indices move when a pane
        # is closed, and a stale index would send the commands to the wrong pane.
        pane.activated.connect(lambda pane=pane: self._on_pane_activated(pane))
        pane.closeRequested.connect(self.close_buffer)
        pane.reordered.connect(self._on_pane_reordered)
        pane.newFileRequested.connect(lambda: self.new_buffer())
        pane.zoomChanged.connect(self._on_zoom_changed)
        pane.fileDropped.connect(self.open_path)
        pane.queryRequested.connect(self._on_query_requested)
        # Which tab is showing decides the window title and the undo state.
        pane.currentChanged.connect(self._on_tab_changed)
        pane.cursorMoved.connect(self._update_details)
        self._panes.append(pane)
        self._editor_splitter.addWidget(pane)
        pane.set_buffers(self._buffers)
        self._apply_context_actions()
        return pane

    def split_editor(self, remember: bool = True, sizes: list[int] | None = None) -> bool:
        """Adds a second pane, showing the current document as well.

        The new pane lists every open document but starts on the one the active
        pane is showing, which is what a split is usually asked for: the same
        program beside itself, or another tab selected on the right.  `sizes`
        restores the widths of a previous session.
        """
        if len(self._panes) > 1:
            return False
        current = self.current_buffer()
        pane = self._add_pane()
        if current is not None:
            pane.set_current(current)
        self._editor_splitter.setSizes(sizes or [1, 1])
        self._active_pane = len(self._panes) - 1
        if remember:
            self._save_split_state()
        self._refresh_titles()
        self._sync_pane_actions()
        self._status.setText("редактор разделён: две панели, одна программа")
        return True

    def merge_editor(self, remember: bool = True) -> bool:
        """Closes the second pane; the documents stay open."""
        if len(self._panes) < 2:
            return False
        pane = self._panes.pop()
        # Before anything else: removing the tabs raises `currentChanged`, and the
        # handler reads the active pane — which is this one until it is reset.
        self._active_pane = 0
        current = pane.current_buffer()
        # The views belong to the pane; they are detached before it goes, or the
        # buffers would keep dangling editors (see `Pane.set_buffers`).
        pane.set_buffers([])
        self._editor_splitter.widget(1).setParent(None)
        pane.deleteLater()
        if current is not None:
            self._panes[0].set_current(current)  # the eyes stay on that program
        if remember:
            self._save_split_state()
        self._refresh_titles()
        self._sync_pane_actions()
        self._status.setText("редактор объединён: одна панель")
        return True

    # -- the output panel --------------------------------------------------
    def output_position(self) -> str:
        """`right` or `bottom` — where the output (and the input queue) sits."""
        if self._panel_splitter.orientation() == Qt.Orientation.Vertical:
            return "bottom"
        return "right"

    def output_visible(self) -> bool:
        """Whether the panel is shown (`isHidden`, so a window that was never
        shown reads as visible — the same trap the toolbar switch has)."""
        return not self._panel_tabs.isHidden()

    def _apply_output_position(self, remember: bool = True) -> None:
        """Puts the panel on the side the settings name, with its sizes."""
        bottom = self._settings.output_position == "bottom"
        self._panel_splitter.setOrientation(
            Qt.Orientation.Vertical if bottom else Qt.Orientation.Horizontal
        )
        # The sizes mean different things after a turn (widths become heights), and
        # a hand-edited `0` would collapse both halves — so only a pair of positive
        # numbers is taken from the file.
        stored = [size for size in self._settings.panel_sizes if size > 0]
        self._panel_splitter.setSizes(stored if len(stored) == 2 else [600, 400])
        if remember:
            self._save_panel_state()

    def flip_output_position(self) -> None:
        """`Ctrl+F4`: the panel moves between the right side and the bottom."""
        self._settings.output_position = (
            "bottom" if self.output_position() == "right" else "right"
        )
        self._apply_output_position()
        self._status.setText(
            "панель вывода внизу"
            if self.output_position() == "bottom"
            else "панель вывода справа"
        )

    def _toggle_output(self, visible: bool) -> None:
        """`F4`: show or hide the output panel."""
        self._settings.output_visible = bool(visible)
        self._panel_tabs.setVisible(bool(visible))
        self._status.setText("панель вывода показана" if visible else "панель вывода скрыта")

    def _save_panel_state(self) -> None:
        """Remembers the side of the panel and the splitter's two sizes."""
        self._settings.output_position = self.output_position()
        self._settings.panel_sizes = list(self._panel_splitter.sizes())

    # -- the panel tabs (task_50) ------------------------------------------
    def panel_tabs(self) -> QTabWidget:
        """The tab widget that carries Проблемы, Вывод, Система, Ввод and Таблица."""
        return self._panel_tabs

    def _tab_index(self, tab: str) -> int:
        """The position of a tab in the bar, by the pane (or widget) it shows."""
        widget = {
            panels.TAB_PROBLEMS: self._problems,
            panels.TAB_OUTPUT: self._output,
            panels.TAB_SYSTEM: self._system,
            panels.TAB_INPUT: self._input_tab,
            panels.TAB_TABLE: self._table,
        }[tab]
        return self._panel_tabs.indexOf(widget)

    def _show_panel_tab(self, tab: str) -> None:
        """Brings one tab of the panel to the front."""
        index = self._tab_index(tab)
        if index >= 0:
            self._panel_tabs.setCurrentIndex(index)

    @staticmethod
    def _line_count(pane) -> int:
        """How many complete lines a read-only pane holds (0 while empty)."""
        return max(0, pane.document().blockCount() - 1)

    def _input_count(self) -> int:
        """The prepared answers: non-blank lines of the queue (task_50)."""
        return sum(1 for line in self._input_pane.toPlainText().split("\n") if line.strip())

    def _problem_count(self) -> int:
        """The errors and warnings of the current run, for the tab title."""
        return self._error_count + self._warning_count

    def _refresh_panel_tabs(self) -> None:
        """Names the tabs with their counts, and paints «Проблемы» by its state.

        `Вывод:5`, `Проблемы:0`, `Система:3`, `Ввод:2`, `Таблица:3` — the title is
        the pane's contents in one word: lines of text, and the table's row count,
        which is its number of solutions (task_59).  «Проблемы» is the ordinary
        colour with none, orange with warnings only, red once an error has arrived.
        """
        bar = self._panel_tabs.tabBar()
        bar.setTabText(self._tab_index(panels.TAB_PROBLEMS),
                       f"Проблемы:{self._problem_count()}")
        bar.setTabText(self._tab_index(panels.TAB_OUTPUT),
                       f"Вывод:{self._line_count(self._output)}")
        bar.setTabText(self._tab_index(panels.TAB_SYSTEM),
                       f"Система:{self._line_count(self._system)}")
        bar.setTabText(self._tab_index(panels.TAB_INPUT),
                       f"Ввод:{self._input_count()}")
        bar.setTabText(self._tab_index(panels.TAB_TABLE),
                       f"Таблица:{self._table.solution_count()}")
        if self._error_count:
            colour = self._settings.palette.error
        elif self._warning_count:
            colour = self._settings.palette.warning
        else:
            colour = None
        bar.setTabTextColor(
            self._tab_index(panels.TAB_PROBLEMS), QColor(colour) if colour else QColor()
        )

    def active_pane(self) -> Pane:
        return self._panes[self._active_pane]

    def panes(self) -> list[Pane]:
        """The editor panes, left to right (one, or two when split)."""
        return list(self._panes)

    def view_for(self, buffer: Buffer) -> CodeEditor | None:
        """A view of `buffer`, in the active pane.

        Which view is asked for hardly matters: they share one document, so a
        change made through any of them is the same change.
        """
        return self.active_pane().view_for(buffer)

    def pane_count(self) -> int:
        return len(self._panes)

    def _save_split_state(self) -> None:
        """Remembers the split editor for the next start."""
        self._settings.split_editor = len(self._panes) > 1
        self._settings.split_sizes = list(self._editor_splitter.sizes())

    # -- the window itself -------------------------------------------------
    def window_geometry_text(self) -> str:
        """The window's size and place as text, for the settings file (task_49)."""
        return geometry.geometry_text(self)

    def restore_window_geometry(self) -> bool:
        """Puts the window back where it stood, if the file remembers it.

        True when the stored text was used.  A window is only as stubborn as its
        `restoreGeometry`: a blob written on a screen that is gone (or by another
        display layout) is placed by Qt where it can be, so nothing here has to
        check whether the rectangle is still on a monitor.
        """
        return geometry.restore_geometry(self, self._settings.window_geometry)

    def _save_window_state(self) -> None:
        """Remembers the window's size and place for the next start."""
        self._settings.window_geometry = self.window_geometry_text()

    def _on_pane_activated(self, pane: Pane) -> None:
        if pane not in self._panes:
            return
        self._active_pane = self._panes.index(pane)
        self._refresh_titles()
        # «Найти» acts on the pane that was used last, so the matches move with it.
        self._refollow_find()
        buffer = self.current_buffer()
        where = f" — панель {self._active_pane + 1} из {len(self._panes)}" if len(self._panes) > 1 else ""
        if buffer is not None and buffer.model.path:
            self._status.setText(f"открыт {documents.short_path(buffer.model.path)}{where}")
        elif where:
            self._status.setText(f"активна левая панель{where}" if self._active_pane == 0 else f"активна правая панель{where}")

    def _on_pane_reordered(self, buffers: list[Buffer]) -> None:
        """A tab was dragged: the order is shared, so every pane follows it."""
        if set(buffers) != set(self._buffers):
            return  # a stale signal from a pane that is being changed
        self._buffers = list(buffers)
        for pane in self._panes:
            pane.set_buffers(self._buffers)

    # -- actions -----------------------------------------------------------
    def run_program(self, *, trace: bool = False, step: bool = False,
                    questions: bool | None = None) -> bool:
        """Runs the current buffer in a fresh interpreter.

        A run starts from a clean slate: a fresh interpreter (no clauses, RNG
        seed, redirected files or preloaded input left from the previous run)
        and an empty output pane.  Reusing the session accumulates clauses —
        with a duplicated `факториал/2` the factorial example returns 64
        solutions instead of one, which looks like a loop — so `start()` stops
        a live process first.

        `trace` turns `ТРАССА` on for this run: the trace arrives as `trace`
        events and is coloured apart from the program's own output.  `step` arms
        the step hook, so the run stops at its first step point and waits for
        `Шаг`/`Продолжить` — and, like `trace`, it goes on the *load*, because a
        program's own `?`-statements and directives run there.

        `questions=False` loads the program without running its own `?`-statements:
        that is what the editor's margin needs, so one clicked question is
        answered *alone* instead of after the whole lesson (task_36).  Left out, it
        follows the «Выполнять вопросы при запуске» switch (task_29), which is on
        by default — a lesson is normally run to see its questions answered.

        The result is True when the load was sent; a caller that wants to add a
        query of its own (`_on_query_requested`) must not do it otherwise.
        """
        # A new run cancels the deadline of a polite stop that is still pending:
        # the old process goes either way (`session.start` stops a live one).  The
        # `_stopping` flag itself is *not* cleared here: the terminated process's
        # `ended` event consumes it, and that event is delivered before this load
        # reaches the new interpreter — clearing it early would report the
        # termination status as an exit code.
        self._stop_grace.stop()
        self._timeout.stop()
        if self._session.paused() and not (trace or step):
            # `F5` while a step is paused means «продолжить»: starting the file over
            # would throw away the run the user is walking through.
            self.step_continue()
            return False
        buffer = self.current_buffer()
        if buffer is None:
            return False
        if questions is None:
            questions = self._settings.run_questions
        path = buffer.model.path
        if self._settings.save_before_run and buffer.is_modified():
            # The switch of the «Выполнение» menu: a run is then always of what is
            # on disk, which is what makes `ИМПОРТ` and the diagnostics agree
            # with the editor about the file's own path.
            if not self.save_buffer(buffer):
                self._status.setText("запуск отменён: сохранить не удалось")
                return False
        # The panes start empty, and so does what has not reached them yet: a run
        # begins with its own output, never with the tail of the previous one.
        self._discard_output()
        self._reset_panels()
        # The panel shows the program's output while the run is going (task_50);
        # a diagnostic switches it to «Проблемы» later.
        self._show_panel_tab(panels.TAB_OUTPUT)
        # The clock of the run, read by `_on_loaded` for the
        # «база знаний загружена (N мс)» line.
        self._run_clock.restart()
        # A new run starts clean: the red line of the last failure and the line a
        # step was standing on are both about a run that is over.
        self._clear_marks()
        self._step_stack.clear()
        self._step_pane.idle()
        # Every run starts with the prepared answers from the field: that is what
        # makes a program that reads several values runnable without a dialog per
        # value — and a cancelled question applies to this run only.
        self._stopped_input = False
        self._queued_input = self._input_lines()
        if not self._start_session():
            return False
        # A run starts a *fresh* interpreter, and its screen comes up blank: the
        # window's picture clears with it, or it would keep showing a drawing the
        # engine no longer has (`start` is also what a restart of a live session
        # does, so this is the one place the two agree).
        if self._canvas is not None:
            self._canvas.clear()
            if self._graphics_window is not None:
                self._graphics_window.refresh()
        # The new run may show the picture window again: the decision is taken at
        # the first primitive of *this* run (task_48).
        self._graphics_shown = False
        # After `start()`, not before: it stops a live session first, and the
        # `ended` event of that old process (delivered inside the stop) would
        # clear the flags just set — a restart is not an unload, and the new
        # interpreter has the program loaded from here on.
        self._busy = True
        self._loaded = True
        self._results_in_load = 0
        self._failed_in_load = False
        self._awaiting_query = False
        # A question from an older click is about a program that this run replaces
        # (task_60).  Both paths that ask after a load set it *after* this call.
        self._pending_query = None
        # At once, not when `ready` arrives: the user pressed the button, and it
        # must not be pressable again while the interpreter is coming up.
        self._sync_run_actions()
        self._update_details()
        self._append_note("--- загрузка базы знаний ---\n")
        if self._queued_input:
            self._append_note(f"--- ввод из поля, строк — {len(self._queued_input)} ---\n")
        # The guards of the run (task_46): three go on the wire with the load, and
        # the deadline is the window's own clock — the same answer «Остановить»
        # uses, so a program that computes forever stops on time.
        limits = self._settings.limits()
        note = self._limits_note()
        if note:
            self._append_note(note)
        self._arm_timeout()
        if path is not None and not buffer.is_modified():
            # A saved, unmodified buffer is loaded by path: `ИМПОРТ` resolves
            # against the file's own directory and diagnostics name the file.
            self._session.load_file(path, step=step, trace=trace, questions=questions,
                                    print_questions=self._settings.print_questions,
                                    limits=limits)
            self._status.setText(f"выполняется {pathlib.Path(path).name}")
        else:
            # Otherwise the text comes from the editor, and the path, when there
            # is one, is what the loader treats as the importing file.  The
            # status line says which case is running, so a failing `ИМПОРТ` is
            # not a mystery: without a path it searches only the working
            # directory and the `-I` directories.
            # The text comes from the editor, but the identity comes from the tab:
            # a saved file is named by its path (so `ИМПОРТ` and the diagnostics
            # point at the real file), an unnamed buffer by its title — the name
            # the user sees in the tab and in the status bar of a diagnostic.
            self._session.load_text(buffer.text(), path or buffer.title(), step=step,
                                    trace=trace, questions=questions,
                                    print_questions=self._settings.print_questions,
                                    limits=limits)
            name = pathlib.Path(path).name if path else buffer.title()
            self._status.setText(f"выполняется {name} (есть несохранённые правки)")
        return True

    # -- the graphics window (task_45) -------------------------------------
    def canvas(self) -> graphics.Canvas:
        """The picture, created on first use."""
        if self._canvas is None:
            self._canvas = graphics.Canvas()
        return self._canvas

    def graphics_window(self) -> graphicswindow.GraphicsWindow:
        """The window the picture is shown in, created on first use."""
        if self._graphics_window is None:
            window = graphicswindow.GraphicsWindow(self.canvas(), self)
            window.closed.connect(lambda: self.show_graphics_window(False))
            self._graphics_window = window
        return self._graphics_window

    def graphics_available(self) -> bool:
        """Whether a window for the picture exists (tests ask instead of opening)."""
        return self._graphics_window is not None

    def show_graphics_window(self, visible: bool) -> None:
        """The «Графическое окно» entry: shows or hides the picture.

        Opening a window that is *not* the interpreter's only subscriber is why
        the snapshot exists: the program may have drawn half a picture while this
        window did not exist, and the interpreter still holds every pixel of it.

        Showing it also marks this run as «the window was brought up», whichever
        way it was shown (the entry, the settings, or the first primitive of a
        run): that is what keeps a window the user closed closed (task_48).  Hiding
        it does not clear the mark — closing the window *is* the gesture that must
        not be answered by reopening it.
        """
        window = self.graphics_window()
        visible = bool(visible)
        if visible:
            self._graphics_shown = True
            window.restore_geometry(self._settings.graphics_geometry)
            window.show()
            window.raise_()
            if self._session.is_running():
                self._session.request_graphics_snapshot()
        else:
            window.hide()
        self._settings.graphics_visible = visible
        self._settings.graphics_geometry = window.geometry_text()
        self._actions["graphics"].setChecked(visible)
        self._status.setText(
            "графическое окно показано" if visible else "графическое окно скрыто"
        )

    def _on_drawn(self, event: dict) -> None:
        """One primitive reached the window (protocol 10).

        A program that draws without being asked shows its picture: the first
        primitive of a run brings the window up (task_48).  The moment is the
        first *primitive* rather than the start of the run because it is the first
        moment there is something to see — a program that draws nothing must not
        open a window — and the decision is taken once per run: a window the user
        closed during an animation stays closed, and the next run opens it again.

        What was drawn before this window existed is not lost: the program's
        pixels live in the interpreter, and opening a window mid-run asks for the
        snapshot (that is why `show_graphics_window` requests one).
        """
        if not self._graphics_shown:
            self._graphics_shown = True
            if self._graphics_window is None or not self._graphics_window.isVisible():
                self.show_graphics_window(True)
        if self._canvas is None:
            return  # the snapshot is on its way; the next primitive draws
        self._canvas.draw(event)
        if self._graphics_window is not None:
            self._graphics_window.refresh()

    def _on_bitmap(self, width: int, height: int, data: bytes) -> None:
        """The whole screen arrived: what a window opened mid-run starts from."""
        self.canvas().apply_bitmap(width, height, data)
        if self._graphics_window is not None:
            self._graphics_window.refresh()
        self._status.setText(f"рисунок получен ({width}×{height})")

    def _limits_note(self) -> str:
        """The limits a run goes with, in the words of their rows (task_46).

        This is the window's half of the answer a limit that fires leaves open.
        The engine's message names the limit and its value («Превышен предел шагов
        выполнения: 5000») and nothing else — it has no idea that a command line
        or a settings dialog exists (ADR-020) — while the row that raises a limit
        is *here*.  So a run whose limits differ from the shipped ones says so
        before it starts, named the way the dialog names them: a limit nobody can
        find is the mystery the message alone would leave.

        A value equal to the default is not a choice the user made, and a run of a
        lesson would otherwise report the same two numbers for ever.
        """
        named = []
        for value, default, label in (
            (self._settings.max_steps, settings.DEFAULT_MAX_STEPS, "«Предел шагов»"),
            (self._settings.max_depth, settings.DEFAULT_MAX_DEPTH, "«Предел глубины»"),
            (self._settings.max_findall, settings.DEFAULT_MAX_FINDALL,
             "«Предел решений НАЙТИВСЕ»"),
            (self._settings.timeout_milliseconds, settings.DEFAULT_TIMEOUT_MILLISECONDS,
             "«Предел времени, мс»"),
        ):
            if value == default:
                continue
            named.append(f"{label} {value}" if value else f"{label} — без предела")
        if not named:
            return ""
        return ("--- пределы: " + ", ".join(named) +
                " — строки в «Выполнении» настроек ---\n")

    def _arm_timeout(self) -> None:
        """Starts the «Предел времени» clock of a run, if one is set (task_46).

        The deadline is a `QTimer` and the answer is `interrupt` — the same polite
        stop the button uses, so the engine ends the query where it stands instead
        of the window killing a process mid-write.  What it cannot reach is a
        program waiting *outside* the solver (a `ВВОД` nobody answers, a `ЖДИ`):
        the request is read when the solver looks next, and until then the run
        keeps waiting — «Остановить» is what ends a program like that.
        """
        self._timeout.stop()
        milliseconds = self._settings.timeout_milliseconds
        if milliseconds > 0:
            self._timeout.start(milliseconds)

    def _on_timeout(self) -> None:
        """The run outlived its deadline: ask the interpreter to stop solving."""
        if not self._busy:
            return
        milliseconds = self._settings.timeout_milliseconds
        self._append_note(f"--- предел времени: {milliseconds} мс, остановлено ---\n")
        self._status.setText(f"остановлено по времени (предел {milliseconds} мс)")
        self._session.interrupt()

    def format_document(self) -> None:
        """Lays the current buffer — or the selection — out (task_30).

        The formatter lives in prlib, next to the grammar it has to understand,
        so the text travels over the protocol and the answer is put back here.
        What this method has to get right is everything *around* the text: the
        replacement is one undo step, the caret and the selection keep their
        places (only whitespace moves, and `formatter.map_positions` carries the
        old offsets over), and a program that does not parse comes back untouched
        with its line marked — a formatter must never be the reason a buffer is
        lost.
        """
        mode = self._settings.format_mode
        view = self.active_pane().current_view()
        if view is None or self._format_pending is not None:
            return
        cursor = view.textCursor()
        region = None
        if self._settings.format_selection and cursor.hasSelection():
            region = (cursor.selectionStart(), cursor.selectionEnd())
        old = view.toPlainText()
        text = old[region[0]:region[1]] if region is not None else old
        if not text:
            return
        self._format_pending = {
            "view": view,
            "old": old,
            "region": region,
            "anchor": cursor.anchor(),
            "position": cursor.position(),
        }
        # The request goes through the interpreter process — prlib is there — so
        # a session has to be up; starting one is cheap, and nothing is loaded
        # into it.
        if not self._session.is_running():
            if not self._start_session():
                return
        self._status.setText("форматирование…")
        self._session.format_text(
            text,
            mode=mode,
            width=self._settings.format_width,
            indent=self._settings.format_indent,
            unit=self._settings.format_unit,
            selection=region is not None,
            name="<buffer>",
        )

    def _on_formatted(self, text: str, changed: bool) -> None:
        """Puts the laid-out text back — or says why it was not put back."""
        pending = self._format_pending
        self._format_pending = None
        if pending is None:
            return
        view = pending["view"]
        if self._buffer_of_view(view) is None:
            return  # the tab was closed while the request was in flight
        if view.toPlainText() != pending["old"]:
            # An edit arrived between the question and the answer; rewriting the
            # buffer now would throw that edit away.
            self._status.setText("форматирование отменено: текст изменился")
            return
        if not changed:
            self._status.setText("уже отформатировано")
            return
        anchor, position = formatter.map_positions(
            pending["old"], text, [pending["anchor"], pending["position"]]
        )
        cursor = view.textCursor()
        cursor.beginEditBlock()  # one undo step for the whole replacement
        if pending["region"] is not None:
            start, end = pending["region"]
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        else:
            cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(text)
        cursor.endEditBlock()
        restored = view.textCursor()
        if pending["region"] is not None:
            # The formatted fragment stays selected: it is what was rewritten,
            # and formatting it again is one key press away.
            start = pending["region"][0]
            restored.setPosition(start)
            restored.setPosition(start + len(text), QTextCursor.MoveMode.KeepAnchor)
        else:
            restored.setPosition(anchor)
            restored.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
        view.setTextCursor(restored)
        self._status.setText("отформатировано")

    def _run_query(self) -> None:
        text = self._query_line.text().strip()
        if not text:
            return
        self._query_line.clear()
        if not text.startswith("?"):
            text = "?" + text
        # A query needs an interpreter, and the window may not have one yet: the
        # session is started by the first run *or* by a goal typed into this line.
        if not self._session.is_running():
            if not self._start_session():
                return
        if not self._loaded:
            # There is no program to ask: load what the editor holds, quietly, and
            # ask when the load has answered (task_60).  With a base loaded this
            # line asks *that* base and never reloads — one program, one load, and
            # a goal typed after an edit belongs to the run that is in the window.
            if not self.run_program(questions=False):
                return
            self._ask_after_load(text)
            self._sync_run_actions()
            self._update_details()
            return
        self._busy = True
        self._arm_answer_table()
        self._session.run_query(text)
        self._sync_run_actions()
        self._update_details()

    def _on_query_requested(self, statement: str) -> None:
        """Runs one question from the editor's margin — and the answer alone.

        The statement goes into the query line first, so what is running stays
        visible while the answer arrives, and the program is loaded *quietly*
        (`questions=False`): running its own `?`-statements would fill the pane
        with the whole lesson before the clicked question's answer.

        A click during a run stops that run first.  The margin marker is the way
        out of a runaway query as much as it is a way to ask one, and after the
        stop the clicked question is the one that answers (task_36).

        The question itself goes out when the load has answered (`_ask_after_load`):
        a file that does not parse has no base to ask, and asking anyway answered
        «НЕТ» and repeated the file's own parse error as the query's (task_60).
        """
        if not statement:
            return
        if self._busy or self._session.paused():
            # «Остановить», then the clicked query: a runaway is ended by ending
            # its process.  Immediate, not the polite ask of `stop_program`: the
            # clicked query follows at once, and the stopped run's own events must
            # not arrive in the middle of it (the marker is «stop this and answer
            # that», and nobody waits for the runaway to agree).
            if self._session.is_running():
                self._stop_now("остановлено")
        self._query_line.setText(statement)
        if not self.run_program(questions=False):
            return
        self._ask_after_load(statement)

    def _ask_after_load(self, statement: str) -> None:
        """Keeps a question until the program it was sent with has loaded (task_60).

        `_on_loaded` is the only place that knows the text parsed, and it is where
        the question goes out from.  Asking at once, as the window used to, meant a
        file that does not parse answered a question against an empty knowledge base
        («НЕТ», plus «не найдено: факт/1») and reported its broken line twice: once
        as the buffer's, once as the query's.
        """
        self._pending_query = statement
        # The run is over when this question answers, not when the load does: the
        # `loaded` event of the quiet load is the moment the question goes out, and
        # from there the answer is what `_awaiting_query` waits for.
        self._awaiting_query = True

    def _send_pending_query(self) -> None:
        """Sends the question that was waiting for its program."""
        statement, self._pending_query = self._pending_query, None
        if statement is None:
            return
        self._arm_answer_table()
        self._session.run_query(statement)

    def _drop_pending_query(self, note: str = "") -> None:
        """Forgets a question whose program never loaded, saying so if asked.

        The file's own diagnostic is already in «Проблемах», with its line marked,
        so silence would leave the click looking broken and a second question to the
        interpreter would look like an answer.  One line in «Системе» is the middle
        ground (task_60).
        """
        if self._pending_query is None:
            return
        self._pending_query = None
        if note:
            self._append_note(note)

    # -- files -------------------------------------------------------------
    def new_buffer(self, name: str | None = None) -> Buffer:
        """Adds an empty document and makes it current."""
        used = [buffer.model.name for buffer in self._buffers]
        return self._add_buffer(
            documents.Document.untitled(name or documents.untitled_name(used))
        )

    def open_path(self, path: str, encoding: str | None = None) -> bool:
        """Opens a file in its own tab — and *only* into the editor.

        Opening must not run anything: `load` adds clauses to the live
        interpreter (that is what `ИМПОРТ` needs), so opening a file into a
        session that already ran something put a second copy of the program in
        it.  With duplicated recursive clauses every solution multiplies, which
        is why opening the factorial example twice looked like an endless loop.
        Running is F5.
        """
        path = str(pathlib.Path(path))
        existing = self._buffer_for_path(path)
        if existing is not None:
            # Already open: show that tab instead of a second copy of the file.
            self.active_pane().set_current(existing)
            return True
        try:
            model = documents.Document.from_file(path, encoding)
        except documents.DecodeFailure as failure:
            return self._open_with_encoding(failure)
        except OSError as error:
            self._append_note(f"*** не могу открыть {path}: {error}\n")
            return False

        if len(self._buffers) == 1 and self._is_placeholder(self._buffers[0]):
            # A single empty buffer is a placeholder, not work: the file takes
            # its place instead of leaving an empty tab behind.  The welcome
            # program is not empty, so it stays until it is closed.
            self._replace_buffer(self._buffers[0], model)
        else:
            self._add_buffer(model)
        self._remember(path)
        self._status.setText(f"открыт {documents.short_path(path)}")
        return True

    def save_buffer(self, buffer: Buffer | None = None, path: str | None = None) -> bool:
        """Writes a buffer, asking for a name when it has none.  False = not saved.

        `False` matters: whoever asked must not close anything when the file
        could not be written.
        """
        buffer = buffer or self.current_buffer()
        if buffer is None:
            return False
        if path is None and buffer.model.path is None:
            path = self._ask_save_path(buffer)
            if not path:
                return False
        buffer.take_text()
        try:
            written = buffer.model.save(path)
        except UnicodeEncodeError as error:
            # A file read as cp1251 cannot hold every character.  Replacement
            # characters would corrupt it silently, so UTF-8 is offered instead.
            if not self._offer_utf8(buffer, error):
                return False
            try:
                written = buffer.model.save(path)
            except OSError as retry_error:
                self._append_note(
                    f"*** не могу записать {path or buffer.model.path}: {retry_error}\n"
                )
                self._status.setText("не сохранено")
                return False
        except OSError as error:
            self._append_note(f"*** не могу записать {path or buffer.model.path}: {error}\n")
            self._status.setText("не сохранено")
            return False
        buffer.mark_saved()
        self._refresh_titles()
        self._remember(written)
        self._status.setText(f"сохранён {documents.short_path(written)}")
        return True

    def reload_buffer(self) -> bool:
        """Re-reads the current tab from its file (`Ctrl+Shift+R`)."""
        buffer = self.current_buffer()
        if buffer is None or buffer.model.path is None:
            self._status.setText("буфер не связан с файлом")
            return False
        if buffer.is_modified():
            answer = self._ask_save(buffer.model.name)
            if answer == CANCEL:
                return False
            if answer == SAVE and not self.save_buffer(buffer):
                return False
        try:
            model = documents.Document.from_file(buffer.model.path, buffer.model.encoding)
        except (OSError, documents.DecodeFailure) as error:
            self._append_note(f"*** не могу перечитать {buffer.model.path}: {error}\n")
            return False
        buffer.set_text(model.text)
        buffer.model.eol = model.eol
        buffer.mark_saved()
        self._refresh_titles()
        self._status.setText(f"перечитан {documents.short_path(buffer.model.path)}")
        return True

    def close_buffer(self, buffer: Buffer) -> bool:
        """Closes one document, asking first.  Cancelling keeps it open."""
        if buffer not in self._buffers:
            return False
        if not self._confirm_close(buffer):
            return False
        self._drop_buffer(buffer)
        if not self._buffers and not self._closing:
            self.new_buffer()  # there is always somewhere to type
        self._refresh_titles()
        return True

    def close_all(self) -> bool:
        """Closes every document, one at a time, showing the one that is closing.

        The document is made current *before* the question, so the file the box is
        about is the one on screen, and it disappears as soon as the question is
        answered.  Cancelling therefore stops where it happened, leaving the
        documents closed so far closed — the earlier rule (ask about everything
        first, then close) kept them open but gave no clue *which* file each of the
        questions was about, which is worse in practice.
        """
        while self._buffers:
            buffer = self._buffers[0]
            self.active_pane().set_current(buffer)
            if not self._confirm_close(buffer):
                return False
            self._drop_buffer(buffer)
        return True

    # -- prompts -----------------------------------------------------------
    def _ask_save(self, name: str) -> str:
        """Save, discard or cancel for one modified buffer.

        A method of its own so it can be replaced: a modal box cannot be driven
        from a headless test, and the *decision* is what the tests are about.
        """
        box = QMessageBox(self)
        box.setWindowTitle("PrologD")
        box.setText(f"Сохранить изменения в «{name}»?")
        save = box.addButton("Сохранить", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Не сохранять", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        # Enter lands on «Отмена»: throwing work away has to be a click, not a
        # reflex, and the destructive button sits last for the same reason.
        box.setDefaultButton(cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return SAVE
        if clicked is discard:
            return DISCARD
        return CANCEL

    def _ask_save_path(self, buffer: Buffer) -> str | None:
        """A file name for a buffer that has none."""
        start = buffer.model.path or str(
            pathlib.Path(self._settings.last_directory or ".") / f"{buffer.model.name}.pld"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить программу", start, "PrologD (*.pld);;Все файлы (*)"
        )
        return path or None

    def _confirm_close(self, buffer: Buffer) -> bool:
        if not buffer.is_modified():
            return True
        answer = self._ask_save(buffer.model.name)
        if answer == CANCEL:
            return False
        if answer == DISCARD:
            self._discarded.append(buffer)
            return True
        # A save that failed must not lose the buffer either.
        return self.save_buffer(buffer)

    def _offer_utf8(self, buffer: Buffer, error: UnicodeEncodeError) -> bool:
        character = error.object[error.start]
        answer = QMessageBox.question(
            self,
            "PrologD",
            f"В кодировке {buffer.model.encoding} нет символа «{character}» "
            f"(позиция {error.start}).\nСохранить файл в UTF-8?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        buffer.model.encoding = documents.DEFAULT_ENCODING
        return True

    def _ask_encoding(self, path: str) -> str | None:
        """Which encoding to use for a file that is not UTF-8.

        Replaceable for the same reason as `_ask_save`: a modal box cannot be
        driven from a headless test, and a test that forgets to replace it does
        not fail — it *hangs*.
        """
        choice, accepted = QInputDialog.getItem(
            self,
            "Кодировка",
            f"{pathlib.Path(path).name} не читается как UTF-8.\nВыберите кодировку файла:",
            list(documents.SUGGESTED_ENCODINGS),
            0,
            False,
        )
        return choice if accepted else None

    def _open_with_encoding(self, failure: documents.DecodeFailure) -> bool:
        """Asks which encoding to use — a file is never decoded by guesswork."""
        choice = self._ask_encoding(failure.path)
        if choice is None:
            self._append_note(f"*** {failure}\n")
            return False
        return self.open_path(failure.path, encoding=choice)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть программу",
            self._settings.last_directory,
            "PrologD (*.pld);;Все файлы (*)",
        )
        if path:
            self.open_path(path)

    def _save_as(self) -> None:
        buffer = self.current_buffer()
        if buffer is None:
            return
        path = self._ask_save_path(buffer)
        if path:
            self.save_buffer(buffer, path)

    def _save_all(self) -> None:
        for buffer in list(self._buffers):
            if buffer.is_modified() and not self.save_buffer(buffer):
                return

    def stop_program(self) -> None:
        """Ends the run — politely first, and the base is not lost on the way.

        The solver reads the interrupt at every step of its loop, so a query
        that is running (a runaway included), waiting for input or paused at a
        step point all end on the request: the session answers with the runtime
        error of the interrupted query (`Interrupted`) and is then idle *with
        its knowledge base*, which is the difference between stopping a run and
        stopping the interpreter.  The deadline covers what the request cannot
        reach — a front-end that never reads, say — and then the process goes as
        it always did.

        An idle interpreter with a base loaded is the other meaning: stopping
        *it* unloads the base, and that is the one case that is immediate.
        """
        if not self._session.is_running():
            self._status.setText("интерпретатор уже остановлен")
            return
        unloading = self._loaded and not self._busy
        if self._closing:
            # Closing the window must not wait for a timer: the child goes at once,
            # even if a polite stop is still on its way.
            self._stop_now("база знаний выгружена" if unloading else "остановлено")
            return
        if self._stopping:
            return  # a polite stop is already on its way; do not restart the clock
        if unloading:
            self._stop_now("база знаний выгружена")
            return
        self._stopping = True
        self._status.setText("останавливаю…")
        self._session.interrupt()
        self._stop_grace.start(STOP_GRACE_MS)

    def _stop_expired(self) -> None:
        """The polite stop's deadline: the process goes, as it always did."""
        if self._stopping:
            self._stop_now("остановлено")

    def _stop_now(self, message: str) -> None:
        """Ends the session at once (terminate, grace, kill) and says why."""
        self._stop_grace.stop()
        self._stopping = True
        self._busy = False
        self._loaded = False
        # A stopped query answers nothing, so nothing is left to tabulate — and a
        # question still waiting for its load will never get one (task_60).
        self._answer_text = None
        self._drop_pending_query()
        self._session.stop()
        self._input_console.idle()
        self._step_pane.idle()
        self._step_stack.clear()
        self._status.setText(message)
        self._append_note(f"--- {message} ---\n")
        # The process is gone, so the buttons change at once — waiting for `ended`
        # would leave «Остановить» enabled on a session that is already dead.
        self._sync_run_actions()
        self._update_details()

    def _finish_polite_stop(self) -> None:
        """The interrupted query ended by itself: the session stays, the base too."""
        self._stop_grace.stop()
        self._stopping = False
        self._busy = False
        # The interrupted query answers nothing: there is no table to build, and a
        # question that was still waiting for its load has no load coming.  The
        # waiting flag goes too — it was set for the query that just ended, and a
        # later `loaded` would read it as «a question of mine is still to come».
        self._answer_text = None
        self._drop_pending_query()
        self._awaiting_query = False
        self._input_console.idle()
        self._step_pane.idle()
        self._step_stack.clear()
        self._status.setText("остановлено")
        self._append_note("--- остановлено ---\n")
        self._sync_run_actions()
        self._update_details()

    def clear_output(self) -> None:
        """Empties the read-only panes and the table; the input queue is user data.

        «Очистить вывод» clears what a run produced — the program's output, the
        diagnostics and the window's own notes — but never the prepared answers.
        The table is a view of the same answer, so it goes with the text: leaving
        it behind would show a table whose source is gone (task_59).
        """
        self._discard_output()
        self._output.reset()
        self._problems.reset()
        self._system.reset()
        self._table.set_answer(None)
        self._answer_text = None
        self._error_count = 0
        self._warning_count = 0
        self._refresh_panel_tabs()

    def _save_output(self) -> None:
        """Writes the output pane to a file of the user's choosing."""
        path = self._ask_save_output_path()
        if not path:
            return
        # What is still queued belongs to the log as much as the rest does.
        self._flush_output()
        try:
            self._output.save_to(path)
        except OSError as error:
            self._append_note(f"*** не могу записать {path}: {error}\n")
            self._status.setText("вывод не сохранён")
            return
        self._append_note(f"--- вывод сохранён в {path} ---\n")
        self._status.setText(f"вывод сохранён: {pathlib.Path(path).name}")

    def _ask_save_output_path(self) -> str | None:
        """Where to put the output.

        Replaceable for the same reason as `_ask_save`: a modal box cannot be driven
        from a headless test, and a test that forgets to replace one does not fail —
        it *hangs*.
        """
        start = pathlib.Path(self._settings.last_directory or pathlib.Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить вывод",
            str(start / "вывод.txt"),
            "Текст (*.txt);;Все файлы (*)",
        )
        return path or None

    # -- buffers -----------------------------------------------------------
    def _add_buffer(self, model: documents.Document) -> Buffer:
        """Adds a document, shows it in every pane, makes it current."""
        buffer = Buffer(model, self._settings, self)
        buffer.changed.connect(self._refresh_titles)
        # Undo and redo belong to the *document*, so every document reports its own
        # changes and the slot reads the one that is showing.
        buffer.document.undoAvailable.connect(self._sync_undo_actions)
        buffer.document.redoAvailable.connect(self._sync_undo_actions)
        # The reserved names arrive with `ready`; a buffer opened after that gets
        # them here, and a buffer created before it is served by `_on_ready`.
        buffer.set_keywords(self._session.keywords)
        buffer.set_reference(self._reference)
        buffer.set_shortcuts(self._shortcuts)
        self._buffers.append(buffer)
        for pane in self._panes:
            pane.set_buffers(self._buffers)
        self.active_pane().set_current(buffer)
        self._apply_context_actions()
        self._refresh_titles()
        return buffer

    def _replace_buffer(self, buffer: Buffer, model: documents.Document) -> Buffer:
        """Turns a placeholder tab into the file that takes its place."""
        self._drop_buffer(buffer)
        return self._add_buffer(model)

    def _drop_buffer(self, buffer: Buffer) -> None:
        """Forgets a document everywhere.  No questions are asked here."""
        if buffer in self._buffers:
            self._buffers.remove(buffer)
        for pane in self._panes:
            pane.set_buffers(self._buffers)  # detaches the views as well
        # Its views are about to go, so the find bar must not hold the buffer they
        # belonged to — and must not keep a highlight it can no longer clear.
        if self._find_highlighted is buffer:
            self._find_highlighted = None
            self._find_matches = []
            self._find_current = None
            if self._find_bound not in buffer.views():
                self._find_bound = None
        buffer.deleteLater()

    def _is_placeholder(self, buffer: Buffer) -> bool:
        """An empty untitled buffer with nothing in it to lose."""
        return (
            buffer.model.path is None
            and not buffer.is_modified()
            and not buffer.text().strip()
        )

    def _buffer_for_path(self, path: str) -> Buffer | None:
        wanted = pathlib.Path(path)
        for buffer in self._buffers:
            if buffer.model.path and pathlib.Path(buffer.model.path) == wanted:
                return buffer
        return None

    def _remember(self, path: str) -> None:
        """Records the file and its directory for the next dialog."""
        self._settings.recent_files = self._recent.add(path)
        self._settings.last_directory = str(pathlib.Path(path).parent)

    # -- titles ------------------------------------------------------------
    def _refresh_titles(self) -> None:
        for pane in self._panes:
            pane.refresh_titles()
        buffer = self.current_buffer()
        self.setWindowTitle(buffer.model.window_title() if buffer is not None else "PrologD")

    def _next_tab(self) -> None:
        self._cycle_tab(1)

    def _previous_tab(self) -> None:
        self._cycle_tab(-1)

    def _cycle_tab(self, step: int) -> None:
        if len(self._buffers) < 2:
            return
        pane = self.active_pane()
        pane.setCurrentIndex((pane.currentIndex() + step) % len(self._buffers))

    def _close_current(self) -> None:
        buffer = self.current_buffer()
        if buffer is not None:
            self.close_buffer(buffer)

    def _close_all_tabs(self) -> None:
        if self.close_all():
            self.new_buffer()

    def _restore_session(self) -> int:
        """Opens the tabs of the previous run; returns how many did open.

        A *file* tab is read from disk, so the window opens on the file as it is
        now, not on what the editor held when the last window closed; a file that
        has gone is skipped and named in the status line, because a half session
        that says nothing is worse than one that says what is missing.  An
        untitled tab comes back with its text and with the state it had: a tab the
        user had changed stays unsaved work and the next close has to ask about
        it, while one that was never touched comes back clean (task_49 — every
        restored untitled tab used to be starred, which was a save question about
        a program nobody had edited).
        """
        records = documents.decode_tabs(self._settings.session_tabs)
        missing: list[str] = []
        opened = 0
        for record in records:
            if record.path:
                if pathlib.Path(record.path).is_file():
                    before = len(self._buffers)
                    if self.open_path(record.path) and len(self._buffers) > before:
                        opened += 1
                else:
                    missing.append(record.name or record.path)
                continue
            used = [buffer.model.name for buffer in self._buffers]
            model = documents.Document.untitled(
                record.name or documents.untitled_name(used)
            )
            model.text = record.text
            buffer = self._add_buffer(model)
            if record.modified:
                # Unsaved work stays unsaved: closing the window must ask about it.
                buffer.document.setModified(True)
                buffer.sync_modified()
            opened += 1

        current = self._settings.session_current
        if current:
            for buffer in self._buffers:
                if (buffer.model.path or buffer.model.name) == current:
                    self.active_pane().set_current(buffer)
                    break
        if opened or missing:
            said = f"восстановлено вкладок: {opened}"
            if missing:
                said += "; не найдено: " + ", ".join(
                    documents.short_path(name) for name in missing
                )
            self._status.setText(said)
        self._refresh_titles()
        return opened

    def _store_session(self, tabs: list[Buffer], current: Buffer | None) -> int:
        """Remembers the tabs that were open for the next start.

        `tabs` is the tab list taken *before* the closing questions walked over
        it, and it holds the buffers themselves rather than copies: a buffer the
        user saves to a file while closing is then remembered as the file it
        became, not as the unnamed buffer it was.  An untitled buffer answered
        with «Не сохранять» is left out (`self._discarded`) — that answer means
        the text is not to be seen again.

        A file tab is stored by its path (see `documents.TabRecord`) and an
        untitled one by its text and by whether it held unsaved changes, up to the
        budget; `session_records` says how many did not fit.
        """
        kept = [buffer for buffer in tabs if buffer not in self._discarded]
        records, dropped = documents.session_records(
            (buffer.model.path or "", buffer.model.name, buffer.text(), buffer.is_modified())
            for buffer in kept
        )
        self._settings.session_tabs = documents.encode_tabs(records)
        self._settings.session_current = (
            (current.model.path or current.model.name) if current is not None else ""
        )
        return dropped

    def session_tabs(self) -> list[documents.TabRecord]:
        """The remembered session as it stands (what a test and `О программе` read)."""
        return documents.decode_tabs(self._settings.session_tabs)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """Closing the window asks about every modified buffer first."""
        self._closing = True
        try:
            # What the next start should reopen is taken here, while the tabs are
            # still there, and *written* only once the close really happened:
            # answering «Отмена» to a save question leaves the window open, and a
            # session stored on the way out would then describe a window that never
            # closed.  The questions may take a buffer out of it — «Не сохранять»
            # on an unnamed buffer — so the list is not what is in `_buffers` now.
            self._discarded.clear()
            tabs = list(self._buffers)
            current = self.current_buffer()
            if self.close_all():
                self._store_session(tabs, current)
                self._save_split_state()
                self._save_panel_state()
                self._save_window_state()
                # The interpreter is this window's child: an unasked-for close
                # must not leave it running behind the user (and a headless test
                # suite otherwise collects one live process per test).
                self.stop_program()
                event.accept()
            else:
                event.ignore()
        finally:
            self._closing = False

    # -- keys ---------------------------------------------------------------
    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """`Esc` closes what is in the way, in one order (task_48).

        The graphics window, then the find bar, then the reference dock, then the
        cheat sheet: the thing a reader just put on the screen is the thing they
        want gone, and the picture is the biggest of them.

        Handled by *propagation*, not by a `QShortcut`.  A shortcut is processed
        before the focused widget, and it would take `Esc` away from the
        completion popup (which closes on `Esc`) and from the find bar's own
        field: those two answer for themselves, and what is left lands here.
        """
        if event.key() == Qt.Key.Key_Escape and self._escape_closes_something():
            event.accept()
            return
        super().keyPressEvent(event)

    def _escape_closes_something(self) -> bool:
        """One step of the `Esc` order; False when there is nothing to close.

        The graphics window counts as «in the way» only while it is on screen —
        closing it is the same gesture as unticking the entry, so the state is
        remembered the way the entry remembers it.
        """
        if self._graphics_window is not None and self._graphics_window.isVisible():
            self.show_graphics_window(False)
            return True
        if self.find_open():
            self.close_find()
            return True
        if not self._reference_dock.isHidden():
            self._reference_dock.hide()
            return True
        if not self._shortcut_dock.isHidden():
            self._shortcut_dock.hide()
            return True
        return False

    # -- commands that act on the current tab ------------------------------
    def _comment(self) -> None:
        self.editor().comment()

    def _uncomment(self) -> None:
        self.editor().uncomment()

    def _reset_zoom(self) -> None:
        self.editor().reset_zoom()

    # -- searching ---------------------------------------------------------
    def find_bar(self) -> findbar.FindBar:
        """The bar itself — its fields are what the user and the tests type into."""
        return self._find_bar

    def find_open(self) -> bool:
        """Whether the bar is on screen.

        `isHidden`, not `isVisible`: a window that was never shown reads as
        invisible whatever the bar is doing, the same trap the toolbar switch has.
        """
        return not self._find_bar.isHidden()

    def _find_view(self) -> CodeEditor | None:
        """The view the search works on: the active pane's current tab."""
        pane = self.active_pane() if self._panes else None
        return pane.current_view() if pane is not None else None

    def _find_options(self) -> search.Options:
        return search.Options(
            match_case=self._find_bar.match_case(),
            whole_word=self._find_bar.whole_word(),
            span=self._find_span,
        )

    @staticmethod
    def _prefill(view: CodeEditor) -> str:
        """What `Ctrl+F` starts with: the selection, else the word at the caret."""
        return view.selected_token() or view.word_under_cursor()

    @staticmethod
    def _match_from(
        text: str, needle: str, position: int, options: search.Options
    ) -> tuple[int | None, bool]:
        """The match at `position`, else the next one, and whether that wrapped.

        A caret *inside* a match counts as being on it: `Ctrl+F` in the middle of
        `факт` must land on that `факт`.  An `F3` step is unaffected, because it
        continues after the match it has just found.
        """
        covered = search.match_at(text, needle, position, options)
        if covered is not None:
            return covered, False
        offset = search.next_match(text, needle, position, options)
        return offset, offset is not None and offset < position

    def show_find(self, text: str | None = None) -> bool:
        """`Ctrl+F`: the bar above the editor, prefilled and focused.

        `text` overrides the prefill, so a caller can hand over a question of its
        own.  An empty prefill leaves the previous question in the field: a reader
        who searched for `факт` a moment ago does not want the field wiped because
        the caret happens to sit on a bracket.
        """
        view = self._find_view()
        if view is None:
            return False
        if text is None:
            text = self._prefill(view)
        if text:
            self._find_bar.set_needle(text)
        self._find_bar.setVisible(True)
        self._bind_find_view(view)
        self._find_current = None
        if self._find_bar.needle():
            # From the caret: a match the caret is *inside* is the one to start on.
            self.find_step(False)
        else:
            self._refresh_find()
        self._find_bar.focus_find()
        return True

    def close_find(self) -> None:
        """`Esc`: the bar and its highlight go, and the editor has the focus."""
        self._find_bar.setVisible(False)
        self._find_bar.set_only_in_selection(False)
        self._find_span = None
        self._find_matches = []
        self._find_current = None
        self._bind_find_view(None)
        self._apply_find_highlight()
        view = self._find_view()
        if view is not None:
            view.setFocus()

    def find_step(self, backwards: bool = False) -> bool:
        """`F3` / `Shift+F3`: the next match, wrapping at the ends.

        Works with the bar closed — the question in its field is the one the last
        search asked — but a bar that has never been used has no question and
        `F3` then does what `Ctrl+F` does.
        """
        view = self._find_view()
        if view is None:
            return False
        if not self._find_bar.needle():
            return self.show_find()
        needle = self._find_bar.needle()
        options = self._find_options()
        text = view.toPlainText()
        found = search.matches(text, needle, options)
        self._find_matches = found
        if not found:
            self._find_current = None
            self._apply_find_highlight()
            self._find_status()
            return False
        if self._find_current in found:
            # Past the match the caret is on, in the direction of travel.
            start = self._find_current - 1 if backwards else self._find_current + len(needle)
        else:
            start = view.textCursor().selectionStart()
        if backwards:
            offset = search.previous_match(text, needle, start, options)
            # It wrapped when the match is *after* where the search started.
            wrapped = offset > start
        else:
            offset, wrapped = self._match_from(text, needle, start, options)
        self._find_current = offset
        self._select_match(view, offset, len(needle))
        self._apply_find_highlight()
        self._find_status(wrapped=wrapped, backwards=backwards)
        return True

    def _find_step_from_bar(self, backwards: bool) -> None:
        """`Enter`/`Shift+Enter` in the question field."""
        self.find_step(backwards)

    def replace_current(self) -> bool:
        """«Заменить»: the match the caret is on, then look for the next one."""
        view = self._find_view()
        needle = self._find_bar.needle()
        if view is None or not needle or self._find_current is None:
            return False
        replacement = self._find_bar.replacement()
        offset = self._find_current
        cursor = view.textCursor()
        cursor.setPosition(offset)
        cursor.setPosition(offset + len(needle), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)  # one `insertText` is one undo step itself
        # The caret now sits after what was written, and that is where the next
        # step goes from.
        self._find_current = None
        return self.find_step(False)

    def replace_all(self) -> bool:
        """«Заменить всё»: every match, in *one* undo step.

        The whole replacement is one block of edits, the way comment/uncomment is:
        a reader who disliked it presses `Ctrl+Z` once, not once per match.
        """
        view = self._find_view()
        needle = self._find_bar.needle()
        if view is None or not needle:
            return False
        replacement = self._find_bar.replacement()
        text = view.toPlainText()
        replaced, how_many = search.replace_all(text, needle, replacement, self._find_options())
        if not how_many:
            self._refresh_find()
            self._find_bar.set_status("не найдено")
            return False
        cursor = view.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.setPosition(0)
            cursor.setPosition(len(text), QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(replaced)
        finally:
            cursor.endEditBlock()
        self._find_current = None
        self._refresh_find()
        # After `_refresh_find`, which sets the status of the search that is left.
        self._find_bar.set_status(f"заменено {how_many}")
        return True

    def _select_match(self, view: CodeEditor, offset: int, length: int) -> None:
        cursor = view.textCursor()
        cursor.setPosition(offset)
        cursor.setPosition(offset + length, QTextCursor.MoveMode.KeepAnchor)
        view.setTextCursor(cursor)
        # Scrolled into view, but not centred: a match jumping to the middle of the
        # window loses the paragraph the reader was following.
        view.ensureCursorVisible()

    def _refresh_find(self) -> None:
        """Recomputes the matches after the text or the question changed.

        The caret is deliberately not moved here: typing in the editor with the bar
        open must not throw the caret into the next match.  Only a step does that.
        """
        view = self._find_view()
        needle = self._find_bar.needle()
        options = self._find_options()
        text = view.toPlainText() if view is not None else ""
        self._find_matches = search.matches(text, needle, options) if needle and view else []
        if self._find_current not in self._find_matches:
            self._find_current = None
        if self._find_current is None and self._find_matches and view is not None:
            # The match the caret is on (or inside), else the first one after it.
            self._find_current, _wrapped = self._match_from(
                text, needle, view.textCursor().selectionStart(), options
            )
        self._apply_find_highlight()
        self._find_status()

    def _on_find_changed(self) -> None:
        """The question or a switch changed: search again from the caret."""
        view = self._find_view()
        if view is None:
            return
        self._find_current = None
        if self._find_bar.needle():
            self.find_step(False)
        else:
            self._refresh_find()

    def _on_find_span_toggled(self, checked: bool) -> None:
        """«Только в выделении» keeps the span it was switched on over.

        Kept, and not read again on every step: the search itself moves the
        selection, so a span read afresh would shrink to the match just found.
        """
        view = self._find_view()
        cursor = view.textCursor() if view is not None else None
        if checked and (cursor is None or not cursor.hasSelection()):
            self._find_bar.uncheck_only_in_selection()
            self._find_bar.set_status("сначала выделите фрагмент")
            self._find_span = None
            return
        self._find_span = (
            (cursor.selectionStart(), cursor.selectionEnd()) if checked and cursor else None
        )
        self._on_find_changed()

    def _refollow_find(self) -> None:
        """Points the bar at the pane and the tab that are showing now."""
        if not self.find_open():
            return
        self._bind_find_view(self._find_view())
        self._find_current = None
        self._refresh_find()

    def _bind_find_view(self, view: CodeEditor | None) -> None:
        """Keeps the matches fresh while the text is edited under the bar."""
        if self._find_bound is view:
            return
        if self._find_bound is not None:
            try:
                self._find_bound.textChanged.disconnect(self._refresh_find)
            except (RuntimeError, TypeError):  # the view is already gone
                pass
        self._find_bound = view
        if view is not None:
            view.textChanged.connect(self._refresh_find)

    def _apply_find_highlight(self) -> None:
        """Paints the matches in every view of the active document, nowhere else.

        Every view, because the split editor shows one text twice; and only the
        active document, because a highlight left in a tab the user switched away
        from is a lie about where the search is.
        """
        pane = self.active_pane() if self._panes else None
        buffer = pane.current_buffer() if pane is not None else None
        length = len(self._find_bar.needle())
        current = None if self._find_current is None else (self._find_current, length)
        ranges = (
            [(offset, length) for offset in self._find_matches] if self.find_open() else []
        )
        if self._find_highlighted is not None and self._find_highlighted is not buffer:
            for view in self._find_highlighted.views():
                view.set_search_ranges([])
            self._find_highlighted = None
        if buffer is not None:
            for view in buffer.views():
                view.set_search_ranges(ranges, current)
            self._find_highlighted = buffer if ranges else None

    def _find_status(self, wrapped: bool = False, backwards: bool = False) -> None:
        """«3 из 17», and where the search went round — reported, not silent."""
        if not self._find_bar.needle():
            self._find_bar.set_status("")
            return
        if not self._find_matches:
            self._find_bar.set_status("не найдено")
            return
        index = (
            self._find_matches.index(self._find_current) + 1
            if self._find_current in self._find_matches
            else 0
        )
        where = ""
        if wrapped:
            where = " — поиск с конца" if backwards else " — поиск с начала"
        self._find_bar.set_status(f"{index} из {len(self._find_matches)}{where}")

    # -- input requests ----------------------------------------------------
    def _on_input_request(self, kind: str) -> None:
        """Feeds the program: the prepared lines first, the dialog only after them.

        The lines come from the field under the output pane, one per request, and
        are echoed with `>` so it stays visible what the program was given.  Only
        when that list is empty does the window ask the user.

        An answer typed here is a *piece of the program's input stream*, not one
        line: since task_54 the interpreter splits it on `\n` itself, so two lines
        in the console answer two `ВВОДСТР` and the window is asked once.  The
        queue below still gives one line per request — it is where the `>` echo
        and the «осталось строк» counter come from, and it is typed one line at a
        time anyway.

        Where it asks is the «Спрашивать ввод» switch (task_29): in the console
        under the output — the field takes the answer and the box is what is left
        when that panel is hidden — or in a box every time.
        """
        if self._stopped_input:
            # Cancelled earlier in this run: the interpreter is on its way out and
            # must not be given anything else to wait for.
            self._session.answer_input("")
            return
        if self._queued_input:
            line = self._queued_input.pop(0)
            self._append_output(f"> {line}\n", panels.ECHO)
            self._session.answer_input(line)
            self._status.setText(f"ввод из поля, осталось строк — {len(self._queued_input)}")
            return
        if not self._panel_tabs.isHidden() and self._settings.input_mode == "panel":
            # The console appears under the goal line, and the panel stays on
            # the tab the reader chose (usually Вывод) — the question never pulls
            # the eye off the output it belongs to (task_50).
            self._input_console.ask(kind)
            self._status.setText(f"ждёт ввода: {panels.INPUT_PROMPTS.get(kind, 'значение')}")
            return
        answer = self._ask_input(kind)
        if answer is None:
            self._cancel_input()
            return
        self._send_input(answer)

    def _send_input(self, answer: str) -> None:
        """One answer — from the console or from the dialog — echoed and sent."""
        self._input_console.idle()
        self._append_output(f"> {answer}\n", panels.ECHO)
        self._session.answer_input(answer)
        self._status.setText("ввод принят")

    def _cancel_input(self) -> None:
        """«Отмена» stops the whole run: nothing else is asked during it."""
        self._stopped_input = True
        self._input_console.idle()
        self._append_note("--- ввод отменён: программа остановлена ---\n")
        self._session.stop()
        self._status.setText("ввод отменён, выполнение остановлено")

    def _input_lines(self) -> list[str]:
        """The input field, one answer per line, blank lines dropped.

        A line is taken as written — leading spaces can matter for a string — but
        a line that is empty or only spaces is an answer to nothing, and skipping
        it is what keeps the field easy to read.  The field is a tab of its own
        since task_50, so its lines feed every run, whichever tab is showing.
        """
        return [line for line in self._input_pane.toPlainText().split("\n") if line.strip()]

    def _ask_input(self, kind: str) -> str | None:
        """One line from the user; `None` when the question was cancelled.

        A method of its own, like `_ask_save`: a modal box cannot be driven from a
        headless test, and a test that forgets to replace it hangs instead of
        failing.  The field is single-line on purpose — `Enter` answers, the way it
        does in the query line, and a whole line of program input is rarely a
        paragraph.
        """
        prompt = {"token": "Слово", "line": "Строки", "codepoint": "Символ"}.get(kind, "Ввод")
        answer, accepted = QInputDialog.getText(self, "Ввод", prompt + ":")
        return answer if accepted else None

    # -- accessors for the actions and the tests ---------------------------
    @property
    def session(self) -> PrologSession:
        """The interpreter session; the window owns exactly one."""
        return self._session

    def buffers(self) -> list[Buffer]:
        """The open documents, in the order the panes show them."""
        return list(self._buffers)

    def tab_count(self) -> int:
        return len(self._buffers)

    def current_buffer(self) -> Buffer | None:
        """The document the commands act on: the active pane's current tab."""
        return self.active_pane().current_buffer()

    def _buffer_of_view(self, view) -> Buffer | None:
        """The open buffer a view shows, or None when that view is gone."""
        for buffer in self._buffers:
            if any(shown is view for shown in buffer.views()):
                return buffer
        return None

    def editor(self) -> CodeEditor:
        """The current tab's editor in the active pane.

        There is always one while the window is open: the last document is never
        closed without a replacement being made.
        """
        view = self.active_pane().current_view()
        assert view is not None, "окно без вкладок"
        return view

    def editor_text(self) -> str:
        buffer = self.current_buffer()
        return buffer.text() if buffer is not None else ""

    def _current_document_text(self) -> str:
        """The text the query line's completion scans: the showing buffer's.

        A goal names predicates of the file it will run against, so the query
        line offers them from here rather than from its own one line (task_50).
        """
        return self.editor_text()

    def output(self) -> ZoomablePlainTextEdit:
        """The read-only output pane (task_27 gives it a place of its own)."""
        return self._output

    def input_pane(self) -> ZoomablePlainTextEdit:
        """The input queue under the output: one line per answer."""
        return self._input_pane

    def pending_input(self) -> list[str]:
        """The prepared answers that are left for the running program."""
        return list(self._queued_input)

    def status_text(self) -> str:
        """What the status bar says — the running program's state, in words."""
        return self._status.text()

    def output_text(self) -> str:
        """What the Вывод pane holds — the batch still in flight goes in first.

        The window hands output over on the next turn of the event loop (task_49),
        so a caller that reads the pane has to be the one who ends that turn: a test
        and «сохранить вывод» would otherwise miss the last lines of a run.
        """
        self._flush_output()
        return self._output.toPlainText()

    def problems_text(self) -> str:
        """What the Проблемы pane holds: the run's errors and warnings."""
        self._flush_output()
        return self._problems.toPlainText()

    def system_text(self) -> str:
        """What the Система pane holds: the window's own notes."""
        self._flush_output()
        return self._system.toPlainText()

    def current_path(self) -> str | None:
        buffer = self.current_buffer()
        return buffer.model.path if buffer is not None else None

    def recent_files(self) -> list[str]:
        """What the recent-files menu of task_26 will show, newest first."""
        return self._recent.paths()

    # -- the reference of a predicate --------------------------------------
    def show_reference(self) -> None:
        """`F1`: the record of the word under the caret — summary, modes, section.

        An unknown word is said in so many words: silence would look like a dead
        key.  A checkout without `doc/builtins.json` is not a failure either —
        the dock says the reference is unavailable.
        """
        if len(self._reference) == 0:
            text = "справочник недоступен: не найден doc/builtins.json"
        else:
            view = self.editor()
            word = view.selected_token() or view.word_under_cursor()
            record = self._reference.record(word) if word else None
            if record is None:
                text = (
                    f"нет справки для «{word}»"
                    if word
                    else "поставьте курсор на имя предиката"
                )
            else:
                text = self._reference_text(record)
        self._reference_pane.setPlainText(text)
        self._reference_dock.setVisible(True)
        self._reference_dock.raise_()

    @staticmethod
    def _reference_text(record: dict) -> str:
        """A record as the dock shows it: the title, the section, the modes."""
        lines = [reference.record_title(record)]
        lines.append(f"раздел руководства: {record['section']}")
        variants = record.get("variants") or []
        if variants:
            lines.append("")
            lines.extend(variants)
        return "\n".join(lines)

    def reference_text(self) -> str:
        """What the reference dock is showing ("" while it was never filled)."""
        return self._reference_pane.toPlainText()

    # -- the cheat sheet of the insert chords ------------------------------
    def show_shortcuts(self) -> None:
        """«Справка → Шпаргалка по вставкам»: what `Ctrl`+key inserts (task_31).

        The list is built from the table itself, so a remapped chord shows up
        here without a second place to edit — and a dock, not a modal box, for
        the same reason as the reference: it is read *next to* the code, and a
        modal cannot be driven from a headless test.
        """
        self._shortcut_pane.setPlainText("\n".join(self._shortcuts.cheatsheet()))
        self._shortcut_dock.setVisible(True)
        self._shortcut_dock.raise_()

    def shortcut_text(self) -> str:
        """What the cheat-sheet dock is showing ("" while it was never filled)."""
        return self._shortcut_pane.toPlainText()

    # -- session events ----------------------------------------------------
    def _on_ready(self, version: str) -> None:
        # The reserved names reach every open buffer, including the ones opened
        # before the interpreter announced itself; those created later are served
        # by `_add_buffer`.
        self._version = version
        self._exit_code = None
        self._warning_count = 0
        for buffer in self._buffers:
            buffer.set_keywords(self._session.keywords)
            buffer.set_reference(self._reference)
        # The goal field offers the same names (task_50).
        self._query_line.set_completion_keywords(self._session.keywords)
        self._status.setText(f"PrologD {version} готов")
        self._refresh_titles()
        self._sync_run_actions()
        self._update_details()

    def _on_zoom_changed(self, size: float) -> None:
        """The editor's own size — a preference since task_29, not both panels'.

        Setting the size on the other editors emits `zoomChanged` again; those
        calls change nothing and stop there, because `set_font_size` returns
        early when the size is already the one asked for.  The output panel has a
        size of its own (`_on_output_zoom`), which is why the two are apart.
        """
        self._settings.font_size = size
        for buffer in self._buffers:
            buffer.set_font_size(size)
        # The output has no size of its own until someone gives it one: while the
        # key is unwritten it follows the editor, exactly as it did before task_29
        # split the two.  A wheel over the panel writes the key, and from then on
        # the two are apart for good.  The follow applies the size *without*
        # writing it: writing the key here froze the pair on the very first zoom,
        # which nobody asked for — and after task_58 took the size box off the
        # toolbar, zooming is the everyday way to change the size.
        if not self._settings.has(OUTPUT_FONT_SIZE):
            self._apply_output_font(size)
        # The step strip and the two help panes show program text, so they read
        # at the program's size; the query line is typed like one, too.
        self._step_pane.set_font_size(size)
        self._reference_pane.set_font_size(size)
        self._shortcut_pane.set_font_size(size)
        self._sync_query_line_font()
        self._status.setText(f"шрифт редактора: {size:.0f} pt")

    def _on_output_zoom(self, size: float) -> None:
        """The output's own size: the pane, the input queue and the console."""
        self._settings.output_font_size = size
        self._apply_output_font()
        self._status.setText(f"шрифт вывода: {size:.0f} pt")

    def _apply_output_font(self, size: float | None = None) -> None:
        """Pushes the output's size into the panes and the input widgets.

        `size` is for the case where the output is *following* the editor: the size
        is then applied with the panes' signals blocked, so the key that means «the
        output has a size of its own» stays unwritten until the output itself is
        resized.  The block is the whole point: the five panes report `zoomChanged`,
        their own handler (`_on_output_zoom`) reads that as «the user resized me» and
        writes the key — which is how the very first editor zoom used to freeze the
        follow.
        """
        following = size is not None
        if size is None:
            size = self._settings.output_font_size
        panes = (self._output, self._problems, self._system, self._input_pane, self._table)
        if following:
            for pane in panes:
                pane.blockSignals(True)
        try:
            for pane in panes:
                pane.set_font_size(size)
            self._input_console.set_font_size(size)
        finally:
            if following:
                for pane in panes:
                    pane.blockSignals(False)

    def _sync_query_line_font(self) -> None:
        """The query line reads like the program it asks about, not like the log."""
        font = QFont(self._settings.font_family)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSizeF(self._settings.font_size)
        self._query_line.setFont(font)

    # -- the settings dialog (task_29) --------------------------------------
    def show_settings(self) -> bool:
        """«Правка → Настройки…»: the dialog, then whatever it changed.

        The dialog writes through `Settings` itself (ОК, «Применить»), and the
        window re-reads the store afterwards — which is what makes a change show
        without a restart.  `_run_settings_dialog` is the modal `exec()` in one
        replaceable method: a modal box hangs a headless test instead of failing
        it, and the settings are not worth breaking that rule for.
        """
        dialog = settingsdialog.SettingsDialog(self._settings, self)
        # «Применить» must be *visible*: the window behind a modal dialog still
        # paints, so the dialog says «written» and the window re-reads the store
        # right then, instead of waiting for the dialog to close.
        dialog.changesApplied.connect(self.apply_settings)
        try:
            accepted = self._run_settings_dialog(dialog)
            applied = dialog.applied()
        finally:
            dialog.deleteLater()
        if applied:
            self.apply_settings()
        return accepted and applied

    def _run_settings_dialog(self, dialog) -> bool:
        """Runs the dialog modally; tests replace this with a scripted answer."""
        from PySide6.QtWidgets import QDialog

        return dialog.exec() == QDialog.DialogCode.Accepted

    def apply_settings(self) -> None:
        """Pushes every preference into the widgets — no restart needed.

        The whole list, not the difference: it is cheap, it makes «Применить» and
        a start-up read share one code path, and a switch that forgot to arrive is
        exactly the bug this method exists to prevent.
        """
        for buffer in self._buffers:
            buffer.set_font_family(self._settings.font_family)
            buffer.set_font_size(self._settings.font_size)
            buffer.set_line_numbers(self._settings.line_numbers)
            buffer.set_current_line(self._settings.current_line)
            buffer.set_wrap(self._settings.wrap)
            buffer.set_indent(self._settings.indent_character, self._settings.indent_width)
            buffer.set_auto_indent(self._settings.auto_indent)
            buffer.set_palette(self._settings.palette)
            buffer.set_completion(
                self._settings.completion,
                self._settings.auto_complete_after,
                self._settings.completion_match_case,
            )
        # The goal field follows the same two knobs (task_50).
        self._query_line.set_auto_complete_after(self._settings.auto_complete_after)
        self._query_line.set_completion_match_case(self._settings.completion_match_case)
        self._apply_output_font()
        for pane in (self._output, self._problems, self._system):
            pane.set_line_limit(self._settings.output_line_limit)
            pane.set_palette(self._settings.palette)
        # The table has no line limit of its own and its own colour: the grid comes
        # from the theme, and Qt's default is a light-palette one (task_59).
        self._table.set_palette(self._settings.palette)
        self._output.set_follow_output(self._settings.follow_output)
        self._sync_query_line_font()
        self._step_pane.set_font_size(self._settings.font_size)
        self._reference_pane.set_font_size(self._settings.font_size)
        self._shortcut_pane.set_font_size(self._settings.font_size)

        self._toolbar.setVisible(self._settings.toolbar_visible)
        self._panel_tabs.setVisible(self._settings.output_visible)
        self._apply_output_position(remember=False)
        self._refresh_panel_tabs()
        appearance.apply_theme(QApplication.instance(), self._settings.theme)

        # The insert table is data in the same file, and «Вернуть встроенную
        # таблицу» in the dialog has to reach the editors of an open window too.
        table = shortcuts.Shortcuts.from_json(self._settings.shortcuts_table)
        self._shortcuts = table
        for buffer in self._buffers:
            buffer.set_shortcuts(table)

        # The search path and the cheap timers: `-I`, autosave, the recent list.
        self._session.set_includes(self._import_directories())
        self._apply_autosave()
        self._trim_recent()

        self._sync_format_menu()
        self._sync_theme_menu()
        self._sync_actions()
        self._status.setText("настройки применены")

        # The interpreter and where its files go (task_46): a changed value
        # cannot reach a live process (the program and the working directory are
        # fixed once it is up), so a live session is restarted — and the status
        # says so, because a silently different interpreter is exactly the
        # mystery these rows exist to end.  A path that does not exist is not
        # something to restart *to*: the live session keeps its own binary, the
        # row takes effect at the next start, and the status says why.
        executable = self._interpreter_path()
        directory = self._process_working_directory()
        changed = executable != self._session.executable() or directory != self._session.working_directory()
        if changed:
            live = self._session.is_running()
            self._session.set_executable(executable)
            self._session.set_working_directory(directory)
            if live:
                if pathlib.Path(executable).is_file():
                    self._session.start()
                    self._status.setText(
                        "настройки применены; интерпретатор изменён — сессия перезапущена"
                    )
                else:
                    self._status.setText(
                        f"интерпретатор не найден: {pathlib.Path(executable).name}"
                    )
        self._update_details()

    def _import_directories(self) -> list[str]:
        """The `-I` directories of the next session: command line, then settings.

        «Дополнительные каталоги ИМПОРТ» is a *search* list for `ИМПОРТ`, not the
        working directory of the process, and it is passed exactly like
        `--include`: the engine tries the importing file's own folder first, so a
        local `lib/x.pld` still wins over a same-named file in a shared one
        (task_46 folded the single «Рабочая папка» row into this list).
        """
        directories = list(self._command_line_includes)
        directories.extend(self._settings.import_paths)
        seen: set[str] = set()
        result: list[str] = []
        for directory in directories:
            text = str(directory).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    def _trim_recent(self) -> None:
        """Applies a new «Помнить недавних файлов» to the list already stored."""
        limit = self._settings.recent_limit
        if self._recent.limit() == limit:
            return
        self._recent = documents.RecentFiles(self._recent.paths(), max_size=limit)
        self._settings.recent_files = self._recent.paths()

    # -- autosave (task_29) -------------------------------------------------
    def _apply_autosave(self) -> None:
        """Arms or disarms the autosave timer from the settings."""
        minutes = self._settings.autosave_minutes
        if minutes <= 0:
            self._autosave.stop()
            return
        self._autosave.start(int(minutes) * 60_000)

    def autosave_now(self) -> int:
        """Writes every modified buffer that has a name; returns how many.

        The timer calls this, and a test calls it directly rather than waiting a
        minute.  A buffer without a path is *skipped*: an autosave must never ask
        a question (a name nobody chose is not a file), and a modal box out of a
        timer would be the worst possible one.  A buffer that cannot be written
        — read-only file, locked directory — is reported in the output pane and
        left alone; nothing is lost, because the text stays in the tab.
        """
        written = 0
        for buffer in self._buffers:
            if buffer.model.path is None or not buffer.is_modified():
                continue
            buffer.take_text()
            try:
                buffer.model.save()
            except (OSError, UnicodeEncodeError) as error:
                self._append_note(f"*** автосохранение: {buffer.title()}: {error}\n")
                continue
            buffer.mark_saved()
            written += 1
        if written:
            self._refresh_titles()
            self._status.setText(f"автосохранение: файлов {written}")
        return written

    def _on_result(self, found: bool) -> None:
        """Records the outcome; the text of the answer already arrived as output.

        The interpreter prints `ДА`, `НЕТ` or the bindings itself, and `result`
        only says the query is over.  Appending another `НЕТ` here is what made a
        failing query print it twice — the program was never wrong.

        The query being over is what frees `Запустить`: the run is finished, the
        knowledge base is still loaded, and the next run restarts the file.
        """
        if self._stopping:
            # The query we asked to stop has concluded.  A read that was waiting
            # for input ends as a *failure* (`НЕТ`), not as an error — the
            # interpreter calls the cut-off read the end of input — so the stop
            # has to finish here as well as in `_on_failed`.
            self._finish_polite_stop()
            return
        self._busy = False
        self._results_in_load += 1
        self._awaiting_query = False
        # The answer is complete now, so the table is built from it (task_59).  A
        # `result` of the program's own questions finds nothing collected and does
        # nothing: only a single goal arms the collection.
        self._finish_answer_table()
        text = "решение найдено" if found else "решения нет"
        if self._warning_count:
            text += f" · предупреждений: {self._warning_count}"
        self._status.setText(text)
        if not self._session.paused():
            # Whatever was being stepped through is over; the line it stopped on
            # stays marked until the next run or the first edit.
            self._step_pane.idle()
            self._step_stack.clear()
        self._sync_run_actions()
        self._update_details()

    # -- the answer table (task_59) ----------------------------------------
    def _arm_answer_table(self) -> None:
        """Starts collecting the output for the table — if the switch asks for it.

        Called where a *single* goal is sent (the goal line, a margin marker), and
        never by `run_program`: a whole run answers all of its `?`-questions into
        one stream where nothing tells the answers apart, so there is no table to
        build (task_59, §5).  With the switch off nothing is collected at all.
        """
        self._answer_text = [] if self._settings.answer_table else None

    def _finish_answer_table(self) -> None:
        """Shows the answer of the goal that just concluded — and disarms.

        The table is emptied when there is nothing to show, so the tab never keeps
        a table of a question the user has moved on from.  A diagnostic of this run
        keeps the panel on «Проблемы» (`_show_panel_tab` there): an error is what
        is looked for after a bad run, and a table must not push it aside.
        """
        collected = self._answer_text
        self._answer_text = None
        if collected is None:
            return
        answer = answers.parse("".join(collected))
        self._table.set_answer(answer)
        self._refresh_panel_tabs()
        if answer.is_empty() or self._error_count or self._warning_count:
            return
        self._show_panel_tab(panels.TAB_TABLE)

    def _on_loaded(self) -> None:
        """The load and the program's own `?`-statements are over (protocol 8).

        `result` arrives once per question, so a program that asks none — an
        empty one included — used to leave the window saying «выполняется» with
        `Запустить` disabled forever: nothing said the run had finished.  The
        event does, and the run state follows it.  The status keeps the last
        answer when there was one, and the error's message when it was an error
        that concluded the run; only a run that said nothing at all gets a word
        of its own instead of the stale «выполняется».
        """
        if self._awaiting_query or self._stopping:
            # A question still has to answer (the margin's click), or a stop of
            # our own is in flight; both conclude with their own event.  The line
            # about the load is not one of those things: the knowledge base is
            # loaded by now, whoever asked for it, and a click on a margin marker
            # gets the same line `F5` gets (task_58).  It goes *before* the answer,
            # which is the order `F5` produces as well.
            if self._awaiting_query and not self._failed_in_load:
                self._append_note(
                    f"--- база знаний загружена ({self._run_clock.elapsed()} мс) ---\n"
                )
                # The program parsed, so the question that was waiting for it can
                # be asked now (task_60).
                self._send_pending_query()
            return
        self._busy = False
        if not self._failed_in_load:
            # The whole file ran to the end (protocol 8): one system line says how
            # long the load took, measured by the window's own clock (task_50).
            self._append_note(
                f"--- база знаний загружена ({self._run_clock.elapsed()} мс) ---\n"
            )
        if self._results_in_load == 0 and not self._failed_in_load:
            self._status.setText("выполнено")
        self._sync_run_actions()
        self._update_details()

    def _on_failed(self, kind: str, severity: str, message: str, position=None) -> None:
        """A diagnostic: the pane shows it with its file, the editor marks the line.

        The position arrives in fields of its own (protocol 3), so nothing is
        parsed out of the message — the message is what the interpreter wrote, and
        the file and the line are put in front of it here.  A *warning* is amber
        in the pane and counted in the status bar; it never ends the run, which is
        why the rest of this handler only runs for an error.
        """
        where = position.where() if position is not None else ""
        if kind == "format":
            # The format request failed and the buffer was left exactly as it was.
            # The line is marked when the diagnostic is about the whole buffer; a
            # selection is a fragment, and its line numbers are not the buffer's.
            pending = self._format_pending
            self._format_pending = None
            if (
                position is not None
                and pending is not None
                and pending["region"] is None
                and self._buffer_of_view(pending["view"]) is self.current_buffer()
            ):
                self._mark_error_line(position)
            self._status.setText(f"форматирование: не удалось разобрать — {message}")
            return
        if self._stopping and self._session.is_running() and severity != "warning":
            # This is the error of the query *we* stopped: the run is over — the
            # note of the stop says so — and a user's own stop marks no line.
            # (After a terminated process there is nothing to finish: the events
            # that were already in flight are shown as they always were.)
            self._finish_polite_stop()
            return
        if severity == "warning":
            self._append_output(
                f"*** предупреждение: {where + ': ' if where else ''}{message}\n",
                panels.WARNING,
            )
            self._warning_count += 1
            self._show_panel_tab(panels.TAB_PROBLEMS)
            self._refresh_panel_tabs()
            self._status.setText(
                f"предупреждение: {where or 'без места'} (всего: {self._warning_count})"
            )
            return
        self._append_output(
            f"*** {kind}: {where + ': ' if where else ''}{message}\n", panels.ERROR
        )
        self._error_count += 1
        self._busy = False
        self._failed_in_load = True
        self._awaiting_query = False
        # The query ended in an error, not in an answer: nothing to tabulate, and a
        # question that was waiting for this program is not asked at all (task_60).
        self._answer_text = None
        self._drop_pending_query("--- вопрос не выполнен: база знаний не загрузилась ---\n")
        self._step_pane.idle()
        self._step_stack.clear()
        self._show_panel_tab(panels.TAB_PROBLEMS)
        self._refresh_panel_tabs()
        if position is not None and position.line:
            self._mark_error_line(position)
        # A failure ends whatever was in flight; whether the process is still there
        # is a separate question, and `_sync_run_actions` asks it.
        self._sync_run_actions()
        self._update_details()

    def _on_trace(self, text: str) -> None:
        """The `ТРАССА` text of a traced run: the pane colours it apart."""
        self._append_output(text, panels.TRACE)

    # -- stepping ----------------------------------------------------------
    def step_pane(self) -> panels.StepPane:
        """The strip that shows where a stepped run stands."""
        return self._step_pane

    def stepping(self) -> bool:
        """True while the step panel is up: a stepped run is in flight."""
        return not self._step_pane.isHidden()

    def step_into(self) -> None:
        """`F10`: one point further in — or start a run that stops at the first."""
        if self._session.paused():
            self._session.answer_step("into")
            return
        self.run_program(step=True)

    def step_over(self) -> None:
        """`Shift+F10`: on to the next point of *this* goal, or to its end.

        The skipping happens in the interpreter: the points inside the goal are
        not stops there.  Doing it here would mean receiving them all and
        discarding them, which is the same traffic for no gain.
        """
        if self._session.paused():
            self._session.answer_step("over")
            return
        self.run_program(step=True)

    def step_continue(self) -> None:
        """`F5` while paused: run on to the end without stopping again."""
        if not self._session.paused():
            return
        self._session.answer_step("continue")
        self._step_stack.clear()
        self._step_pane.idle()
        self._status.setText("продолжение без остановок")
        self._update_details()

    def _on_stepped(self, point) -> None:
        """One step point: the panel, the stack and the line in the editor.

        The stack is rebuilt here, from the events themselves: a `call` pushes the
        goal it names, and the `exit`/`fail` that answers it pops — an `exit`
        carries no goal of its own, because the goal that succeeded is the one the
        `call` already reported.
        """
        if point.action == "call":
            if point.goal:
                self._step_stack.append(point.goal)
        elif self._step_stack:
            self._step_stack.pop()
        self._step_pane.show_point(point, self._step_stack)
        self._mark_trace_line(point.position)
        self._status.setText(f"шаг: {self._step_pane.action_text()} {point.goal}".rstrip())
        self._sync_run_actions()
        self._update_details()

    # -- where a diagnostic and a step point stand -------------------------
    def _clear_marks(self) -> None:
        """Both marks, in every view: a new run starts clean."""
        for buffer in self._buffers:
            for view in buffer.views():
                view.clear_marks()

    def _diagnostic_buffer(self, position) -> Buffer | None:
        """The tab a diagnostic points at, opening it when it is a file of ours.

        A diagnostic from an `ИМПОРТ`ed file names *that* file, and marking a line
        in the wrong tab would be worse than marking none: the file is looked for
        among the open tabs, then next to the file that imported it, then on disk
        (where it is opened).  A name in angle brackets is not a file at all: the
        text the window itself sent is `<buffer>` (the program — the showing
        buffer's lines), `<query>` (one statement) or `<library>` (the
        interpreter's own) — and only the first of them has lines in a tab.
        """
        name = position.file if position is not None else ""
        if not name or name == "<buffer>":
            # The program text the window itself sent: its lines are the buffer's.
            return self.current_buffer()
        if name.startswith("<"):
            # `<query>` — the one statement of a `query` request (the query line
            # or a margin marker); `<library>` — the interpreter's own preloaded
            # text.  Neither has a line in any tab: marking the current one would
            # say the program broke where it did not.
            return None
        # An unnamed buffer is named by its tab title («Без имени 2»): the text is
        # the window's own, and its lines are that buffer's lines.
        for buffer in self._buffers:
            if buffer.model.path is None and buffer.title() == name:
                return buffer
        wanted = pathlib.Path(name)
        candidates = [wanted]
        current = self.current_buffer()
        if not wanted.is_absolute() and current is not None and current.model.path:
            # A relative name is relative to the file the import was written in.
            candidates.append(pathlib.Path(current.model.path).parent / wanted)
        for candidate in candidates:
            found = self._buffer_for_path(str(candidate))
            if found is not None:
                return found
        for candidate in candidates:
            if candidate.is_file() and self.open_path(str(candidate)):
                return self._buffer_for_path(str(pathlib.Path(candidate)))
        return None

    def _mark_error_line(self, position) -> None:
        """Marks the line a diagnostic names and puts the caret on it."""
        buffer = self._diagnostic_buffer(position)
        if buffer is None:
            if position.file.startswith("<"):
                # A statement of its own (`<query>`) or the interpreter's library:
                # nothing to mark and no caret to move — the error is about text
                # that is not in any tab.
                self._status.setText(f"ошибка: {position.where()}")
                return
            # The file is not there and could not be opened: say where the line is
            # rather than marking a line in a tab that has nothing to do with it.
            self._status.setText(f"ошибка в {position.where()} — файл не открыт")
            return
        line = position.line
        for other in self._buffers:
            for view in other.views():
                view.mark_error_line(line if other is buffer else None)
        for view in buffer.views():
            # The mark is clamped to a line that exists (`непарные скобки` is
            # reported where the input ran out), and the caret follows that one.
            view.show_line(view.error_line() or line)
        self._status.setText(f"ошибка: {position.where()}")

    def _mark_trace_line(self, position) -> None:
        """Marks the line a step stands on — in the tab that line belongs to.

        The caret follows only when that tab is the one showing: a stepped run
        through an imported file must not pull the user out of the program they
        are watching, and the mark is there when they switch to it.
        """
        buffer = self._diagnostic_buffer(position) if position is not None else None
        for other in self._buffers:
            for view in other.views():
                if other is not buffer:
                    view.mark_trace_line(None)
        if buffer is None:
            return
        for view in buffer.views():
            view.mark_trace_line(position.line)
        if buffer is self.current_buffer():
            for view in buffer.views():
                view.show_line(view.trace_line() or position.line)

    def _on_ended(self, exit_code: int) -> None:
        # A process that died while a `format` request was in flight will not
        # answer it: the buffer keeps its text and the state is dropped.
        self._format_pending = None
        # The same goes for a query that was in flight: nothing more is coming,
        # so a half-collected answer must not be picked up by the next run — nor a
        # question still waiting for a program that will never load (task_60).
        self._answer_text = None
        self._drop_pending_query()
        # A process *we* killed has no meaningful code: Windows reports the
        # termination status as a number nobody can read (62097), so the message
        # stays «остановлено» and the status bar keeps the last real code.
        if self._stopping:
            self._stopping = False
            self._flush_output()
            self._flush_pane_tails()
            self._sync_run_actions()
            self._update_details()
            return
        self._exit_code = exit_code
        self._busy = False
        self._loaded = False
        self._step_pane.idle()
        self._step_stack.clear()
        # The last half-line: a program that stopped in the middle of `ВЫВОД` left
        # it in a pane's buffer, and nothing else will complete it.
        self._flush_output()
        self._flush_pane_tails()
        self._status.setText(f"интерпретатор завершился, код {exit_code}")
        self._sync_run_actions()
        self._update_details()

    def _append_output(self, text: str, kind: str = panels.OUTPUT) -> None:
        """Queues text for the output pane, which colours it by kind.

        The pane holds whatever follows the last newline, so a program that prints
        with `ВЫВОД` and no `ПС` keeps its half-line until the rest arrives — or
        until the run ends and `flush()` writes it.  What is queued goes in on the
        next turn of the event loop (`_flush_output`), and everything that *reads*
        the pane flushes first, so no caller can see the delay — only the cost per
        line, which is what a trace of a deep recursion cannot afford (task_49).

        This is also the one funnel the answer of a single goal passes through, so
        it is where the table collects it (task_59): only `OUTPUT` counts — the
        window's notes, the diagnostics and the echo of an answer are other kinds.
        """
        if self._answer_text is not None and kind == panels.OUTPUT:
            self._answer_text.append(text)
        self._output_pending.append((kind, text))
        if not self._output_timer.isActive():
            self._output_timer.start()

    def _flush_output(self) -> None:
        """Hands the queued output to the pane: one call per run of one kind.

        A batch, not a throttle: everything that arrived in the turn goes in, and
        the next turn gets its own — nothing is dropped and nothing waits for a
        clock.  A timer that *sampled* the output would lose lines, and a lost line
        in a log is worse than a slow one.
        """
        self._output_timer.stop()
        pending = self._output_pending
        if not pending:
            return
        self._output_pending = []
        kind, text = pending[0]
        for next_kind, more in pending[1:]:
            if next_kind == kind:
                text += more
                continue
            self._feed_pane(kind, text)
            kind, text = next_kind, more
        self._feed_pane(kind, text)
        self._refresh_panel_tabs()

    def _feed_pane(self, kind: str, text: str) -> None:
        """One run of one kind, into the pane its kind belongs to (task_50)."""
        tab = panels.KIND_TAB.get(kind, panels.TAB_OUTPUT)
        if tab == panels.TAB_PROBLEMS:
            self._problems.feed(text, kind)
        elif tab == panels.TAB_SYSTEM:
            self._system.feed(text, kind)
        else:
            self._output.feed(text, kind)

    def _flush_pane_tails(self) -> None:
        """Ends the open half-line in every pane; nothing else will finish it."""
        for pane in (self._output, self._problems, self._system):
            pane.flush()
        self._refresh_panel_tabs()

    def _reset_panels(self) -> None:
        """Empties the read-only panes and the table; the input queue is user data.

        The table goes with them: it is a view of the answer of the *last* run, so
        a new run begins with an empty one — «таблица ответа», not a history of
        answers (`answers.py` keeps nothing).  A half-collected answer goes too.
        """
        self._output.reset()
        self._problems.reset()
        self._system.reset()
        self._table.set_answer(None)
        self._answer_text = None
        self._error_count = 0
        self._warning_count = 0
        self._refresh_panel_tabs()

    def _discard_output(self) -> None:
        """Drops what is queued: the panes are about to be emptied or reused."""
        self._output_timer.stop()
        self._output_pending.clear()

    def _append_note(self, text: str) -> None:
        """Appends a note of our own, coloured apart from the program's output.

        The interpreter prints without a trailing newline when a program uses
        `ВЫВОД` and no `ПС` (that is the documented behaviour: `ВЫВОД` prints,
        `ПС` starts a new line).  The pane closes the half-line first, because the
        kind changed — otherwise the note would be glued to the program's text.
        """
        self._append_output(text, panels.NOTE)

    # -- drag and drop -----------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """A dropped program opens in its own tab.  It is not run: a run is F5.

        The views and the output pane report their own drops (`fileDropped`); this
        is what catches a drop on the tab bar or anywhere else in the window.
        """
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(url.toLocalFile())
        event.acceptProposedAction()
