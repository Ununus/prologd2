#include <algorithm>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "builtins_internal.hpp"
#include "prlib/order.hpp"

namespace prologd {

namespace {

using detail::asNumeric;
using detail::asText;
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

bool sameOrder(Engine& engine, const Term& left, const Term& right) {
  return compareStandardOrder(engine.bindings(), left, right) == 0;
}

}  // namespace

BuiltinResult builtinSort(Engine& engine, std::span<const Term> args) {
  const auto elements = listElements(engine, args[0]);
  if (!elements) {
    badArguments("СОРТИРОВКА");
  }
  std::vector<Term> sorted = *elements;
  std::stable_sort(sorted.begin(), sorted.end(),
                   [&engine](const Term& left, const Term& right) {
                     return compareStandardOrder(engine.bindings(), left, right) < 0;
                   });
  // Whatever the order calls equal is one value here — `РАВНО(1, 1.0)` holds,
  // and two text constants with the same letters are one value too; the stable
  // sort leaves the first of the equals in front, and it is the one that stays.
  sorted.erase(std::unique(sorted.begin(), sorted.end(),
                           [&engine](const Term& left, const Term& right) {
                             return sameOrder(engine, left, right);
                           }),
               sorted.end());
  const Term result = makeListFromVector(sorted);
  return engine.unify(args[1], result) ? BuiltinResult::Continue : BuiltinResult::Fail;
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
