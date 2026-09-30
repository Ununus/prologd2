#pragma once

#include "prlib/diagnostics.hpp"
#include "prlib/parser.hpp"
#include "prlib/program.hpp"

namespace prologd {

/// Static checks over one parsed unit, run right after it was parsed.
///
/// They catch only calls that *cannot* work: a reserved name (`УМНОЖЕНИЕ`,
/// `НЕ`, `ДОБ`, ...) used with an arity it has nowhere — not in the dispatch
/// table, not in the program being loaded, not in the clause database.  Such a
/// call used to fail silently, and a beginner had no way to tell it apart from
/// "no solutions".
///
/// Checks that need the *whole* load (an undefined predicate, an arity that a
/// user predicate does not have) run later, when imports and the rest of the
/// unit are in the database — see `checkCallSites`.
void checkReservedCalls(const ParsedProgram& program, const Database& database,
                        DiagnosticSink& sink);

/// Check every goal of a loaded unit against the clause database, the built-in
/// table and the reserved names.
///
/// This is the post-load half of the call-site checks: an unknown predicate or
/// an arity a user predicate does not have is reported as a *warning* with the
/// position of the goal — never as an error, because an undefined goal is
/// documented to fail (negation as failure leans on it).
///
/// `report` receives the diagnostics; the caller decides where they go.
void checkCallSites(const ParsedProgram& program, const Database& database,
                    const std::function<void(const PrologError&)>& report);

}  // namespace prologd
