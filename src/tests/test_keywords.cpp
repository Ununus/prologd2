#include <catch2/catch_test_macros.hpp>

#include <algorithm>
#include <set>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/keywords.hpp"
#include "prlib/lexer.hpp"

namespace {

const prologd::KeywordInfo* findKeyword(const std::vector<prologd::KeywordInfo>& keywords,
                                        std::string_view name) {
  const auto it = std::find_if(keywords.begin(), keywords.end(),
                               [name](const prologd::KeywordInfo& keyword) {
                                 return keyword.name == name;
                               });
  return it == keywords.end() ? nullptr : &*it;
}

}  // namespace

TEST_CASE("reserved names match the lexer's set") {
  const auto& reserved = prologd::reservedBuiltinNames();
  const std::vector<prologd::KeywordInfo> keywords = prologd::reservedKeywords();
  REQUIRE(keywords.size() == reserved.size());
  for (const prologd::KeywordInfo& keyword : keywords) {
    INFO("name: " << std::string(keyword.name));
    REQUIRE(reserved.count(std::string(keyword.name)) == 1);
  }
}

TEST_CASE("the keyword list is sorted by name and has no duplicates") {
  const std::vector<prologd::KeywordInfo> keywords = prologd::reservedKeywords();
  REQUIRE(std::is_sorted(keywords.begin(), keywords.end(),
                         [](const prologd::KeywordInfo& left,
                            const prologd::KeywordInfo& right) {
                           return left.name < right.name;
                         }));
  std::set<std::string_view> seen;
  for (const prologd::KeywordInfo& keyword : keywords) {
    REQUIRE(seen.insert(keyword.name).second);
  }
}

TEST_CASE("every registered built-in is reserved") {
  // The other direction of the drift check: a built-in that the lexer does not
  // reserve would be parsed as a variable and never called.
  for (const std::string& name : prologd::builtinNames()) {
    INFO("name: " << name);
    REQUIRE(prologd::isReservedBuiltinName(name));
  }
}

TEST_CASE("reserved names are classified") {
  // `mod` and `div` are infix operators, `ИМПОРТ` is the loader's directive and
  // everything else must be callable.  A reserved name with no arity and no
  // classification is exactly the drift this test exists to catch.
  for (const prologd::KeywordInfo& keyword : prologd::reservedKeywords()) {
    INFO("name: " << std::string(keyword.name)
                  << " kind: " << std::string(prologd::keywordKindName(keyword.kind)));
    if (keyword.kind == prologd::KeywordKind::Predicate) {
      REQUIRE((keyword.variadic || !keyword.arities.empty()));
    } else {
      REQUIRE(keyword.arities.empty());
      REQUIRE_FALSE(keyword.variadic);
    }
  }
}

