#include <cstdint>
#include <optional>
#include <string>

#include "builtins_internal.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

using detail::ArgKind;
using detail::asNumeric;
using detail::asText;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyFloat;
using detail::unifyInteger;
using detail::unifyText;

namespace {

/// The largest code point UTF-8 can carry.
constexpr std::int64_t kMaxCodePoint = 0x10FFFF;

/// The optional second argument of the reading predicates is a prompt: it is
/// written before the read, the way the original waited at the console.  A
/// prompt that is not text is an error, like any other wrong type.
void writePrompt(Engine& engine, std::span<const Term> args, std::string_view predicate) {
  if (args.size() < 2) {
    return;
  }
  const auto prompt = asText(engine, args[1]);
  if (!prompt) {
    badArgument(engine, args[1], predicate, 2, ArgKind::Text);
  }
  engine.io().write(*prompt);
}

}  // namespace

BuiltinResult builtinWrite(Engine& engine, std::span<const Term> args) {
  for (const Term& argument : args) {
    engine.io().write(engine.format(argument));
  }
  return BuiltinResult::Continue;
}

BuiltinResult builtinWriteLine(Engine& engine, std::span<const Term> args) {
  // `ВЫВОДПС` is the two built-ins in one goal: the arguments exactly as
  // `ВЫВОД` writes them (task_11), then one `ПС`.  `ВЫВОД` cannot fail, so the
  // line break is written unconditionally rather than through a second call —
  // no `ВЫП`-like indirection and no chance of the newline being skipped.
  for (const Term& argument : args) {
    engine.io().write(engine.format(argument));
  }
  engine.io().newline();
  return BuiltinResult::Continue;
}

BuiltinResult builtinWriteCode(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (value && !value->is_float) {
    const long long code = value->integer.toInt64();
    // A code point has to be a Unicode scalar value.  A negative one, one past
    // U+10FFFF, or a surrogate used to be encoded anyway, which wrote bytes that
    // are not UTF-8 at all — and the JSON protocol cannot carry those back to a
    // front-end.
    if (code < 0 || code > kMaxCodePoint || (code >= 0xD800 && code <= 0xDFFF)) {
      badArgument(engine, args[0], "ВВКОД", 1, ArgKind::Integer, "код символа от 0 до 1114111");
    }
    engine.io().write(utf8Encode(static_cast<CodePoint>(code)));
    return BuiltinResult::Continue;
  }
  if (!value && isUnbound(engine, args[0])) {
    const std::optional<CodePoint> code_point = engine.io().readCodePoint();
    if (!code_point) {
      return BuiltinResult::Fail;
    }
    return unifyInteger(engine, args[0], BigInt(static_cast<std::int64_t>(*code_point)))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }
  badArguments(engine, args, "ВВКОД", ArgKind::Integer);
}

BuiltinResult builtinReadInt(Engine& engine, std::span<const Term> args) {
  writePrompt(engine, args, "ВВОДЦЕЛ");
  const std::optional<std::string> token = engine.io().readToken();
  if (!token) {
    return BuiltinResult::Fail;
  }
  auto parsed = BigInt::tryParse(*token);
  if (!parsed) {
    return BuiltinResult::Fail;
  }
  if (isUnbound(engine, args[0])) {
    return unifyInteger(engine, args[0], *parsed) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
  }
  const auto current = asNumeric(engine, args[0]);
  if (!current || current->is_float) {
    badArgument(engine, args[0], "ВВОДЦЕЛ", 1, ArgKind::Integer);
  }
  return current->integer == *parsed ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadFloat(Engine& engine, std::span<const Term> args) {
  writePrompt(engine, args, "ВВОДВЕЩ");
  const std::optional<std::string> token = engine.io().readToken();
  if (!token) {
    return BuiltinResult::Fail;
  }
  double parsed = 0.0;
  try {
    std::size_t consumed = 0;
    parsed = std::stod(*token, &consumed);
    if (consumed != token->size()) {
      return BuiltinResult::Fail;
    }
  } catch (const std::exception&) {
    return BuiltinResult::Fail;
  }
  if (isUnbound(engine, args[0])) {
    return unifyFloat(engine, args[0], parsed) ? BuiltinResult::Continue
                                               : BuiltinResult::Fail;
  }
  const auto current = asNumeric(engine, args[0]);
  if (!current || !current->is_float) {
    badArgument(engine, args[0], "ВВОДВЕЩ", 1, ArgKind::Number, "вещественное число");
  }
  return current->real == parsed ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadSymbol(Engine& engine, std::span<const Term> args) {
  writePrompt(engine, args, "ВВОДСИМВ");
  const std::optional<std::string> token = engine.io().readToken();
  if (!token) {
    return BuiltinResult::Fail;
  }
  if (isUnbound(engine, args[0])) {
    return unifyText(engine, args[0], *token) ? BuiltinResult::Continue
                                              : BuiltinResult::Fail;
  }
  const auto current = asText(engine, args[0]);
  if (!current) {
    badArgument(engine, args[0], "ВВОДСИМВ", 1, ArgKind::Text);
  }
  return *current == *token ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadString(Engine& engine, std::span<const Term> args) {
  writePrompt(engine, args, "ВВОДСТР");
  const std::optional<std::string> line = engine.io().readWholeLine();
  if (!line) {
    return BuiltinResult::Fail;
  }
  if (isUnbound(engine, args[0])) {
    return unifyText(engine, args[0], *line) ? BuiltinResult::Continue
                                             : BuiltinResult::Fail;
  }
  const auto current = asText(engine, args[0]);
  if (!current) {
    badArgument(engine, args[0], "ВВОДСТР", 1, ArgKind::Text);
  }
  return *current == *line ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinSee(Engine& engine, std::span<const Term> args) {
  if (isUnbound(engine, args[0])) {
    return unifyText(engine, args[0], engine.io().inputName()) ? BuiltinResult::Continue
                                                               : BuiltinResult::Fail;
  }
  const auto path = asText(engine, args[0]);
  if (!path) {
    badArgument(engine, args[0], "ЧТЕНИЕ_ИЗ", 1, ArgKind::Text);
  }
  if (!engine.io().openInput(*path)) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

BuiltinResult builtinTell(Engine& engine, std::span<const Term> args) {
  if (isUnbound(engine, args[0])) {
    return unifyText(engine, args[0], engine.io().outputName()) ? BuiltinResult::Continue
                                                                : BuiltinResult::Fail;
  }
  const auto path = asText(engine, args[0]);
  if (!path) {
    badArgument(engine, args[0], "ЗАПИСЬ_В", 1, ArgKind::Text);
  }
  if (!engine.io().openOutput(*path)) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

}  // namespace prologd
