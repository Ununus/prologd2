#include <algorithm>
#include <catch2/catch_test_macros.hpp>
#include <string>
#include <string_view>

#include "prlib/engine.hpp"
#include "test_helpers.hpp"

namespace {

/// True for a name that has a byte above ASCII in it, which in this project means
/// a Russian name (the language writes built-in names in Cyrillic, and English
/// ones are ASCII by definition).
bool isRussianName(std::string_view name) {
  return std::any_of(name.begin(), name.end(),
                     [](unsigned char byte) { return byte >= 0x80; });
}

/// Names the *engine* or the *parser* answers instead of the dispatch table:
/// they have an English spelling too, but it is not registered with `add`.
bool isAnsweredOutsideTheTable(std::string_view name) {
  return name == "ВЫП" || name == "ИМПОРТ";
}

/// The Russian names that have no English spelling, each for a reason of its own
/// (task_83, task_84, task_107):
///
/// * `ИЛИ/2` is the word of the original dialect, kept so that programs written
///   for it load.  The English way to say the same thing is `first`, the alias of
///   `ПЕРВОЕ`, and the old English twin `or` stays retired.
/// * `КОПИЯ/4` lost `substring` because the ISO predicate for the same work is
///   `sub_string/5` — positions from zero, three counts — so that English name is
///   a predicate of its own rather than an alias.
bool hasNoEnglishSpelling(std::string_view name) {
  return name == "ИЛИ" || name == "КОПИЯ";
}

std::string_view englishOf(std::string_view russian) {
  for (const prologd::BuiltinAlias& alias : prologd::builtinAliases()) {
    if (alias.first == russian) {
      return alias.second;
    }
  }
  return {};
}

}  // namespace

TEST_CASE("every alias is wired to the function its Russian name reaches") {
  // The alias table is what `add` registers from, so this is the test that keeps
  // the two spellings from drifting apart: same name, every arity, one address.
  for (const prologd::BuiltinAlias& alias : prologd::builtinAliases()) {
    const std::string russian(alias.first);
    const std::string english(alias.second);
    if (prologd::builtinArities(russian).variadic) {
      continue;  // variadic, no arities to enumerate; covered below
    }
    for (const std::size_t arity : prologd::builtinArities(russian).arities) {
      INFO("alias: " << english << "/" << arity);
      REQUIRE(prologd::findBuiltin(english, arity) == prologd::findBuiltin(russian, arity));
      REQUIRE(prologd::findBuiltin(english, arity) != nullptr);
    }
  }
}

TEST_CASE("the variadic built-ins are variadic under both spellings") {
  for (const std::string_view russian : {"ВЫВОД", "ВЫВОДПС", "ПЕРВОЕ"}) {
    const std::string_view english = englishOf(russian);
    REQUIRE_FALSE(english.empty());
    for (const std::size_t arity : {std::size_t{1}, std::size_t{3}, std::size_t{9}}) {
      INFO("name: " << russian << " arity: " << arity);
      REQUIRE(prologd::findBuiltin(english, arity) == prologd::findBuiltin(russian, arity));
      REQUIRE(prologd::findBuiltin(russian, arity) != nullptr);
    }
    REQUIRE(prologd::builtinArities(russian).variadic);
    REQUIRE(prologd::builtinArities(english).variadic);
    REQUIRE(prologd::builtinArities(russian).arities.empty());
    REQUIRE(prologd::findBuiltin(russian, 0) == nullptr);
  }
}

TEST_CASE("every Russian built-in has an English spelling") {
  // Completeness, and the reason it is a test rather than a comment: a new
  // built-in added to the dispatch table without a row in the alias table would
  // otherwise be the one Russian name a reader of ordinary Prolog cannot call.
  for (const std::string& name : prologd::builtinNames()) {
    if (!isRussianName(name)) {
      continue;
    }
    if (isAnsweredOutsideTheTable(name) || hasNoEnglishSpelling(name)) {
      continue;  // `ВЫП` -> `call`, `ИМПОРТ` -> `import`; two names by design
    }
    INFO("built-in without an English spelling: " << name);
    REQUIRE_FALSE(englishOf(name).empty());
  }
}

