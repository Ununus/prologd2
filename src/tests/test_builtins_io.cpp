#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <string>
#include <vector>

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

TEST_CASE("the line writer is the writer plus one newline") {
  // The newline comes from the built-in itself, so the next `ВЫВОД` starts a new
  // line without a `ПС` between them — and exactly one line break, not two.
  const auto result = runProgram("?ВЫВОДПС(\"а\", 1), ВЫВОД(\"б\"), ПС.\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "а1\nб\nДА\n");
}

TEST_CASE("the line writer prints arguments exactly as the writer does") {
  // No separator is inserted and the terms are formatted by the same code: a
  // list, an unbound variable and a string are not special-cased here.
  const auto result = runProgram(
      "?ВЫВОДПС(\"без\", \" пробелов\").\n"
      "?ВЫВОДПС(\"Ёё\", [1,2], _).\n"
      "?ВЫВОДПС(1, 2, 3, 4, 5).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "без пробелов\nДА\nЁё[1,2]_1\nДА\n12345\nДА\n");
}

TEST_CASE("writeln is the line writer under its English spelling") {
  const auto result = runProgram("?writeln(\"ок\"), writeln(7).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ок\n7\nДА\n");
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

TEST_CASE("the code writer writes the character of a code point") {
  const auto letter = runProgram("?ВВКОД(1040).\n");
  REQUIRE(letter.loaded);
  REQUIRE(letter.output == "А\nДА\n");

  // The newline character is a code point like any other, and `ПС` is a
  // library clause built on it.
  const auto newline = runProgram("?ВВКОД(10).\n?ВВКОД(1041).\n");
  REQUIRE(newline.loaded);
  REQUIRE(newline.output == "\nДА\nБ\nДА\n");

  // An expression is evaluated first, like everywhere else.
  const auto expression = runProgram("?ВВКОД(#1000+40#).\n");
  REQUIRE(expression.loaded);
  REQUIRE(expression.output == "А\nДА\n");

  const auto maximum = runProgram("?ВВКОД(1114111).\n");
  REQUIRE(maximum.loaded);
  REQUIRE(maximum.output == std::string("\xf4\x8f\xbf\xbf") + "\nДА\n");
}

TEST_CASE("the code writer rejects a code point that is not a Unicode scalar value") {
  // A surrogate or a value past U+10FFFF used to be encoded anyway, into bytes
  // that are not UTF-8 — and the JSON protocol cannot carry those back.
  const std::vector<std::string> cases = {
      "ВВКОД(-1)",       "ВВКОД(1114112)", "ВВКОД(2000000)",
      "ВВКОД(55296)",    // the first surrogate
      "ВВКОД(57343)",    // the last one
      "ВВКОД(a)",        "ВВКОД(\"a\")",  "ВВКОД(1.5)",
  };
  for (const std::string& goal : cases) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("ВВКОД: Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("the code writer reads one code point of input") {
  const auto result = runProgram("?ВВКОД(X).\n?ВВКОД(Y).\n?ВВКОД(Z).\n", "Аб\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1040\nY=1073\nНЕТ\n");

  // The rest of the line stays for the next reader.
  const auto rest = runProgram("?ВВКОД(C).\n?ВВОДСТР(L).\n", "АБВ\n");
  REQUIRE(rest.loaded);
  REQUIRE(rest.output == "C=1040\nL=БВ\n");
}

TEST_CASE("reading a number compares it when the argument is bound") {
  const auto result = runProgram(
      "?ВВОДЦЕЛ(42).\n"
      "?ВВОДЦЕЛ(41).\n"
      "?ВВОДВЕЩ(2.5).\n"
      "?ВВОДВЕЩ(2.6).\n",
      "42 42 2.5 2.5\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nДА\nНЕТ\n");

  // Text compares as text, and an atom matches a string.
  const auto text = runProgram("?ВВОДСИМВ(привет).\n?ВВОДСИМВ(\"привет\").\n?ВВОДСИМВ(нет).\n",
                               "привет привет привет\n");
  REQUIRE(text.loaded);
  REQUIRE(text.output == "ДА\nДА\nНЕТ\n");
}

TEST_CASE("reading refuses a bound argument of the wrong type") {
  struct Case {
    std::string goal;
    std::string predicate;
    std::string input;
  };
  const std::vector<Case> cases = {
      {"ВВОДЦЕЛ(2.5)", "ВВОДЦЕЛ", "2"},   {"ВВОДЦЕЛ(a)", "ВВОДЦЕЛ", "2"},
      {"ВВОДВЕЩ(2)", "ВВОДВЕЩ", "2"},     {"ВВОДСИМВ(5)", "ВВОДСИМВ", "ок"},
      {"ВВОДСТР(5)", "ВВОДСТР", "строка"},
  };
  for (const Case& item : cases) {
    const auto result = runProgram("? " + item.goal + ".\n", item.input);
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find(item.predicate + ": Недопустимый тип аргументов") !=
            std::string::npos);
  }
}

TEST_CASE("a read that cannot parse what it got fails") {
  // The token is consumed either way: the next read takes the next one.
  const auto token = runProgram("?ВВОДЦЕЛ(X).\n?ВВОДЦЕЛ(X).\n", "abc 5\n");
  REQUIRE(token.loaded);
  REQUIRE(token.output == "НЕТ\nX=5\n");

  const auto notWhole = runProgram("?ВВОДЦЕЛ(X).\n", "2.5\n");
  REQUIRE(notWhole.loaded);
  REQUIRE(notWhole.output == "НЕТ\n");

  const auto trailing = runProgram("?ВВОДВЕЩ(X).\n", "1.5x\n");
  REQUIRE(trailing.loaded);
  REQUIRE(trailing.output == "НЕТ\n");

  // Nothing left to read at all.
  const auto empty = runProgram("?ВВОДЦЕЛ(X).\n?ВВОДВЕЩ(X).\n?ВВОДСИМВ(X).\n?ВВОДСТР(X).\n");
  REQUIRE(empty.loaded);
  REQUIRE(empty.output == "НЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("a whole line is read as it is, an empty one included") {
  const auto lines = runProgram("?ВВОДСТР(L).\n?ВВОДСТР(L).\n", "первая строка\nвторая\n");
  REQUIRE(lines.loaded);
  REQUIRE(lines.output == "L=первая строка\nL=вторая\n");

  const auto blank = runProgram("?ВВОДСТР(L).\n", "\n");
  REQUIRE(blank.loaded);
  REQUIRE(blank.output == "L=\n");

  // A last line without a newline is still a line.
  const auto unterminated = runProgram("?ВВОДСТР(L).\n", "без перевода строки");
  REQUIRE(unterminated.loaded);
  REQUIRE(unterminated.output == "L=без перевода строки\n");
}

TEST_CASE("a token read leaves the rest of its line") {
  const auto tokens = runProgram("?ВВОДСИМВ(S).\n?ВВОДСИМВ(T).\n", "  один   два \n");
  REQUIRE(tokens.loaded);
  REQUIRE(tokens.output == "S=один\nT=два\n");

  const auto tokenThenLine = runProgram("?ВВОДСИМВ(S).\n?ВВОДСТР(L).\n",
                                        "имя остаток строки\n");
  REQUIRE(tokenThenLine.loaded);
  REQUIRE(tokenThenLine.output == "S=имя\nL= остаток строки\n");

  const auto lineThenToken = runProgram("?ВВОДСТР(L).\n?ВВОДСИМВ(S).\n",
                                        "целая строка\nтокен остаток\n");
  REQUIRE(lineThenToken.loaded);
  REQUIRE(lineThenToken.output == "L=целая строка\nS=токен\n");
}

TEST_CASE("the prompt of a read is written before the read") {
  const auto integer = runProgram("?ВВОДЦЕЛ(X, \"Число: \").\n", "7\n");
  REQUIRE(integer.loaded);
  REQUIRE(integer.output == "Число: X=7\n");

  const auto compared = runProgram("?ВВОДЦЕЛ(7, \"> \").\n", "7\n");
  REQUIRE(compared.loaded);
  REQUIRE(compared.output == "> \nДА\n");

  const auto line = runProgram("?ВВОДСТР(X, \"Строка: \").\n", "текст\n");
  REQUIRE(line.loaded);
  REQUIRE(line.output == "Строка: X=текст\n");

  // The prompt is written even when there is nothing left to read.
  const auto nothing = runProgram("?ВВОДЦЕЛ(X, \"Число: \").\n");
  REQUIRE(nothing.loaded);
  REQUIRE(nothing.output == "Число: \nНЕТ\n");

  // Without a prompt nothing is written, and a prompt that is not text is an
  // error like any other wrong argument.
  const auto plain = runProgram("?ВВОДЦЕЛ(X).\n", "7\n");
  REQUIRE(plain.loaded);
  REQUIRE(plain.output == "X=7\n");

  for (const std::string& goal : {"ВВОДЦЕЛ(X, P)", "ВВОДЦЕЛ(X, 5)", "ВВОДСТР(X, P)",
                                  "ВВОДСИМВ(X, P)", "ВВОДВЕЩ(X, 5)"}) {
    const auto result = runProgram("? " + goal + ".\n", "7\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("the stream built-ins report the current stream, or fail") {
  // A free argument asks for the name of the stream that is open now: the
  // standard streams have no name.
  const auto names = runProgram("?ЧТЕНИЕ_ИЗ(X).\n?ЗАПИСЬ_В(Y).\n");
  REQUIRE(names.loaded);
  REQUIRE(names.output == "X=\nY=\n");

  // A file that cannot be opened is a failure, not an error; a stream name that
  // is not text is an error.
  const auto missing = runProgram("?ЧТЕНИЕ_ИЗ(\"нет_такого_файла.txt\").\n");
  REQUIRE(missing.loaded);
  REQUIRE_FALSE(missing.runtimeError);
  REQUIRE(missing.output == "НЕТ\n");

  const auto directory = runProgram("?ЗАПИСЬ_В(\"нет_такого_каталога/файл.txt\").\n");
  REQUIRE(directory.loaded);
  REQUIRE_FALSE(directory.runtimeError);
  REQUIRE(directory.output == "НЕТ\n");

  for (const std::string& goal : {"ЧТЕНИЕ_ИЗ(5)", "ЗАПИСЬ_В(5)"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Недопустимый тип аргументов") != std::string::npos);
  }
}
