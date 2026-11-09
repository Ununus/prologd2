#include <cstdint>
#include <memory>
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

/// The clause the `ДОБ` family builds from a head and a list of goals — copied
/// into the database's own space, so a later binding of the caller's variables
/// cannot reach it.
Clause clauseFrom(Engine& engine, const Term& head_arg, const Term& goals_arg,
                  std::string_view predicate) {
  const Term head = engine.bindings().deref(head_arg);
  if (head.kind != TermKind::Atom && head.kind != TermKind::Compound) {
    badArgument(engine, head_arg, predicate, 1, ArgKind::Text,
                "имя предиката или голова предложения");
  }
  const Term goals = engine.bindings().deref(goals_arg);
  if (!isList(goals)) {
    badArgument(engine, goals_arg, predicate, 2, ArgKind::List);
  }
  const auto body = listElements(engine, goals);
  if (!body) {
    engine.raise(ErrorCode::WrongList);
  }
  for (const Term& goal : *body) {
    if (!isCallable(engine, goal)) {
      badArguments(engine, predicate);
    }
  }
  Clause clause;
  engine.copyClauseResolved(head, *body, clause.head, clause.body);
  return clause;
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

namespace {

/// The walk over the answers of `ПРЕДЛ` when the number is free (part 270): one
/// clause per answer, numbered from one in text order — the numbering `СКОЛЬКО`,
/// `УДАЛЕНИЕ/2` and the bound form of `ПРЕДЛ` already use.
///
/// The clauses are a *snapshot* taken when the goal was called, which is the
/// logical update view the rest of the base keeps: a clause added during the walk
/// is not seen by it.  A snapshot also keeps the numbers stable — a walk over live
/// positions would renumber itself the moment an earlier answer was retracted.
///
/// Every answer instantiates the clause afresh, so the head and the body of one
/// answer share variables with each other and with nothing else.
class ClauseWalk {
 public:
  ClauseWalk(Term number, Term head, Term body, std::vector<Clause> clauses)
      : number_(std::move(number)),
        head_(std::move(head)),
        body_(std::move(body)),
        clauses_(std::move(clauses)) {}

  std::optional<BuiltinAnswer> next(Engine& engine) {
    if (next_ >= clauses_.size()) {
      return std::nullopt;
    }
    const std::size_t index = next_++;
    Term head;
    std::vector<Term> body;
    engine.instantiateClause(clauses_[index], head, body);
    const std::int64_t number = static_cast<std::int64_t>(index) + 1;
    BuiltinAnswer answer;
    answer.unify.push_back({number_, makeInt(BigInt(number))});
    answer.unify.push_back({head_, std::move(head)});
    answer.unify.push_back({body_, makeListFromVector(body)});
    return answer;
  }

 private:
  Term number_;
  Term head_;
  Term body_;
  std::vector<Clause> clauses_;
  std::size_t next_ = 0;
};

}  // namespace

/// `ПРЕДЛ(Имя, Номер, Голова, Цели)` (`clause_at`).  A bound number asks for that
/// one clause, a free number walks all of them — `?ПРЕДЛ(ребро, Н, Г, Ц).` answers
/// with `Н=1`, then `Н=2`, and so on, which is how a program learns the number of a
/// clause it recognises by its head.
BuiltinResult builtinClauseInfo(Engine& engine, std::span<const Term> args) {
  const auto name = asText(engine, args[0]);
  if (!name) {
    badArgument(engine, args[0], "ПРЕДЛ", 1, ArgKind::Text);
  }
  if (isUnbound(engine, args[1])) {
    auto walk = std::make_shared<ClauseWalk>(args[1], args[2], args[3],
                                             engine.database().clausesByName(*name));
    BuiltinChoice choice;
    choice.produce = [walk](Engine& inner) { return walk->next(inner); };
    engine.setBuiltinChoice(std::move(choice));
    return BuiltinResult::Yield;
  }
  const auto index = integerValue(engine, args[1]);
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
    const auto elements = listElements(engine, list);
    if (!elements || elements->empty()) {
      engine.raise(ErrorCode::WrongList);
    }
    const Term functor = engine.bindings().deref(elements->at(0));
    if (functor.kind != TermKind::Atom) {
      return false;
    }
    if (elements->size() == 1) {
      built = makeAtom(functor.text);
    } else {
      std::vector<Term> arguments(elements->begin() + 1, elements->end());
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
  const auto position = integerValue(engine, args[2]);
  if (!position) {
    badArgument(engine, args[2], "ДОБ", 3, ArgKind::Integer);
  }
  Clause clause = clauseFrom(engine, args[0], args[1], "ДОБ");
  engine.database().insertByNamePosition(std::move(clause), *position);
  return BuiltinResult::Continue;
}

namespace {

/// Does this clause answer to `pattern`?  Asked on a copy of the head, and the
/// bindings are unwound at once: `УДАЛИТЬВСЕ` must not bind anything, and
/// `УДАЛЕНИЕ/1` asks before it answers.
bool headFits(Engine& engine, const Clause& clause, const Term& pattern) {
  Term head;
  std::vector<Term> body;
  engine.instantiateClause(clause, head, body);
  const std::size_t mark = engine.bindings().trailMark();
  const bool fits = engine.unify(pattern, head);
  engine.bindings().unwind(mark);
  return fits;
}

/// The walk over the answers of `УДАЛЕНИЕ/1` (`retract/1`), in ISO's order: one
/// clause per answer, the next one on backtracking.
///
/// The candidates are the clause *identifiers* that matched when the goal was
/// called — the snapshot the logical update view promises, so a clause asserted
/// during the walk is not seen by it.  Identity also survives the removal of an
/// earlier answer, which a position would not.
class RetractWalk {
 public:
  RetractWalk(Engine& engine, Functor functor, Term pattern)
      : functor_(std::move(functor)), pattern_(std::move(pattern)) {
    const auto clauses =
        engine.database().clausesFor(functor_.name, functor_.arity);
    if (!clauses) {
      return;
    }
    for (const Clause& clause : *clauses) {
      if (headFits(engine, clause, pattern_)) {
        candidates_.push_back(clause.id);
      }
    }
  }

  std::optional<BuiltinAnswer> next(Engine& engine) {
    while (next_ < candidates_.size()) {
      const std::uint64_t id = candidates_[next_++];
      const auto clauses = engine.database().clausesFor(functor_.name, functor_.arity);
      const Clause* found = nullptr;
      if (clauses) {
        for (const Clause& clause : *clauses) {
          if (clause.id == id) {
            found = &clause;
            break;
          }
        }
      }
      if (found == nullptr) {
        continue;  // an earlier answer of this walk already took it
      }
      Term head;
      std::vector<Term> body;
      engine.instantiateClause(*found, head, body);
      const std::size_t mark = engine.bindings().trailMark();
      if (!engine.unify(pattern_, head)) {
        engine.bindings().unwind(mark);
        continue;
      }
      engine.database().retractById(functor_.name, functor_.arity, id);
      return BuiltinAnswer{};
    }
    return std::nullopt;
  }

 private:
  Functor functor_;
  Term pattern_;
  std::vector<std::uint64_t> candidates_;
  std::size_t next_ = 0;
};

}  // namespace

/// The one-argument form asserts a fact: the goals are the empty list.
BuiltinResult builtinAssertFirst(Engine& engine, std::span<const Term> args) {
  const Term facts_only = makeNil();
  Clause clause = clauseFrom(engine, args[0], args.size() == 2 ? args[1] : facts_only,
                             "ДОБНАЧ");
  engine.database().insertByNamePosition(std::move(clause), 1);
  return BuiltinResult::Continue;
}

BuiltinResult builtinAssertLast(Engine& engine, std::span<const Term> args) {
  const Term facts_only = makeNil();
  Clause clause = clauseFrom(engine, args[0], args.size() == 2 ? args[1] : facts_only,
                             "ДОБКОН");
  engine.database().appendByName(std::move(clause));
  return BuiltinResult::Continue;
}

/// `УДАЛЕНИЕ(Предложение)` (`retract`): the first clause whose *head* answers to
/// the pattern, one per answer — ISO's `retract/1` minus the body, which a clause
/// term would need (part 251).
BuiltinResult builtinRetractFirst(Engine& engine, std::span<const Term> args) {
  const Term pattern = engine.bindings().deref(args[0]);
  const auto functor = functorOf(pattern);
  if (!functor) {
    badArgument(engine, args[0], "УДАЛЕНИЕ", 1, ArgKind::Text,
                "имя предиката или голова предложения");
  }
  auto walk = std::make_shared<RetractWalk>(engine, *functor, args[0]);
  BuiltinChoice choice;
  choice.produce = [walk](Engine& inner) { return walk->next(inner); };
  engine.setBuiltinChoice(std::move(choice));
  return BuiltinResult::Yield;
}

/// `УДАЛИТЬВСЕ(Предложение)` (`retractall`): every clause whose head answers to
/// the pattern, and nothing left bound — one answer, `ДА`.
BuiltinResult builtinRetractAll(Engine& engine, std::span<const Term> args) {
  const Term pattern = engine.bindings().deref(args[0]);
  const auto functor = functorOf(pattern);
  if (!functor) {
    badArgument(engine, args[0], "УДАЛИТЬВСЕ", 1, ArgKind::Text,
                "имя предиката или голова предложения");
  }
  const auto clauses = engine.database().clausesFor(functor->name, functor->arity);
  if (clauses) {
    std::vector<std::uint64_t> doomed;
    for (const Clause& clause : *clauses) {
      if (headFits(engine, clause, args[0])) {
        doomed.push_back(clause.id);
      }
    }
    for (const std::uint64_t id : doomed) {
      engine.database().retractById(functor->name, functor->arity, id);
    }
  }
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
