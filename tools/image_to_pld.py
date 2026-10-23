"""Turn a picture into `ЗАКРАСКА/5` facts on a small grid.

    python tools/image_to_pld.py \
        --image мышь=ai/_ref/images/mouse.png \
        --image сыр=ai/_ref/images/cheese.png \
        --image стена=ai/_ref/images/wall.png \
        --out examples/problems/maze/maze.images.pld \
        --preview build/images --scale 12

One picture becomes one cell of the maze, so the picture is reduced to a `--size`
square (`16x16` by default) and drawn on the canvas at that size.  Three steps
keep the number of draw calls small — a picture drawn pixel by pixel would be 256
`ЗАКРАСКА` calls per cell:

1. **average** every cell over the pixels it covers (a box filter, not a point
   sample: a 1-pixel eye survives, a single stray pixel does not);
2. **quantise** the result to `--colors` colours (median cut) — a 16×16 icon
   rarely needs more, and every extra colour is extra rectangles;
3. **merge** neighbouring cells of one colour into rectangles, greedily: the run
   grows to the right first, then down while the whole row matches.  A brick wall
   of one colour becomes one rectangle per row instead of sixteen.

Pixels close to the background (`--tolerance`, per channel) are left out
entirely, so an icon's white page does not erase what is drawn under it.

The output is a Prolog file of plain facts, one per rectangle:

    картинка(мышь, 3, 12, 5, 14, 8421504).

which is what `maze.graphics.pld` draws with `ЗАКРАСКА(X1, Y1, X2, Y2, Цвет)`.
A preview PNG of the quantised grid (`--preview`) is written beside it so the
result can be looked at before it goes into a program.

`--size` has to agree with the cell the program draws, otherwise a picture covers
a part of it: the facts carry cell-local coordinates from 0 to `size - 1`.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from render_graphics import write_png  # noqa: E402  (the PNG writer lives there)

Colour = tuple[int, int, int]


def load_rgba(path: pathlib.Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """The picture as a flat list of RGBA tuples (Qt reads PNG, JPEG and friends)."""
    from PySide6.QtGui import QImage

    image = QImage(str(path))
    if image.isNull():
        raise SystemExit(f"cannot read an image from {path}")
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    pixels = []
    for y in range(height):
        for x in range(width):
            colour = image.pixelColor(x, y)
            pixels.append((colour.red(), colour.green(), colour.blue(), colour.alpha()))
    return width, height, pixels


def background_of(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> Colour:
    """The colour most pixels have — for the icons here, the white page."""
    counts: dict[Colour, int] = {}
    for red, green, blue, alpha in pixels:
        if alpha == 0:
            continue
        counts[(red, green, blue)] = counts.get((red, green, blue), 0) + 1
    if not counts:
        return (0, 0, 0)
    return max(counts.items(), key=lambda item: item[1])[0]


def sample(
    width: int,
    height: int,
    pixels: list[tuple[int, int, int, int]],
    size: int,
    background: Colour,
    tolerance: int,
    coverage: float,
) -> list[list[Colour | None]]:
    """The picture as a `size × size` grid of *ink* colours.

    A cell is the mean of the pixels that are **not** the page: averaging the
    page in as well turns a thin dark outline into light grey, and a 16×16 mouse
    becomes a smudge (measured — the first version of this tool did exactly
    that).  A cell whose ink covers less than `coverage` of its area stays empty,
    which is what keeps the outline one cell wide instead of two.
    """
    grid: list[list[Colour | None]] = []
    for row in range(size):
        cells: list[Colour | None] = []
        y1 = row * height // size
        y2 = max((row + 1) * height // size, y1 + 1)
        for column in range(size):
            x1 = column * width // size
            x2 = max((column + 1) * width // size, x1 + 1)
            total = [0, 0, 0]
            ink = 0
            area = 0
            for y in range(y1, min(y2, height)):
                base = y * width
                for x in range(x1, min(x2, width)):
                    red, green, blue, alpha = pixels[base + x]
                    area += 1
                    if alpha == 0 or is_background((red, green, blue), background, tolerance):
                        continue
                    total[0] += red
                    total[1] += green
                    total[2] += blue
                    ink += 1
            if area == 0 or ink / area < coverage:
                cells.append(None)
            else:
                cells.append((total[0] // ink, total[1] // ink, total[2] // ink))
        grid.append(cells)
    return grid


def distance(first: Colour, second: Colour) -> int:
    """Squared distance between two colours."""
    return sum((a - b) ** 2 for a, b in zip(first, second))


def is_background(colour: Colour, background: Colour, tolerance: int) -> bool:
    return max(abs(a - b) for a, b in zip(colour, background)) <= tolerance


def background_of_old(
    grid: list[list[Colour | None]],
) -> Colour:
    counts: dict[Colour, int] = {}
    for row in grid:
        for colour in row:
            if colour is not None:
                counts[colour] = counts.get(colour, 0) + 1
    if not counts:
        return (0, 0, 0)
    return max(counts.items(), key=lambda item: item[1])[0]


def median_cut(colours: list[Colour], count: int) -> list[Colour]:
    """`count` colours that stand for `colours`: split the widest channel in half."""
    boxes: list[list[Colour]] = [list(colours)]
    while len(boxes) < count:
        best: tuple[int, int, int] | None = None  # span, box index, channel
        for index, box in enumerate(boxes):
            if len(box) < 2:
                continue
            for channel in range(3):
                values = [colour[channel] for colour in box]
                span = max(values) - min(values)
                if best is None or span > best[0]:
                    best = (span, index, channel)
        if best is None or best[0] == 0:
            break
        _, index, channel = best
        box = sorted(boxes.pop(index), key=lambda colour: colour[channel])
        middle = len(box) // 2
        boxes.append(box[:middle])
        boxes.append(box[middle:])

    palette = []
    for box in boxes:
        if not box:
            continue
        palette.append(
            (
                sum(colour[0] for colour in box) // len(box),
                sum(colour[1] for colour in box) // len(box),
                sum(colour[2] for colour in box) // len(box),
            )
        )
    return sorted(palette)


def quantise(
    grid: list[list[Colour | None]], palette: list[Colour], background: Colour, tolerance: int
) -> list[list[Colour | None]]:
    """Every cell to its nearest palette colour, background cells to `None`."""
    result: list[list[Colour | None]] = []
    for row in grid:
        cells: list[Colour | None] = []
        for colour in row:
            if colour is None or is_background(colour, background, tolerance):
                cells.append(None)
                continue
            cells.append(min(palette, key=lambda candidate: distance(colour, candidate)))
        result.append(cells)
    return result


def merge_rectangles(grid: list[list[Colour | None]]) -> list[tuple[int, int, int, int, Colour]]:
    """Greedy maximal rectangles: right first, then down while the row matches."""
    size = len(grid)
    covered = [[False] * size for _ in range(size)]

    def free(y: int, x: int) -> bool:
        return 0 <= y < size and 0 <= x < size and not covered[y][x] and grid[y][x] is not None

    rectangles: list[tuple[int, int, int, int, Colour]] = []
    for y in range(size):
        for x in range(size):
            colour = grid[y][x]
            if colour is None or covered[y][x]:
                continue
            x2 = x
            while free(y, x2 + 1) and grid[y][x2 + 1] == colour:
                x2 += 1
            y2 = y
            while all(free(y2 + 1, column) and grid[y2 + 1][column] == colour
                      for column in range(x, x2 + 1)):
                y2 += 1
            for row in range(y, y2 + 1):
                for column in range(x, x2 + 1):
                    covered[row][column] = True
            rectangles.append((x, y, x2, y2, colour))
    return rectangles


def preview(
    grid: list[list[Colour | None]], palette: list[Colour], path: pathlib.Path, scale: int
) -> None:
    """The quantised grid as PNG: the picture as the canvas will draw it."""
    size = len(grid)
    pixels = bytearray()
    for row in grid:
        for colour in row:
            if colour is None:
                pixels += bytes((0, 0, 0, 0xFF))
            else:
                pixels += bytes((colour[0], colour[1], colour[2], 0xFF))
    write_png(path, size, size, bytes(pixels), max(1, scale))


def pld_name(name: str) -> str:
    return name


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--image", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--size", type=int, default=16, help="the grid, in cells (16)")
    parser.add_argument("--colors", type=int, default=6, help="how many colours to keep")
    parser.add_argument("--tolerance", type=int, default=24,
                        help="how close to the background is still background")
    parser.add_argument("--coverage", type=float, default=0.30,
                        help="how much of a cell has to be ink for the cell to be drawn")
    parser.add_argument("--background", default="auto", help="a colour `R,G,B` or `auto`")
    parser.add_argument("--preview", type=pathlib.Path, help="a folder for preview PNGs")
    parser.add_argument("--scale", type=int, default=12, help="preview magnification")
    args = parser.parse_args(argv[1:])

    facts: list[str] = []
    summary: list[str] = []
    for spec in args.image:
        if "=" not in spec:
            raise SystemExit(f"--image wants NAME=PATH, got {spec!r}")
        name, path_text = spec.split("=", 1)
        path = pathlib.Path(path_text)
        width, height, pixels = load_rgba(path)
        background = background_of(width, height, pixels)
        if args.background != "auto":
            red, green, blue = (int(part) for part in args.background.split(","))
            background = (red, green, blue)
        grid = sample(width, height, pixels, args.size, background, args.tolerance,
                      args.coverage)
        kept = [colour for row in grid for colour in row if colour is not None]
        palette = median_cut(kept, args.colors) if kept else []
        quantised = quantise(grid, palette, background, args.tolerance)
        rectangles = merge_rectangles(quantised)
        for x1, y1, x2, y2, (red, green, blue) in rectangles:
            value = (red << 16) | (green << 8) | blue
            facts.append(
                f"картинка({pld_name(name)}, {x1}, {y1}, {x2}, {y2}, {value})."
            )
        summary.append(f"  {name}: {len(rectangles)} rectangles, {len(palette)} colours, "
                       f"source {width}x{height}")
        if args.preview is not None:
            preview(quantised, palette, args.preview / f"{pld_name(name)}.png", args.scale)

    header = [
        f"% Картинки для лабиринта: сетка {args.size}×{args.size}, сгенерировано",
        "% tools/image_to_pld.py из ai/_ref/images.  Руками не править: перегенерация",
        "% перепишет файл.  Каждая картинка — клетка, координаты от 0 до "
        f"{args.size - 1}.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(header + facts) + "\n", encoding="utf-8", newline="\n")
    print(f"written : {args.out} ({len(facts)} facts)")
    for line in summary:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
