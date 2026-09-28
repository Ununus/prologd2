#include "protocol.hpp"

#include <cstddef>
#include <istream>
#include <optional>
#include <ostream>
#include <sstream>
#include <string>
#include <utility>

#include <nlohmann/json.hpp>

#include "prlib/utf8_path.hpp"
#include "prlib/version.hpp"

namespace prologd::cli {
namespace {

using Json = nlohmann::json;

/// Wire format version; bump it whenever a command or an event changes shape.
constexpr int kProtocolVersion = 1;

[[nodiscard]] std::string inputKindName(InputRequestKind kind) {
  switch (kind) {
    case InputRequestKind::Token:
      return "token";
    case InputRequestKind::Line:
      return "line";
    case InputRequestKind::CodePoint:
      return "codepoint";
  }
  return "line";
}

/// Drops the newline a diagnostic sink appends to every message.
[[nodiscard]] std::string withoutTrailingNewlines(std::string text) {
  while (!text.empty() && (text.back() == '\n' || text.back() == '\r')) {
    text.pop_back();
  }
  return text;
}

/// One JSON-line session: the request loop, event emission and the bridge that
/// turns `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД` into `input_request`/`input` pairs.
class Session {
 public:
  Session(Engine& engine, ModuleLoader& loader, std::istream& in, std::ostream& out)
      : engine_(engine), loader_(loader), in_(in), out_(out) {}

  int run() {
    engine_.setStreams(idle_input_, output_, error_);
    // Installed after setStreams, which replaces the whole I/O context: every
    // interactive read now goes through the protocol instead of a stream.
    engine_.io().setInputRequestHandler(
        [this](InputRequestKind kind) { return answerInputRequest(kind); });
    loader_.setQueryRunner([this](const Query& query) { runQuery(query); });

    emit(Json{{"event", "ready"},
              {"protocol", kProtocolVersion},
              {"version", std::string(versionString())}});

    std::string line;
    while (std::getline(in_, line)) {
      if (line.empty()) {
        continue;
      }
      Json request;
      try {
        request = Json::parse(line);
      } catch (const Json::exception& parse_error) {
        fail("protocol", std::string("некорректный JSON: ") + parse_error.what());
        continue;
      }
      if (!request.is_object()) {
        fail("protocol", "запрос должен быть объектом JSON");
        continue;
      }
      const std::string command = request.value("cmd", std::string());
      if (command == "quit") {
        break;
      }
      dispatch(command, request);
      flush();
    }

    flush();
    emit(Json{{"event", "bye"}});
    return exit_code_;
  }

 private:
  void dispatch(const std::string& command, const Json& request) {
    if (command == "load" || command == "query") {
      load(command, request);
      return;
    }
    if (command == "input") {
      fail("protocol", "нет ожидающего запроса ввода");
      return;
    }
    if (command == "interrupt") {
      // Effective between commands and while the interpreter waits for input;
      // a runaway query has to be stopped by ending the process.
      engine_.requestStop();
      return;
    }
    fail("protocol", "неизвестная команда: " + command);
  }

  void load(const std::string& command, const Json& request) {
    std::string error;
    const bool has_path = request.contains("path");
    const bool has_text = request.contains("text");
    if (has_path == has_text) {
      fail("protocol", command + ": нужен ровно один из параметров path или text");
      return;
    }
    bool ok = false;
    if (has_path) {
      ok = loader_.loadFile(fromUtf8Path(request.at("path").get<std::string>()), &error);
    } else {
      const std::string name = request.value("name", std::string("<buffer>"));
      ok = loader_.loadSource(request.at("text").get<std::string>(), name, &error);
    }
    if (!ok) {
      // The parse diagnostics already carry `file:line:column`; the loader's
      // message is only a summary, so it is used when nothing was reported.
      if (!flushDiagnostics("parse")) {
        fail("parse", error);
      }
      exit_code_ = 2;
    }
  }

  void runQuery(const Query& query) {
    try {
      const bool found = engine_.runQuery(query);
      emit(Json{{"event", "result"}, {"found", found}});
    } catch (const PrologRuntimeError& runtime_error) {
      fail("runtime", runtime_error.what());
      exit_code_ = 3;
    }
  }

  std::optional<std::string> answerInputRequest(InputRequestKind kind) {
    flush();  // keep the event order: the output so far, then the prompt
    emit(Json{{"event", "input_request"}, {"kind", inputKindName(kind)}});

    std::string line;
    while (std::getline(in_, line)) {
      if (line.empty()) {
        continue;
      }
      Json request;
      try {
        request = Json::parse(line);
      } catch (const Json::exception& parse_error) {
        fail("protocol", std::string("некорректный JSON: ") + parse_error.what());
        continue;
      }
      if (!request.is_object()) {
        fail("protocol", "запрос должен быть объектом JSON");
        continue;
      }
      const std::string command = request.value("cmd", std::string());
      if (command == "input") {
        return request.value("text", std::string());
      }
      if (command == "interrupt" || command == "quit") {
        engine_.requestStop();
        return std::nullopt;  // end of input: the pending read fails
      }
      fail("protocol", "ожидался ответ input, получено: " + command);
    }
    return std::nullopt;
  }

  void flush() {
    const std::string text = output_.str();
    if (!text.empty()) {
      output_.str(std::string());
      output_.clear();
      emit(Json{{"event", "output"}, {"text", text}});
    }
    flushDiagnostics("runtime");
  }

  /// Emits whatever the engine wrote to its error stream; true when something
  /// was reported.
  bool flushDiagnostics(const std::string& kind) {
    const std::string errors = withoutTrailingNewlines(error_.str());
    if (errors.empty()) {
      return false;
    }
    error_.str(std::string());
    error_.clear();
    emit(Json{{"event", "error"}, {"kind", kind}, {"message", errors}});
    return true;
  }

  void fail(std::string kind, std::string message) {
    emit(Json{{"event", "error"}, {"kind", std::move(kind)}, {"message", std::move(message)}});
  }

  void emit(const Json& event) {
    out_ << event.dump() << '\n';
    out_.flush();
  }

  Engine& engine_;
  ModuleLoader& loader_;
  std::istream& in_;
  std::ostream& out_;

  /// Interactive reads never reach this stream: the input handler answers them.
  std::istringstream idle_input_;
  std::ostringstream output_;
  std::ostringstream error_;
  int exit_code_ = 0;
};

}  // namespace

int runJsonSession(Engine& engine, ModuleLoader& loader, std::istream& in, std::ostream& out) {
  Session session(engine, loader, in, out);
  return session.run();
}

}  // namespace prologd::cli
