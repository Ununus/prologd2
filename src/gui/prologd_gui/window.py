"""Main window: panes of programs, a query line, the output and the input queue.

One program is one `Buffer` (a model, a text document and its views).  The window
owns the open documents; a `Pane` shows them in tabs, and the split editor is two
panes over the same set of documents — so the left pane can show one program while
the right shows another, and both views edit the same text.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QElapsedTimer, QPoint, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QKeySequence,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
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
    engines,
    findbar,
    formatter,
    geometry,
    graphics,
    graphicswindow,
    panels,
    paths,
    reference,
    scriptdialog,
    scripts,
    search,
    settings,
    settingsdialog,
    shortcuts,
    tokens,
)
from .buffers import Buffer
from .editor import CodeEditor, QueryLine, ZoomablePlainTextEdit
from .panes import Pane
from .session import PrologSession, read_keywords
from .settings import OUTPUT_FONT_SIZE, Settings

#: How long «Остановить» waits for the interpreter to end its query by itself
#: before the process is taken down (`stop_program`).
STOP_GRACE_MS = 500

#: The program the first tab holds: the one text that runs on **both** engines
#: (task_79 fixed it, part 111).  It is written in the intersection of the two
#: dialects, so the welcome tab answers whoever is running:
#:
#: * atoms are lower-case and *unquoted* — the old dialect has no quoted atoms at
#:   all (`студент('Вова', …)` is a parse error there), and in the ISO reading a
#:   lower-case name is an atom either way;
#: * the variables are **single** capital letters — `Имя` is a variable in the ISO
#:   reading and a string constant in the old one, while a one-letter name is a
#:   variable in both (one letter of either register is a variable by the old rule).
#:
#: The same program is quoted with its answer in `doc/gui.typ`, section 2, and the
#: promise «answers on either engine» is a check rather than a hope: the test runs it
#: on both and compares the output (`test_window.py`).
WELCOME = """% пример программы
студент(вова, корчагин).
студент(данил, ахмеров).

