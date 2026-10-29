"""The queue of what a run printed, and the panes it is handed to.

A trace of a deep recursion arrives as hundreds of thousands of small events, and
one `feed` per event costs some 30 us of Python on top of the insertion (task_49).
So text is queued and handed over on the next turn, joined by kind: a batch, not a
throttle — nothing is dropped and nothing waits for a clock, because a timer that
*sampled* the output would lose lines.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer

from prologd_gui import panels


class OutputFeed(QObject):
    """What the current turn produced, and where it goes when it is time.

    The three panes and `refresh` are the window's: «Проблемы» is a table and gets
    whole rows, «Система» and «Вывод» are text and keep a half-line until the rest
    arrives.  `refresh` is called where the text *lands*, not where it was queued —
    the tab titles carry the line counts.
    """

    def __init__(self, output, problems, system, refresh, parent=None) -> None:
        super().__init__(parent)
        self._output = output
        self._problems = problems
        self._system = system
        self._refresh = refresh
        #: `(kind, text)` in arrival order, waiting for the next turn.
        self._pending: list[tuple[str, str]] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.flush)

    def append(self, kind: str, text: str) -> None:
        """Queues text for the output pane, which colours it by kind."""
        self._pending.append((kind, text))
        if not self._timer.isActive():
            self._timer.start()

    def flush(self) -> None:
        """Hands the queued output to the panes: one call per run of one kind."""
        self._timer.stop()
        pending = self._pending
        if not pending:
            return
        self._pending = []
        kind, text = pending[0]
        for next_kind, more in pending[1:]:
            if next_kind == kind:
                text += more
                continue
            self._feed(kind, text)
            kind, text = next_kind, more
        self._feed(kind, text)
        self._refresh()

    def flush_tails(self) -> None:
        """Ends the open half-line in every *text* pane; nothing else will finish it.

        «Проблемы» is a table now: it holds whole rows, so there is no half-line to
        complete.
        """
        for pane in (self._output, self._system):
            pane.flush()
        self._refresh()

    def discard(self) -> None:
        """Drops what is queued: the panes are about to be emptied or reused."""
        self._timer.stop()
        self._pending.clear()

    def _feed(self, kind: str, text: str) -> None:
        """One run of one kind, into the pane its kind belongs to (task_50)."""
        tab = panels.KIND_TAB.get(kind, panels.TAB_OUTPUT)
        if tab == panels.TAB_PROBLEMS:
            # Diagnostics come from `window._on_failed` with their fields; text of
            # these two kinds is the window feeding itself, and it gets a row with no
            # place to go to.
            self._problems.add_text(text, kind)
        elif tab == panels.TAB_SYSTEM:
            self._system.feed(text, kind)
        else:
            self._output.feed(text, kind)
