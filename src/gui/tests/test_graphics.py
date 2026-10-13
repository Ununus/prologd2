"""Checks the picture the graphics predicates draw (no Qt needed).

    python src/gui/tests/test_graphics.py

The canvas is the front-end half of task_45: the engine keeps the pixels and
reports every primitive, and this module draws the same primitives into a buffer
the window can show.  Two things are checked here — that each primitive lands
where the engine says it does, and that the *same* drawing rules are in force on
both sides of the pipe.

The second one needs the interpreter, so it is skipped when no build is found:
a program draws, the finished bitmap comes back in a snapshot, and the events the
same session reported are replayed into a canvas.  The two pictures have to match
cell by cell — that is what keeps a Bresenham line here from being a
different-but-reasonable line there.
"""

from __future__ import annotations

import base64
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import graphics, protocol  # noqa: E402


def canvas(width: int = 16, height: int = 12) -> graphics.Canvas:
    return graphics.Canvas(width, height)


def drawn(plane: graphics.Canvas, value: int = 1) -> list[tuple[int, int]]:
    """Every cell of a given value, as `(x, y)` pairs — a small canvas only."""
    return [
        (index % plane.width, index // plane.width)
        for index, cell in enumerate(plane.values)
        if cell == value
    ]


def test_a_point_lands_in_the_cell_it_names() -> None:
    plane = canvas()
    plane.draw({"op": "setPixel", "x": 3, "y": 4, "color": 7})
    assert plane.pixel(3, 4) == 7
    assert plane.pixel(4, 3) == 0
    assert drawn(plane, 7) == [(3, 4)]

    # Outside the screen: nothing is written, and a read answers black, exactly
    # like the engine's own buffer.
    plane.draw({"op": "setPixel", "x": -1, "y": 4, "color": 7})
    plane.draw({"op": "setPixel", "x": 16, "y": 4, "color": 7})
    plane.draw({"op": "setPixel", "x": 3, "y": 12, "color": 7})
    assert drawn(plane, 7) == [(3, 4)]
    assert plane.pixel(-1, 0) == 0
    assert plane.pixel(0, 12) == 0
    print("ok: a point lands in the cell it names, and the screen clips")


def test_a_line_includes_both_of_its_ends() -> None:
    plane = canvas()
    plane.draw({"op": "line", "x1": 0, "y1": 0, "x2": 6, "y2": 3, "color": 5})
    cells = drawn(plane, 5)
    assert (0, 0) in cells and (6, 3) in cells
    assert len(cells) == 7  # one per column of the run
    assert sorted(cells) == cells, cells

    square = canvas()
    square.draw({"op": "line", "x1": 0, "y1": 0, "x2": 11, "y2": 11, "color": 5})
    assert drawn(square, 5) == [(index, index) for index in range(12)]
    print("ok: a line includes both of its ends")


def test_a_rectangle_outlines_its_box() -> None:
    plane = canvas()
    plane.draw({"op": "rectangle", "x1": 2, "y1": 1, "x2": 6, "y2": 4, "color": 3})
    assert plane.pixel(2, 1) == 3 and plane.pixel(6, 4) == 3
    assert plane.pixel(4, 1) == 3 and plane.pixel(2, 3) == 3
    assert plane.pixel(4, 3) == 0, "the outline must not fill the box"
    assert len(drawn(plane, 3)) == 2 * 5 + 2 * 2

    reversed_corners = canvas()
    reversed_corners.draw({"op": "rectangle", "x1": 6, "y1": 4, "x2": 2, "y2": 1, "color": 3})
    assert reversed_corners.values == plane.values
    print("ok: a rectangle outlines its box, whatever order its corners come in")


def test_an_ellipse_is_a_centre_and_two_radii() -> None:
    plane = canvas(width=24, height=18)
    plane.draw({"op": "ellipse", "x": 10, "y": 8, "rx": 8, "ry": 6, "color": 4})
    assert plane.pixel(2, 8) == 4, "the left extreme"
    assert plane.pixel(18, 8) == 4, "the right one"
    assert plane.pixel(10, 2) == 4, "the top one"
    assert plane.pixel(10, 14) == 4, "the bottom one"
    assert plane.pixel(10, 8) == 0, "an outline, not a disc"
    assert plane.pixel(1, 1) == 0, "and nothing outside it"

    # The outline is closed: every row between the extremes carries a cell, so a
    # fill inside cannot leak through a gap in the curve.
    for y in range(2, 15):
        assert any(plane.pixel(x, y) == 4 for x in range(0, 20)), f"row {y} is open"

    # A radius of nought draws the segment the shape shrank to.
    flat = canvas()
    flat.draw({"op": "ellipse", "x": 5, "y": 4, "rx": 3, "ry": 0, "color": 4})
    assert flat.pixel(2, 4) == 4 and flat.pixel(8, 4) == 4
    assert len(drawn(flat, 4)) == 7
    print("ok: an ellipse is a centre and two radii, and its outline has no gaps")


def test_a_fill_stops_at_a_wall() -> None:
    plane = canvas()
    plane.draw({"op": "rectangle", "x1": 2, "y1": 1, "x2": 12, "y2": 9, "color": 5})
    plane.draw({"op": "floodFill", "x": 6, "y": 4, "color": 7})
    inside = [(x, y) for y in range(2, 9) for x in range(3, 12)]
    assert all(plane.pixel(x, y) == 7 for x, y in inside)
    assert plane.pixel(2, 1) == 5, "the wall stays"
    assert plane.pixel(1, 0) == 0, "and the outside is not touched"

    # The outside is a region of its own: a fill there goes round the frame.
    plane.draw({"op": "floodFill", "x": 0, "y": 0, "color": 9})
    assert plane.pixel(0, 0) == 9 and plane.pixel(0, 11) == 9
    assert plane.pixel(2, 1) == 5
    assert plane.pixel(6, 4) == 7

    # Filling with the colour that is already there changes nothing, and a fill
    # started off the screen has no area at all.
    plane.draw({"op": "floodFill", "x": 6, "y": 4, "color": 7})
    assert plane.pixel(6, 4) == 7
    plane.draw({"op": "floodFill", "x": -3, "y": 0, "color": 1})
    assert plane.pixel(0, 0) == 9
    print("ok: a fill stops at a wall, and a fill of the same colour does nothing")


def test_a_run_and_the_whole_screen() -> None:
    plane = canvas()
    plane.draw({"op": "vertical", "x1": 5, "y1": 1, "x2": 5, "y2": 4, "color": 8})
    assert [plane.pixel(5, y) for y in range(6)] == [0, 8, 8, 8, 8, 0]
    plane.draw({"op": "horizontal", "x1": 0, "y1": 6, "x2": 15, "y2": 6, "color": 9})
    assert all(plane.pixel(x, 6) == 9 for x in range(16))

    plane.draw({"op": "clearView", "color": 11})
    assert plane.filled_cells() == 16 * 12
    assert plane.pixel(0, 0) == 11 and plane.pixel(15, 11) == 11

    # A coordinate far outside the screen is clamped, not wrapped: the engine
    # does the same, and a line that crosses the screen still crosses it.
    far = canvas()
    far.draw({"op": "line", "x1": 0, "y1": 0, "x2": 10**18, "y2": 0, "color": 4})
    assert far.pixel(15, 0) == 4 and far.pixel(15, 1) == 0
    print("ok: a run, a whole-screen clear, and a coordinate far away")


def test_a_colour_value_becomes_a_colour_one_way() -> None:
    # task_63: the palette is gone and the value *is* the colour, so `4` is a
    # nearly black blue rather than "dark red"; the names live in the library.
    assert graphics.color_for(0) == "#000000"
    assert graphics.color_for(4) == "#000004"
    assert graphics.color_for(0xFFFFFF) == "#ffffff"
    assert graphics.color_for(0xFF0000) == "#ff0000"
    assert graphics.color_for(0x00FF00) == "#00ff00"

    plane = canvas(width=2, height=1)
    # An untouched screen is opaque black, not transparent: the window would show
    # the desktop through it otherwise.
    assert plane.to_rgba() == bytes((0, 0, 0, 0xFF)) * 2
    plane.draw({"op": "setPixel", "x": 0, "y": 0, "color": 0xAA0000})
    plane.draw({"op": "setPixel", "x": 1, "y": 0, "color": 0xFF0000})
    assert plane.to_rgba() == bytes((0xAA, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0xFF))
    print("ok: a colour value is the colour the program wrote")


def test_a_snapshot_replaces_the_picture() -> None:
    plane = canvas(width=4, height=2)
    plane.apply_bitmap(4, 2, (1).to_bytes(4, "little") * 8)
    assert plane.width == 4 and plane.height == 2
    assert plane.pixel(0, 0) == 1 and plane.pixel(3, 1) == 1
    assert plane.to_rgba()[:4] == bytes((0x00, 0x00, 0x01, 0xFF))  # the value 1

    # The payload a snapshot carries is the payload the engine sends: the bytes
    # go back exactly as they came.
    payload = plane.snapshot_bytes()
    again = canvas()
    again.apply_bitmap(4, 2, payload)
    assert again.values == plane.values

    decoded = graphics.decode_bitmap(
        {"width": 4, "height": 2, "data": base64.b64encode(payload).decode()}
    )
    assert decoded == (4, 2, payload)

    for broken in ({"width": 4, "height": 2, "data": "AAAA"}, {"height": 2, "data": "AAAA"}):
        try:
            graphics.decode_bitmap(broken)
        except ValueError:
            pass
        else:
            raise AssertionError(f"a broken snapshot was accepted: {broken}")
    try:
        plane.apply_bitmap(3, 3, payload)
    except ValueError:
        pass
    else:
        raise AssertionError("a snapshot of the wrong size was accepted")
    print("ok: a snapshot replaces the picture, and a broken one is refused")


def test_an_unknown_primitive_is_refused() -> None:
    plane = canvas()
    try:
        plane.draw({"op": "spray", "x": 1, "y": 1, "color": 1})
    except ValueError as refused:
        assert "spray" in str(refused)
    else:
        raise AssertionError("an unknown operation was drawn")
    assert not drawn(plane, 1)
    print("ok: an unknown primitive is refused, not drawn")


# ---------------------------------------------------------------------------
# The two rasterisers are pinned to each other (needs a build)
# ---------------------------------------------------------------------------
def find_executable() -> str | None:
    """The engine the window itself would run (`prologd_gui.paths`, task_75)."""
    from prologd_gui import paths

    executable = paths.interpreter()
    return executable if pathlib.Path(executable).is_file() else None


#: A program that draws one of everything: a whole-screen fill to start from, a
#: point, two diagonals, a run of each kind, a circle, a frame with a fill inside
#: it, and one more point at the end.  The last picture keeps a lot of non-black
#: cells, so the comparison below is not two empty screens agreeing with each
#: other.
PICTURE = (
    "?ТОЧКА(X, Y, 3).\n"                # the whole screen in one colour
    "?ТОЧКА(3, 4, 1).\n"
    "?ЛИНИЯ(0, 0, 40, 25, 2).\n"
    "?ЛИНИЯ(40, 0, 0, 25, 3).\n"
    "?ЛИНИЯ(60, Y, 5, 20, 4).\n"         # a vertical run
    "?ЛИНИЯ(X, 30, 20, 95, 5).\n"        # a horizontal one
    "?ОКРУЖНОСТЬ(120, 40, 12, 6).\n"
    "?ЛИНИЯ(60, 5, 90, 5, 4).\n"         # a frame, and a fill that stops in it
    "?ЛИНИЯ(60, 20, 90, 20, 4).\n"
    "?ЛИНИЯ(60, 5, 60, 20, 4).\n"
    "?ЛИНИЯ(90, 5, 90, 20, 4).\n"
    "?ЗАКРАСКА(75, 12, 7).\n"
    "?ТОЧКА(1, 1, 9).\n"
)


def test_the_two_rasterisers_agree(executable: str) -> None:
    """The engine's bitmap and the replayed events must be the same picture."""
    requests = [protocol.load_text(PICTURE), protocol.graphics_snapshot()]
    process = subprocess.Popen(
        [executable, "--protocol", "json"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = b"".join(requests) + protocol.quit_session()
    stdout, stderr = process.communicate(payload, timeout=60.0)
    events = list(protocol.Decoder().feed(stdout))
    if process.returncode != 0:
        raise AssertionError(f"exit code {process.returncode}: {stderr.decode('utf-8', 'replace')}")

    drawn_events = [event for event in events if event.get("event") == "graphics"]
    snapshot = [event for event in events if event.get("event") == "bitmap"]
    assert drawn_events, f"no graphics events: {[e.get('event') for e in events]}"
    assert snapshot, f"no snapshot: {[e.get('event') for e in events]}"

    width, height, data = graphics.decode_bitmap(snapshot[0])
    engine = graphics.Canvas()
    engine.apply_bitmap(width, height, data)

    replayed = graphics.Canvas()
    for event in drawn_events:
        replayed.draw(event)
    assert (replayed.width, replayed.height) == (engine.width, engine.height)

    differences = [
        (index % width, index // width)
        for index, (left, right) in enumerate(zip(replayed.values, engine.values))
        if left != right
    ]
    assert not differences, (
        f"{len(differences)} cells differ between the engine and the canvas, "
        f"first: {differences[:5]}"
    )
    print(f"ok: the engine and the canvas draw the same picture ({len(drawn_events)} primitives)")


def main(argv: list[str]) -> int:
    test_a_point_lands_in_the_cell_it_names()
    test_a_line_includes_both_of_its_ends()
    test_a_rectangle_outlines_its_box()
    test_an_ellipse_is_a_centre_and_two_radii()
    test_a_fill_stops_at_a_wall()
    test_a_run_and_the_whole_screen()
    test_a_colour_value_becomes_a_colour_one_way()
    test_a_snapshot_replaces_the_picture()
    test_an_unknown_primitive_is_refused()
    executable = argv[1] if len(argv) > 1 else find_executable()
    if executable is None:
        print("skipped: no prologu build found, pass its path to pin the two rasterisers")
    else:
        test_the_two_rasterisers_agree(executable)
    print("all graphics checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
