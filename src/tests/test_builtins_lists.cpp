#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

// The two sorts of a list (part 259).  Both put it in the standard order of
// terms --- numbers by value, text by code point, compounds by arity, name and
// arguments (task_90) --- and they differ in one thing only: `МНОЖЕСТВО/2`
// (`sort`) drops every repeat and `СОРТИРОВКА/2` (`msort`) keeps them.  The
// expectations here are taken from the built interpreter, not written out of the
// head.

TEST_CASE("the set orders numbers and drops the repeats") {
  const auto result = runProgram(
      "?МНОЖЕСТВО([3, 1, 2, 1], С).\n"
      "?МНОЖЕСТВО([], С).\n"
      "?МНОЖЕСТВО([5], С).\n"
      "?МНОЖЕСТВО([-1, 2.5, 2, 0], С).\n"
      "?sort([5, 4, 4], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[1,2,3]\nС=[]\nС=[5]\nС=[-1,0,2,2.5]\nС=[4,5]\n");
}

TEST_CASE("the set orders text by code point, an atom and a string alike") {
  // `БОЛЬШЕ`/`МЕНЬШЕ` compare either two numbers or two text constants, and a
  // constant may be written as an atom or as a string: the two mix in one list.
  const auto result = runProgram(
      "?МНОЖЕСТВО([\"б\", \"а\", \"в\", \"а\"], С).\n"
      "?МНОЖЕСТВО([б, \"а\"], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[а,б,в]\nС=[а,б]\n");
}

TEST_CASE("the set counts as one value whatever its own comparison calls equal") {
  // `РАВНО(1, 1.0)` holds, and `БОЛЬШЕ`/`МЕНЬШЕ` call those two equal, so the
  // ordered list has one value in it; the stable sort leaves the first of the
  // pair in front, and that is the one that stays.
  const auto result = runProgram("?МНОЖЕСТВО([1, 1.0], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[1]\n");
}

TEST_CASE("the set unifies its second argument with the ordered list") {
  const auto result = runProgram(
      "?МНОЖЕСТВО([2, 1], [1, 2]).\n"
      "?МНОЖЕСТВО([2, 1], [2, 1]).\n"
      "?МНОЖЕСТВО([], [1]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nНЕТ\n");
}

TEST_CASE("the set orders any terms, not only numbers and text") {
  // The standard order of task_90: numbers, then text, then compounds — and
  // compounds by arity first, so `ф(б)` (arity 1) stands before `[а]` (arity 2,
  // the list functor).  `никогда` is the user's example: the ISO `sort/2` sorts
  // a list of pairs by its first element.
  const auto result = runProgram(
      "?МНОЖЕСТВО([1, молоко, 2.5, [а], ф(б)], С).\n"
      "?МНОЖЕСТВО([[б, 2], [а, 1]], С).\n"
      "?МНОЖЕСТВО([ф(2), ф(1)], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "С=[1,2.5,молоко,ф(б),[а]]\nС=[[а,1],[б,2]]\nС=[ф(1),ф(2)]\n");
}

TEST_CASE("the set refuses a list that is not a proper list") {
  // The order now compares anything, so the refusals left are the shape of the
  // first argument: a listlike tail (`[1 | 2]`), something that is not a list,
  // and a list that contains itself — the last is why the walk is guarded, a
  // plain walk would follow the cycle forever.
  for (const std::string goal :
       {"МНОЖЕСТВО([1 | 2], С)", "МНОЖЕСТВО(Х, С)",
        "РАВНО(Ц, [1 | Ц]), МНОЖЕСТВО(Ц, С)"}) {
    INFO("goal: " << goal);
    const auto result = runProgram("?" + goal + ".\n");
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("МНОЖЕСТВО: Недопустимый тип аргументов") != std::string::npos);
  }
}

TEST_CASE("the set names the argument that is not a list") {
  // Part 136: the list family reports the way the arithmetic one does.  A number
  // where a list belongs is an argument to name; an improper list is not (it *is*
  // a list, just not a proper one), and that message stays short.
  const auto named = runProgram("?МНОЖЕСТВО(12, С).\n");
  REQUIRE(named.runtimeError);
  REQUIRE(named.error.find("МНОЖЕСТВО: Недопустимый тип аргументов: аргумент 1 — 12, "
                           "нужно список") != std::string::npos);
}

TEST_CASE("the sort keeps every repeat, one number or not") {
  // `msort/2`: the same order as the set, and no value is thrown away.  `1` and
  // `1.0` are one number in this dialect, so `РАВНО(1, 1.0)` holds and both of
  // them survive here — that is the whole difference from `МНОЖЕСТВО/2`.
  const auto result = runProgram(
      "?СОРТИРОВКА([3, 1, 2, 1], С).\n"
      "?СОРТИРОВКА([1, 1.0], С).\n"
      "?СОРТИРОВКА([\"б\", \"а\", \"в\", \"а\"], С).\n"
      "?msort([5, 4, 4], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[1,1,2,3]\nС=[1,1.0]\nС=[а,а,б,в]\nС=[4,4,5]\n");
}

TEST_CASE("the sort is the plain check, so an unordered list is refused") {
  // The second argument is unified, so the predicate is a test as well: `[2, 1]`
  // ordered is `[1, 2]`, and nothing else unifies with it.
  const auto result = runProgram(
      "?СОРТИРОВКА([2, 1], [1, 2]).\n"
      "?СОРТИРОВКА([2, 1], [2, 1]).\n"
      "?СОРТИРОВКА([1, 1], [1]).\n"
      "?СОРТИРОВКА([], [1]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("the sort counts its own arguments when it refuses") {
  const auto named = runProgram("?СОРТИРОВКА(12, С).\n");
  REQUIRE(named.runtimeError);
  REQUIRE(named.error.find("СОРТИРОВКА: Недопустимый тип аргументов: аргумент 1 — 12, "
                           "нужно список") != std::string::npos);
}

TEST_CASE("the English spellings follow the arity, not the name") {
  // part 259: `sort` is ISO's set at two arguments and the sort with the order at
  // three; `msort` is the two-argument sort alone.  A spelling that names an
  // arity it does not have is refused by the parser, with the arities it does.
  const auto result = runProgram(
      "?sort([5, 4, 4], С).\n"
      "?sort(@>, [1, 2], С).\n"
      "?msort([5, 4, 4], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=[4,5]\nС=[2,1]\nС=[4,4,5]\n");

  const auto wrong = runProgram("?msort(@>, [1, 2], С).\n");
  REQUIRE_FALSE(wrong.loaded);
  REQUIRE(wrong.error.find("msort не имеет арности 3") != std::string::npos);
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

TEST_CASE("the two-argument sort is the ascending sign written out") {
  // `СОРТИРОВКА/2` is `СОРТИРОВКА(@=<, …)`: keeping the repeats is what `@=<`
  // does, and `МНОЖЕСТВО/2` is what `@<` does.  All of them go through one sort,
  // so this is the check that they cannot drift apart.
  const auto result = runProgram(
      "?СОРТИРОВКА([3, 1, 2, 1], А), СОРТИРОВКА(@=<, [3, 1, 2, 1], А).\n"
      "?МНОЖЕСТВО([3, 1, 2, 1], Б), СОРТИРОВКА(@<, [3, 1, 2, 1], Б).\n"
      "?СОРТИРОВКА(@<, [1, 1.0], С).\n"
      "?СОРТИРОВКА(@=<, [1, 1.0], С).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "А=[1,1,2,3]\nБ=[1,2,3]\nС=[1]\nС=[1,1.0]\n");
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
