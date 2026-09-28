"""Main window: tabs of programs, a query line and an output pane."""

from __future__ import annotations

import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import documents
from .buffers import Buffer
from .editor import CodeEditor, ZoomablePlainTextEdit
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

        #: The open programs, in tab order.  The tab bar is kept in step with
        #: this list, including after a tab is dragged to another position.
        self._buffers: list[Buffer] = []
        #: True while the whole window is closing, so closing the last tab does
        #: not open a fresh one on the way out.
        self._closing = False
        self._recent = documents.RecentFiles(self._settings.recent_files)

        self._build_ui()
        # The welcome program goes into the first tab and is *not* unsaved work —
        # the flag is left clear, so closing it asks nothing.
        welcome = documents.Document.untitled(documents.untitled_name([]))
        welcome.text = WELCOME
        self._add_buffer(welcome)
        self._session.start()

    # -- construction ------------------------------------------------------
    def _build_ui(self) -> None:
        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.tabCloseRequested.connect(self.close_buffer)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        # Dragging a tab reorders the widget, not this list: without this the
        # index of a buffer and the index of its tab would drift apart.
        self._tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        # A double click on the empty part of the bar (index -1) starts a new
        # file — the gesture the reference front-end had.
        self._tabs.tabBar().tabBarDoubleClicked.connect(self._on_tab_bar_double_clicked)

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

        self._query_line = QLineEdit()
        # The same face as the panes, so a goal looks like the program it asks
        # about; `_on_zoom_changed` keeps it in step.
        self._query_line.setFont(self._output.font())
        self._query_line.setPlaceholderText("?цель(X). — Enter, чтобы выполнить")
        self._query_line.returnPressed.connect(self._run_query)

        editor_area = QWidget()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self._tabs)
        editor_layout.addWidget(self._query_line)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(editor_area)
        splitter.addWidget(self._output)
        splitter.setSizes([600, 400])
        self.setCentralWidget(splitter)
        # A dropped program opens in its own tab; see `dropEvent`.
        self.setAcceptDrops(True)

        toolbar = QToolBar("Управление", self)
        self.addToolBar(toolbar)
        self._add_action(toolbar, "Запустить", self.run_program, ["F5", "Ctrl+R"])
        self._add_action(toolbar, "Остановить", self.stop_program, ["Shift+F5", "Ctrl+."])
        toolbar.addSeparator()
        self._add_action(toolbar, "Новый", lambda: self.new_buffer(), ["Ctrl+N"])
        self._add_action(toolbar, "Открыть…", self._open_file, ["Ctrl+O"])
        self._add_action(toolbar, "Сохранить", lambda: self.save_buffer(), ["Ctrl+S"])
        toolbar.addSeparator()
        self._add_action(toolbar, "Очистить вывод", self.clear_output, ["Ctrl+L"])

        # The commands task_26 puts into the menus; the keys already work.  Zoom
        # deliberately has no key pair of its own — `Ctrl+=`, `Ctrl++` and
        # `Ctrl+-` belong to the `РАВНО`/`СЛОЖЕНИЕ`/`ВЫЧИТАНИЕ` skeletons of
        # task_31.  `Alt+F4` needs no binding: it closes the window, and
        # `closeEvent` is where the save prompts live.
        self._add_window_action("Сохранить как…", self._save_as, "Ctrl+Shift+S")
        self._add_window_action("Сохранить все", self._save_all)
        self._add_window_action("Закрыть вкладку", self._close_current, "Ctrl+W")
        self._add_window_action("Закрыть все", self._close_all_tabs)
        self._add_window_action("Выход", self.close, "Ctrl+Q")
        self._add_window_action("Перечитать с диска", self.reload_buffer, "Ctrl+Shift+R")
        self._add_window_action("Следующая вкладка", self._next_tab, "Ctrl+Tab")
        self._add_window_action("Предыдущая вкладка", self._previous_tab, "Ctrl+Shift+Tab")
        self._add_window_action("Закомментировать", self._comment, "Ctrl+K")
        self._add_window_action("Раскомментировать", self._uncomment, "Ctrl+U")
        self._add_window_action("Сбросить масштаб", self._reset_zoom, "Ctrl+0")

        self._status = QLabel("запуск…")
        self.statusBar().addWidget(self._status)

    def _make_action(
        self, title: str, slot, shortcuts: str | list[str] | None = None
    ) -> QAction:
        """One action, used by the toolbar, the window and (task_26) the menus.

        `setShortcuts` takes a *list*: a comma inside `QKeySequence` would mean a
        two-stroke sequence (Ctrl+K, Ctrl+C) and not an alternative.  A shortcut
        shorter than the action it names is the defect this makes impossible to
        repeat — **Запустить** was bound to `Ctrl+R` while the plan promised F5,
        so the key did nothing.

        `shortcuts=None` is allowed: a menu entry does not have to have a key.
        """
        if shortcuts is None:
            keys: list[str] = []
        elif isinstance(shortcuts, str):
            keys = [shortcuts]
        else:
            keys = list(shortcuts)
        action = QAction(title, self)
        if keys:
            action.setShortcuts([QKeySequence(key) for key in keys])
            action.setToolTip(f"{title} ({keys[0]})")
        else:
            action.setToolTip(title)
        action.triggered.connect(slot)
        return action

    def _add_action(self, toolbar: QToolBar, title: str, slot, shortcuts: str | list[str]) -> None:
        toolbar.addAction(self._make_action(title, slot, shortcuts))

    def _add_window_action(
        self, title: str, slot, shortcuts: str | list[str] | None = None
    ) -> None:
        """Registers a command on the window, with or without a key."""
        self.addAction(self._make_action(title, slot, shortcuts))

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
        self._output.clear()
        self._session.start()
        self._append_output("--- загрузка программы ---\n")
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
    def new_buffer(self, name: str | None = None) -> int:
        """Adds an empty tab and makes it current."""
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
        index = self._index_of_path(path)
        if index is not None:
            # Already open: show that tab instead of a second copy of the file.
            self._tabs.setCurrentIndex(index)
            return True
        try:
            model = documents.Document.from_file(path, encoding)
        except documents.DecodeFailure as failure:
            return self._open_with_encoding(failure)
        except OSError as error:
            self._append_output(f"*** не могу открыть {path}: {error}\n")
            return False

        if len(self._buffers) == 1 and self._is_placeholder(self._buffers[0]):
            # A single empty buffer is a placeholder, not work: the file takes
            # its place instead of leaving an empty tab behind.  The welcome
            # program is not empty, so it stays until it is closed.
            self._replace_buffer(0, model)
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
                self._append_output(
                    f"*** не могу записать {path or buffer.model.path}: {retry_error}\n"
                )
                self._status.setText("не сохранено")
                return False
        except OSError as error:
            self._append_output(f"*** не могу записать {path or buffer.model.path}: {error}\n")
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
            self._append_output(f"*** не могу перечитать {buffer.model.path}: {error}\n")
            return False
        buffer.editor.setPlainText(model.text)
        buffer.model.eol = model.eol
        buffer.mark_saved()
        self._refresh_titles()
        self._status.setText(f"перечитан {buffer.model.path}")
        return True

    def close_buffer(self, index: int) -> bool:
        """Closes one tab, asking first.  Cancelling keeps it open."""
        if not 0 <= index < len(self._buffers):
            return False
        if not self._confirm_close(self._buffers[index]):
            return False
        self._drop_buffer(index)
        if not self._buffers and not self._closing:
            self.new_buffer()  # there is always somewhere to type
        self._refresh_titles()
        return True

    def close_all(self) -> bool:
        """Closes every tab, one at a time, showing the one that is closing.

        The tab is made current *before* the question, so the file the box is
        about is the one on screen, and it disappears as soon as the question is
        answered.  Cancelling therefore stops where it happened, leaving the
        buffers closed so far closed — the earlier rule (ask about everything
        first, then close) kept the tabs open but gave no clue *which* file each
        of the questions was about, which is worse in practice.
        """
        while self._buffers:
            self._tabs.setCurrentIndex(0)
            if not self._confirm_close(self._buffers[0]):
                return False
            self._drop_buffer(0)
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
            self._append_output(f"*** {failure}\n")
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
        self._append_output("--- остановлено ---\n")

    def clear_output(self) -> None:
        self._output.clear()

    # -- buffers -----------------------------------------------------------
    def _add_buffer(self, model: documents.Document) -> int:
        """Adds a tab for `model` and makes it current."""
        buffer = Buffer(model, self._settings, self)
        buffer.editor.setPlaceholderText("текст программы")
        buffer.editor.zoomChanged.connect(self._on_zoom_changed)
        # A file dropped on the editor opens in its own tab, as it does on the
        # output pane: the pane reports the drop instead of pasting the path.
        buffer.editor.fileDropped.connect(self.open_path)
        # The reserved names arrive with `ready`; a buffer opened after that gets
        # them here, and a buffer created before it is served by `_on_ready`.
        buffer.set_keywords(self._session.keywords)
        buffer.changed.connect(self._refresh_titles)
        self._buffers.append(buffer)
        index = self._tabs.addTab(buffer.editor, buffer.title())
        self._tabs.setCurrentIndex(index)
        self._refresh_titles()
        return index

    def _replace_buffer(self, index: int, model: documents.Document) -> int:
        """Turns a placeholder tab into the file that takes its place."""
        self._drop_buffer(index)
        return self._add_buffer(model)

    def _drop_buffer(self, index: int) -> None:
        """Removes a tab and the buffer behind it.  No questions are asked here."""
        self._tabs.removeTab(index)
        buffer = self._buffers.pop(index)
        buffer.editor.deleteLater()
        buffer.setParent(None)
        buffer.deleteLater()

    def _is_placeholder(self, buffer: Buffer) -> bool:
        """An empty untitled buffer with nothing in it to lose."""
        return (
            buffer.model.path is None
            and not buffer.is_modified()
            and not buffer.text().strip()
        )

    def _index_of_path(self, path: str) -> int | None:
        wanted = pathlib.Path(path)
        for index, buffer in enumerate(self._buffers):
            if buffer.model.path and pathlib.Path(buffer.model.path) == wanted:
                return index
        return None

    def _remember(self, path: str) -> None:
        """Records the file and its directory for the next dialog."""
        self._settings.recent_files = self._recent.add(path)
        self._settings.last_directory = str(pathlib.Path(path).parent)

    # -- tabs --------------------------------------------------------------
    def _on_tab_changed(self, index: int) -> None:
        self._refresh_titles()
        buffer = self.current_buffer()
        if buffer is not None and buffer.model.path:
            self._status.setText(f"открыт {buffer.model.path}")

    def _on_tab_moved(self, source: int, target: int) -> None:
        """Keeps the buffer list in the tab bar's order — the indices are shared."""
        if 0 <= source < len(self._buffers):
            self._buffers.insert(target, self._buffers.pop(source))

    def _on_tab_bar_double_clicked(self, index: int) -> None:
        if index < 0:  # the empty part of the bar, not a tab
            self.new_buffer()

    def _refresh_titles(self) -> None:
        for index, buffer in enumerate(self._buffers):
            self._tabs.setTabText(index, buffer.title())
        buffer = self.current_buffer()
        self.setWindowTitle(buffer.model.window_title() if buffer is not None else "PrologD")

    def _next_tab(self) -> None:
        self._cycle_tab(1)

    def _previous_tab(self) -> None:
        self._cycle_tab(-1)

    def _cycle_tab(self, step: int) -> None:
        if len(self._buffers) < 2:
            return
        self._tabs.setCurrentIndex((self._tabs.currentIndex() + step) % len(self._buffers))

    def _close_current(self) -> None:
        self.close_buffer(self._tabs.currentIndex())

    def _close_all_tabs(self) -> None:
        if self.close_all():
            self.new_buffer()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """Closing the window asks about every modified buffer first."""
        self._closing = True
        try:
            if self.close_all():
                event.accept()
            else:
                event.ignore()
        finally:
            self._closing = False

    # -- commands that act on the current tab ------------------------------
    def _comment(self) -> None:
        buffer = self.current_buffer()
        if buffer is not None:
            buffer.editor.comment()

    def _uncomment(self) -> None:
        buffer = self.current_buffer()
        if buffer is not None:
            buffer.editor.uncomment()

    def _reset_zoom(self) -> None:
        buffer = self.current_buffer()
        if buffer is not None:
            buffer.editor.reset_zoom()

    # -- drag and drop -----------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """A dropped program opens in its own tab.  It is not run: a run is F5."""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(url.toLocalFile())
        event.acceptProposedAction()

    # -- accessors for the actions and the tests ---------------------------
    @property
    def session(self) -> PrologSession:
        """The interpreter session; the window owns exactly one."""
        return self._session

    def buffers(self) -> list[Buffer]:
        """The open programs, in tab order."""
        return list(self._buffers)

    def tab_count(self) -> int:
        return len(self._buffers)

    def current_buffer(self) -> Buffer | None:
        """The tab that is showing, or None in the moment the last one closes."""
        index = self._tabs.currentIndex()
        if 0 <= index < len(self._buffers):
            return self._buffers[index]
        return None

    def editor(self) -> CodeEditor:
        """The current tab's editor, for the commands that act on a selection.

        There is always one while the window is open: the last tab is never
        closed without a replacement being made.
        """
        buffer = self.current_buffer()
        assert buffer is not None, "окно без вкладок"
        return buffer.editor

    def editor_text(self) -> str:
        buffer = self.current_buffer()
        return buffer.text() if buffer is not None else ""

    def output(self) -> ZoomablePlainTextEdit:
        """The read-only output pane (task_27 gives it a place of its own)."""
        return self._output

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
        self._query_line.setFont(self._output.font())
        self._status.setText(f"шрифт {size:.0f} pt")

    def _on_result(self, found: bool) -> None:
        """Records the outcome; the text of the answer already arrived as output.

        The interpreter prints `ДА`, `НЕТ` or the bindings itself, and `result`
        only says the query is over.  Appending another `НЕТ` here is what made a
        failing query print it twice — the program was never wrong.
        """
        self._status.setText("решение найдено" if found else "решения нет")

    def _on_input_request(self, kind: str) -> None:
        prompt = {"token": "Слово", "line": "Строка", "codepoint": "Символ"}.get(kind, "Ввод")
        if kind == "codepoint":
            answer, accepted = QInputDialog.getText(self, "Ввод", prompt + ":")
        else:
            answer, accepted = QInputDialog.getMultiLineText(self, "Ввод", prompt + ":")
        self._session.answer_input(answer if accepted else "")

    def _on_failed(self, kind: str, message: str) -> None:
        self._append_output(f"*** {kind}: {message}\n")

    def _on_ended(self, exit_code: int) -> None:
        self._status.setText(f"интерпретатор завершился, код {exit_code}")

    def _append_output(self, text: str) -> None:
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
