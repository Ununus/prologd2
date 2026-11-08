#include "builtins_internal.hpp"

#include <cstddef>
#include <string>
#include <string_view>

namespace prologd {
namespace {

using detail::ArgKind;
using detail::asText;
using detail::badArgument;
using detail::spokenName;

/// The text of a pattern with every `{}` replaced by the next value.
///
/// A value is written the way `ВЫВОД` writes it (`Engine::format`), so a string is
/// spliced without quotes and a list as `[a,b]`: one printer for the answers and
/// for the text a program builds, and no second set of rules to keep in step.
///
/// `{{` and `}}` are the braces themselves — the rule C++ and Python teach, and
/// the only way to put a literal brace into a message.  A lone brace is an error
/// rather than a literal: a student who writes `{` meaning a place has made a
/// mistake worth naming, and printing it silently would hide the mistake.
///
/// The count is checked *after* the walk, with no value appended where none is
/// left, so that one message can name both numbers instead of whichever came
/// first.
std::string formatInto(Engine& engine, std::string_view pattern,
                       std::span<const Term> values, std::string_view name) {
  std::string text;
  text.reserve(pattern.size() + 8 * values.size());
  std::size_t places = 0;
  std::size_t start = 0;
  for (std::size_t index = 0; index < pattern.size();) {
    const char character = pattern[index];
    if (character != '{' && character != '}') {
      ++index;
      continue;
    }
    if (index + 1 < pattern.size() && pattern[index + 1] == character) {
      text.append(pattern, start, index - start);
      text += character;
      index += 2;
      start = index;
      continue;
    }
    if (character == '}') {
      engine.raise(ErrorCode::TypeMismatch,
                   std::string(name) + ": в образце «}» без пары — «}}» даёт одну скобку");
    }
    if (index + 1 >= pattern.size() || pattern[index + 1] != '}') {
      engine.raise(ErrorCode::TypeMismatch,
                   std::string(name) + ": в образце «{» без пары — «{{» даёт одну скобку");
    }
    text.append(pattern, start, index - start);
    if (places < values.size()) {
      text += engine.format(values[places]);
    }
    ++places;
    index += 2;
    start = index;
  }
  text.append(pattern, start, std::string_view::npos);
  if (places != values.size()) {
    // One message for both mistakes, and «мест — N, а значений — M» so that no
    // Russian plural agreement is needed — the same reason ADR-073 chose «нужно»
    // over «ожидался».
    engine.raise(ErrorCode::TypeMismatch,
                 std::string(name) + ": в образце мест — " + std::to_string(places) +
                     ", а значений — " + std::to_string(values.size()));
  }
  return text;
}

/// The pattern of `ФОРМАТ`/`ВЫВОДФ` as text, or a type error naming the argument.
std::string patternText(Engine& engine, std::span<const Term> args, std::size_t index,
                        std::string_view name) {
  const auto text = asText(engine, args[index]);
  if (!text) {
    badArgument(engine, args[index], name, index + 1, ArgKind::Text,
                "образец строкой или атомом");
  }
  return *text;
}

}  // namespace

/// `ФОРМАТ(Результат, Образец, Значение, ...)` (`format_string`): the text of the
/// pattern with every `{}` replaced by the next value.  The result is a *string*,
/// exactly as `СЦЕП`'s is, so it can be passed on to a file name, a message or
/// another pattern; and since a string unifies with an atom of the same text, the
/// same goal also works as a check.
BuiltinResult builtinFormat(Engine& engine, std::span<const Term> args) {
  const std::string_view name = spokenName(engine, "ФОРМАТ");
  const std::string pattern = patternText(engine, args, 1, name);
  const std::string text = formatInto(engine, pattern, args.subspan(2), name);
  return detail::unifyText(engine, args[0], text) ? BuiltinResult::Continue
                                                  : BuiltinResult::Fail;
}

/// `ВЫВОДФ(Образец, Значение, ...)` (`format`): `ФОРМАТ` straight into the output
/// stream.  The newline of a message comes from the string's own `\n` escape, as
/// everywhere else in the dialect, so no `~n` of its own is needed.
BuiltinResult builtinFormatWrite(Engine& engine, std::span<const Term> args) {
  const std::string_view name = spokenName(engine, "ВЫВОДФ");
  const std::string pattern = patternText(engine, args, 0, name);
  engine.io().write(formatInto(engine, pattern, args.subspan(1), name));
  return BuiltinResult::Continue;
}

}  // namespace prologd
