"""Main window: panes of programs, a query line, the output and the input queue.

One program is one `Buffer` (a model, a text document and its views).  The window
owns the open documents; a `Pane` shows them in tabs, and the split editor is two
panes over the same set of documents — so the left pane can show one program while
the right shows another, and both views edit the same text.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIntValidator, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import actions, appearance, assets, documents, findbar, panels, search
from .buffers import Buffer
from .editor import CodeEditor, ZoomablePlainTextEdit
from .panes import Pane
from .session import PrologSession
from .settings import Settings

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

        self._session = PrologSession(executable, includes, self)
        self._session.ready.connect(self._on_ready)
        self._session.output.connect(self._append_output)
        self._session.result.connect(self._on_result)
        self._session.input_request.connect(self._on_input_request)
        self._session.failed.connect(self._on_failed)
        self._session.trace.connect(self._on_trace)
        self._session.stepped.connect(self._on_stepped)
        self._session.ended.connect(self._on_ended)

        #: Warnings seen in the current run, shown beside the answer; reset when
        #: the interpreter comes up, because every run starts a fresh one.
        self._warning_count = 0

        #: The open documents, in the order every pane shows them.  A pane has its
        #: own *current* tab, but the set and the order are shared: a tab dragged in
        #: one pane has to move in the other as well.
        self._buffers: list[Buffer] = []
        #: True while the whole window is closing, so closing the last document does
        #: not open a fresh one on the way out.
        self._closing = False
        #: Answers taken from the input field, one per request; refilled by every
        #: run (see `run_program`).
        self._queued_input: list[str] = []
        #: Set when the user cancelled an input question: the run is stopped and
        #: nothing else is asked during it.
        self._stopped_input = False
        self._recent = documents.RecentFiles(self._settings.recent_files)
        #: What the interpreter announced in `ready`, for «О программе».
        self._version = ""
        #: The exit code of the last run, shown in the status bar until the next one.
        self._exit_code: int | None = None
        #: True while a stop of our own is in flight, so the exit code it produces
        #: (a termination status, not an exit code) is not reported as one.
        self._stopping = False
        #: Two states, not one: the interpreter is a process that can be *up* and
        #: idle, and a computation can be *in flight* in it.  `Запустить` needs the
        #: second (there is nothing to start while one is running) and `Остановить`
        #: the first (an idle interpreter still holds a knowledge base).
        self._busy = False
        #: Whether a program was loaded into the running interpreter (`run_program`).
        self._loaded = False

        self._build_ui()
        # The split editor comes back if it was left open, and before the first
        # document, so the welcome program is shown in both panes on that start.
        if self._settings.restore_split and self._settings.split_editor:
            self.split_editor(remember=False, sizes=self._settings.split_sizes)
        # The welcome program goes into the first tab and is *not* unsaved work —
        # the flag is left clear, so closing it asks nothing.
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

        # The output is read-only, but it is monospace and it zooms with the
        # editor: one stored size covers both, so what the user set is still
        # there next time in every pane.  (task_29 can split them.)  The pane
        # itself — colours per kind, the bounded history, the tail it holds between
        # chunks — lives in `panels.py`.
        self._output = panels.OutputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._output.setPlaceholderText("вывод интерпретатора")
        self._output.zoomChanged.connect(self._on_zoom_changed)
        # A dropped program opens in a tab wherever it lands (see `dropEvent`).
        self._output.fileDropped.connect(self.open_path)

        # The input queue lives under the output: one line per answer the program
        # will ask for, fed automatically until the list runs out (`_input_lines`).
        self._input_pane = ZoomablePlainTextEdit(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._input_pane.setPlaceholderText("ввод: по строке на каждый запрос")
        self._input_pane.setToolTip(
            "Строки для ВВКОД, ВВОДСТР, ВВОДСИМВ и подобных: по одной на каждый запрос.\n"
            "Пустые строки пропускаются. Когда строки кончатся, окно спросит в диалоге."
        )
        self._input_pane.zoomChanged.connect(self._on_zoom_changed)
        self._input_pane.fileDropped.connect(self.open_path)

        # The console: what the program asks once the prepared lines under it run
        # out (or when that field is hidden).  `Ctrl+Enter` sends; «Остановить» is
        # how a run that waits for an answer is abandoned.
        self._input_console = panels.InputPane(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._input_console.submitted.connect(self._send_input)

        self._query_line = QLineEdit()
        # The same face as the panes, so a goal looks like the program it asks
        # about; `_on_zoom_changed` keeps it in step.
        self._query_line.setFont(self._output.font())
        self._query_line.setPlaceholderText("?цель(X). — Enter, чтобы выполнить")
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
        self._step_pane.stopped.connect(self.stop_program)

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

        # The output on top, the input queue under it.  The two travel together:
        # the panel is one widget that `F4` hides and `Ctrl+F4` moves — the pair of
        # commands the reference front-end had, but arranged as "one splitter with
        # two orientations" rather than two nested splitters being flipped.
        self._editor_area = editor_area
        self._sidebar = QSplitter(Qt.Orientation.Vertical)
        self._sidebar.addWidget(self._output)
        self._sidebar.addWidget(self._input_console)
        self._sidebar.addWidget(self._input_pane)
        stored = [size for size in self._settings.output_sizes if size > 0]
        self._sidebar.setSizes(stored if len(stored) == 3 else [360, 140, 90])
        self._input_pane.setVisible(self._settings.input_queue)

        # One splitter, two orientations: side by side when the panel is on the
        # right, stacked when it is at the bottom.  The order (editor first) is the
        # same either way, so the turn is only an orientation change.
        self._panel_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._panel_splitter.addWidget(self._editor_area)
        self._panel_splitter.addWidget(self._sidebar)
        # A pane may not be dragged away to nothing: an output panel squeezed to
        # zero pixels looks like a lost window rather than a hidden one.
        self._panel_splitter.setChildrenCollapsible(False)
        self._editor_area.setMinimumWidth(240)
        self._sidebar.setMinimumWidth(200)
        self._sidebar.setMinimumHeight(120)
        self.setCentralWidget(self._panel_splitter)
        self._apply_output_position(remember=False)
        self._sidebar.setVisible(self._settings.output_visible)
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
            "select_all": self._select_all,
            "comment": self._comment,
            "uncomment": self._uncomment,
            "clear_output": self.clear_output,
            "find": lambda: self.show_find(),
            "find_next": lambda: self.find_step(False),
            "find_prev": lambda: self.find_step(True),
            "find_selected": lambda: self.find_selected(False),
            "find_selected_prev": lambda: self.find_selected(True),
            "toolbar": self._toggle_toolbar,
            "output": self._toggle_output,
            "input_queue": self._toggle_input_queue,
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
            "theme": self._toggle_theme,
            "full_screen": self._toggle_full_screen,
            "run": lambda: self.run_program(),
            "run_trace": lambda: self.run_program(trace=True),
            "step": self.step_into,
            "step_over": self.step_over,
            "stop": self.stop_program,
            "save_before_run": self._toggle_save_before_run,
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
            elif key == actions.FONT_SIZE:
                self._toolbar.addWidget(self._build_font_size_box())
            else:
                self._toolbar.addAction(self._actions[key])
        self._toolbar.setVisible(self._settings.toolbar_visible)
        self.addToolBar(self._toolbar)

    def _build_font_size_box(self) -> QWidget:
        """The font-size control: the same preference `Ctrl`+wheel writes.

        Editable on purpose.  The wheel produces sizes that are not in any list
        (23 pt, say), and a control that shows `20` while the text is 23 pt is a
        small lie; typing a size is a bonus.  The validator keeps it inside the
        range the editor itself enforces.
        """
        self._font_size_box = QComboBox()
        for size in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 32):
            self._font_size_box.addItem(f"{size}", float(size))
        self._font_size_box.setEditable(True)
        self._font_size_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._font_size_box.lineEdit().setValidator(QIntValidator(6, 72, self))
        self._font_size_box.setToolTip("Размер шрифта всех панелей, 6…72 pt")
        self._font_size_box.currentIndexChanged.connect(self._on_font_size_chosen)
        self._font_size_box.lineEdit().editingFinished.connect(self._on_font_size_typed)
        self._show_font_size(self._settings.font_size)
        return self._font_size_box

    def _show_font_size(self, size: float) -> None:
        """Shows the size in the box without answering for it.

        The box is a *view* of the preference, so its signals are blocked while it
        is set: answering would write the setting back on every repaint.
        """
        if not hasattr(self, "_font_size_box"):
            return
        box = self._font_size_box
        box.blockSignals(True)
        box.lineEdit().blockSignals(True)
        index = box.findData(float(size))
        if index < 0:
            box.setEditText(f"{size:.0f}")
        else:
            box.setCurrentIndex(index)
        box.lineEdit().blockSignals(False)
        box.blockSignals(False)

    def _on_font_size_chosen(self, index: int) -> None:
        size = self._font_size_box.itemData(index)
        if size:
            self._on_zoom_changed(float(size))

    def _on_font_size_typed(self) -> None:
        """A size typed into the box; the validator keeps it 6…72."""
        text = self._font_size_box.currentText().strip()
        try:
            size = float(text)
        except ValueError:
            return  # the validator should not have let this through
        if abs(size - self._settings.font_size) > 0.01:
            self._on_zoom_changed(size)

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
        """
        self._actions["run"].setEnabled(not self._busy)
        self._actions["stop"].setEnabled(self._session.is_running())
        # A *paused* step is a usable state, not a busy one: «Шаг», «Шаг с обходом»
        # and «Запустить» (which then means «продолжить») have to be live, or their
        # keys are dead exactly when the user needs them — a disabled `QAction`
        # fires no shortcut.  A run actually in flight is the blocked state.
        free = not self._busy or self._session.paused()
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
        self._actions["theme"].setChecked(self._settings.theme == appearance.SYSTEM)
        self._actions["save_before_run"].setChecked(self._settings.save_before_run)
        self._actions["full_screen"].setChecked(self.isFullScreen())
        self._actions["output"].setChecked(self.output_visible())
        self._actions["input_queue"].setChecked(self._settings.input_queue)
        self._sync_pane_actions()
        self._sync_undo_actions()
        self._sync_run_actions()
        self._show_font_size(self._settings.font_size)

    # -- editing commands of the current view ------------------------------
    def _undo(self) -> None:
        self.editor().undo()

    def _redo(self) -> None:
        self.editor().redo()

    def _cut(self) -> None:
        self.editor().cut()

    def _copy(self) -> None:
        self.editor().copy()

    def _paste(self) -> None:
        self.editor().paste()

    def _delete(self) -> None:
        self.editor().textCursor().removeSelectedText()

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

    def _toggle_full_screen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _toggle_theme(self, checked: bool) -> None:
        """`system` when checked, the forced light palette otherwise.

        The syntax colours are chosen for a light background, so the light palette
        is the one that always reads well; `system` is there for a desktop that
        wants it (task_29 gives it a dark palette of its own).
        """
        name = appearance.SYSTEM if checked else appearance.LIGHT
        self._settings.theme = name
        appearance.apply_theme(QApplication.instance(), name)
        self._status.setText(f"оформление: {name}")

    def about_text(self) -> str:
        """What «О программе» says.  Separate from the box so a test can read it
        without a modal window it cannot close."""
        return (
            "PrologD 2.0 — графическая оболочка (PySide6).\n\n"
            f"Интерпретатор: {self._version or 'ещё не ответил'}\n"
            f"Панелей редактора: {len(self._panes)}\n"
            f"Настройки: {self._settings.path}"
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
        return not self._sidebar.isHidden()

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
        self._sidebar.setVisible(bool(visible))
        self._status.setText("панель вывода показана" if visible else "панель вывода скрыта")

    def _toggle_input_queue(self, checked: bool) -> None:
        """Hides the prepared answers, and stops taking anything from them."""
        self._settings.input_queue = bool(checked)
        self._input_pane.setVisible(bool(checked))
        self._status.setText("поле очереди ввода: " + ("показано" if checked else "скрыто"))

    def _save_panel_state(self) -> None:
        """Remembers the side of the panel and the sizes inside both splitters."""
        self._settings.output_position = self.output_position()
        self._settings.panel_sizes = list(self._panel_splitter.sizes())
        self._settings.output_sizes = list(self._sidebar.sizes())

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
            self._status.setText(f"открыт {buffer.model.path}{where}")
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
                    questions: bool = True) -> bool:
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
        answered *alone* instead of after the whole lesson (task_36).

        The result is True when the load was sent; a caller that wants to add a
        query of its own (`_on_query_requested`) must not do it otherwise.
        """
        if self._session.paused() and not (trace or step):
            # `F5` while a step is paused means «продолжить»: starting the file over
            # would throw away the run the user is walking through.
            self.step_continue()
            return False
        buffer = self.current_buffer()
        if buffer is None:
            return False
        path = buffer.model.path
        if self._settings.save_before_run and buffer.is_modified():
            # The switch of the «Выполнение» menu: a run is then always of what is
            # on disk, which is what makes `ИМПОРТ` and the diagnostics agree
            # with the editor about the file's own path.
            if not self.save_buffer(buffer):
                self._status.setText("запуск отменён: сохранить не удалось")
                return False
        self._output.clear()
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
        self._busy = True
        self._loaded = True
        self._session.start()
        # At once, not when `ready` arrives: the user pressed the button, and it
        # must not be pressable again while the interpreter is coming up.
        self._sync_run_actions()
        self._update_details()
        self._append_note("--- загрузка базы знаний ---\n")
        if self._queued_input:
            self._append_note(f"--- ввод из поля, строк — {len(self._queued_input)} ---\n")
        if path is not None and not buffer.is_modified():
            # A saved, unmodified buffer is loaded by path: `ИМПОРТ` resolves
            # against the file's own directory and diagnostics name the file.
            self._session.load_file(path, step=step, trace=trace, questions=questions)
            self._status.setText(f"выполняется {pathlib.Path(path).name}")
        else:
            # Otherwise the text comes from the editor, and the path, when there
            # is one, is what the loader treats as the importing file.  The
            # status line says which case is running, so a failing `ИМПОРТ` is
            # not a mystery: without a path it searches only the working
            # directory and the `-I` directories.
            self._session.load_text(buffer.text(), path or "<buffer>", step=step, trace=trace,
                                    questions=questions)
            name = pathlib.Path(path).name if path else "буфер без имени"
            self._status.setText(f"выполняется {name} (есть несохранённые правки)")
        return True

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
            self._session.start()
        self._busy = True
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
        """
        if not statement:
            return
        if self._busy or self._session.paused():
            # «Остановить», then the clicked query: a runaway is ended by ending
            # its process, and the pane's last word is the answer asked for.
            self.stop_program()
        self._query_line.setText(statement)
        if not self.run_program(questions=False):
            return
        self._session.run_query(statement)

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
        self._status.setText(f"открыт {path}")
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
        self._status.setText(f"сохранён {written}")
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
        self._status.setText(f"перечитан {buffer.model.path}")
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
        if not self._session.is_running():
            self._status.setText("интерпретатор уже остановлен")
            return
        # What the stop *means* depends on what it interrupts: a computation that is
        # in flight is stopped, an idle interpreter with a base loaded is unloaded.
        unloading = self._loaded and not self._busy
        self._stopping = True
        self._busy = False
        self._loaded = False
        self._session.stop()
        message = "база знаний выгружена" if unloading else "остановлено"
        self._input_console.idle()
        self._step_pane.idle()
        self._step_stack.clear()
        self._status.setText(message)
        self._append_note(f"--- {message} ---\n")
        # The process is gone, so the buttons change at once — waiting for `ended`
        # would leave «Остановить» enabled on a session that is already dead.
        self._sync_run_actions()
        self._update_details()

    def clear_output(self) -> None:
        """Empties the pane, including the half-line it was holding."""
        self._output.reset()

    def _save_output(self) -> None:
        """Writes the output pane to a file of the user's choosing."""
        path = self._ask_save_output_path()
        if not path:
            return
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

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """Closing the window asks about every modified buffer first."""
        self._closing = True
        try:
            if self.close_all():
                self._save_split_state()
                self._save_panel_state()
                # The interpreter is this window's child: an unasked-for close
                # must not leave it running behind the user (and a headless test
                # suite otherwise collects one live process per test).
                self.stop_program()
                event.accept()
            else:
                event.ignore()
        finally:
            self._closing = False

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

        `text` overrides the prefill, which is how `Ctrl+F3` hands over the word
        it found.  An empty prefill leaves the previous question in the field: a
        reader who searched for `факт` a moment ago does not want the field wiped
        because the caret happens to sit on a bracket.
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

    def find_selected(self, backwards: bool = False) -> bool:
        """`Ctrl+F3` / `Ctrl+Shift+F3`: the word under the caret, then the next one.

        The step starts *outside* the selection, or the first hit would be the
        text that is already on screen and the command would look dead.
        """
        view = self._find_view()
        if view is None:
            return False
        token = view.selected_token() or view.word_under_cursor()
        if not token:
            return False
        self._find_bar.set_needle(token)
        self._find_bar.setVisible(True)
        self._bind_find_view(view)
        cursor = view.textCursor()
        # `-1` backwards is one before the first character, which wraps round the
        # top of the document; `selectionEnd()` forwards is past the current word.
        start = cursor.selectionStart() - 1 if backwards else cursor.selectionEnd()
        self._find_current = None
        found = self.find_step(backwards, start)
        self._find_bar.focus_find()
        return found

    def find_step(self, backwards: bool = False, start: int | None = None) -> bool:
        """`F3` / `Shift+F3`: the next match, wrapping at the ends.

        Works with the bar closed — the question in its field is the one the last
        search asked — but a bar that has never been used has no question and
        `F3` then does what `Ctrl+F` does.

        `start` overrides where the step begins, which is how «Найти выделенное»
        skips the word that is already selected.
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
        if start is None:
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
        if not self._sidebar.isHidden():
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
        it is what keeps the field easy to read.  A *hidden* field contributes
        nothing: hiding it is how the console below takes over for good.
        """
        if self._input_pane.isHidden():
            return []
        return [line for line in self._input_pane.toPlainText().split("\n") if line.strip()]

    def _ask_input(self, kind: str) -> str | None:
        """One line from the user; `None` when the question was cancelled.

        A method of its own, like `_ask_save`: a modal box cannot be driven from a
        headless test, and a test that forgets to replace it hangs instead of
        failing.  The field is single-line on purpose — `Enter` answers, the way it
        does in the query line, and a whole line of program input is rarely a
        paragraph.
        """
        prompt = {"token": "Слово", "line": "Строка", "codepoint": "Символ"}.get(kind, "Ввод")
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
        return self._output.toPlainText()

    def current_path(self) -> str | None:
        buffer = self.current_buffer()
        return buffer.model.path if buffer is not None else None

    def recent_files(self) -> list[str]:
        """What the recent-files menu of task_26 will show, newest first."""
        return self._recent.paths()

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
        self._status.setText(f"PrologD {version} готов")
        self._refresh_titles()
        self._sync_run_actions()
        self._update_details()

    def _on_zoom_changed(self, size: float) -> None:
        """One size for every editor, the output and the query line, stored at once.

        Setting the size on the other panes emits `zoomChanged` again; those
        calls change nothing and stop there, because `set_font_size` returns
        early when the size is already the one asked for.
        """
        self._settings.font_size = size
        for buffer in self._buffers:
            buffer.set_font_size(size)
        self._output.set_font_size(size)
        self._input_pane.set_font_size(size)
        self._input_console.set_font_size(size)
        self._step_pane.set_font_size(size)
        self._query_line.setFont(self._output.font())
        self._show_font_size(size)
        self._status.setText(f"шрифт {size:.0f} pt")

    def _on_result(self, found: bool) -> None:
        """Records the outcome; the text of the answer already arrived as output.

        The interpreter prints `ДА`, `НЕТ` or the bindings itself, and `result`
        only says the query is over.  Appending another `НЕТ` here is what made a
        failing query print it twice — the program was never wrong.

        The query being over is what frees `Запустить`: the run is finished, the
        knowledge base is still loaded, and the next run restarts the file.
        """
        self._busy = False
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

    def _on_failed(self, kind: str, severity: str, message: str, position=None) -> None:
        """A diagnostic: the pane shows it with its file, the editor marks the line.

        The position arrives in fields of its own (protocol 3), so nothing is
        parsed out of the message — the message is what the interpreter wrote, and
        the file and the line are put in front of it here.  A *warning* is amber
        in the pane and counted in the status bar; it never ends the run, which is
        why the rest of this handler only runs for an error.
        """
        where = position.where() if position is not None else ""
        if severity == "warning":
            self._output.feed(
                f"*** предупреждение: {where + ': ' if where else ''}{message}\n",
                panels.WARNING,
            )
            self._warning_count += 1
            self._status.setText(
                f"предупреждение: {where or 'без места'} (всего: {self._warning_count})"
            )
            return
        self._output.feed(f"*** {kind}: {where + ': ' if where else ''}{message}\n", panels.ERROR)
        self._busy = False
        self._step_pane.idle()
        self._step_stack.clear()
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
        (where it is opened).  A name in angle brackets (`<buffer>`, `<library>`)
        is not a file at all — it is the text the window itself sent.
        """
        name = position.file if position is not None else ""
        if not name or name.startswith("<"):
            return self.current_buffer()
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
        # A process *we* killed has no meaningful code: Windows reports the
        # termination status as a number nobody can read (62097), so the message
        # stays «остановлено» and the status bar keeps the last real code.
        if self._stopping:
            self._stopping = False
            self._output.flush()
            self._sync_run_actions()
            self._update_details()
            return
        self._exit_code = exit_code
        self._busy = False
        self._loaded = False
        self._step_pane.idle()
        self._step_stack.clear()
        # The last half-line: a program that stopped in the middle of `ВЫВОД` left
        # it in the pane's buffer, and nothing else will complete it.
        self._output.flush()
        self._status.setText(f"интерпретатор завершился, код {exit_code}")
        self._sync_run_actions()
        self._update_details()

    def _append_output(self, text: str, kind: str = panels.OUTPUT) -> None:
        """Hands text to the output pane, which colours it by kind.

        The pane holds whatever follows the last newline, so a program that prints
        with `ВЫВОД` and no `ПС` keeps its half-line until the rest arrives — or
        until the run ends and `flush()` writes it.
        """
        self._output.feed(text, kind)

    def _append_note(self, text: str) -> None:
        """Appends a note of our own, coloured apart from the program's output.

        The interpreter prints without a trailing newline when a program uses
        `ВЫВОД` and no `ПС` (that is the documented behaviour: `ВЫВОД` prints,
        `ПС` starts a new line).  The pane closes the half-line first, because the
        kind changed — otherwise the note would be glued to the program's text.
        """
        self._output.feed(text, panels.NOTE)
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
