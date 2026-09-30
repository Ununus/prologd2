"""Checks that the window stays readable whatever the system theme is.

    python src/gui/tests/test_appearance.py

The complaint this pins down: with a dark Windows theme Qt 6 hands the widgets a
dark palette, and the syntax colours of `theme.py` — chosen against a white
background — become unreadable.  So the default appearance is forced to light,
and the colours are checked for contrast against the background they are actually
drawn on.  This machine has a dark desktop, which is exactly the case the test
has to survive.
"""

from __future__ import annotations

import os
import pathlib
import sys
from dataclasses import fields

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui import appearance  # noqa: E402
from prologd_gui.theme import Theme, contrast_ratio  # noqa: E402

#: WCAG AA for body text.
MINIMUM_CONTRAST = 4.5


def test_light_gives_a_light_background_and_dark_text(app: QApplication) -> None:
    appearance.apply_theme(app, appearance.LIGHT)
    palette = app.palette()

    base = palette.color(QPalette.ColorRole.Base)
    window = palette.color(QPalette.ColorRole.Window)
    text = palette.color(QPalette.ColorRole.Text)

    assert base.lightness() > 128, f"editor background is not light: {base.name()}"
    assert window.lightness() > 128, f"window background is not light: {window.name()}"
    assert text.lightness() < 128, f"text is not dark: {text.name()}"
    assert app.style().objectName().lower() == "fusion", app.style().objectName()
    print(f"ok: light — base {base.name()}, window {window.name()}, text {text.name()}")


def test_every_syntax_colour_contrasts_with_the_background(app: QApplication) -> None:
    """The property the user noticed by eye, measured.

    A colour that fails here is unreadable on the background the editor paints,
    so this is the check that would have caught the dark-theme problem before a
    user did.
    """
    appearance.apply_theme(app, appearance.LIGHT)
    background = app.palette().color(QPalette.ColorRole.Base).name()
    theme = Theme()

    worst = min(
        ((field.name, getattr(theme, field.name)) for field in fields(Theme)),
        key=lambda item: contrast_ratio(item[1], background),
    )
    for field in fields(Theme):
        colour = getattr(theme, field.name)
        ratio = contrast_ratio(colour, background)
        assert ratio >= MINIMUM_CONTRAST, (
            f"{field.name} {colour} on {background} has contrast {ratio:.2f}"
        )
    print(
        f"ok: all {len(fields(Theme))} syntax colours clear {MINIMUM_CONTRAST} "
        f"on {background} (worst: {worst[0]} at {contrast_ratio(worst[1], background):.2f})"
    )


def test_system_leaves_the_platform_palette_alone(app: QApplication) -> None:
    appearance.apply_theme(app, appearance.SYSTEM)
    palette = app.palette()
    # Whatever the platform chose, the roles must be set — this is the option a
    # light desktop wants, and the hook for a real dark theme (task_29).
    assert palette.color(QPalette.ColorRole.Base).isValid()
    assert palette.color(QPalette.ColorRole.Text).isValid()
    print(
        "ok: system keeps the platform palette "
        f"(base {palette.color(QPalette.ColorRole.Base).name()})"
    )


def test_an_unknown_theme_is_refused(app: QApplication) -> None:
    try:
        appearance.apply_theme(app, "midnight")
    except ValueError as error:
        assert "midnight" in str(error)
        print("ok: an unknown theme is refused with a message that names it")
        return
    raise AssertionError("an unknown theme was accepted")


def test_tooltip_pair_stays_readable(app: QApplication) -> None:
    """The popup's description label is a tooltip window: check its own pair.

    It takes its colours from the palette's `ToolTip` roles rather than from
    `theme.py`, so this is the check that covers it — the same WCAG threshold as
    the syntax colours.
    """
    appearance.apply_theme(app, appearance.LIGHT)
    palette = app.palette()
    text = palette.color(QPalette.ColorRole.ToolTipText).name()
    base = palette.color(QPalette.ColorRole.ToolTipBase).name()
    ratio = contrast_ratio(text, base)
    assert ratio >= MINIMUM_CONTRAST, f"tooltip text {text} on {base} is {ratio:.2f}"
    print(f"ok: the tooltip pair stays readable ({ratio:.2f})")


def main() -> int:
    app = QApplication(sys.argv[:1])
    test_light_gives_a_light_background_and_dark_text(app)
    test_every_syntax_colour_contrasts_with_the_background(app)
    test_system_leaves_the_platform_palette_alone(app)
    test_an_unknown_theme_is_refused(app)
    test_tooltip_pair_stays_readable(app)
    print("all appearance checks passed")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
