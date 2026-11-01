#include <catch2/catch_test_macros.hpp>

#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "test_helpers.hpp"

using prologd::test::runProgram;
using prologd::test::runProgramWithIncludes;

namespace {

std::string readExample(const std::string& relative) {
  const std::string path = std::string(PROLOGD_TEST_DATA_DIR) + "/" + relative;
  std::ifstream stream(path, std::ios::binary);
  REQUIRE(stream.good());
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return buffer.str();
}

/// Like `readExample`, but a missing file is an empty string instead of a
/// failure: a lesson needs an input file only when it reads input.
std::string readOptional(const std::string& relative) {
  std::ifstream stream(std::string(PROLOGD_TEST_DATA_DIR) + "/" + relative, std::ios::binary);
  if (!stream.good()) {
    return {};
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return buffer.str();
}

/// What a lesson promises the reader: every `%!` line, in file order, with the
/// marker removed.  `%! Х=12` promises the line `Х=12`, a ground answer is
/// written `%! ДА`, and a bare `%!` promises an empty line.  Ordinary `%`
/// comments stay prose.
std::string expectedOutput(const std::string& source) {
  std::istringstream input(source);
  std::string line;
  std::string result;
  while (std::getline(input, line)) {
    const std::size_t first = line.find_first_not_of(" \t");
    if (first == std::string::npos || line.compare(first, 2, "%!") != 0) {
      continue;
    }
    std::size_t text = first + 2;
    if (text < line.size() && line[text] == ' ') {
      ++text;
    }
    result += line.substr(text);
    result += '\n';
  }
  return result;
}

/// Lessons whose printed output is compared with the `%!` lines they carry.  A
/// lesson joins this list when it is rewritten for the course — see
/// `ai/task_35_lessons_rework.md` — and from that moment it cannot drift: as soon
/// as the interpreter prints something else, this check fails.  A lesson that
/// reads input carries the answers next to it as `<name>.input.txt`.
const std::vector<std::string>& checkedLessons() {
  static const std::vector<std::string> names = {
      "lesson_01.pld",
      "lesson_02.pld",
      "lesson_03.pld",
      "lesson_04.pld",
      "lesson_05.pld",
      "lesson_06.pld",
      "lesson_07.pld",
      "lesson_08.pld",
      "lesson_09.pld",
      "lesson_10.pld",
      "lesson_11.pld",
      "lesson_12.pld",
      "appendix_debug.pld",
  };
  return names;
}

/// Examples beside the lessons whose `%!` lines are checked the same way.  Each of
/// them shows one group of the built-ins the dialect added on top of the port or
/// carries the ISO spelling beside it (part 245): the arithmetic signs, the three
/// collectors, `ПЕРВОЕ` and `->`, the standard order, `ПОДСТРОКА`, `СОРТИРОВКА`,
/// `ПОЛНЫЙ` and `ДЛЯВСЕХ`.  Also here: the tour of the standard library, the two
/// problems whose output is the same on every machine, the study sorts that left
/// the library for `examples/problems/sorting.pld` (task_89) and the family tree.
/// `problems/hanoi.pld` draws and `problems/hanoi_play.pld` reads input, so those
/// two are only parsed (see the test below), and so is `problems/maze/maze.pld`
/// with its two modules: it draws a maze and walks a mouse along the found path.
const std::vector<std::string>& checkedExamples() {
  static const std::vector<std::string> names = {
      "arith.pld",
      "findall.pld",
      "if_then.pld",
      "order.pld",
      "sub_string.pld",
      "sort.pld",
      "ground.pld",
      "forall.pld",
      "stdlib.pld",
      "problems/sorting.pld",
      "problems/family.pld",
      "problems/factorial.pld",
      "problems/knapsack.pld",
  };
  return names;
}

/// Run one file and compare the whole output with the `%!` lines it carries.
void checkPromises(const std::string& relative, const std::string& input,
                   std::vector<std::filesystem::path> include_paths) {
  const std::string source = readExample(relative);
  INFO("file: " << relative);
  REQUIRE(source.find("%!") != std::string::npos);
  // Lesson files are stored with LF ends; a stray CR would end up in the expected
  // text and never match what the interpreter prints.
  REQUIRE(source.find('\r') == std::string::npos);
  const auto result = runProgramWithIncludes(source, input, std::move(include_paths));
  INFO("errors: " << result.error);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == expectedOutput(source));
}

/// Remove query/directive lines so the file can be loaded without running it.
std::string withoutQueries(const std::string& source) {
  std::istringstream input(source);
  std::string line;
  std::string result;
  while (std::getline(input, line)) {
    const std::size_t first = line.find_first_not_of(" \t");
    if (first != std::string::npos && (line[first] == '?' || line[first] == ':')) {
      continue;
    }
    result += line;
    result += '\n';
  }
  return result;
}

}  // namespace

TEST_CASE("ported example programs parse cleanly") {
  const std::vector<std::string> files = {
      "problems/factorial.pld", "problems/hanoi.pld", "problems/hanoi_play.pld",
      "problems/maze/maze.pld", "problems/maze/maze.graphics.pld",
      "problems/maze/maze.images.pld",
      "file_io.pld", "drawing.pld",
      "import/import.pld", "import/lib/library.pld", "import/lib/hello.pld",
  };
  for (const std::string& file : files) {
    const auto result = runProgram(withoutQueries(readExample(file)));
    INFO("file: " << file);
    INFO("errors: " << result.error);
    REQUIRE(result.loaded);
    REQUIRE(result.output.empty());
  }
}

TEST_CASE("every lesson prints exactly what its comments promise") {
  for (const std::string& name : checkedLessons()) {
    const std::string stem = name.substr(0, name.rfind('.'));
    // Lesson 11 imports `lesson_11_lib.pld`, which lies beside it, and lesson 12 the
    // colour names of the standard library, so the check searches the two places a
    // reader's own run reaches: the folder of the lesson, then `stdlib`.
    checkPromises("lessons/" + name, readOptional("lessons/" + stem + ".input.txt"),
                  {std::string(PROLOGD_TEST_DATA_DIR) + "/lessons",
                   std::string(PROLOGD_STDLIB_DIR)});
  }
}

TEST_CASE("the example programs print what their comments promise") {
  for (const std::string& name : checkedExamples()) {
    // `stdlib.pld` imports the standard library, so the check looks where
    // the CLI looks with `-I stdlib`; it is also the only example that reads —
    // the numbers come from `stdlib.input.txt` beside it.
    const std::string stem = name.substr(0, name.rfind('.'));
    checkPromises(name, readOptional(stem + ".input.txt"),
                  {std::string(PROLOGD_TEST_DATA_DIR), std::string(PROLOGD_STDLIB_DIR)});
  }
}

TEST_CASE("a dot ends a number only after a digit") {
  // task_52, as in ISO: `1.` is the integer 1 and the sentence terminator — a
  // statement may now *end* with a number (`?2 > 1.`) — so a real without a
  // fraction is written `1.0`, inside `#…#` too.
  const auto real = runProgram("?РАВНО(X, #1.0 + 2.0#).\n");
  REQUIRE(real.loaded);
  REQUIRE(real.output == "X=3.0\n");

  // The trailing-dot float of the original PrologD is gone: the dot ends the
  // number, and there is no closing bracket left for the `)` to match.
  const auto trailing = runProgram("?РАВНО(X, #1. + 2.#).\n");
  REQUIRE_FALSE(trailing.loaded);
}
