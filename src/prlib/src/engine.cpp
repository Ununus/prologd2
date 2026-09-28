#include "prlib/engine.hpp"

#include <iostream>
#include <utility>

#include "prlib/term_print.hpp"

namespace prologd {

// ---------------------------------------------------------------------------
// ArithValue
// ---------------------------------------------------------------------------

ArithValue ArithValue::ofInteger(BigInt value) {
  ArithValue result;
  result.integer = std::move(value);
  return result;
}

ArithValue ArithValue::ofFloat(double value) {
  ArithValue result;
  result.is_float = true;
  result.real = value;
  return result;
}

double ArithValue::asDouble() const { return is_float ? real : integer.toDouble(); }

BigInt ArithValue::asInteger() const {
  return is_float ? BigInt::fromDouble(real) : integer;
}

// ---------------------------------------------------------------------------
// Solver
// ---------------------------------------------------------------------------

namespace {

/// Persistent environment frame.  Pushing or advancing an environment creates
/// a new node that shares its parent chain, so a choice point can capture the
/// whole continuation in O(1) and restore it in O(1).
struct EnvNode {
  std::shared_ptr<const EnvNode> parent;  // null for the root environment
  std::shared_ptr<std::vector<Term>> goals;
  std::size_t index = 0;
  std::size_t cp_barrier = 0;
};

using EnvRef = std::shared_ptr<const EnvNode>;

EnvRef makeEnv(EnvRef parent, std::shared_ptr<std::vector<Term>> goals,
               std::size_t barrier) {
  auto node = std::make_shared<EnvNode>();
  node->parent = std::move(parent);
  node->goals = std::move(goals);
  node->cp_barrier = barrier;
  return node;
}

EnvRef advanceEnv(const EnvRef& env) {
  auto node = std::make_shared<EnvNode>(*env);
  node->index = env->index + 1;
  return node;
}

struct ChoicePoint {
  Database::ClauseListPtr clauses;
  std::size_t next = 0;
  std::size_t goal_index = 0;
  std::size_t trail_mark = 0;
  std::size_t barrier = 0;
  Term goal;
  EnvRef env;  // continuation captured when the choice point was created
};

bool isExpression(const Term& term) {
  return term.kind == TermKind::Compound && term.compound != nullptr &&
         term.compound->name == "$expr" && term.compound->args.size() == 1;
}

}  // namespace

/// Resolution machine over a persistent environment chain and a choice-point
/// stack.
class Solver {
 public:
  explicit Solver(Engine& engine) : engine_(engine) {}

  void run(std::span<const Term> goals, const std::function<bool()>& on_solution);

 private:
  bool resolveGoal(const Term& goal);
  bool selectClause(ChoicePoint& cp);
  bool backtrack();
  void applyCut();
  void pushMeta(const Term& goal, std::size_t barrier);
  void traceGoal(const Term& goal);
  void traceText(std::string_view text);

