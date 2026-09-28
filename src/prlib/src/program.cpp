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

std::string Database::key(std::string_view name, std::size_t arity) {
  return std::string(name) + '/' + std::to_string(arity);
}

std::shared_ptr<Database::ClauseList> Database::mutableListFor(std::string_view name,
                                                               std::size_t arity) {
  const std::string k = key(name, arity);
  auto it = table_.find(k);
  if (it == table_.end()) {
    auto fresh = std::make_shared<ClauseList>();
    table_.emplace(k, fresh);
    key_order_.push_back(k);
    return fresh;
  }
  if (it->second.use_count() == 1) {
    return it->second;
  }
  // Copy-on-write: a snapshot may still be referenced by a running enumeration.
  auto copy = std::make_shared<ClauseList>(*it->second);
  it->second = copy;
  return copy;
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
  auto it = table_.find(key(name, arity));
  if (it == table_.end()) {
    return kEmpty;
  }
  return it->second;
}

bool Database::hasPredicate(std::string_view name, std::size_t arity) const {
  return table_.find(key(name, arity)) != table_.end();
}

std::size_t Database::clauseCount(std::string_view name, std::size_t arity) const {
  return clausesFor(name, arity)->size();
}

std::vector<Functor> Database::predicates() const {
  std::vector<Functor> result;
  result.reserve(table_.size());
  for (const auto& [k, list] : table_) {
    const auto slash = k.rfind('/');
    if (slash == std::string::npos) {
      continue;
    }
    Functor functor;
    functor.name = k.substr(0, slash);
    functor.arity = static_cast<std::size_t>(std::stoull(k.substr(slash + 1)));
    result.push_back(std::move(functor));
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
  const std::string prefix = std::string(name) + '/';
  for (const std::string& k : key_order_) {
    if (k.size() < prefix.size() || k.compare(0, prefix.size(), prefix) != 0) {
      continue;
    }
    auto it = table_.find(k);
    if (it == table_.end()) {
      continue;
    }
    merged.insert(merged.end(), it->second->begin(), it->second->end());
  }
  return merged;
}

std::size_t Database::clauseCountByName(std::string_view name) const {
  std::size_t total = 0;
  const std::string prefix = std::string(name) + '/';
  for (const std::string& k : key_order_) {
    if (k.size() < prefix.size() || k.compare(0, prefix.size(), prefix) != 0) {
      continue;
    }
    auto it = table_.find(k);
    if (it != table_.end()) {
      total += it->second->size();
    }
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
  key_order_.clear();
  next_id_ = 1;
}

}  // namespace prologd
