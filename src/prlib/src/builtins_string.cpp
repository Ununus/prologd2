#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>

#include "builtins_internal.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

using detail::asInteger;
using detail::asText;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyInteger;
using detail::unifyText;

namespace {

std::optional<long long> positionOf(Engine& engine, const Term& term) {
  const auto value = asInteger(engine, term);
  if (!value) {
    return std::nullopt;
  }
  return value->toInt64();
}

/// Code-point index (0-based) of a byte offset.
std::size_t codePointIndexAt(std::string_view text, std::size_t byte_offset) {
  std::size_t index = 0;
  std::size_t offset = 0;
  while (offset < byte_offset && offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    if (decoded.length == 0) {
      break;
    }
    offset += decoded.length;
    ++index;
  }
  return index;
}

BuiltinResult classifyCharacter(Engine& engine, std::span<const Term> args,
                                bool (*classify)(CodePoint), std::string_view name) {
  const auto text = asText(engine, args[0]);
  if (!text) {
    badArguments(name);
  }
  const std::size_t length = utf8Length(*text);
  if (isUnbound(engine, args[1])) {
    for (std::size_t i = 0; i < length; ++i) {
      const DecodeResult decoded = decodeCodePoint(*text, utf8ByteOffset(*text, i));
      if (decoded.valid && classify(decoded.code_point)) {
        return unifyInteger(engine, args[1], BigInt(static_cast<std::int64_t>(i + 1)))
                   ? BuiltinResult::Continue
                   : BuiltinResult::Fail;
      }
    }
    return BuiltinResult::Fail;
  }
  const auto position = positionOf(engine, args[1]);
  if (!position) {
    badArguments(name);
  }
  if (*position < 1 || static_cast<std::size_t>(*position) > length) {
    return BuiltinResult::Fail;
  }
  const DecodeResult decoded =
      decodeCodePoint(*text, utf8ByteOffset(*text, static_cast<std::size_t>(*position - 1)));
  if (!decoded.valid || !classify(decoded.code_point)) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

bool isLetterCodePoint(CodePoint code_point) { return isLetter(code_point); }
bool isDigitCodePoint(CodePoint code_point) { return isAsciiDigit(code_point); }

}  // namespace

BuiltinResult builtinIsLetter(Engine& engine, std::span<const Term> args) {
  return classifyCharacter(engine, args, isLetterCodePoint, "БУКВА");
}

BuiltinResult builtinIsDigit(Engine& engine, std::span<const Term> args) {
  return classifyCharacter(engine, args, isDigitCodePoint, "ЦИФРА");
}

BuiltinResult builtinStringLength(Engine& engine, std::span<const Term> args) {
  const auto text = asText(engine, args[0]);
  if (!text) {
    badArguments("ДЛИНА");
  }
  const auto length = static_cast<std::int64_t>(utf8Length(*text));
  if (isUnbound(engine, args[1])) {
    return unifyInteger(engine, args[1], BigInt(length)) ? BuiltinResult::Continue
                                                         : BuiltinResult::Fail;
  }
  const auto expected = positionOf(engine, args[1]);
  if (!expected) {
    badArguments("ДЛИНА");
  }
  return *expected == length ? BuiltinResult::Continue : BuiltinResult::Fail;
}

BuiltinResult builtinConcat(Engine& engine, std::span<const Term> args) {
  const auto first = asText(engine, args[0]);
  const auto second = asText(engine, args[1]);
  const auto third = asText(engine, args[2]);
  if (first && second) {
    const std::string combined = *first + *second;
    if (third) {
      return combined == *third ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    if (isUnbound(engine, args[2])) {
      return unifyText(engine, args[2], combined) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
    }
    badArguments("СЦЕП");
  }
  if (first && third && isUnbound(engine, args[1])) {
    // C = A ++ B with A and C known: C must start with A.
    if (third->size() >= first->size() && third->compare(0, first->size(), *first) == 0) {
      const std::string remainder = third->substr(first->size());
      return unifyText(engine, args[1], remainder) ? BuiltinResult::Continue
                                                   : BuiltinResult::Fail;
    }
    return BuiltinResult::Fail;
  }
  if (second && third && isUnbound(engine, args[0])) {
    // C = A ++ B with B and C known: C must end with B.
    if (third->size() >= second->size() &&
        third->compare(third->size() - second->size(), second->size(), *second) == 0) {
      const std::string remainder = third->substr(0, third->size() - second->size());
      return unifyText(engine, args[0], remainder) ? BuiltinResult::Continue
                                                   : BuiltinResult::Fail;
    }
    return BuiltinResult::Fail;
  }
  badArguments("СЦЕП");
}

BuiltinResult builtinCopy(Engine& engine, std::span<const Term> args) {
  const Term& source_arg = args[0];
  const Term& position_arg = args[1];
  const Term& length_arg = args[2];
  const Term& substring_arg = args[3];

  const auto source = asText(engine, source_arg);
  if (!source) {
    badArguments("КОПИЯ");
  }
  const bool have_position = !isUnbound(engine, position_arg);
  const bool have_length = !isUnbound(engine, length_arg);
  const auto substring = asText(engine, substring_arg);
  const std::size_t total = utf8Length(*source);

  // str int int var|str
  if (have_position && have_length) {
    const auto position = positionOf(engine, position_arg);
    const auto length = positionOf(engine, length_arg);
    if (!position || !length) {
      badArguments("КОПИЯ");
    }
    long long count = *length;
    if (count < 0) {
      count = -count;
    }
    if (*position < 1 ||
        static_cast<std::size_t>(*position - 1) + static_cast<std::size_t>(count) > total) {
      return BuiltinResult::Fail;
    }
    const std::string piece =
        utf8Substr(*source, static_cast<std::size_t>(*position - 1),
                   static_cast<std::size_t>(count));
    if (substring) {
      return piece == *substring ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    if (isUnbound(engine, substring_arg)) {
      return unifyText(engine, substring_arg, piece) ? BuiltinResult::Continue
                                                     : BuiltinResult::Fail;
    }
    badArguments("КОПИЯ");
  }

  // str int var str
  if (have_position && !have_length && substring) {
    const auto position = positionOf(engine, position_arg);
    if (!position) {
      badArguments("КОПИЯ");
    }
    const std::size_t piece_length = utf8Length(*substring);
    if (*position >= 1 &&
        static_cast<std::size_t>(*position - 1) + piece_length <= total) {
      const std::string piece =
          utf8Substr(*source, static_cast<std::size_t>(*position - 1), piece_length);
      if (piece == *substring) {
        return unifyInteger(engine, length_arg, BigInt(static_cast<std::int64_t>(piece_length)))
                   ? BuiltinResult::Continue
                   : BuiltinResult::Fail;
      }
    }
    return BuiltinResult::Fail;
  }

  // str var int str
  if (!have_position && have_length && substring) {
    const auto length = positionOf(engine, length_arg);
    if (!length) {
      badArguments("КОПИЯ");
    }
    long long count = *length;
    const bool from_right = count < 0;
    if (count < 0) {
      count = -count;
    }
    const std::size_t piece_length = utf8Length(*substring);
    if (static_cast<std::size_t>(count) != piece_length) {
      return BuiltinResult::Fail;
    }
    if (piece_length == 0) {
      return unifyInteger(engine, position_arg, BigInt(1)) ? BuiltinResult::Continue
                                                           : BuiltinResult::Fail;
    }
    if (piece_length > total) {
      return BuiltinResult::Fail;
    }
    const std::size_t byte_index =
        from_right ? source->rfind(*substring) : source->find(*substring);
    if (byte_index == std::string::npos) {
      return BuiltinResult::Fail;
    }
    const std::size_t code_index = codePointIndexAt(*source, byte_index);
    return unifyInteger(engine, position_arg, BigInt(static_cast<std::int64_t>(code_index + 1)))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }

  // str var var str
  if (!have_position && !have_length && substring) {
    const std::size_t piece_length = utf8Length(*substring);
    if (piece_length == 0) {
      const bool ok = unifyInteger(engine, position_arg, BigInt(1)) &&
                      unifyInteger(engine, length_arg, BigInt(0));
      return ok ? BuiltinResult::Continue : BuiltinResult::Fail;
    }
    const std::size_t byte_index = source->find(*substring);
    if (byte_index == std::string::npos) {
      return BuiltinResult::Fail;
    }
    const std::size_t code_index = codePointIndexAt(*source, byte_index);
    const bool ok =
        unifyInteger(engine, position_arg, BigInt(static_cast<std::int64_t>(code_index + 1))) &&
        unifyInteger(engine, length_arg, BigInt(static_cast<std::int64_t>(piece_length)));
    return ok ? BuiltinResult::Continue : BuiltinResult::Fail;
  }

  badArguments("КОПИЯ");
}

}  // namespace prologd
