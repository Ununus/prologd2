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

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QTextCharFormat,
    QTextCursor,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import answers, assets, documents, theme
from .editor import ZoomablePlainTextEdit
from .settings import MAXIMUM_FONT_SIZE, MINIMUM_FONT_SIZE

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

#: The tabs of the output panel (task_50): a pane per tab, the input queue with
#: the request console under it in the last one.  The order is the order they are
#: built in — «Проблемы» first, because a diagnostic is the thing the user is
#: looking for when a run stops.
TAB_PROBLEMS = "problems"
TAB_OUTPUT = "output"
TAB_SYSTEM = "system"
TAB_INPUT = "input"
#: The answer table (task_59) — the *fifth* tab, and the only one that is not a
#: view of the text: it is built from the answer of a single goal, so no `kind`
#: belongs to it and `KIND_TAB` has no entry for it.
TAB_TABLE = "table"

#: What a kind belongs to.  The program's own output, the echo of an answer and
#: the trace are all *the output*; the window's notes are system talk; the
#: diagnostics are problems.  `OUTPUT` deliberately has no entry of its own — it
#: falls back to the Вывод tab.
KIND_TAB: dict[str, str] = {
    ECHO: TAB_OUTPUT,
    TRACE: TAB_OUTPUT,
    NOTE: TAB_SYSTEM,
    ERROR: TAB_PROBLEMS,
    WARNING: TAB_PROBLEMS,
}

#: The colours of the kinds that have one, from a theme palette (task_29).  The
#: pane is given a palette, so the dark theme's colours reach it the same way the
#: editor's do; `KIND_COLORS` is only the light default.
#:
#: `output` has no colour on purpose: it is the data being read, and it takes the
#: text colour of the widget palette.
def kind_colors(palette: theme.Palette) -> dict[str, str]:
    return {
        ECHO: palette.echo,  # our echo of an answer: the query colour
        NOTE: palette.note,  # our own markers (`--- загрузка программы ---`)
        ERROR: palette.error,  # diagnostics
        WARNING: palette.warning,  # a warning: the same pane, amber instead of red
        TRACE: palette.trace,  # the trace stream (task_28)
    }


