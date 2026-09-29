#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <optional>
#include <random>
#include <string>

#include "builtins_internal.hpp"
#include "prlib/term_print.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

using detail::asNumeric;
using detail::asText;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyFloat;
using detail::unifyInteger;
using detail::unifyText;

namespace {

std::mt19937_64& randomEngine() {
  static std::mt19937_64 engine(std::random_device{}());
  return engine;
}

bool isExpressionWrapper(const Term& term) {
  return term.kind == TermKind::Compound && term.compound != nullptr &&
         term.compound->name == "$expr" && term.compound->args.size() == 1;
}

int compareValues(const ArithValue& left, const ArithValue& right) {
  if (!left.is_float && !right.is_float) {
    if (left.integer < right.integer) {
      return -1;
    }
    if (left.integer > right.integer) {
      return 1;
    }
    return 0;
  }
  const double a = left.asDouble();
  const double b = right.asDouble();
  if (a < b) {
    return -1;
  }
  if (a > b) {
    return 1;
  }
  return 0;
}

BuiltinResult unifyValue(Engine& engine, const Term& target, const ArithValue& value) {
  if (value.is_float) {
    return unifyFloat(engine, target, value.real) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
  }
  return unifyInteger(engine, target, value.integer) ? BuiltinResult::Continue
                                                     : BuiltinResult::Fail;
}

BuiltinResult compareGreater(Engine& engine, const Term& first, const Term& second,
                             bool swap) {
  const auto left = asNumeric(engine, first);
  const auto right = asNumeric(engine, second);
  if (left && right) {
    const int cmp = compareValues(*left, *right);
    const bool greater = swap ? cmp < 0 : cmp > 0;
    return greater ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  const auto leftText = asText(engine, first);
  const auto rightText = asText(engine, second);
  if (leftText && rightText) {
    const bool greater = swap ? (*leftText < *rightText) : (*leftText > *rightText);
    return greater ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  badArguments(swap ? "МЕНЬШЕ" : "БОЛЬШЕ");
}
}  // namespace

BuiltinResult builtinGreater(Engine& engine, std::span<const Term> args) {
  return compareGreater(engine, args[0], args[1], false);
}

BuiltinResult builtinLess(Engine& engine, std::span<const Term> args) {
  return compareGreater(engine, args[0], args[1], true);
}

// ---------------------------------------------------------------------------
// Addition
// ---------------------------------------------------------------------------

BuiltinResult builtinAdd(Engine& engine, std::span<const Term> args) {
  const Term& a = args[0];
  const Term& b = args[1];
  const Term& c = args[2];
  const auto av = asNumeric(engine, a);
  const auto bv = asNumeric(engine, b);
  const auto cv = asNumeric(engine, c);
  if (!av && !isUnbound(engine, a)) {
    badArguments("СЛОЖЕНИЕ");
  }
  if (!bv && !isUnbound(engine, b)) {
    badArguments("СЛОЖЕНИЕ");
  }
  if (!cv && !isUnbound(engine, c)) {
    badArguments("СЛОЖЕНИЕ");
  }
  const int known = (av ? 1 : 0) + (bv ? 1 : 0) + (cv ? 1 : 0);
  const bool anyFloat = (av && av->is_float) || (bv && bv->is_float) || (cv && cv->is_float);
  if (known == 3) {
    ArithValue expected;
    if (anyFloat) {
      expected = ArithValue::ofFloat(av->asDouble() + bv->asDouble());
      return expected.real == cv->asDouble() ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    expected = ArithValue::ofInteger(av->integer + bv->integer);
    return expected.integer == cv->integer ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (known == 2) {
    if (av && bv) {
      if (anyFloat) {
        return unifyValue(engine, c, ArithValue::ofFloat(av->asDouble() + bv->asDouble()));
      }
      return unifyValue(engine, c, ArithValue::ofInteger(av->integer + bv->integer));
    }
    if (av && cv) {
      if (anyFloat) {
        return unifyValue(engine, b, ArithValue::ofFloat(cv->asDouble() - av->asDouble()));
      }
      return unifyValue(engine, b, ArithValue::ofInteger(cv->integer - av->integer));
    }
    if (bv && cv) {
      if (anyFloat) {
        return unifyValue(engine, a, ArithValue::ofFloat(cv->asDouble() - bv->asDouble()));
      }
      return unifyValue(engine, a, ArithValue::ofInteger(cv->integer - bv->integer));
    }
  }
  badArguments("СЛОЖЕНИЕ");
}

// ---------------------------------------------------------------------------
// Multiplication
// ---------------------------------------------------------------------------

BuiltinResult builtinMul3(Engine& engine, std::span<const Term> args) {
  const Term& a = args[0];
  const Term& b = args[1];
  const Term& c = args[2];
  const auto av = asNumeric(engine, a);
  const auto bv = asNumeric(engine, b);
  const auto cv = asNumeric(engine, c);
  if (!av && !isUnbound(engine, a)) {
    badArguments("УМНОЖЕНИЕ");
  }
  if (!bv && !isUnbound(engine, b)) {
    badArguments("УМНОЖЕНИЕ");
  }
  if (!cv && !isUnbound(engine, c)) {
    badArguments("УМНОЖЕНИЕ");
  }
  const int known = (av ? 1 : 0) + (bv ? 1 : 0) + (cv ? 1 : 0);
  const bool anyFloat = (av && av->is_float) || (bv && bv->is_float) || (cv && cv->is_float);
  if (known == 3) {
    if (anyFloat) {
      return (av->asDouble() * bv->asDouble() == cv->asDouble()) ? BuiltinResult::Continue
                                                                 : BuiltinResult::Fail;
    }
    return (av->integer * bv->integer == cv->integer) ? BuiltinResult::Continue
                                                      : BuiltinResult::Fail;
  }
  if (known == 2) {
    if (av && bv) {
      if (anyFloat) {
        return unifyValue(engine, c, ArithValue::ofFloat(av->asDouble() * bv->asDouble()));
      }
      return unifyValue(engine, c, ArithValue::ofInteger(av->integer * bv->integer));
    }
    if (bv && cv) {
      if (bv->is_float ? bv->real == 0.0 : bv->integer.isZero()) {
        return BuiltinResult::Fail;
      }
      if (bv->is_float || cv->is_float) {
        return unifyValue(engine, a, ArithValue::ofFloat(cv->asDouble() / bv->asDouble()));
      }
      if ((cv->integer % bv->integer).isZero()) {
        return unifyValue(engine, a, ArithValue::ofInteger(cv->integer / bv->integer));
      }
      return unifyValue(engine, a, ArithValue::ofFloat(cv->asDouble() / bv->asDouble()));
    }
    if (av && cv) {
      if (av->is_float ? av->real == 0.0 : av->integer.isZero()) {
        return BuiltinResult::Fail;
      }
      if (av->is_float || cv->is_float) {
        return unifyValue(engine, b, ArithValue::ofFloat(cv->asDouble() / av->asDouble()));
      }
      if ((cv->integer % av->integer).isZero()) {
        return unifyValue(engine, b, ArithValue::ofInteger(cv->integer / av->integer));
      }
      return unifyValue(engine, b, ArithValue::ofFloat(cv->asDouble() / av->asDouble()));
    }
  }
  badArguments("УМНОЖЕНИЕ");
}

BuiltinResult builtinMul4(Engine& engine, std::span<const Term> args) {
  const Term& a = args[0];
  const Term& b = args[1];
  const Term& c = args[2];
  const Term& d = args[3];
  const auto ai = detail::asInteger(engine, a);
  const auto bi = detail::asInteger(engine, b);
  const auto ci = detail::asInteger(engine, c);
  const auto di = detail::asInteger(engine, d);
  const auto af = detail::asFloat(engine, a);
  const auto bf = detail::asFloat(engine, b);
  const auto cf = detail::asFloat(engine, c);
  const auto df = detail::asFloat(engine, d);
  const auto an = asNumeric(engine, a);
  const auto bn = asNumeric(engine, b);
  const auto cn = asNumeric(engine, c);
  const auto dn = asNumeric(engine, d);
  const bool aNum = an.has_value();
  const bool bNum = bn.has_value();
  const bool cNum = cn.has_value();
  const bool dNum = dn.has_value();
  const bool anyFloat = (an && an->is_float) || (bn && bn->is_float) ||
                        (cn && cn->is_float) || (dn && dn->is_float);

  if (aNum && bNum && cNum && dNum) {
    if (anyFloat) {
      return (*af * *bf + *cf == *df) ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    return (*ai * *bi + *ci == *di) ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (aNum && bNum && cNum && isUnbound(engine, d)) {
    if (anyFloat) {
      return unifyValue(engine, d, ArithValue::ofFloat(*af * *bf + *cf));
    }
    return unifyValue(engine, d, ArithValue::ofInteger(*ai * *bi + *ci));
  }
  if (aNum && bNum && isUnbound(engine, c) && dNum) {
    if (anyFloat) {
      return unifyValue(engine, c, ArithValue::ofFloat(*df - *af * *bf));
    }
    return unifyValue(engine, c, ArithValue::ofInteger(*di - *ai * *bi));
  }
  if (!anyFloat && isUnbound(engine, a) && bNum && cNum && dNum) {
    if (!bi || bi->isZero()) {
      return BuiltinResult::Fail;
    }
    const BigInt work = *di - *ci;
    if ((work % *bi).isZero()) {
      return unifyValue(engine, a, ArithValue::ofInteger(work / *bi));
    }
    return BuiltinResult::Fail;
  }
  if (!anyFloat && isUnbound(engine, b) && aNum && cNum && dNum) {
    if (!ai || ai->isZero()) {
      return BuiltinResult::Fail;
    }
    const BigInt work = *di - *ci;
    if ((work % *ai).isZero()) {
      return unifyValue(engine, b, ArithValue::ofInteger(work / *ai));
    }
    return BuiltinResult::Fail;
  }
  if (aNum && isUnbound(engine, b) && isUnbound(engine, c) && dNum) {
    if (!ai || ai->isZero()) {
      return BuiltinResult::Fail;
    }
    const bool ok = unifyInteger(engine, b, *di / *ai) && unifyInteger(engine, c, *di % *ai);
    return ok ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (isUnbound(engine, a) && bNum && isUnbound(engine, c) && dNum) {
    if (!bi || bi->isZero()) {
      return BuiltinResult::Fail;
    }
    const bool ok = unifyInteger(engine, a, *di / *bi) && unifyInteger(engine, c, *di % *bi);
    return ok ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  // Float fallbacks for the "one unknown" cases.
  if (isUnbound(engine, a) && bf && cf && df && *bf != 0.0) {
    return unifyValue(engine, a, ArithValue::ofFloat((*df - *cf) / *bf));
  }
  if (isUnbound(engine, b) && af && cf && df && *af != 0.0) {
    return unifyValue(engine, b, ArithValue::ofFloat((*df - *cf) / *af));
  }
  badArguments("УМНОЖЕНИЕ");
}

// ---------------------------------------------------------------------------
// Elementary functions
// ---------------------------------------------------------------------------

BuiltinResult builtinAbs(Engine& engine, std::span<const Term> args) {
  const auto x = asNumeric(engine, args[0]);
  const auto y = asNumeric(engine, args[1]);
  if (x && !y && isUnbound(engine, args[1])) {
    if (x->is_float) {
      return unifyFloat(engine, args[1], std::fabs(x->real)) ? BuiltinResult::Continue
                                                             : BuiltinResult::Fail;
    }
    return unifyInteger(engine, args[1], x->integer.abs()) ? BuiltinResult::Continue
                                                           : BuiltinResult::Fail;
  }
  if (!x && isUnbound(engine, args[0]) && y) {
    const double value = y->asDouble();
    if (value < 0) {
      return BuiltinResult::Fail;
    }
    return unifyValue(engine, args[0], *y);
  }
  if (x && y) {
    if (x->is_float || y->is_float) {
      return std::fabs(x->asDouble()) == y->asDouble() ? BuiltinResult::Continue
                                                       : BuiltinResult::Fail;
    }
    return x->integer.abs() == y->integer ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  badArguments("ABS");
}

BuiltinResult builtinSqrt(Engine& engine, std::span<const Term> args) {
  const auto x = asNumeric(engine, args[0]);
  const auto y = asNumeric(engine, args[1]);
  if (x && !y && isUnbound(engine, args[1])) {
    const double root = std::sqrt(x->asDouble());
    // A negative argument has no real root.  `BigInt::fromDouble(nan)` is zero,
    // so without this check `SQRT(-4, X)` *succeeded* and said the root of -4 is
    // 0, and the float mode unified `nan` — a value that is not a number at all.
    if (!std::isfinite(root)) {
      return BuiltinResult::Fail;
    }
    if (x->is_float) {
      return unifyFloat(engine, args[1], root) ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    return unifyInteger(engine, args[1], BigInt::fromDouble(root)) ? BuiltinResult::Continue
                                                                   : BuiltinResult::Fail;
  }
  if (!x && isUnbound(engine, args[0]) && y) {
    if (y->is_float) {
      return unifyFloat(engine, args[0], y->real * y->real) ? BuiltinResult::Continue
                                                            : BuiltinResult::Fail;
    }
    return unifyInteger(engine, args[0], y->integer * y->integer) ? BuiltinResult::Continue
                                                                  : BuiltinResult::Fail;
  }
  if (x && y) {
    return std::sqrt(x->asDouble()) == y->asDouble() ? BuiltinResult::Continue
                                                     : BuiltinResult::Fail;
  }
  badArguments("SQRT");
}

namespace {

BuiltinResult unaryFloat(Engine& engine, std::span<const Term> args, double (*forward)(double),
                         double (*inverse)(double), std::string_view name) {
  const auto x = asNumeric(engine, args[0]);
  const auto y = asNumeric(engine, args[1]);
  if (x && !y && isUnbound(engine, args[1])) {
    const double value = forward(x->asDouble());
    // Out of the domain of the inverse function — `ln` of a negative number,
    // `asin` of 2 — the result is not a number, and unifying `nan` with the
    // argument would be a lie about what the interpreter computed.  (The forward
    // direction can also overflow to infinity: `EXP(1000.0, X)`.)
    if (!std::isfinite(value)) {
      return BuiltinResult::Fail;
    }
    return unifyFloat(engine, args[1], value) ? BuiltinResult::Continue
                                              : BuiltinResult::Fail;
  }
  if (!x && isUnbound(engine, args[0]) && y) {
    const double value = inverse(y->asDouble());
    if (!std::isfinite(value)) {
      return BuiltinResult::Fail;
    }
    return unifyFloat(engine, args[0], value) ? BuiltinResult::Continue
                                              : BuiltinResult::Fail;
  }
  if (x && y) {
    return forward(x->asDouble()) == y->asDouble() ? BuiltinResult::Continue
                                                   : BuiltinResult::Fail;
  }
  badArguments(name);
}

}  // namespace

BuiltinResult builtinSin(Engine& engine, std::span<const Term> args) {
  return unaryFloat(engine, args, [](double v) { return std::sin(v); },
                    [](double v) { return std::asin(v); }, "SIN");
}

BuiltinResult builtinCos(Engine& engine, std::span<const Term> args) {
  return unaryFloat(engine, args, [](double v) { return std::cos(v); },
                    [](double v) { return std::acos(v); }, "COS");
}

BuiltinResult builtinTan(Engine& engine, std::span<const Term> args) {
  return unaryFloat(engine, args, [](double v) { return std::tan(v); },
                    [](double v) { return std::atan(v); }, "TAN");
}

BuiltinResult builtinExp(Engine& engine, std::span<const Term> args) {
  return unaryFloat(engine, args, [](double v) { return std::exp(v); },
                    [](double v) { return std::log(v); }, "EXP");
}

// ---------------------------------------------------------------------------
// Conversions
// ---------------------------------------------------------------------------

BuiltinResult builtinToInt(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (!value) {
    if (isUnbound(engine, args[0])) {
      engine.raise(ErrorCode::TypeConversion);
    }
    engine.raise(ErrorCode::TypeConversion);
  }
  if (!value->is_float) {
    return BuiltinResult::Continue;
  }
  const double truncated = std::trunc(value->real);
  return truncated == value->real ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinToFloat(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (!value) {
    engine.raise(ErrorCode::TypeConversion);
  }
  return BuiltinResult::Continue;
}

BuiltinResult builtinRandom(Engine& engine, std::span<const Term> args) {
  if (args.size() == 1) {
    const auto value = asNumeric(engine, args[0]);
    if (value && !value->is_float) {
      randomEngine().seed(static_cast<std::uint64_t>(value->integer.toInt64()));
      return BuiltinResult::Continue;
    }
    if (!value && isUnbound(engine, args[0])) {
      std::uniform_int_distribution<std::int32_t> distribution(
          std::numeric_limits<std::int32_t>::min(), std::numeric_limits<std::int32_t>::max());
      return unifyInteger(engine, args[0], BigInt(distribution(randomEngine())))
                 ? BuiltinResult::Continue
                 : BuiltinResult::Fail;
    }
    badArguments("СЛУЧ");
  }
  const auto low = detail::asInteger(engine, args[1]);
  const auto high = detail::asInteger(engine, args[2]);
  if (!isUnbound(engine, args[0]) || !low || !high) {
    badArguments("СЛУЧ");
  }
  if (*low > *high) {
    engine.raise(ErrorCode::TypeMismatch, "СЛУЧ: АРГ2 > АРГ3");
  }
  std::uniform_int_distribution<long long> distribution(low->toInt64(), high->toInt64());
  return unifyInteger(engine, args[0], BigInt(distribution(randomEngine())))
             ? BuiltinResult::Continue
             : BuiltinResult::Fail;
}

BuiltinResult builtinConvertIntFloat(Engine& engine, std::span<const Term> args) {
  const auto a = asNumeric(engine, args[0]);
  const auto b = asNumeric(engine, args[1]);
  if (a && !b && isUnbound(engine, args[1])) {
    if (a->is_float) {
      return unifyInteger(engine, args[1], a->asInteger()) ? BuiltinResult::Continue
                                                           : BuiltinResult::Fail;
    }
    return unifyFloat(engine, args[1], a->integer.toDouble()) ? BuiltinResult::Continue
                                                              : BuiltinResult::Fail;
  }
  if (!a && isUnbound(engine, args[0]) && b) {
    if (b->is_float) {
      return unifyInteger(engine, args[0], b->asInteger()) ? BuiltinResult::Continue
                                                           : BuiltinResult::Fail;
    }
    return unifyFloat(engine, args[0], b->integer.toDouble()) ? BuiltinResult::Continue
                                                              : BuiltinResult::Fail;
  }
  if (a && b) {
    if (a->is_float && b->is_float) {
      return a->real == b->real ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    if (!a->is_float && !b->is_float) {
      return a->integer == b->integer ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    const ArithValue& integer = a->is_float ? *b : *a;
    const ArithValue& real = a->is_float ? *a : *b;
    return integer.integer == BigInt::fromDouble(real.real) ? BuiltinResult::Continue
                                                            : BuiltinResult::Fail;
  }
  badArguments("ЦЕЛВЕЩ");
}

BuiltinResult builtinStringToInt(Engine& engine, std::span<const Term> args) {
  const auto text = asText(engine, args[0]);
  const auto number = asNumeric(engine, args[1]);
  if (text && !number && isUnbound(engine, args[1])) {
    auto parsed = BigInt::tryParse(*text);
    if (!parsed) {
      return BuiltinResult::Fail;
    }
    return unifyInteger(engine, args[1], *parsed) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
  }
  if (text && number) {
    auto parsed = BigInt::tryParse(*text);
    if (!parsed) {
      return BuiltinResult::Fail;
    }
    return *parsed == number->asInteger() ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (!text && isUnbound(engine, args[0]) && number) {
    const std::string rendered =
        number->is_float ? formatFloat(number->real) : number->integer.toString();
    return unifyText(engine, args[0], rendered) ? BuiltinResult::Continue
                                                : BuiltinResult::Fail;
  }
  badArguments("СТРЦЕЛ");
}

BuiltinResult builtinStringToFloat(Engine& engine, std::span<const Term> args) {
  const auto text = asText(engine, args[0]);
  const auto number = asNumeric(engine, args[1]);
  auto parse = [](const std::string& value) -> std::optional<double> {
    try {
      std::size_t consumed = 0;
      const double result = std::stod(value, &consumed);
      if (consumed != value.size()) {
        return std::nullopt;
      }
      return result;
    } catch (const std::exception&) {
      return std::nullopt;
    }
  };
  if (text && !number && isUnbound(engine, args[1])) {
    const auto parsed = parse(*text);
    if (!parsed) {
      return BuiltinResult::Fail;
    }
    return unifyFloat(engine, args[1], *parsed) ? BuiltinResult::Continue
                                                : BuiltinResult::Fail;
  }
  if (text && number) {
    const auto parsed = parse(*text);
    if (!parsed) {
      return BuiltinResult::Fail;
    }
    return *parsed == number->asDouble() ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (!text && isUnbound(engine, args[0]) && number) {
    return unifyText(engine, args[0], formatFloat(number->asDouble()))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }
  badArguments("СТРВЕЩ");
}

BuiltinResult builtinStringToList(Engine& engine, std::span<const Term> args) {
  const auto text = asText(engine, args[0]);
  if (text) {
    std::vector<Term> codes;
    for (CodePoint code_point : utf8Decode(*text)) {
      codes.push_back(makeInt(static_cast<std::int64_t>(code_point)));
    }
    const Term list = makeListFromVector(codes);
    return engine.unify(args[1], list) ? BuiltinResult::Continue : BuiltinResult::Fail;
  }
  if (isUnbound(engine, args[0])) {
    const Term resolved = engine.bindings().deref(args[1]);
    if (!isList(resolved)) {
      badArguments("СТРСПИС");
    }
    std::vector<Term> elements;
    Term tail;
    listToVectorWithTail(resolved, elements, tail);
    if (!isNil(tail)) {
      engine.raise(ErrorCode::WrongList);
    }
    std::vector<CodePoint> code_points;
    code_points.reserve(elements.size());
    for (const Term& element : elements) {
      const auto value = detail::asInteger(engine, element);
      if (!value) {
        badArguments("СТРСПИС");
      }
      long long code = value->toInt64();
      code %= 0x110000;
      if (code < 0) {
        code += 0x110000;
      }
      code_points.push_back(static_cast<CodePoint>(code));
    }
    return unifyText(engine, args[0], utf8FromCodePoints(code_points))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }
  badArguments("СТРСПИС");
}

// ---------------------------------------------------------------------------
// Arithmetic expression evaluation
// ---------------------------------------------------------------------------

namespace {

ArithValue evaluateNode(Engine& engine, const Term& node);

ArithValue evaluateBinary(Engine& engine, std::string_view op, const Term& left,
                          const Term& right) {
  const ArithValue a = evaluateNode(engine, left);
  const ArithValue b = evaluateNode(engine, right);
  const bool floatResult = a.is_float || b.is_float;
  if (op == "mod" || op == "div") {
    if (floatResult) {
      engine.raise(op == "mod" ? ErrorCode::ArithmeticType
                               : ErrorCode::ArithmeticType);
    }
    if (b.integer.isZero()) {
      engine.raise(ErrorCode::DivisionByZero);
    }
    return op == "mod" ? ArithValue::ofInteger(a.integer % b.integer)
                       : ArithValue::ofInteger(a.integer / b.integer);
  }
  if (op == "/") {
    if (floatResult) {
      if (b.asDouble() == 0.0) {
        engine.raise(ErrorCode::DivisionByZero);
      }
      return ArithValue::ofFloat(a.asDouble() / b.asDouble());
    }
    if (b.integer.isZero()) {
      engine.raise(ErrorCode::DivisionByZero);
    }
    return ArithValue::ofInteger(a.integer / b.integer);
  }
  if (op == "+") {
    return floatResult ? ArithValue::ofFloat(a.asDouble() + b.asDouble())
                       : ArithValue::ofInteger(a.integer + b.integer);
  }
  if (op == "-") {
    return floatResult ? ArithValue::ofFloat(a.asDouble() - b.asDouble())
                       : ArithValue::ofInteger(a.integer - b.integer);
  }
  if (op == "*") {
    return floatResult ? ArithValue::ofFloat(a.asDouble() * b.asDouble())
                       : ArithValue::ofInteger(a.integer * b.integer);
  }
  engine.raise(ErrorCode::InvalidArithmeticExpression);
}

ArithValue evaluateNode(Engine& engine, const Term& node) {
  const Term resolved = engine.bindings().deref(node);
  if (isExpressionWrapper(resolved)) {
    return evaluateNode(engine, resolved.compound->args[0]);
  }
  switch (resolved.kind) {
    case TermKind::Int:
      return ArithValue::ofInteger(resolved.integer);
    case TermKind::Float:
      return ArithValue::ofFloat(resolved.real);
    case TermKind::Compound: {
      if (resolved.compound == nullptr) {
        engine.raise(ErrorCode::InvalidArithmeticExpression);
      }
      const std::string& name = resolved.compound->name;
      const auto& arguments = resolved.compound->args;
      if (name == "neg" && arguments.size() == 1) {
        const ArithValue value = evaluateNode(engine, arguments[0]);
        return value.is_float ? ArithValue::ofFloat(-value.real)
                              : ArithValue::ofInteger(-value.integer);
      }
      if (arguments.size() == 2) {
        return evaluateBinary(engine, name, arguments[0], arguments[1]);
      }
      engine.raise(ErrorCode::InvalidArithmeticExpression);
    }
    default:
      engine.raise(ErrorCode::InvalidArithmeticExpression,
                   "Нечисловой операнд арифметического выражения");
  }
}

}  // namespace

ArithValue Engine::evaluateArithmetic(const Term& wrapper) {
  if (!isExpressionWrapper(wrapper)) {
    raise(ErrorCode::InvalidArithmeticExpression);
  }
  return evaluateNode(*this, wrapper.compound->args[0]);
}

Term Engine::evaluateToTerm(const Term& wrapper) {
  const ArithValue value = evaluateArithmetic(wrapper);
  return value.is_float ? makeFloat(value.real) : makeInt(value.integer);
}

}  // namespace prologd
