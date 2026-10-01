"""Window appearance: making the editor readable whatever the system theme is.

Qt 6 follows the Windows dark theme, and the syntax palette of `theme.py` was
chosen against a **white** background — on a dark one those colours turn into
mud, which is exactly what a user with a dark desktop saw.  So the default here is
a forced light appearance.

A dark theme is not a switch over it: it needs its own syntax palette (bright
colours) *and* its own chrome.  That is `theme.DARK`, and this module is the thin
half that turns a palette into a `QPalette` — the colours themselves, and the
contrast they have to keep, are data in `theme.py` and are checked by
`test_appearance.py` for every palette there is.

`system` keeps whatever the platform chose.  It is what a light desktop wants;
a dark one should say `dark`, because the platform palette alone would colour the
widgets and leave the syntax colours of the light theme on a dark page.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from . import theme

#: Accepted values, in the order the CLI help and the settings dialog list them.
LIGHT = theme.LIGHT.name
DARK = theme.DARK.name
SYSTEM = "system"
THEMES = (LIGHT, DARK, SYSTEM)


def qt_palette(palette: theme.Palette) -> QPalette:
    """The widget palette of a theme palette.

    Built rather than taken from the style: `QStyle.standardPalette()` follows the
    platform colour scheme since Qt 6.5, so on a dark desktop it hands back a dark
    palette whatever the user asked for.  Only the roles that matter are set; Qt
    fills in the rest, and the test asserts the relation that matters — the
    window's `Base` *is* the palette's page, which is what the syntax colours are
    measured against.
    """
    text = QColor(palette.foreground)
    window = QColor(palette.window)

    result = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, window),
        (QPalette.ColorRole.WindowText, text),
        (QPalette.ColorRole.Base, QColor(palette.background)),
        (QPalette.ColorRole.AlternateBase, QColor(palette.alternate_base)),
        (QPalette.ColorRole.ToolTipBase, QColor(palette.tooltip_background)),
        (QPalette.ColorRole.ToolTipText, QColor(palette.tooltip_text)),
        (QPalette.ColorRole.Text, text),
        (QPalette.ColorRole.Button, window),
        (QPalette.ColorRole.ButtonText, text),
        (QPalette.ColorRole.BrightText, QColor(palette.bright_text)),
        (QPalette.ColorRole.Link, QColor(palette.link)),
        (QPalette.ColorRole.Highlight, QColor(palette.highlight)),
        (QPalette.ColorRole.HighlightedText, QColor(palette.highlighted_text)),
        (QPalette.ColorRole.PlaceholderText, QColor(palette.placeholder)),
    ):
        result.setColor(role, color)

    disabled = QColor(palette.disabled_text)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        result.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    return result


def apply_theme(app: QApplication, name: str = LIGHT) -> None:
    """Sets the widget appearance; `light` is the default and the safe one.

    `system` is the platform's own palette, which may be dark — the syntax colours
    then stay the light ones, which is why `dark` exists as a choice of its own.
    """
    if name == SYSTEM:
        return
    if name not in theme.PALETTE_BY_NAME:
        raise ValueError(
            f"unknown theme: {name!r}, expected one of {', '.join(THEMES)}"
        )
    # Fusion draws from the palette on every platform, so the chosen colours are
    # what the user actually gets, instead of a native style ignoring them.
    style = QStyleFactory.create("Fusion")
    if style is not None:
        app.setStyle(style)
    app.setPalette(qt_palette(theme.PALETTE_BY_NAME[name]))
