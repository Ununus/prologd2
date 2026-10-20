#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

// `СОРТИРОВКА/2` (`sort`): the list is put in the standard order of terms ---
// numbers by value, text by code point, compounds by arity, name and arguments
// --- and the repeats are dropped (task_90).  The expectations here are taken
// from the built interpreter, not written out of the head.

TEST_CASE("sort orders numbers and drops the repeats") {
  const auto result = runProgram(
      "?СОРТИРОВКА([3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА([], С).\n"
      "?СОРТИРОВКА([5], С).\n"
      "?СОРТИРОВКА([-1, 2.5, 2, 0], С).\n"
      "?sort([5, 4, 4], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[1,2,3]\nС=[]\nС=[5]\nС=[-1,0,2,2.5]\nС=[4,5]\n");
}

TEST_CASE("sort orders text by code point, an atom and a string alike") {
  // `БОЛЬШЕ`/`МЕНЬШЕ` compare either two numbers or two text constants, and a
  // constant may be written as an atom or as a string: the two mix in one list.
  const auto result = runProgram(
      "?СОРТИРОВКА([\"б\", \"а\", \"в\", \"а\"], С).\n"
      "?СОРТИРОВКА([б, \"а\"], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[а,б,в]\nС=[а,б]\n");
}

TEST_CASE("sort counts as one value whatever its own comparison calls equal") {
  // `РАВНО(1, 1.0)` holds, and `БОЛЬШЕ`/`МЕНЬШЕ` call those two equal, so the
  // ordered list has one value in it; the stable sort leaves the first of the
  // pair in front, and that is the one that stays.
  const auto result = runProgram("?СОРТИРОВКА([1, 1.0], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[1]\n");
}

TEST_CASE("sort unifies its second argument with the ordered list") {
  const auto result = runProgram(
      "?СОРТИРОВКА([2, 1], [1, 2]).\n"
      "?СОРТИРОВКА([2, 1], [2, 1]).\n"
      "?СОРТИРОВКА([], [1]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nНЕТ\n");
}

TEST_CASE("sort orders any terms, not only numbers and text") {
  // The standard order of task_90: numbers, then text, then compounds — and
  // compounds by arity first, so `ф(б)` (arity 1) stands before `[а]` (arity 2,
  // the list functor).  `никогда` is the user's example: the ISO `sort/2` sorts
  // a list of pairs by its first element.
  const auto result = runProgram(
      "?СОРТИРОВКА([1, молоко, 2.5, [а], ф(б)], С).\n"
      "?СОРТИРОВКА([[б, 2], [а, 1]], С).\n"
      "?СОРТИРОВКА([ф(2), ф(1)], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "С=[1,2.5,молоко,ф(б),[а]]\nС=[[а,1],[б,2]]\nС=[ф(1),ф(2)]\n");
}

TEST_CASE("sort refuses a list that is not a proper list") {
  // The order now compares anything, so the refusals left are the shape of the
  // first argument: a listlike tail (`[1 | 2]`), something that is not a list,
  // and a list that contains itself — the last is why the walk is guarded, a
  // plain walk would follow the cycle forever.
  for (const std::string& goal :
       {"СОРТИРОВКА([1 | 2], С)", "СОРТИРОВКА(Х, С)",
        "РАВНО(Ц, [1 | Ц]), СОРТИРОВКА(Ц, С)"}) {
    INFO("goal: " << goal);
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("СОРТИРОВКА: Недопустимый тип аргументов") != std::string::npos);
  }
}
