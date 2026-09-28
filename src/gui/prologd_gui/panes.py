"""A pane of the editor: one tab bar of views on the open documents.

The split editor (task_25) is two of these side by side.  Each pane has its own
current tab, so the left pane can show one program while the right shows another —
but they show the *same set* of documents, in the same order, and the views share
one `QTextDocument` per document.  That is the whole trick: one text, one undo
stack and one modified flag, so an edit in one pane appears in the other
immediately and there is never a second copy to keep in sync.

Which pane a command acts on is the one that was last used: clicking in a view or
switching its tab makes that pane active, and the window's run/save/comment
commands follow `active_pane()`.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget

from .buffers import Buffer
from .editor import CodeEditor
from .settings import Settings


class Pane(QTabWidget):
    """A tab bar of views; the documents themselves belong to the window."""

    #: This pane was clicked or its tab changed: the commands act on it now.
    activated = Signal()
    #: A view zoomed (Ctrl+wheel); the window stores one size for every pane.
    zoomChanged = Signal(float)
    #: A program file was dropped on a view; the window opens it in a tab.
    fileDropped = Signal(str)
    #: A tab's close button was pressed; the window asks about unsaved changes.
    closeRequested = Signal(object)
    #: The empty part of the tab bar was double clicked: start a new file.
    newFileRequested = Signal()
    #: Tabs were dragged into another order; the window re-orders every pane.
    reordered = Signal(object)

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._buffers: list[Buffer] = []
        self._views: dict[Buffer, CodeEditor] = {}
        #: True while the tabs are re-ordered from the outside, so `tabMoved` does
        #: not try to re-order the list that is being applied.
        self._silent = False

        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self._on_close_requested)
        self.currentChanged.connect(self._on_current_changed)
        self.tabBar().tabMoved.connect(self._on_tab_moved)
        self.tabBar().tabBarDoubleClicked.connect(self._on_tab_bar_double_clicked)

    # -- what it shows ------------------------------------------------------
    def buffers(self) -> list[Buffer]:
        """The documents in tab order."""
        return list(self._buffers)

    def current_buffer(self) -> Buffer | None:
        index = self.currentIndex()
        if 0 <= index < len(self._buffers):
            return self._buffers[index]
        return None

    def view_for(self, buffer: Buffer) -> CodeEditor | None:
        return self._views.get(buffer)

    def current_view(self) -> CodeEditor | None:
        buffer = self.current_buffer()
        return self._views.get(buffer) if buffer is not None else None

    def set_current(self, buffer: Buffer | None) -> bool:
        if buffer is None or buffer not in self._buffers:
            return False
        self.setCurrentIndex(self._buffers.index(buffer))
        return True

    def set_buffers(self, buffers: list[Buffer]) -> None:
        """Shows exactly these documents, in this order, keeping the current one.

        The window owns the set and the order (a tab dragged here has to move
        everywhere), so this is how a pane is told what to show.
        """
        current = self.current_buffer()
        self._silent = True
        try:
            wanted = set(buffers)
            for index in reversed(range(len(self._buffers))):
                if self._buffers[index] not in wanted:
                    self._detach(index)
            for buffer in buffers:
                if buffer not in self._views:
                    self._attach(buffer)
            self._reorder(buffers)
        finally:
            self._silent = False
        # Keeping the current tab matters more than the index: re-ordering must not
        # move the user's eyes to another file.
        if not self.set_current(current) and self._buffers:
            self.setCurrentIndex(len(self._buffers) - 1)

    # -- internals ---------------------------------------------------------
    def _attach(self, buffer: Buffer) -> None:
        """Adds a view of `buffer` and a tab for it."""
        view = buffer.add_view()
        view.setPlaceholderText("текст программы")
        view.zoomChanged.connect(self.zoomChanged)
        view.fileDropped.connect(self.fileDropped)
        view.activated.connect(self.activated)
        self._views[buffer] = view
        self._buffers.append(buffer)
        self.addTab(view, buffer.title())

    def _detach(self, index: int) -> None:
        buffer = self._buffers.pop(index)
        view = self._views.pop(buffer, None)
        self.removeTab(index)
        if view is not None:
            buffer.remove_view(view)

    def _reorder(self, buffers: list[Buffer]) -> None:
        for target, buffer in enumerate(buffers):
            current = self._buffers.index(buffer)
            if current != target:
                self.tabBar().moveTab(current, target)
                self._buffers.insert(target, self._buffers.pop(current))

    def refresh_titles(self) -> None:
        """Re-reads every tab's title from its document."""
        for index, buffer in enumerate(self._buffers):
            self.setTabText(index, buffer.title())

    # -- events ------------------------------------------------------------
    def _on_close_requested(self, index: int) -> None:
        if 0 <= index < len(self._buffers):
            self.closeRequested.emit(self._buffers[index])

    def _on_current_changed(self, _index: int) -> None:
        if not self._silent:
            self.activated.emit()

    def _on_tab_moved(self, source: int, target: int) -> None:
        if self._silent or not 0 <= source < len(self._buffers):
            return
        self._buffers.insert(target, self._buffers.pop(source))
        self.reordered.emit(list(self._buffers))

    def _on_tab_bar_double_clicked(self, index: int) -> None:
        if index < 0:  # the empty part of the bar, not a tab
            self.newFileRequested.emit()
