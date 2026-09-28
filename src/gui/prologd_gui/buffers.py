"""One open program: its model, its text document and the views showing it.

Apart from the window because there is one of these per tab and the window is
busy with actions.  A buffer owns one `QTextDocument` and any number of views of
it (task_25's split editor), so two panes show one text with one undo stack
instead of two copies that drift apart.
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
    """A model, a `QTextDocument` and the views that show it.

    The document is created here and *parented* here: a view that takes it with
    `setDocument` does not become its owner (Qt keeps an explicitly given parent),
    which is what makes several views of one text possible.
    """

    #: The text changed in a way the tab title should know about.
    changed = Signal()

    def __init__(self, model: documents.Document, settings: Settings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self._settings = settings
        self._views: list[CodeEditor] = []

        # The layout is not optional.  A `QPlainTextEdit` refuses a document that
        # does not use `QPlainTextDocumentLayout` — Qt prints one warning and the
        # pane stays empty while the document *does* hold the text, which is a
        # silent loss rather than an error.
        self.document = QTextDocument(self)
        self.document.setDocumentLayout(QPlainTextDocumentLayout(self.document))
        self.document.setPlainText(model.text)
        self.document.setModified(model.modified)
        self.highlighter = PrologHighlighter(self.document)

        self.document.modificationChanged.connect(self._on_modification_changed)

    # -- views -------------------------------------------------------------
    def add_view(self) -> CodeEditor:
        """A view of this document: one text, one undo stack, one modified flag.

        The view brings its own font, zoom, line-number margin and completion
        popup; the text it shows belongs to the buffer.
        """
        editor = CodeEditor(
            font_family=self._settings.font_family,
            font_size=self._settings.font_size,
            line_numbers=self._settings.line_numbers,
            completion=self._settings.completion,
            auto_complete_after=self._settings.auto_complete_after,
        )
        editor.setDocument(self.document)
        editor.set_completion_keywords(self.highlighter.keywords)
        self._views.append(editor)
        return editor

    def remove_view(self, editor: CodeEditor) -> None:
        """Drops a view; the document stays alive for the other views."""
        if editor in self._views:
            self._views.remove(editor)
        editor.setParent(None)
        editor.deleteLater()

    def views(self) -> list[CodeEditor]:
        return list(self._views)

    # -- text --------------------------------------------------------------
    def text(self) -> str:
        """The text as the editor holds it: LF, no BOM, no trailing surprises."""
        return self.document.toPlainText()

    def set_text(self, text: str) -> None:
        """Replaces the text in every view at once (`Перечитать с диска`)

        The undo history goes with it, which is what a reload means.
        """
        self.document.setPlainText(text)

    def take_text(self) -> None:
        """Hands the text to the model, the way a save does."""
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
        """The reserved names from `ready`, for the colours and the popups."""
        self.highlighter.set_keywords(keywords)
        for view in self._views:
            view.set_completion_keywords(keywords)

    def set_font_size(self, size: float) -> None:
        for view in self._views:
            view.set_font_size(size)

    def title(self) -> str:
        return self.model.title()

    def _on_modification_changed(self, _modified: bool) -> None:
        self.sync_modified()
        self.changed.emit()
