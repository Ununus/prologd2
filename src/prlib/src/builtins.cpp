#include <chrono>
#include <thread>
#include <unordered_map>

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
  throw PrologRuntimeError(PrologError{
      ErrorCode::TypeMismatch, std::string(predicate) + ": Недопустимый тип аргументов", {}, false});
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

BuiltinResult builtinOr(Engine& engine, std::span<const Term> args) {
  // `ИЛИ` commits to the first solution of its first goal, exactly like the
  // library clause `ИЛИ(X,_) <- ВЫП(X), !`.
  if (engine.callOnce(args[0]) || engine.callOnce(args[1])) {
    return BuiltinResult::Continue;
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
// НАЙТИВСЁ/3
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
  std::string name;
  std::size_t arity;

  friend bool operator==(const BuiltinKey&, const BuiltinKey&) = default;
};

struct BuiltinKeyHash {
  std::size_t operator()(const BuiltinKey& key) const {
    return std::hash<std::string>{}(key.name) ^ (key.arity * 1099511628211ULL);
  }
};

using BuiltinTable = std::unordered_map<BuiltinKey, BuiltinFn, BuiltinKeyHash>;

const BuiltinTable& builtinTable() {
  static const BuiltinTable table = [] {
    BuiltinTable result;
    auto add = [&result](std::string_view name, std::size_t arity, BuiltinFn function) {
      result.emplace(BuiltinKey{std::string(name), arity}, function);
    };

    // Control and logic.
    add("ЛОЖЬ", 0, builtinFalse);
    add("ТРАССА", 0, builtinTrace);
    add("НЕТ_ТРАССЫ", 0, builtinNoTrace);
    add("ТИХО", 0, builtinQuiet);
    add("ВЕРСИЯ", 0, builtinVersion);
    add("НЕ", 1, builtinNot);
    add("ИЛИ", 2, builtinOr);
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
    add("НАЙТИВСЁ", 3, builtinFindAll);

    // Arithmetic.
    add("БОЛЬШЕ", 2, builtinGreater);
    add("МЕНЬШЕ", 2, builtinLess);
    add("СЛОЖЕНИЕ", 3, builtinAdd);
    add("УМНОЖЕНИЕ", 3, builtinMul3);
    add("УМНОЖЕНИЕ", 4, builtinMul4);
    add("ABS", 2, builtinAbs);
    add("SQRT", 2, builtinSqrt);
    add("SIN", 2, builtinSin);
    add("COS", 2, builtinCos);
    add("TAN", 2, builtinTan);
    add("EXP", 2, builtinExp);
    add("int", 1, builtinToInt);
    add("float", 1, builtinToFloat);
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
  // `ВЫВОД` accepts any positive arity.
  if (name == "ВЫВОД" && arity >= 1) {
    return builtinWrite;
  }
  const auto& table = builtinTable();
  const auto it = table.find(BuiltinKey{std::string(name), arity});
  if (it == table.end()) {
    return nullptr;
  }
  return it->second;
}

}  // namespace prologd
