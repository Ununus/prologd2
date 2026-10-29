#include <algorithm>
#include <chrono>
#include <string>
#include <string_view>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

#include "builtins_internal.hpp"
#include "prlib/term_print.hpp"
#include "prlib/utf8.hpp"
#include "prlib/version.hpp"

namespace prologd {

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

namespace detail {

Term derefTerm(Engine& engine, const Term& term) { return engine.bindings().deref(term); }

bool isUnbound(Engine& engine, const Term& term) {
  return engine.bindings().deref(term).kind == TermKind::Var;
}

bool isTextual(Engine& engine, const Term& term) {
  const Term resolved = engine.bindings().deref(term);
  return resolved.kind == TermKind::Atom || resolved.kind == TermKind::String;
}

std::optional<ArithValue> asNumeric(Engine& engine, const Term& term) {
  const Term resolved = engine.bindings().deref(term);
  switch (resolved.kind) {
    case TermKind::Int:
      return ArithValue::ofInteger(resolved.integer);
    case TermKind::Float:
      return ArithValue::ofFloat(resolved.real);
    case TermKind::Compound:
      if (resolved.compound != nullptr && resolved.compound->name == kExpressionFunctor &&
          resolved.compound->args.size() == 1) {
        return engine.evaluateArithmetic(resolved);
      }
      return std::nullopt;
    default:
      return std::nullopt;
  }
}

std::optional<BigInt> asInteger(Engine& engine, const Term& term) {
  const auto value = asNumeric(engine, term);
  if (!value) {
    return std::nullopt;
  }
  return value->asInteger();
}

std::optional<double> asFloat(Engine& engine, const Term& term) {
  const auto value = asNumeric(engine, term);
  if (!value) {
    return std::nullopt;
  }
  return value->asDouble();
}

std::optional<std::string> asText(Engine& engine, const Term& term) {
  const Term resolved = engine.bindings().deref(term);
  if (resolved.kind == TermKind::Atom || resolved.kind == TermKind::String) {
    return resolved.text;
  }
  return std::nullopt;
}

Term integerTerm(const BigInt& value) { return makeInt(value); }
Term floatTerm(double value) { return makeFloat(value); }

bool unifyInteger(Engine& engine, const Term& argument, const BigInt& value) {
  return engine.unify(argument, makeInt(value));
}

bool unifyFloat(Engine& engine, const Term& argument, double value) {
  return engine.unify(argument, makeFloat(value));
}

bool unifyText(Engine& engine, const Term& argument, const std::string& value) {
  const Term resolved = engine.bindings().deref(argument);
  if (resolved.kind == TermKind::Atom) {
    return engine.unify(argument, makeAtom(value));
  }
  return engine.unify(argument, makeString(value));
}

[[noreturn]] void badArguments(Engine& engine, std::string_view predicate) {
  engine.raise(ErrorCode::TypeMismatch,
               std::string(predicate) + ": Недопустимый тип аргументов");
}

namespace {

/// How much of an argument a diagnostic may quote: it is printed as one line, and a
/// long term would either wrap it or push the expectation out of view.
constexpr std::size_t kArgumentTextLimit = 60;

/// An argument as the message shows it.  The engine's printer evaluates `#… #`, so
/// `БОЛЬШЕ(#1+1#, атом)` names the first argument `2`; an expression that cannot be
/// evaluated is named, because the printer would show `#_?_#` — a gap that says
/// nothing at all.
std::string argumentText(Engine& engine, const Term& term) {
  std::string text;
  try {
    text = engine.format(term);
  } catch (const std::exception&) {
    text = "арифметическое выражение";
  }
  if (utf8Length(text) <= kArgumentTextLimit) {
    return text;
  }
  std::string cut;
  std::size_t taken = 0;
  for (const CodePoint code_point : utf8Decode(text)) {
    if (++taken > kArgumentTextLimit) {
      break;
    }
    cut += utf8Encode(code_point);
  }
  return cut + "…";
}

bool fitsKind(Engine& engine, const Term& term, ArgKind kind) {
  if (kind == ArgKind::Number) {
    return asNumeric(engine, term).has_value();
  }
  if (kind == ArgKind::NumberOrText) {
    return asNumeric(engine, term).has_value() || asText(engine, term).has_value();
  }
  if (kind == ArgKind::Integer) {
    return asInteger(engine, term).has_value();
  }
  if (kind == ArgKind::Text) {
    return asText(engine, term).has_value();
  }
  if (kind == ArgKind::Comparable) {
    // A list is comparable, but only with a list; whether the *pair* fits is the
    // comparison's own business, not this argument's.
    return asNumeric(engine, term).has_value() || asText(engine, term).has_value() ||
           isList(engine.bindings().deref(term));
  }
  // A cell or the empty list.  Whether the list is *proper* is a different
  // question — an improper one is refused by the predicate itself, and the short
  // message is the honest one there.
  return isList(engine.bindings().deref(term));
}

std::string_view expectedText(ArgKind kind) {
  if (kind == ArgKind::Number) {
    return "число";
  }
  if (kind == ArgKind::NumberOrText) {
    return "число или текст";
  }
  if (kind == ArgKind::Integer) {
    return "целое число";
  }
  if (kind == ArgKind::Text) {
    return "строка или атом";
  }
  if (kind == ArgKind::Comparable) {
    return "число, текст или список";
  }
  return "список";
}

[[noreturn]] void raiseTypeError(Engine& engine, std::string message) {
  engine.raise(ErrorCode::TypeMismatch, std::move(message));
}

}  // namespace

[[noreturn]] void badArgument(Engine& engine, const Term& term, std::string_view predicate,
                              std::size_t index, ArgKind kind, std::string_view expected) {
  const std::string_view wanted = expected.empty() ? expectedText(kind) : expected;
  std::string message = std::string(predicate) + ": Недопустимый тип аргументов: аргумент " +
                        std::to_string(index) + " — ";
  message += isUnbound(engine, term) ? std::string("несвязанная переменная")
                                     : argumentText(engine, term);
  message += ", нужно ";
  message += wanted;
  raiseTypeError(engine, std::move(message));
}

[[noreturn]] void badArguments(Engine& engine, std::span<const Term> args,
                               std::string_view predicate, ArgKind kind,
                               std::string_view expected, std::size_t index_base) {
  std::size_t first_unbound = 0;
  for (std::size_t i = 0; i < args.size(); ++i) {
    if (isUnbound(engine, args[i])) {
      if (first_unbound == 0) {
        first_unbound = i + 1;
      }
      continue;
    }
    if (!fitsKind(engine, args[i], kind)) {
      badArgument(engine, args[i], predicate, index_base + i, kind, expected);
    }
  }
  if (first_unbound != 0) {
    badArgument(engine, args[first_unbound - 1], predicate,
                index_base + first_unbound - 1, kind, expected);
  }
  raiseTypeError(engine, std::string(predicate) + ": Недопустимый тип аргументов");
}

}  // namespace detail

using detail::ArgKind;
using detail::asFloat;
using detail::asInteger;
using detail::asNumeric;
using detail::asText;
using detail::badArgument;
using detail::badArguments;
using detail::derefTerm;
using detail::isUnbound;
using detail::unifyFloat;
using detail::unifyInteger;
using detail::unifyText;

// ---------------------------------------------------------------------------
// Control and logic
// ---------------------------------------------------------------------------

BuiltinResult builtinFalse(Engine&, std::span<const Term>) { return BuiltinResult::Fail; }

BuiltinResult builtinTrue(Engine&, std::span<const Term>) { return BuiltinResult::Continue; }

BuiltinResult builtinTrace(Engine& engine, std::span<const Term>) {
  engine.setTrace(true);
  return BuiltinResult::Continue;
}

BuiltinResult builtinNoTrace(Engine& engine, std::span<const Term>) {
  engine.setTrace(false);
  return BuiltinResult::Continue;
}

BuiltinResult builtinQuiet(Engine& engine, std::span<const Term>) {
  engine.setQuiet(true);
  return BuiltinResult::Continue;
}

/// `ВЕРСИЯ` prints the version of the *language*, not of the program: see
/// `kDialectVersion`.  `prologd --version` is where the release number lives.
BuiltinResult builtinVersion(Engine& engine, std::span<const Term>) {
  engine.io().write(kDialectVersion);
  engine.io().newline();
  return BuiltinResult::Continue;
}

BuiltinResult builtinNot(Engine& engine, std::span<const Term> args) {
  return engine.hasSolution(args[0]) ? BuiltinResult::Fail : BuiltinResult::Continue;
}

BuiltinResult builtinForall(Engine& engine, std::span<const Term> args) {
  // «Нет такого решения Условия, для которого Следствие не решается» — то же,
  // что `НЕ((Условие, НЕ(Следствие)))`, но читается как утверждение и не
  // оставляет переменных связанными.  Это и есть ISO `forall/2`.
  return engine.hasCounterexample(args[0], args[1]) ? BuiltinResult::Fail
                                                    : BuiltinResult::Continue;
}

BuiltinResult builtinFirst(Engine& engine, std::span<const Term> args) {
  // Commits to the first solution of the first goal that has one; the full
  // disjunction is `A ; B` (task_41).  Any positive arity, like `ВЫВОД`
  // (task_51): one goal is «the first solution of this goal» — committed, so
  // unlike `ВЫП(Ц)` it does not backtrack into the rest of that goal's
  // solutions.
  //
  // Two names reach this loop (task_83): `ПЕРВОЕ`, the descriptive one, at any
  // arity from one, and `ИЛИ`, the word of the original dialect, at arity two
  // — the library definition the port inherited and the manual prints,
  // `ИЛИ(X, _) :- ВЫП(X), !.` and `ИЛИ(_, X) :- ВЫП(X).`, which is exactly what
  // the loop does with two arguments.  `ИЛИ` cannot be written that way *in the
  // language*: a name starting with a capital letter is a variable in mode 0 and
  // a string constant in mode 1, so no library file can define it.
  for (const Term& goal : args) {
    if (engine.callOnce(goal)) {
      return BuiltinResult::Continue;
    }
  }
  return BuiltinResult::Fail;
}

BuiltinResult builtinEqual(Engine& engine, std::span<const Term> args) {
  return engine.unify(args[0], args[1]) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinNewline(Engine& engine, std::span<const Term>) {
  engine.io().newline();
  return BuiltinResult::Continue;
}

BuiltinResult builtinWait(Engine& engine, std::span<const Term> args) {
  const auto milliseconds = asInteger(engine, args[0]);
  if (!milliseconds) {
    badArguments(engine, args, "ЖДИ", ArgKind::Integer);
  }
  const long long value = milliseconds->toInt64();
  if (value > 0) {
    std::this_thread::sleep_for(std::chrono::milliseconds(value));
  }
  return BuiltinResult::Continue;
}

// ---------------------------------------------------------------------------
// Type tests
// ---------------------------------------------------------------------------

BuiltinResult builtinIsVar(Engine& engine, std::span<const Term> args) {
  return isUnbound(engine, args[0]) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinIsInt(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (!value) {
    return BuiltinResult::Fail;
  }
  return value->is_float ? BuiltinResult::Fail : BuiltinResult::Continue;
}

BuiltinResult builtinIsFloat(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (!value) {
    return BuiltinResult::Fail;
  }
  return value->is_float ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinIsSymbol(Engine& engine, std::span<const Term> args) {
  return detail::isTextual(engine, args[0]) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinIsList(Engine& engine, std::span<const Term> args) {
  return isList(engine.bindings().deref(args[0])) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
}

namespace {

/// One walk for `ПОЛНЫЙ`: a free variable anywhere means «не полный».
///
/// `path` is the chain of compounds being walked, so a term that contains itself
/// stops at the second visit instead of walking forever --- the guard the printer
/// uses, and for the same reason (`РАВНО(X, f(X))` is legal here: there is no
/// occurs check).  A cycle holds no free variable, so it counts as ground.
bool isGroundWalk(const Bindings& bindings, const Term& term,
                  std::vector<const CompoundTerm*>& path) {
  if (term.kind == TermKind::Var) {
    return false;
  }
  if (term.kind != TermKind::Compound || term.compound == nullptr) {
    return true;  // an atom, a whole number, a real, a string
  }
  const CompoundTerm* cell = term.compound.get();
  if (std::find(path.begin(), path.end(), cell) != path.end()) {
    return true;
  }
  path.push_back(cell);
  for (const Term& argument : term.compound->args) {
    if (!isGroundWalk(bindings, bindings.deref(argument), path)) {
      path.pop_back();
      return false;
    }
  }
  path.pop_back();
  return true;
}

}  // namespace

BuiltinResult builtinIsGround(Engine& engine, std::span<const Term> args) {
  std::vector<const CompoundTerm*> path;
  const Term resolved = engine.bindings().deref(args[0]);
  return isGroundWalk(engine.bindings(), resolved, path) ? BuiltinResult::Continue
                                                         : BuiltinResult::Fail;
}

// ---------------------------------------------------------------------------
// НАЙТИВСЕ/3
// ---------------------------------------------------------------------------

BuiltinResult builtinFindAll(Engine& engine, std::span<const Term> args) {
  const std::size_t limit = engine.options().maxFindAllSolutions;
  std::vector<Term> collected = engine.collectAll(args[1], args[0], limit);
  const Term list = makeListFromVector(collected);
  return engine.unify(args[2], list) ? BuiltinResult::Continue : BuiltinResult::Fail;
}

// ---------------------------------------------------------------------------
// ВСЕРЕШ/3 (bagof) and МНОРЕШ/3 (setof) — task_91
//
// The first built-ins that are not deterministic: one call leaves a *choice
// point* in the machine (`BuiltinResult::Yield`), and every answer binds the
// free variables of the goal as well as the bag.  The collection is done once,
// up front, exactly as `НАЙТИВСЕ` does it; the answers only hand out what was
// collected, so a side effect in the goal still happens once per solution.
// ---------------------------------------------------------------------------

namespace {

/// Turns the collected groups into answers, `sorted` for `МНОРЕШ`.
///
/// An empty collection **fails**: that is the one place where `bagof` does not
/// copy `НАЙТИВСЕ`, which answers `[]`.  Ordinary Prolog does the same, and the
/// difference is worth knowing — `ВСЕРЕШ(Х, ЛОЖЬ, С)` is a goal that does not
/// hold, not a goal with an empty bag.
BuiltinResult yieldGroups(Engine& engine, std::span<const Term> args,
                          const CollectedGroups& collected, bool sorted) {
  if (collected.groups.empty()) {
    return BuiltinResult::Fail;
  }
  BuiltinChoice choice;
  choice.answers.reserve(collected.groups.size());
  for (const GroupedSolution& group : collected.groups) {
    BuiltinAnswer answer;
    const std::size_t pairs = std::min(collected.free.size(), group.key.size());
    answer.unify.reserve(pairs + 1);
    for (std::size_t index = 0; index < pairs; ++index) {
      answer.unify.emplace_back(makeVar(collected.free[index]), group.key[index]);
    }
    std::vector<Term> values = group.values;
    if (sorted) {
      // `МНОРЕШ` is `ВСЕРЕШ` plus the order `СОРТИРОВКА/2` gives — the same
      // function, so the two cannot disagree about what «sorted» means.
      values = sortedTerms(engine, std::move(values), /*ascending=*/true,
                           /*keepDuplicates=*/false);
    }
    answer.unify.emplace_back(args[2], makeListFromVector(values));
    choice.answers.push_back(std::move(answer));
  }
  engine.setBuiltinChoice(std::move(choice));
  return BuiltinResult::Yield;
}

}  // namespace

BuiltinResult builtinBagOf(Engine& engine, std::span<const Term> args) {
  const std::size_t limit = engine.options().maxFindAllSolutions;
  const CollectedGroups collected =
      engine.collectGroupedSolutions(args[0], args[1], limit, "ВСЕРЕШ");
  return yieldGroups(engine, args, collected, /*sorted=*/false);
}

BuiltinResult builtinSetOf(Engine& engine, std::span<const Term> args) {
  const std::size_t limit = engine.options().maxFindAllSolutions;
  const CollectedGroups collected =
      engine.collectGroupedSolutions(args[0], args[1], limit, "МНОРЕШ");
  return yieldGroups(engine, args, collected, /*sorted=*/true);
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

namespace {

struct BuiltinKey {
  // A view, not an owned string: every name in the table is a string literal
  // (`add` is never called with anything else — `englishName` returns a view
  // into the same literal table), so building a `std::string` per lookup is
  // pure tax on the per-goal path (task_42).
  std::string_view name;
  std::size_t arity = 0;

  friend bool operator==(const BuiltinKey&, const BuiltinKey&) = default;
};

struct BuiltinKeyHash {
  std::size_t operator()(const BuiltinKey& key) const {
    return std::hash<std::string_view>{}(key.name) ^ (key.arity * 1099511628211ULL);
  }
};

using BuiltinTable = std::unordered_map<BuiltinKey, BuiltinFn, BuiltinKeyHash>;

/// The English spelling of every built-in that has a Russian name.
///
/// The Russian name is the one the course teaches and stays first; the alias is
/// what a reader of ordinary Prolog expects (`НАЙТИВСЕ`/`findall`), and it is
/// lowercase, like the two names that were always English in this dialect
/// (`mod`, `div`) and like `to_int`/`to_float`.  The table is *data* on purpose:
/// a name cannot be registered without its Russian original, and the alias is
/// registered by the same `add` call, so a new built-in cannot be added to the
/// dispatch table and forgotten here.
///
/// Names that are not listed are already English (`abs`, `sqrt`, `sin`, `cos`,
/// `tan`, `exp`, `mod`, `div`) or are answered outside the dispatch
/// table (`ВЫП`/`call`, handled by the solver; `ИМПОРТ`/`import`, handled by the
/// parser) — see `keywords.cpp` and `parser.cpp`.  `ПЕРВОЕ`/`first`,
/// `ВЫВОД`/`write` and `ВЫВОДПС`/`writeln` are here for their English spelling,
/// but they are registered by `kVariadicNames`, not by `add`.  `ИЛИ` is
/// deliberately not here (task_83): the word belongs to the original dialect,
/// and the English way to say the same thing is `first`, the alias of `ПЕРВОЕ`
/// (`test_aliases.cpp` allows the exception by name).
constexpr std::pair<std::string_view, std::string_view> kEnglishNames[] = {
    {"ЛОЖЬ", "fail"},         {"ИСТИНА", "true"},
    {"ТРАССА", "trace"},
    {"НЕТ_ТРАССЫ", "no_trace"}, {"ТИХО", "quiet"},
    {"ВЕРСИЯ", "version"},      {"НЕ", "not"},
    {"ДЛЯВСЕХ", "forall"},      {"ПЕРВОЕ", "first"},
    {"РАВНО", "equal"},
    {"ПС", "nl"},            {"ЖДИ", "wait"},
    {"ПЕР", "var"},           {"ЦЕЛ", "integer"},
    {"ВЕЩ", "float"},         {"СИМВ", "is_text"},
    {"СПИСОК", "is_list"},      {"ПОЛНЫЙ", "ground"},
    {"НАЙТИВСЕ", "findall"},    {"СОРТИРОВКА", "sort"},
    // `ВСЕРЕШ`/`bagof` and `МНОРЕШ`/`setof` collect by groups (task_91); the words
    // are made of the same letters as `НАЙТИВСЕ`, so a reader of the course can
    // guess them: «все решения», «много решений».
    {"ВСЕРЕШ", "bagof"},      {"МНОРЕШ", "setof"},
    {"СРАВНЕНИЕ", "compare"},
    {"БОЛЬШЕ", "greater"},      {"МЕНЬШЕ", "less"},
    {"СЛОЖЕНИЕ", "plus"},       {"УМНОЖЕНИЕ", "mul"},
    {"СЛУЧ", "random"},       {"ЦЕЛВЕЩ", "int_to_float"},
    {"СТРЦЕЛ", "str_to_int"},    {"СТРВЕЩ", "str_to_float"},
    {"СТРСПИС", "str_to_list"},   {"БУКВА", "is_letter"},
    {"ЦИФРА", "is_digit"},      {"СЦЕП", "concat"},
    {"ПОДСТРОКА", "sub_string"},
    // `КОПИЯ` has no English spelling any more (task_84): the ISO predicate for
    // the same work is `sub_string/5`, whose positions count from zero, so it is
    // a name of its own and not an alias.  `substring/4` is retired with a
    // message, and `test_aliases.cpp` allows the exception by name.
    {"ДЛИНА", "strlen"},
    {"ВЫВОД", "write"},         {"ВЫВОДПС", "writeln"},
    {"ВВКОД", "put_code"},      {"ВВОДЦЕЛ", "read_int"},
    {"ВВОДВЕЩ", "read_float"},  {"ВВОДСИМВ", "read_char"},
    {"ВВОДСТР", "read_string"}, {"ЧТЕНИЕ_ИЗ", "see"},
    {"ЗАПИСЬ_В", "tell"},       {"СКОЛЬКО", "clause_count"},
    {"ПРЕДЛ", "clause_at"},     {"ТЕРМ", "univ"},
    {"ДОБ", "assert"},          {"УДАЛЕНИЕ", "retract"},
    {"ТОЧКА", "point"},         {"ЛИНИЯ", "line"},
    {"ОКРУЖНОСТЬ", "circle"},   {"ЗАКРАСКА", "fill"},
};

/// English spelling of `name`, empty when it has none (already English, or
/// answered outside the dispatch table).
std::string_view englishName(std::string_view name) {
  for (const auto& [russian, english] : kEnglishNames) {
    if (russian == name) {
      return english;
    }
  }
  return {};
}

/// The variadic names: every positive arity is legal, so they have no table
/// entry to enumerate — `findBuiltin` looks here first.
///
/// `ВЫВОД`/`write` prints every argument (task_11); `ВЫВОДПС`/`writeln` does the
/// same and ends the line (task_53); `ПЕРВОЕ`/`first` tries every argument as a
/// goal and commits to the first one that succeeds (task_51).  Both spellings
/// of a name are listed: `add` registers the English spelling with the table,
/// and these names never reach it.
struct VariadicName {
  std::string_view name;
  BuiltinFn function;
};

constexpr VariadicName kVariadicNames[] = {
    {"ВЫВОД", builtinWrite},     {"write", builtinWrite},
    {"ВЫВОДПС", builtinWriteLine}, {"writeln", builtinWriteLine},
    {"ПЕРВОЕ", builtinFirst},    {"first", builtinFirst},
};

/// The function behind a variadic name, `nullptr` when the name is not variadic.
BuiltinFn variadicBuiltin(std::string_view name) {
  for (const VariadicName& entry : kVariadicNames) {
    if (entry.name == name) {
      return entry.function;
    }
  }
  return nullptr;
}

const BuiltinTable& builtinTable() {
  static const BuiltinTable table = [] {
    BuiltinTable result;
    // Registers the Russian name and, when it has one, its English spelling:
    // both are callable afterwards, which is what `--list-keywords`, the GUI
    // completion and the highlighter pick up from here.
    auto registerOne = [&result](std::string_view name, std::size_t arity,
                                 BuiltinFn function) {
      result.insert_or_assign(BuiltinKey{name, arity}, function);
    };
    auto add = [&registerOne](std::string_view name, std::size_t arity, BuiltinFn function) {
      registerOne(name, arity, function);
      if (const std::string_view english = englishName(name); !english.empty()) {
        registerOne(english, arity, function);
      }
    };

    // Control and logic.
    add("ЛОЖЬ", 0, builtinFalse);
    // The identity goal (part 158): without it the ISO idiom «если — то — иначе без
    // иначе», `(A -> B ; ИСТИНА)`, has nothing to fall back on — the maze example
    // needed exactly that.
    add("ИСТИНА", 0, builtinTrue);
    add("ТРАССА", 0, builtinTrace);
    add("НЕТ_ТРАССЫ", 0, builtinNoTrace);
    add("ТИХО", 0, builtinQuiet);
    add("ВЕРСИЯ", 0, builtinVersion);
    add("НЕ", 1, builtinNot);
    add("ДЛЯВСЕХ", 2, builtinForall);
    // `ПЕРВОЕ` is variadic and lives in `kVariadicNames`; `ИЛИ` is the same
    // behaviour under the dialect's own name, and only for two goals — that is
    // the shape the original had (task_83).
    add("ИЛИ", 2, builtinFirst);
    add("РАВНО", 2, builtinEqual);
    add("ПС", 0, builtinNewline);
    add("ЖДИ", 1, builtinWait);

    // Type tests.
    add("ПЕР", 1, builtinIsVar);
    add("ЦЕЛ", 1, builtinIsInt);
    add("ВЕЩ", 1, builtinIsFloat);
    add("СИМВ", 1, builtinIsSymbol);
    add("СПИСОК", 1, builtinIsList);
    add("ПОЛНЫЙ", 1, builtinIsGround);

    // findall.
    add("НАЙТИВСЕ", 3, builtinFindAll);
    add("ВСЕРЕШ", 3, builtinBagOf);
    add("МНОРЕШ", 3, builtinSetOf);

    // Lists.  `СОРТИРОВКА/2` is ISO's `sort/2`; `/3` is the same sort with the
    // order written down (task_95) — the cheap form of the `sort/4` that SWI has,
    // and `sort/2` is exactly its `sort(0, @<, …)`.
    add("СОРТИРОВКА", 2, builtinSort);
    add("СОРТИРОВКА", 3, builtinSort3);

    // The standard order of terms (task_90): `СРАВНЕНИЕ/3` is the dialect's own
    // name and `compare` its English spelling (task_94); the four `@` signs of the
    // same order are parser sugar over this call.
    add("СРАВНЕНИЕ", 3, builtinCompare);

    // Arithmetic.
    add("БОЛЬШЕ", 2, builtinGreater);
    add("МЕНЬШЕ", 2, builtinLess);
    add("СЛОЖЕНИЕ", 3, builtinAdd);
    add("УМНОЖЕНИЕ", 3, builtinMul3);
    add("УМНОЖЕНИЕ", 4, builtinMul4);
    add("abs", 2, builtinAbs);
    add("sqrt", 2, builtinSqrt);
    add("sin", 2, builtinSin);
    add("cos", 2, builtinCos);
    add("tan", 2, builtinTan);
    add("exp", 2, builtinExp);
    // `int` and `float` were never conversions: they *check* that a value can be
    // taken as a whole number, or as any number at all (`int(4.0)` holds,
    // `int(4.5)` does not, `float(4)` does).  The strict type tests take the ISO
    // names (`integer`, `float`), so these two got names that say what they do.
    // They keep the `is_` prefix that marks a predicate of ours: ISO `number/1`
    // merely fails on an unbound argument, while these raise a type error.
    add("is_whole", 1, builtinToInt);
    add("is_number", 1, builtinToFloat);
    add("СЛУЧ", 1, builtinRandom);
    add("СЛУЧ", 3, builtinRandom);
    add("ЦЕЛВЕЩ", 2, builtinConvertIntFloat);
    add("СТРЦЕЛ", 2, builtinStringToInt);
    add("СТРВЕЩ", 2, builtinStringToFloat);
    add("СТРСПИС", 2, builtinStringToList);
    // Strings.
    add("БУКВА", 2, builtinIsLetter);
    add("ЦИФРА", 2, builtinIsDigit);
    add("СЦЕП", 3, builtinConcat);
    add("КОПИЯ", 4, builtinCopy);
    // The ISO predicate of the same family (task_84): five arguments, positions
    // and lengths from zero.  It answers `ПОДСТРОКА` as well — the ISO name is
    // the spelling a reader of ordinary Prolog looks for, and the Russian one is
    // what the rest of the dialect's built-ins are called.
    add("ПОДСТРОКА", 5, builtinSubString);
    add("ДЛИНА", 2, builtinStringLength);

    // Input/output.
    add("ВВКОД", 1, builtinWriteCode);
    add("ВВОДЦЕЛ", 1, builtinReadInt);
    add("ВВОДЦЕЛ", 2, builtinReadInt);
    add("ВВОДВЕЩ", 1, builtinReadFloat);
    add("ВВОДВЕЩ", 2, builtinReadFloat);
    add("ВВОДСИМВ", 1, builtinReadSymbol);
    add("ВВОДСИМВ", 2, builtinReadSymbol);
    add("ВВОДСТР", 1, builtinReadString);
    add("ВВОДСТР", 2, builtinReadString);
    add("ЧТЕНИЕ_ИЗ", 1, builtinSee);
    add("ЗАПИСЬ_В", 1, builtinTell);

    // Program database.
    add("СКОЛЬКО", 2, builtinClauseCount);
    add("ПРЕДЛ", 4, builtinClauseInfo);
    add("ТЕРМ", 2, builtinTermConvert);
    add("ДОБ", 3, builtinAssert);
    add("УДАЛЕНИЕ", 2, builtinRetract);

    // Graphics.
    add("ТОЧКА", 3, builtinPoint);
    add("ЛИНИЯ", 5, builtinLine);
    add("ОКРУЖНОСТЬ", 4, builtinCircle);
    add("ЗАКРАСКА", 3, builtinFill);
    add("ЗАКРАСКА", 5, builtinFillRect);
    return result;
  }();
  return table;
}

}  // namespace

BuiltinFn findBuiltin(std::string_view name, std::size_t arity) {
  // The variadic names accept any positive arity (`ВЫВОД`, `ВЫВОДПС`, `ПЕРВОЕ`).
  if (BuiltinFn variadic = variadicBuiltin(name); variadic != nullptr && arity >= 1) {
    return variadic;
  }
  const auto& table = builtinTable();
  const auto it = table.find(BuiltinKey{name, arity});
  if (it == table.end()) {
    return nullptr;
  }
  return it->second;
}

std::span<const BuiltinAlias> builtinAliases() { return kEnglishNames; }

BuiltinArities builtinArities(std::string_view name) {
  // A variadic name has no table entry to enumerate: `findBuiltin` accepts any
  // positive arity for it.
  if (variadicBuiltin(name) != nullptr) {
    return BuiltinArities{{}, true};
  }
  BuiltinArities result;
  for (const auto& entry : builtinTable()) {
    if (entry.first.name == name) {
      result.arities.push_back(entry.first.arity);
    }
  }
  std::sort(result.arities.begin(), result.arities.end());
  return result;
}

std::vector<std::string> builtinNames() {
  std::vector<std::string> result;
  result.reserve(builtinTable().size() + std::size(kVariadicNames));
  for (const auto& entry : builtinTable()) {
    result.emplace_back(entry.first.name);
  }
  for (const VariadicName& entry : kVariadicNames) {
    result.emplace_back(entry.name);  // variadic: the names without a table entry
  }
  std::sort(result.begin(), result.end());
  result.erase(std::unique(result.begin(), result.end()), result.end());
  return result;
}

}  // namespace prologd
