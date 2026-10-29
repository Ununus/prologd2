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

TEST_CASE("the comparison signs are sugar over the long forms") {
  // task_52: `<`, `>`, `=<`, `>=`; the last two are `НЕ(МЕНЬШЕ/БОЛЬШЕ)`.
  const auto result = runProgram(
      "?2 > 1.\n"
      "?2 >= 2.\n"
      "?1 < 2.\n"
      "?2 =< 1.\n"
      "?2 > 1.0.\n"
      "?\"а\" < \"б\".\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "ДА\nДА\nДА\nНЕТ\nДА\nДА\n");

  // A free operand is the runtime error of the predicate the sign names,
  // exactly as with the long form.
  const auto free_operand = runProgram("?X >= 1.\n");
  REQUIRE(free_operand.loaded);
  REQUIRE(free_operand.runtimeError);
  REQUIRE(free_operand.error.find("МЕНЬШЕ: Недопустимый тип аргументов") !=
          std::string::npos);
}

TEST_CASE("a wrong argument is named, with what was given and what was expected") {
  // Part 136: `БОЛЬШЕ(терм(один, 2), атом).` used to say only that the types were
  // wrong.  The argument, the term in it and the expectation are what a reader
  // needs, and the short message is still the prefix, so everything that looked
  // for `БОЛЬШЕ: Недопустимый тип аргументов` still finds it.
  const auto comparison = runProgram("?БОЛЬШЕ(терм(один, 2), атом).\n");
  REQUIRE(comparison.loaded);
  REQUIRE(comparison.runtimeError);
  REQUIRE(comparison.error.find(
              "БОЛЬШЕ: Недопустимый тип аргументов: аргумент 1 — терм(один,2), "
              "нужно число, текст или список") != std::string::npos);

  // A free variable is not a wrong type — nobody bound it — and the message says
  // that instead of blaming the type.
  const auto unbound = runProgram("?БОЛЬШЕ(X, 1).\n");
  REQUIRE(unbound.loaded);
  REQUIRE(unbound.runtimeError);
  REQUIRE(unbound.error.find("БОЛЬШЕ: Недопустимый тип аргументов: аргумент 1 — "
                             "несвязанная переменная, нужно число, текст или "
                             "список") != std::string::npos);

  // The culprit is found where it is, not just the first argument: here the first
  // one is a number and the second is the atom.
  const auto second = runProgram("?СЛОЖЕНИЕ(1, атом, С).\n");
  REQUIRE(second.loaded);
  REQUIRE(second.runtimeError);
  REQUIRE(second.error.find("СЛОЖЕНИЕ: Недопустимый тип аргументов: аргумент 2 — атом, "
                            "нужно число") != std::string::npos);
}

TEST_CASE("a type error in a rule names the clause it happened in") {
  // Part 137: `badArguments` used to throw on its own, so the error carried no
  // place and the window's «Место» column was empty for every type error — while a
  // division by zero, raised through `Engine::raise`, had one.  The message text
  // is the same; only the place is new.
  const auto rule = runProgram("плохо(X) :- БОЛЬШЕ(X, терм(один, 2)).\n?плохо(1).\n");
  REQUIRE(rule.runtimeError);
  REQUIRE(rule.errorLocation.file == "<test>");
  REQUIRE(rule.errorLocation.line == 1);

  // A goal written in the question itself is reported at the question's own line.
  const auto question = runProgram("хорошо(1).\n?БОЛЬШЕ(терм(один, 2), 1).\n");
  REQUIRE(question.runtimeError);
  REQUIRE(question.errorLocation.line == 2);
}

TEST_CASE("lists compare element by element") {
  // Part 138, the rule the original gained in `112e241`: lexicographic, the way
  // strings compare — the empty list is the smallest, heads follow the same rules
  // as the arguments themselves, and equal heads leave the tails to decide.
  const auto result = runProgram(
      "?БОЛЬШЕ([1,3],[1,2]).\n"
      "?МЕНЬШЕ([1,2],[1,3]).\n"
      "?БОЛЬШЕ([1,2],[1,3]).\n"
      "?МЕНЬШЕ([1,2],[1,2,3]).\n"
      "?БОЛЬШЕ([1,2,3],[1,2]).\n"
      "?МЕНЬШЕ([],[1]).\n"
      "?БОЛЬШЕ([1],[]).\n"
      "?БОЛЬШЕ([],[]).\n"
      "?МЕНЬШЕ([],[]).\n"
      "?МЕНЬШЕ([аня],[боря]).\n"
      "?МЕНЬШЕ([\"аб\"],[\"ав\"]).\n"
      "?МЕНЬШЕ([[1],[2]],[[1],[3]]).\n"
      "?МЕНЬШЕ([1.5],[2]).\n"
      "?БОЛЬШЕ([1,2],[1,2]).\n"
      "?РАВНО([1,2],[1,2]).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output ==
          "ДА\nДА\nНЕТ\nДА\nДА\nДА\nДА\nНЕТ\nНЕТ\nДА\nДА\nДА\nДА\nНЕТ\nДА\n");
}

TEST_CASE("a list is compared only with a list of comparable elements") {
  // Kinds do not mix: a list is not comparable with a number or with text, and
  // the elements obey the same rule — a number against an atom inside a list is
  // the same refusal.
  for (const std::string goal :
       {"БОЛЬШЕ([1,2], 5)", "БОЛЬШЕ(5, [1,2])", "БОЛЬШЕ([1], [аня])",
        "БОЛЬШЕ([Х], [1])"}) {
    INFO("goal: " << goal);
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("the ISO arithmetic signs are sugar over the long forms") {
  // task_92: `is`, `=:=`, `=\=`, `\=` — the same goals an ISO reader writes,
  // built from the parts the dialect already had.  Their operands are ordinary
  // arithmetic expressions, so no `#…#` is needed.
  const auto result = runProgram(
      "?X is 2 + 3.\n"
      "?X is 2*3 + 1.\n"
      "?X is #2+2#.\n"
      "?Y = 3, X is Y + 1.\n"
      "?X is -1.\n"
      "?1 + 1 =:= 2.\n"
      "?2 =:= 1 + 2.\n"
      "?2 =\\= 1 + 2.\n"
      "?1 =:= 1.0.\n"
      "?X \\= 1.\n"
      "?2 \\= 2.\n"
      "?f(a) \\= 1.\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output ==
          "X=5\nX=7\nX=4\nY=3\nX=4\nX=-1\nДА\nНЕТ\nДА\nДА\nНЕТ\nНЕТ\nДА\n");
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
      "?ABS(-5, X).\n"
      "?ABS(-5.5, X).\n"
      "?ABS(X, 5).\n"
      "?ABS(X, 0).\n"
      "?ABS(X, -5).\n"
      "?ABS(5, 5).\n"
      "?ABS(-5, 5).\n"
      "?ABS(5, -5).\n"
      "?SQRT(9, X).\n"
      "?SQRT(2, X).\n"
      "?SQRT(2.25, X).\n"
      "?SQRT(0, X).\n"
      "?SQRT(X, 4).\n"
      "?SQRT(X, -4).\n"
      "?SQRT(X, 0).\n"
      "?SQRT(9, 3).\n"
      "?SQRT(2, 1).\n"
      "?SQRT(-4, X).\n"
      "?SQRT(-4.0, X).\n"
      "?SQRT(-4, 0).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=5\nX=5.5\nX=5\nX=0\nНЕТ\nДА\nДА\nНЕТ\n"
                            "X=3\nX=1\nX=1.5\nX=0\nX=16\nX=16\nX=0\nДА\nНЕТ\n"
                            "НЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("SIN, COS, TAN and EXP: forward, inverse, and the check") {
  // The three branches of the whole family, plus the edges of the domains: a
  // value the function does not have is a *failure*, never a `nan` unified with
  // the argument — `ln` of a negative number, `ln` of zero, `asin` of 2, and a
  // forward value that overflows (`EXP(1000.0, X)`).
  const auto result = runProgram(
      "?SIN(0.0, X).\n"
      "?COS(0.0, X).\n"
      "?TAN(0.0, X).\n"
      "?EXP(0.0, X).\n"
      "?SIN(X, 0.0).\n"
      "?COS(X, 1.0).\n"
      "?TAN(X, 0.0).\n"
      "?EXP(X, 1.0).\n"
      "?SIN(0.0, 0.0).\n"
      "?COS(0.0, 1.0).\n"
      "?TAN(0.0, 0.0).\n"
      "?EXP(0.0, 1.0).\n"
      "?COS(0.0, 0.0).\n"
      "?EXP(1.0, 0.0).\n"
      "?EXP(X, -1.0).\n"
      "?EXP(X, 0.0).\n"
      "?EXP(1000.0, X).\n"
      "?SIN(X, 2.0).\n"
      "?COS(X, 2.0).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=0.0\nX=1.0\nX=0.0\nX=1.0\nX=0.0\nX=0.0\nX=0.0\nX=0.0\n"
                            "ДА\nДА\nДА\nДА\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("the arithmetic predicates are capitals, the functions lowercase") {
  // Part 219: a goal and a name inside `#…#` are told apart by case.  `ABS/2` is
  // the predicate; `abs` stayed the function of an expression, and calling it as
  // a goal of arity two is the retired spelling, not «не найдено».
  const auto functions = runProgram("?X is abs(-5) + sqrt(4) + sin(0) + cos(0) + tan(0) + exp(0).\n");
  REQUIRE(functions.loaded);
  REQUIRE(functions.output == "X=9.0\n");

  for (const auto& [query, expected] :
       {std::pair{"?abs(-5, X).\n", "«abs/2» переименовано: теперь «ABS(X, Y)»"},
        std::pair{"?sqrt(9, X).\n", "«sqrt/2» переименовано: теперь «SQRT(X, Y)»"},
        std::pair{"?sin(0.0, X).\n", "«sin/2» переименовано: теперь «SIN(X, Y)»"},
        std::pair{"?cos(0.0, X).\n", "«cos/2» переименовано: теперь «COS(X, Y)»"},
        std::pair{"?tan(0.0, X).\n", "«tan/2» переименовано: теперь «TAN(X, Y)»"},
        std::pair{"?exp(0.0, X).\n", "«exp/2» переименовано: теперь «EXP(X, Y)»"}}) {
    INFO("query: " << query);
    const auto result = runProgram(query);
    REQUIRE_FALSE(result.loaded);
    REQUIRE(result.error.find(expected) != std::string::npos);
  }

  // Arity one of a capital name is a wrong arity, not a missing name: the
  // predicate is there, and the message says how many arguments it takes.
  const auto wrongArity = runProgram("?ABS(3).\n");
  REQUIRE_FALSE(wrongArity.loaded);
  REQUIRE(wrongArity.error.find("ABS не имеет арности 1") != std::string::npos);
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
  // which is the only reason this test can look at a random number at all.  The
  // engine is `std::mt19937_64` and the mapping from its output to a range is
  // ours, not `std::uniform_int_distribution`'s (that one differs between the
  // standard libraries), so the number below is the same on every platform.
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
      "ABS(\"а\", X)",
      "SQRT(\"а\", X)",
      "SIN(\"а\", X)",
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
  for (const std::string goal :
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

TEST_CASE("`/` is float division and `//` the integer one") {
  // ISO's `/` always answers a real: `1 / 2` is `0.5` and `6 / 3` is `2.0`.  The
  // integer quotient is `//` (or `div`), which truncates toward zero.
  const auto result = runProgram(
      "?X is 1 / 2.\n"
      "?X is 6 / 3.\n"
      "?X is 1 // 2.\n"
      "?X is 7 // 2.\n"
      "?X is -7 // 2.\n"
      "?X is 6 // 3.\n"
      "?X is 6 div 3.\n"
      "?ВЕЩ(#1/2#).\n"
      "?ЦЕЛ(#1//2#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=0.5\nX=2.0\nX=0\nX=3\nX=-3\nX=2\nX=2\nДА\nДА\n");
}

TEST_CASE("`rem` and `mod` answer the remainder with the dividend's sign") {
  // ISO's `rem` takes the sign of the dividend and `div` truncates toward zero,
  // so `-5 rem 3` is `-2` while `-5 div 3` is `-1`.  ISO's `mod` would answer 1
  // — that difference is on purpose here, so it is written down as a check.
  const auto result = runProgram(
      "?X is -5 rem 3.\n"
      "?X is -5 mod 3.\n"
      "?X is -5 div 3.\n"
      "?X is 5 rem 3.\n"
      "?X is -5 rem -3.\n"
      "?X is 5 mod -3.\n"
      "?X is 7 // 2 * 2 + 7 rem 2.\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=-2\nX=-2\nX=-1\nX=2\nX=-2\nX=2\nX=7\n");
}

TEST_CASE("the arithmetic functions of ISO work inside an expression") {
  // A function is written with its name and one argument: `abs(-5)` — not
  // `abs(-5, X)`, which is the two-argument predicate of the same name.  `abs`
  // and `sign` keep the type of the argument, the other four always answer a
  // real, and `pi` is the constant.
  const auto result = runProgram(
      "?X is abs(-5).\n"
      "?X is abs(-5.5).\n"
      "?X is abs(5).\n"
      "?X is sign(-3).\n"
      "?X is sign(0).\n"
      "?X is sign(2.5).\n"
      "?X is sign(-0.5).\n"
      "?X is sqrt(9).\n"
      "?X is sin(0).\n"
      "?X is cos(0).\n"
      "?X is tan(0).\n"
      "?X is exp(0).\n"
      "?X is pi.\n"
      "?X is abs(2 - 5) + 1.\n"
      "?X is -abs(-2).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "X=5\nX=5.5\nX=5\nX=-1\nX=0\nX=1.0\nX=-1.0\nX=3.0\nX=0.0\n"
          "X=1.0\nX=0.0\nX=1.0\nX=3.141593\nX=4\nX=-2\n");
}

TEST_CASE("the rounding functions answer whole numbers") {
  // ISO's four rounding functions, each with its own rule: `floor` down,
  // `ceiling` up, `round` to the nearest (a half goes away from zero) and
  // `truncate` toward zero.  A whole argument comes back untouched — going
  // through `double` would lose digits past 2^53.
  const auto result = runProgram(
      "?X is floor(3.7).\n"
      "?X is floor(-3.7).\n"
      "?X is ceiling(3.2).\n"
      "?X is ceiling(-3.2).\n"
      "?X is round(3.5).\n"
      "?X is round(-3.5).\n"
      "?X is round(2.4).\n"
      "?X is truncate(3.9).\n"
      "?X is truncate(-3.9).\n"
      "?X is floor(5).\n"
      "?X is truncate(100000000000000000000).\n"
      "?ЦЕЛ(#round(2.4)#).\n"
      "?ВЕЩ(#floor(2.4)#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3\nX=-4\nX=4\nX=-3\nX=4\nX=-4\nX=2\nX=3\nX=-3\n"
                            "X=5\nX=100000000000000000000\nДА\nНЕТ\n");
}

TEST_CASE("`**` is ISO's power, and it binds tighter than the sign") {
  // ISO's `**` is `xfx`: tighter than the unary sign, so `-2**2` is `-(2**2)`
  // and the answer is -4, and tighter than `*`.  A whole base with a whole
  // exponent stays whole and exact, a negative exponent turns the answer real.
  const auto result = runProgram(
      "?X is 2 ** 10.\n"
      "?X is 2 ** 100.\n"
      "?X is -2 ** 2.\n"
      "?X is 2 ** 3 + 1.\n"
      "?X is 2 * 3 ** 2.\n"
      "?X is (2 ** 3) ** 2.\n"
      "?X is 2 ** (3 ** 2).\n"
      "?X is 2 ** -1.\n"
      "?X is 4 ** 0.5.\n"
      "?X is 0 ** 0.\n"
      "?X is (-2) ** 3.\n"
      "?X is 2 ** 0.5 * 2 ** 0.5.\n"
      "?X is #2 ** 3#.\n"
      "?2 ** 3 =:= 8.\n"
      "?ВЕЩ(#2 ** 2#).\n"
      "?ЦЕЛ(#2 ** 2#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "X=1024\nX=1267650600228229401496703205376\nX=-4\nX=9\nX=18\nX=64\n"
          "X=512\nX=0.5\nX=2.0\nX=1\nX=-8\nX=2.0\nX=8\nДА\nНЕТ\nДА\n");
}

TEST_CASE("`**` refuses a chain and a number it cannot hold") {
  // `**` is not associative even in ISO, and the two readings of `2**3**4`
  // differ by a factor of `2**74`: the brackets are asked for, not guessed.
  const auto chain = runProgram("?X is 2 ** 3 ** 4.\n");
  REQUIRE_FALSE(chain.loaded);
  REQUIRE(chain.error.find("не цепочка") != std::string::npos);
  // The integers have no fixed width, but a power that would run for hours is
  // refused instead of attempted, and the message says why.
  const auto tooBig = runProgram("?X is 2 ** 100000.\n");
  REQUIRE(tooBig.loaded);
  REQUIRE(tooBig.runtimeError);
  REQUIRE(tooBig.error.find("слишком велик") != std::string::npos);
  for (const auto& [query, expected] :
       {std::pair{"?X is 0 ** -1.\n", "деление на ноль"},
        std::pair{"?X is (-8) ** 0.5.\n", "дробной степени"},
        std::pair{"?X is 2.0 ** 1024.\n", "не представим"}}) {
    INFO("query: " << query);
    const auto answer = runProgram(query);
    REQUIRE(answer.loaded);
    REQUIRE(answer.runtimeError);
    REQUIRE(answer.error.find(expected) != std::string::npos);
  }
}

TEST_CASE("`log` is the natural logarithm") {
  const auto result = runProgram(
      "?X is log(exp(1)).\n"
      "?X is log(1).\n"
      "?X is log(exp(2)).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1.0\nX=0.0\nX=2.0\n");
  // The logarithm has no value at zero or below: a real number cannot come out,
  // and an expression cannot answer «нет» — so it is a runtime error.
  for (const char* query : {"?X is log(0).\n", "?X is log(-1).\n"}) {
    INFO("query: " << query);
    const auto answer = runProgram(query);
    REQUIRE(answer.loaded);
    REQUIRE(answer.runtimeError);
    REQUIRE(answer.error.find("логарифм") != std::string::npos);
  }
}

TEST_CASE("a function of a value it does not have is an error") {
  // Inside an expression there is no «failure» to answer `НЕТ` with: a root of a
  // negative number and an overflow are runtime errors, and the message names
  // the function.
  for (const auto& [query, expected] :
       {std::pair{"?X is sqrt(-1).\n", "корень из отрицательного числа"},
        std::pair{"?X is exp(1000).\n", "результат не представим числом"}}) {
    INFO("query: " << query);
    const auto result = runProgram(query);
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find(expected) != std::string::npos);
  }
  // A non-number where a function wants one is the usual type error.
  const auto wrong = runProgram("?X is sqrt(\"4\").\n");
  REQUIRE(wrong.loaded);
  REQUIRE(wrong.error.find("Нечисловой операнд") != std::string::npos);
}

TEST_CASE("division by zero is a runtime error") {
  for (const char* query : {"?РАВНО(X, #1/0#).\n", "?РАВНО(X, #1//0#).\n",
                            "?РАВНО(X, #1 mod 0#).\n", "?РАВНО(X, #1 rem 0#).\n",
                            "?РАВНО(X, #1.0/0#).\n"}) {
    INFO("query: " << query);
    const auto result = runProgram(query);
    REQUIRE(result.loaded);
    REQUIRE(result.error.find("деление на ноль") != std::string::npos);
  }
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
