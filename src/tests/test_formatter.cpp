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

TEST_CASE("the first line of a file decides how its names are read") {
  // `Сумма'` is one variable in the old dialect and an unterminated quote in mode
  // 0, so the very same clause parses only when the file says so (task_67).  The
  // marker also has to *stay* the first line of the output: it is an ordinary
  // statement.
  const std::string clause = "длинное:-РАВНО(Сумма',5).\n";
  const FormatResult declared = format(":- ИМЕНА(2).\n" + clause);
  REQUIRE(declared.ok());
  REQUIRE(declared.text.find("Сумма'") != std::string::npos);
  REQUIRE(declared.text.rfind(":- ИМЕНА(2).", 0) == 0);

  // task_77: `2` is a spelling of `1` now, so the same file whose first line says
  // `1` comes back the same way, marker and all.
  const FormatResult spelled_one = format(":- ИМЕНА(1).\n" + clause);
  REQUIRE(spelled_one.ok());
  std::string expected = declared.text;
  expected.replace(0, std::string(":- ИМЕНА(2).").size(), ":- ИМЕНА(1).");
  REQUIRE(spelled_one.text == expected);

  const FormatResult bare = format(clause);
  REQUIRE_FALSE(bare.ok());

  // The option is the fallback for a text without a marker — the window's row and
  // the CLI's `--vars`.
  FormatOptions options;
  options.variables = prologd::VariableMode::Old;
  REQUIRE(format(clause, options).ok());
}

