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
  // The head stands alone: the *first* goal was the one glued to it, and a goal
  // that hides at the end of the head's line is the one a reader skips (task_47).
  const std::string expected =
      "правило(а,б,с):-\n"
      "\tфункция1(а,б,с),\n"
      "\tфункция2(а,б,с),\n"
      "\tфункция3(а,б,с),\n"
      "\tфункция4(а,б,с),\n"
      "\tфункция5(а,б,с),\n"
      "\tфункция6(а,б,с).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == expected);
}

TEST_CASE("the hard shape leaves a directive and a query on their line") {
  // There is no head to stand alone: `:-` or `?` on a line of its own is noise,
  // and a directive is one command with its arguments.  A query is one question,
  // so its goals stay beside `?` too — the window runs a question from a *line*
  // (task_36), and a question split in two cannot be clicked (task_47).
  const std::string source =
      ":- ИМПОРТ(\"lib.pld\").\n"
      ":- РАВНО(Х, 1).\n"
      "?цель(Х), другая(Х).\n"
      "факт(1).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("a space after the last comma does not survive") {
  const std::string source = "факт(1).   \nцель(Х):-часть(Х), два(Х). \n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == "факт(1).\nцель(Х):-\n\tчасть(Х),\n\tдва(Х).\n");
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

TEST_CASE("a string escape keeps its two bytes of source") {
  // The lexer decodes `\n` into one character, so the formatter has to measure
  // the raw span again — otherwise it would cut the literal short and change
  // the program it was asked to lay out.
  const std::string source = "текст(\"1\\n2\\\\3\\t4\\\"5\").\n";
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

TEST_CASE("an arrow keeps the spaces the corpus gives it") {
  // `->` is spaced like `;` (task_85): one space on either side, whatever the
  // source had.  It is a break point of the hard shape as well, and a query
  // stays on its own line either way.
  const std::string source =
      "выбор(Х):-дешёвый(Х)->надёжный(Х);отложить(Х).\n"
      "?цена(Т, 40)->Т = дорого;Т = иначе.\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          "выбор(Х):-дешёвый(Х) -> надёжный(Х) ; отложить(Х).\n"
          "?цена(Т, 40) -> Т = дорого ; Т = иначе.\n");

  const FormatResult broken = format(source, hard());
  REQUIRE(broken.ok());
  REQUIRE(broken.text ==
          "выбор(Х):-\n"
          "\tдешёвый(Х) ->\n"
          "\tнадёжный(Х) ;\n"
          "\tотложить(Х).\n"
          "?цена(Т, 40) -> Т = дорого ; Т = иначе.\n");
}

TEST_CASE("an arrow rule formats like a colon-dash rule") {
  const std::string source = "правило(Х)<-часть(Х),   ещё(Х).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == "правило(Х)<-\n\tчасть(Х),\n\tещё(Х).\n");
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

TEST_CASE("`\\+` stays one operator in every shape") {
  // The lexer reads `\+` whole (task_55), so the formatter must not treat the
  // backslash as a goal of its own and must not break between the operator and
  // the goal it negates — in any mode.
  const std::string source = "цель(Х) :- \\+ часть(Х), ещё(Х).\n";
  for (const FormatOptions& options : {FormatOptions{}, hard(), hard(20)}) {
    const FormatResult result = format(source, options);
    REQUIRE(result.ok());
    REQUIRE(result.text.find("\\+ часть(Х)") != std::string::npos);
  }
}

TEST_CASE("a query and a directive keep their one line") {
  // A query is a question and a directive is an instruction: neither has a head
  // or a body to lay out, and the window's margin marker reads a *line*
  // (task_36), so a break inside one is a question nobody can click.  The width
  // therefore never opens them, however narrow it is (task_47).
  const std::string source =
      ":- ИМПОРТ(\"длинное_имя_библиотеки_для_проверки.pld\", "
      "\"длинное_имя_модуля_для_проверки_импорта\").\n"
      "?первая_цель(Очень_длинный_аргумент), вторая_цель(Ещё_Длиннее_Аргумент), "
      "третья_цель(Х).\n";
  FormatOptions narrow;
  narrow.width = 20;
  for (const FormatOptions& options : {FormatOptions{}, narrow, hard(), hard(20)}) {
    const FormatResult result = format(source, options);
    REQUIRE(result.ok());
    REQUIRE_FALSE(result.changed);
    REQUIRE(result.text == source);
  }
}

TEST_CASE("the names marker is laid out like any other directive") {
  // The modes are gone, so the line declares nothing — but it is still a call the
  // parser reads, and laying text out is not loading it: the formatter leaves the
  // line alone and it is the loader that refuses the file, with the message of a
  // retired name (see the engine's own checks).
  const std::string source = ":- ИМЕНА(1).\nдлинное:-РАВНО(Сумма, 5).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text.rfind(":- ИМЕНА(1).", 0) == 0);
}

TEST_CASE("an apostrophe is a quote and never part of a name") {
  // The old dialect's long variable names are gone with its mode: `Сумма'` is the
  // name `Сумма` and an unterminated quoted atom, so a file written that way does
  // not parse and the formatter hands it back as it is.
  const std::string source = "длинное:-РАВНО(Сумма',5).\n";
  const FormatResult result = format(source);
  REQUIRE_FALSE(result.ok());
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.diagnostics.empty());
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
          "второй(Х):-\n"
          "\tчасть(Х),\n"
          "\n"
          "\tещё(Х).\n");
}

