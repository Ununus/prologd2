#include <algorithm>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "builtins_internal.hpp"

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

/// What `СОРТИРОВКА` can put in order: the dialect compares numbers among
/// themselves and text among itself (5.1), and nothing else.
enum class ElementKind { Number, Text };

std::optional<ElementKind> elementKind(Engine& engine, const Term& element) {
  if (asNumeric(engine, element)) {
    return ElementKind::Number;
  }
  if (asText(engine, element)) {
    return ElementKind::Text;
  }
  return std::nullopt;
}

bool sameOrder(Engine& engine, const Term& left, const Term& right) {
  return detail::compareOrder(engine, left, right, "СОРТИРОВКА") == 0;
}

}  // namespace

BuiltinResult builtinSort(Engine& engine, std::span<const Term> args) {
  const auto elements = listElements(engine, args[0]);
  if (!elements) {
    badArguments("СОРТИРОВКА");
  }
  // Every element is looked at *before* the sort, so a list that mixes numbers
  // and text is refused once and in the same place, instead of depending on
  // which pairs the algorithm happens to compare.
  std::optional<ElementKind> kind;
  for (const Term& element : *elements) {
    const auto current = elementKind(engine, element);
    if (!current || (kind && *kind != *current)) {
      badArguments("СОРТИРОВКА");
    }
    kind = current;
  }
  std::vector<Term> sorted = *elements;
  std::stable_sort(sorted.begin(), sorted.end(),
                   [&engine](const Term& left, const Term& right) {
                     return detail::compareOrder(engine, left, right, "СОРТИРОВКА") < 0;
                   });
  // `РАВНО(1, 1.0)` holds and `БОЛЬШЕ`/`МЕНЬШЕ` call those two equal, so they are
  // one value here as well; the stable sort leaves the first of the equals in
  // front, and it is the one that stays.
  sorted.erase(std::unique(sorted.begin(), sorted.end(),
                           [&engine](const Term& left, const Term& right) {
                             return sameOrder(engine, left, right);
                           }),
               sorted.end());
  const Term result = makeListFromVector(sorted);
  return engine.unify(args[1], result) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

}  // namespace prologd
