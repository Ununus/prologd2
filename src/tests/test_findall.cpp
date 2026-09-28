#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("НАЙТИВСЁ collects the teacher's example") {
  const auto result = runProgram(
      "студент(вова, корчагин).\n"
      "студент(данил, ахмеров).\n"
      "студент(ваня, петров).\n"
      "?НАЙТИВСЁ(И, студент(И, Ф), А).\n"
      "?НАЙТИВСЁ([И, Ф], студент(И, Ф), А).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "И=_1\n"
          "Ф=_1\n"
          "А=[вова,данил,ваня]\n"
          "И=_1\n"
          "Ф=_1\n"
          "А=[[вова,корчагин],[данил,ахмеров],[ваня,петров]]\n");
}

TEST_CASE("НАЙТИВСЁ enumerates a goal in order") {
  const auto result = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?НАЙТИВСЁ(X, член(X, [1,2,3]), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[1,2,3]\n");
}

TEST_CASE("НАЙТИВСЁ yields an empty list when the goal fails") {
  const auto result = runProgram(
      "?НАЙТИВСЁ(X, ЛОЖЬ, L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[]\n");
}

TEST_CASE("НАЙТИВСЁ does not leak bindings") {
  const auto result = runProgram(
      "значение(1).\n"
      "значение(2).\n"
      "?РАВНО(Z, 0), НАЙТИВСЁ(X, значение(X), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Z=0\nX=_1\nL=[1,2]\n");
}

TEST_CASE("НАЙТИВСЁ copies template variables") {
  const auto result = runProgram(
      "значение(1).\n"
      "значение(2).\n"
      "?НАЙТИВСЁ([X, Y], значение(X), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nY=_1\nL=[[1,_1],[2,_2]]\n");
}
