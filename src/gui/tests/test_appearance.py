"""Checks that the window stays readable whatever the system theme is.

    python src/gui/tests/test_appearance.py

The complaint this pins down: with a dark Windows theme Qt 6 hands the widgets a
dark palette, and the syntax colours of `theme.py` — chosen against a white
background — become unreadable.  So the default appearance is forced to light,

and since task_29 there is a **dark theme** of its own: a second syntax palette,
a second page and a second set of bands.  Every pair of colours that has to be
readable is measured here (WCAG AA, 4.5) — for *both* palettes, because a dark
theme that is a switch over the light one is exactly the half-done thing this
file exists to prevent.  This machine has a dark desktop, which is the case the
test has to survive.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QColor, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui import appearance, theme  # noqa: E402
from prologd_gui.theme import contrast_ratio  # noqa: E402

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
    """The property the user noticed by eye, measured — for every palette.

    `Palette.readable_pairs` is the list of pairs that must be readable, and the
    page each one is drawn on comes with it; the widget palette is asserted to
    paint that same page, so the numbers describe what the user really sees.
    """
    for palette in theme.PALETTES:
        appearance.apply_theme(app, palette.name)
        base = app.palette().color(QPalette.ColorRole.Base).name()
        assert base == palette.background, (
            f"{palette.name}: the page is {base}, the palette says {palette.background}"
        )
        pairs = palette.readable_pairs()
        worst = min(pairs, key=lambda item: contrast_ratio(item[1], item[2]))
        for what, colour, background in pairs:
            ratio = contrast_ratio(colour, background)
            assert ratio >= MINIMUM_CONTRAST, (
                f"{palette.name}: {what} {colour} on {background} has contrast {ratio:.2f}"
            )
        print(
            f"ok: {palette.name} — {len(pairs)} pairs clear {MINIMUM_CONTRAST} "
            f"(worst: {worst[0]} at {contrast_ratio(worst[1], worst[2]):.2f})"
        )


def test_dark_gives_a_dark_background_and_light_text(app: QApplication) -> None:
    """The dark theme is a dark one, drawn with Fusion like the light one."""
    appearance.apply_theme(app, appearance.DARK)
    palette = app.palette()

    base = palette.color(QPalette.ColorRole.Base)
    window = palette.color(QPalette.ColorRole.Window)
    text = palette.color(QPalette.ColorRole.Text)

    assert base.lightness() < 128, f"editor background is not dark: {base.name()}"
    assert window.lightness() < 128, f"window background is not dark: {window.name()}"
    assert text.lightness() > 128, f"text is not light: {text.name()}"
    assert app.style().objectName().lower() == "fusion", app.style().objectName()
    print(f"ok: dark — base {base.name()}, window {window.name()}, text {text.name()}")


def test_system_leaves_the_platform_palette_alone(app: QApplication) -> None:
    appearance.apply_theme(app, appearance.SYSTEM)
    palette = app.palette()
    # Whatever the platform chose, the roles must be set — this is the option a
    # light desktop wants.
    assert palette.color(QPalette.ColorRole.Base).isValid()
    assert palette.color(QPalette.ColorRole.Text).isValid()
    print(
        "ok: system keeps the platform palette "
        f"(base {palette.color(QPalette.ColorRole.Base).name()})"
    )


def test_system_colours_the_text_as_well_as_the_widgets(app: QApplication) -> None:
    """«Использовать системные цвета»: one page for the widgets and the syntax.

    The half-done version of this choice was a platform palette with the *light*
    syntax colours on top of it — a dark window full of dark-blue keywords.  So the
    palette `system` resolves to must be the one whose page matches the desktop,
    and the widget palette must agree with it.
    """
    appearance.apply_theme(app, appearance.SYSTEM)
    palette = appearance.theme_palette(appearance.SYSTEM)
    expected = theme.DARK if appearance.system_is_dark() else theme.LIGHT
    assert palette is expected, f"system gave {palette.name}"

    base = app.palette().color(QPalette.ColorRole.Base)
    page_is_dark = base.lightness() < 128
    assert page_is_dark == appearance.system_is_dark(), (
        f"the desktop is {'dark' if appearance.system_is_dark() else 'light'}, "
        f"the widgets say {base.name()}"
    )
    print(
        f"ok: system — desktop is {'dark' if appearance.system_is_dark() else 'light'}, "
        f"base {base.name()}, syntax palette {palette.name}"
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

    It takes its colours from the palette's `ToolTip` roles rather than from the
    syntax palette, so this is the check that covers it — the same WCAG threshold,
    in both themes (the pair is in `readable_pairs` too; this one reads the *widget*
    palette, which is what the label really uses).
    """
    for name in (appearance.LIGHT, appearance.DARK):
        appearance.apply_theme(app, name)
        palette = app.palette()
        text = palette.color(QPalette.ColorRole.ToolTipText).name()
        base = palette.color(QPalette.ColorRole.ToolTipBase).name()
        ratio = contrast_ratio(text, base)
        assert ratio >= MINIMUM_CONTRAST, f"{name}: tooltip text {text} on {base} is {ratio:.2f}"
        print(f"ok: the {name} tooltip pair stays readable ({ratio:.2f})")


