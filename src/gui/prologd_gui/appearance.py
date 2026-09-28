"""Window appearance: making the editor readable whatever the system theme is.

Qt 6 follows the Windows dark theme, and the syntax palette of `theme.py` was
chosen against a **white** background — on a dark one those colours turn into
mud, which is exactly what a user with a dark desktop sees.  So the default here
is a forced light appearance.

`system` keeps whatever the platform chose; it is what a light desktop wants, and
it is where a real dark theme will hook in.  A dark theme is *not* just this
switch: it needs its own syntax palette (bright colours), which is task_29's
colour page — a half-done dark mode would be worse than none.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

#: Accepted values, in the order the CLI help lists them.
LIGHT = "light"
SYSTEM = "system"
THEMES = (LIGHT, SYSTEM)


def light_palette() -> QPalette:
    """The light palette, built by hand rather than taken from the style.

    `QStyle.standardPalette()` is not usable here: since Qt 6.5 it follows the
    platform colour scheme, so on a dark desktop it hands back a dark palette.
    Only the roles that matter are set; Qt fills in the rest, and the test
    asserts the property that actually matters — a light background with dark
    text, which is what the syntax colours need.
    """
    text = QColor("#1a1a1a")
    window = QColor("#f0f0f0")
    base = QColor("#ffffff")
    disabled = QColor("#a0a0a0")

    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, window),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, base),
        (QPalette.ColorRole.AlternateBase, QColor("#f7f7f7")),
        (QPalette.ColorRole.ToolTipBase, QColor("#ffffe1")),
        (QPalette.ColorRole.ToolTipText, text),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, window),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.BrightText, QColor("#d40000")),
        (QPalette.ColorRole.Link, QColor("#0a22d6")),
        (QPalette.ColorRole.Highlight, QColor("#0a5fd6")),
        (QPalette.ColorRole.HighlightedText, QColor("#ffffff")),
        (QPalette.ColorRole.PlaceholderText, QColor("#8a8a8a")),
    ):
        palette.setColor(role, color)

    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    return palette


def apply_theme(app: QApplication, name: str = LIGHT) -> None:
    """Sets the widget appearance; `light` is the default and the safe one."""
    if name == LIGHT:
        # Fusion draws from the palette on every platform, so the forced colours
        # are what the user actually gets, instead of a native style ignoring
        # them on Windows.
        style = QStyleFactory.create("Fusion")
        if style is not None:
            app.setStyle(style)
        app.setPalette(light_palette())
        return
    if name == SYSTEM:
        return
    raise ValueError(f"unknown theme: {name!r}, expected one of {', '.join(THEMES)}")
