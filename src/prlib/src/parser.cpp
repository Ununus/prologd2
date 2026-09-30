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

void Parser::beginScope() {
  scope_.clear();
  query_variables_.clear();
}

VarId Parser::variableFor(std::string_view name, bool anonymous) {
  if (anonymous) {
    return allocator_("");
  }
  const std::string key(name);
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
  if (check(TokenKind::Hash)) {
    return parseArithmetic();
  }
  return parsePrimary();
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
      return makeVar(variableFor(token.text, token.text == "_"), token.text);
    case TokenKind::Identifier:
      return parseCompoundOrAtom();
    case TokenKind::LBracket:
      return parseList();
    case TokenKind::LParen: {
      advance();
      std::vector<Term> parts;
      parts.push_back(parseTerm());
      while (!failed_ && match(TokenKind::Comma)) {
        parts.push_back(parseTerm());
      }
      if (!match(TokenKind::RParen)) {
        report(ErrorCode::UnpairedBracket, peek().location);
      }
      // `(A, B)` is a conjunction; represent it as the compound `,`/2 so that
      // it can be passed to meta-predicates such as НАЙТИВСЁ.
      Term result = parts.front();
      for (std::size_t i = 1; i < parts.size(); ++i) {
        result = makeCompound(",", {std::move(result), parts[i]});
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
  if (!match(TokenKind::LParen)) {
    return makeAtom(name.text);
  }
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
    report(ErrorCode::UnpairedBracket, peek().location);
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
    report(ErrorCode::UnpairedBracket, open.location);
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
    if (goal.text.empty() || goal.text == "_") {
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

std::vector<Term> Parser::parseGoalList() {
  std::vector<Term> goals;
  if (check(TokenKind::Dot) || check(TokenKind::Semicolon) || atEnd()) {
    report(ErrorCode::InvalidSentence, peek().location,
           "Пустое тело предложения");
    return goals;
  }
  goals.push_back(parseGoal());
  while (!failed_ && match(TokenKind::Comma)) {
    goals.push_back(parseGoal());
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
  if (match(TokenKind::ColonDash) || match(TokenKind::Arrow)) {
    body = parseGoalList();
  }
  if (!check(TokenKind::Dot) && !check(TokenKind::Semicolon)) {
    const TokenKind kind = peek().kind;
    if (kind == TokenKind::Bang) {
      report(ErrorCode::MisplacedCut, peek().location);
    } else if (kind == TokenKind::RBracket) {
      report(ErrorCode::UnpairedBracket, peek().location);
    } else if (kind == TokenKind::RParen) {
      report(ErrorCode::UnpairedBracket, peek().location);
    } else {
      report(ErrorCode::InvalidSentence, peek().location);
    }
    recoverToStatementEnd();
    out.ok = false;
    return false;
  }
  advance();  // terminator
  Clause clause;
  clause.head = std::move(head);
  clause.body = std::move(body);
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
  std::vector<Term> goals = parseGoalList();
  if (!check(TokenKind::Dot) && !check(TokenKind::Semicolon)) {
    report(ErrorCode::InvalidSentence, peek().location);
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
