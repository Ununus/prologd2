# task_21 — PySide6 front-end and the JSON session protocol

**Status:** in progress (protocol, prlib seams and the GUI skeleton are in;
window not yet run on a machine with PySide6)
**Depends on:** task_15 (graphics), task_16 (CLI)
**Milestone:** post-M10
**Supersedes:** task_20 (the Qt 6 C++ front-end plan)

## Goal

Give PrologD a graphical front-end without putting any GUI code into the
interpreter: a Python/PySide6 application in `src/gui` that drives the built
`prologd` executable over a documented, versioned JSON session.

## Why not in-process

A user program can loop forever, ask for input in the middle of a query, or
crash the interpreter.  Running the interpreter as a child process keeps all of
that away from the UI thread; a restart is a process restart.  See ADR-014 for
the alternatives that were rejected (Qt C++ front-end, pybind11 bindings).

## Deliverables

Protocol (CLI side, `src/cli/protocol.cpp`):

- [x] `--protocol json`; requests on stdin, events on stdout, one JSON object
      per line; protocol version 1.
- [x] Requests: `load` (path or text), `query`, `input`, `interrupt`, `quit`.
- [x] Events: `ready`, `output`, `result`, `input_request`, `error`, `bye`.
- [x] Diagnostics carry their kind (`parse`, `runtime`, `protocol`) and keep the
      `file:line:column` prefix the parser produces.
- [x] `-i`/`-o`/`-e` refused in protocol mode (the protocol owns both streams).
- [x] Exit codes: 0 clean, 1 usage, 2 load/parse, 3 runtime.

Core seams (the only changes `prlib` was allowed to take):

- [x] `IoContext::setInputRequestHandler` — interactive reads ask the front-end
      instead of a stream; `InputRequestKind` tells a token from a line from a
      code point.  `ЧТЕНИЕ_ИЗ` redirection keeps priority (the `$` lines that also
      had it were removed in part 81).
- [x] `EngineOptions::externalStop` — polled by the solver next to its own flag,
      so a signal handler only has to set a flag (ADR-013/014).
- [x] CLI: SIGINT/SIGTERM handler feeding `externalStop`.

Front-end (`src/gui`):

- [x] `prologd_gui/protocol.py` — Qt-free request/event encoding and decoding.
- [x] `prologd_gui/session.py` — `QProcess` bridge emitting Qt signals.
- [x] `prologd_gui/window.py`, `main.py` — editor, query line, output pane,
      Run/Open/Stop, input dialogs.
- [x] `tests/protocol_smoke.py` — headless check of the wire format against the
      real executable (no PySide6 needed).
- [x] `README.md` — the protocol contract, the invocation notes and the roadmap.

## Tests

- [x] CTest `cli_json_protocol` drives a full session (`load`, `query`,
      `input_request`/`input`, `quit`), a parse failure (exit code 2) and the
      `-o` conflict (exit code 1) through `src/tests/protocol_session.cmake`.
- [x] Catch2 `test_io_context.cpp`: handler routing, kind reporting, redirected
      precedence, `externalStop` interrupting a runaway query.
- [x] `python src/gui/tests/protocol_smoke.py`: the Python client against the
      built interpreter.

## Open items

- [ ] Run the window on a machine with PySide6 and check the input dialogs, the
      Stop button and the exit-code path by hand.
- [ ] Syntax highlighting from the lexer keyword set.
- [ ] A graphics pane: a `GraphicsBackend` implementation that emits protocol
      events, so `ТОЧКА`/`ЛИНИЯ`/… become visible (task_15 backends are null and
      recording today) — **moved out**: it is a task of its own now,
      `task_45_gui_graphics_window.md` (2026-10-01), because it needs protocol
      events, a bitmap backend in the engine and a window of its own.
- [ ] Stepping over the `ТРАССА` stream.
- [ ] Settings persistence (interpreter path, includes, window layout).

## Acceptance

`python src/gui/main.py` opens a window, runs the editor buffer with **Запустить**,
shows `ВЫВОД` output, answers `ВВОДСТР` with a dialog and survives **Остановить**
on a runaway query.  The protocol is documented in `src/gui/README.md` and
covered by tests that do not need a display.
