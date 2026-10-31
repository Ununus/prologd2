#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

// The standard order of terms (task_90): variables, then numbers, then text,
// then compounds — numbers by value, text by code point, compounds by arity,
// name and arguments.  `compare/3` is the call, and the four `@` signs are sugar
// over it: `A @< B` *is* `compare(<, A, B)`, and `A @=< B` is the same call under
// `НЕ`, the way `=<` is.  Every expectation here is taken from the built
// interpreter.

TEST_CASE("compare answers with the sign of the standard order") {
  const auto result = runProgram(
      "?compare(Порядок, 1, 2).\n"
      "?compare(Порядок, 2, 1).\n"
      "?compare(Порядок, 1, 1.0).\n"
      "?compare(Порядок, а, \"а\").\n"
      "?compare(Порядок, 1, а).\n"
      "?compare(Порядок, ф(1), ф(1, 2)).\n"
      "?compare(Порядок, ф(1), д(2)).\n"
      "?compare(Порядок, [а], ф(б)).\n"
      "?compare(Порядок, аб, аа).\n"
      "?compare(Порядок, Х, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // Numbers by value (`1` and `1.0` are one number, as `РАВНО` and `БОЛЬШЕ`
  // have it), an atom and a string with the same letters are one text, arity is
  // asked *before* the name (`ф/1` before `ф/2`, `ф/1` before `'.'/2`), and a
  // free variable stands before everything.
  REQUIRE(result.output ==
          "Порядок=<\n"
          "Порядок=>\n"
          "Порядок==\n"
          "Порядок==\n"
          "Порядок=<\n"
          "Порядок=<\n"
          "Порядок=>\n"
          "Порядок=>\n"
          "Порядок=>\n"
          "Порядок=<\n"
          "Х=_1\n");
}

TEST_CASE("compare tests the order when its answer is already given") {
  // The four `@` signs are built on exactly this form, so it has to answer
  // «ДА»/«НЕТ» and not bind anything.
  const auto result = runProgram(
      "?compare(<, 1, 2).\n"
      "?compare(=, 1, 1).\n"
      "?compare(>, 1, 2).\n"
      "?compare(<, 2, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\nНЕТ\n");
}

TEST_CASE("the four at-signs compare by the standard order") {
  const auto result = runProgram(
      "?1 @< 2.\n"
      "?2 @< 1.\n"
      "?1 @=< 1.\n"
      "?1 @>= 1.\n"
      "?2 @> 1.\n"
      "?ф(1) @< ф(1, 2).\n"
      "?[а, б] @< [б].\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "ДА\nНЕТ\nДА\nДА\nДА\nДА\nДА\n");
}

TEST_CASE("a term that contains itself compares as far as it can") {
  // `РАВНО(Ц, ф(Ц))` is legal here — there is no occurs check — so the walk
  // stops at a pair of cells it has already seen, the guard `ПОЛНЫЙ` uses.  A
  // plain walk would compare the two terms forever.
  const auto result = runProgram(
      "?РАВНО(Ц, ф(Ц)), compare(Порядок, Ц, Ц).\n"
      "?РАВНО(А, ф(А)), РАВНО(Б, ф(Б)), compare(Порядок, А, Б).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "Ц=ф(...)\nПорядок==\nА=ф(...)\nБ=ф(...)\nПорядок==\n");
}

TEST_CASE("a list of pairs sorts by its first element") {
  // The example that started task_90 (a program from a book): `sort/2` over
  // `[[Диалект, Автор], …]`.  Cyrillic comes after the Latin letters by code
  // point, so «Д» stands last — that is the order, not a sorting fault.
  const auto result = runProgram(
      "пролог(\"Д\", \"Григорьев\").\n"
      "пролог(\"GNU\", \"Диас\").\n"
      "пролог(\"SWI\", \"Виламакер\").\n"
      "?НАЙТИВСЕ([Диалект, Автор], пролог(Диалект, Автор), Q), СОРТИРОВКА(Q, W).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output ==
          "Диалект=_1\nАвтор=_1\n"
          "Q=[[Д,Григорьев],[GNU,Диас],[SWI,Виламакер]]\n"
          "W=[[GNU,Диас],[SWI,Виламакер],[Д,Григорьев]]\n");
}

TEST_CASE("the dialect's own name for compare reaches the same function") {
  // task_94: `СРАВНЕНИЕ/3` is the Russian name the manual leads with, and
  // `compare` is its English spelling — one function behind two names, as with
  // every other pair.  The answers are signs, so they read the same either way.
  // (The test *name* stays ASCII: `catch_discover_tests` writes the names into a
  // file with the console code page, and a Cyrillic one comes back mangled.)
  const auto result = runProgram(
      "?СРАВНЕНИЕ(Порядок, 1, 2).\n"
      "?СРАВНЕНИЕ(<, 2, 1).\n"
      "?СРАВНЕНИЕ(=, а, \"а\").\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "Порядок=<\nНЕТ\nДА\n");
}

TEST_CASE("a mixed pair of numbers compares exactly and not through a double") {
  // 2^53 + 1 and the real 2^53 are different numbers that a `double` comparison
  // calls equal.  Comparing them through `double` made the answer to `compare`
  // disagree with `РАВНО` and threw one of them out of `СОРТИРОВКА`; the
  // comparator now takes the exact rule from `compareNumbers`, the one
  // unification uses.
  const auto result = runProgram(
      "?compare(Порядок, #2 ** 53 + 1#, #2 ** 53 + 0.0#).\n"
      "?БОЛЬШЕ(#2 ** 53 + 1#, #2 ** 53 + 0.0#).\n"
      "?МЕНЬШЕ(#2 ** 53 + 0.0#, #2 ** 53 + 1#).\n"
      "?РАВНО(#2 ** 53 + 1#, #2 ** 53 + 0.0#).\n"
      "?РАВНО(#2 ** 53#, #2 ** 53 + 0.0#).\n"
      "?РАВНО(#2 ** 100#, #2 ** 100 + 0.0#).\n"
      "?X is 2 ** 53, Y is 2 ** 53 + 1, Z is 2 ** 53 + 0.0, СОРТИРОВКА([Y, Z, X], L).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output ==
          // Bigger by one, and the order says so; the real 2^53 is the same
          // number as the whole 2^53, which is why `РАВНО` pairs them.
          "Порядок=>\n"
          "ДА\n"
          "ДА\n"
          "НЕТ\n"
          "ДА\n"
          "ДА\n"
          // Both numbers survive: the real `2^53` is a duplicate of the whole
          // `2^53` and goes, `2^53 + 1` stays.
          "X=9007199254740992\n"
          "Y=9007199254740993\n"
          "Z=9007199254740992.0\n"
          "L=[9007199254740992.0,9007199254740993]\n");
}
