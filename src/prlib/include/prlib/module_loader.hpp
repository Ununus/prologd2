#pragma once

#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/parser.hpp"

namespace prologd {

/// The directory the running interpreter lives in, empty when it cannot be found.
///
/// The standard library travels beside the executable (part 84), and this is how
/// the interpreter learns where «beside» is.  Windows asks the loader about the
/// running module (`GetModuleFileNameW`), Linux reads the `/proc/self/exe` link;
/// where neither is available the answer is empty and `ИМПОРТ` searches only the
/// directories it was given.
std::filesystem::path executableDirectory();

/// The standard library that belongs to an interpreter in `directory`, empty when
/// there is none.
///
/// The rule is one line — a `stdlib` folder below the executable — but it is a
/// *pure* function of the directory on purpose: a test can exercise it in a
/// temporary folder instead of copying an interpreter next to a library.  A file,
/// rather than a folder, named `stdlib` is not a library.
std::filesystem::path standardLibraryDirectory(const std::filesystem::path& directory);

/// Loads source files and their `ИМПОРТ(...)` dependencies into an `Engine`.
///
/// Replaces the old textual preprocessor: imports are resolved relative to the
/// importing file and the configured include directories, each file is loaded
/// once, cycles are detected and paths cannot escape the optional root.
class ModuleLoader {
 public:
  using QueryRunner = std::function<void(const Query&)>;

  explicit ModuleLoader(Engine& engine,
                        std::vector<std::filesystem::path> include_paths = {},
                        std::optional<std::filesystem::path> root = std::nullopt);

  /// How one attempted import path ended.  Kept so a failed import can name the
  /// directories it tried instead of only the file it wanted (task_32).
  enum class SearchOutcome {
    Found,        ///< the file was there and usable
    Missing,      ///< nothing at that path
    NotAFile,     ///< something is there, but it is a directory
    OutsideRoot,  ///< a file, but outside the configured root
  };

  /// One place the import search visited, in the order it was visited.
  struct SearchStep {
    std::filesystem::path path;
    SearchOutcome outcome = SearchOutcome::Missing;
  };

  /// Load `path` and everything it imports.  Returns false on error.
  bool loadFile(const std::filesystem::path& path, std::string* error = nullptr);

  /// Load an in-memory source (REPL, tests, stdin).
  bool loadSource(std::string_view source, const std::string& virtual_name,
                  std::string* error = nullptr);

  void setQueryRunner(QueryRunner runner) { query_runner_ = std::move(runner); }

  [[nodiscard]] const std::vector<std::filesystem::path>& loadedFiles() const noexcept {
    return loaded_paths_;
  }

 private:
  bool process(const ParsedProgram& program, const std::filesystem::path& file,
               std::string* error);
  std::optional<std::filesystem::path> resolve(const std::string& name,
                                               const std::filesystem::path& importer,
                                               std::vector<SearchStep>* steps) const;
  bool withinRoot(const std::filesystem::path& candidate) const;
  static std::optional<std::string> readFileText(const std::filesystem::path& path,
                                                 std::string* error);

  /// Warn once per predicate whose clauses came from two files that do not
  /// import one another: `ИМПОРТ` merges everything into one database, so two
  /// unrelated definitions silently become one predicate.  Runs after the
  /// outermost file finished loading (task_43).
  void reportModuleCollisions();
  /// True when `from` imports `to`, directly or through other files.
  [[nodiscard]] bool importsPath(const std::string& from, const std::string& to) const;

  Engine& engine_;
  std::vector<std::filesystem::path> include_paths_;
  std::optional<std::filesystem::path> root_;
  std::unordered_set<std::string> loaded_;
  std::vector<std::string> loading_stack_;
  std::vector<std::filesystem::path> loaded_paths_;
  /// Import edges seen so far (`importer -> imported`, canonical keys) and the
  /// predicate/file pairs already reported — a file loaded later can join a
  /// clash the previous load already described.
  std::unordered_map<std::string, std::unordered_set<std::string>> imports_;
  std::unordered_set<std::string> reported_collisions_;
  QueryRunner query_runner_;
};

}  // namespace prologd
