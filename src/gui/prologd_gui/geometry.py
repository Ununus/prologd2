"""Window geometry between a window and the settings file (task_45, task_49).

`QWidget.saveGeometry()` and `restoreGeometry()` know about screens, a maximised
window and a display that is no longer there; a hand-made x/y/width/height would
have to re-learn all of it.  What they produce is bytes, so it is stored base64 —
text, which is what a value in the settings file can be.

Both windows that remember their place go through here: the graphics window since
task_45 and the main window since task_49, which is the one the user moves first.
Two copies of «wrap it in base64 and swallow junk» would be two chances to disagree
about the format a settings file holds.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QWidget


def geometry_text(widget: QWidget) -> str:
    """The window's size, place and state as text, for a settings value."""
    return bytes(widget.saveGeometry().toBase64()).decode("ascii")


def restore_geometry(widget: QWidget, text: str) -> bool:
    """Puts the window back where it was; junk in the file is ignored.

    True when Qt accepted the text, so a caller can tell «the file remembered
    nothing» from «the file remembered something this Qt refused» — the difference
    between a window that starts where the code puts it and one that starts
    somewhere the user did not choose.
    """
    if not text:
        return False
    try:
        return bool(widget.restoreGeometry(QByteArray.fromBase64(text.encode("ascii"))))
    except (ValueError, TypeError):
        return False
