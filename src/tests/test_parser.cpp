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

/// Renders a goal term as `name(args)`, so a test can say what the parser built
/// without walking the tree by hand.
std::string goalText(const Term& term) {
  if (term.kind == TermKind::Atom) {
    return term.text;
  }
  if (term.kind != TermKind::Compound || term.compound == nullptr) {
    return "?";
  }
  std::string text = term.compound->name + '(';
  for (std::size_t i = 0; i < term.compound->args.size(); ++i) {
    if (i != 0) {
      text += ',';
    }
    text += goalText(term.compound->args[i]);
  }
  return text + ')';
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

TEST_CASE("parser accepts both rule arrows") {
  DiagnosticSink sink;
  const auto program = parse("a(X) <- b(X). c(X) :- d(X).", sink);
  REQUIRE_FALSE(sink.hasErrors());
  REQUIRE(program.clauses.size() == 2);
  REQUIRE(program.clauses[0].body.size() == 1);
  REQUIRE(program.clauses[1].body.size() == 1);
}

TEST_CASE("a disjunction is one goal and `,` binds tighter") {
  // `;` is the disjunction of ISO (task_41) and `,` binds tighter, so the body
  // of a clause is one goal whatever the mix of the two.
  const auto bodyOf = [](const ParsedProgram& program) {
    REQUIRE(program.clauses.size() == 1);
    REQUIRE(program.clauses[0].body.size() == 1);
    return goalText(program.clauses[0].body[0]);
  };
  {
    DiagnosticSink sink;
    const auto program = parse("p :- a ; b.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(a,b)");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- a, b ; c.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(,(a,b),c)");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- a ; b, c.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(a,,(b,c))");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- a ; b, c ; d.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(;(a,,(b,c)),d)");
  }
  {
    // A parenthesised disjunction followed by a comma stays a flat conjunction:
    // a body is a list of goals, and `(a ; b)` is one of them.  The `,`/2
    // compound appears only when a conjunction is passed as an argument.
    DiagnosticSink sink;
    const auto program = parse("p :- (a ; b), c.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(program.clauses.size() == 1);
    REQUIRE(program.clauses[0].body.size() == 2);
    REQUIRE(goalText(program.clauses[0].body[0]) == ";(a,b)");
    REQUIRE(goalText(program.clauses[0].body[1]) == "c");
  }
  {
    // A parenthesised disjunction is a goal argument, the way a parenthesised
    // conjunction already is for НАЙТИВСЕ.
    DiagnosticSink sink;
    const auto program = parse("p :- ВЫП((a ; b)).", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == "ВЫП(;(a,b))");
  }
}

TEST_CASE("a cut cannot be written inside a meta-call's argument") {
  // Аргумент `ВЫП` — терм, а `!` допустим только на месте цели: парсер
  // отказывает с «неверное использование "!"».  Прозрачность отсечения для
  // `ВЫП` остаётся свойством движка (goal идёт в области отсечения вызова), но
  // из исходного текста такое отсечение не написать (task_43).
  DiagnosticSink sink;
  const auto program = parse("?ВЫП((!, ЛОЖЬ)).", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().code == ErrorCode::MisplacedCut);
  (void)program;
}

TEST_CASE("`\\+` is ISO's spelling of the same negation") {
  // `\+ Ц` is the goal `НЕ(Ц)` (task_55).  It is a prefix at the term level, so
  // `,` and `;` bind looser — `\+ A, B` is `(\+ A), B` — and the brackets of
  // `\+ (A, B)` are the same brackets `НЕ((A, B))` needs.
  {
    DiagnosticSink sink;
    const auto program = parse("p :- \\+ q.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(goalText(program.clauses[0].body[0]) == "НЕ(q)");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- \\+ q, r.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(program.clauses[0].body.size() == 2);
    REQUIRE(goalText(program.clauses[0].body[0]) == "НЕ(q)");
    REQUIRE(goalText(program.clauses[0].body[1]) == "r");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- \\+ (q, r).\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(goalText(program.clauses[0].body[0]) == "НЕ(,(q,r))");
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- \\+ \\+ q.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(goalText(program.clauses[0].body[0]) == "НЕ(НЕ(q))");
  }
}

TEST_CASE("an ISO infix `is` says what to write instead") {
  // `X is 2+3` is how a reader of ISO Prolog evaluates an expression, and the
  // dialect has no `is`: the message names `#…#` and the goal that takes it
  // (task_55).  Without it the only reading given is «Цель не может быть
  // переменной», which says nothing about the mistake.
  DiagnosticSink sink;
  const auto program = parse("?X is 2+3.\n", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().front().message ==
          "«is» — не оператор: выражение помечают «#…#», например «РАВНО(X, #2+3#)»");
  (void)program;
}

TEST_CASE("a `;` where the dialect used to accept one is an error") {
  SECTION("as a sentence terminator") {
    DiagnosticSink sink;
    const auto program = parse("a(1);", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(program.clauses.empty());
    const std::string message = sink.diagnostics().front().message;
    REQUIRE(message == "«;» — дизъюнкция; предложение не заканчивается точкой");
  }
  SECTION("after a body, before the end") {
    DiagnosticSink sink;
    parse("a(1) :- b(1);", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "«;» — дизъюнкция; предложение не заканчивается точкой");
  }
  SECTION("in a list") {
    DiagnosticSink sink;
    parse("p([a ; b]).", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "«;» — дизъюнкция; элементы списка разделяются запятой");
  }
  SECTION("in an argument list without parentheses") {
    DiagnosticSink sink;
    parse("p :- f(a ; b).", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "«;» — дизъюнкция; заключите её в скобки: (A ; B)");
  }
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
