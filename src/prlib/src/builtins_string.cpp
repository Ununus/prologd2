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

/// Where `piece` occurs first in `source`, as a code-point index.
std::optional<std::size_t> firstOccurrence(std::string_view source, std::string_view piece) {
  const std::size_t byte_index = source.find(piece);
  if (byte_index == std::string_view::npos) {
    return std::nullopt;
  }
  return codePointIndexAt(source, byte_index);
}

/// One of the three counts of `sub_string/5`: free, or a whole number from zero.
struct SubStringCount {
  bool bound = false;
  std::size_t value = 0;
};

/// A count of `sub_string/5`.  A negative one is the case ISO calls a *domain
/// error*: the goal is not «not satisfied», the number is nonsense — so it is
/// raised, the way an out-of-range colour is (`builtins_graphics.cpp`), and not
/// failed.  A count that is not a number at all is the usual type error.
SubStringCount subStringCount(Engine& engine, const Term& term, const char* name) {
  SubStringCount count;
  if (isUnbound(engine, term)) {
    return count;
  }
  const auto value = asInteger(engine, term);
  if (!value) {
    badArguments("sub_string");
  }
  const long long number = value->toInt64();
  if (number < 0) {
    engine.raise(ErrorCode::TypeMismatch,
                 std::string("sub_string: ") + name + " меньше нуля (" +
                     std::to_string(number) + ")");
  }
  count.bound = true;
  count.value = static_cast<std::size_t>(number);
  return count;
}

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

/// `sub_string(Стр, До, Длина, После, Подстрока)` — the ISO shape of `КОПИЯ/4`
/// (task_84): positions and lengths count from **zero**, the three numbers are
/// «сколько до, сколько взять, сколько осталось», and the piece is a string.
///
/// One answer, and not a walk over all of them: ISO leaves *which* of the three
/// numbers is free to the caller and enumerates on backtracking when the piece is
/// known but its place is not, while a built-in here answers once
/// (`BuiltinResult` is one outcome, and a built-in cannot hand a choice point
/// back to the solver).  What it answers is the *first* solution in ISO's own
/// order — the earliest position, and the shortest piece at that position — which
/// is also what `КОПИЯ/4` does when its position and length are free.  The
/// difference is written down in §7.4 of the manual.
BuiltinResult builtinSubString(Engine& engine, std::span<const Term> args) {
  const auto source = asText(engine, args[0]);
  if (!source) {
    badArguments("sub_string");
  }
  const std::size_t total = utf8Length(*source);
  const SubStringCount before = subStringCount(engine, args[1], "До");
  const SubStringCount length = subStringCount(engine, args[2], "Длина");
  const SubStringCount after = subStringCount(engine, args[3], "После");

  std::optional<std::string> wanted;
  if (!isUnbound(engine, args[4])) {
    wanted = asText(engine, args[4]);
    if (!wanted) {
      badArguments("sub_string");
    }
  }

  std::size_t start = 0;
  std::size_t count = 0;
  if (wanted) {
    // A known piece: the bound counts say where to look for it, and with neither
    // a position nor a tail given, its first occurrence is the answer.
    count = utf8Length(*wanted);
    if (before.bound) {
      start = before.value;
    } else if (after.bound) {
      if (after.value + count > total) {
        return BuiltinResult::Fail;
      }
      start = total - after.value - count;
    } else {
      const auto found = firstOccurrence(*source, *wanted);
      if (!found) {
        return BuiltinResult::Fail;
      }
      start = *found;
    }
  } else {
    // No piece to look for: the counts themselves say what to take out, and a
    // free one follows from the two that are known — the sum of the three is the
    // length of the string.  So the free counts are only chosen where the
    // arithmetic leaves a choice, and then ISO's first solution is taken: the
    // earliest position, and at that position an empty piece.
    if (before.bound && after.bound) {
      if (before.value + after.value > total) {
        return BuiltinResult::Fail;
      }
      start = before.value;
      count = total - before.value - after.value;
    } else if (length.bound) {
      count = length.value;
      if (count > total) {
        return BuiltinResult::Fail;
      }
      if (before.bound) {
        start = before.value;
      } else if (after.bound) {
        if (after.value + count > total) {
          return BuiltinResult::Fail;
        }
        start = total - after.value - count;
      }
    } else if (before.bound) {
      start = before.value;
    } else if (after.bound) {
      if (after.value > total) {
        return BuiltinResult::Fail;
      }
      count = total - after.value;
    }
  }

  // Everything the arguments asked for has to hold of the one piece found.
  if (start + count > total) {
    return BuiltinResult::Fail;
  }
  if ((before.bound && before.value != start) || (length.bound && length.value != count) ||
      (after.bound && total - start - count != after.value)) {
    return BuiltinResult::Fail;
  }
  if (wanted && utf8Substr(*source, start, count) != *wanted) {
    return BuiltinResult::Fail;
  }

  if (!before.bound &&
      !unifyInteger(engine, args[1], BigInt(static_cast<std::int64_t>(start)))) {
    return BuiltinResult::Fail;
  }
  if (!length.bound &&
      !unifyInteger(engine, args[2], BigInt(static_cast<std::int64_t>(count)))) {
    return BuiltinResult::Fail;
  }
  if (!after.bound &&
      !unifyInteger(engine, args[3],
                    BigInt(static_cast<std::int64_t>(total - start - count)))) {
    return BuiltinResult::Fail;
  }
  if (!wanted && !unifyText(engine, args[4], utf8Substr(*source, start, count))) {
    return BuiltinResult::Fail;
  }
  return BuiltinResult::Continue;
}

}  // namespace prologd
