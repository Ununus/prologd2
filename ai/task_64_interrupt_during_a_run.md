# task_64 — the JSON session must notice `interrupt` while a request is being solved

**Status:** open (2026-10-06)
**Depends on:** task_16 (the CLI and the JSON protocol), task_46 (limits), the
`interrupt` request of `src/cli/protocol.hpp`, ADR-020 (a limit is a run option,
and the core names no front-end)
**Found by:** using the window — the user asked whether the interpreter really
runs apart from the window, and why «Предел времени» does not end the run

## The defect, measured

A session reads its requests one after another (`src/cli/protocol.cpp`, the loop
around `std::getline(std::cin, …)` → `dispatch`), and a `load`/`query` request is
solved *inside* `dispatch`.  Nothing reads the stream while that happens, so
`{"cmd":"interrupt"}` written during a solving query is only dispatched after the
query is over — the one case it was meant for.

A probe (`prologd --protocol json`, `цикл:-цикл.` with `?цикл.`, then
`{"cmd":"interrupt"}`) leaves the process busy for ever: after the request the
only event seen is `ready`, and the process is alive.

Consequences today:

* a query that is *waiting* (for input, or at a step point — both wait *inside*
  the request and read the stream there) ends politely and keeps the base — the
  case `test_stopping_a_query_asks_first_and_keeps_the_base` covers;
* a query that is *solving* cannot be stopped politely at all, so
  **Остановить** — and now «Предел времени» — fall back on killing the process
  after `STOP_GRACE_MS`, and the knowledge base goes with it;
* the console build is unaffected: `SIGINT` sets the flag from the signal
  handler, which does not need the request loop (`main.cpp`'s
  `consumeInterrupt`), so Ctrl+C stops a runaway there.

## The cure (not done)

Watch the stream while a request is being solved, and stop on `interrupt` (or
`quit`):

1. **In the session's own stop hook.**  The engine already calls
   `EngineOptions::externalStop` periodically; the session's hook could, besides
   consuming the SIGINT flag, take one *available* line from `stdin` without
   blocking and remember it, so the main loop handles it next.  Platform-specific
   work: a peek needs `PeekNamedPipe`/`_kbhit` on Windows and `poll` on POSIX —
   the tree already has such `#ifdef`s for `isatty`.
2. **A reader thread.**  One thread owns `std::cin` and hands lines to the main
   loop through a queue; `interrupt`/`quit` set the flag directly.  More robust,
   but the request loop and the *program's own* input answers then share one
   channel and need a rule for who reads next.

Either way the run must end with the runtime error of the interrupted query and
leave the interpreter idle **with** its base, which is what the window's
`_finish_polite_stop` already expects.

## What must not change

* The order of the event stream and the shape of the requests (protocol 11).
* The engine's stop flag stays the engine's business; a front-end never links
  into it (ADR-020).
* `СТОП`/`interrupt` while a step point is paused must keep ending the pause.

## Verification

* A protocol-level test: a runaway `load`, then `interrupt`, then the
  `Interrupted` error within a second, and the session answering the next request
  with its base still loaded.
* `src/gui/tests/test_window.py` — «Остановить» on a *solving* run ends politely
  (the base survives) instead of waiting for `STOP_GRACE_MS`;
  `src/gui/tests/protocol_smoke.py` for the wire.
* The console's Ctrl+C path unchanged (`cli_diagnostics`/`engine_limits`).

Until this is done, the window keeps its deadline, and both the deadline and the
politeness are documented as they really are (`doc/gui.typ`, `src/gui/README.md`,
`window.py`).
