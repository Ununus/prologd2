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

from . import actions, documents
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
        #: The built-in descriptions, shared by every view's popup (task_37).
        self._reference = None
        #: The `Ctrl`+key insertions (task_31), shared by every view.
        self._shortcuts = None

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
            indent_character=self._settings.indent_character,
            indent_width=self._settings.indent_width,
            auto_indent=self._settings.auto_indent,
            completion=self._settings.completion,
            auto_complete_after=self._settings.auto_complete_after,
            completion_match_case=self._settings.completion_match_case,
            current_line=self._settings.current_line,
        )
        editor.setDocument(self.document)
        editor.set_completion_keywords(self.highlighter.keywords)
        editor.set_reference(self._reference)
        editor.set_shortcuts(self._shortcuts)
        editor.set_wrap(self._settings.wrap)
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
        """Claims the text as saved — and says so, even when the flag was already
        clear.

        A caller that fills a widget and then marks the result saved would otherwise
        keep the wrong tab picture: the picture is fetched when `changed` arrives,
        and `setModified(False)` on an unmodified document emits nothing.
        """
        self.document.setModified(False)
        self.model.modified = False
        self.changed.emit()

    def sync_modified(self) -> None:
        self.model.modified = self.document.isModified()

    # -- shared state ------------------------------------------------------
    def set_keywords(self, keywords) -> None:
        """The reserved names from `ready`, for the colours and the popups."""
        self.highlighter.set_keywords(keywords)
        for view in self._views:
            view.set_completion_keywords(keywords)

    def set_reference(self, reference) -> None:
        """The built-in descriptions (`doc/builtins.json`), for the popup label."""
        self._reference = reference
        for view in self._views:
            view.set_reference(reference)

    def set_shortcuts(self, table) -> None:
        """The `Ctrl`+key insertions (task_31); one table for every view."""
        self._shortcuts = table
        for view in self._views:
            view.set_shortcuts(table)

    def set_font_size(self, size: float) -> None:
        for view in self._views:
            view.set_font_size(size)

    def set_font_family(self, family: str) -> None:
        for view in self._views:
            view.set_font_family(family)

    def set_line_numbers(self, enabled: bool) -> None:
        for view in self._views:
            view.set_line_numbers(enabled)

    def set_wrap(self, enabled: bool) -> None:
        for view in self._views:
            view.set_wrap(enabled)

    def set_current_line(self, enabled: bool) -> None:
        for view in self._views:
            view.set_current_line(enabled)

    def set_indent(self, character: str, width: int) -> None:
        for view in self._views:
            view.set_indent(character, width)

    def set_auto_indent(self, enabled: bool) -> None:
        for view in self._views:
            view.set_auto_indent(enabled)

    def set_completion(self, enabled: bool, after: int, match_case: bool) -> None:
        """The three completion switches of task_29, in one call per view."""
        for view in self._views:
            view.enable_completion(enabled)
            view.set_auto_complete_after(after)
            view.set_completion_match_case(match_case)

    def title(self) -> str:
        return self.model.title()

    def icon_name(self) -> str:
        """Which picture the tab shows.

        A modified buffer is marked whichever way it is saved, and a buffer that
        has a file looks different from one that was never saved: those are the two
        things a tab bar has to say about the work in it.  The names come from
        `actions`, where the icon audit finds them.
        """
        if self.is_modified():
            return actions.MODIFIED_ICON
        return actions.SAVED_ICON if self.model.path else actions.FILE_ICON

    def _on_modification_changed(self, _modified: bool) -> None:
        self.sync_modified()
        self.changed.emit()
