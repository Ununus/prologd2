#include <CLI/CLI.hpp>

#include <csignal>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/keywords.hpp"
#include "prlib/module_loader.hpp"
#include "prlib/utf8_path.hpp"
#include "prlib/version.hpp"

#include "protocol.hpp"

#if defined(_WIN32)
#include <io.h>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#define PROLOGD_ISATTY _isatty(_fileno(stdin))
#else
#include <unistd.h>
#define PROLOGD_ISATTY isatty(fileno(stdin))
#endif

namespace {

#if defined(_WIN32)
/// Switch the Windows console to UTF-8 so Cyrillic output is not mangled.
void enableUtf8Console() {
  SetConsoleOutputCP(CP_UTF8);
  SetConsoleCP(CP_UTF8);
}
#else
void enableUtf8Console() {}
#endif

/// Set by the SIGINT/SIGTERM handler.  The engine polls it through
/// `EngineOptions::externalStop`, which is the only part of an interrupt that
/// may be done from a signal handler.
volatile std::sig_atomic_t g_interrupted = 0;

void handleInterruptSignal(int) { g_interrupted = 1; }

/// Consumes a pending interrupt.  The flag is cleared on delivery so that one
/// Ctrl+C stops one query instead of every later one.
bool consumeInterrupt() {
  if (g_interrupted == 0) {
    return false;
  }
  g_interrupted = 0;
  return true;
}

std::string queryText(prologd::Engine& engine, const prologd::Query& query) {
  std::string text = "?";
  for (std::size_t i = 0; i < query.goals.size(); ++i) {
    if (i != 0) {
      text += ',';
    }
    text += engine.format(query.goals[i]);
  }
  text += '.';
  return text;
}

}  // namespace

