#include "prlib/module_loader.hpp"

#include <algorithm>
#include <fstream>
#include <sstream>

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

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

bool ModuleLoader::loadFile(const std::filesystem::path& path, std::string* error) {
  std::error_code code;
  const auto canonical = std::filesystem::weakly_canonical(path, code);
  const std::string key = toUtf8PathGeneric(code ? path : canonical);
  if (!loading_stack_.empty()) {
    // The file on top of the stack resolved this import.  Recorded before the
    // import-once test, so a diamond keeps all of its edges (task_43).
    imports_[loading_stack_.back()].insert(key);
  }
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
  const auto file_path = code ? path : canonical;
  ParsedProgram program = engine_.parseSource(*text, key);
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
  if (loading_stack_.empty()) {
    // The outermost file and everything it imports are in: the cross-file view
    // of the database can be checked now (task_43).
    reportModuleCollisions();
  }
  return true;
}

bool ModuleLoader::loadSource(std::string_view source, const std::string& virtual_name,
                              std::string* error) {
  ParsedProgram program = engine_.parseSource(source, virtual_name);
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
  // Everything this unit and its imports define is loaded: a goal that names
  // nothing can now be told apart from one that simply has no solutions.
  engine_.checkCallSites(program);
  return true;
}

bool ModuleLoader::importsPath(const std::string& from, const std::string& to) const {
  if (from == to) {
    return true;
  }
  std::vector<std::string> pending{from};
  std::unordered_set<std::string> seen{from};
  while (!pending.empty()) {
    const std::string current = std::move(pending.back());
    pending.pop_back();
    const auto it = imports_.find(current);
    if (it == imports_.end()) {
      continue;
    }
    for (const std::string& next : it->second) {
      if (next == to) {
        return true;
      }
      if (seen.insert(next).second) {
        pending.push_back(next);
      }
    }
  }
  return false;
}

void ModuleLoader::reportModuleCollisions() {
  // A predicate fed by two files that do not import one another is the clash the
  // old lessons hit: the definitions were separate, and the one global database
  // silently made one predicate with more clauses out of them.  A file that adds
  // clauses to a module it imports is the wanted extension and stays silent —
  // the import graph tells the two apart (task_43).
  for (const Functor& functor : engine_.database().predicates()) {
    const Database::ClauseListPtr clauses = engine_.database().clausesFor(functor);
    std::vector<std::pair<std::string, std::size_t>> by_file;
    for (const Clause& clause : *clauses) {
      const std::string& file = clause.location.file;
      if (file.empty() || file.front() == '<') {
        continue;  // made at run time, or a virtual source (tests, the prompt)
      }
      const auto found = std::find_if(by_file.begin(), by_file.end(),
                                      [&file](const auto& entry) { return entry.first == file; });
      if (found == by_file.end()) {
        by_file.emplace_back(file, 1);
      } else {
        ++found->second;
      }
    }
    if (by_file.size() < 2) {
      continue;
    }
    bool warned = false;
    for (std::size_t i = 0; i < by_file.size() && !warned; ++i) {
      for (std::size_t j = i + 1; j < by_file.size(); ++j) {
        if (importsPath(by_file[i].first, by_file[j].first) ||
            importsPath(by_file[j].first, by_file[i].first)) {
          continue;  // one file can see the other: an extension, not a clash
        }
        std::string key = functor.name + '/' + std::to_string(functor.arity) + '|' +
                          by_file[i].first + '|' + by_file[j].first;
        if (reported_collisions_.insert(std::move(key)).second) {
          std::string message = functor.name + '/' + std::to_string(functor.arity);
          message += ": предложения из разных файлов объединены в один предикат — ";
          message += by_file[i].first;
          message += " (предложений: " + std::to_string(by_file[i].second) + ')';
          message += ", ";
          message += by_file[j].first;
          message += " (предложений: " + std::to_string(by_file[j].second) + ')';
          message += "; если это разные определения, переименуйте одно";
          engine_.reportWarning(ErrorCode::ConflictingDefinitions, std::move(message));
        }
        warned = true;  // one warning per predicate
        break;
      }
    }
  }
}

std::filesystem::path executableDirectory() {
#if defined(_WIN32)
  // A path longer than the buffer is not an error but a request to ask again with
  // more room, which is why the call is looped rather than done once.
  std::wstring buffer(260, L'\0');
  for (;;) {
    const DWORD written =
        ::GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (written == 0) {
      return {};
    }
    if (written < buffer.size()) {
      buffer.resize(written);
      break;
    }
    buffer.resize(buffer.size() * 2);
  }
  return std::filesystem::path(buffer).parent_path();
#elif defined(__linux__)
  std::error_code error;
  const std::filesystem::path self = std::filesystem::read_symlink("/proc/self/exe", error);
  return error ? std::filesystem::path{} : self.parent_path();
#else
  return {};
#endif
}

std::filesystem::path standardLibraryDirectory(const std::filesystem::path& directory) {
  if (directory.empty()) {
    return {};
  }
  std::error_code error;
  const std::filesystem::path candidate = directory / "stdlib";
  return std::filesystem::is_directory(candidate, error) ? candidate
                                                         : std::filesystem::path{};
}

}  // namespace prologd
