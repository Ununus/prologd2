# task_45 — GUI: the graphics window

**Status:** done (2026-10-01) — protocol 10, the bitmap backend, the canvas, the
window and the tests are in; the two defects the by-hand look found are recorded
under «What was built»
**Depends on:** task_15 (the `GraphicsBackend` interface and the four built-ins),
task_27 (the panels: a dock, the run states), task_29 (settings rows and the
dialog), task_21 (the protocol and the window skeleton)
**Milestone:** M15

## What was built (2026-10-01)

| Piece | Where |
|---|---|
| `GraphicsOp`, `GraphicsEvent`, `BitmapGraphicsBackend` | `prlib/graphics.hpp`, `prlib/graphics.cpp` |
| protocol 10: `graphics` events, `{"cmd":"graphics","snapshot":true}` → `bitmap` | `src/cli/protocol.cpp` |
| `Canvas` (Qt-free), the palette, `decode_bitmap` | `src/gui/prologd_gui/graphics.py` |
| `CanvasView`, `GraphicsWindow` | `src/gui/prologd_gui/graphicswindow.py` |
| the live action, the wiring, `view/graphics_visible` + `view/graphics_geometry` | `actions.py`, `window.py`, `settings.py` |
| 12 Catch2 cases, the cmake session cases, `test_graphics.py` | `test_graphics_backend.cpp`, `protocol_session.cmake`, `src/gui/tests/` |

Decisions taken while building it (ADR-022):

* A cell holds the **colour value the program wrote**, not an ARGB word, so
  `ТОЧКА(X, Y, Цвет)` gives back exactly what was put there; the palette that turns
  a value into a visible colour lives on the front-end side (`color_for`), and
  `0`…`15` are the EGA palette (`examples/drawing.pld` draws with those numbers)
  while anything above is read as `0xRRGGBB`.
