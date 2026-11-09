#include <catch2/catch_test_macros.hpp>

#include <cstddef>
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "test_helpers.hpp"

namespace {

namespace fs = std::filesystem;

std::string readFile(const fs::path& path) {
  std::ifstream stream(path, std::ios::binary);
  REQUIRE(stream.good());
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  return buffer.str();
}

/// `name/arity` of every clause head in one library file.
///
/// A head is what stands before `:-` or before the closing `.`, on a line that
/// starts in the first column — the formatter indents the continuations of a body
/// with a tab, so `\tmin_list(...)` is never a head.  The arity is the number of
/// commas between the outermost brackets plus one, counted at bracket depth one:
/// `nth(Список, Номер, Элемент)` is `nth/3`, and the commas inside `[Первый, Второй]`
/// do not count.
std::set<std::string> clauseHeads(const std::string& source) {
  std::set<std::string> result;
  std::istringstream input(source);
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == ' ' || line[0] == '\t') {
      continue;  // blank, or the continuation of a body
    }
    if (line[0] == '%' || line[0] == ':' || line[0] == '?') {
      continue;  // a comment, a directive or a query
    }
    const std::size_t open = line.find('(');
    if (open == std::string::npos) {
      continue;
    }
    std::size_t stop = line.find(":-");
    const std::size_t dot = line.find('.');
    if (stop == std::string::npos || (dot != std::string::npos && dot < stop)) {
      stop = dot;
    }
    if (stop == std::string::npos || stop < open) {
      continue;
    }
    const std::string name = line.substr(0, open);
    if (name.empty() || name.find(' ') != std::string::npos) {
      continue;
    }
    int depth = 0;
    std::size_t commas = 0;
    for (std::size_t index = open; index < stop; ++index) {
      const char symbol = line[index];
      if (symbol == '(' || symbol == '[' || symbol == '{') {
        ++depth;
      } else if (symbol == ')' || symbol == ']' || symbol == '}') {
        --depth;
      } else if (symbol == ',' && depth == 1) {
        ++commas;
      }
    }
    result.insert(name + "/" + std::to_string(commas + 1));
  }
  return result;
}

}  // namespace

TEST_CASE("the library document names every predicate the library defines") {
  // A reference that has fallen behind is worse than no reference: the reader
  // trusts it.  `stdlib/*.pld` is the truth and `doc/library.typ` the summary, so
  // the two are compared here — a predicate added to the library without a line in
  // the document fails this check, and so does a renamed one (part 85).
  const fs::path library(PROLOGD_STDLIB_DIR);
  const std::string document = readFile(fs::path(PROLOGD_DOC_DIR) / "library.typ");
  std::size_t checked = 0;
  std::size_t files = 0;
  for (const auto& entry : fs::directory_iterator(library)) {
    if (!entry.is_regular_file() || entry.path().extension() != ".pld") {
      continue;
    }
    ++files;
    const std::set<std::string> heads = clauseHeads(readFile(entry.path()));
    REQUIRE_FALSE(heads.empty());
    for (const std::string& head : heads) {
      INFO("file: " << entry.path().filename().string() << ", predicate: " << head);
      REQUIRE(document.find(head) != std::string::npos);
      ++checked;
    }
  }
  REQUIRE(files >= 5);
  REQUIRE(checked >= 80);
}

TEST_CASE("the knowledge base library replaces in place and copies a predicate") {
  // Part 271: the library had no way to *change* the base — only the engine's
  // primitives, each acting on one clause.  `replace_clause` keeps the position
  // (the order of clauses is the order of answers, which a graph search depends
  // on) and `copy_predicate` is what a snapshot of a graph is.
  using prologd::test::runProgramWithIncludes;
  const std::vector<std::filesystem::path> library{PROLOGD_STDLIB_DIR};
  const auto result = runProgramWithIncludes(
      ":- ИМПОРТ('database.pld').\n"
      "ребро(а, б). ребро(б, в). ребро(в, г).\n"
      "?replace_clause(ребро(б, в), ребро(б, д)), ребро(X, Y).\n",
      "", library);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // The replacement stands where the old clause stood: б-д between а-б and в-г.
  REQUIRE(result.output == "X=а\nY=б\nX=б\nY=д\nX=в\nY=г\n");
}

