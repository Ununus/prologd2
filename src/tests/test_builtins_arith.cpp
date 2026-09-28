#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("СЛОЖЕНИЕ is reversible") {
  const auto result = runProgram(
      "?СЛОЖЕНИЕ(100, 100, A).\n"
      "?СЛОЖЕНИЕ(100, A, 100).\n"
      "?СЛОЖЕНИЕ(A, 50, 100).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "A=200\nA=0\nA=50\n");
}

TEST_CASE("УМНОЖЕНИЕ/4 implements the documented reversible cases") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(10, 2, 2, 22).\n"
      "?УМНОЖЕНИЕ(10, 2, 2, A).\n"
      "?УМНОЖЕНИЕ(10, 2, A, 22).\n"
      "?УМНОЖЕНИЕ(10, A, 2, 22).\n"
      "?УМНОЖЕНИЕ(A, 2, 2, 22).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nA=22\nA=2\nA=2\nA=10\n");
}

TEST_CASE("УМНОЖЕНИЕ/3 divides with remainder detection") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(5, 7, X).\n"
      "?УМНОЖЕНИЕ(X, 7, 35).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=35\nX=5\n");
}

TEST_CASE("БОЛЬШЕ compares numbers and text") {
  const auto result = runProgram(
      "?БОЛЬШЕ(5, 3).\n"
      "?БОЛЬШЕ(3, 5).\n"
      "?БОЛЬШЕ(2.5, 2).\n"
      "?БОЛЬШЕ(\"б\", \"а\").\n"
      "?МЕНЬШЕ(3, 5).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nДА\nДА\nДА\n");
}

TEST_CASE("ABS and SQRT") {
  const auto result = runProgram(
      "?ABS(-5, X).\n"
      "?ABS(5, 5).\n"
      "?SQRT(9, X).\n"
      "?SQRT(X, 4).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=5\nДА\nX=3\nX=16\n");
}

TEST_CASE("arithmetic expressions evaluate with precedence") {
  const auto result = runProgram(
      "?РАВНО(X, #2+2*2+(2+2)*2#).\n"
      "?РАВНО(X, #3.3+3.3#).\n"
      "?РАВНО(#3.3+3.3#, 6.6).\n"
      "?РАВНО(X, #-1*5#).\n"
      "?РАВНО(X, #10 div 3#).\n"
      "?РАВНО(X, #10 mod 3#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=14\nX=6.6\nДА\nX=-5\nX=3\nX=1\n");
}

TEST_CASE("division by zero is a runtime error") {
  const auto result = runProgram("?РАВНО(X, #1/0#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.error.find("деление на ноль") != std::string::npos);
}

TEST_CASE("long arithmetic") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(123456789123456789123456789,123456789123456789123456789,0,Ч).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "Ч=15241578780673678546105778281054720515622620750190521\n");
}

TEST_CASE("ЦЕЛВЕЩ, СТРЦЕЛ, СТРВЕЩ conversions") {
  const auto result = runProgram(
      "?ЦЕЛВЕЩ(3, X).\n"
      "?ЦЕЛВЕЩ(X, 3.7).\n"
      "?СТРЦЕЛ(\"42\", K).\n"
      "?СТРЦЕЛ(gamma, K).\n"
      "?СТРВЕЩ(\"3.14\", K).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3.0\nX=3\nK=42\nНЕТ\nK=3.14\n");
}