?студент(И, Ф).
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
        #: Which engine this window runs (task_79).  The window is a *host* of two
        #: programs — our own «Пролог-У» and the original «Пролог-Д» (task_75,
        #: task_78) — and the choice between them is `view/engine`.  Two things
        #: outrank it for one launch: `--exe`, and task_46's removed
        #: «Интерпретатор» row, still read from the file.  `engines.launch` is the
        #: one rule for all of it — `main.py` asks the same function before it lets
        #: the window open at all.
        launch = str(executable or "").strip() or self._settings.legacy_interpreter
        self._engine, self._engine_folder = engines.launch(launch, self._settings.engine)
        #: Whether the choice had to make way for the only engine this build has
        #: (part 143): a package with «Пролог-Д» alone starts it, and the window
        #: says so in the pane instead of leaving the user to guess.
        self._engine, self._engine_folder, self._engine_swapped = paths.starting_engine(
            self._engine, folder=self._engine_folder
        )
        #: A build with one engine and no names to choose writes that answer into the
        #: row (part 148) — before the first buffer exists, so nothing is coloured by
        #: the other dialect for a moment.
        self._adopt_engine_dialect()
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
        self._session.output.connect(self._on_output)
        self._session.result.connect(self._on_result)
        self._session.input_request.connect(self._on_input_request)
        self._session.failed.connect(self._on_failed)
        self._session.trace.connect(self._on_trace)
        self._session.stepped.connect(self._on_stepped)
        self._session.loaded.connect(self._on_loaded)
        self._session.formatted.connect(self._on_formatted)
        self._session.drawn.connect(self._on_drawn)
        self._session.bitmap.connect(self._on_bitmap)
        self._session.screen.connect(self._on_screen)
        self._session.flooded.connect(self._on_flooded)
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
        #: Which picture «Остановить» carries: `True` for the red octagon (a run to
        #: break), `False` for the blue stop (a base to unload), `None` before the
        #: first refresh (part 141).
        self._stop_abort: bool | None = None
        #: How many output events the run in flight has produced (task_66): the
        #: counter behind «Предел вывода», reset when a run starts.
        self._output_events = 0
        #: Has the run in flight asked for its picture yet?  The canvas a program
        #: names with `:- ХОЛСТ(Высота, Ширина).` is known only to the interpreter,
        #: and the size travels with a snapshot and with nothing else, so the first
        #: primitive of a run asks for one (ADR-035).
        self._picture_asked = False
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
        #: How «Показать в проводнике» shows a file (task_68).  A replaceable seam
        #: like `_ask_save`: a test must not open a file manager, and no platform's
        #: file manager can be asked to report whether it worked.
        self._reveal_path = paths.reveal
        self._editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        # The output panel (task_50): three read-only panes — Проблемы, Вывод,
        # Система — and the Ввод tab with the prepared answers and, under them,
        # the per-request console.  Вывод and Система are `OutputPane`s, so the
        # bounded history, the colours per kind and the tail they hold reach both
        # the same way; Проблемы is a *table* (part 88): a diagnostic arrives as
        # fields — kind, severity, message, position — and a row is what a
        # double-click can take the editor to the line of.
        self._problems = panels.ProblemsPane(
            font_family=self._settings.font_family,
            font_size=self._settings.output_font_size,
            line_limit=self._settings.output_line_limit,
        )
        self._problems.set_palette(self._settings.palette)
        # A type and a place do not need the width of a message; the message column
        # takes the rest, so these two are only a sensible starting point.
        self._problems.setColumnWidth(0, 130)
        self._problems.setColumnWidth(1, 260)
        self._problems.zoomChanged.connect(self._on_output_zoom)
        self._problems.problemActivated.connect(self._open_problem)

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
        # The goal line and the per-request console under it are *one* panel: the
        # console appears where the question is answered, without moving the panel
        # off the Вывод tab, and «Вид → Панель ввода цели» hides the two together
        # (an answer box under nothing would be a puzzle — part 92).
        self._query_panel = QWidget()
        # A plain `QWidget` has no vertical wish of its own, and the editor column has
        # room to spare: without this the strip shared that room with the editor and
        # the goal line floated in the middle of a tall empty panel — the very defect
        # the console had, which cured it with a policy of its own (task_50).
        # `Maximum` means «as tall as the line, plus the console while a question
        # waits, and not a pixel more».
        self._query_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        query_layout = QVBoxLayout(self._query_panel)
        query_layout.setContentsMargins(0, 0, 0, 0)
        query_layout.addWidget(self._query_line)
        query_layout.addWidget(self._input_console)
        self._query_panel.setVisible(self._settings.query_visible)
        editor_layout.addWidget(self._query_panel)

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
        # A right click on this bar offers «Очистить вывод» on the «Вывод» tab
        # (task_71), the way the tab bar of an editor pane offers its own command.
        self._panel_tabs.tabBar().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._panel_tabs.tabBar().customContextMenuRequested.connect(
            self._on_panel_tab_context
        )

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
        # Which engine runs decides what is offered at all (task_79), so the state
        # of the gated entries is settled before anything else can be clicked.
        self._apply_engine()
        self._sync_actions()
        self._update_details()
        self._announce_engine()

    def _announce_engine(self) -> None:
        """Says in the pane when the stored choice was not there to start (part 143).

        A one-engine package has nothing to choose: the file it carries is the one
        that runs, and the opening line of the pane is where that is written down —
        the control that would say it is not on the toolbar at all
        (`_sync_state_button`).
        """
        if not self._engine_swapped:
            return
        missing = engines.other(self._engine)
        self._append_note(
            f"--- движок: {self._engine.title} ({self._engine.file_name}); "
            f"{missing.title} ({missing.file_name}) в этой сборке нет ---\n"
        )

    # -- the engine (task_79) ----------------------------------------------
    def engine(self) -> engines.Engine:
        """The engine the next run starts (the tests and the toolbar ask)."""
        return self._engine

    def _interpreter_path(self) -> str:
        """The file the next run starts: the chosen engine, in the launch's folder.

        `--exe` names a *folder* — «here are my builds», because the two engines
        were built together — and task_46's removed «Интерпретатор» row did the
        same.  A file that is not there is reported by `_start_session`, before a
        process is asked to start, rather than being answered by another build tree.
        """
        return paths.engine_executable(self._engine, folder=self._engine_folder)

    def _engine_available(self, engine: engines.Engine) -> bool:
        """Whether `engine`'s file is where a run would look for it."""
        return pathlib.Path(
            paths.engine_executable(engine, folder=self._engine_folder)
        ).is_file()

    def _only_engine(self) -> bool:
        """True when this build has no second engine, so nothing to choose (parts 143–148).

        The test the three «one engine» rules share: the naming control hides with it,
        the names row takes the old dialect with it, and `_announce_engine` explains a
        choice that had to give way to it.
        """
        return not self._engine_available(engines.other(self._engine))

    def _adopt_engine_dialect(self) -> None:
        """Writes «PLD» into the names row when this build has nothing to choose.

        The row belongs to our own engine: the original has no modes and always reads
        names the old way (`_default_variable_mode`).  A build that carries **only**
        that engine therefore keeps a row that cannot be changed and, left as it is,
        says «ISO» while the engine reads «PLD» — a setting that lies about what
        happens is worse than one written down once (part 148).  So the first start
        of such a build stores the old dialect.

        The condition is the one that hides the two state controls: no naming modes on
        the engine *and* no second engine to switch to.  A two-engine build keeps the
        stored choice — there the row is our engine's, and switching to the original
        is a visit, not a new home.
        """
        if self._engine.has(engines.NAMING):
            return
        if not self._only_engine():
            return
        if self._settings.variable_mode != "1":
            self._settings.variable_mode = "1"

    def choose_engine(self, target: engines.Engine) -> None:
        """Runs `target`: the one door every engine change goes through.

        A row of the state control ends up here (task_93), and the order is the
        reason this is not one line.  A live child process goes on sending its
        events, and after the choice changed they would arrive as the output of a
        run that belongs to another binary — so the stop comes first.

        And it is the *session* that goes, not just the run: the process belongs to
        the engine being left, the base it holds is of no use to the other one, and
        the polite request of «Остановить» would leave it idle and alive under a
        window that now says it runs the other engine.  So it ends the way the grace
        deadline ends a run (`_stop_now`), and the pane says why.

        What the choice writes is `view/engine`, so the next window starts on the
        same engine.  The folder the engines are looked for in is not touched — a
        build tree is where both of them lie — and the value task_46's removed row
        left in the file is dropped, because otherwise it would name the engine again
        on the next start and outlive the click.  The reserved names are re-read as
        well: the two engines answer `--list-keywords` with different tables (66
        names against our 131), and completion, colouring and the cheat sheet are all
        built from them.

        Asking for the engine that already runs does nothing: the menu has three
        rows, and the one in force must not end a session when it is clicked.
        """
        if target is self._engine:
            return
        if self._session.is_running():
            self._stop_now("движок изменён")
        self._engine = target
        self._settings.engine = self._engine.key
        self._settings.clear_legacy_interpreter()
        self._session.set_executable(self._interpreter_path())
        self._session.keywords = read_keywords(self._interpreter_path())
        self._apply_keywords()
        self._apply_engine()
        self._append_note(
            f"--- движок: {self._engine.title} ({self._engine.file_name}) ---\n"
        )
        self._status.setText(f"движок: {self._engine.title}")
        self._update_details()

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
            # The action is added to the window itself as well as to the surfaces
            # that show it.  A `QAction`'s shortcut works only while the action
            # belongs to a widget, and a menu that is shown on demand — the tab menu
            # of task_68 — holds it only while it is open: `Ctrl+E` typed into the
            # editor went nowhere, while the very same entry worked when clicked.
            self.addAction(action)

    def _slot_for(self, key: str):
        """The method an action runs — one place, so nothing is wired twice."""
        return {
            "new": lambda: self.new_buffer(),
            "script_image": self.convert_image,
            # «PLD to ISO» and «ISO to PLD» (task_99): the answer is a new text, so
            # it opens in a tab of its own rather than replacing the buffer.
            "names_iso": lambda: self.convert_names(0),
            "names_pld": lambda: self.convert_names(1),
            "reveal": self._reveal_in_file_manager,
            "open_import": self._open_import_under_cursor,
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
            "query": self._toggle_query,
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
                self._format_action = self._toolbar.addWidget(self._build_format_button())
            elif key == actions.STATE:
                self._state_action = self._toolbar.addWidget(self._build_state_button())
            else:
                self._toolbar.addAction(self._actions[key])
        #: The two controls of the toolbar that stand for a *capability* of the
        #: engine, each as the pair `addWidget` returns: the action it answers with
        #: and the widget inside it.  Hiding has to go through the action (part 145) —
        #: the toolbar lays its items out on show and calls `setVisible` on the widget
        #: by the action's visibility, so a bare `widget.setVisible(False)` lives only
        #: until the window appears.  One table, one setter (`_show_toolbar_control`),
        #: so no call site can forget half of the pair.
        self._toolbar_controls: dict[str, tuple[QAction, QToolButton]] = {
            "format": (self._format_action, self._format_button),
            "state": (self._state_action, self._state_button),
        }
        self._toolbar.setVisible(self._settings.toolbar_visible)
        self.addToolBar(self._toolbar)

    def _show_toolbar_control(self, key: str, visible: bool) -> None:
        """Shows or hides a toolbar control — the action **and** the widget (part 145)."""
        action, widget = self._toolbar_controls[key]
        action.setVisible(visible)
        widget.setVisible(visible)

    def _build_state_button(self) -> QToolButton:
        """«Which program runs, and how it reads names» — the last control (task_93).

        One `QToolButton` with a menu of three states, in place of the two controls
        of task_79.  Those carried a picture of an `И` and a picture of a `Д`, so the
        reader had to know what the letters stood for — and `Д` was taken for
        «Пролог-Д 2.0», the name of the whole product, rather than for the original
        engine.  The three pictures (`engine-iso`, `engine-pld`, `engine-1.x`) are the
        words themselves, so the state is read off the toolbar without a click, and
        the menu spells each one out.

        Everything about the button follows from the state of the window
        (`_sync_state_button`).
        """
        button = QToolButton(self)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(self._build_state_menu())
        self._state_button = button
        return button

    def _build_state_menu(self) -> QMenu:
        """The three states, word for word as the dialog and the manual name them.

        The two `2.x` entries are the «Имена переменных» row, so their words are read
        from the `Setting` record itself — from the part after its own `ISO:`/`PLD:`,
        which the state label already carries — and a renamed row renames the menu with
        it.  A second copy of those words is exactly what would drift.
        """
        menu = QMenu("Движок и имена", self)
        # A menu row is read at a glance; the rest of the sentence goes to the tooltip.
        menu.setToolTipsVisible(True)
        self._state_menu = menu
        group = QActionGroup(self)
        group.setExclusive(True)
        self._state_actions: dict[str, QAction] = {}
        for state in actions.STATES:
            entry = menu.addAction(f"{state.label}: {self._state_detail(state)}")
            entry.setCheckable(True)
            entry.setActionGroup(group)
            entry.setToolTip(state.hint)
            entry.triggered.connect(
                lambda _checked=False, key=state.key: self._choose_state(key)
            )
            self._state_actions[state.key] = entry
        self._sync_state_menu()
        return menu

    def _state_detail(self, state: actions.State) -> str:
        """The words after the state label in its menu row.

        «2.x ISO: переменная с большой буквы» is assembled from the label and the
        settings row itself, so the menu says what the dialog says.
        """
        if state.key == actions.STATE_ORIGINAL:
            return "оригинальный движок"
        value = "0" if state.key == actions.STATE_ISO else "1"
        for choice, title in settings.BY_KEY[settings.VARIABLE_MODE].choices:
            if choice == value:
                return title.split(":", 1)[-1].strip() or title
        return ""

    def _current_state(self) -> str:
        """Which of the three rows is in force: the engine first, then the dialect."""
        if self._engine is engines.ORIGINAL:
            return actions.STATE_ORIGINAL
        if self._settings.variable_mode == "1":
            return actions.STATE_PLD
        return actions.STATE_ISO

    def _sync_state_button(self) -> None:
        """The picture, the tooltip and the availability of the state control.

        The control answers two questions at once, so it is hidden only when neither
        has an answer: a build whose only engine is the original has no other program
        to start and no dialects to choose (`_only_engine`, parts 143 and 148) — the
        package of «Пролог-Д» alone.  Every other build keeps the control on either
        engine: on the original the two `2.x` rows are the way back, which the old
        naming button could not offer at all.

        A row that would start an engine this build does not carry is *greyed out*
        rather than hidden: the menu is a map of three states, and a hole in it says
        less than a row that names what is missing.
        """
        other_available = self._engine_available(engines.other(self._engine))
        self._show_toolbar_control(
            "state", other_available or self._engine.has(engines.NAMING)
        )
        state = actions.STATE_BY_KEY[self._current_state()]
        found = assets.icon(state.icon)
        if found is None:
            # The picture *is* the label here, so a missing file would leave a button
            # with nothing on it: the words are the fallback, and `test_icons` is what
            # keeps the file from going missing in the first place.
            self._state_button.setIcon(QIcon())
            self._state_button.setText(state.label)
            self._state_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        else:
            self._state_button.setIcon(found)
            self._state_button.setText("")
            self._state_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._state_button.setToolTip(f"{state.hint} — нажмите, чтобы сменить")
        self._sync_state_menu()

    def _sync_state_menu(self) -> None:
        """Shows the state in force, and greys out what this build cannot start."""
        if not hasattr(self, "_state_menu"):
            return
        current = self._current_state()
        for state in actions.STATES:
            entry = self._state_actions[state.key]
            target = (
                engines.ORIGINAL if state.key == actions.STATE_ORIGINAL else engines.OURS
            )
            entry.setEnabled(target is self._engine or self._engine_available(target))
            entry.blockSignals(True)
            entry.setChecked(state.key == current)
            entry.blockSignals(False)

    def _choose_state(self, key: str) -> None:
        """A row of the menu: the light answer and the heavy one, told apart.

        `2.x ISO` and `2.x PLD` differ only in the dialect — a stored value and the
        colouring of the open buffers — so on our own engine they cost nothing and a
        live session is left alone.  `1.x`, and either `2.x` row while the original
        runs, changes *which program* answers: that is `choose_engine`, and it stops
        the session first.  Choosing `1.x` leaves the stored dialect untouched, so
        coming back to `2.x` restores the one the user picked last.
        """
        if key == actions.STATE_ORIGINAL:
            self.choose_engine(engines.ORIGINAL)
            return
        self.choose_engine(engines.OURS)
        self._set_variable_mode("0" if key == actions.STATE_ISO else "1")

    def _apply_engine(self) -> None:
        """Everything that follows from *which* engine runs (task_79).

        The window is a host of two programs that are not interchangeable, and the
        protocol number cannot tell them apart: the original answers `13` as well,
        and its own sources call that a sub-set of our 13.  So what a command needs
        of the engine is written once, in the tables — `actions.Action.needs` for a
        menu or toolbar entry, `settings.GATED_ROWS` for a row of the dialog — and
        this is the one place that asks.  An entry the engine cannot answer is
        *disabled*, with the reason in its tooltip; and the format mode control
        beside «Форматировать» goes with the command it belongs to.
        """
        for spec in actions.ACTIONS:
            if not spec.implemented or not spec.needs:
                continue
            action = self._actions[spec.key]
            allowed = self._engine.has(spec.needs)
            action.setEnabled(allowed)
            hint = spec.tooltip()
            if not allowed:
                hint = f"{hint} — {self._engine.title} этого не умеет"
            action.setToolTip(hint)
            action.setStatusTip(hint)
        # The two controls that stand for a *capability* of the engine go with it.  The
        # format mode control is *hidden*: it belongs to a command that does not exist
        # on that engine (a hidden widget takes no room, so no hole is left), and the
        # command itself is greyed out beside it.  The state control stays **visible**
        # on the original — two of its three rows are the way back to our own engine —
        # and a row it cannot offer is greyed out instead (`_sync_state_menu`).
        formats = self._engine.has(engines.FORMAT)
        self._show_toolbar_control("format", formats)
        self._sync_state_button()
        # `run`, `stop`, the two steps and the traced run are computed with the
        # state of the session as well, and that formula lives in one place.
        self._sync_run_actions()

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

    def _set_variable_mode(self, mode: str) -> None:
        """The state control writes the row's own key, and the open buffers follow.

        One key, one write: the dialog reads the same `execution/variable_mode`, and
        the fallback of every buffer that declares no dialect is handed out again
        (`_apply_dialect`) — a mode chosen here is in force as soon as it is clicked.
        The control itself follows too: it wears the picture of the dialect in force
        (`_sync_state_button`).
        """
        self._settings.variable_mode = mode
        self._sync_state_button()
        self._apply_dialect()
        self._status.setText(f"имена переменных: {self._naming_label()}")

    def _naming_label(self) -> str:
        """The mode in force as the row names it: its label up to the colon.

        «ISO: переменная с большой буквы» is read as `ISO` — the two dialects have
        short names, and they are the row's own words; a label that grows no colon is
        used whole, so a renamed row cannot make this empty.
        """
        for value, entry_title in settings.BY_KEY[settings.VARIABLE_MODE].choices:
            if value == self._settings.variable_mode:
                return entry_title.split(":", 1)[0].strip() or entry_title
        return self._settings.variable_mode

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
                elif key == actions.NAMES_SUBMENU:
                    submenu = menu.addMenu(actions.NAMES_MENU_TITLE)
                    submenu.setToolTipsVisible(True)
                    for name in actions.NAMES_CONVERSIONS:
                        submenu.addAction(self._actions[name])
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
        """Three states for «Остановить», two for «Запустить».

        `Запустить` is for a computation that is not in flight — it restarts the
        whole file, whether the interpreter is idle with a base loaded or gone
        altogether.

        `Остановить` is the command with two meanings, and the button says which one
        it will do (part 141, after task_87's two-state button): dark while there is
        nothing to stop; red — `execution-abort` — while a run is in flight, because
        then the click breaks a computation; blue — `execution-stop` — while the
        interpreter is up and idle with its base, because then the click unloads the
        base, which is the one act that is immediate.  A red button over an idle
        session read as «the program is looping», and a dark one took away the only
        way to unload a base that is waiting for input.

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
        # «Остановить» has three states (part 141, after task_87's two): dark while
        # there is nothing to stop; the red octagon while a run is in flight, because
        # then the click breaks a computation; and the blue stop while the interpreter
        # is up and idle with its base, because then the click only unloads the base.
        # One picture for both acts was what made the red one misleading: over an
        # idle session it read as «the program is looping».
        in_flight = self._busy or self._session.paused()
        stop = self._actions["stop"]
        enabled = self._session.is_running() and (in_flight or self._loaded)
        stop.setEnabled(enabled)
        # Blue only where it will really unload: a disabled button, and a run to
        # break, both keep the red octagon.
        self._stop_picture(in_flight or not enabled)
        # A step and a traced run need a second thing beyond a program that may be
        # started: an engine that answers the request (task_79).  «Запустить» above
        # is deliberately not gated — running a program is what both engines do.
        # The list is read from the table, so the reason a key is here and the
        # reason `_apply_engine` greys the entry out are one fact, not two.
        for key in ("run_trace", "step", "step_over"):
            self._actions[key].setEnabled(
                free and self._engine.has(actions.BY_KEY[key].needs)
            )

    def _refresh_navigation_actions(self) -> None:
        """Offers `F12` only where it does something: on the `ИМПОРТ` line of the caret.

        Called from `_update_details`, which every caret move and every tab switch
        reaches (task_69): an enabled state that is recomputed somewhere else is a
        state that goes stale.
        """
        action = getattr(self, "_actions", {}).get("open_import")
        if action is not None:
            action.setEnabled(self._import_under_cursor() is not None)

    def _stop_picture(self, in_flight: bool) -> None:
        """Puts the picture of the moment on «Остановить» (part 141).

        Red is a computation to break, blue is a base to unload — the same command,
        two very different acts.  Set only when the state changes: a refresh runs on
        every caret move, and repainting the toolbar there would be pure noise.
        """
        if self._stop_abort == in_flight:
            return
        self._stop_abort = in_flight
        action = self._actions["stop"]
        picture = assets.icon("execution-abort" if in_flight else "execution-stop")
        if picture is not None:
            action.setIcon(picture)
        hint = (
            "Остановить (Shift+F5): прервать прогон"
            if in_flight
            else "Остановить (Shift+F5): выгрузить базу знаний"
        )
        action.setToolTip(hint)
        action.setStatusTip(hint)

    def _update_details(self) -> None:
        """The right-hand side of the status bar: state, caret, file shape."""
        self._refresh_navigation_actions()
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
        # Which engine the next run starts, and — when the build was named by hand
        # (task_79: `--exe`, or task_46's «Интерпретатор» row that is still read
        # from the file) — the file itself.  A window that runs another build than
        # the one beside it has to say so, and which of the two *engines* it is
        # matters even more: the same click means different things under them.
        parts.append(f"движок: {self._engine.title}")
        if self._engine_folder:
            parts.append(self._interpreter_path())
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

    def _set_checked(self, key: str, checked: bool) -> None:
        """Sets a checkable entry *without* running the handler behind it.

        A handler writes the preference it belongs to, and `_sync_actions` is not
        the user: letting the signal through is how showing the output panel for a
        run overwrote the fact that the user had hidden it (part 92).  The entry
        still shows the state — that is the whole point of syncing it.
        """
        action = self._actions[key]
        blocked = action.blockSignals(True)
        action.setChecked(bool(checked))
        action.blockSignals(blocked)

    def _sync_actions(self) -> None:
        """Makes the checkable entries agree with the settings and the panes.

        Reading a widget's state back into the entry that would *write* it is what
        `_set_checked` is for: the entries follow, the preferences do not move.
        """
        # `isHidden`, not `isVisible`: a toolbar of a window that was never shown
        # is not visible either, and reading that as "the user hid it" would write
        # the wrong preference on the first start.
        self._set_checked("toolbar", not self._toolbar.isHidden())
        self._set_checked("line_numbers", self._settings.line_numbers)
        self._set_checked("wrap", self._settings.wrap)
        self._set_checked("save_before_run", self._settings.save_before_run)
        self._set_checked("run_questions", self._settings.run_questions)
        self._set_checked("print_questions", self._settings.print_questions)
        self._set_checked("answer_table", self._settings.answer_table)
        self._set_checked("full_screen", self.isFullScreen())
        self._set_checked("output", self.output_visible())
        self._set_checked("query", self.query_visible())
        self._set_checked("graphics", self._settings.graphics_visible)
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
        file and the command that builds it.  In a package (task_61) `doc/` is a
        folder beside the window, and that command is not something anyone there
        could run.
        """
        pdf = paths.document(name)
        if pdf.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
            return
        if paths.frozen():
            QMessageBox.information(
                self,
                "PrologD",
                f"Файл {pdf} не найден.\n\n"
                "Похоже, сборка неполная: папка doc должна лежать рядом с окном.",
            )
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
        pane.tabContextRequested.connect(
            lambda index, point, pane=pane: self._on_tab_context_requested(pane, index, point)
        )
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

    def query_visible(self) -> bool:
        """Whether the goal field is shown (`isHidden`, for the same reason)."""
        return not self._query_panel.isHidden()

    def _reveal_output_panel(self) -> None:
        """Shows the output panel for a run — without writing the preference.

        «Скрыта» is a temporary state the user chose, and a run has output to show,
        so the panel comes back for it (part 92).  The *key* is left alone: the
        first run would otherwise erase the choice for ever — the rule the
        followed font size already follows (task_58), where a side effect of
        running writes nothing and only the user's own act does.
        """
        if self._panel_tabs.isHidden():
            self._panel_tabs.setVisible(True)
            self._sync_actions()

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

    def _toggle_query(self, visible: bool) -> None:
        """«Вид → Панель ввода цели»: show or hide the goal field."""
        self._settings.query_visible = bool(visible)
        self._query_panel.setVisible(bool(visible))
        self._status.setText(
            "панель ввода цели показана" if visible else "панель ввода цели скрыта"
        )

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
        seed or redirected files left from the previous run) and an empty
        output pane.  Reusing the session accumulates clauses —
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
        # a diagnostic switches it to «Проблемы» later.  A run has output to show,
        # so a panel the user hid comes back for it — and only for it: the key is
        # not written, so the choice survives (part 92).
        self._reveal_output_panel()
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
        limits = self._engine_limits()
        note = self._limits_note()
        if note:
            self._append_note(note)
        self._output_events = 0
        self._picture_asked = False
        self._arm_timeout()
        # A canvas that is already there follows the setting too (task_73): the
        # engine draws on the new screen, and the window must not keep clipping the
        # picture at the old one.  Only on a change — a resize clears the picture.
        if self._canvas is not None and (
            (self._canvas.width, self._canvas.height) != self._settings.screen_size
        ):
            self._canvas.reset(*self._settings.screen_size)
            if self._graphics_window is not None:
                self._graphics_window.refresh()
        # A canvas that is already there follows the setting too (task_73): the
        # engine will draw on the new screen, and the window must not keep clipping
        # the picture at the old one.  Only on a change — resizing clears it.
        if self._canvas is not None and (
            (self._canvas.width, self._canvas.height) != self._settings.screen_size
        ):
            self._canvas.reset(*self._settings.screen_size)
        if path is not None and not buffer.is_modified():
            # A saved, unmodified buffer is loaded by path: `ИМПОРТ` resolves
            # against the file's own directory and diagnostics name the file.
            self._session.load_file(path, step=step, trace=trace, questions=questions,
                                    print_questions=self._settings.print_questions,
                                    limits=limits,
                                    screen=self._settings.screen_size,
                                    variable_mode=buffer.variable_mode())
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
                                    limits=limits,
                                    screen=self._settings.screen_size,
                                    variable_mode=buffer.variable_mode())
            name = pathlib.Path(path).name if path else buffer.title()
            self._status.setText(f"выполняется {name} (есть несохранённые правки)")
        return True

    # -- the graphics window (task_45) -------------------------------------
    def canvas(self) -> graphics.Canvas:
        """The picture, created on first use — the size of the screen of the run."""
        if self._canvas is None:
            # The engine draws on the screen the settings name (task_73), and this
            # canvas is that same screen: a canvas of another size would clip the
            # picture where the engine did not.
            self._canvas = graphics.Canvas(*self._settings.screen_size)
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
            self._ask_for_picture()
        else:
            window.hide()
        self._settings.graphics_visible = visible
        self._settings.graphics_geometry = window.geometry_text()
        self._actions["graphics"].setChecked(visible)
        self._status.setText(
            "графическое окно показано" if visible else "графическое окно скрыто"
        )

    def _count_output(self) -> None:
        """One output event of the run; stops it past «Предел вывода» (task_66).

        The cap counts what the front-end receives — a line of the program's text,
        a drawing primitive, a trace line — and it is the same escalation as the
        «Предел времени»: the request first, the process after the grace.  It is
        the window's guard, not the engine's, which is why it also ends a program
        that floods output — exactly the one the request never reaches (task_64).
        """
        limit = self._settings.max_output_events
        if limit <= 0 or self._stopping:
            return
        self._output_events += 1
        if self._output_events > limit:
            self._append_note(f"--- предел вывода: {limit} событий, остановлено ---\n")
            self._status.setText(f"остановлено по пределу вывода ({limit})")
            self._stopping = True
            self._session.interrupt()
            self._stop_grace.start(STOP_GRACE_MS)

    def _on_output(self, text: str) -> None:
        """One line of the program's output: counted, then shown (task_66).

        While a stop is in flight the pane is *not* fed: the text keeps coming,
        and feeding it would keep the event loop busy — the one thing the
        «Остановить» deadline needs, in a visible window whose panes are being
        repainted, to fire at all.  The counter keeps running until the cap trips,
        but once the user — or a limit — asked for a stop, there is nothing left
        to show.
        """
        self._count_output()
        if not self._stopping:
            self._append_output(text)

    def _on_flooded(self, count: int) -> None:
        """A program writes faster than the pane can show: say so once (task_65).

        Nothing is dropped — the text and the picture stay complete, only later —
        so the line is a *note*, not an error: it explains why the window lags
        behind a program that prints or draws in a tight loop, and why
        «Остановить» may take a moment to be served.
        """
        if self._stopping:
            return
        self._append_note(
            f"--- программа выводит быстрее, чем окно успевает: {count} событий в секунду ---\n"
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
        if self._stopping:
            return
        self._count_output()
        if not self._graphics_shown:
            self._graphics_shown = True
            if self._graphics_window is None or not self._graphics_window.isVisible():
                self.show_graphics_window(True)
        if self._canvas is None:
            return  # the snapshot is on its way; the next primitive draws
        # The first primitive of a run is the first moment there is something the
        # window may have missed; `_ask_for_picture` says the rest.
        self._ask_for_picture()
        self._canvas.draw(event)
        if self._graphics_window is not None:
            self._graphics_window.refresh()

    def _picture_may_be_asked(self) -> bool:
        """May the picture be asked for right now?

        Only when the interpreter is running and is not waiting for an answer: while
        an `input_request` or a step point is pending, the session takes one answer
        and nothing else, so a snapshot request would be refused as «ожидался ответ
        input, получено: graphics».  The engine tolerates one now (protocol 14), but
        a window has no reason to send what it knows is out of turn (ADR-035).
        """
        return (
            self._session.is_running()
            and not self._session.awaiting_input()
            and not self._session.paused()
        )

    def _ask_for_picture(self) -> None:
        """Asks for the pixels drawn so far — once per run, and only in turn.

        This is not about the *size* of the canvas: a program's own
        `:- ХОЛСТ(Высота, Ширина).` reaches the window as a `screen` event of its own.
        It is about the picture a window missed — one that was not open yet, or was
        closed while the program drew.  Asked once per run because every ask costs a
        whole bitmap on the wire, and a second answer would say the same thing.
        """
        if self._picture_asked or self._canvas is None:
            return
        if not self._picture_may_be_asked():
            return
        self._picture_asked = True
        self._session.request_graphics_snapshot()

    def _on_screen(self, width: int, height: int) -> None:
        """The program named its own canvas (protocol 14, ADR-035).

        `:- ХОЛСТ(Высота, Ширина).` is applied while the program loads, so this
        arrives *before* the first primitive: the window's canvas takes the size
        the program asks for and the animation is laid out right from the first
        frame, instead of being a corner of a bigger sheet until a snapshot comes.
        A size outside the limits is refused by the engine, which reports it.
        """
        if width <= 0 or height <= 0:
            return
        self.canvas().reset(width, height)
        if self._graphics_window is not None:
            self._graphics_window.refresh()

    def _on_bitmap(self, width: int, height: int, data: bytes) -> None:
        """The whole screen arrived: what a window opened mid-run starts from.

        It is also how a program's own canvas size reaches the window — the size
        travels with the picture, so a run whose `screen` event was missed still
        ends with the canvas the program named (ADR-035).
        """
        self._picture_asked = True
        self.canvas().apply_bitmap(width, height, data)
        if self._graphics_window is not None:
            self._graphics_window.refresh()
        self._status.setText(f"рисунок получен ({width}×{height})")

    def _engine_limits(self) -> dict | None:
        """The `limits` object of a `load`, for the engine that reads it (task_79).

        The original engine knows no caps at all — the object is ours (protocol 9)
        — so under it a request would only be a line the engine skips.  The
        window's own two guards are not here: the clock and the event counter are
        kept in this process, and they work under both engines.
        """
        return self._settings.limits() if self._engine.has(engines.LIMITS) else None

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

        Three of the five rows are the *engine's* (task_79), and the original does
        not read them: promising them there would be a promise nobody keeps.  A row
        the user did raise is still said out loud, in a line of its own — under
        Пролог-Д it is a row that does nothing, and that is exactly the kind of
        thing the note exists to make findable.
        """
        engine_rows = (
            (self._settings.max_steps, settings.DEFAULT_MAX_STEPS, "«Предел шагов»"),
            (self._settings.max_depth, settings.DEFAULT_MAX_DEPTH, "«Предел глубины»"),
            (self._settings.max_findall, settings.DEFAULT_MAX_FINDALL,
             "«Предел решений НАЙТИВСЕ»"),
        )
        window_rows = (
            (self._settings.timeout_milliseconds, settings.DEFAULT_TIMEOUT_MILLISECONDS,
             "«Предел времени, мс»"),
            (self._settings.max_output_events, settings.DEFAULT_MAX_OUTPUT_EVENTS,
             "«Предел вывода»"),
        )
        named: list[str] = []
        unread: list[str] = []
        for rows, into in (
            (engine_rows, named if self._engine.has(engines.LIMITS) else unread),
            (window_rows, named),
        ):
            for value, default, label in rows:
                if value == default:
                    continue
                into.append(f"{label} {value}" if value else f"{label} — без предела")
        lines = []
        if named:
            lines.append("--- пределы: " + ", ".join(named) +
                         " — строки в «Выполнении» настроек ---\n")
        if unread:
            lines.append(f"--- {self._engine.title} их не читает: " + ", ".join(unread) +
                         " — эти строки действуют только на Пролог-У ---\n")
        return "".join(lines)

    def _arm_timeout(self) -> None:
        """Starts the «Предел времени» clock of a run, if one is set (task_46).

        The deadline is a `QTimer` and the answer is `interrupt` — the same polite
        stop the button uses, so an interpreter that is *waiting* (for input, or at
        a step point) ends the query where it stands instead of the window killing a
        process mid-write.  What the request cannot reach is a query that is
        *solving*: the session reads its next request only between two requests, so
        a runaway reads the interrupt when the query it was meant for is over
        (task_64).  That is why the polite request is followed by the deadline
        `_on_timeout` arms below — the same `STOP_GRACE_MS` «Остановить» waits.
        """
        self._timeout.stop()
        milliseconds = self._settings.timeout_milliseconds
        if milliseconds > 0:
            self._timeout.start(milliseconds)

    def _on_timeout(self) -> None:
        """The run outlived its deadline: ask the interpreter to stop, then take it.

        The request alone is not enough: a program that is solving never looks at
        its input stream, so the run would outlive the very limit that was meant to
        end it (found by using the window, task_64).  The deadline of «Остановить»
        follows the note, and after it the process goes — the base is lost, which is
        what a run nobody can interrupt costs.
        """
        if not self._busy:
            return
        milliseconds = self._settings.timeout_milliseconds
        self._append_note(f"--- предел времени: {milliseconds} мс, остановлено ---\n")
        self._status.setText(f"остановлено по времени (предел {milliseconds} мс)")
        self._session.interrupt()
        self._stopping = True
        self._stop_grace.start(STOP_GRACE_MS)

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
            "kind": "format",
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
            variable_mode=self._variable_mode(),
        )

    def _show_converted(self, text: str, target: int) -> None:
        """A converted program in a tab of its own (task_99)."""
        self.new_buffer()
        self.editor().setPlainText(text)
        mode = "ISO" if target == 0 else "PLD"
        lines = len(text.splitlines())
        self._status.setText(f"имена переведены в режим {mode}: {lines} строк в новом табе")

    def convert_names(self, target: int) -> bool:
        """«Скрипты → Сконвертировать исходник → …» (task_99).

        The conversion is the formatter's own token pass, so the request is the one
        «Форматировать» sends with the *target* naming mode added — the buffer is
        read in its own mode (`_variable_mode()`), and the answer is the same program
        spelled the other way, marker line and all.  It opens in a new unnamed tab:
        a conversion produces a new text, and the tab in front of the user stays as
        it was written.

        `target` is the mode to print: 0 is ISO, 1 the old dialect.
        """
        view = self.active_pane().current_view()
        if view is None or self._format_pending is not None:
            return False
        text = view.toPlainText()
        if not text.strip():
            self._status.setText("конвертировать нечего: таб пуст")
            return False
        # `soft` whatever the «Форматировать» control says: a converted program is
        # read afterwards, and a one-line answer («в одну строку») is not.
        self._format_pending = {
            "kind": "names",
            "target": target,
            "view": view,
            "old": text,
            "region": None,
        }
        if not self._session.is_running():
            if not self._start_session():
                self._format_pending = None
                return False
        self._status.setText("перевожу имена…")
        self._session.format_text(
            text,
            mode="soft",
            width=self._settings.format_width,
            indent=self._settings.format_indent,
            unit=self._settings.format_unit,
            name="<buffer>",
            variable_mode=self._variable_mode(),
            names=target,
        )
        return True

    def _on_formatted(self, text: str, changed: bool) -> None:
        """Puts the laid-out text back — or says why it was not put back."""
        pending = self._format_pending
        self._format_pending = None
        if pending is None:
            return
        if pending.get("kind") == "names":
            # A conversion is a new text, not a rewrite: it opens in a tab of its
            # own and the buffer keeps what its author wrote (task_99).
            self._show_converted(text, pending["target"])
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

    def _default_variable_mode(self) -> int:
        """How a file that says nothing about names is read by the engine that runs.

        The row («Имена переменных») is the answer for our own engine.  The original
        has no modes at all — no `variables` field, no idea that an ISO reading
        exists — it reads one-letter variables and unquoted string constants because
        that *is* the old dialect.  So under it a marker-less file is coloured,
        completed and sent as the old one: otherwise the window would call a name a
        variable that the engine prints as a string constant, and the row is
        disabled in the dialog for exactly this reason (`GATED_ROWS`).

        A file that declares `:- ИМЕНА(N).` in its first line keeps its own mode
        either way: the dialect belongs to the file (task_67), even where the engine
        running it would not read the marker.
        """
        if not self._engine.has(engines.NAMING):
            return tokens.MODE_OLD
        return self._settings.variable_mode_number

    def _apply_dialect(self) -> None:
        """Gives every open buffer the mode a file that declares none is read in.

        Two things move that answer: the «Имена переменных» row (the dialog's
        «Применить») and the engine (task_79).  One door for both, because a buffer
        that kept the old answer would colour one dialect while the engine reads
        another.
        """
        mode = self._default_variable_mode()
        for buffer in self._buffers:
            buffer.set_fallback_variable_mode(mode)

    def _variable_mode(self) -> int:
        """How the program in front of the user reads names (task_67).

        The file's own `:- ИМЕНА(N).` first line, else the window's answer for a file
        that says nothing — the row, or the old dialect under an engine that has no
        other one (`_default_variable_mode`).  This is the same answer the
        highlighter is given.  A run and a formatting request carry it, and so does a
        question of its own: a statement typed into the goal line or clicked on a
        margin marker arrives *without* the file's first line, so the interpreter
        cannot read a mode out of it, and without this a question about a mode-1
        program would read its constants as variables.
        """
        buffer = self.current_buffer()
        if buffer is not None:
            return buffer.variable_mode()
        return self._default_variable_mode()

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
        # A goal typed into the line answers into the output panel: asking it with
        # that panel hidden would look like nothing happened at all (part 92).
        self._reveal_output_panel()
        self._session.run_query(text, variable_mode=self._variable_mode(),
                                screen=self._settings.screen_size)
        self._sync_run_actions()
        self._update_details()

    def _on_panel_tab_context(self, point: QPoint) -> None:
        """Shows the panel's tab menu — nothing where there is no command (task_71)."""
        index = self._panel_tabs.tabBar().tabAt(point)
        if index < 0:
            return
        menu = self._prepare_panel_tab_menu(index)
        if menu is None:
            return
        menu.exec(self._panel_tabs.tabBar().mapToGlobal(point))

    def _prepare_panel_tab_menu(self, index: int) -> QMenu | None:
        """The menu of the output panel's tab bar, or `None` — showing it is the caller's.

        The titles of these tabs carry a counter (`Вывод:5`), so a tab is told apart
        by the pane it shows and not by its text.  The entries are the shared
        `QAction`s of the action table, the same objects the menu bar hands out, so
        «Очистить вывод» here and `Ctrl+L` elsewhere are one command.  The tab is
        not made current the way the editor's menu does it: that command acts on the
        Вывод pane whether or not it is in front, and switching tabs under a right
        click would move the reader for nothing.  Built in a method of its own so a
        headless test can look at the menu without opening it.
        """
        if self._panel_tabs.widget(index) is not self._output:
            return None
        menu = QMenu(self)
        for key in actions.PANEL_TAB_CONTEXT:
            menu.addAction(self._actions[key])
        return menu

    def _on_tab_context_requested(self, pane: Pane, index: int, point) -> None:
        """Shows a tab's context menu (task_68)."""
        self._prepare_tab_menu(pane, index).exec(point)

    def _prepare_tab_menu(self, pane: Pane, index: int) -> QMenu:
        """Selects the pointed-at tab and builds its menu — showing it is the caller's.

        Made current first: a right click does *not* switch tabs in Qt, and the menu
        commands act on the tab in front — «Показать в проводнике» has to act on the
        tab the user pointed at.  The entries are the shared `QAction`s of the action
        table, so a title, an icon or an enabled state cannot exist twice.  Built in
        a method of its own so a headless test can look at the menu without opening
        it: `exec` waits for a click that no test can make.
        """
        self._on_pane_activated(pane)
        pane.setCurrentIndex(index)
        buffer = pane.current_buffer()
        self._actions["reveal"].setEnabled(
            buffer is not None and bool(buffer.model.path)
        )
        menu = QMenu(self)
        for key in actions.TAB_CONTEXT:
            menu.addAction(self._actions[key])
        return menu

    def _import_under_cursor(self) -> str | None:
        """The file named by the `ИМПОРТ` line under the caret, if that is the line.

        The line is read with the editor's own tokenizer, so it may be written any way
        the language allows — `:- ИМПОРТ("lib/x.pld").` and `:- import("x.pld").`
        both do.  When one line names several files, the string the caret sits in wins.
        """
        pane = self.active_pane() if self._panes else None
        view = pane.current_view() if pane is not None else None
        if view is None:
            return None
        cursor = view.textCursor()
        directive = False
        names: list[tuple[int, str]] = []
        for token in tokens.tokenize(cursor.block().text(), self._session.keywords):
            if token.kind == tokens.DIRECTIVE or (
                token.kind == tokens.KEYWORD and token.text in ("ИМПОРТ", "import")
            ):
                directive = True
            elif directive and token.kind == tokens.STRING:
                # The tokenizer hands a literal over as it was written — quotes and
                # all — while the lexer's `text` is decoded (task_69).
                names.append((token.start, tokens.literal_text(token.text)))
        if not directive or not names:
            return None
        for start, name in names:
            if start <= cursor.positionInBlock() <= start + len(name):
                return name
        return names[0][1]

    def _open_import_under_cursor(self) -> None:
        """Opens the file the `ИМПОРТ` line under the caret names (task_69).

        Resolved the way the interpreter resolves it — `paths.resolve_import` — so
        the tab that opens is the file the run would load.  A name that is nowhere to
        be found says so in «Системе»: silence would look like a broken key.
        """
        name = self._import_under_cursor()
        if name is None:
            return
        buffer = self.current_buffer()
        source_dir = (
            pathlib.Path(buffer.model.path).parent
            if buffer is not None and buffer.model.path
            else None
        )
        found = paths.resolve_import(
            name,
            source_dir=source_dir,
            directories=self._import_directories(),
            interpreter_path=self._interpreter_path(),
        )
        if found is None:
            self._append_note(f"ИМПОРТ: не найдено {name}")
            return
        if not self.open_path(found):
            self._append_note(f"ИМПОРТ: не удалось открыть {found}")

    def _reveal_in_file_manager(self) -> None:
        """Shows the file of the current tab where it lives (task_68).

        An unnamed buffer has no file to show, and the menu entry is disabled for
        it; a file that was never saved cannot be revealed at all.
        """
        buffer = self.current_buffer()
        path = buffer.model.path if buffer is not None else None
        if path:
            self._reveal_path(path)

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
        self._session.run_query(statement, variable_mode=self._variable_mode(),
                                screen=self._settings.screen_size)

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

    def convert_image(self) -> bool:
        """«Скрипты → Сконвертировать картинку…» (ADR-036).

        The dialog collects the converter's arguments (`scriptdialog`), the tool runs
        in this very interpreter (`scripts`), and the facts it prints land in a new
        unnamed tab — the user decides whether they are worth a file.  The tab is
        text, not a run: nothing is loaded into the interpreter, so a conversion
        cannot disturb a session.

        Returns False when the dialog was cancelled or the tool refused; the reason
        is said in a box, because a silent no-op after «ОК» reads as a broken menu.
        """
        dialog = scriptdialog.ImageToPldDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        try:
            text = scripts.run(dialog.arguments())
        except scripts.ScriptError as error:
            QMessageBox.warning(self, "Сконвертировать картинку", str(error))
            return False
        buffer = self.new_buffer()
        self.editor().setPlainText(text)
        self._status.setText(
            f"картинка {dialog.name()}: {len(text.splitlines())} строк в новом табе"
        )
        return True

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
        *it* unloads the base, and that is the one case that is immediate.  The
        two-state button no longer reaches this branch (task_87 — it is dark while
        no run is in flight, and the next start loads the base again); the command
        keeps it for a caller that does want to unload.
        """
        if not self._session.is_running():
            self._status.setText("интерпретатор уже остановлен")
            return
        unloading = self._loaded and not self._busy and not self._session.paused()
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
        self._problems.clear_problems()
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
        # them here, and a buffer created before it is served by `_on_ready`.  The
        # dialect of a file that declares none is the engine's answer too (task_79).
        buffer.set_keywords(self._session.keywords)
        buffer.set_fallback_variable_mode(self._default_variable_mode())
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
        under the goal line — the field takes the answer and the box is what is
        left when either that panel or the goal field itself is hidden (part 92) —
        or in a box every time.
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
        if (
            not self._panel_tabs.isHidden()
            and not self._query_panel.isHidden()
            and self._settings.input_mode == "panel"
        ):
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

    def query_panel(self) -> QWidget:
        """The goal field and the console under it — one panel (part 92)."""
        return self._query_panel

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
        return self._problems.text()

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
        """A record as the dock shows it: the title, the section, the modes.

        The section line is added only when the record names one.  The records of
        the *original* engine's repository (`doc/builtins.json` of `Ununus/prologd`,
        the reference a package of that engine ships) carry no `section` and no
        `aliases` — that file serves the window, not a manual — and indexing the key
        raised inside the slot, so `F1` in the 1.27 package did nothing at all
        (part 146).
        """
        lines = [reference.record_title(record)]
        section = record.get("section")
        if isinstance(section, str) and section:
            lines.append(f"раздел руководства: {section}")
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
    def _apply_keywords(self) -> None:
        """Hands the reserved names to everything that colours or completes.

        One door for the two places they change: the engine that answered `ready`
        (task_50), and the switch of task_79, where the same window starts talking
        to another engine — whose table is not the same one (66 names against our
        131), so colouring, completion and the cheat sheet have to be rebuilt.

        The dialect a marker-less file is read in travels with them: it is the
        engine's, not the row's, and it changes at the same moment.
        """
        for buffer in self._buffers:
            buffer.set_keywords(self._session.keywords)
        self._apply_dialect()
        # The goal field offers the same names (task_50).
        self._query_line.set_completion_keywords(self._session.keywords)

    def _on_ready(self, version: str) -> None:
        # The reserved names reach every open buffer, including the ones opened
        # before the interpreter announced itself; those created later are served
        # by `_add_buffer`.
        self._version = version
        self._exit_code = None
        self._warning_count = 0
        for buffer in self._buffers:
            buffer.set_reference(self._reference)
        self._apply_keywords()
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
        dialog = settingsdialog.SettingsDialog(
            self._settings,
            self,
            self._engine,
            # The choosers of the dialog open where the engine is (task_80) — and the
            # window is the one that knows *which* engine, folders and all.
            engine_directory=str(pathlib.Path(self._interpreter_path()).parent),
        )
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
            # How this file's names are read (task_67): its own first line, else the
            # row that just changed.
            buffer.refresh_variable_mode()
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
        self._query_panel.setVisible(self._settings.query_visible)
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
        # The engine too (task_79): the button, the format mode control and the
        # entries a disabled engine cannot answer are states like the checkable
        # ones, and a settings file edited by hand may name another engine.
        self._apply_engine()
        # «Имена переменных» is a *fallback* (task_67), so the rows of this dialog
        # reach the buffers directly — the engine's answer included (task_79).
        self._apply_dialect()
        self._status.setText("настройки применены")

        # Where the child process starts is a row of this dialog (task_46), and a
        # changed value cannot reach a live process — the working directory is
        # fixed when it comes up — so a live session is restarted.  Which *engine*
        # runs is no longer a row here: that is the button on the toolbar
        # (task_79), and it needs no restart because it stops the session first.
        directory = self._process_working_directory()
        if directory != self._session.working_directory():
            live = self._session.is_running()
            self._session.set_working_directory(directory)
            if live:
                self._session.start()
                self._status.setText(
                    "настройки применены; рабочий каталог изменён — сессия перезапущена"
                )
        self._update_details()

    def _import_directories(self) -> list[str]:
        """The `-I` directories of the next session (task_61 put the rule in `paths`).

        «Дополнительные каталоги ИМПОРТ» is a *search* list for `ИМПОРТ`, not the
        working directory of the process, and it is passed exactly like
        `--include`: the engine tries the importing file's own folder first, so a
        local `lib/x.pld` still wins over a same-named file in a shared one
        (task_46 folded the single «Рабочая папка» row into this list).  Only what
        the user put in the list is passed — a package's own `examples/lib` is *not*
        added (2026-10-03): lesson 11 asks the student to add that folder by hand, so
        the row they see is the whole truth, and a folder copied to another machine
        cannot leave a remembered path behind.
        """
        return paths.import_directories(
            [*self._command_line_includes, *self._settings.import_paths]
        )

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
        # The run is over and the session is idle: whatever the window missed while
        # it was closed is still in the interpreter.
        self._ask_for_picture()
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
        """A diagnostic: a row of «Проблемы», and the line marked in the editor.

        The position arrives in fields of its own (protocol 3), so nothing is
        parsed out of the message — the message is what the interpreter wrote, and
        the file and the line are put in front of it in the row (part 88).  A
        *warning* is amber in the table and counted in the status bar; it never ends
        the run, which is why the rest of this handler only runs for an error.
        """
        where = position.where() if position is not None else ""
        if kind == "format":
            # The format request failed and the buffer was left exactly as it was.
            # The line is marked when the diagnostic is about the whole buffer; a
            # selection is a fragment, and its line numbers are not the buffer's.
            pending = self._format_pending
            self._format_pending = None
            converting = pending is not None and pending.get("kind") == "names"
            if (
                position is not None
                and pending is not None
                and pending.get("region") is None
                and self._buffer_of_view(pending["view"]) is self.current_buffer()
            ):
                self._mark_error_line(position)
            what = "конвертация" if converting else "форматирование"
            self._status.setText(f"{what}: не удалось разобрать — {message}")
            return
        if self._stopping and self._session.is_running() and severity != "warning":
            # This is the error of the query *we* stopped: the run is over — the
            # note of the stop says so — and a user's own stop marks no line.
            # (After a terminated process there is nothing to finish: the events
            # that were already in flight are shown as they always were.)
            self._finish_polite_stop()
            return
        if severity == "warning":
            self._problems.add_problem(kind, severity, message, position)
            self._warning_count += 1
            self._show_panel_tab(panels.TAB_PROBLEMS)
            self._refresh_panel_tabs()
            self._status.setText(
                f"предупреждение: {where or 'без места'} (всего: {self._warning_count})"
            )
            return
        self._problems.add_problem(kind, severity, message, position)
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

    def _open_problem(self, position) -> None:
        """Takes the editor to the line a row of «Проблемы» points at (part 88).

        What a double-click in the table does.  The row already knows its position,
        so this is the same road a fresh diagnostic takes — plus the one thing the
        click is for: the tab of that file is brought to the front.  A diagnostic
        never switches to a tab that is *already* open (it marks the line where it
        is, so a run cannot pull the user out of what they are reading), while a
        file it has to open is shown at once — showing what it opens is what
        opening a file does (part 90).

        A row with no place (a diagnostic about `<query>` or the interpreter's
        library) says so in the status bar instead of moving a caret into text the
        error is not about.
        """
        if position is None or not position.file:
            self._status.setText("проблема не указывает место в тексте")
            return
        buffer = self._diagnostic_buffer(position)
        if buffer is not None:
            # `set_current` also covers the file the run already opened: the tab
            # exists, but the one showing is the program's.
            self.active_pane().set_current(buffer)
        self._mark_error_line(position)

    def _on_trace(self, text: str) -> None:
        """The `ТРАССА` text of a traced run: the pane colours it apart."""
        if self._stopping:
            return
        self._count_output()
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
            # or a margin marker); `<library>` — the interpreter's own library.
            # Neither has a line in any tab: marking the current one would say
            # the program broke where it did not.
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
            # Diagnostics come from `_on_failed` with their fields; text of these
            # two kinds is the window feeding itself, and it gets a row with no
            # place to go to.
            self._problems.add_text(text, kind)
        elif tab == panels.TAB_SYSTEM:
            self._system.feed(text, kind)
        else:
            self._output.feed(text, kind)

    def _flush_pane_tails(self) -> None:
        """Ends the open half-line in every *text* pane; nothing else will finish it.

        «Проблемы» is a table now: it holds whole rows, so there is no half-line to
        complete.
        """
        for pane in (self._output, self._system):
            pane.flush()
        self._refresh_panel_tabs()

    def _reset_panels(self) -> None:
        """Empties the read-only panes and the table; the input queue is user data.

        A new run starts clean, which is exactly the emptying «Очистить вывод» does
        — the program's output, the diagnostics, the window's own notes and the
        answer table all go together, and a half-collected answer goes too.  One
        body, two names: the button, and the start of a run.
        """
        self.clear_output()

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