  Engine& engine_;
  EnvRef env_;
  std::vector<ChoicePoint> cps_;
  std::size_t steps_ = 0;
};

void Solver::traceText(std::string_view text) {
  if (engine_.traceEnabled()) {
    engine_.io().write(text);
    engine_.io().newline();
  }
}

void Solver::traceGoal(const Term& goal) {
  if (engine_.traceEnabled()) {
    engine_.io().write("Цель " + engine_.format(goal));
    engine_.io().newline();
  }
}

void Solver::applyCut() {
  if (cps_.size() > env_->cp_barrier) {
    cps_.resize(env_->cp_barrier);
  }
}

void Solver::pushMeta(const Term& goal, std::size_t barrier) {
  auto goals = std::make_shared<std::vector<Term>>();
  goals->push_back(goal);
  env_ = makeEnv(env_, std::move(goals), barrier);
}

bool Solver::selectClause(ChoicePoint& cp) {
  while (cp.next < cp.clauses->size()) {
    const Clause& clause = (*cp.clauses)[cp.next++];
    const std::size_t mark = engine_.bindings().trailMark();
    Term head;
    std::vector<Term> body;
    engine_.instantiateClause(clause, head, body);
    if (engine_.traceEnabled()) {
      traceText("Согласуется с " + engine_.format(head));
    }
    if (engine_.unify(head, cp.goal)) {
      if (engine_.traceEnabled()) {
        traceText("Успех");
      }
      env_ = advanceEnv(cp.env);
      env_ = makeEnv(env_, std::make_shared<std::vector<Term>>(std::move(body)), cp.barrier);
      return true;
    }
    if (engine_.traceEnabled()) {
      traceText("Неудача");
    }
    engine_.bindings().unwind(mark);
  }
  return false;
}

bool Solver::backtrack() {
  while (!cps_.empty()) {
    ChoicePoint cp = std::move(cps_.back());
    cps_.pop_back();
    engine_.bindings().unwind(cp.trail_mark);
    env_ = cp.env;
    if (engine_.traceEnabled()) {
      traceText("Переделка. Цель " + engine_.format(cp.goal));
    }
    if (selectClause(cp)) {
      if (cp.next < cp.clauses->size()) {
        cps_.push_back(std::move(cp));
      }
      return true;
    }
  }
  return false;
}

bool Solver::resolveGoal(const Term& goal) {
  std::string_view name;
  std::size_t arity = 0;
  if (goal.kind == TermKind::Atom) {
    name = goal.text;
    arity = 0;
  } else if (goal.kind == TermKind::Compound && goal.compound != nullptr) {
    name = goal.compound->name;
    arity = goal.compound->args.size();
  } else {
    engine_.raise(ErrorCode::InvalidSentence, "Цель должна быть предикатом");
  }

  if (name == "!" && arity == 0) {
    applyCut();
    env_ = advanceEnv(env_);
    return true;
  }
  if (name == "," && arity == 2) {
    // A parenthesised conjunction used as a single goal: expand in place.
    std::vector<Term>& goals = *env_->goals;
    const std::size_t index = env_->index;
    goals[index] = goal.compound->args[0];
    goals.insert(goals.begin() + static_cast<std::ptrdiff_t>(index) + 1,
                 goal.compound->args[1]);
    return true;
  }
  if (name == "ВЫП" && arity == 1) {
    // Meta-call: solve the argument in the caller's cut scope.
    const std::size_t barrier = env_->cp_barrier;
    env_ = advanceEnv(env_);
    pushMeta(goal.compound->args[0], barrier);
    return true;
  }

  if (BuiltinFn builtin = findBuiltin(name, arity)) {
    std::span<const Term> args;
    if (goal.kind == TermKind::Compound) {
      args = std::span<const Term>(goal.compound->args.data(), goal.compound->args.size());
    }
    const BuiltinResult result = builtin(engine_, args);
    switch (result) {
      case BuiltinResult::Continue:
        env_ = advanceEnv(env_);
        return true;
      case BuiltinResult::Fail:
        return false;
      case BuiltinResult::Handled:
        return true;
    }
    return true;
  }

  traceGoal(goal);

  Database::ClauseListPtr clauses = engine_.database().clausesFor(name, arity);
  if (!clauses || clauses->empty()) {
    return false;  // unknown predicate fails, like the original
  }
  ChoicePoint cp;
  cp.clauses = std::move(clauses);
  cp.next = 0;
  cp.goal_index = env_->index;
  cp.trail_mark = engine_.bindings().trailMark();
  cp.barrier = cps_.size();
  cp.goal = goal;
  cp.env = env_;
  if (!selectClause(cp)) {
    return false;
  }
  if (cp.next < cp.clauses->size()) {
    cps_.push_back(std::move(cp));
  }
  return true;
}

void Solver::run(std::span<const Term> goals, const std::function<bool()>& on_solution) {
  cps_.clear();
  steps_ = 0;
  env_ = makeEnv(nullptr,
                 std::make_shared<std::vector<Term>>(goals.begin(), goals.end()), 0);

  for (;;) {
    if (engine_.shouldStop()) {
      engine_.raise(ErrorCode::Interrupted);
    }
    if (engine_.options().maxSteps != 0 && ++steps_ > engine_.options().maxSteps) {
      engine_.raise(ErrorCode::Interrupted, "Превышен лимит шагов выполнения");
    }
    if (env_->index >= env_->goals->size()) {
      if (env_->parent == nullptr) {
        // All query goals are satisfied: report the solution.
        if (on_solution && !on_solution()) {
          return;
        }
        if (!backtrack()) {
          return;
        }
      } else {
        env_ = env_->parent;
      }
      continue;
    }
    const Term goal = engine_.deref((*env_->goals)[env_->index]);
    if (!resolveGoal(goal)) {
      if (!backtrack()) {
        return;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------

Engine::Engine()
    : io_(std::make_unique<IoContext>(std::cin, std::cout, std::cerr)),
      graphics_(std::make_shared<NullGraphicsBackend>()) {}

Engine::~Engine() = default;

void Engine::setStreams(std::istream& input, std::ostream& output, std::ostream& error) {
  io_ = std::make_unique<IoContext>(input, output, error);
}

void Engine::setGraphicsBackend(std::shared_ptr<GraphicsBackend> backend) {
  if (backend) {
    graphics_ = std::move(backend);
  }
}

VarId Engine::allocateVar(std::string_view name) { return bindings_.freshVar(name); }

Term Engine::instantiateImpl(const Term& templ, std::unordered_map<VarId, VarId>& mapping) {
  const Term resolved = bindings_.deref(templ);
  switch (resolved.kind) {
    case TermKind::Var: {
      const auto it = mapping.find(resolved.var);
      if (it != mapping.end()) {
        return makeVar(it->second, bindings_.varName(it->second));
      }
      const VarId fresh = bindings_.freshVar(resolved.text);
      mapping.emplace(resolved.var, fresh);
      return makeVar(fresh, resolved.text);
    }
    case TermKind::Compound: {
      if (resolved.compound == nullptr) {
        return resolved;
      }
      std::vector<Term> args;
      args.reserve(resolved.compound->args.size());
      for (const Term& arg : resolved.compound->args) {
        args.push_back(instantiateImpl(arg, mapping));
      }
      return makeCompound(resolved.compound->name, std::move(args));
    }
    default:
      return resolved;
  }
}

Term Engine::instantiate(const Term& templ) {
  std::unordered_map<VarId, VarId> mapping;
  return instantiateImpl(templ, mapping);
}

void Engine::instantiateClause(const Clause& clause, Term& head, std::vector<Term>& body) {
  std::unordered_map<VarId, VarId> mapping;
  head = instantiateImpl(clause.head, mapping);
  body.clear();
  body.reserve(clause.body.size());
  for (const Term& goal : clause.body) {
    body.push_back(instantiateImpl(goal, mapping));
  }
}

Term Engine::copyTermResolvedImpl(const Term& term, std::unordered_map<VarId, VarId>& mapping) {
  const Term resolved = bindings_.deref(term);
  switch (resolved.kind) {
    case TermKind::Var: {
      const auto it = mapping.find(resolved.var);
      if (it != mapping.end()) {
        return makeVar(it->second);
      }
      const VarId fresh = bindings_.freshVar(resolved.text);
      mapping.emplace(resolved.var, fresh);
      return makeVar(fresh);
    }
    case TermKind::Compound: {
      if (resolved.compound == nullptr) {
        return resolved;
      }
      std::vector<Term> args;
      args.reserve(resolved.compound->args.size());
      for (const Term& arg : resolved.compound->args) {
        args.push_back(copyTermResolvedImpl(arg, mapping));
      }
      return makeCompound(resolved.compound->name, std::move(args));
    }
    default:
      return resolved;
  }
}

Term Engine::copyTermResolved(const Term& term) {
  std::unordered_map<VarId, VarId> mapping;
  return copyTermResolvedImpl(term, mapping);
}

bool Engine::unify(const Term& first, const Term& second) {
  std::vector<std::pair<Term, Term>> work;
  work.emplace_back(first, second);
  while (!work.empty()) {
    auto [left, right] = std::move(work.back());
    work.pop_back();
    left = bindings_.deref(left);
    right = bindings_.deref(right);

    if (left.kind == TermKind::Var || right.kind == TermKind::Var) {
      const bool left_is_var = left.kind == TermKind::Var;
      const Term var_term = left_is_var ? left : right;
      Term other = left_is_var ? right : left;
      // The original PrologD evaluates an arithmetic expression when it is
      // bound to a variable, so bindings never accumulate expression trees.
      if (isExpression(other)) {
        other = evaluateToTerm(other);
      }
      if (var_term.kind != TermKind::Var) {
        return false;
      }
      if (other.kind == TermKind::Var && other.var == var_term.var) {
        continue;
      }
      bindings_.bind(var_term.var, other);
      continue;
    }

    if (isExpression(left) && isExpression(right)) {
      work.emplace_back(evaluateToTerm(left), evaluateToTerm(right));
      continue;
    }
    if (isExpression(left)) {
      work.emplace_back(evaluateToTerm(left), right);
      continue;
    }
    if (isExpression(right)) {
      work.emplace_back(left, evaluateToTerm(right));
      continue;
    }

    if (left.kind == TermKind::Int && right.kind == TermKind::Float) {
      const double real = right.real;
      if (!(real - 1 < left.integer.toDouble())) {
        return false;
      }
      if (real != static_cast<double>(static_cast<float>(left.integer.toDouble()))) {
        return false;
      }
      continue;
    }
    if (left.kind == TermKind::Float && right.kind == TermKind::Int) {
      const double real = left.real;
      if (!(real - 1 < right.integer.toDouble())) {
        return false;
      }
      if (real != static_cast<double>(static_cast<float>(right.integer.toDouble()))) {
        return false;
      }
      continue;
    }

    if (left.kind != right.kind) {
      // Atoms and strings are interchangeable in PrologD.
      const bool leftTextual = left.kind == TermKind::Atom || left.kind == TermKind::String;
      const bool rightTextual = right.kind == TermKind::Atom || right.kind == TermKind::String;
      if (!(leftTextual && rightTextual)) {
        return false;
      }
      if (left.text != right.text) {
        return false;
      }
      continue;
    }
    switch (left.kind) {
      case TermKind::Atom:
      case TermKind::String:
        if (left.text != right.text) {
          return false;
        }
        break;
      case TermKind::Int:
        if (!(left.integer == right.integer)) {
          return false;
        }
        break;
      case TermKind::Float:
        if (left.real != right.real) {
          return false;
        }
        break;
      case TermKind::Compound: {
        if (left.compound == right.compound) {
          break;
        }
        if (left.compound == nullptr || right.compound == nullptr) {
          return false;
        }
        if (left.compound->name != right.compound->name ||
            left.compound->args.size() != right.compound->args.size()) {
          return false;
        }
        for (std::size_t i = 0; i < left.compound->args.size(); ++i) {
          work.emplace_back(left.compound->args[i], right.compound->args[i]);
        }
        break;
      }
      case TermKind::Var:
        break;
    }
  }
  return true;
}

bool Engine::hasSolution(const Term& goal) {
  const std::size_t mark = bindings_.trailMark();
  bool found = false;
  Solver nested(*this);
  const Term single = goal;
  if (++nested_depth_ > options_.maxNestedDepth) {
    --nested_depth_;
    bindings_.unwind(mark);
    raise(ErrorCode::StackOverflow);
  }
  nested.run(std::span<const Term>(&single, 1), [&found]() {
    found = true;
    return false;
  });
  --nested_depth_;
  bindings_.unwind(mark);
  return found;
}

bool Engine::callOnce(const Term& goal) {
  const std::size_t mark = bindings_.trailMark();
  bool found = false;
  Solver nested(*this);
  const Term single = goal;
  if (++nested_depth_ > options_.maxNestedDepth) {
    --nested_depth_;
    bindings_.unwind(mark);
    raise(ErrorCode::StackOverflow);
  }
  nested.run(std::span<const Term>(&single, 1), [&found]() {
    found = true;
    return false;
  });
  --nested_depth_;
  if (!found) {
    bindings_.unwind(mark);
  }
  return found;
}

void Engine::copyClauseResolved(const Term& head, const std::vector<Term>& body,
                                Term& out_head, std::vector<Term>& out_body) {
  std::unordered_map<VarId, VarId> mapping;
  out_head = copyTermResolvedImpl(head, mapping);
  out_body.clear();
  out_body.reserve(body.size());
  for (const Term& goal : body) {
    out_body.push_back(copyTermResolvedImpl(goal, mapping));
  }
}

std::vector<Term> Engine::collectAll(const Term& goal, const Term& templ,
                                     std::size_t limit) {
  const std::size_t mark = bindings_.trailMark();
  std::vector<Term> collected;
  bool exceeded = false;
  Solver nested(*this);
  const Term single = goal;
  if (++nested_depth_ > options_.maxNestedDepth) {
    --nested_depth_;
    bindings_.unwind(mark);
    raise(ErrorCode::StackOverflow);
  }
  nested.run(std::span<const Term>(&single, 1), [&]() {
    if (collected.size() >= limit) {
      exceeded = true;
      return false;
    }
    collected.push_back(copyTermResolved(templ));
    return true;
  });
  --nested_depth_;
  bindings_.unwind(mark);
  if (exceeded) {
    raise(ErrorCode::TooManySolutions);
  }
  return collected;
}

void Engine::raise(ErrorCode code, std::string message) {
  PrologError error;
  error.code = code;
  error.message = message.empty() ? std::string(errorCodeText(code)) : std::move(message);
  throw PrologRuntimeError(std::move(error));
}

void Engine::raiseAt(ErrorCode code, const SourceLocation& location, std::string message) {
  PrologError error;
  error.code = code;
  error.location = location;
  error.message = message.empty() ? std::string(errorCodeText(code)) : std::move(message);
  throw PrologRuntimeError(std::move(error));
}

ParsedProgram Engine::parseSource(std::string_view source, const std::string& file_name) {
  DiagnosticSink sink;
  Lexer lexer(source, file_name);
  std::vector<Token> tokens = lexer.tokenize(sink);
  auto allocator = [this](std::string_view name) { return allocateVar(name); };
  Parser parser(std::move(tokens), allocator, &sink);
  ParsedProgram program = parser.parseProgram();
  for (const PrologError& diagnostic : sink.diagnostics()) {
    if (diagnostic.code == ErrorCode::NoErrors) {
      continue;
    }
    io_->errorStream() << DiagnosticSink::format(diagnostic) << '\n';
  }
  if (sink.hasErrors()) {
    program.ok = false;
  }
  return program;
}

void Engine::loadProgram(const ParsedProgram& program) {
  for (const Clause& clause : program.clauses) {
    database_.addClause(clause);
  }
}

std::string Engine::format(const Term& term) const {
  PrintOptions options;
  options.evaluate = [this](const Term& expression) {
    return const_cast<Engine*>(this)->evaluateToTerm(expression);
  };
  return formatTerm(term, bindings_, options);
}

bool Engine::runQuery(const Query& query, const std::function<bool()>& onSolution) {
  quiet_ = false;
  stop_requested_ = false;
  if (query.isDirective) {
    bool found = false;
    Solver solver(*this);
    solver.run(query.goals, [&found]() {
      found = true;
      return false;
    });
    return found;
  }
  const bool has_variables = !query.variables.empty();
  bool found = false;
  bool user_stopped = false;

  Solver solver(*this);
  solver.run(query.goals, [&]() {
    found = true;
    if (onSolution && !onSolution()) {
      user_stopped = true;
      return false;
    }
    if (quiet_) {
      return !has_variables;  // a ground query stops after the first solution
    }
    if (!has_variables) {
      if (!io_->atLineStart()) {
        io_->newline();
      }
      io_->write("ДА");
      io_->newline();
      return false;  // ground queries report "ДА" once
    }
    for (const auto& [name, var] : query.variables) {
      const Term value = bindings_.deref(makeVar(var, name));
      io_->write(name + "=" + format(value));
      io_->newline();
    }
    return true;
  });

  if (!quiet_ && !found) {
    if (!io_->atLineStart()) {
      io_->newline();
    }
    io_->write("НЕТ");
    io_->newline();
  }
  (void)user_stopped;
  return found;
}

void Engine::initialize() {
  static constexpr std::string_view kLibrary = R"PLD(
НЕ(X) :- ВЫП(X), !, ЛОЖЬ.
НЕ(_).
ИЛИ(X, _) :- ВЫП(X), !.
ИЛИ(_, X) :- ВЫП(X).
РАВНО(X, X).
МЕНЬШЕ(X, Y) :- БОЛЬШЕ(Y, X).
СЛОЖЕНИЕ(X, Y, Z) :- УМНОЖЕНИЕ(1, X, Y, Z).
ПС :- ВВКОД(10).
ДЛИНА(X, Y) :- КОПИЯ(X, 1, Y, X).
)PLD";
  ParsedProgram library = parseSource(kLibrary, "<library>");
  loadProgram(library);
}

}  // namespace prologd
