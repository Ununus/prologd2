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
      "lessons/lesson_1.pld", "lessons/lesson_2.pld", "lessons/lesson_3.pld",
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

TEST_CASE("lesson 1 produces the documented output") {
  const auto result = runProgram(readExample("lessons/lesson_1.pld"));
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "X=sky\n"
          "X=sun\n"
          "X=star\n"
          "X=небо\n"
          "Y=Himmel\n"
          "A=star\n"
          "Б=Лена\n"
          "Б=Надя\n"
          "Д=Сергей\n"
          "Д=Николай\n"
          "И=Боря\n"
          "В_=65\n"
          "Х=7\n"
          "Х=5\n"
          "Ф=5040\n");
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
  const std::string program = withoutQueries(readExample("lessons/lesson_3.pld")) +
                              "?обращение(абвгдежз,С).\n"
                              "?замена(\"а\",\"ю\",абвабва,Т).\n";
  const auto result = runProgram(program);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "С=зжедгвба\nТ=юбвабва\n");
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
