#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>

#include "builtins_internal.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

using detail::ArgKind;
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
    badArgument(engine, args[0], name, 1, ArgKind::Text);
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
    badArgument(engine, args[1], name, 2, ArgKind::Integer);
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

/// One of the three counts of `sub_string/5`: free, or a whole number from zero.
struct SubStringCount {
  bool bound = false;
  std::size_t value = 0;
};

/// A count of `sub_string/5`.  A negative one is the case ISO calls a *domain
/// error*: the goal is not «not satisfied», the number is nonsense — so it is
/// raised, the way an out-of-range colour is (`builtins_graphics.cpp`), and not
/// failed.  A count that is not a number at all is the usual type error.
SubStringCount subStringCount(Engine& engine, std::span<const Term> args, std::size_t index,
                              const char* name) {
  SubStringCount count;
  const Term& term = args[index];
  if (isUnbound(engine, term)) {
    return count;
  }
  const auto value = asInteger(engine, term);
  if (!value) {
    badArgument(engine, term, "sub_string", index + 1, ArgKind::Integer);
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
    badArgument(engine, args[0], "ДЛИНА", 1, ArgKind::Text);
  }
  const auto length = static_cast<std::int64_t>(utf8Length(*text));
  if (isUnbound(engine, args[1])) {
    return unifyInteger(engine, args[1], BigInt(length)) ? BuiltinResult::Continue
                                                         : BuiltinResult::Fail;
  }
  const auto expected = positionOf(engine, args[1]);
  if (!expected) {
    badArgument(engine, args[1], "ДЛИНА", 2, ArgKind::Integer);
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
    badArguments(engine, args, "СЦЕП", ArgKind::Text);
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
  badArguments(engine, args, "СЦЕП", ArgKind::Text);
}

BuiltinResult builtinCopy(Engine& engine, std::span<const Term> args) {
  const Term& source_arg = args[0];
  const Term& position_arg = args[1];
  const Term& length_arg = args[2];
  const Term& substring_arg = args[3];

  const auto source = asText(engine, source_arg);
  if (!source) {
    badArgument(engine, source_arg, "КОПИЯ", 1, ArgKind::Text);
  }
  const bool have_position = !isUnbound(engine, position_arg);
  const bool have_length = !isUnbound(engine, length_arg);
  const auto substring = asText(engine, substring_arg);
  const std::size_t total = utf8Length(*source);

  // str int int var|str
  if (have_position && have_length) {
    const auto position = positionOf(engine, position_arg);
    const auto length = positionOf(engine, length_arg);
    if (!position) {
      badArgument(engine, position_arg, "КОПИЯ", 2, ArgKind::Integer);
    }
    if (!length) {
      badArgument(engine, length_arg, "КОПИЯ", 3, ArgKind::Integer);
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
    badArgument(engine, substring_arg, "КОПИЯ", 4, ArgKind::Text);
  }

  // str int var str
  if (have_position && !have_length && substring) {
    const auto position = positionOf(engine, position_arg);
    if (!position) {
      badArgument(engine, position_arg, "КОПИЯ", 2, ArgKind::Integer);
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
      badArgument(engine, length_arg, "КОПИЯ", 3, ArgKind::Integer);
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

  badArguments(engine, "КОПИЯ");
}

namespace {

/// The walk over the answers of `sub_string/5`, in ISO's order: «До» from zero
/// up and, at each position, «Длина» from zero up — the order `КОПИЯ/4` gives
/// when its position and length are both free, so the first answer of the two is
/// the same.
///
/// Why a walk and not a table: a string of n characters has n(n+1)/2 substrings
/// and their total length is n(n+1)(n+2)/6, so pieces made in advance would cost
/// a megabyte for a phrase of a hundred characters and a gigabyte for a page.
/// A bound count narrows the walk instead of filtering it (`lengthsAt` keeps the
/// intersection of what the three counts allow), so a shape that has one answer
/// still costs one answer.
struct SubStringWalk {
  SubStringWalk(std::string text, const SubStringCount& beforeCount,
                const SubStringCount& lengthCount, const SubStringCount& afterCount,
                std::optional<std::string> wantedPiece, const std::array<Term, 4>& arguments)
      : source(std::move(text)),
        piece(std::move(wantedPiece)),
        before(beforeCount),
        length(lengthCount),
        after(afterCount),
        targets(arguments),
        total(utf8Length(source)),
        piece_length(this->piece ? utf8Length(*this->piece) : 0) {
    start = before.bound ? before.value : 0;
    start_to = before.bound ? before.value : total;
    if (after.bound) {
      if (after.value > total) {
        start_to = 0;
        start = 1;  // «После» alone is longer than the string: nothing fits
      } else {
        start_to = std::min(start_to, total - after.value);
      }
    }
    start_to = std::min(start_to, total);
  }

  /// False when no answer can exist — a count that is out of range on its own.
  [[nodiscard]] bool walking() const { return start <= start_to; }

  [[nodiscard]] std::optional<BuiltinAnswer> next() {
    while (walking()) {
      const auto [from, to] = lengthsAt(start);
      if (count < from) {
        count = from;
      }
      while (count <= to) {
        const std::size_t taken = count++;
        if (!piece || utf8Substr(source, start, taken) == *piece) {
          return answerAt(start, taken);
        }
      }
      ++start;
      count = 0;
    }
    return std::nullopt;
  }

 private:
  /// The lengths worth trying at `at`: what the three counts allow, intersected
  /// with the room the string has left.  `at` never exceeds `total` here — the
  /// position was clamped — so `total - at - after.value` cannot go below zero.
  [[nodiscard]] std::pair<std::size_t, std::size_t> lengthsAt(std::size_t at) const {
    std::size_t from = 0;
    std::size_t to = total - at;
    if (length.bound) {
      from = std::max(from, length.value);
      to = std::min(to, length.value);
    }
    if (after.bound) {
      const std::size_t fixed = total - at - after.value;
      from = std::max(from, fixed);
      to = std::min(to, fixed);
    }
    if (piece) {
      from = std::max(from, piece_length);
      to = std::min(to, piece_length);
    }
    return {from, to};
  }

  [[nodiscard]] BuiltinAnswer answerAt(std::size_t at, std::size_t taken) const {
    const std::size_t rest = total - at - taken;
    BuiltinAnswer answer;
    answer.unify = {{targets[0], makeInt(static_cast<std::int64_t>(at))},
                    {targets[1], makeInt(static_cast<std::int64_t>(taken))},
                    {targets[2], makeInt(static_cast<std::int64_t>(rest))},
                    {targets[3], makeString(utf8Substr(source, at, taken))}};
    return answer;
  }

  std::string source;
  std::optional<std::string> piece;
  SubStringCount before;
  SubStringCount length;
  SubStringCount after;
  std::array<Term, 4> targets;  // «До», «Длина», «После», «Подстрока»
  std::size_t total = 0;
  std::size_t piece_length = 0;
  std::size_t start = 0;     // the position being tried
  std::size_t start_to = 0;  // the last one worth trying
  std::size_t count = 0;     // the length being tried at `start`
};

}  // namespace

/// `sub_string(Стр, До, Длина, После, Подстрока)` — the ISO shape of `КОПИЯ/4`
/// (task_84; the Russian name `ПОДСТРОКА` came later): positions and lengths
/// count from **zero**, the three numbers are «сколько до, сколько взять, сколько
/// осталось», and the piece is a string.
///
/// Every combination the counts allow is an answer, handed out on backtracking —
/// that is what ISO's `sub_string/5` does, and the difference from the first
/// version of this built-in (one answer, the first of the walk) is gone.  The
/// answers are produced one at a time rather than collected (`SubStringWalk`).
BuiltinResult builtinSubString(Engine& engine, std::span<const Term> args) {
  auto source = asText(engine, args[0]);
  if (!source) {
    badArgument(engine, args[0], "sub_string", 1, ArgKind::Text);
  }
  const SubStringCount before = subStringCount(engine, args, 1, "До");
  const SubStringCount length = subStringCount(engine, args, 2, "Длина");
  const SubStringCount after = subStringCount(engine, args, 3, "После");

  std::optional<std::string> piece;
  if (!isUnbound(engine, args[4])) {
    piece = asText(engine, args[4]);
    if (!piece) {
      badArgument(engine, args[4], "sub_string", 5, ArgKind::Text);
    }
  }

  auto walk = std::make_shared<SubStringWalk>(
      std::move(*source), before, length, after, std::move(piece),
      std::array<Term, 4>{args[1], args[2], args[3], args[4]});
  if (!walk->walking()) {
    return BuiltinResult::Fail;
  }
  BuiltinChoice choice;
  choice.produce = [walk](Engine&) { return walk->next(); };
  engine.setBuiltinChoice(std::move(choice));
  return BuiltinResult::Yield;
}

}  // namespace prologd
