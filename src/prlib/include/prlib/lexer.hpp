#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <utility>
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

/// True when `name` must lex as a predicate name rather than a variable: a
/// current reserved built-in or a retired spelling of one (which the checks
/// then report with a suggestion).
bool isReservedBuiltinName(std::string_view name);

/// How a name is read (task_67, merged in task_77): two modes, and the file (or
/// the run) says which one it wants.
///
/// `Iso` is what the port ships: only a lowercase name is an atom, an upper-case
/// one is a variable, and `'` quotes an atom.  `Old` is the old Пролог-Д: **any**
/// single letter is a variable, a bare capitalised name is a string constant, and
/// a long variable name ends with an apostrophe (`Сумма'`).
///
/// The old dialect used to be *two* modes — `1` without apostrophe names, `2`
/// with them — until task_77.  The original reads `число'` in a file that declares
/// nothing, so `2` was never a dialect of its own: it was the honest half of `1`.
/// The two are one mode now, and `2` stays a *spelling* of `1` wherever a number
/// names a mode (the marker, `--vars`, the protocol's `vars`, a stored setting),
/// so a file, a script or an ini that says it keeps working.
///
/// A name is classified while the text is read, so the mode belongs to the *file*
/// and to the run — never to a goal inside the program.
enum class VariableMode : std::uint8_t {
  Iso = 0,
  Old = 1,
};

/// The mode a number names: `0`, `1`, and `2` as a spelling of `1` (task_77).
/// `std::nullopt` for every other number; what to do about it is the caller's
/// business — the CLI has already refused it, the protocol raises, and the marker
/// means «the file says nothing».
std::optional<VariableMode> variableModeFromNumber(int number);

/// The `:- ИМЕНА(0|1|2).` marker of a file's first line (task_67), together with
/// how many bytes of the source the marker line takes up — that is, everything up
/// to its newline, which itself stays in place so that the line numbers of the
/// text below do not move.
///
/// The mode of a file has to be known *before* it is lexed, because a name is
/// classified as it is read, so the first line is read here on its own, in the ISO
/// rules the marker is written in.  `std::nullopt` means the first line is not the
/// marker — a line carrying anything else as well, or an argument outside `0`…`2`,
/// is not one — and the file then keeps the mode of the run, while the directive
/// itself reaches the built-in, which says where the marker belongs.
///
/// Both readers of a file use this: the loader (`Engine::parseSource`) and the
/// formatter (`formatSource`), so the rule lives in one place.
std::optional<std::pair<VariableMode, std::size_t>> readVariableMarker(std::string_view source);

/// What the lexer needs to know about the file rather than about the language.
struct LexerOptions {
  /// How names are read; `Iso` unless the file (or the run) says otherwise.
  VariableMode variables = VariableMode::Iso;
};

/// UTF-8 aware lexer for the PrologD surface language.
class Lexer {
 public:
  Lexer(std::string_view source, std::string file_name, LexerOptions options = {});

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
  LexerOptions options_;
  std::size_t offset_ = 0;
  std::uint32_t line_ = 1;
  std::uint32_t column_ = 1;
  bool reported_error_ = false;
};

}  // namespace prologd
