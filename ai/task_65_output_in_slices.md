# task_65 — the window stays alive while a program floods its output

**Status:** done (2026-10-06)
**Depends on:** task_27 (`PrologSession`, the panes), task_45/49 (the graphics window
and the output that arrives as it is written), task_64 (the `interrupt` that cannot
reach a solver)
**Found by:** using the window — the user could not stop a program that printed or
drew in a tight loop

## The defect, measured

`PrologSession._on_stdout` read everything the child had written and dispatched
every event it decoded, in one call, on the window's own thread.  A program that
writes faster than the window can draw therefore kept the event loop busy for as
long as the flood lasted: a click on «Остановить» and the «Предел времени» timer
(whoever set it) were queued behind the whole stream and could not end the run.

The `drawing.pld` accident of the previous round is the same defect seen from the
other side: the teeth loop drew more than 300 000 primitives, and the window
became unusable.

## The cure (done)

* **One slice per turn.**  Events are queued (`_events`) and handed over in
  `EVENTS_PER_TURN` (250) slices by a single-shot timer, so the event loop runs
  between two slices — clicks, timers, painting and the stop path included.  The
  work is the same as before; only its granularity changed.  Order is preserved,
  and no second thread is involved (a thread would buy nothing: the GIL does not
  let Python work in parallel, and one signal per event across a thread boundary
  would fill Qt's queue instead of the session's).
* **`ended` is the last event a front-end hears.**  A process that exits while its
  events are still queued defers `ended` until the queue is empty, so a pane never
  reports the end of a run whose last line is still waiting.  `start()`/`stop()`
  drop the queue, so a new session cannot answer with the previous one's output.
* **The flood guard (the user's option 3).**  Nothing is dropped — a picture with
  a primitive quietly missing looks correct and is not — so the guard only *says*
  it: more than `FLOOD_EVENTS` (20 000) events in one second puts one line in
  «Системе» (`flooded` → `_on_flooded`), which explains why the window lags behind
  and why «Остановить» may take a moment to be served.

## What was not done

* Coalescing the *repaint* of the graphics view: Qt already merges `update()`
  calls into one paint per turn, so a primitive costs only a Python call.
* Dropping intermediate graphics events: the plane must stay exactly what the
  program drew.  A window that reconnects asks for a snapshot (`graphics_snapshot`)
  instead.
* Moving the decoder into a worker thread: measured reasoning above — the slices
  are what the loop needs, and a thread would add a queue without removing work.

## Verification

* `src/gui/tests/test_window.py` — `test_a_flood_of_output_leaves_the_window_alive`:
  a program that prints in a loop; a 20 ms timer must keep ticking while the flood
  is dispatched, and «Остановить» must end the run.
* `test_session.py`, `test_output.py`, `protocol_smoke.py` — the wire and the
  session's state machine (queue, `ended` order, restart).
* `ctest` (the interpreter is untouched) and the six documents.
