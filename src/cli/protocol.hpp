#pragma once

#include <iosfwd>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"

namespace prologd::cli {

/// Line-delimited JSON session used by front-ends (the PySide6 GUI in
/// `src/gui`) instead of parsing human-readable console output.
///
/// Requests arrive on `in`, one JSON object per line:
///
/// | Request | Meaning |
/// |---------|---------|
/// | `{"cmd":"load","path":"prog.pld"}` | load a file (imports use `-I`) |
/// | `{"cmd":"load","text":"...","name":"buffer"}` | load program text |
/// | `{"cmd":"query","text":"?goal."}` | run one statement |
/// | `{"cmd":"input","text":"..."}` | answer the pending `input_request` |
/// | `{"cmd":"step","action":"into"}` | answer the pending `step` event |
/// | `{"cmd":"graphics","snapshot":true}` | the picture drawn so far |
/// | `{"cmd":"interrupt"}` | stop the current query |
/// | `{"cmd":"quit"}` | end the session |
///
/// `load` and `query` take `"trace":true` (the trace of `ТРАССА` goes out as
/// `trace` events) and `"step":true` (the run stops at the first step point and
/// waits for a `step` request; `action` is `into`, `over`, `continue` or `stop`).
///
/// Events are written to `out`, one JSON object per line: `ready`, `output`,
/// `result`, `input_request`, `step`, `trace`, `graphics`, `bitmap`, `error`,
/// `bye`.  `error` carries `file`/`line`/`column` when the diagnostic has a
/// position.  The contract is written down in `src/gui/README.md`.
///
/// The graphics predicates draw into the session itself (`graphics` events, one
/// per primitive, in the order the program called them) and the `graphics`
/// request answers with the whole `bitmap` for a window that was not open while
/// the picture was made (task_45).
///
/// The session replaces the engine streams and the loader's query runner, so it
/// is an alternative to the console front-end, not an addition to it.
///
/// Returns the process exit code: 0 clean, 2 a load/parse failure, 3 a runtime
/// failure.
int runJsonSession(Engine& engine, ModuleLoader& loader, std::istream& in, std::ostream& out);

}  // namespace prologd::cli
