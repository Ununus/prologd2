#pragma once

#include <cstddef>
#include <functional>
#include <string>
#include <string_view>

#include "prlib/bindings.hpp"
#include "prlib/term.hpp"

namespace prologd {

class Engine;

/// Options controlling term printing.
struct PrintOptions {
  /// Called for `$expr` terms to obtain their numeric value.  May be empty, in
  /// which case expressions print as `#_?_#`.
  std::function<Term(const Term&)> evaluate;
  /// How deep a nested term may be before the rest is written as `...`.
  ///
  /// The limit is also a safety net: writing a compound recurses in C++, so a
  /// limit far beyond the C++ stack (this used to be 100000) turns a deeply
  /// nested term into a crash instead of a shortened line.  A cyclic term —
  /// which `РАВНО(X, f(X))` can build, since there is no occurs check — is
  /// stopped by the writer's own cycle detection, not by this number.
  std::size_t maxDepth = 2000;
};

/// Render a term in PrologD notation using `bindings` to resolve variables.
///
/// Unbound variables are printed as `_N` with `N` assigned in encounter order
/// within this call.  Strings print unquoted, atoms as-is, lists as `[a,b|T]`.
std::string formatTerm(const Term& term, const Bindings& bindings,
                       const PrintOptions& options = {});

/// Render a float the way the original PrologD did (trailing zeros trimmed).
std::string formatFloat(double value);

}  // namespace prologd
