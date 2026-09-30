#include <catch2/catch_test_macros.hpp>

#include <string>
#include <vector>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("addition is reversible") {
  const auto result = runProgram(
      "?СЛОЖЕНИЕ(100, 100, A).\n"
      "?СЛОЖЕНИЕ(100, A, 100).\n"
      "?СЛОЖЕНИЕ(A, 50, 100).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "A=200\nA=0\nA=50\n");
}

TEST_CASE("multiplication/4 implements the documented reversible cases") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(10, 2, 2, 22).\n"
      "?УМНОЖЕНИЕ(10, 2, 2, A).\n"
      "?УМНОЖЕНИЕ(10, 2, A, 22).\n"
      "?УМНОЖЕНИЕ(10, A, 2, 22).\n"
      "?УМНОЖЕНИЕ(A, 2, 2, 22).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nA=22\nA=2\nA=2\nA=10\n");
}

TEST_CASE("multiplication/3 divides with remainder detection") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(5, 7, X).\n"
      "?УМНОЖЕНИЕ(X, 7, 35).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=35\nX=5\n");
}

TEST_CASE("greater-than compares numbers and text") {
  // Two branches: two numbers (integer, float, big integer or an arithmetic
  // expression — `asNumeric` evaluates it) and two strings.  Text is compared
  // as *text*, so "10" is not greater than "9": that is the documented
  // behaviour and the reason the predicate is not a numeric comparison.
  const auto result = runProgram(
      "?БОЛЬШЕ(5, 3).\n"
      "?БОЛЬШЕ(3, 5).\n"
      "?БОЛЬШЕ(2.5, 2).\n"
      "?БОЛЬШЕ(2, 2.5).\n"
      "?БОЛЬШЕ(-1, -2).\n"
      "?БОЛЬШЕ(5, 5).\n"
      "?БОЛЬШЕ(100000000000000000000, 1).\n"
      "?БОЛЬШЕ(#2+2#, 3).\n"
      "?БОЛЬШЕ(\"б\", \"а\").\n"
      "?БОЛЬШЕ(\"а\", \"б\").\n"
      "?БОЛЬШЕ(\"10\", \"9\").\n"
      "?МЕНЬШЕ(3, 5).\n"
      "?МЕНЬШЕ(\"а\", \"б\").\n"
      "?МЕНЬШЕ(\"9\", \"10\").\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nДА\nНЕТ\nДА\nНЕТ\nДА\nДА\nДА\nНЕТ\nНЕТ\n"
                            "ДА\nДА\nНЕТ\n");
}

