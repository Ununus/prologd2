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

TEST_CASE("the standard library is the stdlib folder beside the interpreter") {
  // Part 84: the rule the CLI uses to find the library it ships — pure, so the test
  // does not have to copy an interpreter beside a library.
  TempDir empty;
  REQUIRE(standardLibraryDirectory(empty.path()).empty());
  REQUIRE(standardLibraryDirectory({}).empty());

  TempDir dir;
  fs::create_directories(dir.path() / "stdlib");
  REQUIRE(standardLibraryDirectory(dir.path()) == dir.path() / "stdlib");

  // A *file* called `stdlib` is not a library.
  TempDir file;
  file.write("stdlib", "не папка\n");
  REQUIRE(standardLibraryDirectory(file.path()).empty());
}

TEST_CASE("the executable directory is the folder holding this test") {
  // The engine finds `stdlib` beside its own executable.  This helper is what
  // makes that work on Windows (`GetModuleFileNameW`), Linux (`/proc/self/exe`)
  // and macOS (`_NSGetExecutablePath`); a missing branch answers with an empty
  // path, which the first check catches on every platform.
  const fs::path directory = executableDirectory();
  REQUIRE_FALSE(directory.empty());
  REQUIRE(fs::is_directory(directory));
#if defined(_WIN32)
  REQUIRE(fs::is_regular_file(directory / "prlib_tests.exe"));
#else
  REQUIRE(fs::is_regular_file(directory / "prlib_tests"));
#endif
}

TEST_CASE("an import reaches the standard library beside the program") {
  TempDir dir;
  fs::create_directories(dir.path() / "stdlib");
  dir.write("stdlib/lists.pld", "длина_списка([], 0).\n");
  dir.write("программа.pld",
            ":- ИМПОРТ(\"lists.pld\").\n"
            "?длина_списка([], N).\n");
  // What the CLI hands the loader: the interpreter's own `stdlib`, last.
  const LoadOutcome outcome =
      load(dir.path() / "программа.pld", {standardLibraryDirectory(dir.path())});
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "N=0\n");
}

