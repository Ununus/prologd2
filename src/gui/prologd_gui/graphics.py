"""The picture the graphics predicates draw, without Qt.

The interpreter keeps the pixels (a `getPixel` and a `ЗАКРАСКА` read cells from
inside a built-in) and reports every primitive as it is drawn, so this module has
one job: draw the same primitive, the same way, into a buffer a widget can show.

The rasterising rules are written twice on purpose — here and in
`src/prlib/src/graphics.cpp`, where the engine draws the same primitives — and
they are pinned to each other by `protocol_smoke.py`, which draws a program,
asks the interpreter for the finished bitmap and replays the events it received
into a `Canvas`: the two pictures have to match cell by cell.  That is why the
line is Bresenham, why the ellipse is computed from its parametric equation with
`math.floor(value + 0.5)`, and why a coordinate is clamped before any arithmetic
touches it.

A cell holds the colour *value* the program wrote, exactly like the engine's
buffer, so a snapshot and a replayed picture are comparable.  Turning a value
into a visible colour is `color_for`, and it is the only thing here that knows
about colours.
"""

from __future__ import annotations

import base64
import math
import struct
from array import array

#: The screen of the original interpreter — `kMaxGrX`/`kMaxGrY` in the engine.
MAX_GR_X = 1024
MAX_GR_Y = 768

#: How far outside the screen a coordinate is pulled back before it is used, the
#: same number as `kCoordinateLimit` in the engine: a program may draw from
#: `10**18`, and both sides have to compute the same clipped picture.
COORDINATE_LIMIT = 1_000_000

#: Every primitive the wire can carry (protocol 10).  A front-end that hears
#: something else is talking to a newer interpreter, and says so instead of
#: drawing a picture that is quietly wrong.
GRAPHICS_OPS = (
    "setPixel",
    "line",
    "rectangle",
    "ellipse",
    "floodFill",
    "clearView",
    "vertical",
    "horizontal",
)

#: The default colour value of an empty screen: black, which is what
#: `getPixel`/`ТОЧКА(X, Y, Ц)` reports for a cell nobody painted.
BLANK = 0


def color_for(value: int) -> str:
    """The colour of a cell value, as `#rrggbb`.

    The value *is* the colour: `0xRRGGBB`, which is what the graphics predicates
    take and what `ТОЧКА(X, Y, Цвет)` with a free colour hands back.  There is no
    palette any more (task_63): `0` is plain black, and the names a program wants
    (`красный`, `синий`, …) live in `stdlib/graphics.pld`, each one an `rgb/4` call —
    one definition of a colour for the library and the window both.  The mask is
    belt and braces: the interpreter refuses a value out of range, and a front-end
    that hears one from somewhere else still has to draw *something*.
    """
    return "#%06x" % (value & 0xFFFFFF)


def _rgba(value: int) -> bytes:
    """The four bytes of a cell's colour, in the order `QImage` wants them."""
    text = color_for(value)
    return bytes((int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16), 0xFF))


def _clamp(value: int) -> int:
    if value < -COORDINATE_LIMIT:
        return -COORDINATE_LIMIT
    if value > COORDINATE_LIMIT:
        return COORDINATE_LIMIT
    return int(value)


def _half_up(value: float) -> int:
    """`floor(value + 0.5)` — the engine's rounding rule, not Python's."""
    return int(math.floor(value + 0.5))


