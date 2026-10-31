#include "prlib/term.hpp"

#include <cmath>
#include <compare>
#include <utility>

namespace prologd {

Term makeVar(VarId id, std::string_view name) {
  Term term;
  term.kind = TermKind::Var;
  term.var = id;
  term.text = std::string(name);
  return term;
}

Term makeAtom(std::string_view name) {
  Term term;
  term.kind = TermKind::Atom;
  term.text = std::string(name);
  return term;
}

Term makeInt(BigInt value) {
  Term term;
  term.kind = TermKind::Int;
  term.integer = std::move(value);
  return term;
}

Term makeInt(std::int64_t value) { return makeInt(BigInt(value)); }

Term makeFloat(double value) {
  Term term;
  term.kind = TermKind::Float;
  term.real = value;
  return term;
}

Term makeString(std::string_view value) {
  Term term;
  term.kind = TermKind::String;
  term.text = std::string(value);
  return term;
}

namespace {

/// Frees a compound without recursing through its arguments.
///
/// A list is a chain of `shared_ptr`: the plain deleter destroys the tail inside
/// the destructor of its head, one C++ stack frame per element, and a list of
/// about 20 000 cells already killed the process (measured 2026-09-30, together
/// with the same failure in the environment chain).  The children are *taken
/// out* of a node before it dies, so no destruction path is ever holding a node
/// that still owns its own children — the worklist below keeps every child alive
/// while its parent goes.
///
/// The `const_cast` is the one place where the immutability of a term is broken,
/// and it is safe for the reason the class is immutable in the first place: the
/// deleter runs only when this `shared_ptr` is the last owner, and the node is
/// about to be destroyed, so nobody can observe the emptied argument list.
struct CompoundDeleter {
  void operator()(const CompoundTerm* node) const noexcept {
    std::vector<Term> pending = std::move(const_cast<CompoundTerm*>(node)->args);
    delete node;
    while (!pending.empty()) {
      Term child = std::move(pending.back());
      pending.pop_back();
      if (child.kind == TermKind::Compound && child.compound != nullptr &&
          child.compound.use_count() == 1) {
        auto* payload = const_cast<CompoundTerm*>(child.compound.get());
        for (Term& argument : payload->args) {
          pending.push_back(std::move(argument));
        }
        payload->args.clear();
      }
      // `child` is released here.  A node this loop emptied cannot cascade, and
      // a node somebody else still holds is not destroyed at all.
    }
  }
};

}  // namespace

Term makeCompound(std::string_view name, std::vector<Term> args) {
  Term term;
  term.kind = TermKind::Compound;
  auto payload = std::shared_ptr<CompoundTerm>(new CompoundTerm(), CompoundDeleter{});
  payload->name = std::string(name);
  payload->args = std::move(args);
  term.compound = std::move(payload);
  return term;
}

Term makeList(Term head, Term tail) {
  return makeCompound(kListFunctor, {std::move(head), std::move(tail)});
}

Term makeNil() { return makeAtom(kNilAtom); }

Term makeListFromVector(const std::vector<Term>& elements, Term tail) {
  Term result = std::move(tail);
  for (std::size_t i = elements.size(); i-- > 0;) {
    result = makeList(elements[i], std::move(result));
  }
  return result;
}

bool isNil(const Term& term) {
  return term.kind == TermKind::Atom && term.text == kNilAtom;
}

bool isListCell(const Term& term) {
  return term.kind == TermKind::Compound && term.compound != nullptr &&
         term.compound->name == kListFunctor && term.compound->args.size() == 2;
}

bool isList(const Term& term) { return isNil(term) || isListCell(term); }

bool isStruct(const Term& term) {
  return term.kind == TermKind::Compound && !isListCell(term);
}

std::size_t listLength(const Term& list, bool* proper) {
  std::size_t count = 0;
  const Term* current = &list;
  while (current != nullptr && isListCell(*current)) {
    ++count;
    current = &current->compound->args[1];
  }
  if (proper != nullptr) {
    *proper = current != nullptr && isNil(*current);
  }
  return count;
}

bool listToVectorWithTail(const Term& list, std::vector<Term>& elements, Term& tail) {
  const Term* current = &list;
  while (isListCell(*current)) {
    elements.push_back(current->compound->args[0]);
    current = &current->compound->args[1];
  }
  tail = *current;
  return isNil(*current);
}

bool listToVector(const Term& list, std::vector<Term>& out) {
  out.clear();
  Term tail;
  return listToVectorWithTail(list, out, tail);
}

bool structurallyEqual(const Term& lhs, const Term& rhs) {
  if (lhs.kind != rhs.kind) {
    return false;
  }
  switch (lhs.kind) {
    case TermKind::Var:
      return lhs.var == rhs.var;
    case TermKind::Atom:
    case TermKind::String:
      return lhs.text == rhs.text;
    case TermKind::Int:
      return lhs.integer == rhs.integer;
    case TermKind::Float:
      return lhs.real == rhs.real;
    case TermKind::Compound: {
      if (lhs.compound == rhs.compound) {
        return true;
      }
      if (lhs.compound == nullptr || rhs.compound == nullptr) {
        return false;
      }
      if (lhs.compound->name != rhs.compound->name ||
          lhs.compound->args.size() != rhs.compound->args.size()) {
        return false;
      }
      for (std::size_t i = 0; i < lhs.compound->args.size(); ++i) {
        if (!structurallyEqual(lhs.compound->args[i], rhs.compound->args[i])) {
          return false;
        }
      }
      return true;
    }
  }
  return false;
}

namespace {

/// Compares a whole number with a real, exactly.  `BigInt::fromDouble` gives the
/// whole part the real holds (it truncates toward zero), so the two integers
/// decide, and the fractional part decides only when they are equal.
int compareIntegerToDouble(const BigInt& integer, double real) {
  if (std::isnan(real)) {
    return 1;  // NaN stands before every number
  }
  if (std::isinf(real)) {
    return real > 0 ? -1 : 1;
  }
  const BigInt whole = BigInt::fromDouble(real);
  const std::strong_ordering order = integer <=> whole;
  if (order != 0) {
    return order < 0 ? -1 : 1;
  }
  const double truncated = std::trunc(real);
  if (real > truncated) {
    return -1;  // the real has a fraction, the integer does not
  }
  return real < truncated ? 1 : 0;
}

}  // namespace

int compareNumbers(const Term& left, const Term& right) {
  if (left.kind == TermKind::Int) {
    if (right.kind == TermKind::Int) {
      const std::strong_ordering order = left.integer <=> right.integer;
      return order < 0 ? -1 : (order > 0 ? 1 : 0);
    }
    return compareIntegerToDouble(left.integer, right.real);
  }
  if (right.kind == TermKind::Int) {
    return -compareIntegerToDouble(right.integer, left.real);
  }
  if (std::isnan(left.real) || std::isnan(right.real)) {
    return std::isnan(left.real) ? (std::isnan(right.real) ? 0 : -1) : 1;
  }
  return left.real < right.real ? -1 : (left.real > right.real ? 1 : 0);
}

std::string functorKey(std::string_view name, std::size_t arity) {
  return std::string(name) + "/" + std::to_string(arity);
}

}  // namespace prologd
