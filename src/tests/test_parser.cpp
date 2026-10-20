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
    // `;` is right-nested, as in ISO (task_85).  For a chain of plain
    // disjunctions the shape changes nothing, but with an if-then in a branch it
    // is the `else` of the pair above that names the whole rest of the chain.
    REQUIRE(bodyOf(program) == ";(a,;(,(b,c),d))");
  }
  {
    // `->` binds looser than `,` and tighter than `;` (task_85): the condition of
    // `a, b -> c` is the conjunction, and the `else` of `a -> b ; c` is `c`.
    DiagnosticSink sink;
    const auto program = parse("p :- a, b -> c ; d.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(->(,(a,b),c),d)");
  }
  {
    // Both operators are right-nested, so the `else` of the first pair is the
    // whole rest of the chain — `a -> b ; c -> d ; e`:
    DiagnosticSink sink;
    const auto program = parse("p :- a -> b ; c -> d ; e.", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == ";(->(a,b),;(->(c,d),e))");
  }
  {
    // A parenthesised if-then is a goal, the way a parenthesised disjunction is:
    DiagnosticSink sink;
    const auto program = parse("p :- ВЫП((a -> b)).", sink);
    REQUIRE_FALSE(sink.hasErrors());
    REQUIRE(bodyOf(program) == "ВЫП(->(a,b))");
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

TEST_CASE("the arithmetic signs take expressions written without hash marks") {
  // task_92: `is`, `=:=` and `=\=` are ISO signs, and their operands are
  // arithmetic expressions — `X is 2 + 3` is the marked `РАВНО(X, #2 + 3#)`.
  // Until this round the dialect answered them with advice instead of a goal.
  {
    DiagnosticSink sink;
    const auto program = parse("p :- X is 2 + 3.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == "РАВНО");
    REQUIRE(goal.compound->args.size() == 2);
    REQUIRE(goal.compound->args[1].compound->name == kExpressionFunctor);
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- 1 + 1 =:= 2.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == "РАВНО");
    // Both sides are expressions: the left one is wrapped here, the right one by
    // the arithmetic parser.
    REQUIRE(goal.compound->args[0].compound->name == kExpressionFunctor);
    REQUIRE(goal.compound->args[1].compound->name == kExpressionFunctor);
  }
  {
    DiagnosticSink sink;
    const auto program = parse("p :- 2 =\\= 1 + 1.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == "НЕ");
    REQUIRE(goal.compound->args[0].compound->name == "РАВНО");
  }
  {
    // `\=` is «не унифицируется», the same negation the sign `=<` uses.
    DiagnosticSink sink;
    const auto program = parse("p :- X \\= 1.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == "НЕ");
    REQUIRE(goal.compound->args[0].compound->name == "РАВНО");
  }
  // A name that merely reads `is` is still a name: `is(X, Y)` is an ordinary
  // compound, and the sign only stands between two terms.
  {
    DiagnosticSink sink;
    const auto program = parse("p :- is(X, Y).\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == "is");
    REQUIRE(goal.compound->args.size() == 2);
  }
}

TEST_CASE("an ISO module directive is refused before it can confuse") {
  // `:- module(м, [факт/1]).` — the export list is not parseable here (`факт/1`
  // needs `/` as an operator of terms), and the ordinary path answered
  // «непарные скобки» about brackets that are perfectly matched.  Stage 4 of
  // task_82: one message, and it names the construct.
  DiagnosticSink sink;
  parse(":- module(м, [факт/1]).\n", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().size() == 1);
  REQUIRE(sink.diagnostics().front().message.find("«:- module(…)» в Пролог-Д нет") !=
          std::string::npos);
}

TEST_CASE("ISO rationals are not read as a lost dot") {
  // `1 rdiv 3` stops right before `rdiv`, because `rdiv` is an ordinary name to
  // this grammar: the statement looks complete one token early.  The message
  // has to name the rationals, not a missing dot.
  DiagnosticSink sink;
  parse("?X = 1 rdiv 3.\n", sink);
  REQUIRE(sink.hasErrors());
  REQUIRE(sink.diagnostics().size() == 1);
  REQUIRE(sink.diagnostics().front().message.find("рациональных чисел") !=
          std::string::npos);
}

TEST_CASE("a `;` where the dialect used to accept one is an error") {
  SECTION("as a sentence terminator") {
    DiagnosticSink sink;
    const auto program = parse("a(1);", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(program.clauses.empty());
    const std::string message = sink.diagnostics().front().message;
    REQUIRE(message == "«;» — дизъюнкция; предложение должно заканчиваться точкой");
  }
  SECTION("after a body, before the end") {
    DiagnosticSink sink;
    parse("a(1) :- b(1);", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "«;» — дизъюнкция; предложение должно заканчиваться точкой");
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

TEST_CASE("a statement that lost its dot is told where the dot belongs") {
  SECTION("a fact written before the next one") {
    DiagnosticSink sink;
    parse("студент(вова, корчагин)\nстудент(данил, ахмеров).\n", sink);
    REQUIRE(sink.hasErrors());
    const PrologError& error = sink.diagnostics().front();
    REQUIRE(error.code == ErrorCode::InvalidSentence);
    REQUIRE(error.message == "предложение должно заканчиваться точкой");
    // The end of the first line, where the dot belongs: `студент(вова, корчагин)`
    // is 41 bytes long, so the `)` sits in the 42nd column (columns count bytes).
    REQUIRE(error.location.line == 1);
    REQUIRE(error.location.column == 42);
  }
  SECTION("a rule written before a fact") {
    DiagnosticSink sink;
    parse("a(X) :- b(X)\na(2).\n", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "предложение должно заканчиваться точкой");
  }
  SECTION("a query written before a fact") {
    DiagnosticSink sink;
    parse("?- a(1)\nb(2).\n", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message ==
            "предложение должно заканчиваться точкой");
  }
  SECTION("a dot ends every statement") {
    DiagnosticSink sink;
    parse("a(1).\nb(2).\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
  }
  SECTION("what cannot begin a statement keeps the generic wording") {
    DiagnosticSink sink;
    parse("a(1), b(2).\n", sink);
    REQUIRE(sink.hasErrors());
    REQUIRE(sink.diagnostics().front().message == "ошибка при разборе предложения");
  }
}

TEST_CASE("the comparison signs are sugar over the built-ins") {
  SECTION("`=` is РАВНО/2") {
    DiagnosticSink sink;
    const auto program = parse("верно(X) :- X = 1.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.kind == TermKind::Compound);
    REQUIRE(goal.compound->name == "РАВНО");
    REQUIRE(goal.compound->args.size() == 2);
  }
  SECTION("the comparisons are МЕНЬШЕ/БОЛЬШЕ, `>=` and `=<` their negation") {
    const struct {
      std::string source;
      std::string functor;
      bool negated;
    } rows[] = {{"p :- X < 1.", "МЕНЬШЕ", false},
               {"p :- X > 1.", "БОЛЬШЕ", false},
               {"p :- X =< 1.", "БОЛЬШЕ", true},
               {"p :- X >= 1.", "МЕНЬШЕ", true}};
    for (const auto& row : rows) {
      INFO("source: " << row.source);
      DiagnosticSink sink;
      const auto program = parse(row.source, sink);
      REQUIRE_FALSE(sink.hasErrors());
      const Term& goal = program.clauses[0].body[0];
      REQUIRE(goal.kind == TermKind::Compound);
      if (row.negated) {
        REQUIRE(goal.compound->name == "НЕ");
        REQUIRE(goal.compound->args[0].compound->name == row.functor);
      } else {
        REQUIRE(goal.compound->name == row.functor);
      }
    }
  }
  SECTION("the signs work wherever a term does") {
    // The layer sits in `parseTerm`, so a negation, a goal argument, a list
    // element and an arithmetic operand all take one.
    DiagnosticSink sink;
    const auto program =
        parse("p :- НЕ(X = 1), q([A = B]), r(#1 + 1# = 2), ВЫП((X >= 0)).\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const std::vector<Term>& body = program.clauses[0].body;
    REQUIRE(body.size() == 4);
    REQUIRE(body[0].compound->args[0].compound->name == "РАВНО");
    REQUIRE(body[1].compound->args[0].compound->args[0].compound->name == "РАВНО");
    // `r(#1 + 1# = 2)`: the argument is `РАВНО(#expr(1 + 1), 2)`.
    const Term& argument = body[2].compound->args[0];
    REQUIRE(argument.compound->name == "РАВНО");
    REQUIRE(argument.compound->args[0].compound->name == kExpressionFunctor);
    REQUIRE(body[3].compound->name == "ВЫП");
  }
  SECTION("`,` and `;` still bind looser") {
    DiagnosticSink sink;
    const auto program = parse("p :- X = 1, Y = 2 ; Z = 3.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const Term& goal = program.clauses[0].body[0];
    REQUIRE(goal.compound->name == ";");
    REQUIRE(goal.compound->args[0].compound->name == ",");
  }
  SECTION("the four at-signs are compare with the answer given") {
    // task_90: `A @< B` is `compare(<, A, B)`, and the two «or equal» rows are
    // that call under `НЕ`, exactly like `=<` and `>=` above.
    const struct {
      std::string source;
      bool negated;
      std::string order;
    } rows[] = {{"p :- X @< 1.", false, "<"},
               {"p :- X @> 1.", false, ">"},
               {"p :- X @=< 1.", true, ">"},
               {"p :- X @>= 1.", true, "<"}};
    for (const auto& row : rows) {
      INFO("source: " << row.source);
      DiagnosticSink sink;
      const auto program = parse(row.source, sink);
      REQUIRE_FALSE(sink.hasErrors());
      const Term& goal = program.clauses[0].body[0];
      const Term& call = row.negated ? goal.compound->args[0] : goal;
      if (row.negated) {
        REQUIRE(goal.compound->name == "НЕ");
      }
      REQUIRE(call.compound->name == "compare");
      REQUIRE(call.compound->args.size() == 3);
      REQUIRE(call.compound->args[0].text == row.order);
    }
  }
  SECTION("a sign where a term is expected is the atom of the sign") {
    // `compare(<, A, B)` and `Порядок = <` are how ISO reads the answer of
    // `compare/3`; the same tokens are still infix after a term.
    DiagnosticSink sink;
    const auto program = parse("p :- compare(<, A, B), C = @>=.\n", sink);
    REQUIRE_FALSE(sink.hasErrors());
    const std::vector<Term>& body = program.clauses[0].body;
    REQUIRE(body[0].compound->name == "compare");
    REQUIRE(body[0].compound->args[0].kind == TermKind::Atom);
    REQUIRE(body[0].compound->args[0].text == "<");
    REQUIRE(body[1].compound->name == "РАВНО");
    REQUIRE(body[1].compound->args[1].text == "@>=");
  }
  SECTION("a chain is an error at the second sign") {
    DiagnosticSink sink;
    parse("p :- X = Y = 1.\n", sink);
    REQUIRE(sink.hasErrors());
    const PrologError& error = sink.diagnostics().front();
    REQUIRE(error.code == ErrorCode::InvalidSentence);
    REQUIRE(error.message ==
            "«=» — не цепочка: разбейте на два сравнения, «A = B, B = C»");
    REQUIRE(error.location.column == 12);  // the second `=`
    // A mixed chain quotes the sign the position points at — the second one —
    // and each half of the suggestion keeps the sign it was written with.
    DiagnosticSink mixed;
    parse("p :- X = Y < 1.\n", mixed);
    REQUIRE(mixed.hasErrors());
    REQUIRE(mixed.diagnostics().front().message ==
            "«<» — не цепочка: разбейте на два сравнения, «A = B, B < C»");
    DiagnosticSink chained;
    parse("p :- X @< Y @< Z.\n", chained);
    REQUIRE(chained.hasErrors());
    REQUIRE(chained.diagnostics().front().message ==
            "«@<» — не цепочка: разбейте на два сравнения, «A @< B, B @< C»");
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
  REQUIRE(expression.compound->name == kExpressionFunctor);
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
