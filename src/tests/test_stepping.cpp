#include <catch2/catch_test_macros.hpp>

#include <cstddef>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/diagnostics.hpp"
#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"
#include "test_helpers.hpp"

using namespace prologd;
using prologd::test::runProgram;

namespace {

/// A small program with two clauses, one nested goal and one failure: enough for
/// the four points (call, exit, redo, fail) to show up in a short list.
constexpr std::string_view kProgram =
    "факт(1).\n"
    "факт(2).\n"
    "счёт(X) :- факт(X).\n"
    "?счёт(X).\n";

[[nodiscard]] std::string_view actionName(StepAction action) {
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
  return "?";
}

/// One recorded point, as a line of text: the goal is formatted with the
/// bindings of the moment, exactly as the protocol does it.
[[nodiscard]] std::string describe(Engine& engine, const StepInfo& info) {
  std::string text(actionName(info.action));
  text += " ";
  text += info.goal != nullptr ? engine.format(*info.goal) : std::string("-");
  text += " @" + std::to_string(info.depth);
  if (!info.location.file.empty()) {
    text += " " + info.location.toString();
  }
  return text;
}

}  // namespace

TEST_CASE("the step hook sees the four points of a run") {
  std::vector<std::string> points;
  const test::RunResult result = runProgram(std::string(kProgram), {}, nullptr,
                                            [&points](Engine& engine) {
                                              engine.options().stepHook =
                                                  [&points, &engine](const StepInfo& info) {
                                                    points.push_back(describe(engine, info));
                                                    return StepDecision::Continue;
                                                  };
                                            });

  REQUIRE(result.loaded);
  REQUIRE(points.size() >= 6);
  // The query's own goal is entered first, at depth 0 and with the position of
  // the `?` statement; the goal inside the body is one deeper, and its position
  // is the clause that calls it.
  CHECK(points[0] == "call счёт(_1) @0 <test>:4:1");
  CHECK(points[1] == "call факт(_1) @1 <test>:3:1");
  CHECK(points[2] == "exit - @1 <test>:1:1");
  CHECK(points[3] == "exit - @0 <test>:3:1");
  // Backtracking into `факт` gives the second solution, and the run ends.
  CHECK(points[4] == "redo факт(_1) @1 <test>:3:1");
  CHECK(points[5] == "exit - @1 <test>:2:1");
  CHECK(result.output.find("X=1") != std::string::npos);
}

TEST_CASE("a goal with no matching clause reports a failure") {
  std::vector<std::string> points;
  const test::RunResult result =
      runProgram("известно(1).\n?неизвестно(1).\n", {}, nullptr, [&points](Engine& engine) {
        engine.options().stepHook = [&points, &engine](const StepInfo& info) {
          points.push_back(describe(engine, info));
          return StepDecision::Continue;
        };
      });

  REQUIRE(result.loaded);
  REQUIRE(points.size() == 2);
  CHECK(points[0] == "call неизвестно(1) @0 <test>:2:1");
  CHECK(points[1] == "fail неизвестно(1) @0 <test>:2:1");
}

TEST_CASE("a meta-call with extra arguments steps into the expanded goal") {
  std::vector<std::string> points;
  const test::RunResult result =
      runProgram("цель(5).\n?ВЫП(цель, X).\n", {}, nullptr, [&points](Engine& engine) {
        engine.options().stepHook = [&points, &engine](const StepInfo& info) {
          points.push_back(describe(engine, info));
          return StepDecision::Continue;
        };
      });

  REQUIRE(result.loaded);
  REQUIRE_FALSE(points.empty());
  // `ВЫП` не попадает в шаги: сработавшая цель — развёрнутая `цель(_1)`, в
  // среде мета-вызова (поэтому на шаг глубже, чем цель запроса).
  CHECK(points[0] == "call цель(_1) @1 <test>:2:1");
  for (const std::string& point : points) {
    REQUIRE(point.find("ВЫП") == std::string::npos);
  }
}

TEST_CASE("the hook can stop a query at the n-th point") {
  std::size_t seen = 0;
  const test::RunResult result =
      runProgram(std::string(kProgram), {}, nullptr, [&seen](Engine& engine) {
        engine.options().stepHook = [&seen](const StepInfo&) {
          return ++seen >= 3 ? StepDecision::Stop : StepDecision::Continue;
        };
      });

  // The same outcome as an interrupt: the query ends with a runtime error, and
  // the front-end shows it the way it shows a runaway stop.
  REQUIRE(result.runtimeError);
  CHECK(seen == 3);
  CHECK(result.error.find("выполнение прервано") != std::string::npos);
}

TEST_CASE("the hook is asked nothing when it is not installed") {
  // The cost of the seam: with no hook, a run behaves exactly as before.
  const test::RunResult result = runProgram(std::string(kProgram));
  REQUIRE(result.loaded);
  CHECK(result.output.find("X=1\nX=2\n") != std::string::npos);
  CHECK_FALSE(result.runtimeError);
}

TEST_CASE("a runtime error names the clause it happened in") {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream errors;
  Engine engine;
  engine.setStreams(input, output, errors);
  engine.initialize();
  ModuleLoader loader(engine);
  loader.setQueryRunner([&engine](const Query& query) { engine.runQuery(query); });

  // `БОЛЬШЕ` evaluates both arguments, so the division happens inside `дели`,
  // and that clause is what the diagnostic has to point at — a query typed at
  // the prompt has no position of its own to report.
  std::string error;
  try {
    const bool loaded = loader.loadSource("дели(Х) :- БОЛЬШЕ(1, #1/0#).\n?дели(1).\n", "boom.pld", &error);
    CHECK(loaded);
    FAIL("the division by zero did not raise");
  } catch (const PrologRuntimeError& failure) {
    CHECK(failure.error().code == ErrorCode::DivisionByZero);
    CHECK(failure.error().location.file == "boom.pld");
    CHECK(failure.error().location.line == 1);
  }
}

TEST_CASE("a parse error keeps its position in structured form") {
  std::vector<PrologError> seen;
  const test::RunResult result =
      runProgram("факт(1\n", {}, nullptr, [&seen](Engine& engine) {
        engine.setDiagnosticHook([&seen](const PrologError& diagnostic) { seen.push_back(diagnostic); });
      });

  CHECK_FALSE(result.loaded);
  REQUIRE_FALSE(seen.empty());
  // The file the diagnostic came from, and a line to mark in an editor — the
  // whole point of the hook.
  CHECK(seen.front().location.file == "<test>");
  CHECK(seen.front().location.line >= 1);
  CHECK_FALSE(seen.front().message.empty());
  // A front-end that took the diagnostics does not need them spelled out on the
  // error stream as well: one of the two gets them, never both.
  const std::string formatted = DiagnosticSink::format(seen.front());
  CHECK(result.error.find(formatted) == std::string::npos);
}

TEST_CASE("the trace goes to the sink when a front-end asks for it") {
  std::vector<std::string> traced;
  const test::RunResult result =
      runProgram(std::string(kProgram), {}, nullptr, [&traced](Engine& engine) {
        engine.io().setTraceSink([&traced](std::string_view line) { traced.emplace_back(line); });
        engine.setTrace(true);
      });

  REQUIRE(result.loaded);
  REQUIRE_FALSE(traced.empty());
  bool follows_clause = false;
  for (const std::string& line : traced) {
    follows_clause = follows_clause || line.find("Согласуется с") != std::string::npos;
  }
  CHECK(follows_clause);
  // …and it did not also land in the program's own output, which is where the
  // console front-end reads it.
  CHECK(result.output.find("Согласуется") == std::string::npos);
}
