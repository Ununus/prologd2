#include "prlib/module_loader.hpp"

#include <algorithm>
#include <fstream>
#include <sstream>

#include "prlib/utf8.hpp"
#include "prlib/utf8_path.hpp"

namespace prologd {

namespace {

/// The candidate list of a failed import: absolute paths in the order they were
/// tried, capped so a long `-I` chain cannot flood the output.  One line, so the
/// `file:line:column: error: message` shape survives.
std::string describeImportSearch(const std::vector<ModuleLoader::SearchStep>& steps) {
  constexpr std::size_t kMaxEntries = 5;
  std::string text;
  const std::size_t shown = std::min(steps.size(), kMaxEntries);
  for (std::size_t index = 0; index < shown; ++index) {
    if (index != 0) {
      text += "; ";
    }
    // Absolute, because the first candidate of an unsaved buffer is relative to
    // the process working directory and an empty prefix would say nothing.
    std::error_code code;
    const std::filesystem::path absolute = std::filesystem::absolute(steps[index].path, code);
    text += toUtf8Path(code ? steps[index].path : absolute);
    switch (steps[index].outcome) {
      case ModuleLoader::SearchOutcome::NotAFile:
        text += " (это каталог)";
        break;
      case ModuleLoader::SearchOutcome::OutsideRoot:
        text += " (вне корневого каталога)";
        break;
      case ModuleLoader::SearchOutcome::Found:
      case ModuleLoader::SearchOutcome::Missing:
        break;
    }
  }
  if (steps.size() > shown) {
    text += "; …";
  }
  return text;
}

}  // namespace

ModuleLoader::ModuleLoader(Engine& engine, std::vector<std::filesystem::path> include_paths,
                           std::optional<std::filesystem::path> root)
    : engine_(engine), include_paths_(std::move(include_paths)), root_(std::move(root)) {}

std::optional<std::string> ModuleLoader::readFileText(const std::filesystem::path& path,
                                                      std::string* error) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    if (error != nullptr) {
      *error = "Не могу открыть файл: " + toUtf8Path(path);
    }
    return std::nullopt;
  }
  std::ostringstream buffer;
  buffer << stream.rdbuf();
  std::string text = buffer.str();
  text = std::string(stripByteOrderMark(text));
  return text;
}

bool ModuleLoader::withinRoot(const std::filesystem::path& candidate) const {
  if (!root_) {
    return true;
  }
  std::error_code code;
  const auto canonical_root = std::filesystem::weakly_canonical(*root_, code);
  const auto canonical_candidate = std::filesystem::weakly_canonical(candidate, code);
  if (code) {
    return false;
  }
  const auto root_text = toUtf8PathGeneric(canonical_root);
  const auto candidate_text = toUtf8PathGeneric(canonical_candidate);
  return candidate_text == root_text ||
         candidate_text.rfind(root_text + "/", 0) == 0;
}

std::optional<std::filesystem::path> ModuleLoader::resolve(
    const std::string& name, const std::filesystem::path& importer,
    std::vector<SearchStep>* steps) const {
  steps->clear();
  if (name.empty()) {
    return std::nullopt;
  }
  const std::filesystem::path requested = fromUtf8Path(name);
  std::vector<std::filesystem::path> candidates;
  if (requested.is_absolute()) {
    candidates.push_back(requested);
  } else {
    // The importing file's own directory first, then every `-I` directory in
    // the order the user gave them: a local module wins over a shared one.
    candidates.push_back(importer / requested);
    for (const auto& directory : include_paths_) {
      candidates.push_back(directory / requested);
    }
  }
  for (const auto& candidate : candidates) {
    std::error_code code;
    if (!std::filesystem::exists(candidate, code) || code) {
      steps->push_back(SearchStep{candidate, SearchOutcome::Missing});
      continue;
    }
    if (!std::filesystem::is_regular_file(candidate, code) || code) {
      steps->push_back(SearchStep{candidate, SearchOutcome::NotAFile});
      continue;
    }
    if (!withinRoot(candidate)) {
      steps->push_back(SearchStep{candidate, SearchOutcome::OutsideRoot});
      continue;
    }
    steps->push_back(SearchStep{candidate, SearchOutcome::Found});
    return std::filesystem::weakly_canonical(candidate, code);
  }
  return std::nullopt;
}

