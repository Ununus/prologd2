#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "prlib/source_location.hpp"
#include "prlib/term.hpp"

namespace prologd {

/// A single program clause (fact when `body` is empty).
struct Clause {
  Term head;
  std::vector<Term> body;
  /// Where each goal of `body` starts in the source, one entry per goal;
  /// empty for a fact and for a clause built at run time by `ДОБ`.
  std::vector<SourceLocation> bodyLocations;
  SourceLocation location;
  std::uint64_t id = 0;
};

/// Functor of a clause head: name and arity.  Empty when the head is not a
/// callable term.
struct Functor {
  std::string name;
  std::size_t arity = 0;

  friend bool operator==(const Functor&, const Functor&) = default;
};

std::optional<Functor> functorOf(const Term& term);

/// Clause database with copy-on-write snapshots.
///
/// `clausesFor` returns an immutable snapshot.  Asserting or retracting a clause
/// replaces the snapshot for that predicate, so enumerations that are already
/// running (choice points) keep a consistent view of the database.
class Database {
 public:
  using ClauseList = std::vector<Clause>;
  using ClauseListPtr = std::shared_ptr<const ClauseList>;

  /// Append a clause at the end of its predicate's list.
  void addClause(Clause clause);
  /// Insert a clause so that it becomes the `position`-th (1-based) of its
  /// predicate; `position < 2` makes it first, a position past the end makes it
  /// last.
  void insertClause(Clause clause, std::int64_t position);
  /// Remove the `index`-th (1-based) clause; `index < 1` removes the first,
  /// an index past the end removes the last.  Returns false when the predicate
  /// has no clauses at all.
  bool retractClause(std::string_view name, std::size_t arity, std::int64_t index);

  [[nodiscard]] ClauseListPtr clausesFor(std::string_view name, std::size_t arity) const;
  [[nodiscard]] ClauseListPtr clausesFor(const Functor& functor) const {
    return clausesFor(functor.name, functor.arity);
  }
  [[nodiscard]] bool hasPredicate(std::string_view name, std::size_t arity) const;
  [[nodiscard]] std::size_t clauseCount(std::string_view name, std::size_t arity) const;

  /// Clauses of every arity sharing `name`, in definition order.
  [[nodiscard]] std::vector<Clause> clausesByName(std::string_view name) const;
  [[nodiscard]] std::size_t clauseCountByName(std::string_view name) const;
  /// Remove the `index`-th (1-based) clause of `name` across all arities.
  bool retractByNamePosition(std::string_view name, std::int64_t index);
  /// Assert `clause` so that it becomes the `position`-th clause of its own
  /// name (all arities), following the historical `ДОБ` rules.
  void insertByNamePosition(Clause clause, std::int64_t position);

  /// All predicates currently known, sorted by name/arity.
  [[nodiscard]] std::vector<Functor> predicates() const;

  void clear();

 private:
  static std::string key(std::string_view name, std::size_t arity);
  std::shared_ptr<ClauseList> mutableListFor(std::string_view name, std::size_t arity);

  std::unordered_map<std::string, std::shared_ptr<ClauseList>> table_;
  std::vector<std::string> key_order_;
  std::uint64_t next_id_ = 1;
};

}  // namespace prologd
