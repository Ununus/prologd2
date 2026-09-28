"""The code editor: line numbers, font zoom, block comment and indentation.

The highlighting lives in `highlighter.py` and the rules in `tokens.py`; this
module is about *editing*.  Everything here is deliberately small and does one
thing per method, because each of these behaviours is easy to get subtly wrong
and hard to notice — a line number area that stops repainting after a scroll, an
undo that takes two presses, an indent that eats a selection.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, QStringListModel, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QTextCursor, QTextFormat, QWheelEvent
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from . import completion, tokens

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

#: Keys that take the highlighted completion.  With `Shift` they keep their own
#: meaning: `Shift+Enter` is a newline and `Shift+Tab` an outdent.
_COMPLETION_ACCEPT_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab)

#: Keys that close the popup and still do their job in the editor — the caret
#: keeps its arrows inside the line.  `Up`/`Down` are deliberately not here:
#: they walk the list.
_POPUP_CLOSE_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, Qt.Key.Key_End)


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
        completion: bool = True,
        auto_complete_after: int = 2,
    ) -> None:
        super().__init__(parent)
        self._indent_character = indent_character
        self._indent_width = max(1, indent_width)
        self._line_numbers = line_numbers
        self._error_line: int | None = None
        self._keywords: object | None = None
        self._auto_complete_after = max(1, int(auto_complete_after))
        self._completion: completion.CompletionModel | None = None
        self._offers: list[completion.Candidate] = []
        self._completer: QCompleter | None = None
        self._offer_list: QStringListModel | None = None

        self._margin = LineNumberArea(self)
        self.setFont(self._make_font(font_family, font_size))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(False)

        self.blockCountChanged.connect(self._update_margin_width)
        self.updateRequest.connect(self._update_margin)
        self.cursorPositionChanged.connect(self._margin.update)
        self._update_margin_width()
        if completion:
            self.enable_completion(True)

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

    # -- completion ---------------------------------------------------------
    def enable_completion(self, enabled: bool) -> None:
        """Turns the popup on or off; what it offers stays Qt-free."""
        if enabled == (self._completer is not None):
            return
        if not enabled:
            self._hide_completion()
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

    def set_auto_complete_after(self, letters: int) -> None:
        self._auto_complete_after = max(1, int(letters))

    def show_completion(self) -> None:
        """Opens the popup on demand (`Ctrl+Space`)."""
        self._maybe_complete(force=True)

    def _hide_completion(self) -> None:
        if self._completer is not None:
            self._completer.popup().hide()

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