class Canvas:
    """The pixels of one interpreter session, and the ways to put them there.

    `values` is what the engine's own buffer holds (so `pixel` answers what
    `ТОЧКА(X, Y, Ц)` would), and `rgba` is the same picture as bytes a `QImage`
    can be built over — the widget wraps that buffer, so a drawing call costs a
    few writes and no copy.
    """

    def __init__(self, width: int = MAX_GR_X, height: int = MAX_GR_Y) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.values = array("I", bytes(4 * self.width * self.height))
        # Opaque from the start: a bytearray of zeros is *transparent* black, and
        # an untouched screen showed the desktop through the window.
        self.rgba = bytearray(_rgba(BLANK) * (self.width * self.height))

    # -- reading -----------------------------------------------------------
    def pixel(self, x: int, y: int) -> int:
        """The value of a cell; `0` outside the screen, like `getPixel`."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.values[y * self.width + x])
        return BLANK

    def to_rgba(self) -> bytes:
        """A copy of the picture, for saving or for a check."""
        return bytes(self.rgba)

    def filled_cells(self) -> int:
        """How many cells are not the blank colour — a picture's size, cheaply."""
        return sum(1 for value in self.values if value != BLANK)

    # -- writing -----------------------------------------------------------
    def clear(self, value: int = BLANK) -> None:
        """The whole screen in one colour (`ТОЧКА(X, Y, Цвет)` with two frees)."""
        self.values = array("I", [value & 0xFFFFFFFF]) * (self.width * self.height)
        self.rgba[:] = _rgba(value) * (self.width * self.height)

    def put(self, x: int, y: int, value: int) -> None:
        """One cell, clipped to the screen; nothing outside is written."""
        if 0 <= x < self.width and 0 <= y < self.height:
            index = y * self.width + x
            self.values[index] = value & 0xFFFFFFFF
            self.rgba[4 * index : 4 * index + 4] = _rgba(value)

    def line(self, x1: int, y1: int, x2: int, y2: int, value: int) -> None:
        """Bresenham, both ends included — the engine's `drawLine`."""
        left, top = _clamp(x1), _clamp(y1)
        right, bottom = _clamp(x2), _clamp(y2)
        dx = abs(right - left)
        dy = -abs(bottom - top)
        step_x = 1 if left < right else -1
        step_y = 1 if top < bottom else -1
        error = dx + dy
        x, y = left, top
        while True:
            self.put(x, y, value)
            if x == right and y == bottom:
                return
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x += step_x
            if doubled <= dx:
                error += dx
                y += step_y

    def rectangle(self, x1: int, y1: int, x2: int, y2: int, value: int) -> None:
        """The outline of the box, in any corner order."""
        left, right = sorted((_clamp(x1), _clamp(x2)))
        top, bottom = sorted((_clamp(y1), _clamp(y2)))
        self.line(left, top, right, top, value)
        self.line(left, bottom, right, bottom, value)
        self.line(left, top, left, bottom, value)
        self.line(right, top, right, bottom, value)

    def ellipse(self, x: int, y: int, rx: int, ry: int, value: int) -> None:
        """The outline of the ellipse centred at `(x, y)` with the radii `rx`/`ry`.

        Centre and radii, **not** a bounding box: `ОКРУЖНОСТЬ(X, Y, R, Цвет)`
        passes its four numbers straight through to the backend, and reading
        them as a box turned every circle of `examples/drawing.pld` into a line.
        """
        centre_x = _clamp(x)
        centre_y = _clamp(y)
        radius_x = abs(_clamp(rx))
        radius_y = abs(_clamp(ry))
        if radius_x < 1 and radius_y < 1:
            self.put(centre_x, centre_y, value)
            return
        if radius_x < 1:
            self.line(centre_x, centre_y - radius_y, centre_x, centre_y + radius_y, value)
            return
        if radius_y < 1:
            self.line(centre_x - radius_x, centre_y, centre_x + radius_x, centre_y, value)
            return
        for column in range(_half_up(centre_x - radius_x), _half_up(centre_x + radius_x) + 1):
            t = (column - centre_x) / radius_x
            offset = radius_y * math.sqrt(max(0.0, 1.0 - t * t))
            self.put(column, _half_up(centre_y - offset), value)
            self.put(column, _half_up(centre_y + offset), value)
        for row in range(_half_up(centre_y - radius_y), _half_up(centre_y + radius_y) + 1):
            t = (row - centre_y) / radius_y
            offset = radius_x * math.sqrt(max(0.0, 1.0 - t * t))
            self.put(_half_up(centre_x - offset), row, value)
            self.put(_half_up(centre_x + offset), row, value)

    def flood_fill(self, x: int, y: int, value: int) -> None:
        """Four-connected fill from a cell, stopping at a different colour."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        target = int(self.values[y * self.width + x])
        if target == value:
            return
        pending = [(x, y)]
        while pending:
            cx, cy = pending.pop()
            if not (0 <= cx < self.width and 0 <= cy < self.height):
                continue
            index = cy * self.width + cx
            if int(self.values[index]) != target:
                continue
            self.values[index] = value & 0xFFFFFFFF
            self.rgba[4 * index : 4 * index + 4] = _rgba(value)
            pending.append((cx + 1, cy))
            pending.append((cx - 1, cy))
            pending.append((cx, cy + 1))
            pending.append((cx, cy - 1))

    # -- the wire ----------------------------------------------------------
    def draw(self, event: dict) -> None:
        """Draws one `graphics` event, as the session received it."""
        op = str(event.get("op", ""))
        value = int(event.get("color", BLANK)) & 0xFFFFFFFF
        if op == "setPixel":
            self.put(_clamp(event["x"]), _clamp(event["y"]), value)
        elif op == "line":
            self.line(event["x1"], event["y1"], event["x2"], event["y2"], value)
        elif op == "rectangle":
            self.rectangle(event["x1"], event["y1"], event["x2"], event["y2"], value)
        elif op == "ellipse":
            self.ellipse(event["x"], event["y"], event["rx"], event["ry"], value)
        elif op == "floodFill":
            self.flood_fill(_clamp(event["x"]), _clamp(event["y"]), value)
        elif op == "clearView":
            self.clear(value)
        elif op == "vertical":
            self.line(event["x1"], event["y1"], event["x2"], event["y2"], value)
        elif op == "horizontal":
            self.line(event["x1"], event["y1"], event["x2"], event["y2"], value)
        else:
            # The session refuses an operation it does not know before this is
            # reached; a silent no-op here would draw a picture that is quietly
            # missing a primitive.
            raise ValueError(f"неизвестная графическая операция: {op!r}")

    def apply_bitmap(self, width: int, height: int, data: bytes) -> None:
        """Replaces the picture with a `bitmap` event's payload.

        A window that was closed (or not open yet) while the program drew asks
        for this instead of starting blank.  The payload is four bytes per cell,
        least significant first, exactly the engine's own `unsigned` values.
        """
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0 or len(data) != 4 * width * height:
            raise ValueError(
                f"снимок {width}×{height} не совпадает с данными ({len(data)} байт)"
            )
        self.width = width
        self.height = height
        self.values = array("I")
        self.values.frombytes(data)
        # A picture uses a handful of colours, so the RGBA buffer is built by
        # looking each *value* up once instead of converting every cell.
        patterns = {value: _rgba(int(value)) for value in set(self.values)}
        self.rgba = bytearray(b"".join([patterns[value] for value in self.values]))

    def snapshot_bytes(self) -> bytes:
        """The payload a `bitmap` event would carry for this picture."""
        return struct.pack("<%dI" % (self.width * self.height), *self.values)


def decode_bitmap(event: dict) -> tuple[int, int, bytes]:
    """`(width, height, data)` of a `bitmap` event, or a `ValueError`.

    The size is checked here and not only where the picture is painted: a
    snapshot that does not match its own numbers is a broken event, and a window
    should be told so rather than shown a picture that is out of step with the
    interpreter.
    """
    try:
        width = int(event["width"])
        height = int(event["height"])
        raw = event["data"]
    except (KeyError, TypeError, ValueError) as missing:
        raise ValueError(f"неполный снимок: {event!r}") from missing
    if not isinstance(raw, str):
        raise ValueError("снимок должен нести data строкой base64")
    if width <= 0 or height <= 0:
        raise ValueError(f"снимок {width}×{height} невозможен")
    data = base64.b64decode(raw)
    if len(data) != 4 * width * height:
        raise ValueError(
            f"снимок {width}×{height} не совпадает с данными ({len(data)} байт)"
        )
    return width, height, data
