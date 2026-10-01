# task_45 — GUI: the graphics window

**Status:** not started
**Depends on:** task_15 (the `GraphicsBackend` interface and the four built-ins),
task_27 (the panels: a dock, the run states), task_29 (settings rows and the
dialog), task_21 (the protocol and the window skeleton)
**Milestone:** M15

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
  build installs the null one, `--graphics-log` the recording one.
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
- [ ] Protocol **10** (`9` is the limits of task_46): `{"event":"graphics", …}` per primitive, and a snapshot for
      a window that was opened (or reopened) while the program was drawing:
      `{"cmd":"graphics","snapshot":true}` → `{"event":"bitmap","width":…,
      "height":…,"data":"<base64 ARGB>"}`.  `protocol_session.cmake` covers both;
      `protocol_smoke.py` gets the client half.
- [ ] `src/gui/prologd_gui/graphics.py` (Qt-free): `Canvas` — the pixels, `draw(event)`,
      `apply_bitmap(width, height, data)`, `to_image()`.  Every drawing rule worth
      checking (clipping at the edges, `floodFill`, a colour's byte order) lives
      here, so `test_graphics.py` needs no display.
- [ ] The window: a **separate window** (`QWidget` with its own title, owned by the
      main window), because that is what the action is called, it can go to a
      second screen, and it does not compete for space with the editor.  Shown and
      hidden by the action; its geometry and visibility are machine keys
      (`view/graphics_visible`, `view/graphics_geometry`); a «Сохранить как PNG…»
      command and «Очистить» in its own small toolbar.
- [ ] The drawing arrives as it is produced: the canvas follows the run (lesson 12's
      animation is the case to watch by hand), and a window opened mid-run asks for
      the snapshot instead of starting blank.
- [ ] `actions.py`: the entry is live (`implemented` again), the icon
      `view-graphics` is drawn already, and the audit's counts move with it.

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
  ordinary protocol `error`, not a crash.
* `--graphics-log` keeps working: the recording backend is what the console tests
  use, and the bitmap one is what the session installs.

## Tests

- [ ] Catch2 `test_graphics_backend.cpp`: each primitive changes exactly the
      pixels it should (a `line`'s ends, a `rectangle`'s corners, an `ellipse`'s
      extremes), `getPixel` after `setPixel`, `clearView` fills, `floodFill` stops
      at a boundary and follows the original's rules, and the clipping rule at
      `kMaxGrX`/`kMaxGrY` is pinned.
- [ ] `src/tests/protocol_session.cmake`: a program that draws reaches the wire as
      `graphics` events in order, the snapshot comes back with the right size and
      the pixels that were drawn, and both are refused in the console build.
- [ ] `src/gui/tests/test_graphics.py` (Qt-free): `Canvas` under each event,
      including a snapshot taken mid-animation, an event outside the screen, and a
      `floodFill` that has to stop at a line.
- [ ] `test_window.py`: the action is enabled and does not say «не реализовано»;
      it opens the window, a run with `ТОЧКА`/`ЛИНИЯ` puts pixels on the canvas,
      and closing and reopening the window keeps the picture (the snapshot path).
- [ ] By hand: `examples/drawing.pld` and lesson 12's first drawing, on the real
      display (`offscreen` paints, but a picture wants eyes).

## Acceptance

A program that calls the graphics predicates draws into a window the student can
see, move, zoom and save; the console build and `--graphics-log` are unchanged;
the menu has no disabled entry left.
