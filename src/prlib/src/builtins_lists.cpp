#include <algorithm>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "builtins_internal.hpp"
#include "prlib/order.hpp"

namespace prologd {

std::vector<Term> sortedTerms(Engine& engine, std::vector<Term> elements, bool ascending,
                              bool keepDuplicates) {
  std::stable_sort(elements.begin(), elements.end(),
                   [&engine, ascending](const Term& left, const Term& right) {
                     const int sign = compareStandardOrder(engine.bindings(), left, right);
                     return ascending ? sign < 0 : sign > 0;
                   });
  if (!keepDuplicates) {
    // Whatever the order calls equal is one value here — `РАВНО(1, 1.0)` holds,
    // and two text constants with the same letters are one value too; the stable
    // sort leaves the first of the equals in front, and it is the one that stays.
    elements.erase(std::unique(elements.begin(), elements.end(),
                               [&engine](const Term& left, const Term& right) {
                                 return compareStandardOrder(engine.bindings(), left, right) ==
                                        0;
                               }),
                   elements.end());
  }
  return elements;
}

namespace {

using detail::ArgKind;
using detail::asNumeric;
using detail::asText;
using detail::badArgument;
using detail::badArguments;

/// The elements of `argument`, with every tail dereferenced, or `nullopt` when it
/// is not a proper list of elements.
///
/// Both refusals matter: a listlike tail (`[1 | 2]`) is not a list of elements,
/// and a list that contains itself would send the plain loop of `listToVector`
/// walking forever.  The visited set is what makes the second one an error
/// instead of a hang (`РАВНО(X, [1 | X])` is legal here — there is no occurs
/// check).
std::optional<std::vector<Term>> listElements(Engine& engine, const Term& argument) {
  std::vector<Term> elements;
  std::unordered_set<const CompoundTerm*> visited;
  Term current = engine.deref(argument);
  while (isListCell(current)) {
    if (!visited.insert(current.compound.get()).second) {
      return std::nullopt;
    }
    elements.push_back(current.compound->args[0]);
    current = engine.deref(current.compound->args[1]);
  }
  if (!isNil(current)) {
    return std::nullopt;
  }
  return elements;
}

/// How `СОРТИРОВКА/3` was asked to order the list (task_95).
///
/// The four signs are the standard order read in two directions, and the duplicate
/// rule follows SWI's `sort/4`: the two signs that admit equality -- `@=<` and
/// `@>=` -- are the two that **keep** repeats, because a repeat is equal to its
/// twin.  It reads backwards until it is said out loud, so the manual says it
/// twice.
struct SortOrder {
  bool ascending = true;
  bool keepDuplicates = false;
};

/// The order named by `argument`, or `nullopt` when it is not one of the four.
std::optional<SortOrder> sortOrderFrom(Engine& engine, const Term& argument) {
  const auto text = asText(engine, argument);
  if (!text) {
    return std::nullopt;
  }
  if (*text == "@<") {
    return SortOrder{true, false};
  }
  if (*text == "@=<") {
    return SortOrder{true, true};
  }
  if (*text == "@>") {
    return SortOrder{false, false};
  }
  if (*text == "@>=") {
    return SortOrder{false, true};
  }
  return std::nullopt;
}

/// The one sort both arities share: copy `source` in the standard order, drop the
/// repeats when the order says so, and unify `result` with that list.
///
/// `argument` is the number `source` carries among the predicate's arguments, so a
/// refusal counts the way the caller does (part 136).  A list that is not *proper*
/// keeps the short message: it is a list, just not one that ends.
BuiltinResult sortTerms(Engine& engine, const Term& source, const Term& result,
                        const SortOrder& order, std::size_t argument) {
  const auto elements = listElements(engine, source);
  if (!elements) {
    badArguments(engine, std::span<const Term>(&source, 1), "СОРТИРОВКА", ArgKind::List, {},
                 argument);
  }
  std::vector<Term> sorted = sortedTerms(engine, *elements, order.ascending,
                                         order.keepDuplicates);
  const Term answer = makeListFromVector(sorted);
  return engine.unify(result, answer) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

}  // namespace

BuiltinResult builtinSort(Engine& engine, std::span<const Term> args) {
  // ISO's `sort/2`: ascending, repeats dropped — `СОРТИРОВКА/3` with `@<` written
  // out, and both arities go through one function so they cannot disagree (task_95).
  return sortTerms(engine, args[0], args[1], SortOrder{}, 1);
}

BuiltinResult builtinSort3(Engine& engine, std::span<const Term> args) {
  const auto order = sortOrderFrom(engine, args[0]);
  if (!order) {
    badArgument(engine, args[0], "СОРТИРОВКА", 1, ArgKind::Text, "@<, @=<, @> или @>=");
  }
  return sortTerms(engine, args[1], args[2], *order, 2);
}

BuiltinResult builtinCompare(Engine& engine, std::span<const Term> args) {
  // ISO's `compare(Order, X, Y)`: the first argument may be free (it is bound to
  // `<`, `=` or `>`) or given, in which case the call simply tests.  This is
  // also what the four `@` signs are sugar for, so the two answer alike.
  const int order = compareStandardOrder(engine.bindings(), args[1], args[2]);
  const char* const answer = order < 0 ? "<" : (order > 0 ? ">" : "=");
  return engine.unify(args[0], makeAtom(answer)) ? BuiltinResult::Continue
                                                 : BuiltinResult::Fail;
}

}  // namespace prologd
