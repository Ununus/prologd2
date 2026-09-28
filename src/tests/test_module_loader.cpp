#include <catch2/catch_test_macros.hpp>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"
#include "prlib/utf8_path.hpp"

using namespace prologd;
namespace fs = std::filesystem;

namespace {

class TempDir {
 public:
  TempDir() {
    static int counter = 0;
    path_ = fs::temp_directory_path() /
            ("prologd_import_test_" + std::to_string(++counter));
    fs::create_directories(path_);
  }
  ~TempDir() {
    std::error_code code;
    fs::remove_all(path_, code);
  }
  [[nodiscard]] const fs::path& path() const { return path_; }

  fs::path write(const std::string& name, const std::string& contents) const {
    const fs::path file = path_ / fromUtf8Path(name);
    std::ofstream stream(file, std::ios::binary);
    stream << contents;
    return file;
  }

 private:
  fs::path path_;
};

struct LoadOutcome {
  std::string output;
  std::string error;
  bool ok = false;
};

LoadOutcome load(const fs::path& entry, std::vector<fs::path> includes = {},
                 std::optional<fs::path> root = std::nullopt) {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  Engine engine;
  engine.setStreams(input, output, error);
  engine.initialize();
  ModuleLoader loader(engine, std::move(includes), std::move(root));
  loader.setQueryRunner([&](const Query& query) { engine.runQuery(query); });
  std::string message;
  LoadOutcome outcome;
  outcome.ok = loader.loadFile(entry, &message);
  outcome.output = output.str();
  outcome.error = error.str() + message;
  return outcome;
}

}  // namespace

TEST_CASE("import loads a module once") {
  TempDir dir;
  dir.write("base.pld", "факт(1).\nфакт(2).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"base.pld\").\n"
            ":- ИМПОРТ(\"base.pld\").\n"
            "?СКОЛЬКО(факт, N).\n"
            "?факт(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "N=2\nX=1\nX=2\n");
}

TEST_CASE("import resolves relative to the importing file") {
  TempDir dir;
  fs::create_directories(dir.path() / "sub");
  dir.write("sub/helper.pld", "помощь(да).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"sub/helper.pld\").\n"
            "?помощь(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=да\n");
}

TEST_CASE("import finds modules on the include path") {
  TempDir dir;
  dir.write("lib.pld", "библиотека(ок).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"lib.pld\").\n"
            "?библиотека(X).\n");
  const LoadOutcome outcome =
      load(dir.path() / "main.pld", {dir.path()}, dir.path());
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=ок\n");
}

TEST_CASE("import detects cycles") {
  TempDir dir;
  dir.write("a.pld", ":- ИМПОРТ(\"b.pld\").\nа(1).\n");
  dir.write("b.pld", ":- ИМПОРТ(\"a.pld\").\nб(2).\n");
  const LoadOutcome outcome = load(dir.path() / "a.pld");
  REQUIRE_FALSE(outcome.ok);
  REQUIRE(outcome.error.find("Циклический импорт") != std::string::npos);
}

TEST_CASE("import rejects paths outside the root") {
  TempDir dir;
  TempDir outside;
  outside.write("secret.pld", "секрет(1).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"../" + outside.path().filename().string() + "/secret.pld\").\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld", {}, dir.path());
  REQUIRE_FALSE(outcome.ok);
}

TEST_CASE("import reports a missing file") {
  TempDir dir;
  dir.write("main.pld", ":- ИМПОРТ(\"nope.pld\").\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE_FALSE(outcome.ok);
  REQUIRE(outcome.error.find("nope.pld") != std::string::npos);
}

TEST_CASE("import works with UTF-8 file names") {
  TempDir dir;
  dir.write("модуль.pld", "привет(мир).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"модуль.pld\").\n"
            "?привет(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=мир\n");
}
