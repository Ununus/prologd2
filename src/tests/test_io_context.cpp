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

TEST_CASE("an answer is a piece of the input stream, not a line") {
  // The whole point of task_54: an answer with a separator in it is several
  // lines, and both of them come out of one ask.
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("первая\nвторая");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  const auto first = io.readWholeLine();
  REQUIRE(first == std::optional<std::string>("первая"));
  const auto second = io.readWholeLine();
  REQUIRE(second == std::optional<std::string>("вторая"));
  REQUIRE(script.calls() == 1);

  // The piece is used up now, so the third read asks the front-end again.
  script.queue("третья");
  const auto third = io.readWholeLine();
  REQUIRE(third == std::optional<std::string>("третья"));
  REQUIRE(script.calls() == 2);
}

TEST_CASE("the end of a piece ends its last line, it does not open an empty one") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("а\n");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  const auto line = io.readWholeLine();
  REQUIRE(line == std::optional<std::string>("а"));
  REQUIRE(script.calls() == 1);

  // Not an empty line: the next read waits for the user, as it does at the end
  // of a file whose last line had a terminator.
  script.queue("б");
  const auto next = io.readWholeLine();
  REQUIRE(next == std::optional<std::string>("б"));
  REQUIRE(script.calls() == 2);

  REQUIRE_FALSE(io.readWholeLine().has_value());  // the script is exhausted
}

TEST_CASE("an empty answer is one empty line, and only one") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  const auto empty = io.readWholeLine();
  REQUIRE(empty.has_value());
  REQUIRE(empty->empty());
  REQUIRE(script.calls() == 1);

  script.queue("после пустой");
  const auto next = io.readWholeLine();
  REQUIRE(next == std::optional<std::string>("после пустой"));
  REQUIRE(script.calls() == 2);
}

TEST_CASE("an empty line in the middle of a piece is a line of its own") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("а\n\nб");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  REQUIRE(io.readWholeLine() == std::optional<std::string>("а"));
  const auto middle = io.readWholeLine();
  REQUIRE(middle.has_value());
  REQUIRE(middle->empty());
  REQUIRE(io.readWholeLine() == std::optional<std::string>("б"));
  REQUIRE(script.calls() == 1);

  // A file holding the same bytes agrees: `а`, an empty line, `б`, and then the
  // end of the stream rather than a fourth line.
  const TempFile file("а\n\nб\n");
  REQUIRE(io.openInput(file.path()));
  REQUIRE(io.readWholeLine() == std::optional<std::string>("а"));
  const auto file_middle = io.readWholeLine();
  REQUIRE(file_middle.has_value());
  REQUIRE(file_middle->empty());
  REQUIRE(io.readWholeLine() == std::optional<std::string>("б"));
  REQUIRE_FALSE(io.readWholeLine().has_value());
}

TEST_CASE("a token and the rest of its line come out of one piece") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("имя остаток строки\nследующая");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  REQUIRE(io.readToken() == std::optional<std::string>("имя"));
  // «Остаток строки» is a line's tail, not the piece's: the separator is still
  // a separator, so the space is kept but the `\n` is not part of the text.
  REQUIRE(io.readWholeLine() == std::optional<std::string>(" остаток строки"));
  REQUIRE(io.readWholeLine() == std::optional<std::string>("следующая"));
  REQUIRE(script.calls() == 1);
}

TEST_CASE("the separator of a piece is never handed out as a code point") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("ab\ncd");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  std::string read;
  for (int index = 0; index < 4; ++index) {
    const auto code_point = io.readCodePoint();
    REQUIRE(code_point.has_value());
    REQUIRE(*code_point != U'\n');
    read.push_back(static_cast<char>(*code_point));
  }
  REQUIRE(read == "abcd");
  REQUIRE(script.calls() == 1);  // code 10 would have been a fifth call
}

TEST_CASE("a carriage return before a separator is not part of the line") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  script.queue("а\r\nб\r\n");
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  REQUIRE(io.readWholeLine() == std::optional<std::string>("а"));
  REQUIRE(io.readWholeLine() == std::optional<std::string>("б"));
  REQUIRE(script.calls() == 1);
}

TEST_CASE("a byte order mark is a marker at the start of a stream only") {
  const std::string mark = "\xEF\xBB\xBF";  // U+FEFF in UTF-8
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  ScriptedInput script;
  io.setInputRequestHandler([&script](InputRequestKind kind) { return script(kind); });

  // The start of a piece: the mark goes, the text stays.
  script.queue(mark + "первая\n" + mark + "вторая");
  REQUIRE(io.readWholeLine() == std::optional<std::string>("первая"));
  // The second line is not the start of the piece, so its mark is data.
  REQUIRE(io.readWholeLine() == std::optional<std::string>(mark + "вторая"));

  // The start of a file, and of the base stream, are the same kind of start.
  const TempFile file(mark + "из файла\n");
  REQUIRE(io.openInput(file.path()));
  REQUIRE(io.readWholeLine() == std::optional<std::string>("из файла"));

  std::istringstream marked(mark + "из потока\n");
  std::ostringstream sink;
  std::ostringstream errors;
  IoContext stream(marked, sink, errors);
  REQUIRE(stream.readWholeLine() == std::optional<std::string>("из потока"));
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

TEST_CASE("a written line tells its owner that it ended") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  IoContext io(input, output, error);

  int lines = 0;
  io.setOutputLineSink([&lines] { ++lines; });
  REQUIRE(io.hasOutputLineSink());

  io.write("первая");  // the line is not over yet: nothing to hand on
  REQUIRE(lines == 0);
  io.newline();
  REQUIRE(lines == 1);

  io.write("вторая\nтретья");  // the newline inside the text ends a line
  REQUIRE(lines == 2);
  io.write(" и хвост");  // and the open line stays open
  REQUIRE(lines == 2);
  io.newline();
  REQUIRE(lines == 3);
  REQUIRE(output.str() == "первая\nвторая\nтретья и хвост\n");

  // Without a sink the text is the same and nobody is told: that is the console,
  // which reads the stream itself.
  std::ostringstream quiet_output;
  IoContext quiet(input, quiet_output, error);
  REQUIRE_FALSE(quiet.hasOutputLineSink());
  quiet.write("молча\n");
  REQUIRE(quiet_output.str() == "молча\n");
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
