#pragma once

#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>

namespace prologd {

/// What a reserved name is.  A front-end colours a name by its kind and offers
/// only the callable ones in a completion list.
enum class KeywordKind : std::uint8_t {
  Predicate,  ///< callable: registered in the built-in dispatch table
  Operator,   ///< infix arithmetic operator: `mod`, `div`, `rem`
  /// A name that is only an arithmetic function or constant, written inside
  /// `#…#`/`is` and never called as a goal: `sign`, `pi`.  The functions that
  /// are also predicates (`abs`, `sqrt`, `sin`…) are `Predicate`.
  Function,
  Directive,  ///< statement form the loader handles: `ИМПОРТ`
};

/// Stable spelling of a kind for the CLI and the JSON protocol.
[[nodiscard]] std::string_view keywordKindName(KeywordKind kind) noexcept;

/// One reserved name.
///
/// The *lexer* owns the reserved set: a name is an atom and never a variable
/// because the lexer says so.  The arities come from the dispatch table, so a
/// new built-in cannot be forgotten in a second list.
struct KeywordInfo {
  std::string_view name;
  KeywordKind kind = KeywordKind::Predicate;
  /// Sorted; empty for operators, directives and variadic predicates.
  std::vector<std::size_t> arities;
  /// True for a predicate that accepts many arities (`ВЫВОД`).
  bool variadic = false;
};

/// Every reserved name with its arities, sorted by name (UTF-8 byte order).
[[nodiscard]] std::vector<KeywordInfo> reservedKeywords();

}  // namespace prologd
