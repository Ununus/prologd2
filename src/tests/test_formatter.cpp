#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "prlib/formatter.hpp"

using namespace prologd;

namespace {

FormatResult format(const std::string& source, FormatOptions options = {}) {
  return formatSource(source, options);
}

FormatOptions hard(std::size_t width = 80) {
  FormatOptions options;
  options.mode = FormatMode::Hard;
  options.width = width;
  return options;
}

std::string readFile(const std::filesystem::path& path) {
  std::ifstream stream(path, std::ios::binary);
  REQUIRE(stream.good());
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return buffer.str();
}

}  // namespace

TEST_CASE("the soft shape of the acceptance example comes out byte for byte") {
  // The task wrote the head as `Правило`; a capital initial is a variable in
  // this dialect, so the language's own spelling of the example is lowercase —
  // the columns are the same, and the shape is the one that was asked for.
  const std::string source =
      "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
      "функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n";
  const std::string expected =
      "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
      "\tфункция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text == expected);
  REQUIRE(result.changed);
}

TEST_CASE("the hard shape puts one goal of a body per line") {
  const std::string source =
      "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
      "функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n";
  const std::string expected =
      "правило(а,б,с):-функция1(а,б,с),\n"
      "\tфункция2(а,б,с),\n"
      "\tфункция3(а,б,с),\n"
      "\tфункция4(а,б,с),\n"
      "\tфункция5(а,б,с),\n"
      "\tфункция6(а,б,с).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == expected);
}

TEST_CASE("a space after the last comma does not survive") {
  const std::string source = "факт(1).   \nцель(Х):-часть(Х), два(Х). \n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == "факт(1).\nцель(Х):-часть(Х),\n\tдва(Х).\n");
  REQUIRE(result.text.find(" \n") == std::string::npos);
}

TEST_CASE("a one-goal clause is already formatted") {
  const std::string source = "факт(1).\nсчёт(Х):-факт(Х).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("comments stay on their own side of a break") {
  const std::string source =
      "% шапка файла\n"
      "факт(1). % хвост\n"
      "\n"
      "\n"
      "% перед правилом\n"
      "цель(Х):-часть(Х),\n"
      "    % пояснение к следующей цели\n"
      "    два(Х).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  const std::string expected =
      "% шапка файла\n"
      "факт(1). % хвост\n"
      "\n"
      "% перед правилом\n"
      "цель(Х):-часть(Х),\n"
      "\t% пояснение к следующей цели\n"
      "\tдва(Х).\n";
  REQUIRE(result.text == expected);
}

TEST_CASE("the bytes of every token are copied verbatim") {
  const std::string source =
      "странно('атом с, запятой', \"строка с \\\"кавычкой\\\"\").\n"
      "расчёт(Х):-БОЛЬШЕ(Х, #1+2#), МЕНЬШЕ(Х, 'эт,о').\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("a semicolon keeps the spaces the corpus gives it") {
  const std::string source = "выбор(Х):-РАВНО(Х, 1);РАВНО(Х, 2).\n?цена(Т, 40) ; цена(Т, 500).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          "выбор(Х):-РАВНО(Х, 1) ; РАВНО(Х, 2).\n?цена(Т, 40) ; цена(Т, 500).\n");
}

TEST_CASE("an arrow rule formats like a colon-dash rule") {
  const std::string source = "правило(Х)<-часть(Х),   ещё(Х).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == "правило(Х)<-часть(Х),\n\tещё(Х).\n");
}

TEST_CASE("a directive keeps its space and a query stays glued") {
  const std::string source =
      "?ВЕРСИЯ.\n"
      ":- ИМПОРТ(\"library.pld\").\n"
      "%? НЕ(ЛОЖЬ).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          "?ВЕРСИЯ.\n"
          ":- ИМПОРТ(\"library.pld\").\n"
          "%? НЕ(ЛОЖЬ).\n");
}

TEST_CASE("a source that does not parse comes back untouched, with diagnostics") {
  const std::string source = "цель(Х:-часть(Х).\n";
  const FormatResult result = format(source, hard());
  REQUIRE_FALSE(result.ok());
  REQUIRE_FALSE(result.diagnostics.empty());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("blank lines collapse between clauses and survive inside one") {
  const std::string source =
      "первый(1).\n"
      "\n"
      "\n"
      "\n"
      "второй(Х):-часть(Х),\n"
      "\n"
      "\tещё(Х).\n"
      "\n"
      "\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          "первый(1).\n"
          "\n"
          "второй(Х):-часть(Х),\n"
          "\n"
          "\tещё(Х).\n");
}

TEST_CASE("formatting is idempotent for every example program") {
  namespace fs = std::filesystem;
  const fs::path root(PROLOGD_TEST_DATA_DIR);
  std::vector<fs::path> files;
  for (const auto& entry : fs::recursive_directory_iterator(root)) {
    if (entry.is_regular_file() && entry.path().extension() == ".pld") {
      files.push_back(entry.path());
    }
  }
  REQUIRE(files.size() >= 10);
  for (const fs::path& path : files) {
    const std::string source = readFile(path);
    for (const FormatOptions& options : {FormatOptions{}, hard()}) {
      const FormatResult once = format(source, options);
      INFO("file: " << path.string());
      REQUIRE(once.ok());
      const FormatResult twice = format(once.text, options);
      REQUIRE(twice.ok());
      REQUIRE(twice.text == once.text);
    }
  }
}

TEST_CASE("a fragment is formatted up to its last complete goal") {
  FormatOptions options = hard();
  options.selection_only = true;
  const std::string source = "факт(1).\nсчёт(Х):-факт(Х), ещё(Х), оста";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text == "факт(1).\nсчёт(Х):-факт(Х),\n\tещё(Х), оста");
  REQUIRE(result.changed);
}

TEST_CASE("a complete selection is just formatted") {
  FormatOptions options = hard();
  options.selection_only = true;
  const std::string source = "счёт(Х):-факт(Х), ещё(Х).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text == "счёт(Х):-факт(Х),\n\tещё(Х).\n");
}

TEST_CASE("a fragment with nothing complete in it is left alone") {
  FormatOptions options = hard();
  options.selection_only = true;
  const std::string source = "ещё(Х), оста";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("none mode touches nothing at all") {
  FormatOptions options;
  options.mode = FormatMode::None;
  const std::string source = "цель(Х) :-  часть(Х),   ещё(Х).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}
