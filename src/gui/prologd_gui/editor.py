"""The code editor: line numbers, font zoom, block comment and indentation.

The highlighting lives in `highlighter.py` and the rules in `tokens.py`; this
module is about *editing*.  Everything here is deliberately small and does one
thing per method, because each of these behaviours is easy to get subtly wrong
and hard to notice — a line number area that stops repainting after a scroll, an
undo that takes two presses, an indent that eats a selection.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QTextCursor, QTextFormat, QWheelEvent
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

#: The comment character of the language: `%` to the end of the line.
COMMENT_PREFIX = "%"

#: Background of the line a diagnostic points at (task_28).
ERROR_BACKGROUND = "#ffd9d9"
ERROR_NUMBER = "#c00000"

_MARGIN_BACKGROUND = "#f0f0f0"
_MARGIN_TEXT = "#8a8a8a"
_MARGIN_CURRENT = "#0a22d6"

_MIN_FONT_SIZE = 6.0
_MAX_FONT_SIZE = 72.0

#: Endings after which the next line continues the same clause, so `Enter`
#: indents one more step.  A guess, not a parse: the real structure is the
#: parser's business (task_30 uses it for the formatter).
_CONTINUATION_ENDINGS = (",", ":-", "<-")


class LineNumberArea(QWidget):
    """The margin the editor paints line numbers into."""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt spelling
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """A `QPlainTextEdit` with what writing PrologD needs."""

    #: Emitted after `Ctrl`+wheel or a zoom action; carries the new point size.
    zoomChanged = Signal(float)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        font_family: str = "Cascadia Mono",
        font_size: float = 11.0,
        line_numbers: bool = True,
        indent_character: str = "\t",
        indent_width: int = 1,
    ) -> None:
        super().__init__(parent)
        self._indent_character = indent_character
        self._indent_width = max(1, indent_width)
        self._line_numbers = line_numbers
        self._error_line: int | None = None

        self._margin = LineNumberArea(self)
        self.setFont(self._make_font(font_family, font_size))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(False)

        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin)
        self.cursorPositionChanged.connect(self._margin.update)
        self._update_margin_width()

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

    def set_font_size(self, size: float) -> None:
        clamped = min(_MAX_FONT_SIZE, max(_MIN_FONT_SIZE, float(size)))
        if abs(clamped - self.font_size) < 1e-6:
            return
        font = self.font()
        font.setPointSizeF(clamped)
        self.setFont(font)
        self._update_margin_width()
        self.zoomChanged.emit(clamped)

    def zoom_by(self, steps: float) -> None:
        self.set_font_size(self.font_size + steps)

    def reset_zoom(self) -> None:
        self.set_font_size(11.0)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt spelling
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_by(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    # -- line numbers -------------------------------------------------------
    def set_line_numbers(self, enabled: bool) -> None:
        self._line_numbers = enabled
        self._update_margin_width()

    def line_numbers(self) -> bool:
        return self._line_numbers

    def line_number_area_width(self) -> int:
        if not self._line_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

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
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    # -- diagnostics --------------------------------------------------------
    def mark_error_line(self, line: int | None) -> None:
        """Paints the 1-based `line` red; `None` clears the mark (task_28)."""
        self._error_line = line
        selections: list[QTextEdit.ExtraSelection] = []
        if line is not None:
            block = self.document().findBlockByNumber(line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(QColor(ERROR_BACKGROUND))
                selection.format.setProperty(
                    QTextFormat.Property.FullWidthSelection, True
                )
                cursor = QTextCursor(block)
                cursor.clearSelection()
                selection.cursor = cursor
                selections.append(selection)
        self.setExtraSelections(selections)
        self._margin.update()

    def error_line(self) -> int | None:
        return self._error_line

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

    # -- keys ---------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt spelling
        key = event.key()
        modifiers = event.modifiers()

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

    def _insert_newline_with_indent(self) -> None:
        cursor = self.textCursor()
        before = cursor.block().text()[: cursor.positionInBlock()]
        indent = before[: len(before) - len(before.lstrip())]
        if before.rstrip().endswith(_CONTINUATION_ENDINGS):
            indent += self._indent_text()
        cursor.beginEditBlock()
        cursor.insertText("\n" + indent)
        cursor.endEditBlock()
