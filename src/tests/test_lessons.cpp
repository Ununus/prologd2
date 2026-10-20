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

/// Examples beside the lessons whose `%!` lines are checked the same way.  They
/// are the showcase for the predicates the dialect added on top of the port
/// (`ПЕРВОЕ`, `СОРТИРОВКА`, `ПОЛНЫЙ`, `ДЛЯВСЕХ`), the two problems whose output
/// is the same on every machine, the tour of the standard library, the study
/// sorts that left the library for `examples/sorts.pld` (task_89) and the two
/// examples of the ISO additions (task_84, task_85) in `examples/prologu`;
/// `problems/monk.pld` draws and `problems/monkd.pld` reads input, so those two
/// are only parsed (see the test below).
const std::vector<std::string>& checkedExamples() {
  static const std::vector<std::string> names = {
      "first_demo.pld",
      "sort_demo.pld",
      "ground_demo.pld",
      "forall_demo.pld",
      "sorts.pld",
      "stdlib_demo.pld",
      "use_old_names.pld",
      "problems/factorial.pld",
      "problems/knapsack.pld",
      "prologu/sub_string_demo.pld",
      "prologu/if_then_demo.pld",
      "prologu/standard_order_demo.pld",
  };
  return names;
}

/// The old course's own lessons, kept beside the rewritten ones.  They are written
/// in the dialect the course was taught in, so every one of them starts with
/// `:- ИМЕНА(1).` (task_67) and carries the answers it promises as `%!` lines.
/// Uncommenting an old `?` question means recording its answers.  A question that
/// cannot be uncommented — it never finishes, or it prints hundreds of solutions —
/// stays a comment in the file with the reason written above it, and `_old/lesson_2`
/// and `_old/lesson_9` are not listed at all: the first no longer loads, and the
/// second answers only after a dialogue the check cannot have.
const std::vector<std::string>& checkedOldLessons() {
  static const std::vector<std::string> names = {
      "_old/lesson_1.pld",
      "_old/lesson_3.pld",
      "_old/lesson_4.pld",
      "_old/lesson_5.pld",
      "_old/lesson_6.pld",
      "_old/lesson_8.pld",
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
      "problems/factorial.pld", "problems/monk.pld",     "problems/monkd.pld",
      "file_io.pld",           "drawing.pld",           "findall_demo.pld",
      "import_demo.pld",       "lib/library.pld",
  };
  // `lib/old_lib*.pld` are not here: `withoutQueries` strips every `:` line, and
  // that takes the naming marker with it, so the file would be read in mode 0 and
  // its apostrophe names would not parse.  They are exercised through
  // `use_old_names.pld`, which imports and calls both of them.
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
    // Lesson 11 imports a library and lesson 12 the colour names, so the check
    // searches the same three places the CLI would reach with
    // `-I examples/lib -I stdlib`: next to the lesson, then the two libraries.
    checkPromises("lessons/" + name, readOptional("lessons/" + stem + ".input.txt"),
                  {std::string(PROLOGD_TEST_DATA_DIR) + "/lessons",
                   std::string(PROLOGD_TEST_DATA_DIR) + "/lib",
                   std::string(PROLOGD_STDLIB_DIR)});
  }
}

TEST_CASE("the example programs print what their comments promise") {
  for (const std::string& name : checkedExamples()) {
    // `stdlib_demo.pld` imports the standard library, so the check looks where
    // the CLI looks with `-I stdlib`; it is also the only example that reads —
    // the numbers come from `stdlib_demo.input.txt` beside it.  `use_old_names.pld`
    // imports the two old-format libraries by a path relative to the examples
    // folder, which is the data directory itself.
    const std::string stem = name.substr(0, name.rfind('.'));
    checkPromises(name, readOptional(stem + ".input.txt"),
                  {std::string(PROLOGD_TEST_DATA_DIR), std::string(PROLOGD_STDLIB_DIR)});
  }
}

TEST_CASE("the old course's lessons print what their comments promise") {
  for (const std::string& name : checkedOldLessons()) {
    const std::string stem = name.substr(0, name.rfind('.'));
    // The mode marker on the first line does the job `--vars 1` does for the CLI,
    // so the file is run exactly as a reader would run it.
    checkPromises("lessons/" + name, readOptional("lessons/" + stem + ".input.txt"),
                  {std::string(PROLOGD_TEST_DATA_DIR) + "/lessons",
                   std::string(PROLOGD_TEST_DATA_DIR) + "/lib",
                   std::string(PROLOGD_STDLIB_DIR)});
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
