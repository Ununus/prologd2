#include "prlib/parser.hpp"

#include <cstdlib>
#include <stdexcept>

namespace prologd {

namespace {
constexpr std::string_view kExpressionWrapper = "$expr";
/// The import directive has two spellings: the Russian name the original
/// dialect used, and its English alias (task_39).
constexpr std::string_view kImportNames[] = {"ИМПОРТ", "import"};

bool isImportName(std::string_view name) {
  for (const std::string_view candidate : kImportNames) {
    if (candidate == name) {
      return true;
    }
  }
  return false;
}

/// Folds a comma-separated list of goals into the compound `,`/2, left-nested.
/// The parser and the solver both treat a `,`/2 goal as a conjunction, so the
/// nesting only affects how the term prints.
Term commaGoal(std::vector<Term>& goals) {
  Term result = std::move(goals.front());
  for (std::size_t i = 1; i < goals.size(); ++i) {
    result = makeCompound(",", {std::move(result), std::move(goals[i])});
  }
  return result;
}

/// The wording of a `;` found where the original dialect accepted it as a
/// sentence terminator (task_41) — the message says what changed and what the
/// statement needs instead of the `;`.
constexpr const char* kRetiredTerminator =
    "«;» — дизъюнкция; предложение должно заканчиваться точкой";

/// The wording of an ISO `is` written as an infix operator (`X is 2+3`).  The
/// dialect has no `is`: `#…#` marks an expression, and `РАВНО` evaluates it
/// (task_55).  Without this the reader is told only «Цель не может быть
/// переменной».
constexpr const char* kInfixIsHint =
    "«is» — не оператор: выражение помечают «#…#», например «РАВНО(X, #2+3#)»";

/// Tokens that can open a term, a fact, a rule or a query.  When one of them
/// follows a *complete* statement, what is missing is the dot of that
/// statement — saying so points at the end of the finished line instead of at
/// the start of the next statement, which is where the generic parse error
/// used to land (task_56).
bool beginsStatement(TokenKind kind) {
  switch (kind) {
    case TokenKind::Identifier:
    case TokenKind::Variable:
    case TokenKind::Integer:
    case TokenKind::Float:
    case TokenKind::String:
    case TokenKind::QuotedAtom:
    case TokenKind::Hash:
    case TokenKind::Question:
    case TokenKind::NotGoal:
    case TokenKind::LParen:
    case TokenKind::LBracket:
      return true;
    default:
      return false;
  }
}

/// One row of the infix comparison layer (task_52): the sign, and the built-in
/// goal it is sugar for.  `negated` rows desugar to `НЕ(имя(A, B))`, which is
/// how `>=` and `=<` are written without a second built-in, and why a free
/// operand there is the runtime error of `БОЛЬШЕ`/`МЕНЬШЕ` rather than a
/// silent failure.
struct InfixOperator {
  TokenKind kind;
  const char* text;
  const char* functor;
  bool negated;
};

constexpr InfixOperator kInfixOperators[] = {
    {TokenKind::Equal, "=", "РАВНО", false},
    {TokenKind::Less, "<", "МЕНЬШЕ", false},
    {TokenKind::Greater, ">", "БОЛЬШЕ", false},
    {TokenKind::LessEqual, "=<", "БОЛЬШЕ", true},
    {TokenKind::GreaterEqual, ">=", "МЕНЬШЕ", true},
};

/// The row for a token kind, `nullptr` when the kind is not an infix operator.
const InfixOperator* infixOperator(TokenKind kind) {
  for (const InfixOperator& entry : kInfixOperators) {
    if (entry.kind == kind) {
      return &entry;
    }
  }
  return nullptr;
}
}  // namespace

Parser::Parser(std::vector<Token> tokens, VarAllocator allocator, DiagnosticSink* sink)
    : tokens_(std::move(tokens)), allocator_(std::move(allocator)), sink_(sink) {}

const Token& Parser::peek(std::size_t lookahead) const {
  const std::size_t index = position_ + lookahead;
  if (index >= tokens_.size()) {
    return tokens_.back();
  }
  return tokens_[index];
}

const Token& Parser::previous() const {
  return tokens_[position_ == 0 ? 0 : position_ - 1];
}

Token Parser::advance() {
  const Token token = peek();
  if (position_ + 1 < tokens_.size()) {
    ++position_;
  }
  return token;
}

bool Parser::check(TokenKind kind) const { return peek().kind == kind; }

bool Parser::match(TokenKind kind) {
  if (!check(kind)) {
    return false;
  }
  advance();
  return true;
}

bool Parser::atEnd() const { return check(TokenKind::EndOfFile); }

void Parser::report(ErrorCode code, const SourceLocation& location, std::string message) {
  failed_ = true;
  if (sink_ == nullptr) {
    return;
  }
  PrologError error;
  error.code = code;
  error.location = location;
  error.message = message.empty() ? std::string(errorCodeText(code)) : std::move(message);
  error.isParseError = true;
  sink_->report(std::move(error));
}

void Parser::reportUnclosedBracket(char open, const SourceLocation& location) {
  std::string message = "непарные скобки: '";
  message += open;
  message += "' открыта в строке ";
  message += std::to_string(location.line);
  report(ErrorCode::UnpairedBracket, location, std::move(message));
}

void Parser::reportMissingDot() {
  // The dot belongs right after the last token of the statement, and that is
  // where a reader has to look.  The message says what the statement *needs*:
  // "предложение заканчивается точкой" read as a statement of fact, and
  // "не заканчивается" only named the defect.
  report(ErrorCode::InvalidSentence, previous().location,
         "предложение должно заканчиваться точкой");
}

void Parser::warn(ErrorCode code, const SourceLocation& location, std::string message) {
  if (sink_ == nullptr) {
    return;  // a warning never fails the statement, so there is nothing else to do
  }
  PrologError warning;
  warning.code = code;
  warning.severity = Severity::Warning;
  warning.location = location;
  warning.message = std::move(message);
  warning.isParseError = true;
  sink_->report(std::move(warning));
}

void Parser::warnSingletonVariables(bool has_body) {
  for (const VarUsage& usage : usages_) {
    if (usage.count != 1) {
      continue;
    }
    if (usage.in_head && !has_body) {
      // A fact that never mentions the name again: almost always a constant
      // somebody wrote without quotes.
      warn(ErrorCode::SingletonVariable, usage.first,
           usage.name +
               " — переменная, а не константа; если имелась в виду константа, "
               "запишите её в одинарных кавычках: '" +
               usage.name + "'");
    } else if (usage.in_head) {
      // In a rule the name can also be a forgotten wildcard, so both readings
      // are named — `_` is how the dialect says "the value does not matter".
      warn(ErrorCode::SingletonVariable, usage.first,
           usage.name +
               " — переменная, а не константа; если это пропуск, назовите её _" +
               usage.name + ", а если константа — запишите её в одинарных кавычках: '" +
               usage.name + "'");
    } else {
      warn(ErrorCode::SingletonVariable, usage.first,
           "переменная " + usage.name +
               " встречается один раз; если это намеренно, назовите её _" + usage.name);
    }
  }
}

void Parser::recoverToStatementEnd() {
  while (!atEnd()) {
    const TokenKind kind = peek().kind;
    if (kind == TokenKind::Dot || kind == TokenKind::Semicolon) {
      advance();
      return;
    }
    advance();
  }
}

void Parser::skipToTerminator() {
  // After the chain error (`X = Y = Z`) the rest of the statement is skipped
  // *up to* its terminator, not past it: the caller still has to see the dot it
  // expects, or the same mistake would be reported a second time.
  while (!atEnd()) {
    const TokenKind kind = peek().kind;
    if (kind == TokenKind::Dot || kind == TokenKind::Semicolon) {
      return;
    }
    advance();
  }
}

void Parser::beginScope() {
  scope_.clear();
  query_variables_.clear();
  usages_.clear();
  usage_index_.clear();
}

VarId Parser::variableFor(std::string_view name, bool anonymous,
                          const SourceLocation& location) {
  if (anonymous) {
    return allocator_("");
  }
  const std::string key(name);
  // A name written with a leading underscore is the dialect's way of saying
  // "deliberately unused", so it is not a singleton and not recorded.
  if (!key.empty() && key.front() != '_') {
    const auto known = usage_index_.find(key);
    if (known == usage_index_.end()) {
      usage_index_.emplace(key, usages_.size());
      VarUsage usage;
      usage.name = key;
      usage.count = 1;
      usage.first = location;
      usages_.push_back(std::move(usage));
    } else {
      ++usages_[known->second].count;
    }
  }
  auto it = scope_.find(key);
  if (it != scope_.end()) {
    return it->second;
  }
  const VarId id = allocator_(name);
  scope_.emplace(key, id);
  if (!key.empty() && key.front() != '_') {
    query_variables_.emplace_back(key, id);
  }
  return id;
}

Term Parser::parseTerm() {
  if (match(TokenKind::NotGoal)) {
    // ISO's `\+ Ц` — the same goal as `НЕ(Ц)` (task_55).  A prefix at the term
    // level: `,` and `;` still bind looser, so `\+ A, B` is `(\+ A), B`, and
    // `\+ (A, B)` needs the brackets it needs in ISO as well.
    return makeCompound("НЕ", {parseTerm()});
  }
  // `#…#` is not special here: it is one of the operands the comparison layer
  // takes, so `#1 + 1# = 2` parses like any other comparison (task_52).
  return parseComparison();
}

Term Parser::parseComparison() {
  Term left = parseOperand();
  if (failed_) {
    return left;
  }
  const InfixOperator* row = infixOperator(peek().kind);
  if (row == nullptr) {
    return left;
  }
  const Token op = advance();
  Term right = parseOperand();
  if (failed_) {
    return left;
  }
  // `xfx`, as in ISO: `X = Y = Z` is neither of the nestings a reader might
  // guess, so it is reported on its own — at the *second* sign, which is where
  // the reader has to look, and the message quotes that sign.  The two halves of
  // the suggestion keep their own signs, so a mixed chain (`X = Y < 1`) is not
  // described with the wrong one.
  if (infixOperator(peek().kind) != nullptr) {
    const std::string first = op.text;
    const std::string second = peek().text;
    report(ErrorCode::InvalidSentence, peek().location,
           "«" + second + "» — не цепочка: разбейте на два сравнения, «A " + first +
               " B, B " + second + " C»");
    skipToTerminator();
    return left;
  }
  std::vector<Term> arguments;
  arguments.push_back(std::move(left));
  arguments.push_back(std::move(right));
  if (row->negated) {
    return makeCompound("НЕ", {makeCompound(row->functor, std::move(arguments))});
  }
  return makeCompound(row->functor, std::move(arguments));
}

Term Parser::parseOperand() {
  // `#…#` marks an expression everywhere a term is expected, including here:
  // `X = #2 + 3#` evaluates the right side (task_52).
  if (check(TokenKind::Hash)) {
    return parseArithmetic();
  }
  return parsePrimary();
}

Term Parser::parseCommaGroup() {
  std::vector<Term> parts;
  parts.push_back(parseTerm());
  while (!failed_ && match(TokenKind::Comma)) {
    parts.push_back(parseTerm());
  }
  // A parenthesised conjunction is a goal argument (НАЙТИВСЕ, ВЫП): represent
  // it as the compound `,`/2, which is what the solver expands in place.
  Term result = std::move(parts.front());
  for (std::size_t i = 1; i < parts.size(); ++i) {
    result = makeCompound(",", {std::move(result), std::move(parts[i])});
  }
  return result;
}

Term Parser::parsePrimary() {
  const Token token = peek();
  switch (token.kind) {
    case TokenKind::Integer: {
      advance();
      auto parsed = BigInt::tryParse(token.text);
      if (!parsed) {
        report(ErrorCode::InvalidNumberLiteral, token.location);
        return makeInt(0);
      }
      return makeInt(*parsed);
    }
    case TokenKind::Float: {
      advance();
      try {
        return makeFloat(std::stod(token.text));
      } catch (const std::exception&) {
        report(ErrorCode::InvalidNumberLiteral, token.location);
        return makeFloat(0.0);
      }
    }
    case TokenKind::String:
      advance();
      return makeString(token.text);
    case TokenKind::QuotedAtom:
      advance();
      return makeAtom(token.text);
    case TokenKind::Variable:
      advance();
      return makeVar(variableFor(token.text, token.text == "_", token.location),
                     token.text);
    case TokenKind::Identifier:
      return parseCompoundOrAtom();
    case TokenKind::LBracket:
      return parseList();
    case TokenKind::LParen: {
      const Token open = advance();
      Term result = parseCommaGroup();
      // `(A ; B)` is a disjunction: `,` binds tighter, as in ISO, so the
      // operands of `;` are comma groups.  A parenthesised disjunction is how
      // one reaches `ВЫП` and `НАЙТИВСЕ`, whose goals are arguments.
      while (!failed_ && match(TokenKind::Semicolon)) {
        const Token semicolon = previous();
        if (check(TokenKind::Dot) || atEnd()) {
          report(ErrorCode::InvalidSentence, semicolon.location, kRetiredTerminator);
          break;
        }
        Term right = parseCommaGroup();
        result = makeCompound(";", {std::move(result), std::move(right)});
      }
      if (!match(TokenKind::RParen)) {
        reportUnclosedBracket('(', open.location);
      }
      return result;
    }
    case TokenKind::Minus: {
      advance();
      if (check(TokenKind::Integer)) {
        const Token number = advance();
        auto parsed = BigInt::tryParse(number.text);
        if (!parsed) {
          report(ErrorCode::InvalidNumberLiteral, number.location);
          return makeInt(0);
        }
        return makeInt(-*parsed);
      }
      if (check(TokenKind::Float)) {
        const Token number = advance();
        try {
          return makeFloat(-std::stod(number.text));
        } catch (const std::exception&) {
          report(ErrorCode::InvalidNumberLiteral, number.location);
          return makeFloat(0.0);
        }
      }
      report(ErrorCode::MisplacedSign, token.location);
      return makeAtom("<error>");
    }
    case TokenKind::Plus:
    case TokenKind::Star:
    case TokenKind::Slash:
      advance();
      report(ErrorCode::MisplacedSign, token.location);
      return makeAtom("<error>");
    case TokenKind::Bang:
      advance();
      report(ErrorCode::MisplacedCut, token.location);
      return makeAtom("!");
    default:
      report(ErrorCode::InvalidSentence, token.location);
      advance();
      return makeAtom("<error>");
  }
}

Term Parser::parseCompoundOrAtom() {
  const Token name = advance();
  if (!check(TokenKind::LParen)) {
    return makeAtom(name.text);
  }
  // Keep the opening bracket: when the closing one is missing, that is where
  // a reader has to look.
  const Token open = advance();
  std::vector<Term> arguments;
  if (check(TokenKind::RParen)) {
    report(ErrorCode::InvalidFunction, peek().location,
           "Функция должна иметь хотя бы один аргумент");
    advance();
    return makeAtom(name.text);
  }
  for (;;) {
    if (check(TokenKind::RParen)) {
      report(ErrorCode::InvalidFunction, peek().location,
             "Пропущен аргумент функции");
      break;
    }
    arguments.push_back(parseTerm());
    if (failed_) {
      break;
    }
    if (match(TokenKind::Comma)) {
      continue;
    }
    break;
  }
  if (!match(TokenKind::RParen)) {
    if (check(TokenKind::Semicolon)) {
      report(ErrorCode::InvalidFunction, peek().location,
             "«;» — дизъюнкция; заключите её в скобки: (A ; B)");
    } else {
      reportUnclosedBracket('(', open.location);
    }
  }
  return makeCompound(name.text, std::move(arguments));
}

Term Parser::parseList() {
  const Token open = advance();  // '['
  if (match(TokenKind::RBracket)) {
    return makeNil();
  }
  std::vector<Term> elements;
  Term tail = makeNil();
  bool has_tail = false;
  for (;;) {
    elements.push_back(parseTerm());
    if (failed_) {
      break;
    }
    if (match(TokenKind::Comma)) {
      continue;
    }
    if (match(TokenKind::Bar)) {
      tail = parseTerm();
      has_tail = true;
    }
    break;
  }
  if (!match(TokenKind::RBracket)) {
    if (check(TokenKind::Semicolon)) {
      report(ErrorCode::WrongList, peek().location,
             "«;» — дизъюнкция; элементы списка разделяются запятой");
    } else {
      reportUnclosedBracket('[', open.location);
    }
    return makeNil();
  }
  (void)has_tail;
  return makeListFromVector(elements, tail);
}

Term Parser::parseArithmetic() {
  const Token hash = advance();  // '#'
  Term expression = parseAdditive();
  if (!match(TokenKind::Hash)) {
    report(ErrorCode::InvalidArithmeticExpression, hash.location,
           "Не закрыто арифметическое выражение");
  }
  return makeCompound(kExpressionWrapper, {std::move(expression)});
}

Term Parser::parseAdditive() {
  Term left = parseMultiplicative();
  while (!failed_ && (check(TokenKind::Plus) || check(TokenKind::Minus))) {
    const Token op = advance();
    Term right = parseMultiplicative();
    left = makeCompound(op.text, {std::move(left), std::move(right)});
  }
  return left;
}

Term Parser::parseMultiplicative() {
  Term left = parseUnaryArithmetic();
  while (!failed_) {
    std::string op;
    if (check(TokenKind::Star) || check(TokenKind::Slash)) {
      op = advance().text;
    } else if (check(TokenKind::Identifier) &&
               (peek().text == "mod" || peek().text == "div")) {
      op = advance().text;
    } else {
      break;
    }
    Term right = parseUnaryArithmetic();
    left = makeCompound(op, {std::move(left), std::move(right)});
  }
  return left;
}

Term Parser::parseUnaryArithmetic() {
  if (match(TokenKind::Minus)) {
    return makeCompound("neg", {parseUnaryArithmetic()});
  }
  if (match(TokenKind::Plus)) {
    return parseUnaryArithmetic();
  }
  return parsePrimaryArithmetic();
}

Term Parser::parsePrimaryArithmetic() {
  const Token token = peek();
  switch (token.kind) {
    case TokenKind::Integer:
      return parsePrimary();
    case TokenKind::Float:
      return parsePrimary();
    case TokenKind::Variable:
      return parsePrimary();
    case TokenKind::LParen: {
      advance();
      Term inner = parseAdditive();
      if (!match(TokenKind::RParen)) {
        report(ErrorCode::InvalidArithmeticExpression, peek().location,
               "Не закрыта скобка в арифметическом выражении");
      }
      return inner;
    }
    default:
      report(ErrorCode::InvalidArithmeticExpression, token.location,
             "Ожидался операнд арифметического выражения");
      return makeInt(0);
  }
}

Term Parser::parseGoal() {
  if (match(TokenKind::Bang)) {
    return makeAtom("!");
  }
  Term goal = parseTerm();
  if (failed_) {
    return goal;
  }
  if (goal.kind == TermKind::Var) {
    if (check(TokenKind::Identifier) && peek().text == "is") {
      report(ErrorCode::InvalidSentence, previous().location, kInfixIsHint);
    } else if (goal.text.empty() || goal.text == "_") {
      report(ErrorCode::MisplacedUnderscore, previous().location);
    } else {
      report(ErrorCode::InvalidSentence, previous().location,
             "Цель не может быть переменной");
    }
  } else if (isList(goal)) {
    report(ErrorCode::InvalidGoal, previous().location);
  } else if (goal.kind != TermKind::Atom && goal.kind != TermKind::Compound) {
    report(ErrorCode::InvalidSentence, previous().location,
           "Цель должна быть предикатом");
  }
  return goal;
}

std::vector<Term> Parser::parseGoalList(std::vector<SourceLocation>* locations) {
  std::vector<Term> goals;
  if (check(TokenKind::Dot) || check(TokenKind::Semicolon) || atEnd()) {
    report(ErrorCode::InvalidSentence, peek().location,
           "Пустое тело предложения");
    return goals;
  }
  if (locations != nullptr) {
    locations->push_back(peek().location);
  }
  goals.push_back(parseGoal());
  while (!failed_ && match(TokenKind::Comma)) {
    if (locations != nullptr) {
      locations->push_back(peek().location);
    }
    goals.push_back(parseGoal());
  }
  if (!failed_ && check(TokenKind::Semicolon)) {
    // `,` binds tighter than `;`, so a disjunction swallows the conjunction
    // collected so far: `A, B ; C, D` is `(A, B) ; (C, D)`.  The whole thing
    // becomes one goal, and the per-goal positions collapse to the first.
    Term left = commaGoal(goals);
    while (!failed_ && check(TokenKind::Semicolon)) {
      const Token semicolon = advance();
      if (check(TokenKind::Dot) || atEnd()) {
        // `;` where the statement ends: the terminator of the original dialect,
        // retired in favour of a disjunction.
        report(ErrorCode::InvalidSentence, semicolon.location, kRetiredTerminator);
        break;
      }
      std::vector<Term> right_items;
      right_items.push_back(parseGoal());
      while (!failed_ && match(TokenKind::Comma)) {
        right_items.push_back(parseGoal());
      }
      left = makeCompound(";", {std::move(left), commaGoal(right_items)});
    }
    goals.clear();
    goals.push_back(std::move(left));
    if (locations != nullptr) {
      locations->resize(1);
    }
  }
  return goals;
}

bool Parser::parseClause(ParsedProgram& out) {
  beginScope();
  const SourceLocation location = peek().location;
  Term head = parseTerm();
  if (failed_) {
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  // Everything recorded so far is in the head; a variable of the head that the
  // clause never mentions again is the "constant without quotes" trap.
  for (VarUsage& usage : usages_) {
    if (usage.count > 0) {
      usage.in_head = true;
    }
  }
  if (head.kind == TermKind::Var || isList(head)) {
    report(ErrorCode::InvalidGoal, location,
           "Голова предложения не может быть списком или переменной");
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  if (head.kind != TermKind::Atom && head.kind != TermKind::Compound) {
    report(ErrorCode::InvalidSentence, location,
           "Голова предложения должна быть предикатом");
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  std::vector<Term> body;
  std::vector<SourceLocation> body_locations;
  if (match(TokenKind::ColonDash) || match(TokenKind::Arrow)) {
    body = parseGoalList(&body_locations);
  }
  if (!check(TokenKind::Dot)) {
    const TokenKind kind = peek().kind;
    if (kind == TokenKind::Semicolon) {
      // The terminator of the original dialect; `;` is a disjunction now.
      report(ErrorCode::InvalidSentence, peek().location, kRetiredTerminator);
    } else if (kind == TokenKind::EndOfFile && !failed_) {
      reportMissingDot();
    } else if (kind == TokenKind::Bang) {
      report(ErrorCode::MisplacedCut, peek().location);
    } else if (kind == TokenKind::RBracket) {
      report(ErrorCode::UnpairedBracket, peek().location);
    } else if (kind == TokenKind::RParen) {
      report(ErrorCode::UnpairedBracket, peek().location);
    } else if (!failed_ && beginsStatement(kind)) {
      // The statement is complete and something new begins: the dot is what
      // the reader is missing.
      reportMissingDot();
    } else {
      report(ErrorCode::InvalidSentence, peek().location);
    }
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  advance();  // terminator
  warnSingletonVariables(!body.empty());
  Clause clause;
  clause.head = std::move(head);
  clause.body = std::move(body);
  clause.bodyLocations = std::move(body_locations);
  clause.location = location;
  out.order.push_back(StatementRef{StatementRef::Kind::Clause, out.clauses.size()});
  out.clauses.push_back(std::move(clause));
  return true;
}

bool Parser::parseQueryOrDirective(ParsedProgram& out) {
  const SourceLocation location = peek().location;
  bool is_query = false;
  if (match(TokenKind::Question)) {
    is_query = true;
    match(TokenKind::Minus);  // accept the standard `?-` form
  } else {
    match(TokenKind::ColonDash);
  }
  beginScope();
  std::vector<SourceLocation> goal_locations;
  std::vector<Term> goals = parseGoalList(&goal_locations);
  if (!check(TokenKind::Dot)) {
    if (check(TokenKind::Semicolon)) {
      report(ErrorCode::InvalidSentence, peek().location, kRetiredTerminator);
    } else if ((check(TokenKind::EndOfFile) || beginsStatement(peek().kind)) &&
               !failed_) {
      reportMissingDot();
    } else {
      report(ErrorCode::InvalidSentence, peek().location);
    }
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  advance();

  if (failed_) {
    out.ok = false;
    return false;
  }

  // `ИМПОРТ("file")` is a directive, not a runtime goal.
  if (goals.size() == 1 && goals[0].kind == TermKind::Compound &&
      goals[0].compound != nullptr && isImportName(goals[0].compound->name) &&
      goals[0].compound->args.size() == 1) {
    const Term& argument = goals[0].compound->args[0];
    if (argument.kind == TermKind::String || argument.kind == TermKind::Atom) {
      out.order.push_back(StatementRef{StatementRef::Kind::Import, out.imports.size()});
      out.imports.push_back(ImportDirective{argument.text, location});
      return true;
    }
    report(ErrorCode::ImportError, location, "ИМПОРТ ожидает имя файла в кавычках");
    out.ok = false;
    return false;
  }

  Query query;
  query.goals = std::move(goals);
  query.goalLocations = std::move(goal_locations);
  query.variables = query_variables_;
  query.location = location;
  query.isDirective = !is_query;
  out.order.push_back(StatementRef{StatementRef::Kind::Query, out.queries.size()});
  out.queries.push_back(std::move(query));
  return true;
}

bool Parser::parseStatement(ParsedProgram& out) {
  if (check(TokenKind::Question) || check(TokenKind::ColonDash)) {
    return parseQueryOrDirective(out);
  }
  return parseClause(out);
}

ParsedProgram Parser::parseProgram() {
  ParsedProgram result;
  while (!atEnd()) {
    failed_ = false;
    if (!parseStatement(result)) {
      result.ok = false;
    }
  }
  return result;
}

std::optional<ParsedProgram> Parser::parseOne() {
  if (atEnd()) {
    return std::nullopt;
  }
  ParsedProgram result;
  failed_ = false;
  if (!parseStatement(result)) {
    result.ok = false;
  }
  return result;
}

}  // namespace prologd
