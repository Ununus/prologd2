#include <catch2/catch_test_macros.hpp>

#include <cstddef>
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

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
