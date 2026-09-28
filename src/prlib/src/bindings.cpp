#include "prlib/bindings.hpp"

namespace prologd {

VarId Bindings::freshVar(std::string_view name) {
  const auto id = static_cast<VarId>(bindings_.size());
  bindings_.emplace_back();
  names_.emplace_back(name);
  return id;
}

Term Bindings::deref(const Term& term) const {
  Term current = term;
  while (current.kind == TermKind::Var) {
    if (current.var >= bindings_.size() || !bindings_[current.var].bound) {
      return current;
    }
    current = bindings_[current.var].value;
  }
  return current;
}

bool Bindings::isBound(VarId id) const {
  return id < bindings_.size() && bindings_[id].bound;
}

bool Bindings::bind(VarId id, const Term& value) {
  if (id >= bindings_.size()) {
    return false;
  }
  if (bindings_[id].bound) {
    return false;
  }
  bindings_[id].bound = true;
  bindings_[id].value = value;
  trail_.push_back(id);
  return true;
}

bool Bindings::bindTerm(const Term& term, const Term& value) {
  if (term.kind != TermKind::Var) {
    return false;
  }
  return bind(term.var, value);
}

void Bindings::unwind(std::size_t mark) {
  while (trail_.size() > mark) {
    const VarId id = trail_.back();
    trail_.pop_back();
    if (id < bindings_.size()) {
      bindings_[id].bound = false;
      bindings_[id].value = Term{};
    }
  }
}

std::string_view Bindings::varName(VarId id) const {
  if (id >= names_.size()) {
    return {};
  }
  return names_[id];
}

void Bindings::clear() {
  bindings_.clear();
  names_.clear();
  trail_.clear();
}

}  // namespace prologd
