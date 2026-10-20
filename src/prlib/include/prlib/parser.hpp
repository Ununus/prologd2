#pragma once

#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "prlib/diagnostics.hpp"
#include "prlib/lexer.hpp"
#include "prlib/program.hpp"
#include "prlib/source_location.hpp"
#include "prlib/term.hpp"

namespace prologd {

/// A module import request found in the source.
struct ImportDirective {
  std::string path;
  SourceLocation location;
};

/// A parsed query (`?Goal, Goal.`) together with its named variables in the
/// order of first occurrence.
struct Query {
  std::vector<Term> goals;
  /// Where each goal starts in the source, one entry per goal.
  std::vector<SourceLocation> goalLocations;
  std::vector<std::pair<std::string, VarId>> variables;
  SourceLocation location;
  /// True for `:- Goal.` directives (executed quietly, no solution report).
  bool isDirective = false;
};

/// Position of a statement in a parsed unit, preserving source order.
struct StatementRef {
  enum class Kind { Clause, Query, Import };
  Kind kind = Kind::Clause;
  std::size_t index = 0;
};

/// Result of parsing one source unit.
struct ParsedProgram {
  std::vector<Clause> clauses;
  std::vector<Query> queries;
  std::vector<ImportDirective> imports;
  /// Source order of the statements above.
  std::vector<StatementRef> order;
  bool ok = true;
};

/// Recursive-descent parser for the PrologD surface language.
///
/// The parser never allocates `VarId`s by itself: it calls the allocator passed
/// to the constructor.  The engine supplies an allocator backed by its
/// `Bindings`; tests may supply a simple counter.
class Parser {
 public:
  using VarAllocator = std::function<VarId(std::string_view name)>;

  Parser(std::vector<Token> tokens, VarAllocator allocator, DiagnosticSink* sink);

  /// Parse the whole token stream.
  ParsedProgram parseProgram();

  /// Parse a single statement (used by the REPL).  Returns `nullopt` at EOF.
  std::optional<ParsedProgram> parseOne();

 private:
  const Token& peek(std::size_t lookahead = 0) const;
  const Token& previous() const;
  Token advance();
  bool check(TokenKind kind) const;
  bool match(TokenKind kind);
  bool atEnd() const;

  void report(ErrorCode code, const SourceLocation& location, std::string message = {});
  /// Report a bracket that was opened and never closed: the position is the
  /// opening bracket, and the message names the line it is on.
  void reportUnclosedBracket(char open, const SourceLocation& location);
  /// Report a statement that ran into end-of-file without its final dot.
  void reportMissingDot();
  /// Report a warning: advice that never fails the load.
  void warn(ErrorCode code, const SourceLocation& location, std::string message);
  /// Warn about every variable of the clause just parsed that appears exactly
  /// once — in the head that usually means a constant was meant.
  void warnSingletonVariables(bool has_body);
  /// Skip forward to (and including) the statement terminator.
  void recoverToStatementEnd();
  /// Skip forward to the statement terminator, leaving it for the caller: the
  /// chain error of task_52 needs the statement to still end where it looks.
  void skipToTerminator();

  // Statements.
  bool parseStatement(ParsedProgram& out);
  bool parseQueryOrDirective(ParsedProgram& out);
  bool parseClause(ParsedProgram& out);
  /// Parse a comma-separated goal list.  When `locations` is given, the start
  /// of every goal is appended to it.
  std::vector<Term> parseGoalList(std::vector<SourceLocation>* locations = nullptr);
  Term parseGoal();
  /// `a, b, c` as the compound `,`/2 (left-nested); used inside parentheses,
  /// where a conjunction can be a goal argument (НАЙТИВСЕ, ВЫП).
  Term parseCommaGroup();
  /// A whole goal out of `first` and what follows it: `,` binds tightest, then
  /// `->`, then `;` — as in ISO.  Both operators are right-nested there, and for
  /// `->` that is visible (`A -> T ; B -> U ; E`).
  Term parseGoalExpression(Term first);
  /// `A -> B` over comma groups, right-nested.
  Term parseIfThen(Term first);

  // Terms.
  Term parseTerm();
  /// The infix comparison layer of task_52: `A = B`, `A < B`, `A > B`,
  /// `A >= B`, `A =< B`, each sugar for a built-in goal; `\=` (task_92) is the
  /// same sugar under `НЕ`, and `is`, `=:=`, `=\=` take arithmetic operands and
  /// are handled here too.
  Term parseComparison();
  /// True when the operand being parsed belongs to `is`, `=:=` or `=\=`, which
  /// take arithmetic expressions written without `#…#` (task_92).
  bool arithmeticComparisonAhead() const;
  /// An arithmetic expression as a term of its own: `#expr(…)`.
  Term parseArithmeticOperand();
  /// An operand of a comparison: `#…#` or a primary term.
  Term parseOperand();
  Term parsePrimary();
  Term parseList();
  Term parseCompoundOrAtom();
  Term parseArithmetic();
  Term parseAdditive();
  Term parseMultiplicative();
  Term parseUnaryArithmetic();
  Term parsePrimaryArithmetic();

  VarId variableFor(std::string_view name, bool anonymous, const SourceLocation& location);
  void beginScope();

  /// One variable of the statement being parsed, for the singleton warning.
  struct VarUsage {
    std::string name;
    std::size_t count = 0;
    SourceLocation first;
    /// True once the variable was seen in the head of a clause.
    bool in_head = false;
  };

  std::vector<Token> tokens_;
  std::size_t position_ = 0;
  VarAllocator allocator_;
  DiagnosticSink* sink_;
  std::unordered_map<std::string, VarId> scope_;
  std::vector<std::pair<std::string, VarId>> query_variables_;
  std::vector<VarUsage> usages_;
  std::unordered_map<std::string, std::size_t> usage_index_;
  bool failed_ = false;
};

}  // namespace prologd
