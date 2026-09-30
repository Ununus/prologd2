#include <catch2/catch_test_macros.hpp>

#include "prlib/lexer.hpp"

using namespace prologd;

namespace {

std::vector<Token> lex(const std::string& source, DiagnosticSink& sink) {
  Lexer lexer(source, "test");
  return lexer.tokenize(sink);
}

}  // namespace

TEST_CASE("lexer recognises structural tokens") {
  DiagnosticSink sink;
  const auto tokens = lex("foo(X, [a|b]) :- ! ; bar.", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);
  REQUIRE(tokens[0].text == "foo");
  REQUIRE(tokens[1].kind == TokenKind::LParen);
  REQUIRE(tokens[2].kind == TokenKind::Variable);
  REQUIRE(tokens[2].text == "X");
  REQUIRE(tokens[3].kind == TokenKind::Comma);
  REQUIRE(tokens[4].kind == TokenKind::LBracket);
  REQUIRE(tokens[5].kind == TokenKind::Identifier);
  REQUIRE(tokens[6].kind == TokenKind::Bar);
  REQUIRE(tokens[7].kind == TokenKind::Identifier);
  REQUIRE(tokens[8].kind == TokenKind::RBracket);
  REQUIRE(tokens[9].kind == TokenKind::RParen);
  REQUIRE(tokens[10].kind == TokenKind::ColonDash);
  REQUIRE(tokens[11].kind == TokenKind::Bang);
  REQUIRE(tokens[12].kind == TokenKind::Semicolon);
  REQUIRE(tokens[13].kind == TokenKind::Identifier);
  REQUIRE(tokens[14].kind == TokenKind::Dot);
  REQUIRE(tokens[15].kind == TokenKind::EndOfFile);
}

TEST_CASE("lexer distinguishes atoms, variables and reserved names") {
  DiagnosticSink sink;
  const auto tokens = lex("foo Bar _ _Hidden БОЛЬШЕ НАЙТИВСЕ 'quoted atom'", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);
  REQUIRE(tokens[1].kind == TokenKind::Variable);
  REQUIRE(tokens[2].kind == TokenKind::Variable);
  REQUIRE(tokens[2].text == "_");
  REQUIRE(tokens[3].kind == TokenKind::Variable);
  REQUIRE(tokens[3].text == "_Hidden");
  // Russian built-ins stay atoms even though they start with upper case.
  REQUIRE(tokens[4].kind == TokenKind::Identifier);
  REQUIRE(tokens[4].text == "БОЛЬШЕ");
  REQUIRE(tokens[5].kind == TokenKind::Identifier);
  REQUIRE(tokens[5].text == "НАЙТИВСЕ");
  REQUIRE(tokens[6].kind == TokenKind::QuotedAtom);
  REQUIRE(tokens[6].text == "quoted atom");
}

TEST_CASE("a retired spelling is still a predicate name, not a variable") {
  // `НАЙТИВСЁ` (with ё) and `ИЛИ` left the language (task_44); the lexer keeps
  // them reserved so a call reaches the checks and gets a message instead of
  // failing as an upper-case variable.
  for (const std::string& spelling : {"НАЙТИВСЁ", "ИЛИ"}) {
    INFO("spelling: " << spelling);
    DiagnosticSink sink;
    const auto tokens = lex(spelling, sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Identifier);
    REQUIRE(isReservedBuiltinName(spelling));
    // ... but they are not among the names the keyword table is built from.
    REQUIRE(reservedBuiltinNames().count(spelling) == 0);
  }
}

TEST_CASE("lexer handles numbers") {
  DiagnosticSink sink;
  const auto tokens = lex("42 3.14 -7", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Integer);
  REQUIRE(tokens[1].kind == TokenKind::Float);
  REQUIRE(tokens[2].kind == TokenKind::Minus);
  REQUIRE(tokens[3].kind == TokenKind::Integer);
}

TEST_CASE("lexer reports malformed numbers") {
  DiagnosticSink sink;
  const auto tokens = lex("12.123.123", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().code == ErrorCode::InvalidNumberLiteral);
  (void)tokens;
}

TEST_CASE("lexer reports unterminated strings") {
  DiagnosticSink sink;
  lex("foo(bar,\"er).", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().code == ErrorCode::InvalidStringLiteral);
}

TEST_CASE("lexer handles UTF-8 identifiers and strings") {
  DiagnosticSink sink;
  const auto tokens = lex("Ёжик(Пёс,\"Привет, мир\")", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Variable);
  REQUIRE(tokens[0].text == "Ёжик");
  REQUIRE(tokens[1].kind == TokenKind::LParen);
  REQUIRE(tokens[2].kind == TokenKind::Variable);
  REQUIRE(tokens[3].kind == TokenKind::Comma);
  REQUIRE(tokens[4].kind == TokenKind::String);
  REQUIRE(tokens[4].text == "Привет, мир");
}

TEST_CASE("lexer skips comments") {
  DiagnosticSink sink;
  const auto tokens = lex("foo. % comment\nbar.", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].text == "foo");
  REQUIRE(tokens[2].text == "bar");
}
