#pragma once

#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/parser.hpp"

namespace prologd {

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
                                               const std::filesystem::path& importer) const;
  bool withinRoot(const std::filesystem::path& candidate) const;
  static std::optional<std::string> readFileText(const std::filesystem::path& path,
                                                 std::string* error);
  /// Remove the historical `$...` preloaded input lines from source text.
  void extractInputLines(std::string& text) const;

  Engine& engine_;
  std::vector<std::filesystem::path> include_paths_;
  std::optional<std::filesystem::path> root_;
  std::unordered_set<std::string> loaded_;
  std::vector<std::string> loading_stack_;
  std::vector<std::filesystem::path> loaded_paths_;
  QueryRunner query_runner_;
};

}  // namespace prologd
