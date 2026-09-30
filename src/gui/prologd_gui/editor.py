"""The code editor: line numbers, font zoom, block comment and indentation.

The highlighting lives in `highlighter.py` and the rules in `tokens.py`; this
module is about *editing*.  Everything here is deliberately small and does one
thing per method, because each of these behaviours is easy to get subtly wrong
and hard to notice — a line number area that stops repainting after a scroll, an
undo that takes two presses, an indent that eats a selection.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, QStringListModel, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPalette,
    QPolygon,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QWheelEvent,
)
from PySide6.QtWidgets import QCompleter, QLabel, QPlainTextEdit, QTextEdit, QWidget

from . import completion, queries, search, tokens
from .settings import DEFAULT_FONT_SIZE, MAXIMUM_FONT_SIZE, MINIMUM_FONT_SIZE

#: The comment character of the language: `%` to the end of the line.
COMMENT_PREFIX = "%"

#: Background of the line a diagnostic points at (task_28).
ERROR_BACKGROUND = "#ffd9d9"
ERROR_NUMBER = "#c00000"

#: Backgrounds of the search bar's matches: all of them, and the one the caret is on.
SEARCH_MATCH = "#ffe9a8"
SEARCH_CURRENT = "#ffc14d"

#: The line a *step* is on: the same idea as the error line, in a neutral colour,
#: because where a run stands is information and not a problem.
TRACE_BACKGROUND = "#d8e6f7"
TRACE_NUMBER = "#1b4f86"

#: Background of the other places the selected word appears, and the size of a
#: document worth scanning for them on every selection change.
OCCURRENCE_BACKGROUND = "#e8ecf5"
OCCURRENCE_LIMIT = 200_000

_MARGIN_BACKGROUND = "#f0f0f0"
_MARGIN_TEXT = "#8a8a8a"
_MARGIN_CURRENT = "#0a22d6"

#: The margin's icon column: a run marker for every line that is a question
#: (task_36), and the hit box of the click that runs it.  It sits left of the
#: numbers, so a marker is never hit while aiming at a digit, and a click on
#: the numbers themselves does nothing.
QUERY_MARKER_WIDTH = 14

#: The same blue as a query and as the current line's number: this is the
#: editor's colour for «a question, and something will run it».
_QUERY_MARKER = "#0a22d6"

_MIN_FONT_SIZE = MINIMUM_FONT_SIZE
_MAX_FONT_SIZE = MAXIMUM_FONT_SIZE

#: Endings after which the next line continues the same clause, so `Enter`
#: indents one more step.  A guess, not a parse: the real structure is the
#: parser's business (task_30 uses it for the formatter).
_CONTINUATION_ENDINGS = (",", ":-", "<-")

#: Keys that take the highlighted completion.  With `Shift` they keep their own
#: meaning: `Shift+Enter` is a newline and `Shift+Tab` an outdent.
_COMPLETION_ACCEPT_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab)

#: Keys that close the popup and still do their job in the editor — the caret
#: keeps its arrows inside the line.  `Up`/`Down` are deliberately not here:
#: they walk the list.
_POPUP_CLOSE_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End)


class LineNumberArea(QWidget):
    """The margin the editor paints line numbers and run markers into."""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor
        # The margin is clickable: the marker of a question runs it (task_36),
        # and the hand cursor says so before the click.
        self.setMouseTracking(True)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt spelling
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        self._editor.paint_line_numbers(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if event.button() == Qt.MouseButton.LeftButton:
            self._editor.margin_pressed(event.position().toPoint())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        over = self._editor.statement_at_margin_point(event.position().toPoint()) is not None
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor
        )


class ZoomablePlainTextEdit(QPlainTextEdit):
    """A text pane with the editor's font and zoom, and nothing else.

    The output pane is read-only: it needs no line numbers, no commands and no
    completion.  It does need the *same* font as the editor, because a run's
    answer is read next to the program that produced it — and one stored
    preference then covers both, so nothing the user sets is lost on restart.
    """

    #: Emitted after `Ctrl`+wheel or a zoom command; carries the new point size.
    zoomChanged = Signal(float)

    #: A file was dropped on the pane; the window opens it in a tab.
    fileDropped = Signal(str)

    #: The pane holding this editor was used: the commands act on it now.
    activated = Signal()

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        super().focusInEvent(event)
        self.activated.emit()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = DEFAULT_FONT_SIZE,
    ) -> None:
        super().__init__(parent)
        self.setFont(self._make_font(font_family, font_size))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(False)

    # -- the document ------------------------------------------------------
    def setDocument(self, document: QTextDocument) -> None:  # noqa: N802 - Qt spelling
        """Takes a document and gives it this pane's font.

        A `QTextDocument` carries its *own* default font, and the plain text
        layout measures every block with it — not with the widget's font.  A
        document made outside the editor therefore arrived with the application's
        font size, and the text stayed small until something forced a relayout
        (the first zoom, or a scroll).  Setting the font on the widget is not
        enough; the document has to be told as well.
        """
        super().setDocument(document)
        document.setDefaultFont(self.font())
        self.viewport().update()

    # -- drag and drop -----------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """A dropped file is for the window to open, not for the pane to paste.

        A `QPlainTextEdit` accepts a file drop and inserts the file's URL as text,
        so the event never reached the window: dropping a program on the editor
        pasted its path.  The pane now reports the drop and the window opens it.
        """
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if not paths:
            super().dropEvent(event)
            return
        for path in paths:
            self.fileDropped.emit(path)
        event.acceptProposedAction()

    # -- font and zoom ------------------------------------------------------
    @staticmethod
    def _make_font(family: str, size: float) -> QFont:
        font = QFont(family)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSizeF(size)
        return font

    @property
    def font_family(self) -> str:
        return self.font().family()

    @property
    def font_size(self) -> float:
        return self.font().pointSizeF()

    def set_font_family(self, family: str) -> None:
        font = self.font()
        font.setFamily(family)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self._font_changed()

    def set_font_size(self, size: float) -> None:
        clamped = min(_MAX_FONT_SIZE, max(_MIN_FONT_SIZE, float(size)))
        if abs(clamped - self.font_size) < 1e-6:
            return
        font = self.font()
        font.setPointSizeF(clamped)
        self.setFont(font)
        self._font_changed()
        self.zoomChanged.emit(clamped)

    def _font_changed(self) -> None:
        """The document measures with its own font, so it has to be told too."""
        self.document().setDefaultFont(self.font())

    def zoom_by(self, steps: float) -> None:
        self.set_font_size(self.font_size + steps)

    def reset_zoom(self) -> None:
        self.set_font_size(DEFAULT_FONT_SIZE)

    def set_wrap(self, enabled: bool) -> None:
        """Wraps long lines at the widget's width; `NoWrap` otherwise.

        The editor wants this for a long clause; the output never does, because a
        log line cut in the middle cannot be read as data.
        """
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt spelling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_by(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class CodeEditor(ZoomablePlainTextEdit):
    """A `QPlainTextEdit` with what writing PrologD needs."""

    #: A question's marker was clicked in the margin; carries the statement as
    #: written (from the `?` to the closing `.`), ready to run (task_36).
    queryRequested = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = DEFAULT_FONT_SIZE,
        line_numbers: bool = True,
        indent_character: str = "\t",
        indent_width: int = 1,
        completion: bool = True,
        auto_complete_after: int = 2,
    ) -> None:
        super().__init__(parent, font_family=font_family, font_size=font_size)
        self._indent_character = indent_character
        self._indent_width = max(1, indent_width)
        self._line_numbers = line_numbers
        self._error_line: int | None = None
        #: The line of the clause a stepped run is standing on (task_28).
        self._trace_line: int | None = None
        #: Where the search bar's matches are, and which one the caret sits on.
        self._search_ranges: list[tuple[int, int]] = []
        self._current_range: tuple[int, int] | None = None
        self._keywords: object | None = None
        self._auto_complete_after = max(1, int(auto_complete_after))
        self._completion: completion.CompletionModel | None = None
        self._offers: list[completion.Candidate] = []
        self._completer: QCompleter | None = None
        self._offer_list: QStringListModel | None = None
        #: The built-in descriptions (`doc/builtins.json`), for the label under
        #: the popup; may be absent (task_37).
        self._reference: object | None = None
        self._detail: QLabel | None = None
        #: The runnable questions of the text by line, for the margin's markers
        #: (task_36); the rule that fills this lives in `queries.py`.
        self._statements: dict[int, str] = {}

        self._margin = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin)
        self.cursorPositionChanged.connect(self._margin.update)
        # Selecting a word shows every other place it appears.  `QPlainTextEdit` has
        # one list of extra selections, so all the pieces are composed in one place
        # (`_refresh_extra_selections`) instead of overwriting each other.
        self.selectionChanged.connect(self._refresh_extra_selections)
        # A mark that outlives the text it pointed at is a lie: an edit clears
        # both the error line and the step line.
        self.textChanged.connect(self.clear_marks)
        # Which lines are questions is a property of the text, so an edit changes
        # it.  The scan rejects a line at its first characters and collects the
        # document's names once, so doing this per keystroke is cheap.
        self.textChanged.connect(self._refresh_statements)
        self._update_margin_width()
        if completion:
            self.enable_completion(True)

    # -- font and zoom ------------------------------------------------------
    def _font_changed(self) -> None:
        super()._font_changed()
        # The margin is as wide as the number of digits in the widest number, so
        # it has to be measured again, not just repainted.
        self._update_margin_width()

    # -- line numbers -------------------------------------------------------
    def set_line_numbers(self, enabled: bool) -> None:
        self._line_numbers = enabled
        self._update_margin_width()
        self._margin.update()

    def line_numbers(self) -> bool:
        return self._line_numbers

    def line_number_area_width(self) -> int:
        if not self._line_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        return QUERY_MARKER_WIDTH + 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin_width(self, _count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_margin(self, rect: QRect, dy: int) -> None:
        if dy:
            self._margin.scroll(0, dy)
        else:
            self._margin.update(0, rect.y(), self._margin.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin_width()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        super().resizeEvent(event)
        area = self.contentsRect()
        self._margin.setGeometry(
            QRect(area.left(), area.top(), self.line_number_area_width(), area.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._margin)
        painter.fillRect(event.rect(), QColor(_MARGIN_BACKGROUND))
        current = self.textCursor().blockNumber()
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        offset = self.contentOffset()
        top = round(self.blockBoundingGeometry(block).translated(offset).top())
        height = self.fontMetrics().height()
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if self._error_line == number + 1:
                    painter.setPen(QColor(ERROR_NUMBER))
                elif self._trace_line == number + 1:
                    painter.setPen(QColor(TRACE_NUMBER))
                elif number == current:
                    painter.setPen(QColor(_MARGIN_CURRENT))
                else:
                    painter.setPen(QColor(_MARGIN_TEXT))
                painter.drawText(
                    0,
                    top,
                    self._margin.width() - 6,
                    height,
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                    str(number + 1),
                )
                if number + 1 in self._statements:
                    self._paint_query_marker(painter, top, height)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def _paint_query_marker(self, painter: QPainter, top: int, height: int) -> None:
        """A right-pointing triangle in the icon column: «this line is a question»."""
        centre = top + height // 2
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(_QUERY_MARKER))
        painter.drawPolygon(
            QPolygon([QPoint(4, centre - 4), QPoint(4, centre + 4), QPoint(11, centre)])
        )
        painter.restore()

    def margin_line_at(self, point) -> int | None:
        """The 1-based line of the margin under `point`, or None.

        The same arithmetic `paint_line_numbers` walks: a block's top edge and
        height, starting from the first visible block.  Only the icon column
        counts — a click on the numbers is not a run.
        """
        if point.x() >= QUERY_MARKER_WIDTH:
            return None
        block = self.firstVisibleBlock()
        offset = self.contentOffset()
        top = round(self.blockBoundingGeometry(block).translated(offset).top())
        while block.isValid() and top <= point.y():
            bottom = top + round(self.blockBoundingRect(block).height())
            if point.y() < bottom:
                return block.blockNumber() + 1
            block = block.next()
            top = bottom
        return None

    def statement_at_margin_point(self, point) -> str | None:
        """The question the margin's `point` stands on — None when there is none."""
        if not self._line_numbers:
            return None
        line = self.margin_line_at(point)
        return self._statements.get(line) if line is not None else None

    def margin_pressed(self, point) -> None:
        """A click in the margin: run the question under it, if there is one.

        A click anywhere else — on a number, on the blank margin beside prose —
        does nothing, and nothing happens beside the run either: the caret and
        the selection stay where they were and the document is not modified.
        """
        statement = self.statement_at_margin_point(point)
        if statement is not None:
            self.queryRequested.emit(statement)

    def _refresh_statements(self) -> None:
        """Recomputes which lines carry a runnable question (task_36)."""
        self._statements = dict(queries.find_statements(self.toPlainText(), self._keywords))
        self._margin.update()

    def query_statements(self) -> dict[int, str]:
        """The runnable questions by line — what the margin draws markers for."""
        return dict(self._statements)

    # -- diagnostics, search and occurrences --------------------------------
    def _existing_line(self, line: int | None) -> int | None:
        """A line that exists: the parser can point past the last one.

        `непарные скобки` is reported where the input ran out, which for a file
        that ends without its closing bracket is one line past the end — marking
        the last line there is the honest place, and a mark that points at nothing
        is not a mark at all.
        """
        if line is None:
            return None
        return max(1, min(int(line), max(1, self.document().blockCount())))

    def mark_error_line(self, line: int | None) -> None:
        """Paints the 1-based `line` red; `None` clears the mark (task_28)."""
        self._error_line = self._existing_line(line)
        self._refresh_extra_selections()
        self._margin.update()

    def mark_trace_line(self, line: int | None) -> None:
        """Paints the line a step is standing on, in a neutral colour.

        The same machinery as the error line, and for the same reason: a run that
        is walked goal by goal has to show *where* it is, and the editor is where
        the program is written.
        """
        self._trace_line = self._existing_line(line)
        self._refresh_extra_selections()
        self._margin.update()

    def clear_marks(self) -> None:
        """Drops both marks (the first edit, a new run, a closed panel)."""
        if self._error_line is None and self._trace_line is None:
            return
        self._error_line = None
        self._trace_line = None
        self._refresh_extra_selections()
        self._margin.update()

    def show_line(self, line: int) -> None:
        """Puts the caret at the start of `line` (1-based) and scrolls to it."""
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def set_search_ranges(
        self, ranges: list[tuple[int, int]], current: tuple[int, int] | None = None
    ) -> None:
        """The search bar's matches, and the one the caret is on."""
        self._search_ranges = list(ranges)
        self._current_range = current
        self._refresh_extra_selections()

    def search_ranges(self) -> list[tuple[int, int]]:
        """What is highlighted right now — the window clears the pane it left."""
        return list(self._search_ranges)

    def word_under_cursor(self) -> str:
        """The token the caret is inside, for `Ctrl+F` and `Ctrl+F3`.

        Letters, digits and the underscore, as the whole-word switch counts them:
        a caret in `факт(1)` sitting anywhere in the name gives `факт`, not the
        clause.  An empty answer means there is no word there — whitespace, a
        bracket, or the end of the line.
        """
        cursor = self.textCursor()
        line = cursor.block().text()
        position = cursor.positionInBlock()
        start = position
        while start > 0 and search.is_word_character(line[start - 1]):
            start -= 1
        end = position
        while end < len(line) and search.is_word_character(line[end]):
            end += 1
        return line[start:end]
    def selected_token(self) -> str | None:
        """The selection, when it is worth highlighting everywhere.

        One line and no spaces: dragging over a paragraph should not paint half the
        file, while a name, `факт(1)` or `#X+1#` is exactly what a reader wants to
        see the other occurrences of.  `\u2029` is Qt's line separator inside a
        selection.
        """
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return None
        text = cursor.selectedText()
        if not text or "\u2029" in text or any(character.isspace() for character in text):
            return None
        return text

    def _refresh_extra_selections(self) -> None:
        """The diagnostic line, the search's matches and the selected word's.

        One list, because Qt keeps one: setting it from a single feature is how a red
        diagnostic line disappeared the moment a word was selected.
        """
        selections: list[QTextEdit.ExtraSelection] = []
        if self._error_line is not None:
            block = self.document().findBlockByNumber(self._error_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(ERROR_BACKGROUND))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)

        if self._trace_line is not None and self._trace_line != self._error_line:
            block = self.document().findBlockByNumber(self._trace_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(TRACE_BACKGROUND))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)

        for start, length in self._search_ranges:
            background = SEARCH_CURRENT if (start, length) == self._current_range else SEARCH_MATCH
            selections.append(self._highlight(start, length, background))

        token = self.selected_token()
        text = self.toPlainText()
        # While the find bar is showing its own matches they *are* the occurrences
        # of that word; a second, lighter set drawn over them would only dull the
        # current one.  Case-sensitively otherwise: in PrologD `факт` and `Факт`
        # are two predicates.
        if (
            token is not None
            and not self._search_ranges
            and len(text) <= OCCURRENCE_LIMIT
        ):
            for offset in search.matches(text, token, search.Options(match_case=True)):
                selections.append(self._highlight(offset, len(token), OCCURRENCE_BACKGROUND))
        self.setExtraSelections(selections)

    def _highlight(self, start: int, length: int, background: str) -> QTextEdit.ExtraSelection:
        """One highlighted run of characters."""
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(background))
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        return selection

    def error_line(self) -> int | None:
        return self._error_line

    def trace_line(self) -> int | None:
        return self._trace_line

    # -- indentation --------------------------------------------------------
    def _indent_text(self) -> str:
        return self._indent_character * self._indent_width

    def set_indent(self, character: str, width: int) -> None:
        self._indent_character = character
        self._indent_width = max(1, width)

    def indent_selection(self, outdent: bool = False) -> None:
        unit = self._indent_text()

        def transform(line: str) -> str:
            if not outdent:
                # A blank line stays blank: indenting it is noise in every diff.
                return line if not line.strip() else unit + line
            if unit and line.startswith(unit):
                return line[len(unit) :]
            leading = len(line) - len(line.lstrip(" \t"))
            return line[min(leading, len(unit)) :]

        self._transform_lines(transform)

    # -- comments -----------------------------------------------------------
    def comment(self) -> None:
        """Comments the selected lines, or the current one, as a single undo step."""
        self._transform_lines(
            lambda line: COMMENT_PREFIX + line if line.strip() else line
        )

    def uncomment(self) -> None:
        def transform(line: str) -> str:
            stripped = line.lstrip()
            if not stripped.startswith(COMMENT_PREFIX):
                return line
            indent = line[: len(line) - len(stripped)]
            return indent + stripped[len(COMMENT_PREFIX) :]

        self._transform_lines(transform)

    def _selected_lines(self) -> QTextCursor:
        """A cursor covering whole lines: the selection, or the current line."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            return cursor
        end = cursor.selectionEnd()
        cursor.setPosition(cursor.selectionStart())
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        return cursor

    def _transform_lines(self, transform) -> None:
        """Rewrites the selected lines as one undo step, keeping them selected.

        Keeping the selection is not cosmetic: without it `Ctrl+U` right after
        `Ctrl+K` would act on the current line alone, because the command left
        the cursor collapsed.  The pair has to be reversible on the same text.
        """
        had_selection = self.textCursor().hasSelection()
        cursor = self._selected_lines()
        text = cursor.selection().toPlainText()
        lines = text.split("\n")
        trailing = lines and lines[-1] == ""
        if trailing:
            lines.pop()
        new_text = "\n".join(transform(line) for line in lines)
        if trailing:
            new_text += "\n"
        if new_text == text:
            return
        start = cursor.selectionStart()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(new_text)
        cursor.endEditBlock()
        end = cursor.position()
        if had_selection:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    # -- completion ---------------------------------------------------------
    def enable_completion(self, enabled: bool) -> None:
        """Turns the popup on or off; what it offers stays Qt-free."""
        if enabled == (self._completer is not None):
            return
        if not enabled:
            self._hide_completion()
            if self._detail is not None:
                self._detail.hide()
                self._detail.deleteLater()
                self._detail = None
            self._completer = None
            self._offer_list = None
            self._completion = None
            self._offers = []
            return
        self._completion = completion.CompletionModel(self._keywords)
        self._offer_list = QStringListModel(self)
        completer = QCompleter(self)
        completer.setModel(self._offer_list)
        completer.setWidget(self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        # A click in the popup is the mouse's Enter.  Keyboard accepts are
        # handled in `keyPressEvent`, and `activated` is deliberately left
        # unconnected: Qt emits it for a key press too, which would insert twice.
        completer.popup().clicked.connect(self._accept_index)
        # The description of the highlighted row: Qt's completer has no second
        # row of its own, so this is a label of its own under the popup —
        # frameless and `Qt.ToolTip`, so it takes no focus and the popup's own
        # geometry never changes (the trap of task_24).  It listens to the
        # popup's *current row*, not to `QCompleter.highlighted`, which is not
        # emitted for every way a row becomes current.
        completer.highlighted.connect(self._update_detail)
        selection = completer.popup().selectionModel()
        if selection is not None:
            selection.currentChanged.connect(lambda *_: self._update_detail())
        completer.popup().installEventFilter(self)
        detail = QLabel(None, Qt.WindowType.ToolTip)
        detail.setForegroundRole(QPalette.ColorRole.ToolTipText)
        detail.setBackgroundRole(QPalette.ColorRole.ToolTipBase)
        detail.setAutoFillBackground(True)
        detail.setMargin(4)
        self._detail = detail
        self._completer = completer

    def completion_enabled(self) -> bool:
        return self._completer is not None

    def completion_visible(self) -> bool:
        return self._completer is not None and self._completer.popup().isVisible()

    def completion_labels(self) -> list[str]:
        """What the popup is showing, in its own order; empty when it is closed."""
        if not self.completion_visible():
            return []
        return [offer.label for offer in self._offers]

    def set_completion_keywords(self, keywords) -> None:
        """The reserved names from the interpreter (`ready`); may arrive late."""
        self._keywords = keywords
        if self._completion is not None:
            self._completion.set_keywords(keywords)
        # The same names decide what the margin accepts as a question: «?длина(Х, 2)
        # не завершится.» is prose only because nothing knows the word `не`.
        self._refresh_statements()

    def set_reference(self, reference) -> None:
        """The built-in descriptions (`doc/builtins.json`); may be absent."""
        self._reference = reference

    def completion_detail(self) -> str:
        """What the label under the popup is showing; empty when it is hidden."""
        if self._detail is None or not self._detail.isVisible():
            return ""
        return self._detail.text()

    def set_auto_complete_after(self, letters: int) -> None:
        self._auto_complete_after = max(1, int(letters))

    def show_completion(self) -> None:
        """Opens the popup on demand (`Ctrl+Space`)."""
        self._maybe_complete(force=True)

    def _hide_completion(self) -> None:
        if self._detail is not None:
            self._detail.hide()
        if self._completer is not None:
            self._completer.popup().hide()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt spelling
        """The description follows the popup's own show and hide.

        `_completer` is read through `getattr`: `QAbstractScrollArea` makes the
        editor a filter of its *own viewport* from its constructor, so this runs
        while `__init__` is still building the object and the field may not
        exist yet.
        """
        completer = getattr(self, "_completer", None)
        if (
            completer is not None
            and watched is completer.popup()
            and event.type() in (QEvent.Type.Show, QEvent.Type.Hide)
        ):
            self._update_detail()
        return super().eventFilter(watched, event)

    def _update_detail(self, label: str = "") -> None:
        """The one-line description of the highlighted candidate (task_37).

        `label` is what `QCompleter.highlighted` carries — the text of the row;
        without it (the popup was just shown, or hidden) the highlighted index
        answers.  No record for the name means no label: saying nothing is better
        than a label that says «нет описания» for every name of the document.
        """
        if self._completer is None or self._detail is None or self._reference is None:
            return
        popup = self._completer.popup()
        if not popup.isVisible():
            self._detail.hide()
            return
        offer = next((item for item in self._offers if item.label == label), None)
        if offer is None:
            offer = self._offer_at(popup.currentIndex().row())
        summary = self._reference.summary(offer.name) if offer is not None else ""
        if not summary:
            self._detail.hide()
            return
        self._detail.setText(f"{offer.name} — {summary}")
        self._detail.adjustSize()
        self._detail.move(popup.mapToGlobal(QPoint(0, popup.height() + 2)))
        self._detail.show()

    def _maybe_complete(self, force: bool = False) -> None:
        if self._completer is None or self._completion is None:
            return
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._hide_completion()
            return
        text = self.toPlainText()
        position = cursor.position()
        if not completion.is_code_position(text, position, self._keywords):
            self._hide_completion()
            return
        prefix = completion.word_before(text, position)
        if not force and len(prefix) < self._auto_complete_after:
            self._hide_completion()
            return
        self._completion.update(text)
        self._offers = self._completion.candidates(prefix)
        if not self._offers:
            self._hide_completion()
            return
        self._offer_list.setStringList([offer.label for offer in self._offers])
        popup = self._completer.popup()
        rect = self.cursorRect()
        rect.setWidth(
            popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(rect)
        # Qt highlights a row only when it filtered the list itself.  Here the
        # list arrives already ranked and filtered, so nothing is highlighted —
        # and `Enter` on an unhighlighted popup does nothing at all.
        popup.setCurrentIndex(self._offer_list.index(0, 0))
        # The description follows the row that is highlighted now, whether Qt
        # announced the change or not: the index was set here.
        self._update_detail()

    def _offer_at(self, row: int) -> completion.Candidate | None:
        if 0 <= row < len(self._offers):
            return self._offers[row]
        return None

    def _accept_index(self, index) -> None:
        """A click in the popup takes that row."""
        offer = self._offer_at(index.row())
        if offer is None:
            return
        self._hide_completion()
        self._insert_completion(offer.insert_text)

    def _accept_completion(self) -> bool:
        """`Enter`/`Tab`: takes the highlighted row.  False when there is none."""
        if self._completer is None:
            return False
        offer = self._offer_at(self._completer.popup().currentIndex().row())
        self._hide_completion()
        if offer is None:
            return False
        self._insert_completion(offer.insert_text)
        return True

    def _insert_completion(self, text: str) -> None:
        """Replaces the word being typed; the arity in the label is not inserted."""
        cursor = self.textCursor()
        prefix = completion.word_before(self.toPlainText(), cursor.position())
        cursor.beginEditBlock()
        if prefix:
            cursor.setPosition(
                cursor.position() - len(prefix), QTextCursor.MoveMode.KeepAnchor
            )
        cursor.insertText(text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    # -- keys ---------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt spelling
        key = event.key()
        modifiers = event.modifiers()

        if self._completer is not None:
            if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.ControlModifier:
                self._maybe_complete(force=True)
                event.accept()
                return
            if self.completion_visible():
                if key in _COMPLETION_ACCEPT_KEYS and not (
                    modifiers & Qt.KeyboardModifier.ShiftModifier
                ):
                    if self._accept_completion():
                        event.accept()
                        return
                elif key == Qt.Key.Key_Escape:
                    self._hide_completion()
                    event.accept()
                    return
                elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    # `Up`/`Down` walk the popup's list, not the caret: the list
                    # is a menu while it is open (the keyboard table of the
                    # README says so), and the description follows the row.
                    popup = self._completer.popup()
                    row = popup.currentIndex().row()
                    row += 1 if key == Qt.Key.Key_Down else -1
                    row = max(0, min(row, len(self._offers) - 1))
                    popup.setCurrentIndex(self._offer_list.index(row, 0))
                    self._update_detail()
                    event.accept()
                    return
                elif key in _POPUP_CLOSE_KEYS:
                    self._hide_completion()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers == Qt.KeyboardModifier.NoModifier:
            if not self.textCursor().hasSelection():
                self._insert_newline_with_indent()
                return
        if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
            if self.textCursor().hasSelection():
                self.indent_selection()
                return
            self.insertPlainText(self._indent_text())
            return
        if key == Qt.Key.Key_Backtab or (
            key == Qt.Key.Key_Tab and modifiers & Qt.KeyboardModifier.ShiftModifier
        ):
            self.indent_selection(outdent=True)
            return
        super().keyPressEvent(event)
        # Automatic completion: only after a character that can be part of a
        # name, and only when the model has something to say.
        if self._completer is not None and event.text() and tokens.is_name_character(event.text()[-1]):
            self._maybe_complete()

    def _insert_newline_with_indent(self) -> None:
        cursor = self.textCursor()
        before = cursor.block().text()[: cursor.positionInBlock()]
        indent = before[: len(before) - len(before.lstrip())]
        if before.rstrip().endswith(_CONTINUATION_ENDINGS):
            indent += self._indent_text()
        cursor.beginEditBlock()
        cursor.insertText("\n" + indent)
        cursor.endEditBlock()
