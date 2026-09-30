#include "prlib/program.hpp"

#include <algorithm>

namespace prologd {

std::optional<Functor> functorOf(const Term& term) {
  if (term.kind == TermKind::Atom) {
    return Functor{term.text, 0};
  }
  if (term.kind == TermKind::Compound && term.compound != nullptr) {
    return Functor{term.compound->name, term.compound->args.size()};
  }
  return std::nullopt;
}

std::shared_ptr<Database::ClauseList> Database::mutableListFor(std::string_view name,
                                                               std::size_t arity) {
  auto it = table_.find(name);
  if (it == table_.end()) {
    auto fresh = std::make_shared<ClauseList>();
    Predicate entry;
    entry.by_arity.emplace_back(arity, fresh);
    table_.emplace(std::string(name), std::move(entry));
    return fresh;
  }
  for (auto& [list_arity, list] : it->second.by_arity) {
    if (list_arity != arity) {
      continue;
    }
    if (list.use_count() == 1) {
      return list;
    }
    // Copy-on-write: a snapshot may still be referenced by a running enumeration.
    auto copy = std::make_shared<ClauseList>(*list);
    list = copy;
    return copy;
  }
  auto fresh = std::make_shared<ClauseList>();
  it->second.by_arity.emplace_back(arity, fresh);
  return fresh;
}

void Database::addClause(Clause clause) {
  const auto functor = functorOf(clause.head);
  if (!functor) {
    return;
  }
  clause.id = next_id_++;
  mutableListFor(functor->name, functor->arity)->push_back(std::move(clause));
}

void Database::insertClause(Clause clause, std::int64_t position) {
  const auto functor = functorOf(clause.head);
  if (!functor) {
    return;
  }
  clause.id = next_id_++;
  auto list = mutableListFor(functor->name, functor->arity);
  if (position < 2 || list->empty()) {
    list->insert(list->begin(), std::move(clause));
    return;
  }
  const auto index = static_cast<std::size_t>(position - 1);
  if (index >= list->size()) {
    list->push_back(std::move(clause));
    return;
  }
  list->insert(list->begin() + static_cast<std::ptrdiff_t>(index), std::move(clause));
}

bool Database::retractClause(std::string_view name, std::size_t arity, std::int64_t index) {
  auto existing = clausesFor(name, arity);
  if (existing->empty()) {
    return false;
  }
  std::size_t target = 0;
  if (index < 1) {
    target = 0;
  } else {
    target = static_cast<std::size_t>(index - 1);
    if (target >= existing->size()) {
      target = existing->size() - 1;
    }
  }
  auto list = mutableListFor(name, arity);
  list->erase(list->begin() + static_cast<std::ptrdiff_t>(target));
  return true;
}

Database::ClauseListPtr Database::clausesFor(std::string_view name, std::size_t arity) const {
  static const auto kEmpty = std::make_shared<const ClauseList>();
  auto it = table_.find(name);
  if (it == table_.end()) {
    return kEmpty;
  }
  for (const auto& [list_arity, list] : it->second.by_arity) {
    if (list_arity == arity) {
      return list;
    }
  }
  return kEmpty;
}

bool Database::hasPredicate(std::string_view name, std::size_t arity) const {
  auto it = table_.find(name);
  if (it == table_.end()) {
    return false;
  }
  for (const auto& [list_arity, list] : it->second.by_arity) {
    if (list_arity == arity) {
      return true;
    }
  }
  return false;
}

std::size_t Database::clauseCount(std::string_view name, std::size_t arity) const {
  return clausesFor(name, arity)->size();
}

std::vector<Functor> Database::predicates() const {
  std::vector<Functor> result;
  for (const auto& [name, entry] : table_) {
    for (const auto& [arity, list] : entry.by_arity) {
      result.push_back(Functor{name, arity});
    }
  }
  std::sort(result.begin(), result.end(), [](const Functor& lhs, const Functor& rhs) {
    if (lhs.name != rhs.name) {
      return lhs.name < rhs.name;
    }
    return lhs.arity < rhs.arity;
  });
  return result;
}

std::vector<Clause> Database::clausesByName(std::string_view name) const {
  std::vector<Clause> merged;
  auto it = table_.find(name);
  if (it == table_.end()) {
    return merged;
  }
  for (const auto& [arity, list] : it->second.by_arity) {
    merged.insert(merged.end(), list->begin(), list->end());
  }
  return merged;
}

std::size_t Database::clauseCountByName(std::string_view name) const {
  std::size_t total = 0;
  auto it = table_.find(name);
  if (it == table_.end()) {
    return total;
  }
  for (const auto& [arity, list] : it->second.by_arity) {
    total += list->size();
  }
  return total;
}

bool Database::retractByNamePosition(std::string_view name, std::int64_t index) {
  const std::vector<Clause> merged = clausesByName(name);
  if (merged.empty()) {
    return false;
  }
  std::size_t target = 0;
  if (index < 1) {
    target = 0;
  } else {
    target = static_cast<std::size_t>(index - 1);
    if (target >= merged.size()) {
      target = merged.size() - 1;
    }
  }
  const std::uint64_t clause_id = merged[target].id;
  const auto functor = functorOf(merged[target].head);
  if (!functor) {
    return false;
  }
  auto list = mutableListFor(functor->name, functor->arity);
  for (auto it = list->begin(); it != list->end(); ++it) {
    if (it->id == clause_id) {
      list->erase(it);
      return true;
    }
  }
  return false;
}

void Database::insertByNamePosition(Clause clause, std::int64_t position) {
  const auto functor = functorOf(clause.head);
  if (!functor) {
    return;
  }
  clause.id = next_id_++;
  auto list = mutableListFor(functor->name, functor->arity);
  if (position < 2 || list->empty()) {
    list->insert(list->begin(), std::move(clause));
    return;
  }
  // Count how many clauses of this name (any arity) precede each slot of this
  // predicate's own list, to translate the name-wide position.
  const std::vector<Clause> merged = clausesByName(functor->name);
  const auto target = static_cast<std::size_t>(position - 1);
  if (target >= merged.size()) {
    list->push_back(std::move(clause));
    return;
  }
  const std::uint64_t anchor = merged[target].id;
  std::size_t own_index = list->size();
  for (std::size_t i = 0; i < list->size(); ++i) {
    if ((*list)[i].id == anchor) {
      own_index = i;
      break;
    }
  }
  list->insert(list->begin() + static_cast<std::ptrdiff_t>(own_index), std::move(clause));
}

void Database::clear() {
  table_.clear();
  next_id_ = 1;
}

}  // namespace prologd