TEST_CASE("formatting is idempotent for every example program") {
  namespace fs = std::filesystem;
  const fs::path root(PROLOGD_TEST_DATA_DIR);
  std::vector<fs::path> files;
  for (const auto& entry : fs::recursive_directory_iterator(root)) {
    if (!entry.is_regular_file() || entry.path().extension() != ".pld") {
      continue;
    }
    files.push_back(entry.path());
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

TEST_CASE("the comparison signs survive formatting") {
  // task_52: the signs are ordinary tokens to the formatter — the layout is
  // rewritten, the text of the goals is not.
  const std::string source =
      "правило(Х, У):-Х = #1 + 1#, У >= 2, Х =< У, ЛОЖЬ ; Х > 0.\n";
  const FormatResult once = format(source, hard());
  REQUIRE(once.ok());
  REQUIRE(once.text.find("Х = #1 + 1#") != std::string::npos);
  REQUIRE(once.text.find("У >= 2") != std::string::npos);
  REQUIRE(once.text.find("Х =< У") != std::string::npos);
  const FormatResult twice = format(once.text, hard());
  REQUIRE(twice.ok());
  REQUIRE(twice.text == once.text);
}

TEST_CASE("a source with a block comment comes back untouched") {
  // task_92: the layout rules were written for `%` comments, and a `/* … */`
  // spans lines — a rewrite would either lose the comment or move it into a
  // clause it does not belong to.  The honest answer is to leave the file as
  // the author wrote it (and say the same about any other layout choice).
  const std::string source = "p(X) :-\n  /* пояснение */\n  q(X).\n";
  const FormatResult result = format(source, hard());
  REQUIRE(result.ok());
  REQUIRE(result.text == source);
}

TEST_CASE("the standard-order signs survive formatting") {
  // task_90: the signs are ordinary tokens to the formatter — the layout is
  // rewritten, the text of the goals is not, and a sign used as an *atom*
  // (`compare(<, А, Б)`, `А = @<`) keeps its place too.
  const std::string source =
      "правило(А, Б):-А @< Б, compare(<, А, Б), А @>= Б ; А = @<.\n";
  const FormatResult once = format(source, hard());
  REQUIRE(once.ok());
  REQUIRE(once.text.find("А @< Б") != std::string::npos);
  REQUIRE(once.text.find("compare(<, А, Б)") != std::string::npos);
  REQUIRE(once.text.find("А @>= Б") != std::string::npos);
  REQUIRE(once.text.find("А = @<") != std::string::npos);
  const FormatResult twice = format(once.text, hard());
  REQUIRE(twice.ok());
  REQUIRE(twice.text == once.text);
}

TEST_CASE("every shipped program is already in the standard shape") {
  // `prologd --format` is the layout the repository keeps its own programs in,
  // and the lessons are the widest corpus of real text there is (task_47): the
  // moment one of them drifts, this check says which.  `test_lessons.cpp` is what
  // proves that formatting a lesson did not move a printed line.
  //
  // `stdlib` is the second shipped folder — the standard library travels beside
  // the executable — and it obeys the same rule: a library file is written the
  // way the formatter writes it, or a reader who formats one gets a diff for a
  // change of nothing.
  namespace fs = std::filesystem;
  const std::vector<fs::path> roots = {fs::path(PROLOGD_TEST_DATA_DIR),
                                       fs::path(PROLOGD_STDLIB_DIR)};
  std::size_t checked = 0;
  for (const fs::path& root : roots) {
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
      if (!entry.is_regular_file() || entry.path().extension() != ".pld") {
        continue;
      }
      const std::string source = readFile(entry.path());
      INFO("file: " << entry.path().string());
      const FormatResult result = format(source);
      REQUIRE(result.ok());
      REQUIRE_FALSE(result.changed);
      REQUIRE(result.text == source);
      ++checked;
    }
  }
  REQUIRE(checked >= 25);
}

TEST_CASE("a fragment is formatted up to its last complete goal") {
  FormatOptions options = hard();
  options.selection_only = true;
  const std::string source = "факт(1).\nсчёт(Х):-факт(Х), ещё(Х), оста";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text == "факт(1).\nсчёт(Х):-\n\tфакт(Х),\n\tещё(Х), оста");
  REQUIRE(result.changed);
}

