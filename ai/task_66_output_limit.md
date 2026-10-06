# task_66 — «Предел вывода»: a run is stopped once it has printed or drawn too much

**Status:** done (2026-10-06)
**Depends on:** task_46 (the limits and the run-note), task_64 (the `interrupt` that
cannot reach a solver), task_65 (the events in slices)
**Found by:** using the window — a program that floods the panes could not be
stopped, and the user asked for a max-output setting that stops the process by
itself

## The defect

The polite request (`interrupt`) is dispatched between two requests of the session,
so a query that is *solving* never reads it (task_64).  A program that prints or
draws in a tight loop is exactly that query, which left the user two bad choices:
the window froze (task_65), and the only way out was killing the whole thing.

## The design

* A new setting, **«Предел вывода»** (`execution/max_output_events`, `0` = off):
  how many output events one run may produce.  An event is a line of the program's
  text, a drawing primitive or a trace line — whatever the front-end receives.
* The window counts them (`_output_events`, reset at every run) and, past the cap,
  fires the same escalation as the «Предел времени» deadline: the request, then
  the process after `STOP_GRACE_MS`.  The pane says «предел вывода: N событий,
  остановлено», and the run-note names the row before the run starts.
* The cap is the *window's* guard, not the engine's (ADR-020): the solver has no
  idea how much it has printed, and a program that floods output is the one the
  polite request never reaches.

## What came with it

* The stream's **decode** is bounded too (`DECODE_BYTES_PER_TURN`, 64 KiB per turn)
  — the previous slices only bounded the dispatch, and feeding a whole read to
  `Decoder.feed` in one call still froze the loop.
* `_start_drain` now watches the raw buffer as well as the event queue: with the
  bytes not yet decoded the queue is empty, and the drain used to never start.
* While a stop is in flight the panes are fed no more (`_on_output`, `_on_drawn`,
  `_on_trace`, `_on_flooded` return early).  A visible window keeps repainting the
  panes as the text arrives, and that repainting is exactly what starves the
  «Остановить» deadline — the deadline needs the event loop, and the loop was busy
  painting.  Freezing the panes the moment the stop is asked is what lets the
  deadline fire; the side effect is that a *bounded* flood drains within the grace,
  the `loaded` event lands, and the stop is a polite one — the session and the base
  survive.* A run started after a stop printed nothing, and the fix is in `stop()`: it dropped
  the killed process's deferred `ended` — the event that clears the window's
  `_stopping` — so the flag stuck and `_on_output` swallowed every line of the next
  run.  `stop()` now delivers that `ended` before the new session starts.
## Verification

* `test_the_output_limit_stops_a_flood` — a 100 000-line program with a 1 000-event
  cap ends by itself; the note and the limits line are in the pane.
* `test_a_flood_of_output_leaves_the_window_alive` — the event loop keeps turning
  while a 60 000-line flood is dispatched, and «Остановить» ends it.
* `test_session.py`, `test_output.py`, `test_settings.py`, `protocol_smoke.py` and
  the full `test_window.py`; the six documents build.