def test_the_occurrence_band_stands_out_from_the_page(app: QApplication) -> None:
    """task_58: the other occurrences of the selected word have to be *seen*.

    The measure is not readability, because the band is a background and not text:
    it is how far the colour sits from the page and from the current-line band.
    The dark palette is the one that mattered — it is what a dark desktop gets
    through the «системное» оформление — and `#2d3038` on `#1e1e1e` was 15 units
    away, which is why the highlight could not be found in that theme at all.
    """
    for palette in (theme.LIGHT, theme.DARK):
        page = QColor(palette.background).lightness()
        band = QColor(palette.occurrence).lightness()
        current = QColor(palette.current_line).lightness()
        assert abs(band - page) >= 25, (
            f"{palette.name}: {palette.occurrence} is {abs(band - page)} units of "
            f"lightness from the page {palette.background}"
        )
        assert abs(band - current) >= 15, (
            f"{palette.name}: the occurrence band {palette.occurrence} and the "
            f"current-line band {palette.current_line} are {abs(band - current)} apart"
        )
    print("ok: the occurrence band is visible in both palettes")


def test_an_unknown_palette_name_is_the_light_one() -> None:
    """A hand-edited file must not take the window down — and must not be dark."""
    assert theme.palette_for("полночь").name == theme.LIGHT.name
    print("ok: an unknown theme name falls back to the light palette")


def test_the_settings_store_resolves_the_three_names(directory: pathlib.Path) -> None:
    """What the window reads: an explicit theme is itself, `system` is the desktop."""
    from prologd_gui.settings import Settings

    settings = Settings(directory / "themes.ini")
    assert settings.palette is theme.LIGHT, "the default is the light palette"
    settings.theme = "dark"
    assert settings.palette is theme.DARK
    settings.theme = "system"
    assert settings.palette is appearance.theme_palette(appearance.SYSTEM)
    settings.theme = "полночь"
    assert settings.palette is theme.LIGHT, "a hand-edited name must not be dark"
    print("ok: the store resolves «светлое», «тёмное» and «системное»")


def main() -> int:
    import tempfile

    app = QApplication(sys.argv[:1])
    test_light_gives_a_light_background_and_dark_text(app)
    test_dark_gives_a_dark_background_and_light_text(app)
    test_every_syntax_colour_contrasts_with_the_background(app)
    test_the_occurrence_band_stands_out_from_the_page(app)
    test_an_unknown_palette_name_is_the_light_one()
    test_system_leaves_the_platform_palette_alone(app)
    test_system_colours_the_text_as_well_as_the_widgets(app)
    test_an_unknown_theme_is_refused(app)
    test_tooltip_pair_stays_readable(app)
    with tempfile.TemporaryDirectory(prefix="prologd_theme_") as name:
        test_the_settings_store_resolves_the_three_names(pathlib.Path(name))
    print("all appearance checks passed")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
