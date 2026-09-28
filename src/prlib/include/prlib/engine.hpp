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

struct EngineOptions {
  bool trace = false;
  std::size_t maxNestedDepth = 10'000;
  std::size_t maxFindAllSolutions = 1'000'000;
  std::size_t maxSteps = 0;  // 0 = unlimited

  /// Extra stop condition, polled by the solver next to the internal flag.
  /// A front-end uses it to turn the Ctrl+C signal flag or a GUI "Stop" button
  /// into a stop request: a signal handler may only touch async-signal-safe
  /// state, and this hook is the bridge.  Must not throw.
  std::function<bool()> externalStop;
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
  Database database_;
  Bindings bindings_;
  std::unique_ptr<IoContext> io_;
  std::shared_ptr<GraphicsBackend> graphics_;
  EngineOptions options_;
  bool quiet_ = false;
  bool stop_requested_ = false;
  std::size_t nested_depth_ = 0;

  Term instantiateImpl(const Term& templ, std::unordered_map<VarId, VarId>& mapping);
  Term copyTermResolvedImpl(const Term& term, std::unordered_map<VarId, VarId>& mapping);
};

}  // namespace prologd