TEST_CASE("import loads a module once") {  TempDir dir;
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

TEST_CASE("a directive import brings the definitions and leaves the questions alone") {
  // `:- ИМПОРТ(...)` names a library: the file's `?`-lines stay unrun, so a module
  // cannot print, read the input or abort the load it is part of (ADR-034).
  TempDir dir;
  dir.write("lib.pld",
            "пометка(да).\n"
            "?ВЫВОДПС(\"из библиотеки\").\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"lib.pld\").\n"
            "?пометка(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=да\n");
}

TEST_CASE("the question form of the import keeps the splice of PrologD 2.x") {
  // `?ИМПОРТ("lib.pld").` is how the previous version wrote an import: the file
  // was spliced in where the line stood, questions and all.  Old programs keep
  // that behaviour, and a program that wants a quiet library writes `:-` instead.
  TempDir dir;
  dir.write("lib.pld",
            "пометка(да).\n"
            "?ВЫВОДПС(\"из библиотеки\").\n");
  dir.write("main.pld",
            "?ИМПОРТ(\"lib.pld\").\n"
            "?пометка(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  // The spliced question prints its answer too, as a question of the main file does.
  REQUIRE(outcome.output == "из библиотеки\nДА\nX=да\n");
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
  // A candidate that exists but is rejected must say why, not just disappear.
  REQUIRE(outcome.error.find("вне корневого каталога") != std::string::npos);
}

TEST_CASE("import reports a missing file") {
  TempDir dir;
  dir.write("main.pld", ":- ИМПОРТ(\"nope.pld\").\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE_FALSE(outcome.ok);
  REQUIRE(outcome.error.find("nope.pld") != std::string::npos);
}

TEST_CASE("a missing import names the directories that were tried") {
  TempDir dir;
  TempDir shared;
  dir.write("main.pld", ":- ИМПОРТ(\"нет.pld\").\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld", {shared.path()});
  REQUIRE_FALSE(outcome.ok);
  REQUIRE(outcome.error.find("Искался в:") != std::string::npos);

  // Absolute paths, in the order they were tried: next to the importing file
  // first, then the include directory, so a user sees which one to fix.
  const std::size_t importer_first = outcome.error.find(toUtf8Path(dir.path()));
  const std::size_t include_second = outcome.error.find(toUtf8Path(shared.path()));
  REQUIRE(importer_first != std::string::npos);
  REQUIRE(include_second != std::string::npos);
  REQUIRE(importer_first < include_second);
}

TEST_CASE("a directory named like the import is reported as a directory") {
  TempDir dir;
  fs::create_directories(dir.path() / fromUtf8Path("модуль.pld"));
  dir.write("main.pld", ":- ИМПОРТ(\"модуль.pld\").\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE_FALSE(outcome.ok);
  REQUIRE(outcome.error.find("(это каталог)") != std::string::npos);
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

TEST_CASE("a Cyrillic path names the program and the directory its imports come from") {
  // The program's own name is UTF-8, so the directory it lives in is found through
  // the same conversion as everything else — and an import beside it is read from
  // there, not from the working directory (part 133, the rule the original engine
  // gained with `path_utf8`).
  TempDir dir;
  const fs::path program_dir = dir.path() / fromUtf8Path("примеры");
  fs::create_directories(program_dir);
  {
    std::ofstream library(program_dir / fromUtf8Path("книги.pld"), std::ios::binary);
    library << "удвоить(Ч, Д):-УМНОЖЕНИЕ(Ч, 2, Д).\n";
  }
  {
    std::ofstream program(program_dir / fromUtf8Path("программа.pld"), std::ios::binary);
    program << "?ИМПОРТ(\"книги.pld\").\n?удвоить(21, Д).\n";
  }
  const LoadOutcome outcome = load(program_dir / fromUtf8Path("программа.pld"));
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "Д=42\n");
}

TEST_CASE("an include directory with a Cyrillic name is searched") {
  TempDir dir;
  TempDir shared;
  const fs::path include_dir = shared.path() / fromUtf8Path("библиотека");
  fs::create_directories(include_dir);
  {
    std::ofstream library(include_dir / fromUtf8Path("книги.pld"), std::ios::binary);
    library << "привет(мир).\n";
  }
  dir.write("main.pld",
            "?ИМПОРТ(\"книги.pld\").\n"
            "?привет(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld", {include_dir});
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=мир\n");
}

TEST_CASE("the diamond example loads its shared module once") {
  // `examples/diamond`: the top file imports two branches, each branch imports
  // `base.pld`, and the top file imports it directly as well - three paths to a
  // single file, which must still be loaded exactly once, so the shared
  // predicate keeps its two clauses instead of gaining more.
  const fs::path entry =
      fromUtf8Path(std::string(PROLOGD_TEST_DATA_DIR) + "/diamond/main.pld");
  const LoadOutcome outcome = load(entry, {entry.parent_path()});
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output ==
          "ДА\n"
          "НЕТ\n"
          "Сколько=2\n"
          "Остаток=[1,3]\n"
          "Н=2\n");
  // Один общий модуль по трём путям — и ни одного слова о столкновении имён.
  REQUIRE(outcome.error.find("предложения из разных файлов") == std::string::npos);
}

TEST_CASE("two imported files that define one name are reported") {
  // База одна на всю программу: два независимых файла определили `член/2`, и
  // предикат молча получил бы предложения обоих.
  TempDir dir;
  dir.write("first.pld", "член(X, [X|_]).\n");
  dir.write("second.pld", "член(X, [_|T]) :- член(X, T).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"first.pld\").\n"
            ":- ИМПОРТ(\"second.pld\").\n"
            "?член(X, [1, 2]).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=1\nX=2\n");
  REQUIRE(outcome.error.find("warning") != std::string::npos);
  REQUIRE(outcome.error.find("член/2") != std::string::npos);
  REQUIRE(outcome.error.find("first.pld") != std::string::npos);
  REQUIRE(outcome.error.find("second.pld") != std::string::npos);
  REQUIRE(outcome.error.find("предложения из разных файлов") != std::string::npos);
}

TEST_CASE("a file that extends an imported predicate is not a clash") {
  // Расширение модуля своими предложениями — законный приём: файл видит и сам
  // подключает тот модуль, о котором речь, поэтому предупреждения нет.
  TempDir dir;
  dir.write("base.pld", "фрукт(яблоко).\n");
  dir.write("main.pld",
            ":- ИМПОРТ(\"base.pld\").\n"
            "фрукт(груша).\n"
            "?фрукт(X).\n");
  const LoadOutcome outcome = load(dir.path() / "main.pld");
  REQUIRE(outcome.ok);
  REQUIRE(outcome.output == "X=яблоко\nX=груша\n");
  REQUIRE(outcome.error.find("предложения из разных файлов") == std::string::npos);
}
