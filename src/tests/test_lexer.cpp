#include <catch2/catch_test_macros.hpp>

#include <algorithm>
#include <string>
#include <vector>

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

TEST_CASE("a name is read the way ISO reads it") {
  // The one rule there is: a lower-case initial is a name, an upper-case one a
  // variable, `'` quotes an atom, and a name never ends with an apostrophe.
  DiagnosticSink sink;
  const auto tokens = lex("д Д Молоко молоко 'Молоко'", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);  // д — an atom
  REQUIRE(tokens[1].kind == TokenKind::Variable);    // Д
  REQUIRE(tokens[2].kind == TokenKind::Variable);    // Молоко
  REQUIRE(tokens[3].kind == TokenKind::Identifier);  // молоко
  REQUIRE(tokens[4].kind == TokenKind::QuotedAtom);  // 'Молоко'
  // An underscore makes a variable, and a capitalised name with one too (`В_`).
  const auto underscored = lex("_ _Пер В_", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(underscored[0].kind == TokenKind::Variable);
  REQUIRE(underscored[1].kind == TokenKind::Variable);
  REQUIRE(underscored[2].kind == TokenKind::Variable);
}

TEST_CASE("the names marker is a retired name now") {
  // There is nothing to declare on a file's first line any more, but the word is
  // still reserved: an old file must reach the checks and be told why it no
  // longer loads, rather than be read as a call to an unknown predicate (or, in
  // the old reading, as a string constant).
  DiagnosticSink sink;
  const auto tokens = lex("ИМЕНА variables", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);
  REQUIRE(tokens[1].kind == TokenKind::Identifier);
  REQUIRE(isReservedBuiltinName("ИМЕНА"));
  REQUIRE(isReservedBuiltinName("variables"));
  // Reserved for the checks, not offered as a built-in: nothing can call it.
  REQUIRE(reservedBuiltinNames().count("ИМЕНА") == 0);
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
  // `НАЙТИВСЁ` (with ё) left the language in task_44 and `substring` in task_84;
  // the lexer keeps both reserved so a call reaches the checks and is told what
  // happened, instead of failing as an upper-case variable.
  for (const std::string spelling : {"НАЙТИВСЁ", "substring"}) {
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

TEST_CASE("the original dialect's or-word is reserved like any other built-in") {
  // It came back in task_83, so this time it *is* offered by the keyword table:
  // reserved, and among the names completion and colouring are built from.
  // (The test's own name says «or-word» rather than the word itself because a
  // non-ASCII test *name* does not survive CMake's discovery step.)
  DiagnosticSink sink;
  const auto tokens = lex("ИЛИ", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);
  REQUIRE(isReservedBuiltinName("ИЛИ"));
  REQUIRE(reservedBuiltinNames().count("ИЛИ") == 1);
}

TEST_CASE("`sub_string` is reserved like any other built-in") {
  // task_84: the ISO name is English only, and it is offered — the two tests
  // above are about names the language stopped offering.
  DiagnosticSink sink;
  const auto tokens = lex("sub_string", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].kind == TokenKind::Identifier);
  REQUIRE(reservedBuiltinNames().count("sub_string") == 1);
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

TEST_CASE("`//` is one token, and `/` keeps its own") {
  // ISO's integer division is a sign of its own: `6 // 2` must not read as two
  // divisions.  A block comment is `/*`, which the lexer reads before it ever
  // looks at a slash, so `//` cannot be mistaken for a comment either.
  DiagnosticSink sink;
  const auto tokens = lex("6 // 2 / 3 /* пояснение */ 4", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[1].kind == TokenKind::SlashSlash);
  REQUIRE(tokens[1].text == "//");
  REQUIRE(tokens[3].kind == TokenKind::Slash);
  REQUIRE(tokens[3].text == "/");
  // The block comment is one gap: the token after it is the `4`.
  REQUIRE(tokens[5].kind == TokenKind::Integer);
  REQUIRE(tokens[5].text == "4");
}

TEST_CASE("`**` is one token, and `*` keeps its own") {
  // ISO's power is a sign of its own: `2**3` must not read as two
  // multiplications.  A block comment ends with `*/`, which never reaches the
  // switch — the lexer reads the comment before it looks at a star.
  DiagnosticSink sink;
  const auto tokens = lex("2**3 * 4", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[1].kind == TokenKind::StarStar);
  REQUIRE(tokens[1].text == "**");
  REQUIRE(tokens[3].kind == TokenKind::Star);
  REQUIRE(tokens[3].text == "*");
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
    const auto tokens = lex("<- :- ->", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::Arrow);
    REQUIRE(tokens[1].kind == TokenKind::ColonDash);
    // `->` is an operator of its own since task_85, not advice: it is read as
    // one token, like `;`.
    REQUIRE(tokens[2].kind == TokenKind::IfThen);
    REQUIRE(tokens[2].text == "->");
  }
}

TEST_CASE("the four standard-order signs are read as one token each") {
  // task_90: `@<`, `@=<`, `@>` and `@>=` were advice until the standard order
  // arrived; longest match first, or `@=<` would be read as `@=` and `>`.
  const struct {
    std::string source;
    prologd::TokenKind kind;
  } cases[] = {{"@<", prologd::TokenKind::AtLess},
               {"@=<", prologd::TokenKind::AtLessEqual},
               {"@>", prologd::TokenKind::AtGreater},
               {"@>=", prologd::TokenKind::AtGreaterEqual}};
  for (const auto& item : cases) {
    INFO("source: " << item.source);
    DiagnosticSink sink;
    const auto tokens = lex(item.source, sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens.size() == 2);
    REQUIRE(tokens[0].kind == item.kind);
    REQUIRE(tokens[0].text == item.source);
    REQUIRE(tokens[1].kind == prologd::TokenKind::EndOfFile);
  }
}

TEST_CASE("an ISO operator the dialect lacks is explained") {  // A sign from another Prolog is a lexical error with advice (task_52), not
  // the bare «недопустимый символ»: the reader is told what to write instead.
  // task_92 took `\=`, `=:=` and `=\=` off this list — the dialect reads them
  // now, so what is left is the signs it still does not have.
  const struct {
    std::string source;
    std::string needle;
  } cases[] = {{"X == Y", "сравнение термов записывают унификацией"},
               {"X \\== Y", "термы не совпадают"},
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

TEST_CASE("the ISO signs `\\=`, `=:=` and `=\\=` are single tokens") {
  // Splitting them into `<` and `=` would turn the statement into a syntax
  // error about a lost dot (the trap `@>=` set in task_90).
  const struct {
    std::string source;
    TokenKind kind;
  } cases[] = {{"X \\= Y", TokenKind::NotEqual},
               {"1 + 1 =:= 2", TokenKind::ArithEqual},
               {"2 =\\= 1 + 1", TokenKind::ArithNotEqual}};
  for (const auto& item : cases) {
    INFO("source: " << item.source);
    DiagnosticSink sink;
    const auto tokens = lex(item.source, sink);
    REQUIRE_FALSE(sink.hasErrors());
    const auto it = std::ranges::find_if(
        tokens, [&](const Token& token) { return token.kind == item.kind; });
    REQUIRE(it != tokens.end());
  }
}

TEST_CASE("a block comment runs to its closer") {
  DiagnosticSink sink;
  const auto tokens = lex("foo. /* two\nlines */ bar.", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(tokens[0].text == "foo");
  REQUIRE(tokens[2].text == "bar");
}

TEST_CASE("an unclosed block comment is explained") {
  DiagnosticSink sink;
  lex("foo. /* no closer\nbar.", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().message.find("не закрыт комментарий") !=
          std::string::npos);
}

TEST_CASE("a dict is told there are no dicts") {
  // `_{ключ: значение}` is ISO's dict, and `{Цель}` its shorthand for a call.
  // The brace is the thing to explain, and only the opener carries the
  // sentence — the closer would repeat it (task_82, stage 4).
  DiagnosticSink sink;
  lex("?X = _{a:1}.", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().message.find("фигурных скобок") !=
          std::string::npos);
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

TEST_CASE("a string escape stands for one character, and an unknown one is named") {
  // `\n`, `\t` and `\r` are the characters the escape names; `\\` and `\"` are
  // the two that would otherwise end the literal or vanish from it.
  const struct {
    std::string source;
    std::string expected;
  } cases[] = {{"\"a\\nb\"", "a\nb"},
               {"\"a\\tb\"", "a\tb"},
               {"\"a\\rb\"", "a\rb"},
               {"\"a\\\\b\"", "a\\b"},
               {"\"a\\\"b\"", "a\"b"}};
  for (const auto& item : cases) {
    INFO("source: " << item.source);
    DiagnosticSink sink;
    const auto tokens = lex(item.source, sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(tokens[0].kind == TokenKind::String);
    REQUIRE(tokens[0].text == item.expected);
  }
  // `\q` is a typo, so the literal is refused and the message lists what the
  // language has — one message for the literal, not one per backslash.
  {
    DiagnosticSink sink;
    lex("\"a\\qb\\qc\"", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().size() == 1);
    const PrologError& error = sink.diagnostics().front();
    REQUIRE(error.code == ErrorCode::InvalidStringLiteral);
    REQUIRE(error.message.find("\\q") != std::string::npos);
    REQUIRE(error.message.find("\\n") != std::string::npos);
  }
  // A backslash with the line break behind it escapes nothing.
  {
    DiagnosticSink sink;
    lex("\"a\\\n", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().size() == 1);
    REQUIRE(sink.diagnostics().front().message.find("не закончена") != std::string::npos);
  }
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
