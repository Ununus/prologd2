#include "prlib/keywords.hpp"

#include <algorithm>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/lexer.hpp"

namespace prologd {

namespace {

/// Reserved names that are not predicates: the infix arithmetic operators have
/// no dispatch entry, and `ИМПОРТ` is a statement form the loader handles.
const std::unordered_set<std::string> kReservedOperators = {"mod", "div"};
const std::unordered_set<std::string> kReservedDirectives = {"ИМПОРТ", "import"};

/// Callable names the *engine* answers before it consults the dispatch table
/// (see `Solver::resolveGoal`): they are reserved and callable, but
/// `findBuiltin` never sees them, so the dispatch table cannot report their
/// arity.  `ВЫП` and `call` are `call/N` — the goal first, then any number of
/// extra arguments appended to it — so they are variadic from arity 1
/// (task_43).  The conjunction `,`/2 is handled the same way but is punctuation
/// rather than a reserved name, so it is not listed here.
const std::unordered_set<std::string> kEngineCallables = {
    "ВЫП",
    "call",
};

}  // namespace

std::string_view keywordKindName(KeywordKind kind) noexcept {
  switch (kind) {
    case KeywordKind::Predicate:
      return "predicate";
    case KeywordKind::Operator:
      return "operator";
    case KeywordKind::Directive:
      return "directive";
  }
  return "predicate";
}

std::vector<KeywordInfo> reservedKeywords() {
  const auto& names = reservedBuiltinNames();
  std::vector<KeywordInfo> result;
  result.reserve(names.size());

  for (const std::string& name : names) {
    KeywordInfo info;
    info.name = name;
    const BuiltinArities arities = builtinArities(name);
    if (arities.variadic) {
      info.kind = KeywordKind::Predicate;
      info.variadic = true;
    } else if (!arities.arities.empty()) {
      info.kind = KeywordKind::Predicate;
      info.arities = arities.arities;
    } else if (kEngineCallables.count(name) != 0) {
      // `ВЫП`/`call` are `call/N`: one argument at least, any number after.
      info.kind = KeywordKind::Predicate;
      info.variadic = true;
    } else if (kReservedOperators.count(name) != 0) {
      info.kind = KeywordKind::Operator;
    } else if (kReservedDirectives.count(name) != 0) {
      info.kind = KeywordKind::Directive;
    } else {
      // A reserved name that is neither registered nor classified.  Keep it
      // visible — the GUI must still colour it as a built-in — and let the
      // `reserved names are classified` test fail so the table gets fixed.
      info.kind = KeywordKind::Predicate;
    }
    result.push_back(std::move(info));
  }

  std::sort(result.begin(), result.end(),
            [](const KeywordInfo& left, const KeywordInfo& right) {
              return left.name < right.name;
            });
  return result;
}

}  // namespace prologd
