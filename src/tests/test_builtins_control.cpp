#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("the always-false goal fails and negation turns it round") {
  const auto result = runProgram("?ЛОЖЬ.\n?ЛОЖЬ, НЕ(ЛОЖЬ).\n?НЕ(ЛОЖЬ).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nНЕТ\nДА\n");
}

TEST_CASE("negation undoes the bindings of the goal it checks") {
  const auto result = runProgram(
      "?НЕ(ЛОЖЬ).\n"
      "?НЕ(НЕ(ЛОЖЬ)).\n"                      // double negation is negation
      "?НЕ(ПЕР(X)).\n"                        // ПЕР holds for a free X, so this fails
      "?НЕ(ЦЕЛ(X)).\n"                        // ЦЕЛ does not, and X stays free
      "?НЕ(ПЕР(1)).\n"
      "?НЕ((РАВНО(A, 1), ЛОЖЬ)), ПЕР(A).\n"   // the binding of A is gone
      "?НЕ((РАВНО(B, 1), ЛОЖЬ)), РАВНО(B, 2).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nНЕТ\nX=_1\nДА\nA=_1\nB=2\n");
}

TEST_CASE("negation keeps what a goal did to the database") {
  // Bindings are undone, side effects are not: the database is not backtrackable
  // in PrologD, so the clause asserted inside `НЕ` survives the negation.
  const auto result = runProgram("?НЕ(ДОБ(ф(1), [], 1)).\n?ф(1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nДА\n");
}

TEST_CASE("negation answers a goal that is not a predicate with an error") {
  for (const std::string& goal : {"НЕ(5)", "НЕ(X)"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Цель должна быть предикатом") != std::string::npos);
  }

  // An atom is a goal of arity 0: an unknown one simply fails, so НЕ succeeds.
  const auto atom = runProgram("?НЕ(a).\n");
  REQUIRE(atom.loaded);
  REQUIRE_FALSE(atom.runtimeError);
  REQUIRE(atom.output == "ДА\n");

  // A wrong arity, on the other hand, is not this predicate at all: it cannot
  // ever work, and the load says so (task_40).
  const auto arity = runProgram("?НЕ(ЛОЖЬ, ЛОЖЬ).\n");
  REQUIRE_FALSE(arity.loaded);
  REQUIRE(arity.error.find("НЕ не имеет арности 2 (есть 1)") != std::string::npos);
}

TEST_CASE("a disjunction is true when either side is") {
  const auto result = runProgram(
      "?ИЛИ(ЛОЖЬ, НЕ(ЛОЖЬ)).\n"
      "?ИЛИ(НЕ(ЛОЖЬ), ЛОЖЬ).\n"
      "?ИЛИ(ЛОЖЬ, ЛОЖЬ).\n"
      "?ИЛИ(РАВНО(X, 1), РАВНО(X, 2)).\n"
      "?ИЛИ(ЛОЖЬ, РАВНО(Y, 2)).\n"
      "?ИЛИ(РАВНО(A, 1), РАВНО(B, 2)), РАВНО(A, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\nX=1\nY=2\nA=1\nB=_1\n");
}

TEST_CASE("a disjunction leaves only the first solution of the first goal") {
  // Once the first goal has succeeded the second is out of reach, and a
  // generator in the first position yields a single solution.
  const auto both = runProgram("?ИЛИ(РАВНО(X, 1), РАВНО(X, 2)), РАВНО(X, 2).\n");
  REQUIRE(both.loaded);
  REQUIRE(both.output == "НЕТ\n");

  const auto generator = runProgram("п(1).\nп(2).\n?ИЛИ(п(X), ЛОЖЬ).\n");
  REQUIRE(generator.loaded);
  REQUIRE(generator.output == "X=1\n");
}

TEST_CASE("a disjunction answers a goal that is not a predicate with an error") {
  for (const std::string& goal : {"ИЛИ(5, НЕ(ЛОЖЬ))", "ИЛИ(ЛОЖЬ, 5)", "ИЛИ(X, НЕ(ЛОЖЬ))"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Цель должна быть предикатом") != std::string::npos);
  }

  const auto atom = runProgram("?ИЛИ(a, НЕ(ЛОЖЬ)).\n");
  REQUIRE(atom.loaded);
  REQUIRE_FALSE(atom.runtimeError);
  REQUIRE(atom.output == "ДА\n");

  const auto arity = runProgram("?ИЛИ(ЛОЖЬ, ЛОЖЬ, ЛОЖЬ).\n");
  REQUIRE_FALSE(arity.loaded);
  REQUIRE(arity.error.find("ИЛИ не имеет арности 3 (есть 2)") != std::string::npos);
}

TEST_CASE("quiet silences the query it appears in") {
  // Quiet is a per-query flag: the next query reports as usual.  Note that the
  // answer of the silenced query carries neither `ДА` nor the bindings.
  const auto alone = runProgram("?ТИХО.\n?РАВНО(1, 1).\n");
  REQUIRE(alone.loaded);
  REQUIRE(alone.output == "ДА\n");

  const auto withBindings = runProgram("?ТИХО, РАВНО(X, 1).\n?РАВНО(1, 1).\n");
  REQUIRE(withBindings.loaded);
  REQUIRE(withBindings.output == "ДА\n");
}

TEST_CASE("the trace flags turn tracing on and off") {
  // What the trace produces is the business of the trace sink (see
  // `test_stepping.cpp`); here the two goals only have to succeed and leave the
  // query that follows alone.
  const auto result = runProgram("?ТРАССА.\n?НЕТ_ТРАССЫ.\n?РАВНО(X, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "ДА\nДА\nX=1\n");
}
