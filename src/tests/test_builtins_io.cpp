#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("output writes terms without a newline") {
  const auto result = runProgram("?ВЫВОД(1, 2, 3).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "123\nДА\n");
}

TEST_CASE("output prints strings unquoted and lists") {
  const auto result = runProgram("?ВЫВОД(\"Ёё\", [1,2]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Ёё[1,2]\nДА\n");
}

TEST_CASE("writes a newline") {
  const auto result = runProgram("?ВЫВОД(а), ПС, ВЫВОД(б).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "а\nб\nДА\n");
}

TEST_CASE("reads integers") {
  const auto result = runProgram(
      "?ВВОДЦЕЛ(2).\n"
      "?ВВОДЦЕЛ(3).\n"
      "?ВВОДЦЕЛ(F).\n"
      "?ВВОДЦЕЛ(_).\n",
      "2 2 7 9\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nF=7\nДА\n");
}

TEST_CASE("reads floats") {
  const auto result = runProgram("?ВВОДВЕЩ(X).\n?ВВОДВЕЩ(2.5).\n", "3.5 2.5\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3.5\nДА\n");
}

TEST_CASE("reads tokens and lines") {
  const auto result = runProgram(
      "?ВВОДСИМВ(S).\n"
      "?ВВОДСТР(L).\n",
      "привет\nмир\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "S=привет\nL=мир\n");
}

TEST_CASE("file write and read round-trip") {
  const auto path = (std::filesystem::temp_directory_path() / "prologd_io_test.txt").string();
  const std::string source = ":- ЗАПИСЬ_В(\"" + path + "\").\n" +
                             ":- ВЫВОД(\"данные\").\n" +
                             ":- ЗАПИСЬ_В(\"\").\n" +
                             ":- ЧТЕНИЕ_ИЗ(\"" + path + "\").\n" +
                             "?ВВОДСТР(X).\n" +
                             ":- ЧТЕНИЕ_ИЗ(\"\").\n";
  const auto result = runProgram(source);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=данные\n");
}