KIND_COLORS = kind_colors(theme.LIGHT)

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
        palette: theme.Palette | None = None,
    ) -> None:
        super().__init__(parent, font_family=font_family, font_size=font_size)
        self.setReadOnly(True)
        self._buffer = LineBuffer()
        self._line_limit = max(100, int(line_limit))
        self._palette = palette or theme.LIGHT
        self._colors = kind_colors(self._palette)
        self._formats = {kind: self._format(color) for kind, color in self._colors.items()}
        self._plain = QTextCharFormat()
        self._truncated = False
        #: The kind of every line in the document, in order (`set_palette` needs
        #: them to re-colour the history when the theme changes).
        self._kinds: list[str] = []
        #: True while the view follows the end of the output.
        self._following = True
        #: The preference behind it (task_29's «Следить за выводом»): off, the
        #: pane stays where the reader is even when that is the end.
        self._follow = True
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

        A complete piece goes in with its newline in one `insertText`: two insertions
        per line is twice the work, and a trace of a deep recursion is hundreds of
        thousands of lines (task_49 — that traffic is what froze the window).
        """
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for piece in pieces:
            fmt = self._formats.get(piece.kind, self._plain)
            if piece.complete:
                if piece.text:
                    cursor.insertText(piece.text + "\n", fmt)
                else:
                    cursor.insertText("\n", fmt)
                # The newline ended the line the text went into; Qt opened a block
                # behind it, and that one gets its kind when its text arrives.
                self._record_kind(self.document().blockCount() - 2, piece.kind)
            elif piece.text:
                cursor.insertText(piece.text, fmt)
                self._record_kind(self.document().blockCount() - 1, piece.kind)
        self._trim()
        if self._following and self._follow:
            bar = self.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _record_kind(self, index: int, kind: str) -> None:
        """Remembers the kind of block `index`, growing the list up to it."""
        while len(self._kinds) <= index:
            self._kinds.append(kind)
        self._kinds[index] = kind

    def reset(self) -> None:
        """Empties the pane; the tail and the truncation marker go with it."""
        self.clear()
        self._buffer.reset()
        self._kinds.clear()
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

    def set_line_limit(self, limit: int) -> None:
        """A new bound for the history (task_29's dialog).  Applied at once: a
        smaller limit trims now, not on the next run, or the pane would keep more
        than it claims to."""
        self._line_limit = max(100, int(limit))
        self._trim(force=True)

    def truncated(self) -> bool:
        """Whether the oldest output has been dropped."""
        return self._truncated

    def kind_colors(self) -> dict[str, str]:
        """The colours in force, by kind (a theme may have replaced them)."""
        return dict(self._colors)

    def set_palette(self, palette: theme.Palette) -> None:
        """Re-colours the pane, the history included (task_29's dark theme).

        The kinds of the lines are kept as they are written (`_kinds`), which is
        what makes this possible: without them the text already in the pane would
        keep the colours of the theme it was written in — dark red on a dark page,
        which is the half-done dark mode this design is meant to avoid.
        """
        self._palette = palette
        self._colors = kind_colors(palette)
        self._formats = {kind: self._format(color) for kind, color in self._colors.items()}
        document = self.document()
        for index, kind in enumerate(self._kinds):
            block = document.findBlockByNumber(index)
            if not block.isValid():
                break
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.setCharFormat(self._formats.get(kind, self._plain))

    def following(self) -> bool:
        """Whether the view is at the end of the output."""
        return self._following

    def set_follow_output(self, enabled: bool) -> None:
        """The «Следить за выводом» switch (task_29).

        It does not move the view: turning it back on while the reader is at the
        end changes nothing, and turning it off leaves the text where it is.
        """
        self._follow = bool(enabled)

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

    def _trim(self, *, force: bool = False) -> None:
        """Drops the oldest lines in one edit, keeping the marker first.

        In *bulks*, not one line per append: removing text from the front of a
        `QTextDocument` costs about the same whatever is removed, so dropping one
        line per appended line is quadratic — which is exactly what a traced deep
        recursion does to this pane, and what froze the window (task_49: 200 000
        lines took 22 s one line at a time, and about 2 s in bulk).  The history
        may therefore hold up to one chunk more than its limit, and `force` is for
        the two callers that must not wait for the next chunk: a new limit, and the
        pane being asked what it holds.
        """
        document = self.document()
        excess = document.blockCount() - self._line_limit
        if excess > 0 and (force or excess >= self._trim_step()):
            self._truncated = True
            block = document.findBlockByNumber(excess)
            cut = QTextCursor(document)
            cut.setPosition(0)
            cut.setPosition(block.position(), QTextCursor.MoveMode.KeepAnchor)
            cut.removeSelectedText()
            del self._kinds[:excess]
        self._ensure_marker()

    def _trim_step(self) -> int:
        """How many lines one trim may drop (a tenth of the history, at least one)."""
        return max(1, self._line_limit // 10)

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
        self._kinds.insert(0, ERROR)


#: What a request is called in the console and in the status bar.
INPUT_PROMPTS = {
    "token": "Слово",
    # «Строки», not «Строка»: an answer is a piece of the program's input stream,
    # so two lines in the field are two answers to two reads (task_54).
    "line": "Строки",
    "codepoint": "Символ",
}

#: A yellow frame round the answer while the program is waiting for it.  The
#: console appears and disappears, so the colour is what actually catches the eye.
ARMED_BORDER = "QLineEdit, QPlainTextEdit { border: 2px solid #e0b400; }"


#: The columns of the problems table: what kind of diagnostic it is, where it
#: points and what it says.
PROBLEM_COLUMNS = ("Тип", "Место", "Сообщение")

#: How many diagnostics the table keeps.  A program that warns in a loop can
#: produce thousands, and the tab is read rather than scrolled for ever.
DEFAULT_PROBLEM_LIMIT = 2_000

#: The column that takes the rest of the width and carries the wrapping text.
PROBLEM_MESSAGE_COLUMN = 2


class ZoomableTable(QTableWidget):
    """The zoom the other panes have, shared by the window's two tables.

    «Таблица ответа» (`TablePane`) and «Проблемы» (`ProblemsPane`) are both
    `QTableWidget`s read next to the log, so both follow the output's font size and
    take `Ctrl`+wheel through one code path — the window's zoom handling stays a
    single road whether a table or a text pane was resized.  The subclass decides
    how its rows follow a new font (`_relayout_for_font`): the answer table keeps
    one default row height for its possibly thousands of solutions, the problems
    table re-measures its wrapping rows.
    """

    #: Emitted after `Ctrl`+wheel; carries the new point size.
    zoomChanged = Signal(float)

    @property
    def font_size(self) -> float:
        return self.font().pointSizeF()

    def set_font_size(self, size: float) -> None:
        clamped = min(MAXIMUM_FONT_SIZE, max(MINIMUM_FONT_SIZE, float(size)))
        if abs(clamped - self.font_size) < 1e-6:
            return
        font = QFont(self._family)
        font.setPointSizeF(clamped)
        self.setFont(font)
        self.horizontalHeader().setFont(font)
        self._relayout_for_font(font)
        self.zoomChanged.emit(clamped)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt spelling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.set_font_size(self.font_size + (1 if delta > 0 else -1))
            event.accept()
            return
        super().wheelEvent(event)

    def _relayout_for_font(self, font: QFont) -> None:
        """How the rows follow a new font — the subclass's own rule."""
        raise NotImplementedError


class ProblemsPane(ZoomableTable):
    """The diagnostics of a run as a grid: type, place, message (part 88).

    A diagnostic is *data*: the protocol sends its kind, its severity, its message
    and a position as fields of their own, so it is shown as data.  One row per
    diagnostic, and the row remembers the `Position` it came with — which is what
    makes a double-click able to take the editor to that line instead of leaving the
    reader to pick a path out of the message.

    A long message wraps inside its row: the tab is where a failure is *read*, and
    a message read through a horizontal scrollbar is not read at all.
    """

    #: Emitted when a row is activated — double-clicked or chosen with the
    #: keyboard; carries that row's `Position` (`None` when it had none).
    problemActivated = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
        line_limit: int = DEFAULT_PROBLEM_LIMIT,
        palette: theme.Palette | None = None,
    ) -> None:
        super().__init__(parent)
        # Constructed first: a resize event can arrive before the rest of this
        # method has run, and `resizeEvent` starts this timer.
        self._rewrap = QTimer(self)
        self._rewrap.setSingleShot(True)
        self._rewrap.setInterval(120)
        self._rewrap.timeout.connect(self.resizeRowsToContents)
        self._family = font_family
        self._limit = max(10, int(line_limit))
        self._palette = palette or theme.LIGHT
        self._colors = kind_colors(self._palette)
        #: Every diagnostic in order: `(kind, severity, message, position)`.
        self._problems: list[tuple[str, str, str, object]] = []
        self.setColumnCount(len(PROBLEM_COLUMNS))
        self.setHorizontalHeaderLabels(list(PROBLEM_COLUMNS))
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(False)
        self.setShowGrid(False)
        # Wrapping is the whole point of a row per diagnostic: the message column
        # takes the free width and the row grows to whatever the message needs.
        self.setWordWrap(True)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(PROBLEM_MESSAGE_COLUMN, QHeaderView.ResizeMode.Stretch)
        # Re-wrapping costs a layout pass per row, so it is done once the resizing
        # stops rather than at every intermediate width: the eye follows the drag,
        # and the rows catch up when it is let go.
        header.sectionResized.connect(lambda *_args: self._rewrap.start())
        # A double-click and the keyboard's own activation are the same act here.
        self.itemDoubleClicked.connect(self._on_activated)
        self.itemActivated.connect(self._on_activated)
        self.set_font_size(font_size)

    # -- what the window drives --------------------------------------------
    def add_problem(self, kind: str, severity: str, message: str, position=None) -> None:
        """Adds one diagnostic — the row and what the row points at.

        `severity` is `"warning"` or `"error"`, as the protocol sends it; `position`
        is the `Position` of the event, when it has one.  The kind of an *error* is
        the interpreter's own word for it (`parse`, `runtime`, `protocol`), which is
        what the reader sees in the type column: a name the front-end invented would
        say less.
        """
        self._problems.append((kind, severity, message, position))
        dropped = len(self._problems) - self._limit
        if dropped > 0:
            # The oldest go, like the output pane's history: a bounded tab is worth
            # more than a complete one nobody can scroll to the end of.
            del self._problems[:dropped]
            self._reload()
            return
        self._append_row(len(self._problems) - 1)

    def add_text(self, text: str, kind: str = ERROR) -> None:
        """Adds diagnostics that arrived as text, one row per line.

        The window feeds its own log by kind, and only the two diagnostic kinds
        land in this tab.  Those rows have no place to go to — there is no position
        in a line of text — which is why the real path is `add_problem`.
        """
        for line in text.splitlines():
            if line:
                self.add_problem(kind, "", line, None)

    def clear_problems(self) -> None:
        """Empties the table: a new run starts with its own diagnostics.

        *Not* named `reset`: that is a virtual method of `QTableView` — Qt calls it
        whenever the model is reset — and the obvious body (`clearContents()`) calls
        back into it, so the two spin for ever.  `setRowCount(0)` is the same
        emptying, and it is what the widget itself does.
        """
        self._problems.clear()
        self.setRowCount(0)

    def set_line_limit(self, limit: int) -> None:
        """A new bound for the history (the settings dialog's row)."""
        self._limit = max(10, int(limit))
        dropped = len(self._problems) - self._limit
        if dropped > 0:
            del self._problems[:dropped]
            self._reload()

    def set_palette(self, palette: theme.Palette) -> None:
        """Re-colours the whole history: the theme reaches rows already there."""
        self._palette = palette
        self._colors = kind_colors(palette)
        self._reload()

    def kind_colors(self) -> dict[str, str]:
        """The colour per kind, as the theme has it now."""
        return dict(self._colors)

    def _relayout_for_font(self, font: QFont) -> None:
        """The rows wrap, so their height follows the font row by row."""
        self.resizeRowsToContents()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """A wider pane means fewer wrapped lines, so the rows are measured again."""
        super().resizeEvent(event)
        self._rewrap.start()

    # -- what the window and the tests read --------------------------------
    def problem_count(self) -> int:
        """How many diagnostics are showing — the count in the tab's title."""
        return len(self._problems)

    def severity_counts(self) -> tuple[int, int]:
        """Errors and warnings, in that order."""
        errors = sum(1 for _kind, severity, _text, _pos in self._problems if severity != "warning")
        warnings = len(self._problems) - errors
        return errors, warnings

    def problems(self) -> list[tuple[str, str, str, object]]:
        """The rows as records (what a test reads instead of the widget)."""
        return list(self._problems)

    def text(self) -> str:
        """The table as the log the pane used to be: one line per diagnostic.

        `*** kind: file:line:column: message` — the shape the window's own log has
        always used, with the warnings named «предупреждение» rather than by the
        kind they arrived with.  `problems_text()` and the tests read this, so the
        rows and the log say the same thing.
        """
        return "".join(self._line(record) + "\n" for record in self._problems)

    # -- the rows ----------------------------------------------------------
    @staticmethod
    def _line(record: tuple[str, str, str, object]) -> str:
        kind, severity, message, position = record
        where = position.where() if position is not None else ""
        name = "предупреждение" if severity == "warning" else kind
        return f"*** {name}: {where + ': ' if where else ''}{message}"

    def place_text(self, position) -> str:
        """Where a diagnostic points, as the column shows it.

        The window's own shortening (`…/файл.pld`), with the line and column after
        it: the file name is what a reader recognises, and the path in front of it
        is the part that pushes the message off the screen.  The whole path travels
        in the cell's tooltip.
        """
        if position is None or not position.file:
            return ""
        place = documents.short_path(position.file, parts=1)
        if not position.line:
            return place
        return f"{place}:{position.line}:{position.column}"

    def _append_row(self, index: int) -> None:
        kind, severity, message, position = self._problems[index]
        row = self.rowCount()
        self.insertRow(row)
        color = self._colors.get(WARNING if severity == "warning" else ERROR)
        name = "предупреждение" if severity == "warning" else kind
        values = (name, self.place_text(position), message)
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if color:
                item.setForeground(QColor(color))
            if column == 0:
                # Which record the row stands for: the table is the view, and the
                # record is what a jump needs.
                item.setData(Qt.ItemDataRole.UserRole, index)
            self.setItem(row, column, item)
        if position is not None and position.file:
            tip = position.where()
            for column in range(len(PROBLEM_COLUMNS)):
                found = self.item(row, column)
                if found is not None:
                    found.setToolTip(tip)
        self.resizeRowToContents(row)

    def _reload(self) -> None:
        """Rebuilds every row: the history shrank, or the theme changed.

        The rows are dropped with `setRowCount(0)`, which takes their items with
        them — `clearContents()` would be the same, except that it calls `reset()`
        back (see `clear_problems`).
        """
        self.setRowCount(0)
        for index in range(len(self._problems)):
            self._append_row(index)

    def _on_activated(self, item: QTableWidgetItem) -> None:
        first = self.item(item.row(), 0)
        if first is None:
            return
        record = self._problems[first.data(Qt.ItemDataRole.UserRole)]
        self.problemActivated.emit(record[3])


class AnswerEdit(QPlainTextEdit):
    """The text area for a `line` request, where `Ctrl+Enter` sends.

    Plain `Enter` is a newline here on purpose: an answer may be several lines,
    and since task_54 they are several lines *of the program's input* — a `\n`
    inside the field separates two reads, exactly as it would in a file.  A
    control that sent on the first `Enter` could not type one.
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
        # The console is a strip, not a pane: it never grows past its contents,
        # so it stays the height of one field however the editor column shares
        # space (task_50 — it used to stretch and centre its line in the middle
        # of a tall empty strip).
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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
        # The text area of a `line` request keeps a few lines, not the whole
        # default of a `QPlainTextEdit` (~192 px) — the console stays minimal.
        self._text.setFixedHeight(QFontMetrics(font).lineSpacing() * 4 + 8)


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

#: What the strip's «где» means; the whole `file:line:column` is put under it
#: while a point is shown, since the label itself carries only the place.
WHERE_TOOLTIP = "Где эта цель стоит в файле"


def _tool_button(icon_name: str, tooltip: str, signal) -> QPushButton:
    """A picture button for the step strip, with its words in the tooltip.

    The strip lives in the editor's monospace world, where three text buttons read
    as a paragraph of prose in the middle of a program — and the toolbar already
    has the pictures (`execution-execute`, `execution-step-into`,
    `execution-abort`).  A checkout without `assets/` falls back to the first word
    of the tooltip rather than to an empty square.
    """
    button = QPushButton()
    picture = assets.icon(icon_name)
    if picture is None or picture.isNull():
        button.setText(tooltip.split(" (")[0].split(" —")[0])
    else:
        button.setIcon(picture)
        button.setIconSize(QSize(16, 16))
    button.setToolTip(tooltip)
    button.setAutoDefault(False)
    button.clicked.connect(signal)
    return button


class ElidedLabel(QLabel):
    """A one-line label that says so when it is too narrow for its text.

    The step strip's «где» carries a place in a file.  At full length the path ran
    up against the buttons beside it, and a narrower window cut it mid-word with
    nothing to show that it had been cut.  Painting is what shortens: `text()` —
    and so the tooltip and the accessors — stays whole, and what is painted keeps
    the *end* of the text, because the end of a place in a file (the file's own
    name, then the line and the column) is the part being read.  Qt's own
    `elidedText(…, ElideMiddle, …)` was measured first and reads badly on a path:
    at a third of the width the middle of `…\\examples\\problems\\hanoi.pld:2:1` is
    all that is left — the file's name and the line are gone, which is exactly the
    part being read.
    """

    def display_text(self) -> str:
        """What is painted: the text, or as much of its end as fits, after «…»."""
        text = self.text()
        width = self.contentsRect().width()
        if width <= 0:
            return text
        metrics = QFontMetrics(self.font())
        if metrics.horizontalAdvance(text) <= width:
            return text
        if metrics.horizontalAdvance("…") > width:
            return ""
        for cut in range(len(text)):
            candidate = "…" + text[cut:]
            if metrics.horizontalAdvance(candidate) <= width:
                return candidate
        return "…"

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's own spelling
        shown = self.display_text()
        if shown == self.text():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.contentsRect(), self.alignment().value, shown)


def step_where_text(position) -> str:
    """`file:line:column` for the strip: the file cut to its last two parts.

    A stepped run on an *opened* file reports the whole path, and the whole path
    in the strip's single row ran straight up against its buttons; the last two
    parts (…\\examples\\hanoi.pld:2:1) say the same thing in a fifth of the room,
    and the full text stays in the tooltip.
    """
    if position is None or not position.file:
        return ""
    file = documents.short_path(position.file)
    return f"{file}:{position.line}:{position.column}"


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
    #: «Шаг»: one point further in — the panel's own `F10`.
    stepped = Signal()
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
        self._where = ElidedLabel()
        # A place in a file is data: a path with `<` in it is not markup.
        self._where.setTextFormat(Qt.TextFormat.PlainText)
        self._where.setToolTip(WHERE_TOOLTIP)
        self._stack = QLabel("")
        self._stack.setTextFormat(Qt.TextFormat.PlainText)
        self._resume = _tool_button(
            "execution-execute", "Продолжить (F5) — до конца без остановок", self.resumed
        )
        self._step_button = _tool_button(
            "execution-step-into", "Шаг (F10) — на одну точку дальше", self.stepped
        )
        self._stop_button = _tool_button(
            "execution-abort", "Стоп — закончить прогон", self.stopped
        )

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._action)
        row.addWidget(self._goal, 1)
        row.addWidget(self._depth)
        row.addWidget(self._where)
        row.addWidget(self._resume)
        row.addWidget(self._step_button)
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
        full = point.position.where() if point.position else ""
        self._where.setText(step_where_text(point.position))
        self._where.setToolTip(f"{WHERE_TOOLTIP}\n{full}" if full else WHERE_TOOLTIP)
        self._stack.setText(self._stack_text(stack))
        self._stack.setToolTip(self._stack.text())
        self.setVisible(True)

    def idle(self) -> None:
        """Nothing is being stepped through: no room taken, nothing to show."""
        self._action.clear()
        self._goal.clear()
        self._depth.clear()
        self._where.clear()
        self._where.setToolTip(WHERE_TOOLTIP)
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

    def where_display_text(self) -> str:
        """What the strip actually paints: the text, or its middle shortened."""
        return self._where.display_text()

    def stack_text(self) -> str:
        return self._stack.text()

    def resume_button(self) -> QPushButton:
        return self._resume

    def step_button(self) -> QPushButton:
        return self._step_button

    def stop_button(self) -> QPushButton:
        return self._stop_button

    def set_font_size(self, size: float) -> None:
        """One font for the whole strip — the editor's own.

        The goal and the stack are code and were monospace from the start; the
        labels beside them («вызов», «глубина 0», the position) were not, so the
        strip mixed two fonts at two sizes, and zooming moved only half of it.
        """
        font = QFont(self._family)
        font.setPointSizeF(float(size))
        for label in (self._action, self._goal, self._depth, self._where, self._stack):
            label.setFont(font)


#: The header of the one column a word-answer is shown in.  `ДА` and `НЕТ` are the
#: answer of a query without variables, and a table needs a column: naming it
#: «Ответ» says what the single cell is, instead of leaving a bare box (task_59).
VERDICT_COLUMN = "Ответ"

#: How wide a column may grow when it is fitted to its content.  A value is
#: printed as the interpreter printed it and may be long; the full text is in
#: «Выводе», so the table elides what does not fit rather than scrolling sideways
#: past the end of the answer.
MAX_COLUMN_WIDTH = 480


class TablePane(ZoomableTable):
    """The answer of one goal as a grid: variables are columns, solutions rows.

    Only a *single* goal is tabulated (task_59): a whole run answers all of its
    `?`-questions into one stream of text with no separator, so nothing could say
    where one question's answer ends — `answers.py` has the rules and the reason.

    The pane is a `QTableWidget` with the three things the other panes have: the
    output's font size (the answer is read next to the log it came from), the
    `zoomChanged` signal and `Ctrl`+wheel, so the window's zoom handling stays one
    code path.  Values are text, exactly as printed: nothing is parsed out of them.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
    ) -> None:
        super().__init__(parent)
        self._family = font_family
        #: The colour of the lines between the cells, from the theme (`set_palette`).
        #: Drawn by `paintEvent`: Qt's own grid follows no palette role we could set
        #: (its colour is the style's, and on the dark page it came out one unit
        #: away from the background — no line at all), so the pane draws them.
        self._grid = theme.LIGHT.grid
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setShowGrid(False)
        # Solutions are in the order the interpreter found them, so the row header
        # is hidden and the tab's title carries the count.
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setMaximumSectionSize(MAX_COLUMN_WIDTH)
        self.set_answer(None)
        self.set_font_size(font_size)

    # -- what the window drives --------------------------------------------
    def set_answer(self, answer: answers.Answer | None) -> None:
        """Shows one answer: its columns and rows, or one word, or nothing.

        `None` (and an empty answer) empties the table: a new run starts with its
        own output, and the table is a view of the last answer, not a history.
        """
        self.clear()
        if answer is None or answer.is_empty():
            self.setColumnCount(0)
            self.setRowCount(0)
            return
        if answer.rows:
            titles = answer.columns
            rows = answer.rows
        else:
            # `ДА`/`НЕТ`: the word *is* the answer, so it gets one cell.
            titles = (VERDICT_COLUMN,)
            rows = ((answer.verdict,),)
        self.setColumnCount(len(titles))
        self.setHorizontalHeaderLabels(list(titles))
        self.setRowCount(len(rows))
        for number, row in enumerate(rows):
            for column, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.setItem(number, column, item)
        self.resizeColumnsToContents()

    def solution_count(self) -> int:
        """How many rows are showing — the count in the tab's title."""
        return self.rowCount()

    def set_palette(self, palette: theme.Palette) -> None:
        """Takes the grid's colour from the theme (task_59).

        The table is chrome around the answer, so the line is a shade of the page
        rather than a colour of its own: `theme.Palette.grid`.  It is *drawn* (see
        `paintEvent`) because Qt's own grid does not follow the palette — its colour
        comes from the style, and on the dark page it was `#1f1f20` on `#1e1e1e`,
        which is a table whose columns are told apart by whitespace alone.
        """
        self._grid = palette.grid
        self.viewport().update()

    def column_titles(self) -> list[str]:
        """The names over the columns, left to right (what a test reads)."""
        return [
            self.horizontalHeaderItem(column).text()
            for column in range(self.columnCount())
            if self.horizontalHeaderItem(column) is not None
        ]

    def cells(self) -> list[list[str]]:
        """The table as plain lists of strings (what a test reads)."""
        return [
            [
                item.text() if (item := self.item(row, column)) is not None else ""
                for column in range(self.columnCount())
            ]
            for row in range(self.rowCount())
        ]

    # -- font and zoom ------------------------------------------------------
    def _relayout_for_font(self, font: QFont) -> None:
        # Row heights follow the font through one default size, not through a walk
        # over every row: a runaway `?цель(X)` may answer with thousands of them.
        self.verticalHeader().setDefaultSectionSize(QFontMetrics(font).lineSpacing() + 6)
        self.resizeColumnsToContents()

    # -- the lines between the cells ----------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """Draws the grid over the cells, in the theme's colour.

        The lines go only *between* cells: the right edge of the last column and the
        bottom of the last row are the end of the table, not a boundary, and the
        empty room beside a narrow table stays page-coloured.  Positions come from
        `visualRect` and `columnViewportPosition`, so a scrolled table stays right,
        and only the rows on screen are walked — an answer may have thousands.
        """
        super().paintEvent(event)
        rows = self.rowCount()
        columns = self.columnCount()
        if not rows or not columns:
            return
        painter = QPainter(self.viewport())
        painter.setPen(QPen(QColor(self._grid)))
        first = self.rowAt(0)
        last = self.rowAt(max(0, self.viewport().height() - 1))
        first = 0 if first < 0 else first
        last = rows - 1 if last < 0 else last
        right = self.columnViewportPosition(columns - 1) + self.columnWidth(columns - 1)
        right = min(right, self.viewport().width())
        bottom = self.visualRect(self.model().index(last, 0)).bottom()
        bottom = min(max(bottom, 0), self.viewport().height())
        for column in range(columns - 1):
            x = self.columnViewportPosition(column) + self.columnWidth(column)
            if 0 <= x <= self.viewport().width():
                painter.drawLine(x, 0, x, bottom)
        for row in range(first, last):
            y = self.visualRect(self.model().index(row, 0)).bottom()
            painter.drawLine(0, y, right, y)
        painter.end()

    # -- copying ------------------------------------------------------------
    def copy_selection(self) -> str:
        """The selected cells as text: `Tab` between columns, one line per row.

        That is the shape a spreadsheet wants, and it is why the table has a copy
        of its own at all: the window's `Ctrl+C` copies from *where the user is
        looking*, and a pane it does not know would have sent the command to the
        editor behind the table (task_59).
        """
        items = self.selectedItems()
        if not items:
            return ""
        rows = sorted({item.row() for item in items})
        columns = sorted({item.column() for item in items})
        lines = []
        for row in rows:
            cells = []
            for column in columns:
                item = self.item(row, column)
                cells.append(item.text() if item is not None and item.isSelected() else "")
            lines.append("\t".join(cells))
        return "\n".join(lines)
