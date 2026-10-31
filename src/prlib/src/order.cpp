#include "prlib/order.hpp"

#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include "prlib/bindings.hpp"

namespace prologd {

namespace {

/// Where a kind stands in the standard order: variables first, then numbers,
/// then text, then compounds.
int rankOf(const Term& term) {
  switch (term.kind) {
    case TermKind::Var:
      return 0;
    case TermKind::Int:
    case TermKind::Float:
      return 1;
    case TermKind::Atom:
    case TermKind::String:
      return 2;
    case TermKind::Compound:
      return 3;
  }
  return 3;
}

/// UTF-8 bytes compare as the code points they carry, so this is ISO's «by
/// code point» without decoding anything.
int compareText(const std::string& left, const std::string& right) {
  const int order = left.compare(right);
  return order < 0 ? -1 : (order > 0 ? 1 : 0);
}

/// One walk of two terms.  `path` holds the compound pairs being walked, so a
/// term that contains itself stops at the second visit instead of walking
/// forever — the guard `ПОЛНЫЙ` uses.
int compareTerms(const Bindings& bindings, const Term& first, const Term& second,
                 std::vector<std::pair<const CompoundTerm*, const CompoundTerm*>>& path) {
  const Term left = bindings.deref(first);
  const Term right = bindings.deref(second);
  const int leftRank = rankOf(left);
  const int rightRank = rankOf(right);
  if (leftRank != rightRank) {
    return leftRank < rightRank ? -1 : 1;
  }
  switch (leftRank) {
    case 0:
      // A variable's age is its id: `_1` came before `_2`.
      if (left.var != right.var) {
        return left.var < right.var ? -1 : 1;
      }
      return 0;
    case 1:
      // Numbers by value, exactly — the same answer `РАВНО` and the signs take
      // from `compareNumbers`, so `sort/2`, `compare/3` and unification cannot
      // call one pair equal and different at once.
      return compareNumbers(left, right);
    case 2:
      return compareText(left.text, right.text);
    default:
      break;
  }
  if (left.compound == nullptr || right.compound == nullptr) {
    return 0;  // not reachable: a compound term always carries its payload
  }
  const CompoundTerm& leftTerm = *left.compound;
  const CompoundTerm& rightTerm = *right.compound;
  // ISO: arity first, then the name, then the arguments left to right.
  if (leftTerm.args.size() != rightTerm.args.size()) {
    return leftTerm.args.size() < rightTerm.args.size() ? -1 : 1;
  }
  const int byName = compareText(leftTerm.name, rightTerm.name);
  if (byName != 0) {
    return byName;
  }
  for (const auto& seen : path) {
    if (seen.first == &leftTerm && seen.second == &rightTerm) {
      return 0;
    }
  }
  path.emplace_back(&leftTerm, &rightTerm);
  for (std::size_t index = 0; index < leftTerm.args.size(); ++index) {
    const int order = compareTerms(bindings, leftTerm.args[index], rightTerm.args[index], path);
    if (order != 0) {
      path.pop_back();
      return order;
    }
  }
  path.pop_back();
  return 0;
}

}  // namespace

int compareStandardOrder(const Bindings& bindings, const Term& first, const Term& second) {
  std::vector<std::pair<const CompoundTerm*, const CompoundTerm*>> path;
  return compareTerms(bindings, first, second, path);
}

}  // namespace prologd
