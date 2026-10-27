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
#include "prlib/formatter.hpp"
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

}  // namespace

int main(int argc, char** argv) {
  enableUtf8Console();

  CLI::App app{"Пролог-У: интерпретатор языка логического программирования"};
  app.set_version_flag("--version", prologd::versionBanner());

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
  // `--format` answers and exits like `--list-keywords`; the value is optional
  // (bare `--format` means the soft mode).
  std::string formatMode;
  std::size_t formatWidth = 80;
  std::size_t formatIndent = 1;
  std::string formatUnit = "tab";
  // Left unset on purpose: the engine's own defaults are the ones to use, and a
  // flag that repeats them would become a second place to change them.
  std::optional<std::size_t> maxDepth;
  std::optional<std::size_t> maxSteps;
  std::optional<std::size_t> maxFindAll;
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
                 "Recursion depth limit for one query (0 = unlimited; default: no limit)");
  app.add_option("--max-steps", maxSteps,
                 "Step limit for one query (0 = unlimited; default: no limit)");
  app.add_option("--max-findall", maxFindAll,
                 "Solution limit for one НАЙТИВСЕ (0 = unlimited; default: no limit)");
  app.add_option("--protocol", protocol, "Front-end protocol: text (default) or json")
      ->check(CLI::IsMember({"text", "json"}));
  app.add_flag("--list-keywords", listKeywords,
               "Print the reserved names as name/arity and exit");
  CLI::Option* formatOption = app.add_option(
      "--format", formatMode,
      "Print the source formatted to stdout and exit: soft (default), hard or line")
                                   ->expected(0, 1);
  app.add_option("--format-width", formatWidth,
                 "Soft formatting: what has to fit on one line (default 80)");
  app.add_option("--format-indent", formatIndent,
                 "Continuation indent in units (default 1)");
  app.add_option("--format-unit", formatUnit, "Indent unit: tab (default) or spaces")
      ->check(CLI::IsMember({"tab", "spaces"}));
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
  // for a variadic name (`ВЫВОД`, `ВЫП`/`call`).
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

  // A query of its own too: the formatter is a function of the text, and the
  // answer is the text — no interpreter, no engine.  Unparsable input exits 2
  // with the usual diagnostics, so a script can tell «formatted» from «not
  // formatted» without reading the output.
  if (formatOption != nullptr && formatOption->count() > 0) {
    if (protocol == "json") {
      std::cerr << "error: --format writes the source to stdout; drop --protocol json\n";
      return 1;
    }
    prologd::FormatOptions formatOptions;
    if (formatMode.empty() || formatMode == "soft") {
      formatOptions.mode = prologd::FormatMode::Soft;
    } else if (formatMode == "hard") {
      formatOptions.mode = prologd::FormatMode::Hard;
    } else if (formatMode == "line") {
      formatOptions.mode = prologd::FormatMode::Line;
    } else {
      std::cerr << "error: --format expects soft, hard or line, not " << formatMode << '\n';
      return 1;
    }
    formatOptions.width = formatWidth;
    formatOptions.indent_steps = formatIndent;
    formatOptions.indent_unit =
        formatUnit == "spaces" ? prologd::IndentUnit::Spaces : prologd::IndentUnit::Tab;
    std::vector<std::pair<std::string, std::string>> inputs;
    if (sources.empty()) {
      std::ostringstream buffer;
      buffer << std::cin.rdbuf();
      inputs.emplace_back("<stdin>", buffer.str());
    }
    for (const std::string& file : sources) {
      std::ifstream stream(prologd::fromUtf8Path(file), std::ios::binary);
      if (!stream) {
        std::cerr << "Cannot open input file: " << file << '\n';
        return 1;
      }
      std::ostringstream buffer;
      buffer << stream.rdbuf();
      inputs.emplace_back(file, buffer.str());
    }
    int status = 0;
    for (const auto& [name, text] : inputs) {
      prologd::FormatOptions options = formatOptions;
      options.source_name = name;
      const prologd::FormatResult formatted = prologd::formatSource(text, options);
      if (!formatted.ok()) {
        for (const prologd::PrologError& diagnostic : formatted.diagnostics) {
          std::cerr << prologd::DiagnosticSink::format(diagnostic) << '\n';
        }
        status = 2;
        continue;
      }
      std::cout << formatted.text;
    }
    return status;
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
    // `-i`, `-o` and `-e` name files from the command line, which is UTF-8 like
    // every other name here (part 133): the narrow `open` would read the bytes in
    // the process's ANSI code page instead.
    inputStream.open(prologd::fromUtf8Path(inputFile));
    if (!inputStream) {
      std::cerr << "Cannot open input file: " << inputFile << '\n';
      return 1;
    }
    engine.setStreams(inputStream, std::cout, std::cerr);
  }
  if (!outputFile.empty()) {
    outputStream.open(prologd::fromUtf8Path(outputFile));
    if (!outputStream) {
      std::cerr << "Cannot open output file: " << outputFile << '\n';
      return 1;
    }
    engine.setStreams(inputFile.empty() ? std::cin : inputStream, outputStream,
                      errorFile.empty() ? std::cerr : errorStream);
  }
  if (!errorFile.empty()) {
    errorStream.open(prologd::fromUtf8Path(errorFile));
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
  // One record, one place that copies the three limits in: the same values arrive
  // from the protocol and from the settings dialog, and a `0` means the same thing
  // in all three (task_46).
  prologd::Limits limits;
  if (maxDepth) {
    limits.maxDepth = *maxDepth;
  }
  if (maxSteps) {
    limits.maxSteps = *maxSteps;
  }
  if (maxFindAll) {
    limits.maxFindAllSolutions = *maxFindAll;
  }
  limits.applyTo(engine.options());

  std::vector<std::filesystem::path> includePaths;
  for (const std::string& directory : includeDirectories) {
    includePaths.push_back(prologd::fromUtf8Path(directory));
  }
  // The standard library travels beside the interpreter (part 84): a `stdlib`
  // folder next to `prologu.exe` is searched *last*, after every `-I` directory, so
  // a program of the same name beside the user's own file wins, and no flag is
  // needed for `:- ИМПОРТ("lists.pld").` in the portable package.  A build tree has
  // nothing beside the executable, which is where `-I stdlib` stays useful.
  const std::filesystem::path standard_library =
      prologd::standardLibraryDirectory(prologd::executableDirectory());
  if (!standard_library.empty()) {
    includePaths.push_back(standard_library);
  }

  prologd::ModuleLoader loader(engine, includePaths);
  if (protocol == "json") {
    return prologd::cli::runJsonSession(engine, loader, std::cin, std::cout);
  }
  int exit_code = 0;
  loader.setQueryRunner([&](const prologd::Query& query) {
    if (questions && !query.isDirective) {
      engine.io().write(engine.queryText(query));
      engine.io().newline();
    }
    try {
      engine.runQuery(query);
    } catch (const prologd::PrologRuntimeError& error) {
      // The place is part of the error, not a decoration: `raise` keeps the clause
      // being solved next to it, so a runtime error is printed in the same
      // `file:line:column: error: message` shape as a parse error — and an error
      // inside an `ИМПОРТ`ed file names *that* file (part 89).  `what()` alone used
      // to drop it, which left «деление на ноль» with nowhere to look.
      engine.io().errorStream() << prologd::DiagnosticSink::format(error.error()) << '\n';
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
    // Same line as above: the place travels with the error (`PrologError` carries
    // the location, `what()` carries the message alone).
    engine.io().errorStream() << prologd::DiagnosticSink::format(error.error()) << '\n';
    exit_code = 3;
  }

  return exit_code;
}
