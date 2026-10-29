"""Where a diagnostic and a step point stand, and which tab gets the mark.

Two rules the window would otherwise spell out twice: *which* tab a position names —
an `ИМПОРТ`ed file belongs to that file, and marking the wrong tab is worse than
marking none — and that *one* line is marked at a time, the caret following only
where the user is looking.

Nothing here touches the status bar or opens a file by itself: the callables
`buffer_of` gets are the window's own, so the rules are testable without a window.
"""

from __future__ import annotations

import pathlib

from prologd_gui.buffers import Buffer


def clear(buffers) -> None:
    """Both marks, in every view: a new run starts clean."""
    for buffer in buffers:
        for view in buffer.views():
            view.clear_marks()


def buffer_of(position, buffers, *, current, lookup, open_path) -> Buffer | None:
    """The tab a diagnostic points at, opening it when it is a file of ours.

    The file is looked for among the open tabs, then next to the file that imported
    it, then on disk — where it is opened.  A name in angle brackets is not a file:
    `<buffer>` is the program (the showing tab's lines), `<query>` one statement and
    `<library>` the interpreter's own, and only the first has lines in a tab.

    `buffers` is the open list, `current` returns the showing buffer, `lookup` finds
    an open tab by path, `open_path` opens a file and answers whether it did.
    """
    name = position.file if position is not None else ""
    if not name or name == "<buffer>":
        # The program text the window itself sent: its lines are the buffer's.
        return current()
    if name.startswith("<"):
        # `<query>` — the one statement of a `query` request (the query line or a
        # margin marker); `<library>` — the interpreter's own library.  Neither has
        # a line in any tab: marking the current one would say the program broke
        # where it did not.
        return None
    # An unnamed buffer is named by its tab title («Без имени 2»): the text is the
    # window's own, and its lines are that buffer's lines.
    for buffer in buffers:
        if buffer.model.path is None and buffer.title() == name:
            return buffer
    wanted = pathlib.Path(name)
    candidates = [wanted]
    here = current()
    if not wanted.is_absolute() and here is not None and here.model.path:
        # A relative name is relative to the file the import was written in.
        candidates.append(pathlib.Path(here.model.path).parent / wanted)
    for candidate in candidates:
        found = lookup(str(candidate))
        if found is not None:
            return found
    for candidate in candidates:
        if candidate.is_file() and open_path(str(candidate)):
            return lookup(str(pathlib.Path(candidate)))
    return None


def mark_error(buffers, buffer, line: int) -> None:
    """Marks `line` in `buffer`'s views and puts the caret on it.

    Every other tab loses its mark, so that one line is marked at a time.  The
    caret follows the line the view clamped the mark to: «непарные скобки» is
    reported where the input ran out, and the mark stops at the last line there is.
    """
    for other in buffers:
        for view in other.views():
            view.mark_error_line(line if other is buffer else None)
    for view in buffer.views():
        view.show_line(view.error_line() or line)


def mark_trace(buffers, buffer, line: int | None, *, follow: bool) -> None:
    """Marks the line a step stands on — in the tab that line belongs to.

    The caret follows only when that tab is the one showing (`follow`): a stepped
    run through an imported file must not pull the user out of the program they are
    watching, and the mark is there when they switch to it.  `line` of `None` leaves
    every tab without a mark — there is a point of the run, but not one to stand on.
    """
    for other in buffers:
        for view in other.views():
            if other is not buffer:
                view.mark_trace_line(None)
    if buffer is None or line is None:
        return
    for view in buffer.views():
        view.mark_trace_line(line)
    if follow:
        for view in buffer.views():
            view.show_line(view.trace_line() or line)