TEST_CASE("a string constant of the old dialect keeps its span") {
  // In mode 1 a bare capitalised name is a string constant (task_67), and the
  // formatter measures every token's raw span: assuming a quote there swallowed
  // the rest of the line, and the formatted text of the old lessons came back
  // twenty times longer than the input.
  const std::string program = ":- ИМЕНА(1).\nстудент(Вова).\nстудент(Боря).\n";
  const FormatResult formatted = format(program);
  REQUIRE(formatted.ok());
  REQUIRE(formatted.text == program);
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
  // `examples/lessons/_old` keeps the ported originals as they were written,
  // so their spellings are the ones the port changed (`;` as a terminator,
  // `1.` for 1.0 — task_52) and a few of them no longer parse.  The formatter
  // refuses a source it cannot parse, so they are not its business.
  const fs::path archived = root / "lessons" / "_old";
  // `examples/prologd` is that same story for a whole folder: the original
  // dialect's own programs (task_86), copied as they were written.  The folder is
  // compared by its *first path component*, not by a prefix of the whole path, so
  // a name that merely begins with `prologd` cannot slip into the skip.
  const fs::path original("prologd");
  std::vector<fs::path> files;
  for (const auto& entry : fs::recursive_directory_iterator(root)) {
    if (!entry.is_regular_file() || entry.path().extension() != ".pld") {
      continue;
    }
    if (entry.path().string().find(archived.string()) != std::string::npos) {
      continue;
    }
    const fs::path relative = entry.path().lexically_relative(root);
    if (!relative.empty() && *relative.begin() == original) {
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
  // `prologu --format` is the layout the repository keeps its own programs in,
  // and the lessons are the widest corpus of real text there is (task_47): the
  // moment one of them drifts, this check says which.  `examples/lessons/_old`
  // holds the ported originals for comparison with the port, so it keeps their
  // spelling rather than the port's; `test_lessons.cpp` is what proves that
  // formatting a lesson did not move a printed line.
  //
  // `stdlib` is the second shipped folder — the standard library travels beside
  // the executable — and it obeys the same rule: a library file is written the
  // way the formatter writes it, or a reader who formats one gets a diff for a
  // change of nothing.
  namespace fs = std::filesystem;
  const std::vector<fs::path> roots = {fs::path(PROLOGD_TEST_DATA_DIR),
                                       fs::path(PROLOGD_STDLIB_DIR)};
  // The original dialect's own folder is left alone here for the same reason as
  // `_old` above: those programs are kept exactly as they were written (task_86),
  // and their spelling is what the port changed.
  const fs::path top(PROLOGD_TEST_DATA_DIR);
  const fs::path original("prologd");
  std::size_t checked = 0;
  for (const fs::path& root : roots) {
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
      if (!entry.is_regular_file() || entry.path().extension() != ".pld") {
        continue;
      }
      if (entry.path().parent_path().filename() == "_old") {
        continue;
      }
      const fs::path relative = entry.path().lexically_relative(top);
      if (!relative.empty() && *relative.begin() == original) {
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

// ---------------------------------------------------------------------------
// The naming conversion (task_99)
// ---------------------------------------------------------------------------

namespace {

/// «Print the names in `target` mode», the way `--names` and the window ask for it.
FormatOptions toNames(VariableMode target) {
  FormatOptions options;
  options.names_out = target;
  return options;
}

}  // namespace

TEST_CASE("an old-dialect program is printed in the ISO spelling") {
  // The rules of the old dialect, read backwards: `Х` and `х` are variables and
  // `Str` is a string constant there, so ISO gets numbered variables and the
  // constant in quotes; `var1'` loses its apostrophe, and `_Пер'` is `_Пер` already.
  const std::string source =
      ":- ИМЕНА(1).\n"
      "пример(Х,у):-функ(Str, \"Str\", атом, var1', Var2').\n"
      "конфликты(Х,х,Х',х', X_3).\n"
      "подчёркивание(_Пер, _Пер').\n";
  const FormatResult result = format(source, toNames(VariableMode::Iso));
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          ":- ИМЕНА(0).\n"
          "пример(Х_1,У):-функ(\"Str\", \"Str\", атом, Var1, Var2).\n"
          "конфликты(Х_1,Х_2,Х_3,Х_4, \"X_3\").\n"
          "подчёркивание(_Пер, _Пер).\n");
  REQUIRE(result.changed);
}

TEST_CASE("variables that share a base are numbered in the order they are written") {
  // `Х` and `х` would both be `X`, so a shared base is numbered; a base of its own
  // is printed bare (`Var1`).
  const std::string source =
      ":- ИМЕНА(1).\n"
      "пара(Х,х,Х',х').\n"
      "своё(var1',Var2').\n";
  const FormatResult result = format(source, toNames(VariableMode::Iso));
  REQUIRE(result.ok());
  REQUIRE(result.text == ":- ИМЕНА(0).\nпара(Х_1,Х_2,Х_3,Х_4).\nсвоё(Var1,Var2).\n");
}

TEST_CASE("an ISO program is printed in the old dialect's spelling") {
  // One letter and a letter with a trailing `_` are variables in both dialects, so
  // they stay; everything else gets the apostrophe that makes it a variable there.
  // A string is a string in both, and a quoted atom needs no change either.
  const std::string source =
      ":- ИМЕНА(0).\n"
      "пример(X,Y):-функ(\"Str\", атом, Var1).\n"
      "счёт(Сумма,X_):-сумма(Сумма).\n"
      "кавычки(_Пер,'Тоже атом').\n";
  const FormatResult result = format(source, toNames(VariableMode::Old));
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          ":- ИМЕНА(1).\n"
          "пример(X,Y):-функ(\"Str\", атом, Var1').\n"
          "счёт(Сумма',X_):-сумма(Сумма').\n"
          "кавычки(_Пер,'Тоже атом').\n");
}

TEST_CASE("a converted answer says which mode it is in, marker or not") {
  // A file read by `--vars 1` has no marker of its own; the answer gets one, so a
  // converted program does not depend on how its reader was started.  The single
  // letter is a *variable* in the old dialect, so it comes back capitalised.
  FormatOptions options = toNames(VariableMode::Iso);
  options.variables = VariableMode::Old;
  const FormatResult added = format("пример(а).\n", options);
  REQUIRE(added.ok());
  REQUIRE(added.text == ":- ИМЕНА(0).\nпример(А).\n");

  const FormatResult back = format(added.text, toNames(VariableMode::Old));
  REQUIRE(back.ok());
  REQUIRE(back.text == ":- ИМЕНА(1).\nпример(А).\n");
}

TEST_CASE("the way back keeps the names it can and marks the rest") {
  // A round trip cannot give back `Х`/`х`: they were numbered, and ISO has no way
  // to say that one name was two variables.  What it does keep is every name that
  // was already an old-dialect variable, and the string constant.
  const std::string iso = ":- ИМЕНА(0).\nпример(X_1,Y,\"Str\",_Пер).\n";
  const FormatResult back = format(iso, toNames(VariableMode::Old));
  REQUIRE(back.ok());
  REQUIRE(back.text == ":- ИМЕНА(1).\nпример(X_1',Y,\"Str\",_Пер).\n");
}

TEST_CASE("a one-letter atom takes quotes for the old dialect, which reads it as a variable") {  // In ISO `?одно(а, а).` asks about a *constant*, while the old dialect reads one
  // letter as a variable: without the quotes the question would change its meaning
  // and answer `а=_1` instead of ДА (the owner's example, part 167).  A letter with
  // a trailing `_` is one of the old dialect's variables too, so it takes quotes as
  // well; `а1` and `атом` are names in both dialects and stay bare, a quoted atom
  // already carries its quotes, and a variable keeps the apostrophe it gets.  A
  // one-letter *functor* is quoted the same way — the original reads `'а'(1)`.
  const std::string source =
      ":- ИМЕНА(0).\n"
      "одно(Значение, Значение).\n"
      "?одно(а, а).\n"
      "смесь(Э, а_, а1, атом, 'а').\n"
      "а(1).\n";
  const FormatResult result = format(source, toNames(VariableMode::Old));
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          ":- ИМЕНА(1).\n"
          "одно(Значение', Значение').\n"
          "?одно('а', 'а').\n"
          "смесь(Э, 'а_', а1, атом, 'а').\n"
          "'а'(1).\n");
}

// ---------------------------------------------------------------------------
// The dialect conversion (task_101)
// ---------------------------------------------------------------------------

namespace {

/// «Print the built-ins in `target` language», the way `--dialect` asks for it.
FormatOptions toDialect(Dialect target) {
  FormatOptions options;
  options.dialect_out = target;
  return options;
}

}  // namespace

TEST_CASE("a Russian program is printed in the English names and signs") {
  // Every rule of the direction, in one program.  `ВЫВОД`/`ВЫВОДПС`/`ПС`/`НАЙТИВСЕ`
  // come from the alias table; `РАВНО` is `=` (and `is` when its right operand is a
  // marked expression — the two are one term, `is` differs only by that wrapper),
  // `БОЛЬШЕ`/`МЕНЬШЕ` are the signs, and `НЕ` is ISO's `\+`.  `ИМПОРТ` and `ВЫП` are
  // answered outside the alias table and are listed beside it.  `ИЛИ` has no
  // English name, so it stays; a user's own `вывод_свой` is not a built-in either.
  const std::string source =
      ":- ИМЕНА(0).\n"
      ":- ИМПОРТ(\"библиотека.pld\").\n"
      "свой :- ВЫВОД(1), ВЫВОДПС(2), ПС.\n"
      "вывод_свой :- ВЫВОД(3).\n"
      "оба :- ИЛИ(ИСТИНА, ЛОЖЬ).\n"
      "вызов(G) :- ВЫП(G).\n"
      "больше(X, Y) :- БОЛЬШЕ(X, Y).\n"
      "меньше(X, Y) :- МЕНЬШЕ(X, Y).\n"
      "равно(X, Y) :- РАВНО(X, Y).\n"
      "сумма(X, Y) :- РАВНО(X, #Y + 1#).\n"
      "нет(X) :- НЕ(РАВНО(X, 1)).\n"
      "?НАЙТИВСЕ(X, (число(X), БОЛЬШЕ(X, 2)), L).\n";
  const FormatResult result = format(source, toDialect(Dialect::English));
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          ":- ИМЕНА(0).\n"
          ":- import(\"библиотека.pld\").\n"
          "свой:-write(1), writeln(2), nl.\n"
          "вывод_свой:-write(3).\n"
          "оба:-ИЛИ(true, fail).\n"
          "вызов(G):-call(G).\n"
          "больше(X, Y):-X > Y.\n"
          "меньше(X, Y):-X < Y.\n"
          "равно(X, Y):-X = Y.\n"
          "сумма(X, Y):-X is Y + 1.\n"
          "нет(X):-\\+ X = 1.\n"
          "?findall(X, (число(X), X > 2), L).\n");
}

TEST_CASE("an English program is printed in the Russian names and signs") {
  // The way back: the signs become the calls this dialect spells them with, and
  // `is` puts its operand back inside `#…#`, where the expression wrapper lives.
  const std::string source =
      ":- ИМЕНА(0).\n"
      ":- import(\"библиотека.pld\").\n"
      "свой :- write(1), writeln(2), nl.\n"
      "вызов(G) :- call(G).\n"
      "равно(X, Y) :- X = Y.\n"
      "сумма(X, Y) :- X is Y + 1.\n"
      "нет(X) :- \\+ X = 1.\n"
      "?findall(X, (число(X), X > 2), L).\n";
  const FormatResult result = format(source, toDialect(Dialect::Russian));
  REQUIRE(result.ok());
  REQUIRE(result.text ==
          ":- ИМЕНА(0).\n"
          ":- ИМПОРТ(\"библиотека.pld\").\n"
          "свой:-ВЫВОД(1), ВЫВОДПС(2), ПС.\n"
          "вызов(G):-ВЫП(G).\n"
          "равно(X, Y):-РАВНО(X, Y).\n"
          "сумма(X, Y):-РАВНО(X, #Y + 1#).\n"
          "нет(X):-НЕ(РАВНО(X, 1)).\n"
          "?НАЙТИВСЕ(X, (число(X), БОЛЬШЕ(X, 2)), L).\n");
}

TEST_CASE("a dialect conversion says nothing it cannot say, and keeps every comment") {
  // A call the target language cannot write as a sign keeps its name: a comment
  // stands inside it, its arity is not the sign's, or one of its operands is not
  // an operand.  Renaming is still exact — `equal/2` is `РАВНО/2` — so nothing is
  // ever lost, only left spelled out.
  const std::string source =
      ":- ИМЕНА(0).\n"
      "коммент(X, Y) :- РАВНО(X, % почему\n"
      "                        Y).\n"
      "странно(X) :- БОЛЬШЕ(X).\n"
      "цепочка(X, Y) :- РАВНО(РАВНО(X, Y), Z).\n";
  const FormatResult result = format(source, toDialect(Dialect::English));
  REQUIRE(result.ok());
  // The comment's own line keeps the indentation its author gave it, so the three
  // statements are looked up one by one rather than as one text.
  REQUIRE(result.text.find("equal(X, % почему") != std::string::npos);
  REQUIRE(result.text.find('%') == result.text.find("% почему"));
  REQUIRE(result.text.find("странно(X):-greater(X).") != std::string::npos);
  REQUIRE(result.text.find("цепочка(X, Y):-equal(X = Y, Z).") != std::string::npos);
}

TEST_CASE("the two dialect directions are each other's way back") {
  // A conversion is also a layout (soft, the default), so the program comes back in
  // the standard shape — and not one word of it is lost.
  const std::string source =
      ":- ИМЕНА(0).\n"
      "вывод :- ВЫВОД(1), ВЫВОДПС(2).\n"
      "проверка(X) :- БОЛЬШЕ(X, 1), НЕ(РАВНО(X, #2 + 0#)).\n";
  const FormatResult english = format(source, toDialect(Dialect::English));
  REQUIRE(english.ok());
  const FormatResult back = format(english.text, toDialect(Dialect::Russian));
  REQUIRE(back.ok());
  REQUIRE(back.text ==
          ":- ИМЕНА(0).\n"
          "вывод:-ВЫВОД(1), ВЫВОДПС(2).\n"
          "проверка(X):-БОЛЬШЕ(X, 1), НЕ(РАВНО(X, #2 + 0#)).\n");
}

TEST_CASE("a dialect conversion leaves the marker line and a fragment alone") {
  // The marker is this dialect's own word, and `variables(0)` would not be read as
  // one, so the first line is copied as it is written.  A fragment is not
  // converted at all: its names would be renamed without the numbering a
  // conversion of the whole program needs.
  FormatOptions options = toDialect(Dialect::English);
  options.variables = VariableMode::Old;
  const FormatResult marked = format(":- ИМЕНА(1).\nцель(а).\n", options);
  REQUIRE(marked.ok());
  REQUIRE(marked.text == ":- ИМЕНА(1).\nцель(а).\n");

  FormatOptions fragment = toDialect(Dialect::English);
  fragment.selection_only = true;
  const FormatResult kept = format("ВЫВОД(1), ВЫВОД", fragment);
  REQUIRE(kept.ok());
  REQUIRE(kept.text == "ВЫВОД(1), ВЫВОД");
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

TEST_CASE("a dialect conversion composes with the layout and the names") {
  // One request asks for all three: the words, the variables and the shape.  The
  // order is fixed — dialect first, then the names, then the layout — so the
  // answer is a program that can be read and run straight away.
  FormatOptions options;
  options.mode = FormatMode::Hard;
  options.dialect_out = Dialect::English;
  options.names_out = VariableMode::Iso;
  options.variables = VariableMode::Old;
  const std::string source =
      ":- ИМЕНА(1).\n"
      "пример(Х) :- ВЫВОД(Х), БОЛЬШЕ(Х, 1).\n";
  const FormatResult result = format(source, options);
  REQUIRE(result.ok());
  // `Х` is one variable with no shared base, so its ISO spelling is `Х` itself:
  // the regex of the naming conversion has nothing to number here.
  REQUIRE(result.text ==
          ":- ИМЕНА(0).\n"
          "пример(Х):-\n"
          "\twrite(Х),\n"
          "\tХ > 1.\n");
}
