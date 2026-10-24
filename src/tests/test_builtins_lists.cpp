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
  for (const std::string goal :
       {"СОРТИРОВКА([1 | 2], С)", "СОРТИРОВКА(Х, С)",
        "РАВНО(Ц, [1 | Ц]), СОРТИРОВКА(Ц, С)"}) {
    INFO("goal: " << goal);
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("СОРТИРОВКА: Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("sorting names the argument that is not a list") {
  // Part 136: the list family reports the way the arithmetic one does.  A number
  // where a list belongs is an argument to name; an improper list is not (it *is*
  // a list, just not a proper one), and that message stays short.
  const auto named = runProgram("?СОРТИРОВКА(12, С).\n");
  REQUIRE(named.runtimeError);
  REQUIRE(named.error.find("СОРТИРОВКА: Недопустимый тип аргументов: аргумент 1 — 12, "
                           "нужно список") != std::string::npos);
}

// `СОРТИРОВКА/3` (`sort/3`, task_95): the same sort with the order written down.
// The four signs are the standard order read in two directions, and the duplicate
// rule is SWI's for `sort/4` — the signs that admit equality are the ones that
// keep repeats.  Taken from the built interpreter.

TEST_CASE("sort with an order sign: four signs, and what each does to repeats") {
  const auto result = runProgram(
      "?СОРТИРОВКА(@<, [3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА(@=<, [3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА(@>, [3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА(@>=, [3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА(@>, [], С).\n"
      "?СОРТИРОВКА(@=<, [б, а, б], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "С=[1,2,3]\nС=[1,1,2,3]\nС=[3,2,1]\nС=[3,2,1,1]\nС=[]\nС=[а,б,б]\n");
}

TEST_CASE("sort with the ascending sign is the plain sort, value for value") {
  // `СОРТИРОВКА/2` is ISO's `sort/2`, and the two arities go through one function:
  // this is the check that they cannot drift apart.  `@=<` keeps what the order
  // calls equal, so `1` and `1.0` — one number — both stay.
  const auto result = runProgram(
      "?СОРТИРОВКА([3, 1, 2, 1], А), СОРТИРОВКА(@<, [3, 1, 2, 1], А).\n"
      "?СОРТИРОВКА(@<, [1, 1.0], С).\n"
      "?СОРТИРОВКА(@=<, [1, 1.0], С).\n"
      "?sort(@>, [1, 2], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "А=[1,2,3]\nС=[1]\nС=[1,1.0]\nС=[2,1]\n");
}

TEST_CASE("sort with an order sign refuses anything but the four signs") {
  // The order is an atom from a set of four: `<` and `>` are arithmetic, not the
  // standard order, and a bare word is a typo.  An improper list keeps the short
  // message — it is a list, just not one that ends.
  for (const std::string goal :
       {"СОРТИРОВКА(<, [1], С)", "СОРТИРОВКА(порядок, [1], С)",
        "СОРТИРОВКА(@<, [1 | 2], С)"}) {
    INFO("goal: " << goal);
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("СОРТИРОВКА: Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("sort with an order sign counts its own arguments") {
  // Part 136: a refusal names the argument the way the predicate counts it, so a
  // list that is argument 2 is called «аргумент 2», not «1».
  const auto order = runProgram("?СОРТИРОВКА(12, [1], С).\n");
  REQUIRE(order.runtimeError);
  REQUIRE(order.error.find("СОРТИРОВКА: Недопустимый тип аргументов: аргумент 1 — 12, "
                           "нужно @<, @=<, @> или @>=") != std::string::npos);

  const auto list = runProgram("?СОРТИРОВКА(@<, 12, С).\n");
  REQUIRE(list.runtimeError);
  REQUIRE(list.error.find("СОРТИРОВКА: Недопустимый тип аргументов: аргумент 2 — 12, "
                          "нужно список") != std::string::npos);
}
