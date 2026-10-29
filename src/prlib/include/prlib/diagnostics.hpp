#pragma once

#include <cstddef>
#include <exception>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/source_location.hpp"

namespace prologd {

/// Semantic category of a diagnostic.
///
/// The categories are deliberately independent of the historical PrologD
/// numeric codes: the user-facing text comes from `errorCodeText`, and the
/// category only helps programmatic handling (for example, deciding whether a
/// diagnostic came from parsing).
enum class ErrorCode {
  NoErrors = 0,

  // Lexical.
  InvalidCharacter,
  InvalidNumberLiteral,
  InvalidStringLiteral,

  // Syntax.
  InvalidDefinition,
  InvalidSentence,
  InvalidGoal,
  InvalidFunction,
  UnpairedBracket,
  WrongList,
  MissingFunctor,
  MisplacedSign,
  InvalidArithmeticExpression,
  MisplacedQuestion,
  MisplacedUnderscore,
  MisplacedCut,
  /// A variable that appears once in a clause; see `Parser::warnSingletonVariables`.
  SingletonVariable,
  /// Two variables of one clause whose names differ only in alphabet
  /// (`C` and `С`); see `Parser::warnConfusableVariables`.
  ConfusableVariable,

  // Runtime.
  TypeMismatch,
  WrongArity,
  UnknownPredicate,
  DivisionByZero,
  ArithmeticType,
  ArithmeticError,
  TypeConversion,
  StackOverflow,
  Interrupted,
  TooManySolutions,
  NotEnoughMemory,
  IoError,
  NotImplemented,
  ImportError,
  /// Two files that do not import one another define the same predicate (see
  /// `ModuleLoader`).
  ConflictingDefinitions,
  RuntimeError,
  Unknown,
};

/// Human readable Russian text for an error category.
std::string_view errorCodeText(ErrorCode code);

/// How much a diagnostic matters.
///
/// A `Warning` is advice: it never makes a load fail and never changes an exit
/// code (`DiagnosticSink::hasErrors` counts errors only).  `Note` goes with
/// another diagnostic, as a remark about it.
enum class Severity : std::uint8_t { Error, Warning, Note };

/// Stable spelling of a severity (`error`, `warning`, `note`) for text output
/// and for the JSON protocol.
[[nodiscard]] std::string_view severityText(Severity severity) noexcept;

/// A diagnostic with an optional source location.
struct PrologError {
  ErrorCode code = ErrorCode::NoErrors;
  Severity severity = Severity::Error;
  std::string message;
  SourceLocation location;
  bool isParseError = false;
};

/// Thrown for runtime errors that abort the current query.
class PrologRuntimeError : public std::exception {
 public:
  explicit PrologRuntimeError(PrologError error);

  [[nodiscard]] const PrologError& error() const noexcept { return error_; }
  [[nodiscard]] const char* what() const noexcept override { return what_.c_str(); }

 private:
  PrologError error_;
  std::string what_;
};

/// Collects parse diagnostics while allowing error recovery.
class DiagnosticSink {
 public:
  void report(PrologError error);
  [[nodiscard]] bool hasErrors() const noexcept { return errors_ > 0; }
  [[nodiscard]] std::size_t errorCount() const noexcept { return errors_; }
  [[nodiscard]] std::size_t warningCount() const noexcept { return warnings_; }
  [[nodiscard]] const std::vector<PrologError>& diagnostics() const noexcept {
    return diagnostics_;
  }
  void clear();

  /// Format one diagnostic in the usual compiler style:
  /// `file:line:column: warning: message` (the location is omitted when empty).
  [[nodiscard]] static std::string format(const PrologError& error);

 private:
  std::vector<PrologError> diagnostics_;
  std::size_t errors_ = 0;
  std::size_t warnings_ = 0;
};

}  // namespace prologd