int main(int argc, char** argv) {
  enableUtf8Console();

  CLI::App app{"PrologD logic programming language interpreter"};
  app.set_version_flag("--version", std::string(prologd::versionString()));

  std::vector<std::string> sources;
  std::vector<std::string> includeDirectories;
  std::vector<std::string> positional;
  std::string inputFile;
  std::string outputFile;
  std::string errorFile;
  bool questions = false;
  bool trace = false;
  bool noWarnings = false;
  bool listKeywords = false;
  std::string protocol = "text";
  // Left unset on purpose: the engine's own defaults are the ones to use, and a
  // flag that repeats them would become a second place to change them.
  std::optional<std::size_t> maxDepth;
  std::optional<std::size_t> maxSteps;

  app.add_option("-s,--source", sources, "Interpret the given source file (repeatable)");
  app.add_option("-I,--include", includeDirectories, "Add an import search directory");
  app.add_option("-i,--input", inputFile, "Read program input from this file");
  app.add_option("-o,--output", outputFile, "Write the program output to this file");
  app.add_option("-e,--error", errorFile, "Write diagnostics to this file");
  app.add_flag("-q,--questions", questions, "Echo queries before executing them");
  app.add_flag("-t,--trace", trace, "Start with tracing enabled");
  app.add_flag("--no-warnings", noWarnings,
               "Do not print warnings (they never change the exit code)");
  app.add_option("--max-depth", maxDepth,
                 "Recursion depth limit for one query (0 = unlimited, default 10000)");
  app.add_option("--max-steps", maxSteps,
                 "Step limit for one query (0 = unlimited, default unlimited)");
  app.add_option("--protocol", protocol, "Front-end protocol: text (default) or json")
      ->check(CLI::IsMember({"text", "json"}));
  app.add_flag("--list-keywords", listKeywords,
               "Print the reserved names as name/arity and exit");
  app.add_option("files", positional, "Source files");

  try {
    app.parse(argc, argv);
  } catch (const CLI::ParseError& parseError) {
    return app.exit(parseError);
  }

  for (const std::string& file : positional) {
    sources.push_back(file);
  }

  // A query, not a run mode: answer and exit before anything is loaded.  One
  // `name/arity` per line, a bare name for an operator or directive, and `name/+`
  // for the variadic `ВЫВОД`.
  if (listKeywords) {
    for (const prologd::KeywordInfo& keyword : prologd::reservedKeywords()) {
      if (keyword.arities.empty()) {
        std::cout << keyword.name << (keyword.variadic ? "/+" : "") << '\n';
        continue;
      }
      for (const std::size_t arity : keyword.arities) {
        std::cout << keyword.name << '/' << arity << '\n';
      }
    }
    return 0;
  }

  if (protocol == "json" &&
      (!inputFile.empty() || !outputFile.empty() || !errorFile.empty())) {
    std::cerr << "error: --protocol json owns stdin and stdout; drop -i/-o/-e\n";
    return 1;
  }

  std::ifstream inputStream;
  std::ofstream outputStream;
  std::ofstream errorStream;

  prologd::Engine engine;
  if (!inputFile.empty()) {
    inputStream.open(inputFile);
    if (!inputStream) {
      std::cerr << "Cannot open input file: " << inputFile << '\n';
      return 1;
    }
    engine.setStreams(inputStream, std::cout, std::cerr);
  }
  if (!outputFile.empty()) {
    outputStream.open(outputFile);
    if (!outputStream) {
      std::cerr << "Cannot open output file: " << outputFile << '\n';
      return 1;
    }
    engine.setStreams(inputFile.empty() ? std::cin : inputStream, outputStream,
                      errorFile.empty() ? std::cerr : errorStream);
  }
  if (!errorFile.empty()) {
    errorStream.open(errorFile);
    if (!errorStream) {
      std::cerr << "Cannot open error file: " << errorFile << '\n';
      return 1;
    }
    engine.setStreams(inputFile.empty() ? std::cin : inputStream,
                      outputFile.empty() ? std::cout : outputStream, errorStream);
  }

  engine.initialize();
  engine.setTrace(trace);
  if (noWarnings) {
    // Warnings are advice: dropping them touches nothing else, so the filter is
    // a diagnostic hook that still writes the usual `file:line:column: error:`
    // lines for everything else.
    engine.setDiagnosticHook([&engine](const prologd::PrologError& diagnostic) {
      if (diagnostic.severity == prologd::Severity::Warning) {
        return;
      }
      engine.io().errorStream() << prologd::DiagnosticSink::format(diagnostic) << '\n';
    });
  }

  std::signal(SIGINT, handleInterruptSignal);
#if defined(SIGTERM)
  std::signal(SIGTERM, handleInterruptSignal);
#endif
  engine.options().externalStop = consumeInterrupt;
  if (maxDepth) {
    engine.options().maxDepth = *maxDepth;
  }
  if (maxSteps) {
    engine.options().maxSteps = *maxSteps;
  }

  std::vector<std::filesystem::path> includePaths;
  for (const std::string& directory : includeDirectories) {
    includePaths.push_back(prologd::fromUtf8Path(directory));
  }

  prologd::ModuleLoader loader(engine, includePaths);
  if (protocol == "json") {
    return prologd::cli::runJsonSession(engine, loader, std::cin, std::cout);
  }
  int exit_code = 0;
  loader.setQueryRunner([&](const prologd::Query& query) {
    if (questions && !query.isDirective) {
      engine.io().write(queryText(engine, query));
      engine.io().newline();
    }
    try {
      engine.runQuery(query);
    } catch (const prologd::PrologRuntimeError& error) {
      engine.io().errorStream() << error.what() << '\n';
      exit_code = 3;
    }
  });

  try {
    if (sources.empty()) {
      if (PROLOGD_ISATTY) {
        // Minimal REPL: one statement per line.
        std::string line;
        while (true) {
          std::cout << "?- " << std::flush;
          if (!std::getline(std::cin, line)) {
            break;
          }
          if (line.empty()) {
            continue;
          }
          g_interrupted = 0;  // Ctrl+C at the prompt abandons the line
          std::string error;
          if (!loader.loadSource(line, "<stdin>", &error)) {
            engine.io().errorStream() << error << '\n';
          }
        }
        return exit_code;
      }
      std::string source((std::istreambuf_iterator<char>(std::cin)),
                         std::istreambuf_iterator<char>());
      std::string error;
      if (!loader.loadSource(source, "<stdin>", &error)) {
        engine.io().errorStream() << error << '\n';
        return 2;
      }
      return exit_code;
    }
    for (const std::string& file : sources) {
      std::string error;
      if (!loader.loadFile(prologd::fromUtf8Path(file), &error)) {
        engine.io().errorStream() << error << '\n';
        exit_code = 2;
      }
    }
  } catch (const prologd::PrologRuntimeError& error) {
    engine.io().errorStream() << error.what() << '\n';
    exit_code = 3;
  }

  return exit_code;
}