TEST_CASE("keyword arities come from the dispatch table") {
  const std::vector<prologd::KeywordInfo> keywords = prologd::reservedKeywords();

  const prologd::KeywordInfo* findall = findKeyword(keywords, "НАЙТИВСЕ");
  REQUIRE(findall != nullptr);
  REQUIRE(findall->kind == prologd::KeywordKind::Predicate);
  REQUIRE(findall->arities == std::vector<std::size_t>{3});

  // `ВЫП`/`call` are `call/N`: variadic from arity 1, so the table carries the
  // flag rather than an arity list (task_43).
  const prologd::KeywordInfo* call = findKeyword(keywords, "ВЫП");
  REQUIRE(call != nullptr);
  REQUIRE(call->variadic);
  REQUIRE(call->arities.empty());
  const prologd::KeywordInfo* english = findKeyword(keywords, "call");
  REQUIRE(english != nullptr);
  REQUIRE(english->variadic);

  // Two arities are reported in ascending order, not in registration order.
  const prologd::KeywordInfo* multiplication = findKeyword(keywords, "УМНОЖЕНИЕ");
  REQUIRE(multiplication != nullptr);
  REQUIRE(multiplication->arities == std::vector<std::size_t>{3, 4});

  // `ВЫВОД` is variadic: no arities, and it must still be listed.
  const prologd::KeywordInfo* output = findKeyword(keywords, "ВЫВОД");
  REQUIRE(output != nullptr);
  REQUIRE(output->kind == prologd::KeywordKind::Predicate);
  REQUIRE(output->variadic);
  REQUIRE(output->arities.empty());

  // `ПЕРВОЕ` joined it in task_51: any number of goals from one.
  const prologd::KeywordInfo* first = findKeyword(keywords, "ПЕРВОЕ");
  REQUIRE(first != nullptr);
  REQUIRE(first->kind == prologd::KeywordKind::Predicate);
  REQUIRE(first->variadic);
  REQUIRE(first->arities.empty());
  const prologd::KeywordInfo* firstEnglish = findKeyword(keywords, "first");
  REQUIRE(firstEnglish != nullptr);
  REQUIRE(firstEnglish->variadic);
  REQUIRE(firstEnglish->arities.empty());

  // `ВЫВОДПС` is the third variadic name (task_53): `ВЫВОД` plus `ПС`.  The
  // zero-argument «just a newline» case stays `ПС`/`nl`, so this one starts at
  // one argument like the other two.
  const prologd::KeywordInfo* writeLine = findKeyword(keywords, "ВЫВОДПС");
  REQUIRE(writeLine != nullptr);
  REQUIRE(writeLine->kind == prologd::KeywordKind::Predicate);
  REQUIRE(writeLine->variadic);
  REQUIRE(writeLine->arities.empty());
  const prologd::KeywordInfo* writeLineEnglish = findKeyword(keywords, "writeln");
  REQUIRE(writeLineEnglish != nullptr);
  REQUIRE(writeLineEnglish->variadic);
  REQUIRE(writeLineEnglish->arities.empty());

  // A latin name that is both a type word and a unary predicate.  The dialect
  // has two such checks: `integer` is the strict type test (a whole-valued real
  // is not an integer), `is_whole` asks whether a value *can* be taken as one.
  const prologd::KeywordInfo* integer = findKeyword(keywords, "integer");
  REQUIRE(integer != nullptr);
  REQUIRE(integer->arities == std::vector<std::size_t>{1});

  const prologd::KeywordInfo* isWhole = findKeyword(keywords, "is_whole");
  REQUIRE(isWhole != nullptr);
  REQUIRE(isWhole->arities == std::vector<std::size_t>{1});

  const prologd::KeywordInfo* modulus = findKeyword(keywords, "mod");
  REQUIRE(modulus != nullptr);
  REQUIRE(modulus->kind == prologd::KeywordKind::Operator);

  const prologd::KeywordInfo* import = findKeyword(keywords, "ИМПОРТ");
  REQUIRE(import != nullptr);
  REQUIRE(import->kind == prologd::KeywordKind::Directive);
}

TEST_CASE("an unknown name carries no arity information") {
  const prologd::BuiltinArities nothing = prologd::builtinArities("такого_нет");
  REQUIRE(nothing.arities.empty());
  REQUIRE_FALSE(nothing.variadic);
  REQUIRE(prologd::findBuiltin("такого_нет", 1) == nullptr);
  REQUIRE(findKeyword(prologd::reservedKeywords(), "такого_нет") == nullptr);
}

TEST_CASE("a retired name is not offered, its replacement is") {
  const std::vector<prologd::KeywordInfo> keywords = prologd::reservedKeywords();
  const prologd::KeywordInfo* first = findKeyword(keywords, "ПЕРВОЕ");
  REQUIRE(first != nullptr);
  REQUIRE(first->kind == prologd::KeywordKind::Predicate);
  REQUIRE(first->variadic);  // any number of goals from one (task_51)
  REQUIRE(first->arities.empty());

  // The spellings the language has retired stay reserved for the lexer (so an
  // old call gets a message instead of becoming a variable), but the keyword
  // table — completion, colouring, `--list-keywords` — must not show them.
  REQUIRE(findKeyword(keywords, "ИЛИ") == nullptr);
  REQUIRE(findKeyword(keywords, "or") == nullptr);
  REQUIRE(findKeyword(keywords, "НАЙТИВСЁ") == nullptr);
  REQUIRE(prologd::isReservedBuiltinName("ИЛИ"));
  REQUIRE(prologd::isReservedBuiltinName("НАЙТИВСЁ"));
}
