#pragma once

#include <functional>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"

namespace prologd::test {

/// `text` as a double-quoted string literal of the dialect, ready to be glued
/// into the source of a test program.  The two characters a literal cannot hold
/// as they are, the backslash and the quote, are doubled — and the backslash is
/// the one that bites: a Windows path like `C:\Users\runneradmin\a.txt` carries
/// `\U` (unknown) and `\r` (a carriage return), so it must go through here.
/// A line break is not escaped: a literal does not cross one, so text with a
/// newline in it has no literal form and is not what a path needs.
inline std::string prologStringLiteral(std::string_view text) {
  std::string result;
  result.reserve(text.size() + 2);
  result.push_back('"');
  for (const char ch : text) {
    if (ch == '\\' || ch == '"') {
      result.push_back('\\');
    }
    result.push_back(ch);
  }
  result.push_back('"');
  return result;
}

struct RunResult {
  std::string output;
  std::string error;
  bool loaded = false;
  bool runtimeError = false;
  /// The program called `ЗАВЕРШЕНИЕ` (`halt`): it stopped there, and the
  /// statements after it never ran.
  bool halted = false;
  /// Where the first runtime error happened: the clause it was raised in, or the
  /// question it came from when the goal was written in the query (part 137).
  SourceLocation errorLocation;
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
  SourceLocation error_location;
  loader.setQueryRunner([&](const Query& query) {
    try {
      engine.runQuery(query);
    } catch (const PrologRuntimeError& error) {
      errorStream << error.what() << '\n';
      runtime_error = true;
      error_location = error.error().location;
    }
  });

  std::string error;
  RunResult result;
  try {
    result.loaded = loader.loadSource(source, "<test>", &error);
  } catch (const HaltRequest&) {
    // `ЗАВЕРШЕНИЕ` in a test program is the end of that program, not a failure:
    // the harness stands in for the front-end, so it catches the signal here —
    // otherwise it would take the whole test binary down.
    result.halted = true;
    result.loaded = true;
  } catch (const PrologRuntimeError& runtimeError) {
    errorStream << runtimeError.what() << '\n';
    runtime_error = true;
    error_location = runtimeError.error().location;
    result.loaded = true;
  }
  if (!result.loaded) {
    errorStream << error << '\n';
  }
  result.runtimeError = runtime_error;
  result.errorLocation = error_location;
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
