#include <algorithm>
#include <chrono>
#include <string>
#include <string_view>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

#include "builtins_internal.hpp"
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
      if (resolved.compound != nullptr && resolved.compound->name == "$expr" &&
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

[[noreturn]] void badArguments(std::string_view predicate) {
  throw PrologRuntimeError(
      PrologError{.code = ErrorCode::TypeMismatch,
                  .message = std::string(predicate) + ": Недопустимый тип аргументов"});
}

}  // namespace detail

using detail::asFloat;
using detail::asInteger;
using detail::asNumeric;
using detail::asText;
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

BuiltinResult builtinVersion(Engine& engine, std::span<const Term>) {
  std::string text = "PrologD ";
  text += versionString();
  text += " (";
  text += buildDateString();
  text += ')';
  engine.io().write(text);
  engine.io().newline();
  return BuiltinResult::Continue;
}

BuiltinResult builtinNot(Engine& engine, std::span<const Term> args) {
  return engine.hasSolution(args[0]) ? BuiltinResult::Fail : BuiltinResult::Continue;
}

BuiltinResult builtinFirst(Engine& engine, std::span<const Term> args) {
  // `ПЕРВОЕ` (renamed from "ИЛИ", task_44) commits to the first solution of the
  // first goal that has one; the full disjunction is `A ; B` (task_41).  Any
  // positive arity, like `ВЫВОД` (task_51): one goal is «the first solution of
  // this goal» — committed, so unlike `ВЫП(Ц)` it does not backtrack into the
  // rest of that goal's solutions.
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
    badArguments("ЖДИ");
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
/// `tan`, `exp`, `mod`, `div`) or are answered outside the dispatch table
/// (`ВЫП`/`call`, handled by the solver; `ИМПОРТ`/`import`, handled by the
/// parser) — see `keywords.cpp` and `parser.cpp`.  `ПЕРВОЕ`/`first`,
/// `ВЫВОД`/`write` and `ВЫВОДПС`/`writeln` are here for their English spelling,
/// but they are registered by `kVariadicNames`, not by `add`.
constexpr std::pair<std::string_view, std::string_view> kEnglishNames[] = {
    {"ЛОЖЬ", "fail"},         {"ТРАССА", "trace"},
    {"НЕТ_ТРАССЫ", "no_trace"}, {"ТИХО", "quiet"},
    {"ВЕРСИЯ", "version"},      {"НЕ", "not"},
    {"ПЕРВОЕ", "first"},      {"РАВНО", "equal"},
    {"ПС", "nl"},            {"ЖДИ", "wait"},
    {"ПЕР", "var"},           {"ЦЕЛ", "integer"},
    {"ВЕЩ", "float"},         {"СИМВ", "is_text"},
    {"СПИСОК", "is_list"},      {"НАЙТИВСЕ", "findall"},
    {"БОЛЬШЕ", "greater"},      {"МЕНЬШЕ", "less"},
    {"СЛОЖЕНИЕ", "plus"},       {"УМНОЖЕНИЕ", "mul"},
    {"СЛУЧ", "random"},       {"ЦЕЛВЕЩ", "int_to_float"},
    {"СТРЦЕЛ", "str_to_int"},    {"СТРВЕЩ", "str_to_float"},
    {"СТРСПИС", "str_to_list"},   {"БУКВА", "is_letter"},
    {"ЦИФРА", "is_digit"},      {"СЦЕП", "concat"},
    {"КОПИЯ", "substring"},     {"ДЛИНА", "strlen"},
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
    add("ТРАССА", 0, builtinTrace);
    add("НЕТ_ТРАССЫ", 0, builtinNoTrace);
    add("ТИХО", 0, builtinQuiet);
    add("ВЕРСИЯ", 0, builtinVersion);
    add("НЕ", 1, builtinNot);
    add("РАВНО", 2, builtinEqual);
    add("ПС", 0, builtinNewline);
    add("ЖДИ", 1, builtinWait);

    // Type tests.
    add("ПЕР", 1, builtinIsVar);
    add("ЦЕЛ", 1, builtinIsInt);
    add("ВЕЩ", 1, builtinIsFloat);
    add("СИМВ", 1, builtinIsSymbol);
    add("СПИСОК", 1, builtinIsList);

    // findall.
    add("НАЙТИВСЕ", 3, builtinFindAll);

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
