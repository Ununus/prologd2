"""The window's side of the formatter — Qt-free, so a headless test can drive it.

The formatter itself lives in prlib, next to the grammar it has to understand:
the window sends the text with a `format` request (protocol 6) and receives the
laid-out text back.  What is left on this side is bookkeeping, and this module is
where it lives — mapping the caret and the selection from the old text onto the
new one, so formatting a buffer never throws the user's place away.  Only
whitespace changes, so the mapping is exact except inside the regions that were
rewritten, where a position lands on the start of what replaced it.
"""

from __future__ import annotations

import difflib


def map_positions(old: str, new: str, positions: list[int]) -> list[int]:
    """Where the `positions` of `old` ended up in `new`.

    An offset inside a region the formatter rewrote — the whitespace between two
    goals, the run of spaces in front of a dot — snaps to the beginning of what
    replaced it; an offset anywhere else keeps its distance from the text around
    it.  Everything is clamped to `new`, because the answer of the interpreter is
    all there is to map onto.
    """
    opcodes = difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
    mapped: list[int] = []
    for position in positions:
        point = max(0, min(int(position), len(old)))
        delta = 0
        answer = len(new)
        for tag, i1, i2, j1, j2 in opcodes:
            if point < i1:
                # The change is after the position: nothing before it moved.
                answer = point + delta
                break
            if point <= i2:
                answer = point + delta if tag == "equal" else j1
                break
            delta += (j2 - j1) - (i2 - i1)
        mapped.append(max(0, min(answer, len(new))))
    return mapped