void ModuleLoader::extractInputLines(std::string& text) const {
  std::string cleaned;
  cleaned.reserve(text.size());
  std::size_t start = 0;
  while (start <= text.size()) {
    const std::size_t end = text.find('\n', start);
    const std::size_t length = (end == std::string::npos ? text.size() : end) - start;
    const std::string_view line(text.data() + start, length);
    if (!line.empty() && line.front() == '$') {
      engine_.io().pushPreloadedLine(std::string(line.substr(1)));
    } else {
      cleaned.append(line);
      cleaned.push_back('\n');
    }
    if (end == std::string::npos) {
      break;
    }
    start = end + 1;
  }
  text = std::move(cleaned);
}

bool ModuleLoader::loadFile(const std::filesystem::path& path, std::string* error) {
  std::error_code code;
  const auto canonical = std::filesystem::weakly_canonical(path, code);
  const std::string key = toUtf8PathGeneric(code ? path : canonical);
  if (loaded_.count(key) != 0) {
    return true;  // import-once
  }
  if (std::find(loading_stack_.begin(), loading_stack_.end(), key) != loading_stack_.end()) {
    if (error != nullptr) {
      std::string chain;
      for (const std::string& entry : loading_stack_) {
        chain += entry;
        chain += " -> ";
      }
      chain += key;
      *error = "Циклический импорт: " + chain;
    }
    return false;
  }
  if (!withinRoot(path)) {
    if (error != nullptr) {
      *error = "Импорт выходит за пределы корневого каталога: " + toUtf8Path(path);
    }
    return false;
  }
  const auto text = readFileText(path, error);
  if (!text) {
    return false;
  }
  std::string source = *text;
  extractInputLines(source);
  const auto file_path = code ? path : canonical;
  ParsedProgram program = engine_.parseSource(source, key);
  if (!program.ok) {
    if (error != nullptr) {
      *error = "Ошибка при разборе файла: " + key;
    }
    return false;
  }
  loading_stack_.push_back(key);
  const bool ok = process(program, file_path, error);
  loading_stack_.pop_back();
  if (!ok) {
    return false;
  }
  loaded_.insert(key);
  loaded_paths_.push_back(file_path);
  return true;
}

bool ModuleLoader::loadSource(std::string_view source, const std::string& virtual_name,
                              std::string* error) {
  std::string text(source);
  extractInputLines(text);
  ParsedProgram program = engine_.parseSource(text, virtual_name);
  if (!program.ok) {
    if (error != nullptr) {
      *error = "Ошибка при разборе: " + virtual_name;
    }
    return false;
  }
  return process(program, fromUtf8Path(virtual_name), error);
}

bool ModuleLoader::process(const ParsedProgram& program, const std::filesystem::path& file,
                           std::string* error) {
  for (const StatementRef& statement : program.order) {
    switch (statement.kind) {
      case StatementRef::Kind::Clause:
        engine_.database().addClause(program.clauses[statement.index]);
        break;
      case StatementRef::Kind::Query:
        if (query_runner_) {
          query_runner_(program.queries[statement.index]);
        }
        break;
      case StatementRef::Kind::Import: {
        const ImportDirective& directive = program.imports[statement.index];
        std::vector<SearchStep> search;
        const auto resolved = resolve(directive.path, file.parent_path(), &search);
        if (!resolved) {
          if (error != nullptr) {
            std::string message = "Не найден импортируемый файл '" + directive.path +
                                  "' (" + directive.location.toString() + ")";
            if (!search.empty()) {
              message += ". Искался в: " + describeImportSearch(search);
            }
            *error = std::move(message);
          }
          return false;
        }
        if (!loadFile(*resolved, error)) {
          return false;
        }
        break;
      }
    }
  }
  return true;
}

}  // namespace prologd
