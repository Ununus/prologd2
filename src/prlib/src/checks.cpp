#include "prlib/checks.hpp"

#include <algorithm>
#include <cstddef>
#include <functional>
#include <map>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/keywords.hpp"
#include "prlib/utf8.hpp"

namespace prologd {
namespace {

/// What is known about one name: the arities it can be called with, and how it
/// is answered (`reserved` means the interpreter itself provides it).
struct NameInfo {
  std::vector<std::size_t> arities;
  bool variadic = false;
  bool reserved = false;
  bool operatorName = false;
  bool directive = false;
};

void addArity(NameInfo& info, std::size_t arity) {
  if (std::find(info.arities.begin(), info.arities.end(), arity) == info.arities.end()) {
    info.arities.push_back(arity);
  }
}

bool hasArity(const NameInfo& info, std::size_t arity) {
  if (info.variadic) {
    // `ВЫВОД/+`, `ПЕРВОЕ/+` and `ВЫП/+` take at least one argument: `ВЫВОД.`,
    // `ПЕРВОЕ.` and `ВЫП.` are errors, not a silent failure.
    return arity >= 1;
  }
  return std::find(info.arities.begin(), info.arities.end(), arity) != info.arities.end();
}

/// Every name a goal may call: the reserved names with their arities (which come
/// from the dispatch table), the predicates of the clause database and the
/// predicates the unit itself defines.  A `std::map` keeps the order stable, so
/// a suggestion never depends on hash order.
std::map<std::string, NameInfo> knownNames(const ParsedProgram& program,
                                           const Database& database) {
  std::map<std::string, NameInfo> known;
  for (const KeywordInfo& keyword : reservedKeywords()) {
    NameInfo& info = known[std::string(keyword.name)];
    if (keyword.kind == KeywordKind::Operator) {
      info.operatorName = true;
      continue;
    }
    if (keyword.kind == KeywordKind::Directive) {
      info.directive = true;
      continue;
    }
    info.reserved = true;
    info.variadic = info.variadic || keyword.variadic;
    for (const std::size_t arity : keyword.arities) {
      addArity(info, arity);
    }
  }
  for (const Functor& functor : database.predicates()) {
    addArity(known[functor.name], functor.arity);
  }
  for (const Clause& clause : program.clauses) {
    if (const std::optional<Functor> functor = functorOf(clause.head)) {
      addArity(known[functor->name], functor->arity);
    }
  }
  return known;
}

/// `2`, `3 и 4`, `1, 2 и 3` — the arities of a name in prose.
std::string describeArities(const std::vector<std::size_t>& arities) {
  std::string text;
  for (std::size_t i = 0; i < arities.size(); ++i) {
    if (i != 0) {
      text += i + 1 == arities.size() ? " и " : ", ";
    }
    text += std::to_string(arities[i]);
  }
  return text;
}

/// The code points of `text`; an invalid byte becomes U+FFFD, like everywhere
/// else in the interpreter.
std::vector<char32_t> codePoints(std::string_view text) {
  std::vector<char32_t> result;
  std::size_t offset = 0;
  while (offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    result.push_back(decoded.valid ? decoded.code_point : char32_t(0xFFFD));
    offset += std::max<std::size_t>(decoded.length, 1);
  }
  return result;
}

/// Levenshtein distance over code points, so a Cyrillic typo counts as one edit
/// per letter instead of one per byte.
std::size_t editDistance(const std::vector<char32_t>& first,
                         const std::vector<char32_t>& second) {
  std::vector<std::size_t> previous(second.size() + 1);
  std::vector<std::size_t> current(second.size() + 1);
  for (std::size_t j = 0; j <= second.size(); ++j) {
    previous[j] = j;
  }
  for (std::size_t i = 1; i <= first.size(); ++i) {
    current[0] = i;
    for (std::size_t j = 1; j <= second.size(); ++j) {
      const std::size_t substitution =
          first[i - 1] == second[j - 1] ? 0 : 1;
      current[j] = std::min({previous[j] + 1, current[j - 1] + 1,
                             previous[j - 1] + substitution});
    }
    previous.swap(current);
  }
  return previous[second.size()];
}

/// A name of the same arity within a small edit distance, written as `имя/н`.
/// An empty result means "no candidate" — never a wrong suggestion.
std::string suggestName(std::string_view name, std::size_t arity,
                        const std::map<std::string, NameInfo>& known) {
  const std::vector<char32_t> target = codePoints(name);
  const std::size_t limit = target.size() >= 5 ? 2 : 1;
  std::string best;
  std::size_t best_distance = limit + 1;
  for (const auto& [candidate, info] : known) {
    if (candidate == name || !hasArity(info, arity)) {
      continue;
    }
    const std::size_t distance = editDistance(target, codePoints(candidate));
    if (distance < best_distance) {
      best_distance = distance;
      best = candidate;
    }
  }
  if (best.empty()) {
    return {};
  }
  return best + "/" + std::to_string(arity);
}

/// Names the language has retired, with what to write instead.  A call to one
/// can never work, so it is an error — unlike a name that was never in the
/// language at all, which is a warning (the reader may have meant a name of
/// their own).  The lexer keeps these spellings reserved for the same reason
/// (`kRetiredBuiltinNames` in `lexer.cpp`): they must reach this table rather
/// than being read as variables.
struct RetiredName {
  std::string_view name;
  std::size_t arity;
  const char* message;
};

constexpr RetiredName kRetiredNames[] = {
    // `ИЛИ` was retired here in task_44 and came back in task_83 as a built-in
    // of arity two; the *English* spelling stays out of the language, because
    // the English name for this behaviour is `first`.
    {"or", 2,
     "«or» переименовано: теперь это «first(Ц1, Ц2)», а дизъюнкция — «A ; B»"},
    // The English spelling `КОПИЯ` used to answer to (task_84).  The ISO name of
    // the same work is `sub_string/5`, and its positions count from zero — hence
    // a name of its own rather than an alias.
    {"substring", 4,
     "«substring» снято: «КОПИЯ(Стр, Ц1, Ц2, Стр4)» считает позиции с 1, а "
     "форма ISO — «sub_string(Стр, До, Длина, После, Подстрока)» с позиций с 0"},
};

const char* retiredNameMessage(std::string_view name, std::size_t arity) {
  for (const RetiredName& retired : kRetiredNames) {
    if (retired.name == name && retired.arity == arity) {
      return retired.message;
    }
  }
  return nullptr;
}

/// Spellings borrowed from other Prologs that mean something the dialect writes
/// differently (task_55).  A call to one stays an ordinary unknown predicate —
/// the name is not reserved, so a program may still define its own `is/2` — but
/// the warning names the Пролог-Д spelling of the same thing.
struct ForeignSpelling {
  std::string_view name;
  std::size_t arity;
  const char* hint;
};

constexpr ForeignSpelling kForeignSpellings[] = {
    {"is", 2, "«is» — не предикат: в Пролог-Д это «РАВНО(X, #2+3#)»"},
};

const char* foreignSpellingHint(std::string_view name, std::size_t arity) {
  for (const ForeignSpelling& foreign : kForeignSpellings) {
    if (foreign.name == name && foreign.arity == arity) {
      return foreign.hint;
    }
  }
  return nullptr;
}

/// Visit every goal written in the unit as `(name, arity, location)`.
///
/// The meta-predicates whose arguments are *goals* are opened up, so
/// `ВЫП(члены(Х))` and `НАЙТИВСЕ(Х, п(Х), L)` are checked too; `НАЙТИВСЕ`'s
/// template and the arguments of `ДОБ` are terms, not goals, and stay closed.
void walkGoal(const Term& goal, const SourceLocation& location,
              const std::function<void(std::string_view, std::size_t,
                                       const SourceLocation&)>& visit) {
  if (goal.kind == TermKind::Var) {
    return;  // a variable goal is dynamic: nothing can be checked here
  }
  if (goal.kind == TermKind::Atom) {
    if (goal.text == "!") {
      return;  // the cut is answered by the solver, not by any name table
    }
    visit(goal.text, 0, location);
    return;
  }
  if (goal.kind != TermKind::Compound || goal.compound == nullptr) {
    return;
  }
  const std::string& name = goal.compound->name;
  const std::vector<Term>& args = goal.compound->args;
  const std::size_t arity = args.size();
  if (name == "," && arity == 2) {
    walkGoal(args[0], location, visit);
    walkGoal(args[1], location, visit);
    return;
  }
  if (name == ";" && arity == 2) {
    walkGoal(args[0], location, visit);
    walkGoal(args[1], location, visit);
    return;
  }
  if ((name == "ВЫП" || name == "call") && arity >= 1) {
    if (arity == 1) {
      walkGoal(args[0], location, visit);
      visit(name, 1, location);
      return;
    }
    // `call/N`: the extra arguments are appended to the goal, so what the call
    // reaches is the expanded term — `ВЫП(ф, 1)` calls `ф/1`.
    if (args[0].kind == TermKind::Atom) {
      visit(args[0].text, arity - 1, location);
    } else if (args[0].kind == TermKind::Compound && args[0].compound != nullptr) {
      std::vector<Term> expanded_args = args[0].compound->args;
      expanded_args.insert(expanded_args.end(), args.begin() + 1, args.end());
      walkGoal(makeCompound(args[0].compound->name, std::move(expanded_args)), location,
               visit);
    }
    visit(name, arity, location);
    return;
  }
  if ((name == "НЕ" || name == "not") && arity == 1) {
    walkGoal(args[0], location, visit);
    visit(name, 1, location);
    return;
  }
  if ((name == "ДЛЯВСЕХ" || name == "forall") && arity == 2) {
    walkGoal(args[0], location, visit);
    walkGoal(args[1], location, visit);
    visit(name, 2, location);
    return;
  }
  if ((name == "ПЕРВОЕ" || name == "first" || name == "ИЛИ") && arity == 2) {
    walkGoal(args[0], location, visit);
    walkGoal(args[1], location, visit);
    visit(name, 2, location);
    return;
  }
  if ((name == "НАЙТИВСЕ" || name == "findall") && arity == 3) {
    walkGoal(args[1], location, visit);
    visit(name, 3, location);
    return;
  }
  visit(name, arity, location);
}

void forEachGoal(const ParsedProgram& program,
                 const std::function<void(std::string_view, std::size_t,
                                          const SourceLocation&)>& visit) {
  for (const Clause& clause : program.clauses) {
    for (std::size_t i = 0; i < clause.body.size(); ++i) {
      const SourceLocation location = i < clause.bodyLocations.size()
                                          ? clause.bodyLocations[i]
                                          : clause.location;
      walkGoal(clause.body[i], location, visit);
    }
  }
  for (const Query& query : program.queries) {
    for (std::size_t i = 0; i < query.goals.size(); ++i) {
      const SourceLocation location = i < query.goalLocations.size()
                                          ? query.goalLocations[i]
                                          : query.location;
      walkGoal(query.goals[i], location, visit);
    }
  }
}

}  // namespace

void checkReservedCalls(const ParsedProgram& program, const Database& database,
                        DiagnosticSink& sink) {
  const std::map<std::string, NameInfo> known = knownNames(program, database);
  forEachGoal(program, [&](std::string_view name, std::size_t arity,
                           const SourceLocation& location) {
    if (const char* message = retiredNameMessage(name, arity); message != nullptr) {
      PrologError error;
      error.code = ErrorCode::UnknownPredicate;
      error.severity = Severity::Error;
      error.message = message;
      error.location = location;
      error.isParseError = true;
      sink.report(std::move(error));
      return;
    }
    const auto it = known.find(std::string(name));
    if (it == known.end() || !it->second.reserved) {
      return;  // unknown names are warnings, and they wait for the whole load
    }
    const NameInfo& info = it->second;
    if (hasArity(info, arity)) {
      return;
    }
    std::string message(name);
    message += " не имеет арности ";
    message += std::to_string(arity);
    if (!info.arities.empty()) {
      message += " (есть ";
      message += describeArities(info.arities);
      message += ')';
    }
    PrologError error;
    error.code = ErrorCode::WrongArity;
    error.severity = Severity::Error;
    error.message = std::move(message);
    error.location = location;
    error.isParseError = true;
    sink.report(std::move(error));
  });
}

void checkCallSites(const ParsedProgram& program, const Database& database,
                    const std::function<void(const PrologError&)>& report) {
  const std::map<std::string, NameInfo> known = knownNames(program, database);
  forEachGoal(program, [&](std::string_view name, std::size_t arity,
                           const SourceLocation& location) {
    const auto it = known.find(std::string(name));
    if (it != known.end() && hasArity(it->second, arity)) {
      return;
    }
    PrologError warning;
    warning.severity = Severity::Warning;
    warning.location = location;
    if (it == known.end()) {
      warning.code = ErrorCode::UnknownPredicate;
      std::string message = "не найдено: ";
      message += name;
      message += '/';
      message += std::to_string(arity);
      const std::string suggestion = suggestName(name, arity, known);
      if (!suggestion.empty()) {
        message += "; возможно, ";
        message += suggestion;
      }
      if (const char* hint = foreignSpellingHint(name, arity); hint != nullptr) {
        message += "; ";
        message += hint;
      }
      warning.message = std::move(message);
      report(warning);
      return;
    }
    const NameInfo& info = it->second;
    warning.code = ErrorCode::WrongArity;
    std::string message(name);
    if (info.operatorName) {
      message += " — оператор, а не предикат";
    } else if (info.directive) {
      message += " — директива, а не предикат";
    } else if (info.reserved) {
      message += " не имеет арности ";
      message += std::to_string(arity);
      message += " (есть ";
      message += describeArities(info.arities);
      message += ')';
    } else {
      message += " определён с арностью ";
      message += describeArities(info.arities);
      message += ", а вызван с ";
      message += std::to_string(arity);
    }
    warning.message = std::move(message);
    report(warning);
  });
}

}  // namespace prologd
