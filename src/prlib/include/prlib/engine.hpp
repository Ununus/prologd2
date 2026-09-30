#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "prlib/bindings.hpp"
#include "prlib/diagnostics.hpp"
#include "prlib/graphics.hpp"
#include "prlib/io.hpp"
#include "prlib/parser.hpp"
#include "prlib/program.hpp"
#include "prlib/term.hpp"

namespace prologd {

/// Numeric value produced by arithmetic evaluation.
struct ArithValue {
  bool is_float = false;
  BigInt integer;
  double real = 0.0;

  static ArithValue ofInteger(BigInt value);
  static ArithValue ofFloat(double value);

  [[nodiscard]] double asDouble() const;
  [[nodiscard]] BigInt asInteger() const;  // truncates toward zero
};

/// What the solver was doing when a step hook was called.  The four points are
/// the four the textual trace already has: a goal is entered, it succeeds, the
/// solver goes back into it, or it fails.
enum class StepAction {
  Call,  ///< a user predicate is about to be solved
  Exit,  ///< it succeeded: its body is satisfied
  Redo,  ///< the solver is back in it, looking for another solution
  Fail,  ///< it has no clause that matches, so it fails
};

/// One point of the trace in *structured* form: the text of `ТРАССА` is for
/// humans and changes with the version, while this is what a front-end steps
/// through and shows.
struct StepInfo {
  StepAction action = StepAction::Call;
  /// The goal of the moment; the hook applies the current bindings with
  /// `Engine::format` when it needs the text.
  const Term* goal = nullptr;
  /// Nesting of the goal: 0 for the goals of the query itself, deeper inside a
  /// body.
  std::size_t depth = 0;
  /// Where that goal stands in the source, empty when it is not from a file.
  SourceLocation location;
};

/// What the step hook decided.
///
/// There is no separate "pause": a hook that wants the user to look at the
/// point it was given simply *waits* — reading the next command from the
/// front-end — and then answers with one of these.  The solver has no
/// continuation to suspend, and the request loop a front-end already has for
/// `input_request` is exactly that wait, so blocking is the pause.
enum class StepDecision {
  Continue,  ///< solve on; the hook is asked again at the next point
  Stop,      ///< end the query: the engine raises `Interrupted`
};

struct EngineOptions {
  bool trace = false;
  std::size_t maxNestedDepth = 10'000;
  std::size_t maxFindAllSolutions = 1'000'000;
  std::size_t maxSteps = 0;  // 0 = unlimited
  /// How deep a clause body may nest before the solver refuses to go on.
  ///
  /// The solver itself is a loop — logical depth costs heap, not the C++ stack —
  /// but a frame chain is still *released* through shared_ptr destructors, and
  /// a chain of tens of thousands of frames coming down in one go is a real
  /// stack overflow (measured at ~16 000-32 000 on Windows, where a correct
  /// program printed its answer and then died with 0xC00000FD).  The chain is
  /// released iteratively now, so this limit is a *guard against runaway
  /// programs*, not a workaround: a lesson needs hundreds of levels, and a
  /// search that needs more asks for it with `--max-depth 0`.
  std::size_t maxDepth = 10'000;

  /// Extra stop condition, polled by the solver next to the internal flag.
  /// A front-end uses it to turn the Ctrl+C signal flag or a GUI "Stop" button
  /// into a stop request: a signal handler may only touch async-signal-safe
  /// state, and this hook is the bridge.  Must not throw.
  std::function<bool()> externalStop;

  /// Called by the solver at every step point while it is installed, which is
  /// what `Не выполнять с шагом` costs: one call.  A front-end that steps
  /// installs it when the user asks for a step and removes it when they run on.
  /// The hook runs inside the solver's own loop on the calling thread — it is
  /// *not* a signal handler and may block (that is how a step waits for the
  /// next command) — and it must not throw.
  std::function<StepDecision(const StepInfo&)> stepHook;
};

class Engine;
class Solver;

/// Outcome of a deterministic built-in.
enum class BuiltinResult {
  Continue,  ///< succeeded, advance to the next goal
  Fail,      ///< failed, backtrack
  Handled,   ///< the built-in already advanced the machine state
};

using BuiltinFn = BuiltinResult (*)(Engine&, std::span<const Term>);

/// Look up a built-in by name and arity; nullptr when none.
BuiltinFn findBuiltin(std::string_view name, std::size_t arity);

/// Arity information for a registered built-in.  Both fields are empty/false
/// when the name is not in the dispatch table.  `ВЫВОД` accepts any positive
/// arity, so it reports `variadic` instead of enumerating arities.
struct BuiltinArities {
  std::vector<std::size_t> arities;  ///< sorted ascending
  bool variadic = false;
};

BuiltinArities builtinArities(std::string_view name);

/// Every name the dispatch table can call, plus the variadic `ВЫВОД`, sorted and
/// unique.  Used to keep the reserved-name table and the dispatcher in step
/// (`prlib/keywords.hpp`).
std::vector<std::string> builtinNames();

/// The interpreter: term store, clause database, streams and resolution.
class Engine {
 public:
  Engine();
  ~Engine();

