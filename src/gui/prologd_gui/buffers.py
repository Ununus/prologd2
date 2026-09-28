"""One open program: its model, its text document and the editor showing it.

Apart from the window because there is one of these per tab and the window is
busy with actions.  It is also where the split editor (task_25) belongs: a
second *view* of the same `QTextDocument`, so two panes show one text with one
undo stack instead of two copies that drift apart.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QPlainTextDocumentLayout

from . import documents
from .editor import CodeEditor
from .highlighter import PrologHighlighter
from .settings import Settings


class Buffer(QObject):
    """A model, a `QTextDocument` and the editor that shows it."""

    #: The text changed in a way the tab title should know about.
    changed = Signal()

    def __init__(self, model: documents.Document, settings: Settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.model = model

        # The text document is built here and handed to the editor with
        # `setDocument`: the editor keeps its own until then, and a second pane
        # must share *this* one rather than make a copy of the text.
        #
        # The layout is not optional.  A `QPlainTextEdit` refuses a document that
        # does not use `QPlainTextDocumentLayout` — Qt prints one warning and the
        # pane stays empty while the document *does* hold the text, which is a
        # silent loss rather than an error.
        self.document = QTextDocument(self)
        self.document.setDocumentLayout(QPlainTextDocumentLayout(self.document))
        self.document.setPlainText(model.text)
        self.document.setModified(model.modified)

        self.editor = CodeEditor(
            font_family=settings.font_family,
            font_size=settings.font_size,
            line_numbers=settings.line_numbers,
            completion=settings.completion,
            auto_complete_after=settings.auto_complete_after,
        )
        self.editor.setDocument(self.document)
        self.highlighter = PrologHighlighter(self.document)

        self.document.modificationChanged.connect(self._on_modification_changed)

    # -- text --------------------------------------------------------------
    def text(self) -> str:
        """The text as the editor holds it: LF, no BOM, no trailing surprises."""
        return self.editor.toPlainText()

    def take_text(self) -> None:
        """Hands the editor's text to the model, the way a save does."""
        self.model.set_text(self.text())

    def is_modified(self) -> bool:
        """Qt's own flag: an undo back to the saved text clears it."""
        return self.document.isModified()

    def mark_saved(self) -> None:
        self.document.setModified(False)
        self.model.modified = False

    def sync_modified(self) -> None:
        self.model.modified = self.document.isModified()

    # -- shared state ------------------------------------------------------
    def set_keywords(self, keywords) -> None:
        """The reserved names from `ready`, for the colours and the popup."""
        self.highlighter.set_keywords(keywords)
        self.editor.set_completion_keywords(keywords)

    def set_font_size(self, size: float) -> None:
        self.editor.set_font_size(size)

    def title(self) -> str:
        return self.model.title()

    def _on_modification_changed(self, _modified: bool) -> None:
        self.sync_modified()
        self.changed.emit()
