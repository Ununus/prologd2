#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "prlib/diagnostics.hpp"
#include "prlib/source_location.hpp"

namespace prologd {

enum class TokenKind : std::uint8_t {
  EndOfFile,
  Identifier,   ///< lower-case name, or a reserved built-in name
  Variable,     ///< upper-case name, `_`, or `_Name`
  Integer,
  Float,
  String,       ///< "..."
  QuotedAtom,   ///<'...'
  Comma,
  Dot,
  Semicolon,
  Question,
  ColonDash,
  Arrow,
  IfThen,  ///< `->`, ISO's if-then (task_85)
  Bang,
  NotGoal,  ///< `\+`, ISO's spelling of `НЕ` (task_55)
  Hash,
  Equal,         ///< `=`, the sugar for `РАВНО/2` (task_52)
  Less,          ///< `<`, the sugar for `МЕНЬШЕ/2`
  Greater,       ///< `>`, the sugar for `БОЛЬШЕ/2`
  LessEqual,     ///< `=<`, the sugar for `НЕ(МЕНЬШЕ(A, B))`
  GreaterEqual,  ///< `>=`, the sugar for `НЕ(БОЛЬШЕ(A, B))`
  NotEqual,      ///< `\=`, ISO's «не унифицируется»: `НЕ(РАВНО(A, B))` (task_92)
  ArithEqual,    ///< `=:=`, arithmetic equality over `#… #` (task_92)
  ArithNotEqual, ///< `=\=`, its negation
  AtLess,          ///< `@<`, the standard order: `compare(<, A, B)` (task_90)
  AtLessEqual,     ///< `@=<`, `НЕ(compare(>, A, B))`
  AtGreater,       ///< `@>`, `compare(>, A, B)`
  AtGreaterEqual,  ///< `@>=`, `НЕ(compare(<, A, B))`
  Caret,           ///< `^`, the existential quantifier of `ВСЕРЕШ`/`МНОРЕШ` (task_91)
  Plus,
  Minus,
  Star,
  StarStar,    ///< `**`, ISO's power
  Slash,       ///< `/`, ISO's float division
  SlashSlash,  ///< `//`, ISO's integer division
  Percent,  // unused, reserved for future operators
  LParen,
  RParen,
  LBracket,
  RBracket,
  Bar,
  Unknown,
};

struct Token {
  TokenKind kind = TokenKind::EndOfFile;
  std::string text;  // decoded content for String/QuotedAtom, raw lexeme otherwise
  SourceLocation location;
};

/// Names that always denote predicates, not variables, even though they start
/// with an upper-case letter (ADR-005).
const std::unordered_set<std::string>& reservedBuiltinNames();

/// True when `name` must lex as a predicate name rather than a variable: a
/// current reserved built-in or a retired spelling of one (which the checks
/// then report with a suggestion).
bool isReservedBuiltinName(std::string_view name);

/// UTF-8 aware lexer for the PrologD surface language.
class Lexer {
 public:
  Lexer(std::string_view source, std::string file_name);

  /// Tokenise the whole input.  Lexical errors are reported to `sink` and the
  /// offending token is still emitted (as `Unknown`) so the parser can recover.
  std::vector<Token> tokenize(DiagnosticSink& sink);

  /// Tokenise without diagnostics; lexical errors appear as `Unknown` tokens.
  std::vector<Token> tokenize();

  [[nodiscard]] const std::string& fileName() const noexcept { return file_name_; }

 private:
  std::vector<Token> tokenizeImpl(DiagnosticSink* sink);
  Token makeToken(TokenKind kind, std::string text, SourceLocation location) const;
  void advanceByte(std::size_t count);
  [[nodiscard]] bool atEnd() const noexcept { return offset_ >= source_.size(); }
  [[nodiscard]] char peek(std::size_t lookahead = 0) const;
  [[nodiscard]] SourceLocation here() const;

  Token lexIdentifier(DiagnosticSink* sink);
  Token lexNumber(DiagnosticSink* sink);
  Token lexString(DiagnosticSink* sink);
  Token lexQuotedAtom(DiagnosticSink* sink);

  /// One diagnostic for a sign the dialect cannot read as it stands: `message`
  /// replaces the generic «недопустимый символ» when the sign is a known
  /// spelling from another Prolog (task_52).
  static void reportInvalidSign(DiagnosticSink* sink, const SourceLocation& location,
                                std::string_view message = {});

  std::string_view source_;
  std::string file_name_;
  std::size_t offset_ = 0;
  std::uint32_t line_ = 1;
  std::uint32_t column_ = 1;
};

}  // namespace prologd