  Engine(const Engine&) = delete;
  Engine& operator=(const Engine&) = delete;

  // ---- state accessors ----
  Database& database() noexcept { return database_; }
  Bindings& bindings() noexcept { return bindings_; }
  IoContext& io() noexcept { return *io_; }
  void setStreams(std::istream& input, std::ostream& output, std::ostream& error);
  GraphicsBackend& graphics() noexcept { return *graphics_; }
  void setGraphicsBackend(std::shared_ptr<GraphicsBackend> backend);
  EngineOptions& options() noexcept { return options_; }
  [[nodiscard]] const EngineOptions& options() const noexcept { return options_; }

  [[nodiscard]] bool traceEnabled() const noexcept { return options_.trace; }
  void setTrace(bool value) noexcept { options_.trace = value; }
  [[nodiscard]] bool quiet() const noexcept { return quiet_; }
  void setQuiet(bool value) noexcept { quiet_ = value; }

  /// Every diagnostic the engine reports, with its location and category, so a
  /// front-end can build a structured message instead of reading the text of
  /// the error stream.  A set hook *replaces* that text for diagnostics — one
  /// of the two gets them, never both.  Null by default: the console reads the
  /// usual `file:line:column: error: ...` lines.
  void setDiagnosticHook(std::function<void(const PrologError&)> hook) {
    diagnostic_hook_ = std::move(hook);
  }

  /// The clause being solved right now, for a runtime error to point at.  The
  /// solver keeps it in step with its environment and saves it around a nested
  /// query, so `raise` can fill in a location the caller did not have; empty
  /// before the first goal or after the query.
  [[nodiscard]] const SourceLocation& currentLocation() const noexcept {
    return current_location_;
  }
  void setCurrentLocation(SourceLocation location) noexcept {
    current_location_ = std::move(location);
  }

  // ---- variables and terms ----
  VarId allocateVar(std::string_view name = {});
  /// Rename every variable in `templ` to a fresh variable.
  Term instantiate(const Term& templ);
  /// Rename head and body with one shared variable mapping.
  void instantiateClause(const Clause& clause, Term& head, std::vector<Term>& body);
  /// Apply current bindings and replace remaining variables by fresh ones.
  Term copyTermResolved(const Term& term);

  // ---- unification ----
  bool unify(const Term& first, const Term& second);
  [[nodiscard]] Term deref(const Term& term) const { return bindings_.deref(term); }

  // ---- arithmetic ----
  ArithValue evaluateArithmetic(const Term& wrapper);
  Term evaluateToTerm(const Term& wrapper);

  // ---- nested solving ----
  bool hasSolution(const Term& goal);
  /// Solve `goal` once and keep the bindings of the first solution on success
  /// (undoing them on failure).  Used by `ИЛИ`.
  bool callOnce(const Term& goal);
  std::vector<Term> collectAll(const Term& goal, const Term& templ,
                               std::size_t limit);
  /// Copy a head and body with one shared variable mapping (for `ДОБ`).
  void copyClauseResolved(const Term& head, const std::vector<Term>& body, Term& out_head,
                          std::vector<Term>& out_body);

  // ---- errors ----
  [[noreturn]] void raise(ErrorCode code, std::string message = {});
  [[noreturn]] void raiseAt(ErrorCode code, const SourceLocation& location,
                            std::string message = {});

  // ---- parsing and loading ----
  ParsedProgram parseSource(std::string_view source, const std::string& file_name);
  void loadProgram(const ParsedProgram& program);
  void initialize();

  /// Run a query; `onSolution` is called for every solution and may return
  /// false to stop.  Returns true when at least one solution was found.
  bool runQuery(const Query& query, const std::function<bool()>& onSolution = {});

  [[nodiscard]] bool shouldStop() const noexcept {
    return stop_requested_ ||
           (options_.externalStop && options_.externalStop());
  }
  void requestStop() noexcept { stop_requested_ = true; }

  /// Format a term using the current bindings and arithmetic evaluation.
  [[nodiscard]] std::string format(const Term& term) const;

  friend class Solver;

 private:
  /// One diagnostic: to the front-end when it asked for them, else to the
  /// error stream in the usual `file:line:column: error: ...` form.
  void report(const PrologError& diagnostic);

  Database database_;
  Bindings bindings_;
  std::unique_ptr<IoContext> io_;
  std::shared_ptr<GraphicsBackend> graphics_;
  EngineOptions options_;
  std::function<void(const PrologError&)> diagnostic_hook_;
  SourceLocation current_location_;
  bool quiet_ = false;
  bool stop_requested_ = false;
  std::size_t nested_depth_ = 0;

  Term instantiateImpl(const Term& templ, std::unordered_map<VarId, VarId>& mapping);
  /// `path` collects the compound nodes on the way to the term being copied;
  /// a node that appears twice is a cycle and is reported rather than followed.
  Term copyTermResolvedImpl(const Term& term, std::unordered_map<VarId, VarId>& mapping,
                            std::vector<const CompoundTerm*>& path);
};

}  // namespace prologd
