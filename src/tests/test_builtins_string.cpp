#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

namespace {

/// A type error is a runtime error, not a failure: the program stops, and the
/// message names the predicate.  `badArguments` is the one place that decides it,
/// so one check per predicate is enough to pin the rule.
void checkBadArguments(const std::string& goal, const std::string& predicate) {
  const auto result = runProgram("? " + goal + ".\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find(predicate + ": Недопустимый тип аргументов") != std::string::npos);
}

}  // namespace

TEST_CASE("concatenation: all four modes, and the empty string") {
  // Each line is one branch of the implementation:
  //   с1,с2 bound, с3 bound  → comparison
  //   с1,с2 bound, с3 free   → с3 = с1 ++ с2
  //   с1,с3 bound, с2 free   → с3 must start with с1, с2 = the rest
  //   с2,с3 bound, с1 free   → с3 must end with с2, с1 = the beginning
  const auto result = runProgram(
      "?СЦЕП(\"аб\", \"вг\", X).\n"          // X=абвг
      "?СЦЕП(\"аб\", \"вг\", \"абвг\").\n"    // ДА
      "?СЦЕП(\"аб\", \"вг\", \"абв\").\n"     // НЕТ
      "?СЦЕП(\"аб\", X, \"абвг\").\n"         // X=вг
      "?СЦЕП(X, \"вг\", \"абвг\").\n"         // X=аб
      "?СЦЕП(X, \"бвг\", \"-абвг\").\n"       // X=-а
      "?СЦЕП(\"вг\", X, \"абвг\").\n"         // НЕТ: с3 does not start with "вг"
      "?СЦЕП(X, \"аб\", \"абвг\").\n"         // НЕТ: с3 does not end with "аб"
      // The empty string is a string like any other: it starts and ends anything.
      "?СЦЕП(\"\", \"вг\", X).\n"             // X=вг
      "?СЦЕП(\"аб\", \"\", X).\n"             // X=аб
      "?СЦЕП(X, \"\", \"абвг\").\n"           // X=абвг
      "?СЦЕП(\"\", \"\", X).\n"               // X= (empty)
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=абвг\nДА\nНЕТ\nX=вг\nX=аб\nX=-а\nНЕТ\nНЕТ\n"
                            "X=вг\nX=аб\nX=абвг\nX=\n");
}

TEST_CASE("concatenation: a goal it cannot answer is a type error") {
  // Both halves free with the whole known: nothing can be split out of that, and
  // guessing would be worse than saying so.
  checkBadArguments("СЦЕП(X, Y, \"аб\")", "СЦЕП");
  checkBadArguments("СЦЕП(1, \"а\", X)", "СЦЕП");
}

TEST_CASE("copying a substring: all five modes") {
  // The five modes of the help text, one line each:
  //   s,int,int,free   → the substring            s,int,int,str → comparison
  //   s,int,free,str   → the length               s,free,int,str → the position
  //   s,free,free,str  → position and length of the first occurrence
  const auto result = runProgram(
      "?КОПИЯ(\"ПРОЛОГ\", 2, 3, X).\n"           // X=РОЛ
      "?КОПИЯ(\"ПРОЛОГ\", 2, 3, \"РОЛ\").\n"      // ДА
      "?КОПИЯ(\"ПРОЛОГ\", 2, 3, \"РО\").\n"       // НЕТ
      "?КОПИЯ(\"ПРОЛОГ\", 2, X, \"РОЛ\").\n"      // X=3
      "?КОПИЯ(\"ПРОЛОГ\", 3, X, \"РОЛ\").\n"      // НЕТ: the piece is not there
      "?КОПИЯ(\"ПРОЛОГ\", X, 3, \"РОЛ\").\n"      // X=2
      "?КОПИЯ(\"ПРОЛОГ\", X, Y, \"ЛОГ\").\n"      // X=4, Y=3
      // A negative length means "that many from the end" in the search mode…
      "?КОПИЯ(\"ПРОЛОГ\", X, -3, \"РОЛ\").\n"     // X=2
      // …and the absolute value in the extraction mode.
      "?КОПИЯ(\"ПРОЛОГ\", 2, -3, X).\n"           // X=РОЛ
      // The empty substring is found at position 1 with length 0, and an empty
      // piece is what a zero length takes out of the string.
      "?КОПИЯ(\"ПРОЛОГ\", X, Y, \"\").\n"         // X=1, Y=0
      "?КОПИЯ(\"ПРОЛОГ\", X, 0, \"\").\n"         // X=1
      "?КОПИЯ(\"ПРОЛОГ\", X, 3, \"\").\n"         // НЕТ: an empty substring is not 3 long
      // The first occurrence is the one reported, and positions are code points.
      "?КОПИЯ(\"абаб\", X, Y, \"аб\").\n"         // X=1, Y=2
      "?КОПИЯ(\"ёжик\", X, 1, \"к\").\n"          // X=4
      "?КОПИЯ(\"ёжик\", 2, 1, X).\n"              // X=ж
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=РОЛ\nДА\nНЕТ\nX=3\nНЕТ\nX=2\nX=4\nY=3\nX=2\nX=РОЛ\n"
                            "X=1\nY=0\nX=1\nНЕТ\nX=1\nY=2\nX=4\nX=ж\n");
}

TEST_CASE("copying a substring: the edges of the range are failures, not errors") {
  // A position or a length outside the string is a *failure* — the goal is simply
  // not satisfied — while a wrong type is an error.  The whole six-character
  // string is the reference here, so every case is arithmetic a reader can check.
  const auto result = runProgram(
      "?КОПИЯ(\"ПРОЛОГ\", 1, 6, X).\n"        // X=ПРОЛОГ: the whole string
      "?КОПИЯ(\"ПРОЛОГ\", 6, 1, X).\n"        // X=Г: the last character
      "?КОПИЯ(\"ПРОЛОГ\", 0, 3, X).\n"        // НЕТ: position 0 is before the first
      "?КОПИЯ(\"ПРОЛОГ\", -1, 3, X).\n"       // НЕТ: a negative position never is
      "?КОПИЯ(\"ПРОЛОГ\", 7, 1, X).\n"        // НЕТ: past the last character
      "?КОПИЯ(\"ПРОЛОГ\", 1, 20, X).\n"       // НЕТ: longer than what is left
      "?КОПИЯ(\"ПРОЛОГ\", 5, 5, X).\n"        // НЕТ: 5 from 5 needs 5, only 2 left
      "?КОПИЯ(\"ПРОЛОГ\", 2, 0, X).\n"        // X= (empty): a zero length takes nothing
      "?КОПИЯ(\"ПРОЛОГ\", 7, 0, X).\n"        // X=: position 7 with length 0 is the end
      "?КОПИЯ(\"ПРОЛОГ\", 0, 0, X).\n"        // НЕТ: the position is still out of range
      "?КОПИЯ(\"ПРОЛОГ\", 2, 2, \"\").\n"     // НЕТ: the piece is not empty
      "?КОПИЯ(\"\", X, Y, \"\").\n"           // X=1, Y=0: the empty string
      "?КОПИЯ(\"\", 1, 1, X).\n"              // НЕТ: nothing to take
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=ПРОЛОГ\nX=Г\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nX=\nX=\nНЕТ\n"
                            "НЕТ\nX=1\nY=0\nНЕТ\n");
}

TEST_CASE("copying a substring: a goal it cannot answer is a type error") {
  // The source must be a string, and at least one of position/length/substring
  // must be known: with a free position, a free length *and* a free substring
  // there is nothing to compute.
  checkBadArguments("КОПИЯ(1, 1, 1, X)", "КОПИЯ");
  checkBadArguments("КОПИЯ(\"аб\", X, Y, Z)", "КОПИЯ");
  // A position that is not a number: `asInteger` refuses it.
  checkBadArguments("КОПИЯ(\"аб\", \"б\", 1, X)", "КОПИЯ");
}

TEST_CASE("string length: counts code points, or checks the number") {
  const auto result = runProgram(
      "?ДЛИНА(\"ПРОЛОГ\", X).\n"     // X=6
      "?ДЛИНА(\"ёжик\", X).\n"       // X=4: four code points, eight bytes
      "?ДЛИНА(\"\", X).\n"           // X=0
      "?ДЛИНА(\"ПРОЛОГ\", 6).\n"     // ДА
      "?ДЛИНА(\"ПРОЛОГ\", 5).\n"     // НЕТ
      "?ДЛИНА(\"\", 0).\n"           // ДА
      "?ДЛИНА(\"\", 1).\n"           // НЕТ
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=6\nX=4\nX=0\nДА\nНЕТ\nДА\nНЕТ\n");
}

TEST_CASE("string length: a non-string source and a non-number length are errors") {
  checkBadArguments("ДЛИНА(1, X)", "ДЛИНА");
  checkBadArguments("ДЛИНА(\"аб\", \"б\")", "ДЛИНА");
}

TEST_CASE("letter and digit: the first one, or the one at a position") {
  // Free position: the first character of that kind, which is how a program walks
  // a string looking for a letter or a digit.  Bound position: a check.
  const auto result = runProgram(
      "?БУКВА(\"абв\", X).\n"       // X=1
      "?БУКВА(\"1а2\", X).\n"       // X=2: the digit at 1 is skipped
      "?БУКВА(\"123\", X).\n"       // НЕТ: no letter at all
      "?БУКВА(\"ёжик\", 1).\n"      // ДА: ё is a letter, and it is not ASCII
      "?БУКВА(\"ёжик\", 2).\n"      // ДА: so is ж
      "?ЦИФРА(\"абв1\", X).\n"      // X=4
      "?ЦИФРА(\"1а2\", X).\n"       // X=1
      "?ЦИФРА(\"абв\", X).\n"       // НЕТ
      "?ЦИФРА(\"12\", 2).\n"        // ДА
      "?ЦИФРА(\"абв\", 2).\n"       // НЕТ
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\nX=2\nНЕТ\nДА\nДА\nX=4\nX=1\nНЕТ\nДА\nНЕТ\n");
}

TEST_CASE("letter and digit: a position outside the string fails") {
  const auto result = runProgram(
      "?БУКВА(\"абв\", 0).\n"       // НЕТ
      "?БУКВА(\"абв\", -1).\n"      // НЕТ
      "?БУКВА(\"абв\", 4).\n"       // НЕТ: one past the last
      "?БУКВА(\"\", 1).\n"          // НЕТ: the empty string has no first character
      "?ЦИФРА(\"12\", 0).\n"        // НЕТ
      "?ЦИФРА(\"12\", 3).\n"        // НЕТ
      "?ЦИФРА(\"\", X).\n"          // НЕТ
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("letter and digit: a non-string source is a type error") {
  checkBadArguments("БУКВА(1, X)", "БУКВА");
  checkBadArguments("ЦИФРА(1, X)", "ЦИФРА");
  checkBadArguments("БУКВА(\"абв\", \"а\")", "БУКВА");
}

TEST_CASE("text to number: conversion and comparison") {
  const auto result = runProgram(
      "?СТРЦЕЛ(\"42\", X).\n"                       // X=42
      "?СТРЦЕЛ(\"042\", X).\n"                      // X=42: leading zeros are fine
      "?СТРЦЕЛ(\"-7\", X).\n"                       // X=-7
      "?СТРЦЕЛ(X, 42).\n"                           // X=42
      "?СТРЦЕЛ(X, -7).\n"                           // X=-7
      "?СТРЦЕЛ(X, 100000000000000000000).\n"        // X=100000000000000000000
      "?СТРЦЕЛ(\"42\", 42).\n"                      // ДА
      "?СТРЦЕЛ(\"042\", 42).\n"                     // ДА: the number, not the spelling
      "?СТРЦЕЛ(\"42\", 41).\n"                      // НЕТ
      "?СТРЦЕЛ(\"4.2\", X).\n"                      // НЕТ: that is not an integer
      "?СТРЦЕЛ(\"абв\", X).\n"                      // НЕТ
      "?СТРЦЕЛ(\"\", X).\n"                         // НЕТ
      "?СТРЦЕЛ(\" 42\", X).\n"                      // НЕТ: no trimming, as in `BigInt::tryParse`
      "?СТРЦЕЛ(\"42 \", X).\n"                      // НЕТ
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=42\nX=42\nX=-7\nX=42\nX=-7\nX=100000000000000000000\n"
                            "ДА\nДА\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("text to real: conversion and comparison") {
  const auto result = runProgram(
      "?СТРВЕЩ(\"4.25\", X).\n"       // X=4.25
      "?СТРВЕЩ(\"4\", X).\n"          // X=4.0: it is a float, and prints as one
      "?СТРВЕЩ(\"-0.5\", X).\n"       // X=-0.5
      "?СТРВЕЩ(X, 4.25).\n"           // X=4.25
      "?СТРВЕЩ(\"4.25\", 4.25).\n"    // ДА
      "?СТРВЕЩ(\"4.2\", 4.25).\n"     // НЕТ
      "?СТРВЕЩ(\"абв\", X).\n"        // НЕТ
      "?СТРВЕЩ(\"4.2.5\", X).\n"      // НЕТ: not the whole text is a number
      "?СТРВЕЩ(\"\", X).\n"           // НЕТ
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=4.25\nX=4.0\nX=-0.5\nX=4.25\nДА\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("text conversions: a goal they cannot answer is a type error") {
  checkBadArguments("СТРЦЕЛ(1, X)", "СТРЦЕЛ");
  checkBadArguments("СТРЦЕЛ(\"1\", \"1\")", "СТРЦЕЛ");
  checkBadArguments("СТРВЕЩ(1, X)", "СТРВЕЩ");
  checkBadArguments("СТРВЕЩ(\"1\", \"1\")", "СТРВЕЩ");
}

TEST_CASE("string to list: a string and the list of its code points") {
  const auto result = runProgram(
      "?СТРСПИС(\"аб\", X).\n"                    // X=[1072,1073]
      "?СТРСПИС(X, [1072, 1073]).\n"              // X=аб
      "?СТРСПИС(\"аб\", [1072, 1073]).\n"         // ДА
      "?СТРСПИС(\"аб\", [1072]).\n"               // НЕТ
      "?СТРСПИС(\"\", X).\n"                      // X=[]
      "?СТРСПИС(X, []).\n"                        // X= (empty)
      "?СТРСПИС(\"ё\", X).\n"                     // X=[1105]: a code point, not a byte
  );
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=[1072,1073]\nX=аб\nДА\nНЕТ\nX=[]\nX=\nX=[1105]\n");
}

TEST_CASE("string to list: a broken list and a wrong type are errors") {
  // A list whose tail is not `[]` is not a list of characters.
  const auto result = runProgram("?СТРСПИС(X, [1072|1073]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("список") != std::string::npos);

  checkBadArguments("СТРСПИС(X, [а])", "СТРСПИС");
  checkBadArguments("СТРСПИС(X, 1)", "СТРСПИС");
}

