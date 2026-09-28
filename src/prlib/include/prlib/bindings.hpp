#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/term.hpp"

namespace prologd {

/// Variable store plus undo trail.
///
/// A binding maps a `VarId` to a term which may itself contain variables.
/// `deref` follows the chain; `bind` records the previous state on the trail so
/// `unwind` can restore it during backtracking.
class Bindings {
 public:
  /// Create a fresh variable with an optional display name.
  VarId freshVar(std::string_view name = {});

  /// Follow variable bindings until a non-variable or an unbound variable is
  /// reached.
  [[nodiscard]] Term deref(const Term& term) const;

  /// Bind an unbound variable.  The caller must have dereferenced first; if the
  /// variable is already bound the new binding is ignored and `false` is
  /// returned.
  bool bind(VarId id, const Term& value);

  /// Bind `term` (which must dereference to an unbound variable) to `value`.
  bool bindTerm(const Term& term, const Term& value);

  [[nodiscard]] bool isBound(VarId id) const;

  [[nodiscard]] std::size_t trailMark() const noexcept { return trail_.size(); }
  void unwind(std::size_t mark);

  /// Display name of a variable (empty when never named).
  [[nodiscard]] std::string_view varName(VarId id) const;

  void clear();

  [[nodiscard]] std::size_t variableCount() const noexcept { return bindings_.size(); }

 private:
  struct Binding {
    bool bound = false;
    Term value;
  };

  std::vector<Binding> bindings_;
  std::vector<std::string> names_;
  std::vector<VarId> trail_;
};

}  // namespace prologd
