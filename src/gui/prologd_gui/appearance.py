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

`system` follows the desktop completely: the platform's widget palette **and** the
syntax palette that goes with its colour scheme (`theme_palette`), so a dark
desktop gets a dark window *and* dark-page colours.  Without that it was half a
theme — the widgets dark and the text light — which is why `dark` had to exist as
a separate choice for a darkened desktop.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from . import theme

#: Accepted values, in the order the CLI help and the settings dialog list them.
LIGHT = theme.LIGHT.name
DARK = theme.DARK.name
SYSTEM = "system"
THEMES = (LIGHT, DARK, SYSTEM)

#: What the platform installed, read on the first `apply_theme` — before this
#: module puts anything of its own in place, which is the only moment the answer is
#: honest.  `system` puts these back, so that choice really is «как в системе» and
#: not «Fusion with whatever palette was last in place».
#:
#: The style is remembered by **name**: installing another style makes Qt *delete*
#: the object, and setting a deleted one back raises
#: «Internal C++ object already deleted».  The palette is a value, so a copy of it
#: is safe to keep.
_platform_palette: QPalette | None = None
_platform_style_name: str | None = None
_platform_dark: bool | None = None


def _read_platform(app: QApplication) -> None:
    """Remembers the platform's palette, style and colour scheme — once."""
    global _platform_palette, _platform_style_name, _platform_dark
    if _platform_palette is None:
        _platform_palette = QPalette(app.palette())
    if _platform_style_name is None:
        _platform_style_name = app.style().objectName()
    if _platform_dark is None:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            _platform_dark = True
        elif scheme == Qt.ColorScheme.Light:
            _platform_dark = False
        else:
            # A platform that does not say: its own window colour is what is left.
            _platform_dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def system_is_dark() -> bool:
    """Whether the desktop's colour scheme is dark.

    Qt answers this itself since 6.5 (`QStyleHints.colorScheme`), and the answer is
    remembered from the first call: on Windows it does not change while the window
    is up, and reading it *after* a palette of ours was installed would report our
    own colours as the desktop's.  A process with no application (a Qt-free caller
    of `Settings.palette`) is not a dark desktop as far as this is concerned, and
    nothing is remembered in that case.
    """
    app = QApplication.instance()
    if app is None:
        return False
    _read_platform(app)
    return bool(_platform_dark)


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


def theme_palette(name: str = LIGHT) -> theme.Palette:
    """The colours of a theme name — `system` asks the desktop.

    This is what «использовать системные цвета» means: not only the widgets but the
    page the syntax colours are measured against comes from the desktop, so a dark
    desktop gets `theme.DARK` without anybody choosing it.  An unknown name is the
    light palette (a hand-edited file must not leave a half-dark window).
    """
    if name == SYSTEM:
        return theme.DARK if system_is_dark() else theme.LIGHT
    return theme.palette_for(name)


def apply_theme(app: QApplication, name: str = LIGHT) -> None:
    """Sets the widget appearance; `light` is the default and the safe one.

    `system` puts the platform's own palette and style back — the text follows it
    through `theme_palette`, so the whole window follows the desktop instead of
    half of it.
    """
    _read_platform(app)
    if name == SYSTEM:
        # A *new* style object of the platform's kind (see the note above), and the
        # palette the desktop gave us; both may be unavailable, in which case the
        # colours are still the desktop's, which is what this choice promises.
        if _platform_style_name:
            style = QStyleFactory.create(_platform_style_name)
            if style is not None:
                app.setStyle(style)
        if _platform_palette is not None:
            app.setPalette(_platform_palette)
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
