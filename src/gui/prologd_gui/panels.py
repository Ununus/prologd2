"""The output pane: coloured lines, a bounded history, and a tail that survives.

`output` events carry arbitrary chunks of text, and a chunk need not end on a line
boundary — a program that prints with `ВЫВОД` and never uses `ПС` leaves the window
holding half a line.  Splitting a chunk into lines is where that goes wrong, so it
lives here in a Qt-free class that `test_output.py` hammers: everything up to the
last newline is a line, and the rest waits.

The pane itself is a `ZoomablePlainTextEdit` — the editor's font and zoom,
read-only, never wrapped (a log line cut in the middle cannot be read as data).  It
appends *lines* with a colour per kind, drops the oldest ones when the history grows
past a limit, and follows the end of the output unless the user has scrolled up to
read something.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .editor import ZoomablePlainTextEdit

#: What a line is, which is what decides its colour.  The window knows the kind —
#: it feeds program output, its own notes, the echo of an answer and the
#: interpreter's diagnostics along separate paths — so nothing is guessed from the
#: text.  `output` has no colour on purpose: it is the data being read.
OUTPUT = "output"
ECHO = "echo"
NOTE = "note"
ERROR = "error"
WARNING = "warning"
TRACE = "trace"

#: The colours of the kinds that have one.
KIND_COLORS = {
    ECHO: theme.Theme().query,  # the query blue: our echo of an answer
    NOTE: "#555555",  # our own markers (`--- загрузка программы ---`)
    ERROR: "#a00000",  # diagnostics
    WARNING: "#b35c00",  # a warning: the same pane, amber instead of red
    TRACE: "#777777",  # the trace stream (task_28)
}

#: How many lines the pane keeps.  A runaway `ВЫВОД` must not eat the machine.
DEFAULT_LINE_LIMIT = 50_000

#: The first line of a pane whose beginning has been dropped.
TRUNCATED_MARK = "*** вывод усечён: показаны только последние строки ***"


@dataclass(frozen=True)
class Piece:
    """A run of text of one kind, which may end in the middle of a line.

    `complete` says whether a newline ended it.  An incomplete piece is the line so
    far, and the rest of it may still arrive — it is written out all the same,
    because a program that prints a prompt with `ВЫВОД` and then waits for the
    answer leaves exactly such a line, and a prompt the user cannot see is not a
    prompt.
    """

    text: str
    kind: str = OUTPUT
    complete: bool = True


class LineBuffer:
    """Turns chunks of text into pieces, remembering the line that is still open.

    What it hands out is the *new* text of every chunk, never the line again: the
    pane has already written what it was given, and repeating it would double the
    prompt on screen.  A change of kind closes the open line — the bare newline of
    that piece — so a note of our own never becomes the tail of the program's.

    Qt-free on purpose: a line that goes missing in here is invisible on screen, so
    this is the part that is tested directly.
    """

    def __init__(self) -> None:
        self._tail = ""
        self._kind = OUTPUT

    def feed(self, text: str, kind: str = OUTPUT) -> list[Piece]:
        """The pieces of `text`, continuing the line the previous call left open."""
        pieces: list[Piece] = []
        if self._tail and kind != self._kind:
            # Close the half-line as it is: it belongs to the text it came from.
            pieces.append(Piece("", self._kind, complete=True))
            self._tail = ""
        parts = text.split("\n")
        tail = parts.pop()
        for part in parts:
            pieces.append(Piece(part, kind, complete=True))
        if tail or not pieces:
            pieces.append(Piece(tail, kind, complete=False))
        self._tail = tail
        self._kind = kind
        return pieces

    def flush(self) -> list[Piece]:
        """Ends the open line, if there is one; its text is on screen already."""
        if not self._tail:
            return []
        self._tail = ""
        return [Piece("", self._kind, complete=True)]

    def pending(self) -> str:
        """The text of the line that is still open (for tests and for notes)."""
        return self._tail

    def reset(self) -> None:
        self._tail = ""
        self._kind = OUTPUT


class OutputPane(ZoomablePlainTextEdit):
    """Read-only output: one colour per kind, a bounded history, auto-scroll."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
        line_limit: int = DEFAULT_LINE_LIMIT,
    ) -> None:
        super().__init__(parent, font_family=font_family, font_size=font_size)
        self.setReadOnly(True)
        self._buffer = LineBuffer()
        self._line_limit = max(100, int(line_limit))
        self._formats = {kind: self._format(color) for kind, color in KIND_COLORS.items()}
        self._plain = QTextCharFormat()
        self._truncated = False
        #: True while the view follows the end of the output.
        self._following = True
        self.verticalScrollBar().valueChanged.connect(self._on_scrolled)

    @staticmethod
    def _format(color: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        return fmt

    # -- text --------------------------------------------------------------
    def feed(self, text: str, kind: str = OUTPUT) -> None:
        """Writes whatever of `text` is new, colouring it by `kind`.

        An unfinished line is written at once: waiting for its newline is how the
        prompt of `ВЫВОД`/`ВВОДСИМВ` used to appear only after the answer arrived.
        """
        pieces = self._buffer.feed(text, kind)
        if pieces:
            self.append_pieces(pieces)

    def flush(self) -> None:
        """Ends the open line; the run is over and nothing will finish it."""
        pieces = self._buffer.flush()
        if pieces:
            self.append_pieces(pieces)

    def append_pieces(self, pieces: list[Piece]) -> None:
        """Inserts pieces in one pass.

        A cursor of the *document* rather than the pane's own: the user's caret and
        selection have nothing to do with the output, and moving them would take the
        selection away while a program is running.
        """
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for piece in pieces:
            fmt = self._formats.get(piece.kind, self._plain)
            if piece.text:
                cursor.insertText(piece.text, fmt)
            if piece.complete:
                cursor.insertText("\n", fmt)
        self._trim()
        if self._following:
            bar = self.verticalScrollBar()
            bar.setValue(bar.maximum())

    def reset(self) -> None:
        """Empties the pane; the tail and the truncation marker go with it."""
        self.clear()
        self._buffer.reset()
        self._truncated = False
        self._following = True

    def save_to(self, path: str) -> int:
        """Writes what the pane holds as UTF-8, and says how many characters went.

        The *text* is saved, not the colours: the point is a log of the run, and a
        log readable in any editor is worth more than one that keeps the markup.
        """
        text = self.toPlainText()
        pathlib.Path(path).write_text(text, encoding="utf-8")
        return len(text)

    # -- the history -------------------------------------------------------
    def line_limit(self) -> int:
        return self._line_limit

    def truncated(self) -> bool:
        """Whether the oldest output has been dropped."""
        return self._truncated

    def following(self) -> bool:
        """Whether the view is at the end of the output."""
        return self._following

    def pending(self) -> str:
        """The partial line the pane is holding."""
        return self._buffer.pending()

    def _on_scrolled(self, value: int) -> None:
        """Follows the end unless the user scrolled up to read something.

        Qt reports our own scroll to the bottom the same way, and that only sets
        following back to true — which is exactly what coming back to the bottom
        means, whoever did it.
        """
        self._following = value >= self.verticalScrollBar().maximum()

    def _trim(self) -> None:
        """Drops the oldest lines in one edit, keeping the marker first."""
        document = self.document()
        excess = document.blockCount() - self._line_limit
        if excess > 0:
            self._truncated = True
            block = document.findBlockByNumber(excess)
            cut = QTextCursor(document)
            cut.setPosition(0)
            cut.setPosition(block.position(), QTextCursor.MoveMode.KeepAnchor)
            cut.removeSelectedText()
        self._ensure_marker()

    def _ensure_marker(self) -> None:
        """Keeps «вывод усечён» the first line, so the pane never lies about its
        beginning."""
        if not self._truncated:
            return
        document = self.document()
        if document.firstBlock().text() == TRUNCATED_MARK:
            return
        cursor = QTextCursor(document)
        cursor.setPosition(0)
        cursor.insertText(TRUNCATED_MARK + "\n", self._formats[ERROR])


#: What a request is called in the console and in the status bar.
INPUT_PROMPTS = {
    "token": "Слово",
    "line": "Строка",
    "codepoint": "Символ",
}

#: A yellow frame round the answer while the program is waiting for it.  The
#: console appears and disappears, so the colour is what actually catches the eye.
ARMED_BORDER = "QLineEdit, QPlainTextEdit { border: 2px solid #e0b400; }"


class AnswerEdit(QPlainTextEdit):
    """The text area for a `line` request, where `Ctrl+Enter` sends.

    Plain `Enter` is a newline here on purpose: an answer to `ВВОДСТР` may be a
    sentence, and a control that sends on the first `Enter` cannot type one.
    """

    submitted = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class InputPane(QWidget):
    """The console under the output: what the program asks, and the answer.

    Idle until an `input_request` arrives; then the label says what is wanted (the
    kind decides which field appears — one line for a token or a code point, a text
    area for a line) and `Ctrl+Enter`, `Enter` in the one-line field, or
    «Отправить» sends the answer.  The window wraps it in `{"cmd":"input",…}`.

    The *prepared* answers under it stay: a program that reads a column of numbers
    is still best answered by typing the column once, and the console is what is
    left when those lines run out.
    """

    #: One answer, ready to send.
    submitted = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
    ) -> None:
        super().__init__(parent)
        self._family = font_family
        self._size = font_size
        self._kind = ""

        self._line = QLineEdit()
        self._line.returnPressed.connect(self.send)
        self._text = AnswerEdit()
        self._text.submitted.connect(self.send)
        self._text.setVisible(False)
        self._button = QPushButton("Отправить")
        self._button.clicked.connect(self.send)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._line, 1)
        row.addWidget(self._button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        layout.addLayout(row)
        layout.addWidget(self._text)
        self.set_font_size(font_size)
        self.idle()

    # -- what the window drives --------------------------------------------
    def ask(self, kind: str) -> None:
        """Arms the console for the request that is pending — and shows it.

        The strip is hidden while nothing is asked, because it would otherwise take
        room from the output for nothing; and the question is a *state*, so what it
        wants and which key sends it go into the placeholder.
        """
        self._kind = kind
        word = INPUT_PROMPTS.get(kind, "Значение")
        multiline = kind == "line"
        self._text.setVisible(multiline)
        self._line.setVisible(not multiline)
        self._text.setPlaceholderText(f"{word} — Ctrl+Enter")
        self._line.setPlaceholderText(f"{word} — Enter")
        self._line.clear()
        self._text.clear()
        self.setEnabled(True)
        self.setStyleSheet(ARMED_BORDER)
        self.show()
        (self._text if multiline else self._line).setFocus()

    def idle(self) -> None:
        """Nothing is being asked: no room taken, and nothing to answer."""
        self._kind = ""
        self._line.clear()
        self._text.clear()
        self.setEnabled(False)
        self.setStyleSheet("")
        self.hide()

    def kind(self) -> str:
        return self._kind

    def waiting(self) -> bool:
        return bool(self._kind)

    def answer(self) -> str:
        """What is typed now — a whole text area for a `line`, else one line."""
        if self._kind == "line":
            return self._text.toPlainText()
        return self._line.text()

    def send(self) -> None:
        """Hands the answer over; `Ctrl+Enter`, `Enter` or the button."""
        if not self._kind:
            return
        self.submitted.emit(self.answer())

    def set_font_size(self, size: float) -> None:
        """The console follows the editor's size, like the output above it."""
        self._size = float(size)
        font = self._line.font()
        font.setPointSizeF(self._size)
        self._line.setFont(font)
        self._text.setFont(font)


#: What a step point is called in the panel.  The words are the ones the
#: interpreter's own trace uses (`Согласуется с …`, `Успех`, `Переделка`,
#: `Неудача`), so the panel and the trace do not teach two vocabularies for one
#: thing.
STEP_TITLES = {
    "call": "вызов",
    "exit": "успех",
    "redo": "переделка",
    "fail": "неудача",
}

#: How many frames of the call stack the strip shows.  A deep recursion would
#: otherwise stretch the label — and the window — to the width of the screen.
STACK_FRAMES = 6


class StepPane(QWidget):
    """The strip that shows where a stepped run stands.

    What the solver just did, the goal it did it with and how deep it is, where
    that stands in the source, and the call stack.  The stack is *ours*: the
    interpreter reports one point at a time and an `exit` names no goal, so the
    window pushes what a `call` announced and pops it again on `exit`/`fail` —
    which is exactly what those two events mean.

    Hidden while nothing is being stepped through: like the console, an idle strip
    would take room from the program for nothing.
    """

    #: «Продолжить»: run on to the end without stopping at the next point.
    resumed = Signal()
    #: «Стоп»: end the query, like «Остановить» does.
    stopped = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
    ) -> None:
        super().__init__(parent)
        self._family = font_family
        self._action = QLabel("")
        self._action.setStyleSheet("font-weight: bold;")
        self._goal = QLabel("")
        # A goal is data: `#X+1#` must not be read as markup.
        self._goal.setTextFormat(Qt.TextFormat.PlainText)
        self._depth = QLabel("")
        self._where = QLabel("")
        self._where.setToolTip("Где эта цель стоит в файле")
        self._stack = QLabel("")
        self._stack.setTextFormat(Qt.TextFormat.PlainText)
        self._resume = QPushButton("Продолжить")
        self._resume.clicked.connect(self.resumed)
        self._stop_button = QPushButton("Стоп")
        self._stop_button.clicked.connect(self.stopped)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._action)
        row.addWidget(self._goal, 1)
        row.addWidget(self._depth)
        row.addWidget(self._where)
        row.addWidget(self._resume)
        row.addWidget(self._stop_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)
        layout.addLayout(row)
        layout.addWidget(self._stack)
        # The strip is as tall as its two lines: the same ceiling the find bar has.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.set_font_size(font_size)
        self.setVisible(False)

    # -- what the window drives --------------------------------------------
    def show_point(self, point, stack: list[str]) -> None:
        """Shows one step point of `protocol.StepPoint` shape, and the stack."""
        self._action.setText(STEP_TITLES.get(point.action, point.action))
        self._goal.setText(point.goal)
        self._depth.setText(f"глубина {point.depth}")
        self._where.setText(point.position.where() if point.position else "")
        self._stack.setText(self._stack_text(stack))
        self._stack.setToolTip(self._stack.text())
        self.setVisible(True)

    def idle(self) -> None:
        """Nothing is being stepped through: no room taken, nothing to show."""
        self._action.clear()
        self._goal.clear()
        self._depth.clear()
        self._where.clear()
        self._stack.clear()
        self.setVisible(False)

    @staticmethod
    def _stack_text(stack: list[str]) -> str:
        """The call stack, innermost last, with the head left out when it is long."""
        if not stack:
            return ""
        shown = stack[-STACK_FRAMES:]
        head = "… → " if len(stack) > len(shown) else ""
        return "стек: " + head + " → ".join(shown)

    def action_text(self) -> str:
        return self._action.text()

    def goal_text(self) -> str:
        return self._goal.text()

    def depth_text(self) -> str:
        return self._depth.text()

    def where_text(self) -> str:
        return self._where.text()

    def stack_text(self) -> str:
        return self._stack.text()

    def resume_button(self) -> QPushButton:
        return self._resume

    def stop_button(self) -> QPushButton:
        return self._stop_button

    def set_font_size(self, size: float) -> None:
        """The goal and the stack are code: the editor's own font."""
        font = QFont(self._family)
        font.setPointSizeF(float(size))
        self._goal.setFont(font)
        self._stack.setFont(font)
