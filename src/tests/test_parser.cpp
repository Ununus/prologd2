#include <catch2/catch_test_macros.hpp>

#include "prlib/parser.hpp"

using namespace prologd;

namespace {

ParsedProgram parse(const std::string& source, DiagnosticSink& sink) {
  Lexer lexer(source, "test");
  std::vector<Token> tokens = lexer.tokenize(sink);
  std::uint32_t next = 0;
  Parser parser(std::move(tokens), [&next](std::string_view) { return next++; }, &sink);
  return parser.parseProgram();
}

}  // namespace

TEST_CASE("parser handles facts, rules and queries") {
  DiagnosticSink sink;
  const auto program = parse(
      "родитель(аня, боря).\n"
      "дед(X, Y) :- родитель(X, Z), родитель(Z, Y).\n"
      "?дед(аня, Y).\n",
      sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(program.clauses.size() == 2);
  REQUIRE(program.queries.size() == 1);
  REQUIRE(program.clauses[0].head.kind == TermKind::Compound);
  REQUIRE(program.clauses[1].body.size() == 2);
  REQUIRE(program.queries[0].variables.size() == 1);
  REQUIRE(program.queries[0].variables[0].first == "Y");
  REQUIRE(program.order.size() == 3);
}

TEST_CASE("parser accepts both rule arrows and terminators") {
  DiagnosticSink sink;
  const auto program = parse("a(X) <- b(X); c(X) :- d(X).", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(program.clauses.size() == 2);
  REQUIRE(program.clauses[0].body.size() == 1);
  REQUIRE(program.clauses[1].body.size() == 1);
}

TEST_CASE("parser builds lists and arithmetic expressions") {
  DiagnosticSink sink;
  const auto program = parse("список([1,2|T], #1+2*3#).", sink);
  REQUIRE_FALSE(sink.hasErrors());
  const Term& head = program.clauses[0].head;
  REQUIRE(head.kind == TermKind::Compound);
  REQUIRE(head.compound->name == "список");
  REQUIRE(isListCell(head.compound->args[0]));
  const Term& expression = head.compound->args[1];
  REQUIRE(expression.kind == TermKind::Compound);
  REQUIRE(expression.compound->name == "$expr");
}

TEST_CASE("parser records imports") {
  DiagnosticSink sink;
  const auto program = parse(":- ИМПОРТ(\"other.pld\").\nfoo.\n", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(program.imports.size() == 1);
  REQUIRE(program.imports[0].path == "other.pld");
  REQUIRE(program.clauses.size() == 1);
}

TEST_CASE("parser reports syntax errors") {
  SECTION("unterminated string") {
    DiagnosticSink sink;
    parse("foo(bar,\"er).", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().code == ErrorCode::InvalidStringLiteral);
  }
  SECTION("malformed number") {
    DiagnosticSink sink;
    parse("foo(bar,12.123.123).", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().code == ErrorCode::InvalidNumberLiteral);
  }
  SECTION("missing rule arrow") {
    DiagnosticSink sink;
    parse("foo(bar,er):!.", sink);
    REQUIRE(sink.hasErrors());
  }
  SECTION("anonymous variable as a goal") {
    DiagnosticSink sink;
    parse("foo(a):-_.", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().code == ErrorCode::MisplacedUnderscore);
  }
  SECTION("misplaced cut") {
    DiagnosticSink sink;
    parse("foo(bar,er)!., ", sink);
    REQUIRE(sink.hasErrors());
  }
  SECTION("unpaired list bracket") {
    DiagnosticSink sink;
    parse("foo([).", sink);
    REQUIRE(sink.hasErrors());
  }
  SECTION("empty function argument") {
    DiagnosticSink sink;
    parse("foo(bar,).", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().code == ErrorCode::InvalidFunction);
  }
  SECTION("question in the middle") {
    DiagnosticSink sink;
    parse("foo?", sink);
    REQUIRE(sink.hasErrors());
  }
}

TEST_CASE("parser rejects a variable head") {
  DiagnosticSink sink;
  parse("X :- foo.", sink);
  REQUIRE(sink.hasErrors());
}
