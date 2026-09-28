#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("counts clauses by name") {
  const auto result = runProgram(
      "пример(1) :- пример(3).\n"
      "пример(2).\n"
      "?СКОЛЬКО(пример, N).\n"
      "?СКОЛЬКО(пример, 2).\n"
      "?СКОЛЬКО(пример, 3).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "N=2\nДА\nНЕТ\n");
}

TEST_CASE("inspects clauses") {
  const auto result = runProgram(
      "пример(1) :- пример(3).\n"
      "пример(2).\n"
      "?ПРЕДЛ(пример, 1, X, Y).\n"
      "?ПРЕДЛ(пример, 2, X, Y).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=пример(1)\nY=[пример(3)]\nX=пример(2)\nY=[]\n");
}

TEST_CASE("converts between terms and lists") {
  const auto result = runProgram(
      "?ТЕРМ(T, [пример, 1]).\n"
      "?ТЕРМ(пример(1), L).\n"
      "?ТЕРМ(T, [пример]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "T=пример(1)\nL=[пример,1]\nT=пример\n");
}

TEST_CASE("asserts and retracts clauses") {
  const auto result = runProgram(
      "пример(1).\n"
      "?ДОБ(пример(3), [], 1).\n"
      "?пример(X).\n"
      "?УДАЛЕНИЕ(пример, 1).\n"
      "?пример(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nX=3\nX=1\nДА\nX=1\n");
}

TEST_CASE("asserts a rule with a body") {
  const auto result = runProgram(
      "база(1).\n"
      "?ДОБ(удвоить(X, Y), [УМНОЖЕНИЕ(X, 2, Y)], 1).\n"
      "?удвоить(5, Z).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nY=_1\nZ=10\n");
}
