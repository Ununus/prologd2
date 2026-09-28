#include "prlib/term.hpp"

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

Term makeCompound(std::string_view name, std::vector<Term> args) {
  Term term;
  term.kind = TermKind::Compound;
  auto payload = std::make_shared<CompoundTerm>();
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

std::string functorKey(std::string_view name, std::size_t arity) {
  return std::string(name) + "/" + std::to_string(arity);
}

}  // namespace prologd
