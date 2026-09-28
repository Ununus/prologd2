#include <cstdint>
#include <optional>
#include <string>

#include "builtins_internal.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

using detail::asNumeric;
using detail::asText;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyFloat;
using detail::unifyInteger;
using detail::unifyText;

BuiltinResult builtinWrite(Engine& engine, std::span<const Term> args) {
  for (const Term& argument : args) {
    engine.io().write(engine.format(argument));
  }
  return BuiltinResult::Continue;
}

BuiltinResult builtinWriteCode(Engine& engine, std::span<const Term> args) {
  const auto value = asNumeric(engine, args[0]);
  if (value && !value->is_float) {
    const long long code = value->integer.toInt64();
    if (code < 0) {
      badArguments("ВВКОД");
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
  badArguments("ВВКОД");
}

BuiltinResult builtinReadInt(Engine& engine, std::span<const Term> args) {
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
    badArguments("ВВОДЦЕЛ");
  }
  return current->integer == *parsed ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadFloat(Engine& engine, std::span<const Term> args) {
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
    badArguments("ВВОДВЕЩ");
  }
  return current->real == parsed ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadSymbol(Engine& engine, std::span<const Term> args) {
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
    badArguments("ВВОДСИМВ");
  }
  return *current == *token ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinReadString(Engine& engine, std::span<const Term> args) {
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
    badArguments("ВВОДСТР");
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
    badArguments("ЧТЕНИЕ_ИЗ");
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
    badArguments("ЗАПИСЬ_В");
  }
  if (!engine.io().openOutput(*path)) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

}  // namespace prologd
