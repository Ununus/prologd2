#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

// A truth table per predicate over the term kinds the original knows:
// variable, integer, real, atom, string, list cell, `[]`, compound, and an
// arithmetic expression (which is a compound until it is evaluated).

TEST_CASE("the variable test is true exactly for an unbound variable") {
  const auto result = runProgram(
      "?ПЕР(X).\n"                     // the answer reports the variable itself
      "?ПЕР(5).\n"
      "?ПЕР(a).\n"
      "?ПЕР(\"a\").\n"
      "?ПЕР([]).\n"
      "?ПЕР([1]).\n"
      "?ПЕР(f(1)).\n"
      "?ПЕР(#1+1#).\n"                 // an expression is a term, not a variable
      "?РАВНО(X, 1), ПЕР(X).\n"
      "?РАВНО(X, #1+1#), ПЕР(X).\n"    // an expression bound to X is evaluated
      "?РАВНО(X, Y), ПЕР(X).\n");      // two free variables are one variable
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\n"
                           "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n"
                           "X=_1\nY=_1\n");
}

TEST_CASE("a type test with an unregistered arity is an error") {
  // Each of these names has exactly one arity, so a two-argument call can never
  // succeed; the load stops with the message instead of a silent `НЕТ`.
  for (const std::string goal :
       {"ПЕР(X, X)", "ЦЕЛ(1, 1)", "ВЕЩ(1.0, 1.0)", "СИМВ(a, a)", "СПИСОК([], [])",
        "ПОЛНЫЙ([], [])"}) {
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE_FALSE(result.loaded);
    REQUIRE(result.error.find("не имеет арности 2 (есть 1)") != std::string::npos);
  }
}

