"""Main window: a program editor, a query line and an output pane."""

from __future__ import annotations

import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .session import PrologSession

WELCOME = """% PrologD — пример программы
студент(вова, корчагин).
студент(данил, ахмеров).

?студент(X, Y).
"""


class MainWindow(QMainWindow):
    def __init__(self, executable: str, includes: list[str] | None = None):
        super().__init__()
        self.setWindowTitle("PrologD")
        self.resize(1000, 700)

        self._session = PrologSession(executable, includes, self)
        self._session.ready.connect(self._on_ready)
        self._session.output.connect(self._append_output)
        self._session.result.connect(self._on_result)
        self._session.input_request.connect(self._on_input_request)
        self._session.failed.connect(self._on_failed)
        self._session.ended.connect(self._on_ended)

        #: The file the buffer belongs to, or None for an untitled buffer.  It is
        #: not only a label: `ИМПОРТ` resolves against the directory of the file
        #: the loader is given, so a run passes it to the interpreter.
        self._path: str | None = None

        self._build_ui()
        self._editor.document().modificationChanged.connect(self._update_title)
        self._session.start()

    # -- construction ------------------------------------------------------
    def _build_ui(self) -> None:
        monospace = QFont("Cascadia Mono")
        monospace.setStyleHint(QFont.StyleHint.Monospace)

        self._editor = QPlainTextEdit(WELCOME)
        self._editor.setFont(monospace)
        self._editor.setPlaceholderText("текст программы")

        self._output = QPlainTextEdit()
        self._output.setFont(monospace)
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("вывод интерпретатора")

        self._query_line = QLineEdit()
        self._query_line.setFont(monospace)
        self._query_line.setPlaceholderText("?цель(X). — Enter, чтобы выполнить")
        self._query_line.returnPressed.connect(self._run_query)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._editor)
        left_layout.addWidget(self._query_line)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self._output)
        splitter.setSizes([600, 400])
        self.setCentralWidget(splitter)

        toolbar = QToolBar("Управление", self)
        self.addToolBar(toolbar)
        self._add_action(toolbar, "Запустить", self.run_program, ["F5", "Ctrl+R"])
        self._add_action(toolbar, "Открыть…", self._open_file, ["Ctrl+O"])
        self._add_action(toolbar, "Остановить", self.stop_program, ["Shift+F5", "Ctrl+."])
        self._add_action(toolbar, "Очистить вывод", self.clear_output, ["Ctrl+L"])

        self._status = QLabel("запуск…")
        self.statusBar().addWidget(self._status)

    def _add_action(self, toolbar: QToolBar, title: str, slot, shortcuts: str | list[str]) -> None:
        """Adds a toolbar button whose tooltip names its keys.

        `setShortcuts` takes a *list*: a comma inside `QKeySequence` would mean a
        two-stroke sequence (Ctrl+K, Ctrl+C) and not an alternative.  A shortcut
        shorter than the action it names is the defect this makes impossible to
        repeat — **Запустить** was bound to `Ctrl+R` while the plan promised F5,
        so the key did nothing.
        """
        if isinstance(shortcuts, str):
            shortcuts = [shortcuts]
        action = QAction(title, self)
        action.setShortcuts([QKeySequence(shortcut) for shortcut in shortcuts])
        action.setToolTip(f"{title} ({shortcuts[0]})")
        action.triggered.connect(slot)
        toolbar.addAction(action)

    # -- actions -----------------------------------------------------------
    def run_program(self) -> None:
        # A run starts from a clean slate: a fresh interpreter (no clauses, RNG
        # seed, redirected files or preloaded input left from the previous run)
        # and an empty output pane.  Reusing the session accumulates clauses —
        # with a duplicated `факториал/2` the factorial example returns 64
        # solutions instead of one, which looks like a loop — so `start()` stops
        # a live process first.
        self._output.clear()
        self._session.start()
        self._append_output("--- загрузка программы ---\n")
        if self._path is not None and not self._editor.document().isModified():
            # A saved, unmodified buffer is loaded by path: `ИМПОРТ` resolves
            # against the file's own directory and diagnostics name the file.
            self._session.load_file(self._path)
        else:
            # Otherwise the text comes from the editor, and the path, when there
            # is one, is what the loader treats as the importing file.
            self._session.load_text(self._editor.toPlainText(), self._path or "<buffer>")
        self._status.setText("выполняется")

    def _run_query(self) -> None:
        text = self._query_line.text().strip()
        if not text:
            return
        self._query_line.clear()
        if not text.startswith("?"):
            text = "?" + text
        self._session.run_query(text)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Открыть программу", "", "PrologD (*.pld);;Все файлы (*)")
        if path:
            self.open_path(path)

    def open_path(self, path: str) -> None:
        """Loads a file into the editor — and *only* into the editor.

        Opening must not run anything: `load` adds clauses to the live
        interpreter (that is what `ИМПОРТ` needs), so opening a file into a
        session that already ran something put a second copy of the program in
        it.  With duplicated recursive clauses every solution multiplies, which
        is why opening the factorial example twice looked like an endless loop.
        Running is F5.
        """
        try:
            # `utf-8-sig` drops a byte-order mark, which the lexer also ignores;
            # otherwise the first line would start with an invisible character.
            with open(path, encoding="utf-8-sig") as stream:
                text = stream.read()
        except (OSError, UnicodeDecodeError) as error:
            self._append_output(f"*** не могу открыть {path}: {error}\n")
            return
        self._editor.setPlainText(text)
        self._editor.document().setModified(False)
        self._path = path
        self._update_title()
        self._status.setText(f"открыт {path}")

    def stop_program(self) -> None:
        self._session.stop()
        self._status.setText("остановлено")
        self._append_output("--- остановлено ---\n")

    def clear_output(self) -> None:
        self._output.clear()

    def _update_title(self) -> None:
        name = pathlib.Path(self._path).name if self._path else "Без имени"
        marker = "*" if self._editor.document().isModified() else ""
        self.setWindowTitle(f"{marker}{name} — PrologD")

    # -- accessors for the actions and the tests ---------------------------
    # task_25 replaces these with a document model (tabs, modified flag, save).
    @property
    def session(self) -> PrologSession:
        """The interpreter session; the window owns exactly one until task_25."""
        return self._session

    def editor_text(self) -> str:
        return self._editor.toPlainText()

    def output_text(self) -> str:
        return self._output.toPlainText()

    def current_path(self) -> str | None:
        return self._path

    # -- session events ----------------------------------------------------
    def _on_ready(self, version: str) -> None:
        self._status.setText(f"PrologD {version} готов")
        self._update_title()

    def _on_result(self, found: bool) -> None:
        if not found:
            self._append_output("НЕТ\n")

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
