#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("facts answer ground and variable queries") {
  const auto result = runProgram(
      "человек(аня).\n"
      "человек(боря).\n"
      "?человек(аня).\n"
      "?человек(витя).\n"
      "?человек(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nX=аня\nX=боря\n");
}

TEST_CASE("rules and conjunction work") {
  const auto result = runProgram(
      "родитель(аня, боря).\n"
      "родитель(боря, витя).\n"
      "дед(X, Y) :- родитель(X, Z), родитель(Z, Y).\n"
      "?дед(аня, Y).\n"
      "?дед(аня, боря).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Y=витя\nНЕТ\n");
}

TEST_CASE("backtracking enumerates all solutions in order") {
  const auto result = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?член(X, [1,2,3]).\n"
      "?член(2, [1,2,3]).\n"
      "?член(9, [1,2,3]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\nX=2\nX=3\nДА\nНЕТ\n");
}

TEST_CASE("cut commits to the first clause") {
  const auto result = runProgram(
      "фактор(0, 1) :- !.\n"
      "фактор(N, F) :- фактор(#N-1#, X), УМНОЖЕНИЕ(X, N, F).\n"
      "?фактор(7, F).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "F=5040\n");
}

TEST_CASE("meta-call runs the goal") {
  const auto result = runProgram(
      "цель(5).\n"
      "проверка(X) :- ВЫП(цель(X)).\n"
      "?проверка(Y).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Y=5\n");
}

TEST_CASE("negation as failure") {
  const auto result = runProgram(
      "цель(5).\n"
      "нет_цели(X) :- НЕ(цель(X)).\n"
      "?нет_цели(5).\n"
      "?нет_цели(6).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nДА\n");
}

TEST_CASE("disjunction") {
  const auto result = runProgram(
      "a(1).\n"
      "b(2).\n"
      "c(X) :- ИЛИ(a(X), b(X)).\n"
      "?c(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\n");
}

TEST_CASE("undefined predicates fail") {
  const auto result = runProgram("?нет_такого(1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\n");
}

TEST_CASE("deep recursion does not overflow the C++ stack") {
  const auto result = runProgram(
      "счёт(0) :- !.\n"
      "счёт(N) :- счёт(#N-1#).\n"
      "?счёт(50000).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\n");
}

TEST_CASE("quiet suppresses solution output for its query only") {
  const auto result = runProgram(
      "?ТИХО, ВЫВОД(фыв).\n"
      "?ВЫВОД(куц).\n"
      "foo(5).\n"
      "?ТИХО, foo(X).\n"
      "?foo(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "фывкуц\nДА\nX=5\n");
}
