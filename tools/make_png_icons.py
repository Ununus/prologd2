"""Rebuilds the hicolor icons the Debian package installs (task_118).

    .venv/bin/python tools/make_png_icons.py

`src/gui/assets/prologd2.png` is the application icon: the desktop entry names
`prologd`, and Linux looks that name up in the hicolor theme.  `pld.png` is the
icon of a `.pld` file (`application/x-prologd`), the same source `pld.ico` is
made from (task_116).

Both sources are 64 x 64, so 16/24/32/48 are downscales and 128/256 are upscales.
The large sizes are accepted for the same reason as in `make_pld_icon.py`: a soft
icon beats a missing one, and a bigger source would make them sharp.  Every PNG is
re-encoded, so nothing of the source file's own metadata reaches the theme.

The tool prints ASCII only and needs Pillow.  It is a source-maintenance tool, not
a step of `tools/build_deb.sh`: the generated files are committed.
"""

from __future__ import annotations

import pathlib

from PIL import Image

#: The sizes the hicolor theme is read at; `64` is the source's own size.
SIZES = (16, 24, 32, 48, 64, 128, 256)

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "gui" / "assets"
TARGET = ROOT / "installer" / "linux" / "icons" / "hicolor"

#: Source, then where the theme wants it under a size folder.
ICONS = (
    ("prologd2.png", pathlib.Path("apps") / "prologd.png"),
    ("pld.png", pathlib.Path("mimetypes") / "application-x-prologd.png"),
)


def resampling() -> int:
    """The smoothing filter; Pillow 10 spells it `Image.Resampling.LANCZOS`."""
    return getattr(Image, "Resampling", Image).LANCZOS


def main() -> int:
    for source_name, relative in ICONS:
        source = ASSETS / source_name
        if not source.is_file():
            print(f"no {source_name} in {ASSETS}")
            return 1
        image = Image.open(source).convert("RGBA")
        for size in SIZES:
            target = TARGET / f"{size}x{size}" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            image.resize((size, size), resampling()).save(
                target, format="PNG", optimize=True
            )
            print(f"{source_name} {size}x{size} -> {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
