"""The code editor: line numbers, font zoom, block comment and indentation.

The highlighting lives in `highlighter.py` and the rules in `tokens.py`; this
module is about *editing*.  Everything here is deliberately small and does one
thing per method, because each of these behaviours is easy to get subtly wrong
and hard to notice — a line number area that stops repainting after a scroll, an
undo that takes two presses, an indent that eats a selection.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEvent,
    QMimeData,
    QPoint,
    QRect,
    QSize,
    QStringListModel,
    Qt,
    Signal,
)
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
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

from . import completion, imports, queries, search, shortcuts as shortcuts_module, theme, tokens
from .settings import DEFAULT_FONT_SIZE, MAXIMUM_FONT_SIZE, MINIMUM_FONT_SIZE

#: The comment character of the language: `%` to the end of the line.
COMMENT_PREFIX = "%"

#: Every colour the editor paints with lives in a `theme.Palette` (task_29): the
#: page, the bands of an error and of a step, the search matches, the margin and
#: the marker of a question.  The editor holds the palette in force and reads it
#: where it draws, so a dark theme is the same code with another palette — and the
#: contrast of every one of those colours is checked for *its* page.

#: Background of the other places the selected word appears, and the size of a
#: document worth scanning for them on every selection change.
OCCURRENCE_LIMIT = 200_000

#: The margin's icon column: a run marker for every line that is a question
#: (task_36), and the hit box of the click that runs it.  It sits left of the
#: numbers, so a marker is never hit while aiming at a digit, and a click on
#: the numbers themselves does nothing.
QUERY_MARKER_WIDTH = 14

_MIN_FONT_SIZE = MINIMUM_FONT_SIZE
_MAX_FONT_SIZE = MAXIMUM_FONT_SIZE

#: Endings after which the next line continues the same clause, so `Enter`
#: indents one more step.  A guess, not a parse: the real structure is the
#: parser's business (task_30 uses it for the formatter).
_CONTINUATION_ENDINGS = (",", ":-", "<-")

#: Keys that take the highlighted completion.  With `Shift` they keep their own
#: meaning: `Shift+Enter` is a newline — a real one since 2026-10-03, because Qt's
#: own `Shift+Enter` is a line separator (`U+2028`) and the margin counts lines —
#: and `Shift+Tab` an outdent.
_COMPLETION_ACCEPT_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab)

#: Keys that close the popup and still do their job in the editor — the caret
#: keeps its arrows inside the line.  `Up`/`Down` are deliberately not here:
#: they walk the list.
_POPUP_CLOSE_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End)

#: The width the completion's description wraps at (task_37, made multi-line in
#: 2026-10-02): wide enough for a summary, narrow enough that the label under the
#: popup never runs off the screen.
COMPLETION_DETAIL_WIDTH = 460


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
        auto_indent: bool = True,
        palette: theme.Palette | None = None,
        completion: bool = True,
        auto_complete_after: int = 2,
        completion_match_case: bool = True,
        current_line: bool = True,
    ) -> None:
        super().__init__(parent, font_family=font_family, font_size=font_size)
        self._indent_character = indent_character
        self._indent_width = max(1, indent_width)
        self._auto_indent = bool(auto_indent)
        #: The colours of everything this view paints (task_29); `light` unless the
        #: window hands over another theme.
        self._palette = palette or theme.LIGHT
        self._line_numbers = line_numbers
        #: Whether the line the caret is on gets a pale band (task_29).
        self._current_line = bool(current_line)
        self._error_line: int | None = None
        #: The line of the clause a stepped run is standing on (task_28).
        self._trace_line: int | None = None
        #: Where the search bar's matches are, and which one the caret sits on.
        self._search_ranges: list[tuple[int, int]] = []
        self._current_range: tuple[int, int] | None = None
        self._keywords: object | None = None
        self._auto_complete_after = max(1, int(auto_complete_after))
        self._completion_match_case = bool(completion_match_case)
        self._completion: completion.CompletionModel | None = None
        self._offers: list[completion.Candidate] = []
        self._completer: QCompleter | None = None
        self._offer_list: QStringListModel | None = None
        #: The built-in descriptions (`doc/builtins.json`), for the label under
        #: the popup; may be absent (task_37).
        self._reference: object | None = None
        #: `Ctrl`+physics-key insertions (task_31); the table lives in the
        #: settings file, so every view gets the one the window read.
        self._shortcuts: shortcuts_module.Shortcuts | None = None
        self._detail: QLabel | None = None
        #: How the buffer's `ИМПОРТ` names become texts, handed in by the window
        #: (task_102); `None` means «nothing is imported as far as the popup is
        #: concerned», which is what a check of the editor without a window gets.
        self._import_lookup = None
        #: The directive list the imported texts were read for, so the scan and the
        #: reads happen when that list changes and not on every keystroke.
        self._import_names: list[str] | None = None
        #: The folders an `ИМПОРТ` name is looked for in, handed in by the window;
        #: `None` offers no file names at all (task_104).
        self._import_folders = None
        #: What a file entry replaces when it is accepted (`iso.pld` in `lib/is`).
        self._file_prefix: str | None = None
        #: The runnable questions of the text by line, for the margin's markers
        #: (task_36); the rule that fills this lives in `queries.py`.
        self._statements: dict[int, str] = {}

        self._margin = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin)
        self.cursorPositionChanged.connect(self._margin.update)
        # The current line's band moves with the caret, so the same signal keeps
        # it in place (the margin updates on it anyway).
        self.cursorPositionChanged.connect(self._refresh_extra_selections)
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
        painter.fillRect(event.rect(), QColor(self._palette.margin_background))
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
                    painter.setPen(QColor(self._palette.error_text))
                elif self._trace_line == number + 1:
                    painter.setPen(QColor(self._palette.trace_text))
                elif number == current:
                    painter.setPen(QColor(self._palette.margin_current))
                else:
                    painter.setPen(QColor(self._palette.margin_text))
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
        painter.setBrush(QColor(self._palette.query_marker))
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
        if self._current_line:
            block = self.textCursor().block()
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(self._palette.current_line))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)

        if self._error_line is not None:
            block = self.document().findBlockByNumber(self._error_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(self._palette.error_background))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)

        if self._trace_line is not None and self._trace_line != self._error_line:
            block = self.document().findBlockByNumber(self._trace_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(self._palette.trace_background))
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)

        for start, length in self._search_ranges:
            current = (start, length) == self._current_range
            background = self._palette.search_current if current else self._palette.search_match
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
                selections.append(
                    self._highlight(offset, len(token), self._palette.occurrence)
                )
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

    def set_auto_indent(self, enabled: bool) -> None:
        """Whether `Enter` continues the indentation (task_29's switch).

        Off, a new line starts at the left margin: the indentation of a Prolog
        clause is the author's, and a lecture that indents through a `:-` body is
        easier to type with the editor out of the way.
        """
        self._auto_indent = bool(enabled)

    def palette(self) -> theme.Palette:
        """The colours in force — the editor's own bands and margin, not the page."""
        return self._palette

    def set_palette(self, palette: theme.Palette) -> None:
        """Re-colours the view (task_29's dark theme), margin included.

        The *syntax* colours are the buffer's business (`Buffer.set_palette`): they
        belong to the document, which every view of it shares.
        """
        self._palette = palette
        self._refresh_extra_selections()
        self._margin.update()
        self.viewport().update()

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

    def delete_lines(self) -> None:
        """`Shift+Del`: the whole line under the caret, or every line the selection
        touches.

        The *whole* line goes, not its tail — that is what the command says — and
        the caret lands in the first column of the line that slid up, so a run of
        `Shift+Del` walks down the text.  A selection that stops at a line's first
        column does not take that line with it: a drag from the middle of one line
        to the start of the next means «these lines», not «and one more».

        A document cannot lose its last block, so the last line of a file is
        emptied rather than removed: what is left is an empty line, as in every
        editor with this key.  One edit block, like `comment`, so one `Ctrl+Z`
        brings the text back at once.
        """
        document = self.document()
        selection = self.textCursor()
        if selection.hasSelection():
            first = document.findBlock(selection.selectionStart())
            last = document.findBlock(selection.selectionEnd())
            if last != first and selection.selectionEnd() == last.position():
                last = last.previous()
        else:
            first = last = selection.block()
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(first.position())
        if last.next().isValid():
            # Up to the start of the line below: the newline ends the line being
            # removed, and taking it is what makes the line below slide up.
            cursor.setPosition(last.next().position(), QTextCursor.MoveMode.KeepAnchor)
        else:
            # The last line of the document has no newline after it, so only its
            # text goes: the empty line stays where it is.
            cursor.setPosition(
                last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor
            )
        text = cursor.selection().toPlainText()
        cursor.removeSelectedText()
        cursor.endEditBlock()
        # `Shift+Del` is Windows' other spelling of `Ctrl+X`, so the removed lines go
        # to the clipboard as well — the key borrowed the platform's meaning, and a
        # cut that cannot be pasted back is a surprise (task_58's follow-up).
        if text:
            QApplication.clipboard().setText(text)
        self.setTextCursor(cursor)

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
        self._completion = completion.CompletionModel(
            self._keywords, case_sensitive=self._completion_match_case
        )
        self._offer_list = QStringListModel(self)
        completer = QCompleter(self)
        completer.setModel(self._offer_list)
        completer.setWidget(self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        # The *model* decides what matches; the completer only shows the rows it
        # was handed, so its own case rule would be a second, hidden filter.
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
        # The same names decide what the margin accepts as a question: «?длина(Список, 2)
        # не завершится.» is prose only because nothing knows the word `не`.
        self._refresh_statements()

    def set_reference(self, reference) -> None:
        """The built-in descriptions (`doc/builtins.json`); may be absent."""
        self._reference = reference

    def set_import_lookup(self, lookup) -> None:
        """How the buffer's `ИМПОРТ` names become the texts the popup reads.

        `lookup` takes the directive names of the buffer and answers `{path: text}`
        — the window's business, because only it knows the search directories, the
        interpreter and the folder the file lives in (task_102).  `None` (the
        default) offers nothing from imports.
        """
        self._import_lookup = lookup
        self._import_names = None

    def set_import_folders(self, lookup) -> None:
        """Where an `ИМПОРТ` name is looked for, so the string can complete (task_104).

        `lookup` answers the folders in the engine's order — the window knows them,
        the editor does not.  `None` (the default) keeps the popup out of the
        directive's string, which is what a check without a window gets.
        """
        self._import_folders = lookup

    def set_shortcuts(self, table) -> None:
        """The `Ctrl`+key insertions of task_31 (a `Shortcuts` table)."""
        self._shortcuts = table

    def completion_detail(self) -> str:
        """What the label under the popup is showing; empty when it is hidden."""
        if self._detail is None or not self._detail.isVisible():
            return ""
        return self._detail.text()

    def set_auto_complete_after(self, letters: int) -> None:
        self._auto_complete_after = max(1, int(letters))

    def set_completion_match_case(self, flag: bool) -> None:
        """Whether «най» offers `НАЙТИВСЕ` too (task_29's switch)."""
        self._completion_match_case = bool(flag)
        if self._completion is not None:
            self._completion.set_case_sensitive(flag)

    def set_current_line(self, enabled: bool) -> None:
        """Whether the caret's line gets a pale band behind it."""
        self._current_line = bool(enabled)
        self._refresh_extra_selections()

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
        """The description of the highlighted candidate: title, then the modes.

        `label` is what `QCompleter.highlighted` carries — the text of the row;
        without it (the popup was just shown, or hidden) the highlighted index
        answers.  No record for the name means no label: saying nothing is better
        than a label that says «нет описания» for every name of the document.
        The label is word-wrapped to a width of its own, so a long summary and
        the argument modes read as several lines, not as one line off the screen.

        A name an imported file brings in has no record either, but it does have a
        file (task_102): that line is the whole label, unless the name is also a
        built-in, where the record comes after it.  A name of the document or of a
        library says what its first clause says above itself — the comment is read
        with the name (task_103).
        """
        if self._completer is None or self._detail is None:
            return
        popup = self._completer.popup()
        if not popup.isVisible():
            self._detail.hide()
            return
        offer = next((item for item in self._offers if item.label == label), None)
        if offer is None:
            offer = self._offer_at(popup.currentIndex().row())
        lines: list[str] = []
        if offer is not None and offer.origin:
            lines.append(f"импорт: {offer.origin}")
        if offer is not None and offer.summary:
            lines.append(offer.summary)
        if offer is not None and self._reference is not None:
            lines += self._reference.detail_lines(offer.name)
        if not lines:
            self._detail.hide()
            return
        self._detail.setText("\n".join(lines))
        self._detail.setWordWrap(True)
        self._detail.setMaximumWidth(COMPLETION_DETAIL_WIDTH)
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
        self._file_prefix = None
        # Inside the file name of an `ИМПОРТ` directive the popup offers files
        # instead of names (task_104): that one string is a path, not text.
        typed = imports.import_argument_at(text, position, self._keywords)
        if typed is not None:
            self._complete_file(typed, force)
            return
        if not completion.is_code_position(text, position, self._keywords):
            self._hide_completion()
            return
        prefix = completion.word_before(text, position)
        if not force and len(prefix) < self._auto_complete_after:
            self._hide_completion()
            return
        self._refresh_imports(text)
        self._completion.update(text)
        self._offers = self._completion.candidates(prefix)
        if not completion.at_statement_start(text, position, prefix):
            # A directive is a statement of its own (task_105): inside a body the
            # popup offers names, not `:- ИМПОРТ("…").`.
            self._offers = [offer for offer in self._offers if not offer.directive]
        if not self._offers:
            self._hide_completion()
            return
        self._show_offers()

    def _complete_file(self, typed: tuple[str, str], force: bool) -> None:
        """Offers the files an `ИМПОРТ` name may become (task_104).

        The folders come from the window (it alone knows the search order), the
        entries from the disk; a name is offered after one letter — a file name is
        not a word, and waiting for two would hide `iso.pld` — and after a `/` the
        whole folder is shown.
        """
        folder, name = typed
        if not force and not name and not folder:
            self._hide_completion()
            return
        folders = self._import_folders() if self._import_folders is not None else []
        names = imports.complete_names(folders, folder + name)
        if not names:
            self._hide_completion()
            return
        self._offers = [
            completion.Candidate(entry, None, completion.ATOM_NAME, completion.IMPORTED)
            for entry in names
        ]
        # What the entry replaces is the name part only: `lib/` stays as typed.
        self._file_prefix = name
        self._show_offers()

    def _show_offers(self) -> None:
        """Puts `self._offers` in front of the user and opens the popup on them."""
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

    def _refresh_imports(self, text: str) -> None:
        """Asks the window what the buffer's `ИМПОРТ` lines bring in (task_102).

        Only when the list of directive names differs from the one the texts were
        read for: the popup is asked for on every keystroke, and tokenising (and
        reading) the imported files for each of them is the one thing that would
        make it stutter.
        """
        if self._import_lookup is None or self._completion is None:
            return
        names = imports.directive_names(text, self._keywords)
        if names == self._import_names:
            return
        self._import_names = names
        self._completion.set_imported(self._import_lookup(names))

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
        self._insert_completion(*offer.call_form)

    def _accept_completion(self) -> bool:
        """`Enter`/`Tab`: takes the highlighted row.  False when there is none."""
        if self._completer is None:
            return False
        offer = self._offer_at(self._completer.popup().currentIndex().row())
        self._hide_completion()
        if offer is None:
            return False
        self._insert_completion(*offer.call_form)
        return True

    def _insert_completion(self, text: str, caret_after: int | None = None) -> None:
        """Replaces the word being typed; the caret lands at `caret_after`.

        `caret_after` is the offset from the start of the inserted text — the
        call form puts it right after the opening parenthesis, so the user types
        the first argument at once (the arity in the label is never typed).
        """
        cursor = self.textCursor()
        if self._file_prefix is not None:
            # A file name replaces the name part of the path only (task_104).
            prefix = self._file_prefix
        else:
            prefix = completion.word_before(self.toPlainText(), cursor.position())
        start = cursor.position() - len(prefix) if prefix else cursor.position()
        cursor.beginEditBlock()
        if prefix:
            cursor.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)
        cursor.endEditBlock()
        if caret_after is not None:
            cursor.setPosition(start + caret_after)
        self.setTextCursor(cursor)

    # -- keys ---------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt spelling
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Delete and modifiers == Qt.KeyboardModifier.ShiftModifier:
            # `Shift+Del` never reaches the action's shortcut while the editor has
            # focus: `QTextControl` claims the platform's «cut» sequence (Windows
            # spells `Ctrl+X` as `Shift+Del`), so the key arrives *here* — and with
            # nothing selected it did nothing at all, while the same command from the
            # menu worked (task_58's follow-up).  One command, two doors: this and
            # the `delete_line` action both run `delete_lines`.
            self.delete_lines()
            event.accept()
            return

        if self._insert_shortcut(event):
            return

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

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
        ):
            # One newline, whatever `Shift` says.  Left to Qt, `Shift+Enter` inserts a
            # *line separator* (`U+2028`): the widget draws a new line without counting
            # it, so the line numbers and the question markers of the margin stand on
            # the wrong lines (`tokens.LINE_SEPARATORS`, the report of 2026-10-03).
            # Nothing here is bound to `Ctrl`/`Alt` plus `Enter`, so those still reach
            # Qt as they always did.
            if self._auto_indent and not self.textCursor().hasSelection():
                self._insert_newline_with_indent()
            else:
                # With a selection this replaces it, which is what `Enter` always did.
                self.insertPlainText("\n")
            event.accept()
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

    def insertFromMimeData(self, source: QMimeData) -> None:  # noqa: N802 - Qt spelling
        """A paste never brings a *line separator* into the document.

        `Shift+Enter` is not the only door for `U+2028`/`U+2029`: text copied from a
        browser or a PDF carries them, and they break the line count in exactly the
        same way (`tokens.LINE_SEPARATORS`).  Text read from a file is folded in
        `documents.read_text`, so all three doors now lead to one line break.
        """
        if source.hasText():
            text = tokens.plain_newlines(source.text())
            if text != source.text():
                self.insertPlainText(text)
                return
        super().insertFromMimeData(source)

    def _insert_shortcut(self, event: QKeyEvent) -> bool:
        """`Ctrl`+physical key inserts punctuation (task_31), or nothing.

        Matched on `nativeScanCode()`, never on `event.text()`: the character a
        layout produces is exactly what differs between layouts.  Only `Ctrl`
        (plus the `Shift` a chord asks for) is accepted — `Alt` alone reaches
        the menu bar and `Ctrl+Alt` is `AltGr` on many layouts, so neither may
        be swallowed here.  One `beginEditBlock` makes the insert one undo step,
        exactly like typing the text by hand.
        """
        if self._shortcuts is None:
            return False
        modifiers = event.modifiers()
        if not (modifiers & Qt.KeyboardModifier.ControlModifier):
            return False
        if modifiers & (
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier
        ):
            return False
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        cursor = self.textCursor()
        selection = ""
        if cursor.hasSelection():
            # `selectedText()` spells a paragraph break as U+2029, which is not
            # what the document holds.
            selection = cursor.selectedText().replace("\u2029", "\n")
        insert = self._shortcuts.insert_for(event.nativeScanCode(), shift, selection)
        if insert is None:
            return False
        cursor.beginEditBlock()
        cursor.insertText(insert.text)
        cursor.endEditBlock()
        begin = cursor.position() - len(insert.text)
        cursor.setPosition(begin + insert.start)
        if insert.end != insert.start:
            # A wrapped selection stays selected: it is still the text the user
            # chose, only now it has brackets around it.
            cursor.setPosition(begin + insert.end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        event.accept()
        return True

    def _insert_newline_with_indent(self) -> None:
        cursor = self.textCursor()
        before = cursor.block().text()[: cursor.positionInBlock()]
        indent = before[: len(before) - len(before.lstrip())]
        if before.rstrip().endswith(_CONTINUATION_ENDINGS):
            indent += self._indent_text()
        cursor.beginEditBlock()
        cursor.insertText("\n" + indent)
        cursor.endEditBlock()


class QueryLine(QLineEdit):
    """The goal field under the editor: its own history and the editor's completion.

    `Up`/`Down` walk the submitted commands (up to `HISTORY_LIMIT`), and the
    popup offers the *same* names as the editor — the reserved names and the
    current document's predicates, with the same call-form insertion — so a goal
    is typed with the same help as the program it asks about (task_50).

    The document the completion scans is provided by `document_text`, a callable:
    the query line is not a buffer of its own, and the names a goal may call are
    those of the file it will run against.
    """

    #: How many commands the history keeps (task_50).
    HISTORY_LIMIT = 20

    def __init__(
        self,
        parent: QWidget | None = None,
        document_text=None,
    ) -> None:
        super().__init__(parent)
        self._document_text = document_text or (lambda: "")
        self._history: list[str] = []
        self._history_cursor: int | None = None
        self._draft = ""
        self._auto_complete_after = 2
        self._model = completion.CompletionModel(None, case_sensitive=True)
        self._offers: list[completion.Candidate] = []
        self._offer_list = QStringListModel(self)
        self._completer = QCompleter(self)
        self._completer.setModel(self._offer_list)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        self._completer.popup().clicked.connect(self._accept_index)

    # -- configuration ------------------------------------------------------
    def set_completion_keywords(self, keywords) -> None:
        """The reserved names; the document's own come from `document_text`."""
        self._model.set_keywords(keywords)

    def set_auto_complete_after(self, letters: int) -> None:
        self._auto_complete_after = max(1, int(letters))

    def set_completion_match_case(self, flag: bool) -> None:
        self._model.set_case_sensitive(flag)

    def set_document_text(self, text: str) -> None:
        self._document_text = lambda: text

    # -- history -----------------------------------------------------------
    def history(self) -> list[str]:
        """The submitted commands, oldest first (what a test reads)."""
        return list(self._history)

    def _commit_history(self) -> None:
        """Remembers the goal being submitted; an empty or a repeated one is not."""
        text = self.text().strip()
        self._history_cursor = None
        if not text:
            return
        if self._history and self._history[-1] == text:
            return
        self._history.append(text)
        if len(self._history) > self.HISTORY_LIMIT:
            del self._history[: len(self._history) - self.HISTORY_LIMIT]

    def _history_step(self, direction: int) -> None:
        """`Up` (older) and `Down` (newer); past the newest is the draft again."""
        if not self._history:
            return
        if self._history_cursor is None:
            if direction > 0:
                return  # `Down` before `Up` has nowhere to go.
            self._draft = self.text()
            self._history_cursor = len(self._history) - 1
        else:
            self._history_cursor += direction
            if self._history_cursor >= len(self._history):
                self._history_cursor = None
                self.setText(self._draft)
                self.setCursorPosition(len(self._draft))
                return
            if self._history_cursor < 0:
                self._history_cursor = 0
        text = self._history[self._history_cursor]
        self.setText(text)
        self.setCursorPosition(len(text))

    # -- completion --------------------------------------------------------
    def completion_visible(self) -> bool:
        return self._completer.popup().isVisible()

    def completion_labels(self) -> list[str]:
        """What the popup is showing; empty when it is closed."""
        if not self.completion_visible():
            return []
        return [offer.label for offer in self._offers]

    def show_completion(self) -> None:
        self._maybe_complete(force=True)

    def _maybe_complete(self, force: bool = False) -> None:
        text = self.text()
        position = self.cursorPosition()
        prefix = completion.word_before(text, position)
        if not force and len(prefix) < self._auto_complete_after:
            self._completer.popup().hide()
            return
        self._model.update(self._document_text())
        self._offers = self._model.candidates(prefix)
        if not self._offers:
            self._completer.popup().hide()
            return
        self._offer_list.setStringList([offer.label for offer in self._offers])
        popup = self._completer.popup()
        rect = self.cursorRect()
        rect.setWidth(
            popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(rect)
        popup.setCurrentIndex(self._offer_list.index(0, 0))

    def _accept_index(self, index) -> None:
        """A click in the popup takes that row."""
        if 0 <= index.row() < len(self._offers):
            self._accept(self._offers[index.row()])

    def _accept_completion(self) -> bool:
        row = self._completer.popup().currentIndex().row()
        if not 0 <= row < len(self._offers):
            return False
        self._accept(self._offers[row])
        return True

    def _accept(self, offer: completion.Candidate) -> None:
        """Replaces the word being typed with the call form, caret after `(`."""
        self._completer.popup().hide()
        text, caret = offer.call_form
        prefix = completion.word_before(self.text(), self.cursorPosition())
        start = self.cursorPosition() - len(prefix)
        whole = self.text()
        self.setText(whole[:start] + text + whole[self.cursorPosition() :])
        self.setCursorPosition(start + caret)

    def _move_popup(self, delta: int) -> None:
        popup = self._completer.popup()
        row = popup.currentIndex().row() + delta
        row = max(0, min(row, len(self._offers) - 1))
        popup.setCurrentIndex(self._offer_list.index(row, 0))

    # -- keys ---------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt spelling
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._maybe_complete(force=True)
            event.accept()
            return

        if self._completer.popup().isVisible():
            if key in _COMPLETION_ACCEPT_KEYS and not (
                modifiers & Qt.KeyboardModifier.ShiftModifier
            ):
                if self._accept_completion():
                    event.accept()
                    return
            elif key == Qt.Key.Key_Escape:
                self._completer.popup().hide()
                event.accept()
                return
            elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self._move_popup(1 if key == Qt.Key.Key_Down else -1)
                event.accept()
                return
            elif key in _POPUP_CLOSE_KEYS:
                self._completer.popup().hide()
        else:
            if key == Qt.Key.Key_Up:
                self._history_step(-1)
                event.accept()
                return
            if key == Qt.Key.Key_Down:
                self._history_step(1)
                event.accept()
                return

        # `Enter` with the popup closed submits the goal: remember it first, and
        # let `QLineEdit` emit `returnPressed` as usual.
        if (
            key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not self._completer.popup().isVisible()
        ):
            self._commit_history()

        super().keyPressEvent(event)
        if event.text() and tokens.is_name_character(event.text()[-1]):
            self._maybe_complete()