TEST_CASE("the original dialect's or-word is the two-goal spelling of the choice form") {
  // task_83: the name of the original dialect is callable again, and the English
  // one stays out.  Only the shape is checked here; the behaviour is in
  // `test_builtins_control.cpp`.
  REQUIRE(prologd::isReservedBuiltinName("ИЛИ"));
  REQUIRE(englishOf("ИЛИ").empty());
  REQUIRE(prologd::findBuiltin("or", 2) == nullptr);
  REQUIRE(prologd::builtinArities("ИЛИ").arities == std::vector<std::size_t>{2});
  REQUIRE_FALSE(prologd::builtinArities("ИЛИ").variadic);
  REQUIRE(prologd::findBuiltin("ИЛИ", 2) == prologd::findBuiltin("ПЕРВОЕ", 2));
  REQUIRE(prologd::findBuiltin("ИЛИ", 1) == nullptr);
  REQUIRE(prologd::findBuiltin("ИЛИ", 3) == nullptr);
}

TEST_CASE("the copy predicate answers to no English name, sub_string belongs to ПОДСТРОКА") {
  // task_84: `substring` was the English spelling of `КОПИЯ/4`, and it is gone —
  // the ISO predicate of the same family takes five arguments and counts from
  // zero, so it is a predicate of its own.  In Russian it is `ПОДСТРОКА` (part
  // 218), and `sub_string` is *its* English spelling, not a name of `КОПИЯ`.
  REQUIRE(englishOf("КОПИЯ").empty());
  REQUIRE(prologd::findBuiltin("substring", 4) == nullptr);
  REQUIRE(englishOf("ПОДСТРОКА") == "sub_string");
  REQUIRE(prologd::findBuiltin("sub_string", 5) != nullptr);
  REQUIRE(prologd::findBuiltin("ПОДСТРОКА", 5) == prologd::findBuiltin("sub_string", 5));
  REQUIRE(prologd::builtinArities("sub_string").arities == std::vector<std::size_t>{5});
  REQUIRE(prologd::findBuiltin("sub_string", 4) == nullptr);
}

TEST_CASE("the names marker is not a built-in at all") {
  // The modes are gone, so nothing answers to the marker: both spellings are
  // retired, which keeps them reserved — a call reaches the checks and is told
  // why — while the keyword table, completion and `--list-keywords` stay clear of
  // a name that does nothing.
  REQUIRE(prologd::findBuiltin("ИМЕНА", 1) == nullptr);
  REQUIRE(prologd::findBuiltin("variables", 1) == nullptr);
  REQUIRE(prologd::builtinArities("ИМЕНА").arities.empty());
  REQUIRE(prologd::isReservedBuiltinName("ИМЕНА"));
  REQUIRE(prologd::isReservedBuiltinName("variables"));
  REQUIRE(prologd::reservedBuiltinNames().count("ИМЕНА") == 0);
}

TEST_CASE("the English surface works from a program") {
  const auto result = prologd::test::runProgram(
      "parent(ann, bob).\n"
      "parent(bob, cid).\n"
      "grand(X, Z) :- parent(X, Y), parent(Y, Z).\n"
      "?findall(X, grand(X, Z), L).\n"
      "?call(parent(ann, Who)).\n"
      "?write(ok), nl.\n"
      "?integer(3).\n"
      "?float(3).\n"
      "?is_number(3).\n"
      "?is_whole(3.0).\n"
      "?strlen(\"ёжик\", N).\n"
      "?less(1, 2).\n"
      "?greater(2, 1).\n"
      "?equal(5, 5).\n"
      "?is_list([1]).\n"
      "?is_text(текст).\n"
      "?concat(\"а\", \"б\", Пара).\n"
      "?sub_string(\"абв\", 0, 1, _, Первая).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.error.empty());
  // `findall` undoes the bindings of its goal, so `X` and `Z` come back
  // unbound — which is what the first two lines show.
  REQUIRE(result.output ==
          "X=_1\nZ=_1\nL=[ann]\n"
          "Who=bob\n"
          "ok\n"
          "ДА\nДА\nНЕТ\nДА\nДА\nN=4\n"
          "ДА\nДА\nДА\nДА\nДА\nПара=аб\nПервая=а\n");
}
