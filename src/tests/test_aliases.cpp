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

/// The one built-in that has no English spelling *on purpose* (task_83): `ИЛИ`
/// is the original dialect's word for «the first of two».  The English
/// vocabulary for that behaviour is `ПЕРВОЕ`/`first`, and the old English twin
/// `or` was retired in task_44 and stays retired.
bool isDialectOnlyName(std::string_view name) { return name == "ИЛИ"; }

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
    if (isAnsweredOutsideTheTable(name) || isDialectOnlyName(name)) {
      continue;  // `ВЫП` -> `call`, `ИМПОРТ` -> `import`; `ИЛИ` has none by design
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
      "?concat(\"а\", \"б\", Пара).\n");
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
          "ДА\nДА\nДА\nДА\nДА\nПара=аб\n");
}
