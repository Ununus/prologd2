#include <string>

#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

namespace {

/// Five marks: two pupils, three subjects, one repeated mark — enough for a
/// group of two, a group of three and a repeat that `МНОРЕШ` has to drop.
const char* kMarks =
    "оценка(аня, матем, 5).\n"
    "оценка(аня, физика, 4).\n"
    "оценка(боря, матем, 3).\n"
    "оценка(боря, физика, 5).\n"
    "оценка(боря, химия, 4).\n";

}  // namespace

TEST_CASE("bagof answers one group per pupil") {
  // The goal has two free variables (`У`, `П`) and the template is `А`, so a
  // group is one pupil taken over every subject — two answers, and the solver
  // hands them out on backtracking (task_91).
  const auto result = runProgram(std::string(kMarks) + "?ВСЕРЕШ(А, П^оценка(У, П, А), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "А=_1\n"
          "П=_1\n"
          "У=аня\n"
          "С=[5,4]\n"
          "А=_1\n"
          "П=_1\n"
          "У=боря\n"
          "С=[3,5,4]\n");
}

TEST_CASE("setof sorts the bag and drops the repeats") {
  const auto result = runProgram(std::string(kMarks) + "?МНОРЕШ(А, П^оценка(У, П, А), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "А=_1\n"
          "П=_1\n"
          "У=аня\n"
          "С=[4,5]\n"
          "А=_1\n"
          "П=_1\n"
          "У=боря\n"
          "С=[3,4,5]\n");
}

TEST_CASE("a bag with nothing in it fails") {
  // The one place where `ВСЕРЕШ` does not copy `НАЙТИВСЕ`: an empty collection
  // is a goal that does not hold, not an empty list.
  const auto result = runProgram(
      "?ВСЕРЕШ(А, ЛОЖЬ, С).\n"
      "?НАЙТИВСЕ(А, ЛОЖЬ, С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nА=_1\nС=[]\n");
}

TEST_CASE("a goal without free variables gives one bag") {
  // Nothing but the template is free, so there is one group and one answer — the
  // same list `НАЙТИВСЕ` would give, held while backtracking instead of at once.
  const auto result = runProgram(std::string(kMarks) + "?ВСЕРЕШ(А, У^П^оценка(У, П, А), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "А=_1\n"
          "У=_1\n"
          "П=_1\n"
          "С=[5,4,3,5,4]\n");
}

TEST_CASE("the quantifier keeps a variable out of the key") {
  // `У^П^` names both free variables, so no group is split by them; `П^` alone
  // leaves `У` in the key, which is the two-answer case above.
  const auto result = runProgram(std::string(kMarks) + "?ВСЕРЕШ(А, У^(оценка(У, П, А), РАВНО(П, матем)), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "А=_1\n"
          "У=_1\n"
          "П=матем\n"
          "С=[5,3]\n");
}

TEST_CASE("the bag is matched against the third argument") {
  // The collected list is unified with the bag, so a bound one chooses the
  // group that agrees with it instead of being overwritten.
  const auto result = runProgram(std::string(kMarks) +
                                 "?ВСЕРЕШ(А, оценка(аня, П, А), [4]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "А=_1\nП=физика\n");
}

TEST_CASE("a cut after the bag keeps one group") {
  // The answers are a choice point of the machine, so `!` in the body cuts them
  // off exactly as it cuts the clauses of an ordinary predicate.
  const auto result = runProgram(std::string(kMarks) +
                                 "?ВСЕРЕШ(А, оценка(аня, П, А), С), !.\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "А=_1\nП=матем\nС=[5]\n");
}

TEST_CASE("bags can be collected by findall") {
  // `ВСЕРЕШ` inside `НАЙТИВСЕ` is a goal like any other: every group it answers
  // is one element of the collected list.
  const auto result = runProgram(std::string(kMarks) +
                                 "?НАЙТИВСЕ(С, ВСЕРЕШ(А, оценка(аня, П, А), С), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "С=_1\n"
          "А=_1\n"
          "П=_1\n"
          "L=[[5],[4]]\n");
}

TEST_CASE("the English spellings are the same predicates") {
  const auto result = runProgram(std::string(kMarks) +
                                 "?bagof(A, оценка(аня, П, A), С).\n"
                                 "?setof(A, П^оценка(аня, П, A), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "A=_1\n"
          "П=матем\n"
          "С=[5]\n"
          "A=_1\n"
          "П=физика\n"
          "С=[4]\n"
          "A=_1\n"
          "П=_1\n"
          "С=[4,5]\n");
}

TEST_CASE("an error raised by the collected goal is reported") {
  const auto result = runProgram("?ВСЕРЕШ(Х, ЦЕЛВЕЩ(\"а\", Х), С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("ЦЕЛВЕЩ: Недопустимый тип аргументов") != std::string::npos);
}
