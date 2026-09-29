#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("findall collects the required example") {
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

TEST_CASE("findall enumerates a goal in order") {
  const auto result = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?НАЙТИВСЁ(X, член(X, [1,2,3]), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[1,2,3]\n");
}

TEST_CASE("findall yields an empty list when the goal fails") {
  const auto result = runProgram(
      "?НАЙТИВСЁ(X, ЛОЖЬ, L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[]\n");
}

TEST_CASE("findall does not leak bindings") {
  const auto result = runProgram(
      "значение(1).\n"
      "значение(2).\n"
      "?РАВНО(Z, 0), НАЙТИВСЁ(X, значение(X), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Z=0\nX=_1\nL=[1,2]\n");
}

TEST_CASE("findall copies template variables") {
  const auto result = runProgram(
      "значение(1).\n"
      "значение(2).\n"
      "?НАЙТИВСЁ([X, Y], значение(X), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nY=_1\nL=[[1,_1],[2,_2]]\n");
}

TEST_CASE("findall copies, so the collected list shares no variable") {
  // The element of the list is a copy of the template: binding it later leaves
  // the query's own `X` free, and binding `X` later leaves the list alone.
  const auto result = runProgram(
      "?НАЙТИВСЁ(X, НЕ(ЛОЖЬ), L), РАВНО(L, [1]), ПЕР(X).\n"
      "?НАЙТИВСЁ(X, НЕ(ЛОЖЬ), L), РАВНО(X, 5).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[1]\nX=5\nL=[_1]\n");
}

TEST_CASE("findall matches the list it is given") {
  // The collected list is unified with the third argument, so a bound one has
  // to agree with it: one solution collected is `[_1]`, not `[]`.
  const auto result = runProgram(
      "?НАЙТИВСЁ(X, НЕ(ЛОЖЬ), [1]).\n"
      "?НАЙТИВСЁ(X, НЕ(ЛОЖЬ), []).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nНЕТ\n");
}

TEST_CASE("findall takes a template that is not a variable") {
  const auto result = runProgram(
      "?НАЙТИВСЁ(f(X), НЕ(ЛОЖЬ), L).\n"
      "?НАЙТИВСЁ(X, НАЙТИВСЁ(Y, НЕ(ЛОЖЬ), [Y]), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nL=[f(_1)]\nX=_1\nY=_1\nL=[_1]\n");
}

TEST_CASE("findall reports an error raised by the goal") {
  const auto result = runProgram("?НАЙТИВСЁ(X, ЦЕЛВЕЩ(\"а\", X), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("ЦЕЛВЕЩ: Недопустимый тип аргументов") != std::string::npos);
}
