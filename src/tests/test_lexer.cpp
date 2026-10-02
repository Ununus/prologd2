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

TEST_CASE("`\\+` is one token, and a lone backslash is an error") {
  {
    DiagnosticSink sink;
    const auto tokens = lex("?\\+ foo.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[1].kind == TokenKind::NotGoal);
    REQUIRE(tokens[1].text == "\\+");
    REQUIRE(tokens[2].kind == TokenKind::Identifier);
  }
  {
    // A backslash that starts nothing (task_55): still the character the
    // language does not know, so the diagnostic and the recoverable token stay.
    DiagnosticSink sink;
    const auto tokens = lex("\\", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Unknown);
    REQUIRE(tokens[0].text == "\\");
  }
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

TEST_CASE("a dot ends a number, not a float") {
  // task_52, as in ISO: `2.` is the integer 2 and the sentence terminator, so
  // a real without a fraction is written `2.0`.  The trailing-dot float of the
  // original PrologD would swallow the statement's own dot.
  {
    DiagnosticSink sink;
    const auto tokens = lex("2.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Integer);
    REQUIRE(tokens[0].text == "2");
    REQUIRE(tokens[1].kind == TokenKind::Dot);
  }
  {
    DiagnosticSink sink;
    const auto tokens = lex("2.0", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Float);
    REQUIRE(tokens[0].text == "2.0");
    REQUIRE(tokens[1].kind == TokenKind::EndOfFile);
  }
}

TEST_CASE("the comparison signs are one token each") {
  // task_52: `=`, `<`, `>`, `=<`, `>=` are the sugar of the comparison layer.
  const struct {
    std::string source;
    TokenKind kind;
  } signs[] = {{"=", TokenKind::Equal},
               {"<", TokenKind::Less},
               {">", TokenKind::Greater},
               {"=<", TokenKind::LessEqual},
               {">=", TokenKind::GreaterEqual}};
  for (const auto& sign : signs) {
    INFO("sign: " << sign.source);
    DiagnosticSink sink;
    const auto tokens = lex(sign.source, sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == sign.kind);
    REQUIRE(tokens[0].text == sign.source);
    REQUIRE(tokens[1].kind == TokenKind::EndOfFile);
  }
  // The rule arrows are still two characters, and `=<` must not be read as
  // `<` followed by `=`.
  {
    DiagnosticSink sink;
    const auto tokens = lex("<- :-", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Arrow);
    REQUIRE(tokens[1].kind == TokenKind::ColonDash);
  }
}

TEST_CASE("an ISO operator the dialect lacks is explained") {
  // A sign from another Prolog is a lexical error with advice (task_52), not
  // the bare «недопустимый символ»: the reader is told what to write instead.
  const struct {
    std::string source;
    std::string needle;
  } cases[] = {{"X == Y", "сравнение термов записывают унификацией"},
               {"X \\== Y", "термы не совпадают"},
               {"X \\= Y", "не унифицируется"},
               {"1 + 1 =:= 2", "выражение вычисляет «#…#»"},
               {"X =\\= Y", "«не равно»"},
               {"X @< Y", "сравнение по стандартному порядку"},
               {"X @>= Y", "сравнение по стандартному порядку"},
               {"X -> Y", "выбор в Пролог-Д — это «;» и «ПЕРВОЕ(Ц1, Ц2)»"},
               {"X <= Y", "«меньше или равно» записывают «=<»"}};
  for (const auto& item : cases) {
    INFO("source: " << item.source);
    DiagnosticSink sink;
    lex(item.source, sink);
    REQUIRE(sink.hasErrors());
    const std::string& message = sink.diagnostics().front().message;
    REQUIRE(message.find(item.needle) != std::string::npos);
  }
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
