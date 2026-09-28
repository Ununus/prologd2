#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("concatenates and splits") {
  const auto result = runProgram(
      "?СЦЕП(\"аб\", \"вг\", X).\n"
      "?СЦЕП(X, \"бвг\", \"-абвг\").\n"
      "?СЦЕП(\"аб\", X, \"абвг\").\n"
      "?СЦЕП(\"аб\", \"вг\", \"абвг\").\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=абвг\nX=-а\nX=вг\nДА\n");
}

TEST_CASE("extracts and searches substrings") {
  const auto result = runProgram(
      "?КОПИЯ(\"ПРОЛОГ\", X, Y, \"ЛОГ\").\n"
      "?КОПИЯ(\"ПРОЛОГ\", X, 1, \"О\").\n"
      "?КОПИЯ(\"ПРОЛОГ\", X, -1, \"О\").\n"
      "?КОПИЯ(\"ПРОЛОГ\", 2, 3, X).\n"
      "?КОПИЯ(\"ПРОЛОГ\", 1, 3, \"ПРО\").\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=4\nY=3\nX=3\nX=5\nX=РОЛ\nДА\n");
}

TEST_CASE("measures strings") {
  const auto result = runProgram(
      "?ДЛИНА(\"ПРОЛОГ\", X).\n"
      "?ДЛИНА(\"ПРОЛОГ\", 6).\n"
      "?ДЛИНА(\"ПРОЛОГ\", 5).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=6\nДА\nНЕТ\n");
}

TEST_CASE("locates letters and digits") {
  const auto result = runProgram(
      "?БУКВА(\"абв\", 1).\n"
      "?БУКВА(\"25689\", 5).\n"
      "?БУКВА(\" абв \", X).\n"
      "?ЦИФРА(\"абв01\", X).\n"
      "?ЦИФРА(\"25689\", 5).\n"
      "?ЦИФРА(\"абв\", X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nX=2\nX=4\nДА\nНЕТ\n");
}

TEST_CASE("string positions are code points, not bytes") {
  const auto result = runProgram(
      "?ДЛИНА(\"ёжик\", X).\n"
      "?КОПИЯ(\"ёжик\", X, 1, \"ж\").\n"
      "?СЦЕП(\"ё\", \"ж\", X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=4\nX=2\nX=ёж\n");
}