TEST_CASE("the integer test is true for an integer or an expression that gives one") {
  const auto result = runProgram(
      "?ЦЕЛ(5).\n"
      "?ЦЕЛ(-5).\n"
      "?ЦЕЛ(0).\n"
      "?ЦЕЛ(100000000000000000000).\n"  // long arithmetic counts as integers
      "?ЦЕЛ(#2+3#).\n"
      "?ЦЕЛ(#10 div 3#).\n"
      "?ЦЕЛ(#10 mod 3#).\n"
      "?ЦЕЛ(#1//2#).\n"                 // `//` is the integer quotient: this is 0
      "?ЦЕЛ(#1/2#).\n"                  // `/` on two integers is a *real*: 0.5
      "?ЦЕЛ(5.0).\n"                    // a real is a real, even a whole one
      "?ЦЕЛ(5.5).\n"
      "?ЦЕЛ(#1.0/2#).\n"                // one real operand makes the result real
      "?ЦЕЛ(\"5\").\n"
      "?ЦЕЛ(a).\n"
      "?ЦЕЛ([]).\n"
      "?ЦЕЛ([1]).\n"
      "?ЦЕЛ(f(1)).\n"
      "?ЦЕЛ(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\nДА\nДА\nДА\nДА\n"
                           "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("the real test is true for a real or an expression that gives one") {
  const auto result = runProgram(
      "?ВЕЩ(5.0).\n"
      "?ВЕЩ(5.5).\n"
      "?ВЕЩ(-0.5).\n"
      "?ВЕЩ(#2.0+3#).\n"
      "?ВЕЩ(#1/2.0#).\n"
      "?ВЕЩ(#1/2#).\n"          // `/` is float division whatever the operands are
      "?ВЕЩ(5).\n"
      "?ВЕЩ(100000000000000000000).\n"
      "?ВЕЩ(#2+3#).\n"
      "?ВЕЩ(#10 div 3#).\n"
      "?ВЕЩ(\"5.0\").\n"
      "?ВЕЩ(a).\n"
      "?ВЕЩ([]).\n"
      "?ВЕЩ(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\nДА\nДА\n"
                           "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("the symbol test is true for an atom or a string") {
  const auto result = runProgram(
      "?СИМВ(a).\n"
      "?СИМВ(\"abc\").\n"
      "?СИМВ(\"\").\n"          // an empty string is still a string
      "?СИМВ([]).\n"            // the empty-list constant is a symbol like any atom
      "?СИМВ(5).\n"
      "?СИМВ(5.0).\n"
      "?СИМВ([a]).\n"
      "?СИМВ(f(1)).\n"
      "?СИМВ(#1+1#).\n"
      "?СИМВ(X).\n"
      "?РАВНО(X, \"abc\"), СИМВ(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nX=abc\n");
}

TEST_CASE("the list test is true for a list cell or the empty list") {
  const auto result = runProgram(
      "?СПИСОК([]).\n"
      "?СПИСОК([1]).\n"
      "?СПИСОК([1, 2]).\n"
      "?СПИСОК([1 | 2]).\n"    // a list cell whose tail is not a list is still a cell
      "?СПИСОК([1 | X]).\n"
      "?СПИСОК(X).\n"
      "?СПИСОК(5).\n"
      "?СПИСОК(\"abc\").\n"    // a string is not a list, even a short one
      "?СПИСОК(f(1)).\n"
      "?РАВНО(X, [1]), СПИСОК(X).\n"
      "?РАВНО(X, []), СПИСОК(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\nX=_1\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nX=[1]\nX=[]\n");
}

TEST_CASE("an integer and a real unify when they are the same number") {
  const auto result = runProgram(
      "?РАВНО(6, 6.0).\n"
      "?РАВНО(6, 6.5).\n"
      "?РАВНО(-5, -5.0).\n"
      "?РАВНО(0, 0.0).\n"
      "?РАВНО(0, -0.0).\n"
      "?РАВНО(16777217, 16777217.0).\n"                          // past a float's 24 bits
      "?РАВНО(16777217, 16777216.0).\n"
      "?РАВНО(100000000000000000000, 100000000000000000000.0).\n"
      "?РАВНО(100000000000000000001, 100000000000000000000.0).\n"  // not the same number
      "?РАВНО(2.5, 2).\n"
      "?РАВНО(10000000000, 10000000000.0).\n"
      "?РАВНО(#2+3#, 5.0).\n"
      "?РАВНО(#2.0+3#, 5).\n"
      "?РАВНО(#1/2#, 0.5).\n"                                    // `/` is float division
      "?РАВНО(#1//2#, 0).\n"                                     // `//` is the integer one
      "?РАВНО(5, 5).\n"
      "?РАВНО(\"5\", 5).\n");                                    // a string is not a number
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nДА\nДА\nДА\nДА\nНЕТ\nДА\nНЕТ\n"
                           "НЕТ\nДА\nДА\nДА\nДА\nДА\nДА\nНЕТ\n");
}

TEST_CASE("a cyclic term is written, not followed") {
  // `РАВНО` has no occurs check, so this makes a term that contains itself.
  // Following it used to end the process with a stack overflow — and a cyclic
  // list never ended at all, because its cells are followed in a loop rather
  // than by recursion.  The repeat is written `...` instead.
  const auto compound = runProgram("?РАВНО(X, f(X)).\n");
  REQUIRE(compound.loaded);
  REQUIRE_FALSE(compound.runtimeError);
  REQUIRE(compound.output == "X=f(...)\n");

  const auto list = runProgram("?РАВНО(X, [1 | X]).\n");
  REQUIRE(list.loaded);
  REQUIRE(list.output == "X=[1|...]\n");

  const auto indirect = runProgram("?РАВНО(X, f(Y)), РАВНО(Y, X).\n");
  REQUIRE(indirect.loaded);
  REQUIRE(indirect.output == "X=f(...)\nY=f(...)\n");

  const auto nested = runProgram("?РАВНО(X, f(g(X))).\n");
  REQUIRE(nested.loaded);
  REQUIRE(nested.output == "X=f(g(...))\n");

  // Sharing is not a cycle: the same subterm twice is written twice.
  const auto shared = runProgram("?РАВНО(X, g(1)), РАВНО(Y, f(X, X)).\n");
  REQUIRE(shared.loaded);
  REQUIRE(shared.output == "X=g(1)\nY=f(g(1),g(1))\n");
}

TEST_CASE("a cyclic term cannot be copied") {
  // `ДОБ` and `НАЙТИВСЕ` copy what they are given, and a cyclic term has no
  // finite copy: they say so instead of recursing until the stack ends.
  for (const std::string goal : {"?РАВНО(X, f(X)), ДОБ(X, [], 1).\n",
                                  "?РАВНО(X, f(X)), НАЙТИВСЕ(X, НЕ(ЛОЖЬ), L).\n"}) {
    const auto result = runProgram(goal);
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Циклический терм") != std::string::npos);
  }
}

TEST_CASE("the ground test finds a free variable anywhere in the term") {
  // The whole term is walked, not only its top: a variable inside a compound or
  // inside a list tail is an unbound variable all the same.
  const auto result = runProgram(
      "?ПОЛНЫЙ(5).\n"
      "?ПОЛНЫЙ(а).\n"
      "?ПОЛНЫЙ(\"строка\").\n"
      "?ПОЛНЫЙ([]).\n"
      "?ПОЛНЫЙ(Х).\n"
      "?ПОЛНЫЙ(факт(1, [2, 3])).\n"
      "?ПОЛНЫЙ(факт(1, [2, Х])).\n"
      "?ПОЛНЫЙ([1 | 2]).\n"                        // не список, но весь связан
      "?РАВНО(_Г, [1, 2]), ПОЛНЫЙ(_Г).\n"
      "?РАВНО(_В, 1), ПОЛНЫЙ(факт(_В)).\n"          // связанная переменная — не свободная
      "?ground(факт(1)).\n");                       // английское имя
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\nНЕТ\nДА\nНЕТ\nДА\nДА\nДА\nДА\n");
}

TEST_CASE("ground walks a term that contains itself instead of looping") {
  // `РАВНО(X, f(X))` is legal in this dialect (there is no occurs check), and
  // such a term holds no free variable: it is ground.  The walk carries the same
  // guard the printer uses, so the answer is `ДА` rather than no answer at all.
  const auto result = runProgram("?РАВНО(_Ц, ц(_Ц)), ПОЛНЫЙ(_Ц).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\n");
}
