#include "protocol.hpp"

#include <cstddef>
#include <istream>
#include <optional>
#include <ostream>
#include <sstream>
#include <string>
#include <utility>

#include <nlohmann/json.hpp>

#include "prlib/formatter.hpp"
#include "prlib/keywords.hpp"
#include "prlib/utf8_path.hpp"
#include "prlib/version.hpp"

namespace prologd::cli {
namespace {

using Json = nlohmann::json;

/// Wire format version; bump it whenever a command or an event changes shape.
/// 2: the `ready` event carries `keywords`.
/// 3: `step` events and the `step` command, `trace` events, and `file`/`line`/
///    `column` on `error` events (a front-end no longer parses them out of the
///    message), plus `step`/`trace` flags on `load` and `query`.
/// 4: `error` events carry `severity` (`error` or `warning`).
/// 5: `load` takes `questions` — `false` loads a program without running its
///    own `?`-statements (the editor's margin runs one query alone, task_36).
/// 6: `format` — the formatter, answerable at any time; the answer is a
///    `formatted` event (task_30).
/// 7: the modes of `format` are `line`, `soft` and `hard` — «не менять» left
///    the surface and «в одну строку» joined it.
/// 8: `loaded` — the load and the program's own `?`-statements are over, which
///    is what tells a front-end that a run *finished*.
constexpr int kProtocolVersion = 8;

[[nodiscard]] std::string stepActionName(StepAction action) {
  switch (action) {
    case StepAction::Call:
      return "call";
    case StepAction::Exit:
      return "exit";
    case StepAction::Redo:
      return "redo";
    case StepAction::Fail:
      return "fail";
  }
  return "call";
}

/// Adds the position of a diagnostic, when it has one.  A goal that came from a
/// query typed at the prompt does not, and then the fields are left out.
void addLocation(Json& event, const SourceLocation& location) {
  if (location.file.empty()) {
    return;
  }
  event["file"] = location.file;
  event["line"] = location.line;
  event["column"] = location.column;
}

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

/// The reserved names with their kind and arities, so a front-end can colour
/// and complete them without a second round trip.  `variadic` appears only when
/// it is true, which keeps the event small.
[[nodiscard]] Json keywordList() {
  Json list = Json::array();
  for (const KeywordInfo& keyword : reservedKeywords()) {
    Json entry{{"name", std::string(keyword.name)},
               {"kind", std::string(keywordKindName(keyword.kind))}};
    Json arities = Json::array();
    for (const std::size_t arity : keyword.arities) {
      arities.push_back(arity);
    }
    entry["arities"] = std::move(arities);
    if (keyword.variadic) {
      entry["variadic"] = true;
    }
    list.push_back(std::move(entry));
  }
  return list;
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
    // The trace text of `ТРАССА` goes out as `trace` events, so a front-end can
    // colour it apart from the program's own output (the console keeps reading
    // it in the output stream, where it always was).
    engine_.io().setTraceSink([this](std::string_view text) {
      emit(Json{{"event", "trace"}, {"text", std::string(text) + "\n"}});
    });
    // Diagnostics come with their position: a front-end must not have to parse
    // `file:line:column:` out of the message.
    engine_.setDiagnosticHook([this](const PrologError& diagnostic) {
      reportDiagnostic(diagnostic, "parse");
    });
    loader_.setQueryRunner([this](const Query& query) { runQuery(query); });

    emit(Json{{"event", "ready"},
              {"protocol", kProtocolVersion},
              {"version", std::string(versionString())},
              {"keywords", keywordList()}});

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
    if (command == "format") {
      format(request);
      return;
    }
    if (command == "step") {
      // A `step` is the answer to a paused step point, and the pause is the wait
      // inside `onStep`; reaching this line means nothing is paused.
      fail("protocol", "нет шага, который ждёт ответа");
      return;
    }
    if (command == "interrupt") {
      // The solver reads the stop flag at every step of its loop, so a query
      // that is *solving* — a runaway included — ends with `Interrupted`; a
      // paused step point answers the same request by ending the pause.  What
      // the request cannot reach is a front-end that never reads, and there the
      // process has to go.
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
    // A run can be asked for with the trace on, and one that is stepped through:
    // the program's own `?`-statements and directives run during the load, so the
    // step hook has to be armed around it, not only around `query`.
    engine_.setTrace(request.value("trace", false));
    const bool stepping = request.value("step", false);
    if (stepping) {
      armStepping();
    }
    reported_diagnostics_ = false;
    // A single query asked for from the editor's margin is loaded *quietly*: a
    // run loads the program *and* runs its own `?`-statements (that is what
    // `Запустить` must keep doing), but for one clicked query that would fill
    // the pane with the whole lesson before the answer asked for (task_36).
    const bool questions = request.value("questions", true);
    if (!questions) {
      loader_.setQueryRunner(nullptr);
    }
    bool ok = false;
    if (has_path) {
      ok = loader_.loadFile(fromUtf8Path(request.at("path").get<std::string>()), &error);
    } else {
      // The text the window sent: a program from an unnamed buffer, or one query
      // from the query line or a margin marker.  A query is named apart from the
      // buffer (`<query>`) so a front-end can tell «the error is in the one line
      // I sent» from «the error is in the buffer at line N»: both used to arrive
      // as `<buffer>:1:1`, and the window marked line 1 of the program and moved
      // the caret there for every failed query.
      const std::string name = request.value(
          "name", std::string(command == "query" ? "<query>" : "<buffer>"));
      ok = loader_.loadSource(request.at("text").get<std::string>(), name, &error);
    }
    if (!questions) {
      loader_.setQueryRunner([this](const Query& query) { runQuery(query); });
    }
    if (stepping) {
      disarmStepping();
    }
    if (!ok) {
      // The diagnostics of the parse went out one by one, with their positions;
      // the loader's message is only a summary, used when nothing was reported.
      if (!reported_diagnostics_ && !flushDiagnostics("parse")) {
        fail("parse", error);
      }
      exit_code_ = 2;
      return;
    }
    // The program's own `?`-statements and directives ran during the load, so
    // reaching this line means the whole run is over.  A front-end needs that
    // for a program *without* questions: `result` arrives per question, and a
    // run that asks none (an empty program included) would otherwise leave the
    // window saying «выполняется» forever.  A `query` request is one statement
    // and is answered by its own `result` — no event here.
    if (command == "load") {
      emit(Json{{"event", "loaded"}});
    }
  }

  void runQuery(const Query& query) {
    try {
      const bool found = engine_.runQuery(query);
      emit(Json{{"event", "result"}, {"found", found}});
    } catch (const PrologRuntimeError& runtime_error) {
      reportDiagnostic(runtime_error.error(), "runtime");
      exit_code_ = 3;
    }
  }

  /// The formatter, answerable between queries: it needs no engine, only the
  /// text, and the answer is the text — whitespace only, every other byte
  /// copied.  `selection` is what makes a fragment that breaks off in the
  /// middle of a body come back laid out up to its last complete goal.  A
  /// source that does not parse answers with `error` events (kind `format`) and
  /// leaves the exit code alone: the request failed, the session did not.
  void format(const Json& request) {
    if (!request.contains("text")) {
      fail("format", "format: нужен параметр text с исходником");
      return;
    }
    prologd::FormatOptions options;
    const std::string mode = request.value("mode", std::string("soft"));
    if (mode == "soft") {
      options.mode = FormatMode::Soft;
    } else if (mode == "hard") {
      options.mode = FormatMode::Hard;
    } else if (mode == "line") {
      options.mode = FormatMode::Line;
    } else {
      fail("format", "format: режим должен быть line, soft или hard, не " + mode);
      return;
    }
    options.width = request.value("width", std::size_t{80});
    options.indent_steps = request.value("indent", std::size_t{1});
    options.indent_unit = request.value("unit", std::string("tab")) == "spaces"
                              ? IndentUnit::Spaces
                              : IndentUnit::Tab;
    options.selection_only = request.value("selection", false);
    options.source_name = request.value("name", std::string("<format>"));
    const FormatResult formatted =
        formatSource(request.at("text").get<std::string>(), options);
    if (!formatted.ok()) {
      for (const PrologError& diagnostic : formatted.diagnostics) {
        reportDiagnostic(diagnostic, "format");
      }
      return;
    }
    // Warnings of a source that parses are dropped here: a formatter is not a
    // checker, and a front-end asking for layout does not want advice.
    emit(Json{{"event", "formatted"},
              {"text", formatted.text},
              {"changed", formatted.changed}});
  }

  /// One diagnostic as an `error` event: the message as the human wrote it, and
  /// the position in fields of its own.
  void reportDiagnostic(const PrologError& diagnostic, const std::string& kind) {
    Json event{{"event", "error"},
               {"kind", kind},
               {"severity", std::string(severityText(diagnostic.severity))},
               {"message", diagnostic.message}};
    addLocation(event, diagnostic.location);
    reported_diagnostics_ = true;
    emit(event);
  }

  // ---- stepping ---------------------------------------------------------

  /// Asks the solver for step points.  Called before a run that is to be
  /// stepped through, and removed by `disarmStepping` when it is over.
  void armStepping() {
    pause_at_step_ = true;
    over_depth_.reset();
    engine_.options().stepHook = [this](const StepInfo& info) { return onStep(info); };
  }

  /// Removes the hook *after* the run: clearing it from inside would destroy the
  /// function object that is being called.
  void disarmStepping() {
    engine_.options().stepHook = nullptr;
    pause_at_step_ = false;
    over_depth_.reset();
  }

  /// Runs inside the solver, at a step point.
  StepDecision onStep(const StepInfo& info) {
    if (!pause_at_step_) {
      return StepDecision::Continue;  // running on, but still counting frames
    }
    if (over_depth_.has_value() && info.depth > *over_depth_) {
      // «Шаг с обходом»: the points inside the goal being stepped over are not
      // stops, and they are not announced either.
      return StepDecision::Continue;
    }
    flush();  // the output so far, then the point itself
    Json event{{"event", "step"},
               {"action", stepActionName(info.action)},
               {"depth", info.depth}};
    if (info.goal != nullptr) {
      event["goal"] = engine_.format(*info.goal);
    }
    addLocation(event, info.location);
    over_depth_.reset();
    emit(event);

    // The pause: read requests until the front-end answers, the same re-entrant
    // loop `answerInputRequest` uses — the engine is inside a query, so nothing
    // else can be reading this stream.
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
      if (command == "step") {
        const std::string action = request.value("action", std::string("into"));
        if (action == "into") {
          return StepDecision::Continue;  // stop again at the next point
        }
        if (action == "over") {
          over_depth_ = info.depth;
          return StepDecision::Continue;
        }
        if (action == "continue") {
          pause_at_step_ = false;
          return StepDecision::Continue;
        }
        if (action == "stop") {
          pause_at_step_ = false;
          return StepDecision::Stop;
        }
        fail("protocol", "неизвестное действие шага: " + action);
        continue;
      }
      if (command == "interrupt" || command == "quit") {
        pause_at_step_ = false;
        return StepDecision::Stop;
      }
      fail("protocol", "ожидался ответ step, получено: " + command);
    }
    return StepDecision::Stop;  // the stream is over: nothing more will arrive
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

  /// True once a diagnostic was emitted for the current request, so the loader's
  /// summary is not printed on top of the diagnostics themselves.
  bool reported_diagnostics_ = false;
  /// The state of stepping: stop at the next point, and whether the points
  /// *inside* the goal being stepped over are stops.
  bool pause_at_step_ = false;
  std::optional<std::size_t> over_depth_;
};

}  // namespace

int runJsonSession(Engine& engine, ModuleLoader& loader, std::istream& in, std::ostream& out) {
  Session session(engine, loader, in, out);
  return session.run();
}

}  // namespace prologd::cli
