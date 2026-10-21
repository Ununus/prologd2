#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "builtins_internal.hpp"

namespace prologd {

using detail::ArgKind;
using detail::asInteger;
using detail::asText;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyInteger;

namespace {

std::optional<std::int64_t> integerValue(Engine& engine, const Term& term) {
  const auto value = asInteger(engine, term);
  if (!value) {
    return std::nullopt;
  }
  return value->toInt64();
}

bool isCallable(Engine& engine, const Term& term) {
  const Term resolved = engine.bindings().deref(term);
  return resolved.kind == TermKind::Atom || resolved.kind == TermKind::Compound;
}

}  // namespace

BuiltinResult builtinClauseCount(Engine& engine, std::span<const Term> args) {
  const auto name = asText(engine, args[0]);
  if (!name) {
    badArgument(engine, args[0], "СКОЛЬКО", 1, ArgKind::Text);
  }
  const auto count = static_cast<std::int64_t>(engine.database().clauseCountByName(*name));
  if (isUnbound(engine, args[1])) {
    return unifyInteger(engine, args[1], BigInt(count)) ? BuiltinResult::Continue
                                                        : BuiltinResult::Fail;
  }
  const auto expected = integerValue(engine, args[1]);
  if (!expected) {
    badArgument(engine, args[1], "СКОЛЬКО", 2, ArgKind::Integer);
  }
  return *expected == count ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinClauseInfo(Engine& engine, std::span<const Term> args) {
  const auto name = asText(engine, args[0]);
  const auto index = integerValue(engine, args[1]);
  if (!name) {
    badArgument(engine, args[0], "ПРЕДЛ", 1, ArgKind::Text);
  }
  if (!index) {
    badArgument(engine, args[1], "ПРЕДЛ", 2, ArgKind::Integer);
  }
  const std::vector<Clause> merged = engine.database().clausesByName(*name);
  if (*index < 1 || static_cast<std::size_t>(*index) > merged.size()) {
    return BuiltinResult::Fail;
  }
  const Clause& clause = merged[static_cast<std::size_t>(*index - 1)];
  Term head;
  std::vector<Term> body;
  engine.instantiateClause(clause, head, body);
  if (!engine.unify(args[2], head)) {
    return BuiltinResult::Fail;
  }
  if (!engine.unify(args[3], makeListFromVector(body))) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

BuiltinResult builtinTermConvert(Engine& engine, std::span<const Term> args) {
  const Term first = engine.bindings().deref(args[0]);
  const Term second = engine.bindings().deref(args[1]);

  auto buildFromList = [&engine](const Term& list, Term& built) -> bool {
    std::vector<Term> elements;
    Term tail;
    listToVectorWithTail(list, elements, tail);
    if (!isNil(tail) || elements.empty()) {
      engine.raise(ErrorCode::WrongList);
    }
    const Term functor = engine.bindings().deref(elements[0]);
    if (functor.kind != TermKind::Atom) {
      return false;
    }
    if (elements.size() == 1) {
      built = makeAtom(functor.text);
    } else {
      std::vector<Term> arguments(elements.begin() + 1, elements.end());
      built = makeCompound(functor.text, std::move(arguments));
    }
    return true;
  };

  // List -> term.
  if (isList(second) && !isList(first)) {
    Term built;
    if (!buildFromList(second, built)) {
      return BuiltinResult::Fail;
    }
    return engine.unify(args[0], built) ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (isList(first)) {
    Term built;
    if (!buildFromList(first, built)) {
      return BuiltinResult::Fail;
    }
    return engine.unify(args[1], built) ? BuiltinResult::Continue : BuiltinResult::Fail;
  }

  // Term -> list.
  if (!isUnbound(engine, args[1])) {
    return BuiltinResult::Fail;
  }
  std::vector<Term> elements;
  if (first.kind == TermKind::Atom) {
    elements.push_back(first);
  } else if (first.kind == TermKind::Compound && first.compound != nullptr) {
    elements.push_back(makeAtom(first.compound->name));
    elements.insert(elements.end(), first.compound->args.begin(), first.compound->args.end());
  } else {
    return BuiltinResult::Fail;
  }
  const Term list = makeListFromVector(elements);
  return engine.unify(args[1], list) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinAssert(Engine& engine, std::span<const Term> args) {
  const Term head = engine.bindings().deref(args[0]);
  if (head.kind != TermKind::Atom && head.kind != TermKind::Compound) {
    badArgument(engine, args[0], "ДОБ", 1, ArgKind::Text,
                "имя предиката или голова предложения");
  }
  const Term goals = engine.bindings().deref(args[1]);
  if (!isList(goals)) {
    badArgument(engine, args[1], "ДОБ", 2, ArgKind::List);
  }
  const auto position = integerValue(engine, args[2]);
  if (!position) {
    badArgument(engine, args[2], "ДОБ", 3, ArgKind::Integer);
  }
  std::vector<Term> body;
  Term tail;
  listToVectorWithTail(goals, body, tail);
  if (!isNil(tail)) {
    engine.raise(ErrorCode::WrongList);
  }
  for (const Term& goal : body) {
    if (!isCallable(engine, goal)) {
      badArguments(engine, "ДОБ");
    }
  }
  Clause clause;
  engine.copyClauseResolved(head, body, clause.head, clause.body);
  engine.database().insertByNamePosition(std::move(clause), *position);
  return BuiltinResult::Continue;
}

BuiltinResult builtinRetract(Engine& engine, std::span<const Term> args) {
  const auto name = asText(engine, args[0]);
  const auto index = integerValue(engine, args[1]);
  if (!name) {
    badArgument(engine, args[0], "УДАЛЕНИЕ", 1, ArgKind::Text);
  }
  if (!index) {
    badArgument(engine, args[1], "УДАЛЕНИЕ", 2, ArgKind::Integer);
  }
  return engine.database().retractByNamePosition(*name, *index) ? BuiltinResult::Continue
                                                               : BuiltinResult::Fail;
}

}  // namespace prologd
