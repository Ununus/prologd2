"""Turn a picture into `картинка/6` facts on a grid that keeps its shape.

    python tools/image_to_pld.py \
        --image мышь=ai/_ref/images/mouse.png --cell 8 --canvas-cell 2 \
        --image стена=ai/_ref/images/wall.png --cell 4 --canvas-cell 2 \
        --out examples/problems/maze/maze.images.pld

A cell is a square of `--cell` pixels of the **picture** (`16` by default), and the
grid is however many whole cells fit: 600x800 is 37x50 cells, so the drawing has the
picture's own proportions instead of being squeezed into a square.  What is left over
is trimmed from *both* sides — 600 px is 37 cells of 16 px plus 8 px, four off each
edge — because a half cell is a cell of another colour and another size.

The drawing side is the second number: `--canvas-cell` says how many dots of the
canvas one cell takes (`4` by default, or `auto`, which sizes the picture to the
canvas the engine starts with).  So 37x50 cells at 4 dots is a 148x200 canvas.

Three steps keep the number of draw calls small — a picture drawn pixel by pixel
would be 1850 `ЗАКРАСКА` calls for that 600x800:

1. **average** every cell over the pixels it covers (a box filter, not a point
   sample: a 1-pixel eye survives, a single stray pixel does not);
2. **quantise** the result to `--colors` colours (median cut) — a cell rarely needs
   more, and every extra colour is extra rectangles;
3. **merge** neighbouring cells of one colour into rectangles, greedily: the run
   grows to the right first, then down while the whole row matches.  A brick wall
   of one colour becomes one rectangle per row instead of sixteen.

Pixels close to the background (`--tolerance`, per channel) are left out
entirely, so an icon's white page does not erase what is drawn under it.
`--keep-background` turns that off: the page is painted like everything else, so the
picture covers its whole grid — what a photograph or a texture wants, and the opposite
of a sprite that has to sit on top of what is already drawn.

The output is a Prolog file of plain facts, one per rectangle, in cell coordinates:

    картинка(мышь, 3, 12, 5, 14, 8421504).

A program draws them with `ЗАКРАСКА(X1, Y1, X2, Y2, Цвет)` — `maze.graphics.pld`
adds the corner of the maze cell to every coordinate and its sprite has to be 16x16
cells, so the maze asks for `--cell 14` on a 228-pixel picture (228 = 16 * 14 + 4) and
`--cell 4` on a 64-pixel one.  `--cell` may be a comma list, one value per `--image`.

Without `--out` the tool prints a whole program instead: a canvas the size of the
picture, the facts, `нарисовать_картинку/1` and a `?` question calling it.  That is
what the window's «Сконвертировать картинку…» puts into a tab.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from render_graphics import write_png  # noqa: E402  (the PNG writer lives there)

#: One cell of the picture is `--cell` square pixels of it; 16 unless asked otherwise.
DEFAULT_CELL = 16
MIN_CELL, MAX_CELL = 1, 64

#: Dots of the canvas one cell takes.  `auto` picks the largest cell that keeps the
#: longer side near `CANVAS_COMFORT` — the canvas the engine starts with — and the
#: shorter side at least `MIN_CANVAS` dots.
CANVAS_COMFORT = 600
MIN_CANVAS_CELL, MAX_CANVAS_CELL = 1, 32
#: What `:- ХОЛСТ` accepts: the engine's `kMinScreen` and `kMaxScreen`.
MIN_CANVAS, MAX_CANVAS = 16, 2048

Colour = tuple[int, int, int]


def plan(width: int, height: int, cell: int) -> tuple[int, int, int, int]:
    """The grid a picture makes: cells across and down, and where the window starts.

    The grid follows the picture instead of being a fixed square, so the drawing keeps
    the picture's shape.  What does not fill a whole cell is trimmed from *both* sides:
    600 px with a cell of 16 is 37 cells, and the 8 px left over are 4 off each side.
    """
    cols, rows = width // cell, height // cell
    return cols, rows, (width - cols * cell) // 2, (height - rows * cell) // 2


def auto_canvas_cell(cols: int, rows: int) -> int:
    """How many dots a cell should take: the picture fills the canvas it is shown on.

    `roomy` is what makes the longer side reach `CANVAS_COMFORT`; `enough` is what the
    shorter side needs to stay above the engine's minimum.  A strip of a picture is the
    case where the second one wins.
    """
    long_side, short_side = max(cols, rows), min(cols, rows)
    roomy = CANVAS_COMFORT // long_side
    enough = -(-MIN_CANVAS // short_side)  # ceil: the short side has to reach 16 dots
    return max(MIN_CANVAS_CELL, min(MAX_CANVAS_CELL, max(roomy, enough)))



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
    cell: int,
    left: int,
    top: int,
    cols: int,
    rows: int,
    background: Colour | None,
    tolerance: int,
    coverage: float,
) -> list[list[Colour | None]]:
    """The picture as a `rows × cols` grid of *ink* colours.

    Every cell is the same `cell × cell` square of the picture, starting at the
    centred window `plan()` chose, so a cell means the same thing everywhere — the
    old square grid had to stretch cells of 18 and 19 px to make them fit.

    A cell is the mean of the pixels that are **not** the page: averaging the
    page in as well turns a thin dark outline into light grey, and a 16×16 mouse
    becomes a smudge (measured — the first version of this tool did exactly
    that).  With `background` empty there is no page to leave out and every pixel
    counts, which is what `--keep-background` asks for.  A cell whose ink covers
    less than `coverage` of its area stays empty, which is what keeps the outline
    one cell wide instead of two.
    """
    grid: list[list[Colour | None]] = []
    for row in range(rows):
        cells: list[Colour | None] = []
        y1 = top + row * cell
        for column in range(cols):
            x1 = left + column * cell
            total = [0, 0, 0]
            ink = 0
            for y in range(y1, y1 + cell):
                base = y * width
                for x in range(x1, x1 + cell):
                    red, green, blue, alpha = pixels[base + x]
                    # A fully transparent pixel is nothing at all, page or not.
                    if alpha == 0 or (background is not None
                                      and is_background((red, green, blue), background,
                                                        tolerance)):
                        continue
                    total[0] += red
                    total[1] += green
                    total[2] += blue
                    ink += 1
            # `ink == 0` is a cell of nothing: with `--coverage 0` every cell would
            # otherwise pass the test and the mean would divide by zero.
            if ink == 0 or ink / (cell * cell) < coverage:
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
    grid: list[list[Colour | None]],
    palette: list[Colour],
    background: Colour | None,
    tolerance: int,
) -> list[list[Colour | None]]:
    """Every cell to its nearest palette colour, background cells to `None`."""
    result: list[list[Colour | None]] = []
    for row in grid:
        cells: list[Colour | None] = []
        for colour in row:
            if colour is None or (background is not None
                                  and is_background(colour, background, tolerance)):
                cells.append(None)
                continue
            ink: Colour = colour  # the lambda cannot see the narrowing above
            cells.append(min(palette, key=lambda candidate: distance(ink, candidate)))
        result.append(cells)
    return result


def merge_rectangles(grid: list[list[Colour | None]]) -> list[tuple[int, int, int, int, Colour]]:
    """Greedy maximal rectangles: right first, then down while the row matches."""
    rows, cols = len(grid), len(grid[0])
    covered = [[False] * cols for _ in range(rows)]

    def free(y: int, x: int) -> bool:
        return 0 <= y < rows and 0 <= x < cols and not covered[y][x] and grid[y][x] is not None

    rectangles: list[tuple[int, int, int, int, Colour]] = []
    for y in range(rows):
        for x in range(cols):
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
    rows, cols = len(grid), len(grid[0])
    pixels = bytearray()
    for row in grid:
        for colour in row:
            if colour is None:
                pixels += bytes((0, 0, 0, 0xFF))
            else:
                pixels += bytes((colour[0], colour[1], colour[2], 0xFF))
    write_png(path, cols, rows, bytes(pixels), max(1, scale))


def pld_name(name: str) -> str:
    return name


def drawing_lines(canvas_cell: int) -> list[str]:
    """The predicate that paints the facts, broken the way `prologd --format soft` is.

    A cell of one dot needs no arithmetic, and `X1 * 1 + 0` in a teaching example is
    only noise.  The head line ends on column 80 for a cell of two digits, which is
    why the first goal shares it; the rest is what the formatter packs on the lines
    under it.
    """
    if canvas_cell == 1:
        head, middle = "Слева is X1,", "Справа is X2, Сверху is Y1, Снизу is Y2,"
    else:
        last = canvas_cell - 1
        head = f"Слева is X1 * {canvas_cell},"
        middle = (
            f"Справа is X2 * {canvas_cell} + {last}, "
            f"Сверху is Y1 * {canvas_cell}, "
            f"Снизу is Y2 * {canvas_cell} + {last},"
        )
    return [
        "% Рисование: один факт - один прямоугольник на холсте.  Клетки фактов",
        "% считаются от левого верхнего угла, как в самой картинке.",
        f"нарисовать_картинку(Имя):-картинка(Имя, X1, Y1, X2, Y2, Цвет), {head}",
        f"\t{middle}",
        "\tЗАКРАСКА(Слева, Сверху, Справа, Снизу, Цвет), ЛОЖЬ.",
        "нарисовать_картинку(_).",
        "",
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--image", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--out", type=pathlib.Path,
                        help="write the facts here; without it a whole program goes to stdout")
    parser.add_argument("--cell", default=str(DEFAULT_CELL),
                        help=f"one cell, in picture pixels, {MIN_CELL}..{MAX_CELL} "
                             f"({DEFAULT_CELL}); a comma list gives one per --image")
    parser.add_argument("--canvas-cell", default="auto",
                        help=f"dots of the canvas per cell, {MIN_CANVAS_CELL}.."
                             f"{MAX_CANVAS_CELL}, or `auto`")
    parser.add_argument("--colors", type=int, default=6, help="how many colours to keep")
    parser.add_argument("--tolerance", type=int, default=24,
                        help="how close to the background is still background")
    parser.add_argument("--coverage", type=float, default=0.30,
                        help="how much of a cell has to be ink for the cell to be drawn")
    parser.add_argument("--background", default="auto", help="a colour `R,G,B` or `auto`")
    parser.add_argument("--keep-background", action="store_true",
                        help="paint the page too instead of leaving those cells empty")
    parser.add_argument("--preview", type=pathlib.Path, help="a folder for preview PNGs")
    parser.add_argument("--scale", type=int, default=12, help="preview magnification")
    args = parser.parse_args(argv[1:])

    if args.keep_background and args.background != "auto":
        raise SystemExit(
            "--keep-background и --background вместе: фон либо отбрасывается "
            "выбранного цвета, либо не отбрасывается вовсе"
        )

    cells = [int(part) for part in args.cell.split(",")]
    for value in cells:
        if not MIN_CELL <= value <= MAX_CELL:
            raise SystemExit(f"--cell {value}: {MIN_CELL}..{MAX_CELL} only")
    if len(cells) == 1:
        cells = cells * len(args.image)
    elif len(cells) != len(args.image):
        raise SystemExit(f"--cell wants one value or {len(args.image)}, got {len(cells)}")
    wanted = args.canvas_cell.strip()
    asked_canvas_cell: int | None = None
    if wanted.lower() != "auto":
        asked_canvas_cell = int(wanted)
        if not MIN_CANVAS_CELL <= asked_canvas_cell <= MAX_CANVAS_CELL:
            raise SystemExit(
                f"--canvas-cell {asked_canvas_cell}: `auto` or "
                f"{MIN_CANVAS_CELL}..{MAX_CANVAS_CELL}"
            )

    blocks: list[list[str]] = []
    summary: list[str] = []
    order: list[str] = []
    grids: list[tuple[int, int]] = []
    facts_count = 0
    for spec, cell in zip(args.image, cells):
        if "=" not in spec:
            raise SystemExit(f"--image wants NAME=PATH, got {spec!r}")
        name, path_text = spec.split("=", 1)
        order.append(pld_name(name))
        path = pathlib.Path(path_text)
        width, height, pixels = load_rgba(path)
        cols, rows, left, top = plan(width, height, cell)
        if cols < 1 or rows < 1:
            raise SystemExit(
                f"{path}: картинка {width}x{height} меньше клетки {cell} - "
                f"уменьшите --cell"
            )
        grids.append((cols, rows))
        # `None` means «there is no page»: every pixel counts, and the drawing covers
        # the whole grid instead of only the ink.
        background: Colour | None = None
        if not args.keep_background:
            background = background_of(width, height, pixels)
            if args.background != "auto":
                red, green, blue = (int(part) for part in args.background.split(","))
                background = (red, green, blue)
        grid = sample(width, height, pixels, cell, left, top, cols, rows,
                      background, args.tolerance, args.coverage)
        kept = [colour for row in grid for colour in row if colour is not None]
        palette = median_cut(kept, args.colors) if kept else []
        quantised = quantise(grid, palette, background, args.tolerance)
        rectangles = merge_rectangles(quantised)
        note = f"% {name}: {cols}x{rows} клеток по {cell} px"
        trimmed = (width - cols * cell, height - rows * cell)
        if trimmed != (0, 0):
            note += f", обрезано {trimmed[0]}x{trimmed[1]} px"
        note += f", {len(rectangles)} прямоугольников"
        facts = [note]
        for x1, y1, x2, y2, (red, green, blue) in rectangles:
            value = (red << 16) | (green << 8) | blue
            facts.append(
                f"картинка({pld_name(name)}, {x1}, {y1}, {x2}, {y2}, {value})."
            )
        facts.append("")
        facts_count += len(rectangles)
        blocks.append(facts)
        summary.append(f"  {name}: {cols}x{rows} клеток по {cell} px, "
                       f"{len(rectangles)} прямоугольников, {len(palette)} цветов, "
                       f"исходник {width}x{height}")
        if args.preview is not None:
            preview(quantised, palette, args.preview / f"{pld_name(name)}.png", args.scale)

    header = [
        "% Картинки для программы: одна строка - один прямоугольник рисунка.",
        "% Сгенерировано tools/image_to_pld.py; координаты в клетках, от левого",
        "% верхнего угла картинки.",
        f"% Настройки: цвета {args.colors}, порог фона {args.tolerance}, "
        f"доля «чернил» {args.coverage:g}, "
        f"фон {'не отбрасывается' if args.keep_background else args.background}.",
        "",
    ]
    flat = [line for block in blocks for line in block]
    # Facts only go to a file: `maze.images.pld` is imported, and a `:- ХОЛСТ` or a
    # question would act on the program that imports it (ADR-034 keeps directives).
    # The blank line a block ends with separates pictures; at the end of the file it
    # is a line the soft formatter would drop, and one test checks that it does not
    # have anything to drop.
    text = "\n".join(header + flat).rstrip("\n") + "\n"
    if args.out is None:
        # The window's «Сконвертировать картинку…» runs the tool this way and puts
        # what comes back straight into a tab, so the answer is a *program*: a canvas
        # the size of the picture, the facts, a predicate that draws them, and a
        # question that calls it.  Запустить — и картинка видна.
        cols_max = max(cols for cols, _rows in grids)
        rows_max = max(rows for _cols, rows in grids)
        canvas_cell = (auto_canvas_cell(cols_max, rows_max)
                       if asked_canvas_cell is None else asked_canvas_cell)
        width_dots, height_dots = cols_max * canvas_cell, rows_max * canvas_cell
        for side in (width_dots, height_dots):
            if not MIN_CANVAS <= side <= MAX_CANVAS:
                raise SystemExit(
                    f"холст {width_dots}x{height_dots}: сторона {side} вне пределов "
                    f"{MIN_CANVAS}..{MAX_CANVAS} - смените --canvas-cell"
                    + (" или --cell" if asked_canvas_cell is None else "")
                )
        canvas_lines = [
            f"% Холст: {cols_max}x{rows_max} клеток по {canvas_cell} точек.",
            f":- ХОЛСТ({height_dots}, {width_dots}).",
            "",
        ]
        questions = [f"?нарисовать_картинку({name})." for name in order] + [""]
        #
        # A process without a console gets a pipe that Python encodes with the system
        # ANSI code page (cp1252 here) — and this text is Cyrillic, so the encoding is
        # named outright instead of dying on the first `картинка(`.  The newline is
        # named too: the default would hand the window a tab with CRLF, and every
        # source in this repository is LF.
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", newline="\n")
        program = (header + canvas_lines + flat + drawing_lines(canvas_cell) + questions)
        print("\n".join(program), end="")
        for line in summary:
            print(line, file=sys.stderr)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"written : {args.out} ({facts_count} facts)")
    for line in summary:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
