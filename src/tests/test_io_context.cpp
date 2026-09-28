#include <catch2/catch_test_macros.hpp>

#include <cstddef>
#include <deque>
#include <filesystem>
#include <fstream>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "prlib/io.hpp"
#include "test_helpers.hpp"

using namespace prologd;
using prologd::test::runProgram;
namespace fs = std::filesystem;

namespace {

/// Stand-in for a front-end: records what the interpreter asks for and replays
/// scripted answers, exhausting them as end of input.
class ScriptedInput {
 public:
  void queue(std::string line) { answers_.push_back(std::move(line)); }

  std::optional<std::string> operator()(InputRequestKind kind) {
    kinds_.push_back(kind);
    if (answers_.empty()) {
      return std::nullopt;
    }
    std::string line = answers_.front();
    answers_.pop_front();
    return line;
  }

  [[nodiscard]] std::size_t calls() const noexcept { return kinds_.size(); }

  [[nodiscard]] std::string kindNames() const {
    std::string text;
    for (const InputRequestKind kind : kinds_) {
      switch (kind) {
        case InputRequestKind::Token:
          text += "token,";
          break;
        case InputRequestKind::Line:
          text += "line,";
          break;
        case InputRequestKind::CodePoint:
          text += "codepoint,";
          break;
      }
    }
    return text;
  }

 private:
  std::deque<std::string> answers_;
  std::vector<InputRequestKind> kinds_;
};

/// A short-lived file used by the redirection test.
class TempFile {
 public:
  explicit TempFile(const std::string& contents) {
    path_ = fs::temp_directory_path() / "prologd_io_context_test.txt";
    std::ofstream stream(path_, std::ios::binary | std::ios::trunc);
    stream << contents;
  }
  ~TempFile() {
    std::error_code code;
    fs::remove(path_, code);
  }
  [[nodiscard]] std::string path() const { return path_.string(); }

 private:
  fs::path path_;
};

}  // namespace

TEST_CASE("interactive reads go through the input request handler") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("альфа бета");
  script.queue("строка целиком");
  script.queue("ж");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });
  REQUIRE(io.hasInputRequestHandler());

  const auto first = io.readToken();
  REQUIRE(first.has_value());
  REQUIRE(*first == "альфа");
  const auto second = io.readToken();
  REQUIRE(second.has_value());
  REQUIRE(*second == "бета");
  REQUIRE(script.calls() == 1);  // both tokens come from the same line

  const auto line = io.readWholeLine();
  REQUIRE(line.has_value());
  REQUIRE(*line == "строка целиком");

  const auto code_point = io.readCodePoint();
  REQUIRE(code_point.has_value());
  REQUIRE(*code_point == U'ж');

  const auto exhausted = io.readCodePoint();
  REQUIRE_FALSE(exhausted.has_value());

  REQUIRE(script.kindNames() == "token,line,codepoint,codepoint,");
}

TEST_CASE("preloaded lines are served before the input request handler") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("динамически");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });
  io.pushPreloadedLine("заранее");

  const auto preloaded = io.readToken();
  REQUIRE(preloaded.has_value());
  REQUIRE(*preloaded == "заранее");
  REQUIRE(script.calls() == 0);

  const auto dynamic = io.readToken();
  REQUIRE(dynamic.has_value());
  REQUIRE(*dynamic == "динамически");
  REQUIRE(script.calls() == 1);
}

TEST_CASE("input redirection wins over the input request handler") {
  const TempFile file("из файла\n");
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });
  REQUIRE(io.openInput(file.path()));

  const auto line = io.readWholeLine();
  REQUIRE(line.has_value());
  REQUIRE(*line == "из файла");
  REQUIRE(script.calls() == 0);

  REQUIRE(io.openInput(""));  // back to the interactive source
  script.queue("из обработчика");
  const auto restored = io.readWholeLine();
  REQUIRE(restored.has_value());
  REQUIRE(*restored == "из обработчика");
  REQUIRE(script.calls() == 1);
}

TEST_CASE("without a handler the base stream is read") {
  std::istringstream input("из потока\n");
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  REQUIRE_FALSE(io.hasInputRequestHandler());
  const auto line = io.readWholeLine();
  REQUIRE(line.has_value());
  REQUIRE(*line == "из потока");
}

TEST_CASE("the external stop hook interrupts a running query") {
  const auto result = runProgram(
      "цикл :- цикл.\n"
      "?цикл.\n",
      {}, nullptr,
      [](Engine& engine) { engine.options().externalStop = [] { return true; }; });

  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("прервано") != std::string::npos);
}

TEST_CASE("a query without the external stop hook still succeeds") {
  const auto result = runProgram("факт(1).\n?факт(X).\n", {}, nullptr,
                                 [](Engine& engine) {
                                   engine.options().externalStop = [] { return false; };
                                 });
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "X=1\n");
}