* Every primitive is a **cell, a segment or a box**.  An `ellipse` is the odd one:
  a centre and two radii, *not* a bounding box — `ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes
  its four numbers straight through to the backend, and the interface's parameter
  names (`x1, y1, x2, y2` since task_15) said otherwise.
* The **snapshot** exists for a window that was not open while the program drew;
  it carries four-byte little-endian values, so a replayed picture and the
  engine's own buffer are comparable cell by cell.

Two defects the by-hand look at `examples/drawing.pld` found, and why they are
worth recording:

1. **The ellipse was read as a bounding box.**  Every circle came out as a line,
   and the first `ЗАКРАСКА` then leaked across the whole screen — the picture was
   a blue field with a couple of white spots.  Fixed in both rasterisers, and the
   interface and the wire now say `x, y, rx, ry`.
2. **An untouched canvas was transparent black.**  `bytearray(n)` is zeroed, which
   as `RGBA8888` is alpha 0: the window showed the desktop through the empty parts
   of the picture.  It is the reason `Canvas.__init__` fills the buffer with the
   blank colour.

Neither was visible to a test that only compared the engine and the canvas: both
sides agreed, and both were wrong.  What caught them was looking at the drawing —
which is what the acceptance criterion said to do.

## Goal

Make the graphics predicates **visible**.  `ТОЧКА`, `ЛИНИЯ`, `ОКРУЖНОСТЬ` and
`ЗАКРАСКА` work and are tested (task_15, task_34), but they draw into
`NullGraphicsBackend`: a lesson can paint a picture and the student sees nothing.
This task is the window those calls land in, and the last disabled entry of the
menu — «Графическое окно» — becomes live.

## What already exists (checked 2026-10-01)

* `src/prlib/include/prlib/graphics.hpp`: `GraphicsBackend` — `setPixel`,
  `getPixel`, `line`, `rectangle`, `ellipse`, `floodFill`, `clearView`,
  `vertical`, `horizontal`, `width()`, `height()`; the virtual screen is
  `kMaxGrX = 1024`, `kMaxGrY = 768`; `NullGraphicsBackend` and
  `RecordingGraphicsBackend` (for tests).
* `Engine::setGraphicsBackend(std::shared_ptr<GraphicsBackend>)`; the console
  build installs the null one.  (task_15 also planned `--graphics-log` for the
  recording backend; it was never added — the recording backend is used by the
  Catch2 tests in-process, and the console keeps the null one.)
* The four built-ins reproduce the original argument dispatch, including the
  quirk that `ТОЧКА` with an unbound `Y` draws a vertical run of `color = 0`.
* The GUI speaks JSON over a pipe to the interpreter process: the drawing cannot
  be a direct C++ call, it has to travel as **events**.

## The gap

The backend lives *inside* the interpreter process, and the front-end is on the
other side of a pipe.  Two consequences decide the design:

1. a drawing call is a one-way event (fire and forget);
2. `getPixel` is a **read** the engine performs from inside a built-in — a
   synchronous round trip to the GUI would mean asking a question in the middle
   of a built-in, which the protocol does not do anywhere, and `ЗАКРАСКА`
   (`floodFill`) depends on reads of pixels it has itself written.

## Deliverables

- [ ] `prlib`: **`BitmapGraphicsBackend`** — the source of truth *inside* the
      engine.  A `width × height` ARGB buffer that answers `getPixel` locally,
      applies `floodFill` and `clearView` itself, and reports every primitive to a
      sink (`std::function<void(const GraphicsEvent&)>`).  The JSON session
      installs it; the console build keeps the null one (nothing changes for a
      program run from the command line).
- [ ] `graphics.hpp`: `GraphicsEvent` — the primitive's name (the *backend
      method* names, so the tests, the wire and the GUI share one vocabulary) plus
      its arguments and the colour.  One struct, one function that turns it into
      the protocol's JSON.
- [x] Protocol **10** (`9` is the limits of task_46): `{"event":"graphics", …}` per
      primitive, and a snapshot for a window that was opened (or reopened) while
      the program was drawing: `{"cmd":"graphics","snapshot":true}` →
      `{"event":"bitmap","width":…,"height":…,"data":"…"}`.
      `protocol_session.cmake` covers both; `protocol_smoke.py` gets the client
      half.  The payload is base64 of four-byte **little-endian colour values**
      and not ARGB: the values are the program's own numbers, so a replayed
      picture and a snapshot are comparable cell by cell (ADR-022).  A `graphics`
      request without `snapshot` is an `error` event, and the session reads the
      next line.
- [x] `src/gui/prologd_gui/graphics.py` (Qt-free): `Canvas` — the pixels, `draw(event)`,
      `apply_bitmap(width, height, data)`, `to_rgba()` (the task asked for
      `to_image()`, which would have pulled Qt into a Qt-free module) and
      `snapshot_bytes()`.  Every drawing rule worth checking (clipping at the
      edges, `floodFill`, a colour's byte order) lives here, so `test_graphics.py`
      needs no display.
- [x] The window: a **separate window** (`QWidget` with its own title, owned by the
      main window and marked `Qt.Window`, or a parented widget is a child widget
      and the picture ends up inside the editor), because that is what the action
      is called, it can go to a second screen, and it does not compete for space
      with the editor.  Shown and hidden by the action; its geometry and
      visibility are machine keys (`view/graphics_visible`,
      `view/graphics_geometry`); a «Сохранить как PNG…» command, «Очистить»,
      «Вписать в окно»/«1 : 1» and a cell readout in its own small toolbar.
- [x] The drawing arrives as it is produced: the canvas follows the run (lesson 12's
      animation is the case to watch by hand), and a window opened mid-run asks for
      the snapshot instead of starting blank.
- [x] `actions.py`: the entry is live (checkable, its state is the window's
      visibility), the icon `view-graphics` is drawn already, and the audit's
      counts move with it — no disabled entry is left in the menu.

## Design notes

* **The engine keeps the pixels.**  Sending the whole bitmap after every primitive
  would be megabytes per `ТОЧКА`; sending the primitive is a few bytes and the GUI
  redraws it in O(pixels of that primitive).  The snapshot exists for the moment a
  window is not there to receive them, not as the normal path.
* The **coordinate system is the engine's**: the original screen is 1024×768 with
  the origin at the top left.  The canvas paints it as it comes and offers a
  zoom-to-fit; nothing in the GUI may flip an axis, or a ported lesson would draw
  mirrored while the engine's own `getPixel` says otherwise.
* A **`graphics` request with no session** (or in the console build) is an
  ordinary protocol `error`, not a crash — the console build has no JSON session
  at all, and the session refuses a request it cannot answer.
* The recording backend is what the console tests use in-process, and the bitmap
  one is what the session installs; the console build keeps the null backend and
  nothing there changed (`--graphics-log` was planned in task_15 and never added).

## Tests

- [x] Catch2 `test_graphics_backend.cpp` (12 cases): each primitive changes exactly
      the pixels it should (a `line`'s ends, a `rectangle`'s corners, an
      `ellipse`'s extremes), `getPixel` after `setPixel` — through the interpreter
      as well, `clearView` fills, `floodFill` stops at a boundary and reads the
      cells the same query wrote, every primitive is reported to the sink and a
      read is not, and the clipping at the edges (a coordinate of `10**18`) is
      pinned.
- [x] `src/tests/protocol_session.cmake`: a program that draws reaches the wire as
      `graphics` events in order (and in the order the program drew them), the
      snapshot comes back as 1024×768 with the pixel that was drawn in its first
      bytes, and a `graphics` request without `snapshot` is a `protocol` error
      after which the session goes on.
- [x] `src/gui/tests/test_graphics.py` (Qt-free, and the cross-check needs a
      build): `Canvas` under each event, including an event outside the screen, a
      `floodFill` that has to stop at a line, a snapshot that replaces the
      picture, a broken snapshot, an unknown primitive — and the pin: a program
      draws, the engine's finished bitmap comes back, the reported events are
      replayed into a canvas, and the two pictures are compared cell by cell.
- [x] `test_window.py`: the action is enabled and does not say «не реализовано»;
      it opens the window, a run with `ТОЧКА`/`ЛИНИЯ`/`ЗАКРАСКА` puts pixels on
      the canvas, hiding and closing it keeps the picture, reopening it takes the
      snapshot path, `save_png` writes a file, and a new run clears what the old
      interpreter had drawn.
- [x] By hand: `examples/drawing.pld` was drawn through the whole path and looked
      at as a PNG (a face on a black screen, in the colours the program names),
      and the engine's own bitmap was compared with the replay of the same events:
      61 primitives, **0 cells different**.  Two defects came out of that look (see
      «What was built») — and the offscreen rendering was enough for both, since
      what was wrong was the picture, not the pixels on a real screen.
- [ ] Still to look at with eyes on a real display: lesson 12's animation (the
      events arrive as they are drawn, so it should move rather than jump).

## Acceptance

A program that calls the graphics predicates draws into a window the student can
see, move, zoom and save; the console build is unchanged; the menu has no
disabled entry left.
