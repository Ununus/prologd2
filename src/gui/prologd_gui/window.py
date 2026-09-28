"""Main window: panes of programs, a query line, the output and the input queue.

One program is one `Buffer` (a model, a text document and its views).  The window
owns the open documents; a `Pane` shows them in tabs, and the split editor is two
panes over the same set of documents — so the left pane can show one program while
the right shows another, and both views edit the same text.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIntValidator, QKeySequence
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

from . import actions, appearance, assets, documents
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
        self._session.ended.connect(self._on_ended)

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
        self._session.start()

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
        # there next time in every pane.  (task_29 can split them.)
        self._output = ZoomablePlainTextEdit(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
        )
        self._output.setReadOnly(True)
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

        self._query_line = QLineEdit()
        # The same face as the panes, so a goal looks like the program it asks
        # about; `_on_zoom_changed` keeps it in step.
        self._query_line.setFont(self._output.font())
        self._query_line.setPlaceholderText("?цель(X). — Enter, чтобы выполнить")
        self._query_line.returnPressed.connect(self._run_query)

        editor_area = QWidget()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._editor_splitter)
        editor_layout.addWidget(self._query_line)

        # The output on top, the input queue under it.
        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(self._output)
        right.addWidget(self._input_pane)
        right.setSizes([420, 110])

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(editor_area)
        splitter.addWidget(right)
        splitter.setSizes([600, 400])
        self.setCentralWidget(splitter)
        # A dropped program opens in its own tab; see `dropEvent`.
        self.setAcceptDrops(True)

        self._build_actions()
        self._build_toolbar()
        self._build_menus()

        self._status = QLabel("запуск…")
        self.statusBar().addWidget(self._status)

        # The first pane, always: the window never has no place to edit in.
        self._add_pane()
        self._sync_actions()

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
            "toolbar": self._toggle_toolbar,
            "split": self.split_editor,
            "merge": self.merge_editor,
            "next_tab": self._next_tab,
            "previous_tab": self._previous_tab,
            "line_numbers": self._toggle_line_numbers,
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "zoom_reset": self._reset_zoom,
            "theme": self._toggle_theme,
            "full_screen": self._toggle_full_screen,
            "run": self.run_program,
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

    def _sync_actions(self) -> None:
        """Makes the checkable entries agree with the settings and the panes."""
        # `isHidden`, not `isVisible`: a toolbar of a window that was never shown
        # is not visible either, and reading that as "the user hid it" would write
        # the wrong preference on the first start.
        self._actions["toolbar"].setChecked(not self._toolbar.isHidden())
        self._actions["line_numbers"].setChecked(self._settings.line_numbers)
        self._actions["theme"].setChecked(self._settings.theme == appearance.SYSTEM)
        self._actions["save_before_run"].setChecked(self._settings.save_before_run)
        self._actions["full_screen"].setChecked(self.isFullScreen())
        self._actions["split"].setEnabled(len(self._panes) < 2)
        self._actions["merge"].setEnabled(len(self._panes) > 1)
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

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "О программе",
            "PrologD 2.0 — графическая оболочка (PySide6).\n\n"
            f"Интерпретатор: {self._version or 'ещё не ответил'}\n"
            f"Панелей редактора: {len(self._panes)}\n"
            f"Настройки: {self._settings.path}",
        )

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
        self._status.setText("редактор разделён: две панели, одна программа")
        return True

    def merge_editor(self, remember: bool = True) -> bool:
        """Closes the second pane; the documents stay open."""
        if len(self._panes) < 2:
            return False
        pane = self._panes.pop()
        current = pane.current_buffer()
        # The views belong to the pane; they are detached before it goes, or the
        # buffers would keep dangling editors (see `Pane.set_buffers`).
        pane.set_buffers([])
        self._editor_splitter.widget(1).setParent(None)
        pane.deleteLater()
        self._active_pane = 0
        if current is not None:
            self._panes[0].set_current(current)  # the eyes stay on that program
        if remember:
            self._save_split_state()
        self._refresh_titles()
        self._status.setText("редактор объединён: одна панель")
        return True

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
    def run_program(self) -> None:
        """Runs the current buffer in a fresh interpreter.

        A run starts from a clean slate: a fresh interpreter (no clauses, RNG
        seed, redirected files or preloaded input left from the previous run)
        and an empty output pane.  Reusing the session accumulates clauses —
        with a duplicated `факториал/2` the factorial example returns 64
        solutions instead of one, which looks like a loop — so `start()` stops
        a live process first.
        """
        buffer = self.current_buffer()
        if buffer is None:
            return
        path = buffer.model.path
        if self._settings.save_before_run and buffer.is_modified():
            # The switch of the «Выполнение» menu: a run is then always of what is
            # on disk, which is what makes `ИМПОРТ` and the diagnostics agree
            # with the editor about the file's own path.
            if not self.save_buffer(buffer):
                self._status.setText("запуск отменён: сохранить не удалось")
                return
        self._output.clear()
        # Every run starts with the prepared answers from the field: that is what
        # makes a program that reads several values runnable without a dialog per
        # value — and a cancelled question applies to this run only.
        self._stopped_input = False
        self._queued_input = self._input_lines()
        self._session.start()
        self._append_note("--- загрузка программы ---\n")
        if self._queued_input:
            self._append_note(f"--- ввод из поля, строк — {len(self._queued_input)} ---\n")
        if path is not None and not buffer.is_modified():
            # A saved, unmodified buffer is loaded by path: `ИМПОРТ` resolves
            # against the file's own directory and diagnostics name the file.
            self._session.load_file(path)
            self._status.setText(f"выполняется {pathlib.Path(path).name}")
        else:
            # Otherwise the text comes from the editor, and the path, when there
            # is one, is what the loader treats as the importing file.  The
            # status line says which case is running, so a failing `ИМПОРТ` is
            # not a mystery: without a path it searches only the working
            # directory and the `-I` directories.
            self._session.load_text(buffer.text(), path or "<buffer>")
            name = pathlib.Path(path).name if path else "буфер без имени"
            self._status.setText(f"выполняется {name} (есть несохранённые правки)")

    def _run_query(self) -> None:
        text = self._query_line.text().strip()
        if not text:
            return
        self._query_line.clear()
        if not text.startswith("?"):
            text = "?" + text
        self._session.run_query(text)

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
        self._session.stop()
        self._status.setText("остановлено")
        self._append_note("--- остановлено ---\n")

    def clear_output(self) -> None:
        self._output.clear()

    # -- buffers -----------------------------------------------------------
    def _add_buffer(self, model: documents.Document) -> Buffer:
        """Adds a document, shows it in every pane, makes it current."""
        buffer = Buffer(model, self._settings, self)
        buffer.changed.connect(self._refresh_titles)
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
            self._append_note(f"> {line}\n")
            self._session.answer_input(line)
            self._status.setText(f"ввод из поля, осталось строк — {len(self._queued_input)}")
            return
        answer = self._ask_input(kind)
        if answer is None:
            self._stopped_input = True
            self._append_note("--- ввод отменён: программа остановлена ---\n")
            self._session.stop()
            self._status.setText("ввод отменён, выполнение остановлено")
            return
        self._session.answer_input(answer)

    def _input_lines(self) -> list[str]:
        """The input field, one answer per line, blank lines dropped.

        A line is taken as written — leading spaces can matter for a string — but
        a line that is empty or only spaces is an answer to nothing, and skipping
        it is what keeps the field easy to read.
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
        for buffer in self._buffers:
            buffer.set_keywords(self._session.keywords)
        self._status.setText(f"PrologD {version} готов")
        self._refresh_titles()

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
        self._query_line.setFont(self._output.font())
        self._show_font_size(size)
        self._status.setText(f"шрифт {size:.0f} pt")

    def _on_result(self, found: bool) -> None:
        """Records the outcome; the text of the answer already arrived as output.

        The interpreter prints `ДА`, `НЕТ` or the bindings itself, and `result`
        only says the query is over.  Appending another `НЕТ` here is what made a
        failing query print it twice — the program was never wrong.
        """
        self._status.setText("решение найдено" if found else "решения нет")

    def _on_failed(self, kind: str, message: str) -> None:
        self._append_note(f"*** {kind}: {message}\n")

    def _on_ended(self, exit_code: int) -> None:
        self._status.setText(f"интерпретатор завершился, код {exit_code}")

    def _append_output(self, text: str) -> None:
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _append_note(self, text: str) -> None:
        """Appends a note of our own, starting on a line of its own.

        The interpreter prints without a trailing newline when a program uses
        `ВЫВОД` and no `ПС` (that is the documented behaviour: `ВЫВОД` prints,
        `ПС` starts a new line), so a note would otherwise be glued to the last
        line of the program's output.
        """
        current = self._output.toPlainText()
        if current and not current.endswith("\n"):
            self._append_output("\n")
        self._append_output(text)

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
