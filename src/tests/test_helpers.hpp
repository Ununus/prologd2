#pragma once

#include <functional>
#include <memory>
#include <sstream>
#include <string>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"

namespace prologd::test {

struct RunResult {
  std::string output;
  std::string error;
  bool loaded = false;
  bool runtimeError = false;
};

/// Run a whole program (clauses and queries) in-memory and capture output.
/// `configure` runs after `initialize()` and before the program is loaded; it is
/// the hook for engine options such as `externalStop`.
/// `include_paths` are searched by `ИМПОРТ` after the importing file's own
/// directory, exactly like the `-I` option of the CLI.
inline RunResult runProgram(const std::string& source, const std::string& input = {},
                            std::shared_ptr<GraphicsBackend> graphics = nullptr,
                            const std::function<void(Engine&)>& configure = {},
                            std::vector<std::filesystem::path> include_paths = {}) {
  std::istringstream inputStream(input);
  std::ostringstream outputStream;
  std::ostringstream errorStream;

  Engine engine;
  engine.setStreams(inputStream, outputStream, errorStream);
  engine.initialize();
  if (graphics) {
    engine.setGraphicsBackend(std::move(graphics));
  }
  if (configure) {
    configure(engine);
  }

  ModuleLoader loader(engine, std::move(include_paths));
  bool runtime_error = false;
  loader.setQueryRunner([&](const Query& query) {
    try {
      engine.runQuery(query);
    } catch (const PrologRuntimeError& error) {
      errorStream << error.what() << '\n';
      runtime_error = true;
    }
  });

  std::string error;
  RunResult result;
  try {
    result.loaded = loader.loadSource(source, "<test>", &error);
  } catch (const PrologRuntimeError& runtimeError) {
    errorStream << runtimeError.what() << '\n';
    runtime_error = true;
    result.loaded = true;
  }
  if (!result.loaded) {
    errorStream << error << '\n';
  }
  result.runtimeError = runtime_error;
  result.output = outputStream.str();
  result.error = errorStream.str();
  return result;
}

/// Run a program whose `ИМПОРТ` directives must be resolved.
inline RunResult runProgramWithIncludes(const std::string& source, const std::string& input,
                                       std::vector<std::filesystem::path> include_paths) {
  return runProgram(source, input, nullptr, {}, std::move(include_paths));
}

}  // namespace prologd::test
