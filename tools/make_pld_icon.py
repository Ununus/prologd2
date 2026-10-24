"""Rebuilds `src/gui/assets/pld.ico` from `pld.png` (task_116).

    .venv\\Scripts\\python.exe tools/make_pld_icon.py

The icon of a `.pld` file.  Windows asks the shell for 16, 24, 32, 48, 64, 128 and
256 pixels depending on where the file is drawn — the tree, the desktop, the large
icon view, the Add/Remove list — and an ICO with one size is scaled by the shell,
which is what makes a 64 drawn at 16 look mush.  So every size is generated here.

The source is 64 x 64, so **128 and 256 are upscales** and look soft; that is
accepted (the owner's call) because a soft large icon beats a missing one.  Give
this script a bigger square source when one exists and the large sizes stop being
guesses.

Each entry is a PNG payload inside the ICO container, which Windows Vista and later
read (the manuals name Windows 10 as the floor).  Every payload is re-encoded from
the resized image, so nothing of the source file's own metadata reaches the icon —
the online converter left `Software`, `exif`, `dpi`, `gamma` and `srgb` chunks in
the PNG, and none of them belong in a 16 x 16 image.

The script prints ASCII only and needs Pillow (it is a tool, not a dependency of
the window).
"""

from __future__ import annotations

import io
import pathlib
import struct

from PIL import Image

#: Every size the shell may ask for, smallest first — the order Explorer and every
#: icon editor write.
SIZES = (16, 24, 32, 48, 64, 128, 256)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "gui" / "assets" / "pld.png"
TARGET = ROOT / "src" / "gui" / "assets" / "pld.ico"


def resized(image: Image.Image, size: int) -> Image.Image:
    """The picture at `size`, smoothed: down- and upscaling both want a filter."""
    filter_name = getattr(Image, "Resampling", Image).LANCZOS
    return image.resize((size, size), filter_name)


def payload(image: Image.Image, size: int) -> bytes:
    """One icon image as PNG bytes — re-encoded, so no metadata travels on."""
    buffer = io.BytesIO()
    resized(image, size).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build(image: Image.Image) -> bytes:
    """The whole ICO file: a directory of entries, then the images themselves."""
    parts = [payload(image, size) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(parts))  # reserved, type = icon, count
    offset = len(header) + 16 * len(parts)
    entries = b""
    for size, part in zip(SIZES, parts):
        side = 0 if size == 256 else size  # 256 is written as 0, that is the rule
        entries += struct.pack(
            "<BBBBHHII", side, side, 0, 0, 1, 32, len(part), offset
        )
        offset += len(part)
    return header + entries + b"".join(parts)


def main() -> int:
    if not SOURCE.is_file():
        print(f"no {SOURCE.name} beside this tool: {SOURCE}")
        return 1
    image = Image.open(SOURCE).convert("RGBA")
    data = build(image)
    TARGET.write_bytes(data)
    print(f"{SOURCE.name} {image.width}x{image.height} -> {TARGET.name} "
          f"{len(data)} bytes, sizes {', '.join(str(size) for size in SIZES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