TEST_CASE("ABS and SQRT") {
  // Three branches each: the argument known, the result known (the inverse), and
  // both known (a check).  `ABS` of a negative `Y` has no answer, and a square
  // root of a negative number has none either — that one used to answer 0 for an
  // integer and `nan` for a float, because `BigInt::fromDouble(nan)` is zero.
  const auto result = runProgram(
      "?abs(-5, X).\n"
      "?abs(-5.5, X).\n"
      "?abs(X, 5).\n"
      "?abs(X, 0).\n"
      "?abs(X, -5).\n"
      "?abs(5, 5).\n"
      "?abs(-5, 5).\n"
      "?abs(5, -5).\n"
      "?sqrt(9, X).\n"
      "?sqrt(2, X).\n"
      "?sqrt(2.25, X).\n"
      "?sqrt(0, X).\n"
      "?sqrt(X, 4).\n"
      "?sqrt(X, -4).\n"
      "?sqrt(X, 0).\n"
      "?sqrt(9, 3).\n"
      "?sqrt(2, 1).\n"
      "?sqrt(-4, X).\n"
      "?sqrt(-4.0, X).\n"
      "?sqrt(-4, 0).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=5\nX=5.5\nX=5\nX=0\nНЕТ\nДА\nДА\nНЕТ\n"
                            "X=3\nX=1\nX=1.5\nX=0\nX=16\nX=16\nX=0\nДА\nНЕТ\n"
                            "НЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("sin, cos, tan and exp: forward, inverse, and the check") {
  // The three branches of the whole family, plus the edges of the domains: a
  // value the function does not have is a *failure*, never a `nan` unified with
  // the argument — `ln` of a negative number, `ln` of zero, `asin` of 2, and a
  // forward value that overflows (`exp(1000.0, X)`).
  const auto result = runProgram(
      "?sin(0.0, X).\n"
      "?cos(0.0, X).\n"
      "?tan(0.0, X).\n"
      "?exp(0.0, X).\n"
      "?sin(X, 0.0).\n"
      "?cos(X, 1.0).\n"
      "?tan(X, 0.0).\n"
      "?exp(X, 1.0).\n"
      "?sin(0.0, 0.0).\n"
      "?cos(0.0, 1.0).\n"
      "?tan(0.0, 0.0).\n"
      "?exp(0.0, 1.0).\n"
      "?cos(0.0, 0.0).\n"
      "?exp(1.0, 0.0).\n"
      "?exp(X, -1.0).\n"
      "?exp(X, 0.0).\n"
      "?exp(1000.0, X).\n"
      "?sin(X, 2.0).\n"
      "?cos(X, 2.0).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=0.0\nX=1.0\nX=0.0\nX=1.0\nX=0.0\nX=0.0\nX=0.0\nX=0.0\n"
                            "ДА\nДА\nДА\nДА\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("multiplication/3: the reversible modes and the zero divisor") {
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(2, 3, 6).\n"
      "?УМНОЖЕНИЕ(2, 3, 5).\n"
      "?УМНОЖЕНИЕ(2, 3, X).\n"
      "?УМНОЖЕНИЕ(3, X, 6).\n"
      // Not divisible: the result is a float, as the help says.
      "?УМНОЖЕНИЕ(4, X, 6).\n"
      "?УМНОЖЕНИЕ(X, 3, 6).\n"
      "?УМНОЖЕНИЕ(X, 4, 6).\n"
      // A zero divisor is a failure, not an error and not a guess.
      "?УМНОЖЕНИЕ(0, X, 0).\n"
      "?УМНОЖЕНИЕ(X, 0, 0).\n"
      "?УМНОЖЕНИЕ(2, 0.5, X).\n"
      "?УМНОЖЕНИЕ(-2, 3, X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nX=6\nX=2\nX=1.5\nX=2\nX=1.5\nНЕТ\nНЕТ\nX=1.0\nX=-6\n");
}

TEST_CASE("multiplication/4: every documented mode") {
  // The seven cases of the help text, in order, plus the failures: a remainder
  // that does not divide, and a zero divisor.
  const auto result = runProgram(
      "?УМНОЖЕНИЕ(10, 2, 2, A).\n"
      "?УМНОЖЕНИЕ(10, 2, 2, 22).\n"
      "?УМНОЖЕНИЕ(10, 2, 2, 23).\n"
      "?УМНОЖЕНИЕ(10, 2, A, 22).\n"
      "?УМНОЖЕНИЕ(10, A, 2, 22).\n"
      "?УМНОЖЕНИЕ(A, 2, 2, 22).\n"
      "?УМНОЖЕНИЕ(A, 3, 1, 7).\n"
      "?УМНОЖЕНИЕ(A, 3, 1, 8).\n"
      "?УМНОЖЕНИЕ(2, A, 1, 7).\n"
      "?УМНОЖЕНИЕ(2, A, 1, 8).\n"
      "?УМНОЖЕНИЕ(2, A, B, 7).\n"
      "?УМНОЖЕНИЕ(A, 2, B, 7).\n"
      "?УМНОЖЕНИЕ(A, 2, B, 6).\n"
      "?УМНОЖЕНИЕ(2, 3, 1, 7).\n"
      "?УМНОЖЕНИЕ(A, 0, B, 7).\n"
      // A zero *multiplier* is fine while nothing is divided: only a zero
      // divisor has no answer.
      "?УМНОЖЕНИЕ(2, 0, B, 7).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "A=22\nДА\nНЕТ\nA=2\nA=2\nA=10\n"
                            "A=2\nНЕТ\nA=3\nНЕТ\nA=3\nB=1\nA=3\nB=1\nA=3\nB=0\n"
                            "ДА\nНЕТ\nB=7\n");
}

TEST_CASE("addition: all three modes, integers and floats") {
  const auto result = runProgram(
      "?СЛОЖЕНИЕ(2, 3, 5).\n"
      "?СЛОЖЕНИЕ(2, 3, 6).\n"
      "?СЛОЖЕНИЕ(2, 3, X).\n"
      "?СЛОЖЕНИЕ(2, X, 5).\n"
      "?СЛОЖЕНИЕ(X, 3, 5).\n"
      "?СЛОЖЕНИЕ(0.5, X, 2.5).\n"
      "?СЛОЖЕНИЕ(2, 0.5, X).\n"
      "?СЛОЖЕНИЕ(100000000000000000000, 1, X).\n"
      "?СЛОЖЕНИЕ(-2, -3, X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nX=5\nX=3\nX=2\nX=2.0\nX=2.5\n"
                            "X=100000000000000000001\nX=-5\n");
}

TEST_CASE("is_whole, is_number and the truncating conversion take what they are given") {
  const auto result = runProgram(
      "?is_whole(4).\n"
      "?is_whole(4.0).\n"
      "?is_whole(4.5).\n"
      "?is_whole(-4.5).\n"
      "?is_number(4).\n"
      "?is_number(4.0).\n"
      "?is_number(4.5).\n"
      "?ЦЕЛВЕЩ(5, X).\n"
      "?ЦЕЛВЕЩ(X, 5.0).\n"
      "?ЦЕЛВЕЩ(5.5, X).\n"
      "?ЦЕЛВЕЩ(X, 5.5).\n"
      "?ЦЕЛВЕЩ(5, 5.0).\n"
      "?ЦЕЛВЕЩ(5.5, 5).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\nНЕТ\nДА\nДА\nДА\nX=5.0\nX=5\nX=5\nX=5\nДА\nДА\n");
}

TEST_CASE("the random built-in seeds, draws, and refuses what it cannot do") {
  // `СЛУЧ(N)` seeds — and the seed is what makes the next draw deterministic,
  // which is the only reason this test can look at a random number at all.
  const auto result = runProgram(
      "?СЛУЧ(42).\n"
      "?СЛУЧ(X).\n"
      "?СЛУЧ(X, 1, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nX=-286924074\nX=1\n");

  // The range must be the right way round, and the first argument must be free.
  const auto backwards = runProgram("?СЛУЧ(X, 6, 1).\n");
  REQUIRE(backwards.loaded);
  REQUIRE(backwards.runtimeError);
  REQUIRE(backwards.error.find("АРГ2 > АРГ3") != std::string::npos);

  const auto bound = runProgram("?СЛУЧ(5, 1, 6).\n");
  REQUIRE(bound.loaded);
  REQUIRE(bound.runtimeError);
  REQUIRE(bound.error.find("СЛУЧ: Недопустимый тип аргументов") != std::string::npos);

  // A float bound is truncated, like every other integer argument here (see
  // `ЦЕЛВЕЩ`): the bounds are numbers, and 1.5 is the number 1.
  const auto truncated = runProgram("?СЛУЧ(7).\n?СЛУЧ(X, 1.5, 6.0).\n");
  REQUIRE(truncated.loaded);
  REQUIRE(truncated.output.starts_with("ДА\nX="));
  const std::size_t marker = truncated.output.find('=');
  REQUIRE(marker != std::string::npos);
  // The answer, without the trailing newline.  Cut by the marker, not by a byte
  // count: «ДА» is four bytes in UTF-8, not two.
  const std::string drawn =
      truncated.output.substr(marker + 1, truncated.output.size() - marker - 2);
  REQUIRE(drawn.find_first_not_of("0123456789") == std::string::npos);
  const int value = std::stoi(drawn);
  REQUIRE(value >= 1);
  REQUIRE(value <= 6);
}

TEST_CASE("the arithmetic built-ins report a wrong type as an error") {
  const auto cases = std::vector<std::string>{
      "БОЛЬШЕ(1, \"а\")",          // a number against text: neither branch
      "МЕНЬШЕ(\"а\", 1)",
      "СЛОЖЕНИЕ(2, X, Y)",        // fewer than two arguments known
      "СЛОЖЕНИЕ(\"а\", 1, X)",
      "УМНОЖЕНИЕ(2, X, Y)",
      "abs(\"а\", X)",
      "sqrt(\"а\", X)",
      "sin(\"а\", X)",
      "ЦЕЛВЕЩ(\"а\", X)",
      "СЛУЧ(1.5)",                 // seeding needs an integer
  };
  for (const std::string& goal : cases) {
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Недопустимый тип аргументов") != std::string::npos);
  }

  // `is_whole` and `is_number` have an error of their own: the argument is a
  // number or it is nothing, and «ошибка преобразования типа» says which.
  for (const std::string& goal :
       {"is_whole(\"4\")", "is_number(\"4\")", "is_whole(X)", "is_number(X)"}) {
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("ошибка преобразования типа") != std::string::npos);
  }

  // An arity nothing is registered for cannot work at all, and the load says so
  // instead of leaving a silent failure (task_40).
  const auto unknown = runProgram("?УМНОЖЕНИЕ(1, 2, 3, 4, 5).\n");
  REQUIRE_FALSE(unknown.loaded);
  REQUIRE(unknown.error.find("УМНОЖЕНИЕ не имеет арности 5 (есть 3 и 4)") !=
          std::string::npos);
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

TEST_CASE("conversions between numbers and strings") {
  const auto result = runProgram(
      "?ЦЕЛВЕЩ(3, X).\n"
      "?ЦЕЛВЕЩ(X, 3.7).\n"
      "?СТРЦЕЛ(\"42\", K).\n"
      "?СТРЦЕЛ(gamma, K).\n"
      "?СТРВЕЩ(\"3.14\", K).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3.0\nX=3\nK=42\nНЕТ\nK=3.14\n");
}
