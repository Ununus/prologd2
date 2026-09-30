#include <catch2/catch_test_macros.hpp>

#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "test_helpers.hpp"

using prologd::test::runProgram;

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
  };
  return names;
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
      "lessons/lesson_8.pld", "lessons/lesson_9.pld",
      "factorial.pld",        "file_io.pld",         "drawing.pld",
      "monk.pld",             "monkd.pld",           "findall_demo.pld",
      "import_demo.pld",      "lib/library.pld",
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
    const std::string source = readExample("lessons/" + name);
    INFO("lesson: " << name);
    REQUIRE(source.find("%!") != std::string::npos);
    // Lesson files are stored with LF ends; a stray CR would end up in the
    // expected text and never match what the interpreter prints.
    REQUIRE(source.find('\r') == std::string::npos);
    const std::string stem = name.substr(0, name.rfind('.'));
    const auto result = runProgram(source, readOptional("lessons/" + stem + ".input.txt"));
    INFO("errors: " << result.error);
    REQUIRE(result.loaded);
    REQUIRE_FALSE(result.runtimeError);
    REQUIRE(result.output == expectedOutput(source));
  }
}

TEST_CASE("trailing-dot floats parse as in the original") {
  const auto result = runProgram("?РАВНО(X, #1. + 2.#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3.0\n");
}
