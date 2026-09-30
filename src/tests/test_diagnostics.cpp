#include <catch2/catch_test_macros.hpp>

#include <sstream>
#include <string>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"

// task_40: what the interpreter says when something is wrong, with the position
// a reader can act on.  The subject here is the diagnostic itself — its code,
// its severity, its position and its exact text — so the engine's diagnostic
// hook is used instead of the console text, and the queries are not run: parsing
// and loading are enough for every case below.
//
// The expected messages are copied word for word on purpose: this text is a
// user-visible surface (a beginner reads it), and a test that only looked for
// "some message appeared" would not notice it becoming unhelpful.

namespace {

using prologd::Engine;
using prologd::ErrorCode;
using prologd::ModuleLoader;
using prologd::PrologError;
using prologd::Severity;
using prologd::SourceLocation;

/// Load a program and collect the diagnostics the engine reported.
std::vector<PrologError> diagnosticsOf(const std::string& source) {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  Engine engine;
  engine.setStreams(input, output, error);
  engine.initialize();
  std::vector<PrologError> collected;
  engine.setDiagnosticHook([&collected](const PrologError& diagnostic) {
    collected.push_back(diagnostic);
  });
  ModuleLoader loader(engine);
  std::string message;
  (void)loader.loadSource(source, "<test>", &message);
  return collected;
}

std::vector<const PrologError*> withSeverity(const std::vector<PrologError>& diagnostics,
                                             Severity severity) {
  std::vector<const PrologError*> result;
  for (const PrologError& diagnostic : diagnostics) {
    if (diagnostic.severity == severity) {
      result.push_back(&diagnostic);
    }
  }
  return result;
}

}  // namespace

TEST_CASE("an unclosed bracket is reported at the opening bracket") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("факт(1.\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::UnpairedBracket);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.isParseError);
  REQUIRE(error.location.file == "<test>");
  REQUIRE(error.location.line == 1);
  // Byte columns, like everywhere else in the dialect: `факт` is four letters
  // of two bytes each, so the bracket sits in the ninth column.
  REQUIRE(error.location.column == 9);
  REQUIRE(error.message == "непарные скобки: '(' открыта в строке 1");
}

TEST_CASE("a missing final dot is reported at the end of the clause") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("факт(1)\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::InvalidSentence);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 11);  // the `)` the dot belongs after
  REQUIRE(error.message == "предложение не заканчивается точкой");
}

TEST_CASE("an unclosed string points at its opening quote") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ВЫВОД(\"привет).\n");
  const std::vector<const PrologError*> errors = withSeverity(diagnostics, Severity::Error);
  REQUIRE_FALSE(errors.empty());
  const PrologError& error = *errors.front();
  REQUIRE(error.code == ErrorCode::InvalidStringLiteral);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 13);  // the opening `"`
}

TEST_CASE("a reserved name with an arity it does not have is an error") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?УМНОЖЕНИЕ(2, 3).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::WrongArity);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 2);  // the goal, not the `?`
  REQUIRE(error.message == "УМНОЖЕНИЕ не имеет арности 2 (есть 3 и 4)");
}

TEST_CASE("a singleton in a fact is told to use quotes") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("мама(Лена, Таня).\n");
  REQUIRE(diagnostics.size() == 2);
  const PrologError& first = diagnostics[0];
  REQUIRE(first.code == ErrorCode::SingletonVariable);
  REQUIRE(first.severity == Severity::Warning);
  REQUIRE(first.location.line == 1);
  REQUIRE(first.message ==
          "Лена — переменная, а не константа; если имелась в виду константа, "
          "запишите её в одинарных кавычках: 'Лена'");
  REQUIRE(diagnostics[1].message.find("'Таня'") != std::string::npos);
}

TEST_CASE("a singleton in a rule offers the wildcard as well") {
  // In a rule the name can be a forgotten wildcard, so both readings are named.
  const std::vector<PrologError> head = diagnosticsOf("дв(Н, М) :- БОЛЬШЕ(Н, 1).\n");
  REQUIRE(head.size() == 1);
  REQUIRE(head.front().message ==
          "М — переменная, а не константа; если это пропуск, назовите её _М, "
          "а если константа — запишите её в одинарных кавычках: 'М'");

  // A name used once in the body gets the plain advice.
  const std::vector<PrologError> body = diagnosticsOf("дв(Н) :- МЕНЬШЕ(Н, К).\n");
  REQUIRE(body.size() == 1);
  REQUIRE(body.front().message ==
          "переменная К встречается один раз; если это намеренно, назовите её _К");
}

TEST_CASE("deliberately unused names are not reported") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("p(_X, _).\nq(A) :- r(A).\nr(1).\n");
  REQUIRE(diagnostics.empty());
}

TEST_CASE("an undefined predicate is a warning with a suggestion") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("член(а, [а]).\n?члеен(а, [а]).\n");
  const std::vector<const PrologError*> warnings =
      withSeverity(diagnostics, Severity::Warning);
  REQUIRE(warnings.size() == 1);
  const PrologError& warning = *warnings.front();
  REQUIRE(warning.code == ErrorCode::UnknownPredicate);
  REQUIRE(warning.location.line == 2);
  REQUIRE(warning.location.column == 2);
  // The suggestion is measured in code points, so one Cyrillic letter is one
  // edit — `члеен` is `член` with a letter too many.
  REQUIRE(warning.message == "не найдено: члеен/2; возможно, член/2");
}

TEST_CASE("an arity a user predicate does not have lists the ones it has") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("дв(1, 2).\n?дв(1).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& warning = diagnostics.front();
  REQUIRE(warning.severity == Severity::Warning);
  REQUIRE(warning.code == ErrorCode::WrongArity);
  REQUIRE(warning.location.line == 2);
  REQUIRE(warning.message == "дв определён с арностью 2, а вызван с 1");
}

TEST_CASE("the argument of call is checked when it is a literal goal") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ВЫП(члены(Х)).\n");
  REQUIRE(diagnostics.size() == 1);
  REQUIRE(diagnostics.front().message.find("не найдено: члены/1") == 0);
}

TEST_CASE("a program that defines what it calls is silent") {
  // Forward and mutual references are normal Prolog: the warning must wait for
  // the whole unit, or half of every course file would be flagged.
  const std::vector<PrologError> diagnostics = diagnosticsOf(
      "чёт(0).\n"
      "чёт(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), нечёт(Н1).\n"
      "нечёт(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), чёт(Н1).\n"
      "?ТИХО, чёт(2).\n");
  REQUIRE(diagnostics.empty());
}
