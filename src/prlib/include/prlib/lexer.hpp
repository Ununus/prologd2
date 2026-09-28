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
  Bang,
  Hash,
  Plus,
  Minus,
  Star,
  Slash,
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

/// True when `name` is a reserved built-in predicate name.
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

  std::string_view source_;
  std::string file_name_;
  std::size_t offset_ = 0;
  std::uint32_t line_ = 1;
  std::uint32_t column_ = 1;
  bool reported_error_ = false;
};

}  // namespace prologd
