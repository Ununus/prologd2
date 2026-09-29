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
      "lessons/lesson_2.pld", "lessons/lesson_3.pld",
      "lessons/lesson_4.pld", "lessons/lesson_5.pld", "lessons/lesson_6.pld",
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

TEST_CASE("lesson 2 primitives, digits and reversal") {
  const std::string program = withoutQueries(readExample("lessons/lesson_2.pld")) +
                              "?простое(7).\n"
                              "?простое(8).\n"
                              "?минциф(1785,Ц).\n"
                              "?наоборот(1785,Ф).\n";
  const auto result = runProgram(program);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nЦ=1\nФ=5871\n");
}

TEST_CASE("lesson 3 string predicates") {
  // The lesson is written for the `КОПИЯ` that searches from the beginning of
  // the string: the count walks the rest *after* the first occurrence, and
  // `замена`/`удаление` cut the first one out and recurse.  The original lesson
  // counted from the last one, which only worked while that search went from the
  // end (see ai/porting_notes.md).
  const std::string program = withoutQueries(readExample("lessons/lesson_3.pld")) +
                              "?обращение(абвгдежз,С).\n"
                              "?сколько(идиотизм,\"и\",Н).\n"
                              "?сколько(\"абаб\",\"аб\",Н2).\n"
                              "?сколько(\"абв\",\"абв\",Н3).\n"
                              "?сколько(\"абв\",\"з\",Н4).\n"
                              "?замена(\"а\",\"ю\",абвабва,Т).\n"
                              "?замена(\"а\",\"ю\",бвг,Т2).\n"
                              "?удаление(\"а\",абракадабра,Ю).\n"
                              "?скобки(\"()(()()()))(\").\n";
  const auto result = runProgram(program);
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "С=зжедгвба\n"
          "Н=3\n"
          "Н2=2\n"
          "Н3=1\n"
          "Н4=0\n"
          "Т=юбвюбвю\n"
          "Т2=бвг\n"
          "Ю=бркдбр\n"
          "Неверный порядок скобок в строке: первая скобка - правая ()(()()()))(\n"
          "ДА\n");
}

TEST_CASE("lesson 4 sorting") {
  const std::string program = withoutQueries(readExample("lessons/lesson_4.pld")) +
                              "?сортировка([5,4,3,2,1],A).\n"
                              "?вставсорт([10,9,8,7,6,5,4,3,2,1],B).\n";
  const auto result = runProgram(program);
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "A=[1,2,3,4,5]\n"
          "B=[1,2,3,4,5,6,7,8,9,10]\n");
}

TEST_CASE("lesson 5 monkey and bananas") {
  const auto result = runProgram(readExample("lessons/lesson_5.pld"));
  REQUIRE(result.loaded);
  REQUIRE(result.output.find("Слева [волк,коза,капуста]") != std::string::npos);
  REQUIRE(result.output.find("Справа [коза,капуста,волк]") != std::string::npos);
  REQUIRE(result.output.find("ДА") != std::string::npos);
}

TEST_CASE("lesson 6 logic puzzles") {
  const auto result = runProgram(readExample("lessons/lesson_6.pld"));
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "А=блондин\n"
          "Б=с усами\n"
          "В_=с портфелем\n"
          "А=Денис\n"
          "И=Максим\n"
          "О=Кирилл\n");
}

TEST_CASE("trailing-dot floats parse as in the original") {
  const auto result = runProgram("?РАВНО(X, #1. + 2.#).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=3.0\n");
}
