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
from .tokens import mode_from_first_line


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
        #: How the `ИМПОРТ` lines become the texts the popups read (task_102):
        #: the window answers, because only it knows the search directories.
        self._import_lookup = None
        #: Where an `ИМПОРТ` name is looked for, for the string's own completion
        #: (task_104); also the window's answer.
        self._import_folders = None

        # The layout is not optional.  A `QPlainTextEdit` refuses a document that
        # does not use `QPlainTextDocumentLayout` — Qt prints one warning and the
        # pane stays empty while the document *does* hold the text, which is a
        # silent loss rather than an error.
        self.document = QTextDocument(self)
        self.document.setDocumentLayout(QPlainTextDocumentLayout(self.document))
        self.document.setPlainText(model.text)
        self.document.setModified(model.modified)
        self.highlighter = PrologHighlighter(
            self.document, theme=self._settings.palette.syntax
        )

        self.document.modificationChanged.connect(self._on_modification_changed)
        # The naming mode belongs to the *file* (task_67) and only its first line can
        # set it, so watching for a change is one string comparison per keystroke
        # instead of a re-tokenisation of the buffer.
        self._first_line = ""
        self._variable_mode = 0
        #: How a file that says nothing is read (task_67): the *window's* answer,
        #: handed to every buffer as they appear (`set_fallback_variable_mode`) — a
        #: row for our own engine, the old dialect for one that has no modes at all
        #: (task_79).  The row is only the starting point: the window knows which
        #: engine runs, this object does not.
        self._fallback_mode = self._settings.variable_mode_number
        self.document.contentsChanged.connect(self._on_contents_changed)
        self.refresh_variable_mode()

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
            palette=self._settings.palette,
            completion=self._settings.completion,
            auto_complete_after=self._settings.auto_complete_after,
            completion_match_case=self._settings.completion_match_case,
            current_line=self._settings.current_line,
        )
        editor.setDocument(self.document)
        editor.set_completion_keywords(self.highlighter.keywords)
        editor.set_reference(self._reference)
        editor.set_shortcuts(self._shortcuts)
        editor.set_import_lookup(self._import_lookup)
        editor.set_import_folders(self._import_folders)
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

    def mark_modified(self) -> None:
        """Claims the text as unsaved work — for a tab the window filled itself.

        `setPlainText` clears Qt's flag, so a program a conversion wrote into a new
        tab looked like a file nobody had touched: no star, and — worse — no
        question when that text was about to be lost (task_109).  The text *is*
        unsaved work: it exists in the editor and nowhere else.
        """
        self.document.setModified(True)
        self.model.modified = True
        self.changed.emit()

    def sync_modified(self) -> None:
        self.model.modified = self.document.isModified()

    # -- shared state ------------------------------------------------------
    def refresh_variable_mode(self) -> None:
        """Works out how this document's names are read, and tells the highlighter.

        The file's own `:- ИМЕНА(N).` first line wins (task_67); a file that says
        nothing is read in the window's answer (`_fallback_mode`), the way `--vars`
        covers the CLI.  This is colouring only: the interpreter reads the same
        marker when it runs or formats the file.
        """
        declared = mode_from_first_line(self.text())
        self._variable_mode = (
            self._fallback_mode if declared is None else declared
        )
        self.highlighter.set_mode(self._variable_mode)

    def set_fallback_variable_mode(self, mode: int) -> None:
        """What a file that declares nothing about names is read in (task_79).

        The window answers, not this object: only the window knows *which engine*
        runs, and an engine with no modes of its own reads names the old way, so a
        marker-less file is colouring-, completing- and sending-wise the old one
        under it.  A file that declares `:- ИМЕНА(N).` is not touched — the dialect
        belongs to the file — and the colouring follows at once.
        """
        self._fallback_mode = int(mode)
        self.refresh_variable_mode()

    def variable_mode(self) -> int:
        """How this document's names are read (task_67) — see `refresh_variable_mode`.

        The window sends it with a question of its own: the margin marker and the
        goal line ask with a single statement, which carries no marker of its own.
        """
        return self._variable_mode

    def _on_contents_changed(self) -> None:
        first = self.document.firstBlock().text()
        if first == self._first_line:
            return
        self._first_line = first
        self.refresh_variable_mode()

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

    def set_import_lookup(self, lookup) -> None:
        """How this document's `ИМПОРТ` names become texts the popups can read.

        Completion offers the names a file *brings in* (task_102), and the files are
        found the way the interpreter finds them — which is the window's knowledge
        (the folder of this file, the `-I` rows, the interpreter), not the buffer's.
        """
        self._import_lookup = lookup
        for view in self._views:
            view.set_import_lookup(lookup)

    def set_import_folders(self, lookup) -> None:
        """Where an `ИМПОРТ` name is looked for, for the directive's own string.

        The editor offers the files and folders the directive may name (task_104),
        and finding them is the same search the run does — the window's knowledge,
        handed down the way `set_import_lookup` hands down the texts.
        """
        self._import_folders = lookup
        for view in self._views:
            view.set_import_folders(lookup)

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

    def set_palette(self, palette) -> None:
        """Re-colours the syntax and every view (task_29's dark theme).

        The syntax palette is the *document's*: the highlighter is one per buffer
        and every view of it shows the same colours, so it is set once here and
        the views only get the chrome (bands, margin, matches).
        """
        self.highlighter.set_theme(palette.syntax)
        for view in self._views:
            view.set_palette(palette)

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