TEST_CASE("a replacement of what is not there changes nothing") {
  using prologd::test::runProgramWithIncludes;
  const std::vector<std::filesystem::path> library{PROLOGD_STDLIB_DIR};
  const auto result = runProgramWithIncludes(
      ":- ИМПОРТ('database.pld').\n"
      "ребро(а, б).\n"
      "?replace_clause(ребро(а, з), ребро(а, д)).\n"
      "?replace_clause(ребро(чужой, б), ребро(а, д)).\n"
      "?ПРЕДЛ(ребро, Н, Г, Ц).\n",
      "", library);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // The head does not answer to the first pattern, so both replacements fail and
  // the single fact is untouched: no clause was added where none was removed.
  REQUIRE(result.output == "НЕТ\nНЕТ\nН=1\nГ=ребро(а,б)\nЦ=[]\n");
}

TEST_CASE("a copy takes arms as they are and leaves the original alone") {
  using prologd::test::runProgramWithIncludes;
  const std::vector<std::filesystem::path> library{PROLOGD_STDLIB_DIR};
  const auto result = runProgramWithIncludes(
      ":- ИМПОРТ('database.pld').\n"
      "длинная(а). длинная(б).\n"
      "путь(X):-длинная(X).\n"
      "?copy_predicate(путь, дорога), дорога(X).\n"
      "?replace_clause(дорога(а), дорога(я)), путь(X).\n"
      "?copy_predicate(нетТакого, ничто).\n",
      "", library);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // The copy carries the body it had, the original still answers «а», and there is
  // nothing to copy from an unknown name.
  REQUIRE(result.output == "X=а\nX=б\nX=а\nX=б\nНЕТ\n");
}

TEST_CASE("the knowledge base library reads a predicate and gives its number") {
  // Part 273: `clause_number` is the question a reader actually asks («под каким
  // номером лежит это предложение») without the `ТЕРМ(Чё, Части), Части = [Имя | _]`
  // dance, and `clauses` is the read half of `copy_predicate`.
  using prologd::test::runProgramWithIncludes;
  const std::vector<std::filesystem::path> library{PROLOGD_STDLIB_DIR};
  const auto result = runProgramWithIncludes(
      ":- ИМПОРТ('database.pld').\n"
      "ребро(а, б). ребро(б, в). ребро(в, г).\n"
      "путь(X, Y):-ребро(X, Y).\n"
      "?clause_number(ребро(б, в), Н).\n"
      "?clauses(путь, Все).\n"
      "?clauses(нетакого, Пусто).\n",
      "", library);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "Н=2\n"
                            "Все=[предложение(путь(_1,_2),[ребро(_1,_2)])]\n"
                            "Пусто=[]\n");
}

TEST_CASE("the knowledge base library renames and deletes a predicate") {
  using prologd::test::runProgramWithIncludes;
  const std::vector<std::filesystem::path> library{PROLOGD_STDLIB_DIR};
  const auto result = runProgramWithIncludes(
      ":- ИМПОРТ('database.pld').\n"
      "ребро(а, б). ребро(б, в).\n"
      "?rename_predicate(ребро, дубль), СКОЛЬКО(ребро, Стало), СКОЛЬКО(дубль, Цел).\n"
      "?delete_predicate(дубль), СКОЛЬКО(дубль, Пусто).\n"
      "?delete_predicate(нетакого).\n"
      "?copy_predicate(нетакого, Копия).\n",
      "", library);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // The copy is made before the old name goes, so both counters are read at once;
  // deleting an unknown name is true, copying one is false.
  REQUIRE(result.output == "Стало=0\nЦел=2\nПусто=0\nДА\nНЕТ\n");
}
