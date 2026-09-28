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
/// | `{"cmd":"interrupt"}` | stop the current query |
/// | `{"cmd":"quit"}` | end the session |
///
/// Events are written to `out`, one JSON object per line: `ready`, `output`,
/// `result`, `input_request`, `error`, `bye`.  The contract is written down in
/// `src/gui/README.md`.
///
/// The session replaces the engine streams and the loader's query runner, so it
/// is an alternative to the console front-end, not an addition to it.
///
/// Returns the process exit code: 0 clean, 2 a load/parse failure, 3 a runtime
/// failure.
int runJsonSession(Engine& engine, ModuleLoader& loader, std::istream& in, std::ostream& out);

}  // namespace prologd::cli
