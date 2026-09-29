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

from dataclasses import dataclass

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QWidget

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
TRACE = "trace"

#: The colours of the kinds that have one.
KIND_COLORS = {
    ECHO: theme.Theme().query,  # the query blue: our echo of an answer
    NOTE: "#555555",  # our own markers (`--- загрузка программы ---`)
    ERROR: "#a00000",  # diagnostics
    TRACE: "#777777",  # the trace stream (task_28)
}

#: How many lines the pane keeps.  A runaway `ВЫВОД` must not eat the machine.
DEFAULT_LINE_LIMIT = 50_000

#: The first line of a pane whose beginning has been dropped.
TRUNCATED_MARK = "*** вывод усечён: показаны только последние строки ***"


@dataclass(frozen=True)
class Line:
    """One finished line, with the kind of text it came from."""

    text: str
    kind: str = OUTPUT


class LineBuffer:
    """Turns chunks of text into lines, holding the unfinished tail.

    Qt-free on purpose: this is the part with the classic defect in it — a partial
    line that reaches the pane and is never completed — so it is the part that is
    tested directly.
    """

    def __init__(self) -> None:
        self._tail = ""
        self._kind = OUTPUT

    def feed(self, text: str, kind: str = OUTPUT) -> list[Line]:
        """The complete lines of `text`; what follows the last newline waits."""
        lines: list[Line] = []
        if self._tail and kind != self._kind:
            # The kind changed in the middle of a line — a note arriving while the
            # program left half a line behind.  That half is a line of its own, or
            # it would be painted with the note's colour.
            lines.append(Line(self._tail, self._kind))
            self._tail = ""
        rest = self._tail + text if self._tail else text
        self._tail = ""
        parts = rest.split("\n")
        self._tail = parts.pop()
        self._kind = kind
        lines.extend(Line(part, kind) for part in parts)
        return lines

    def flush(self) -> list[Line]:
        """The held tail as a line — for the end of a run that stopped mid-line."""
        if not self._tail:
            return []
        line = Line(self._tail, self._kind)
        self._tail = ""
        return [line]

    def pending(self) -> str:
        """What is waiting for a newline (the window's notes ask this)."""
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
        """Adds whatever of `text` is a finished line, colouring it by `kind`."""
        lines = self._buffer.feed(text, kind)
        if lines:
            self.append_lines(lines)

    def flush(self) -> None:
        """Writes a held partial line; the run is over and it will not be finished."""
        lines = self._buffer.flush()
        if lines:
            self.append_lines(lines)

    def append_lines(self, lines: list[Line]) -> None:
        """Inserts finished lines in one pass.

        A cursor of the *document* rather than the pane's own: the user's caret and
        selection have nothing to do with the output, and moving them would take
        the selection away while a program is running.
        """
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for line in lines:
            cursor.insertText(line.text + "\n", self._formats.get(line.kind, self._plain))
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