TEST_CASE("a complete selection is just formatted") {
  FormatOptions options = hard();
  options.selection_only = true;
  const std::string source = "счёт(Х):-факт(Х), ещё(Х).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text == "счёт(Х):-\n\tфакт(Х),\n\tещё(Х).\n");
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

TEST_CASE("the soft mode turns a hard layout back into the soft shape") {
  const std::string source =
      "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),\n"
      "функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).\n";
  const FormatResult soft = format(source);
  const FormatResult hard_once = format(source, hard());
  REQUIRE(soft.ok());
  REQUIRE(hard_once.ok());
  const FormatResult back = format(hard_once.text);
  REQUIRE(back.ok());
  REQUIRE(back.text == soft.text);
  REQUIRE(back.changed);
}

TEST_CASE("soft does not keep an author break that fits on one line") {
  // The lines are built again rather than kept: a break the author made cannot
  // be told apart from one the hard mode wrote, and keeping them is what made
  // «из жёсткого обратно в мягкое» impossible.
  const std::string source = "счёт(Х):-часть(Х),\n    ещё(Х).\n";
  const FormatResult result = format(source);
  REQUIRE(result.ok());
  REQUIRE(result.text == "счёт(Х):-часть(Х), ещё(Х).\n");
}

TEST_CASE("the one-line mode joins the body whatever the width") {
  FormatOptions options;
  options.mode = FormatMode::Line;
  options.width = 20;  // not consulted: «в одну строку» means one line
  const std::string source =
      "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с),\n"
      "\tфункция3(а,б,с).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          "правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с).\n");
  // A comment still owns its line: a line cannot hold one and go on.
  FormatResult commented = format("счёт(Х):-часть(Х),\n\t% пояснение\n\tещё(Х).\n", options);
  REQUIRE(commented.ok());
  REQUIRE(commented.text == "счёт(Х):-часть(Х),\n\t% пояснение\n\tещё(Х).\n");
}

TEST_CASE("none mode touches nothing at all") {
  FormatOptions options;
  options.mode = FormatMode::None;
  const std::string source = "цель(Х) :-  часть(Х),   ещё(Х).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.text == source);
  REQUIRE_FALSE(result.changed);
}

TEST_CASE("a last line without a final newline survives the formatter") {
  // The end-of-file marker used to be counted as a statement, so everything
  // after the last dot was a gap *between* statements — and the formatter reads
  // the last line of such a gap as the indentation in front of the next
  // statement.  A text that does not end with a newline therefore lost its last
  // line: the owner formatted two selected comment lines and the second one
  // disappeared (task_114).
  REQUIRE(format("% один\n% два").text == "% один\n% два\n");
  REQUIRE(format("факт(1).\n% один").text == "факт(1).\n% один\n");
  REQUIRE(format("факт(1).\n\n% один\n% два").text == "факт(1).\n\n% один\n% два\n");
  // A terminated last line is nothing special, and neither is a fragment: the
  // cut of a selection ends wherever the caret was.
  REQUIRE(format("% один\n% два\n").text == "% один\n% два\n");
  FormatOptions fragment;
  fragment.selection_only = true;
  REQUIRE(format("% один\n% два", fragment).text == "% один\n% два\n");
}
