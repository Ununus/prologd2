"""Main window: a program editor, a query line and an output pane."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
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

        self._build_ui()
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
        self._add_action(toolbar, "Запустить", self._run_program, "Ctrl+R")
        self._add_action(toolbar, "Открыть…", self._open_file, "Ctrl+O")
        self._add_action(toolbar, "Остановить", self._stop, "Ctrl+.")
        self._add_action(toolbar, "Очистить вывод", self._clear_output, "Ctrl+L")

        self._status = QLabel("запуск…")
        self.statusBar().addWidget(self._status)

    def _add_action(self, toolbar: QToolBar, title: str, slot, shortcut: str) -> None:
        action = QAction(title, self)
        action.setShortcut(shortcut)
        action.triggered.connect(slot)
        toolbar.addAction(action)

    # -- actions -----------------------------------------------------------
    def _run_program(self) -> None:
        self._append_output("--- загрузка программы ---\n")
        self._session.load_text(self._editor.toPlainText())

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
        if not path:
            return
        with open(path, encoding="utf-8") as stream:
            self._editor.setPlainText(stream.read())
        self._session.load_file(path)

    def _stop(self) -> None:
        self._session.stop()
        self._status.setText("остановлено")
        self._append_output("--- остановлено ---\n")
        self._session.start()

    def _clear_output(self) -> None:
        self._output.clear()

    # -- session events ----------------------------------------------------
    def _on_ready(self, version: str) -> None:
        self._status.setText(f"PrologD {version} готов")

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
