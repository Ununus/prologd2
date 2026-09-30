#include "prlib/engine.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <utility>

#include "prlib/checks.hpp"
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
///
/// The frame also carries what a *step* needs: how deep it is, the clause it is
/// solving (a runtime error points there), and whether it is the body of a
/// clause — only those frames are entered and left as a goal, the frames of a
/// conjunction or of `ВЫП` are not.
struct EnvNode {
  std::shared_ptr<const EnvNode> parent;  // null for the root environment
  std::shared_ptr<std::vector<Term>> goals;
  std::size_t index = 0;
  std::size_t cp_barrier = 0;
  std::size_t depth = 0;
  SourceLocation location;
  bool goalFrame = false;
};

using EnvRef = std::shared_ptr<const EnvNode>;

/// A frame of goals.  `location` is set for a clause body and inherited
/// otherwise; the depth counts the chain and no term is copied.
EnvRef makeEnv(EnvRef parent, std::shared_ptr<std::vector<Term>> goals, std::size_t barrier,
               const SourceLocation* location = nullptr, bool goal_frame = false) {
  auto node = std::make_shared<EnvNode>();
  node->parent = std::move(parent);
  node->goals = std::move(goals);
  node->cp_barrier = barrier;
  node->depth = node->parent ? node->parent->depth + 1 : 0;
  node->goalFrame = goal_frame;
  if (location != nullptr) {
    node->location = *location;
  } else if (node->parent) {
    node->location = node->parent->location;
  }
  return node;
}

EnvRef advanceEnv(const EnvRef& env) {
  auto node = std::make_shared<EnvNode>(*env);
  node->index = env->index + 1;
  return node;
}

struct ChoicePoint {
  /// What the alternative is: the next clause of a predicate, or the right
  /// operand of a disjunction (where `clauses` is unused).
  enum class Kind { Clause, Alternative };
  Kind kind = Kind::Clause;
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

/// Releases a chain of environments without recursing through it.
///
/// A frame owns its parent, so letting the *last* reference to a deep frame go
/// destroys the whole chain inside the destructors — one C++ stack frame per
/// level, which is a real stack overflow at tens of thousands of levels
/// (measured: a correct program printed its answer and then died with
/// 0xC00000FD).  Here each level is unlinked from its parent before it dies, and
/// the parent is kept alive by the worklist until its own turn comes.
///
/// The `const_cast` is safe for the same reason as in `CompoundDeleter`: the
/// frame is about to be destroyed and nobody else can observe the cleared link.
void releaseEnvChain(EnvRef& node) noexcept {
  if (!node) {
    return;
  }
  std::vector<EnvRef> pending;
  pending.push_back(std::move(node));
  while (!pending.empty()) {
    EnvRef level = std::move(pending.back());
    pending.pop_back();
    if (level.use_count() == 1 && level->parent) {
      auto* mutable_level = const_cast<EnvNode*>(level.get());
      pending.push_back(std::move(mutable_level->parent));
    }
    // `level` dies here; if it was the last owner, its link is already gone.
  }
}

}  // namespace

/// Resolution machine over a persistent environment chain and a choice-point
/// stack.
class Solver {
 public:
  explicit Solver(Engine& engine) : engine_(engine) {}

  /// Releases whatever is still held when the query ends — the environment
  /// chain and the choice points — through `releaseEnvChain`, or a deep chain
  /// would come down inside the destructors and overflow the C++ stack.
  ~Solver() {
    releaseEnvChain(env_);
    dropChoicePoints(0);
  }

  Solver(const Solver&) = delete;
  Solver& operator=(const Solver&) = delete;

  /// Solve `goals`; `location` is where they stand in the source, which is what
  /// a step point of the query's own goals reports.
  void run(std::span<const Term> goals, const std::function<bool()>& on_solution,
           const SourceLocation& location = {});

 private:
  bool resolveGoal(const Term& goal);
  bool selectClause(ChoicePoint& cp);
  bool backtrack();
  void applyCut();
  /// Keep `keep` choice points and release the rest through `releaseEnvChain`.
  void dropChoicePoints(std::size_t keep);
  void pushMeta(const Term& goal, std::size_t barrier);
  void traceGoal(const Term& goal);
  void traceText(std::string_view text);
  /// The environment moves with the location it stands for: a runtime error and
  /// a step must name the clause that is being solved, not the query.
  void setEnv(EnvRef env);
  /// One step point, if a front-end asked for them.  `goal` may be null where
  /// the goal is the one the matching `Call` already reported, and `depth` is
  /// the nesting the point belongs to — for an `Exit` that is the depth of the
  /// goal that is leaving, not of the frame it leaves.
  void step(StepAction action, const Term* goal, const SourceLocation& location,
            std::size_t depth);

  Engine& engine_;
  EnvRef env_;
  std::vector<ChoicePoint> cps_;
  std::size_t steps_ = 0;
};

/// Puts the engine's current location back when a query ends, however it ends.
/// A nested query (`НАЙТИВСЕ`, `НЕ`, `ПЕРВОЕ`) runs its own solver over its own
/// environment chain, and the outer one has to keep its own idea of where it is.
class LocationGuard {
 public:
  explicit LocationGuard(Engine& engine)
      : engine_(engine), saved_(engine.currentLocation()) {}
  ~LocationGuard() { engine_.setCurrentLocation(saved_); }
  LocationGuard(const LocationGuard&) = delete;
  LocationGuard& operator=(const LocationGuard&) = delete;

 private:
  Engine& engine_;
  SourceLocation saved_;
};

void Solver::setEnv(EnvRef env) {
  env_ = std::move(env);
  engine_.setCurrentLocation(env_->location);
}

void Solver::step(StepAction action, const Term* goal, const SourceLocation& location,
                  std::size_t depth) {
  const EngineOptions& options = engine_.options();
  if (!options.stepHook) {
    return;  // not stepping: this is the whole cost of the hook
  }
  StepInfo info;
  info.action = action;
  info.goal = goal;
  info.depth = depth;
  info.location = location;
  if (options.stepHook(info) == StepDecision::Stop) {
    engine_.raise(ErrorCode::Interrupted);
  }
}

void Solver::traceText(std::string_view text) {
  if (engine_.traceEnabled()) {
    engine_.io().writeTrace(text);
  }
}

void Solver::traceGoal(const Term& goal) {
  if (engine_.traceEnabled()) {
    engine_.io().writeTrace("Цель " + engine_.format(goal));
  }
}

void Solver::applyCut() {
  dropChoicePoints(env_->cp_barrier);
}

void Solver::dropChoicePoints(std::size_t keep) {
  if (keep >= cps_.size()) {
    return;
  }
  for (std::size_t index = keep; index < cps_.size(); ++index) {
    releaseEnvChain(cps_[index].env);
  }
  cps_.resize(keep);
}

void Solver::pushMeta(const Term& goal, std::size_t barrier) {
  auto goals = std::make_shared<std::vector<Term>>();
  goals->push_back(goal);
  setEnv(makeEnv(env_, std::move(goals), barrier));
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
      setEnv(advanceEnv(cp.env));
      // The body of *this* clause: its position is what a runtime error and a
      // step point inside it must report.
      setEnv(makeEnv(env_, std::make_shared<std::vector<Term>>(std::move(body)), cp.barrier,
                     &clause.location, /*goal_frame=*/true));
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
    if (cp.kind == ChoicePoint::Kind::Alternative) {
      // The right branch of a disjunction: the continuation is the goal that
      // follows the `;` goal, and the cut barrier sits where the alternative was,
      // so a cut inside this branch prunes only what the branch itself creates.
      setEnv(advanceEnv(cp.env));
      if (engine_.traceEnabled()) {
        traceText("Переделка. Цель " + engine_.format(cp.goal));
      }
      step(StepAction::Redo, &cp.goal, env_->location, env_->depth);
      pushMeta(cp.goal.compound->args[1], cps_.size());
      return true;
    }
    setEnv(cp.env);
    if (engine_.traceEnabled()) {
      traceText("Переделка. Цель " + engine_.format(cp.goal));
    }
    step(StepAction::Redo, &cp.goal, env_->location, env_->depth);
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
    setEnv(advanceEnv(env_));
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
  if (name == ";" && arity == 2) {
    // A disjunction: the right operand becomes an alternative, and the left one
    // runs in a frame of its own.  That frame's cut barrier sits *above* the
    // alternative, so a cut inside a branch prunes what the branch itself
    // created and leaves the other branch alone (the ISO rule: a cut in a
    // disjunct is local to that disjunct).
    ChoicePoint cp;
    cp.kind = ChoicePoint::Kind::Alternative;
    cp.goal = goal;
    cp.trail_mark = engine_.bindings().trailMark();
    cp.barrier = cps_.size();
    cp.env = env_;
    cps_.push_back(std::move(cp));
    const std::size_t barrier = cps_.size();
    setEnv(advanceEnv(env_));
    pushMeta(goal.compound->args[0], barrier);
    return true;
  }
  if ((name == "ВЫП" || name == "call") && arity == 1) {
    // Meta-call: solve the argument in the caller's cut scope.  `call` is the
    // English spelling of `ВЫП` and reaches the same place: the engine answers
    // this one, not the dispatch table, so the alias has to be matched here.
    const std::size_t barrier = env_->cp_barrier;
    setEnv(advanceEnv(env_));
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
        setEnv(advanceEnv(env_));
        return true;
      case BuiltinResult::Fail:
        return false;
      case BuiltinResult::Handled:
        return true;
    }
    return true;
  }

  traceGoal(goal);
  // A user predicate: the goal is entered (`Exit` or `Fail` will follow), and
  // the position is the clause this goal is being called *from*.
  const SourceLocation caller = env_->location;
  step(StepAction::Call, &goal, caller, env_->depth);

  Database::ClauseListPtr clauses = engine_.database().clausesFor(name, arity);
  if (!clauses || clauses->empty()) {
    step(StepAction::Fail, &goal, caller, env_->depth);
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
    step(StepAction::Fail, &goal, caller, env_->depth);
    return false;
  }
  if (cp.next < cp.clauses->size()) {
    cps_.push_back(std::move(cp));
  }
  return true;
}

void Solver::run(std::span<const Term> goals, const std::function<bool()>& on_solution,
                 const SourceLocation& location) {
  LocationGuard location_guard(engine_);
  dropChoicePoints(0);
  steps_ = 0;
  const std::shared_ptr<std::vector<Term>> root =
      std::make_shared<std::vector<Term>>(goals.begin(), goals.end());
  // The goals of the query itself stand where the query was written — a `?`
  // statement in a file has a line, one typed at the prompt has none.
  setEnv(makeEnv(nullptr, root, 0, &location));

  for (;;) {
    if (engine_.shouldStop()) {
      engine_.raise(ErrorCode::Interrupted);
    }
    if (engine_.options().maxSteps != 0 && ++steps_ > engine_.options().maxSteps) {
      engine_.raise(ErrorCode::Interrupted, "Превышен лимит шагов выполнения");
    }
    // A guard, not a workaround: the solver loops instead of recursing, and the
    // chain release is iterative, so this only stops a runaway program with a
    // message instead of letting it eat memory for an hour.
    if (engine_.options().maxDepth != 0 && env_->depth > engine_.options().maxDepth) {
      engine_.raise(ErrorCode::StackOverflow,
                    "Превышена глубина рекурсии (лимит " +
                        std::to_string(engine_.options().maxDepth) + ")");
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
        // Leaving a clause body: the goal that was entered has succeeded.  The
        // frames of a conjunction and of ВЫП are not goals, so they are not
        // announced — a front-end rebuilds the call stack from Call/Exit pairs.
        if (env_->goalFrame) {
          // The depth of the goal that is leaving, not of the frame it leaves:
          // then an `exit` and the `call` it answers report the same depth, and
          // a front-end can pair them without guessing.
          step(StepAction::Exit, nullptr, env_->location, env_->depth - 1);
        }
        setEnv(env_->parent);
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

Term Engine::copyTermResolvedImpl(const Term& term, std::unordered_map<VarId, VarId>& mapping,
                                  std::vector<const CompoundTerm*>& path) {
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
      // A cyclic term (`?РАВНО(X, f(X)).` builds one — there is no occurs check)
      // has no finite copy: the copy would be cyclic too, and every later walk of
      // it would run forever.  Say so instead of recursing until the stack ends.
      if (std::find(path.begin(), path.end(), resolved.compound.get()) != path.end()) {
        raise(ErrorCode::StackOverflow, "Циклический терм нельзя скопировать");
      }
      path.push_back(resolved.compound.get());
      std::vector<Term> args;
      args.reserve(resolved.compound->args.size());
      for (const Term& arg : resolved.compound->args) {
        args.push_back(copyTermResolvedImpl(arg, mapping, path));
      }
      path.pop_back();
      return makeCompound(resolved.compound->name, std::move(args));
    }
    default:
      return resolved;
  }
}

Term Engine::copyTermResolved(const Term& term) {
  std::unordered_map<VarId, VarId> mapping;
  std::vector<const CompoundTerm*> path;
  return copyTermResolvedImpl(term, mapping, path);
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

    // An integer and a real unify when they are the *same number*: the original
    // keeps the two apart as types but compares their values, so `6` matches
    // `6.0` and not `6.5`.  The comparison has to be exact — the integer used to
    // be narrowed to `float` first and compared with the double, which made
    // different numbers unify (`16777217` with `16777216.0`) and made a large
    // integer miss its own real (`16777217` with `16777217.0`); comparing the
    // integer's nearest double would let `10^20 + 1` match `10^20.0`.
    if ((left.kind == TermKind::Int && right.kind == TermKind::Float) ||
        (left.kind == TermKind::Float && right.kind == TermKind::Int)) {
      const Term& as_int = left.kind == TermKind::Int ? left : right;
      const double real = (left.kind == TermKind::Int ? right : left).real;
      if (!std::isfinite(real) || real != std::trunc(real) ||
          BigInt::fromDouble(real) != as_int.integer) {
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
  std::vector<const CompoundTerm*> path;
  out_head = copyTermResolvedImpl(head, mapping, path);
  out_body.clear();
  out_body.reserve(body.size());
  for (const Term& goal : body) {
    out_body.push_back(copyTermResolvedImpl(goal, mapping, path));
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
  // The clause being solved is where a runtime error happened, and the solver
  // keeps that in step with its environment; `raiseAt` overrides it.
  error.location = current_location_;
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
  // A call to a reserved name with an arity the interpreter does not have can
  // never succeed; the parser cannot see the tables, so the check lives here.
  checkReservedCalls(program, database_, sink);
  for (const PrologError& diagnostic : sink.diagnostics()) {
    if (diagnostic.code == ErrorCode::NoErrors) {
      continue;
    }
    report(diagnostic);
  }
  if (sink.hasErrors()) {
    program.ok = false;
  }
  return program;
}

void Engine::report(const PrologError& diagnostic) {
  if (diagnostic_hook_) {
    // The front-end takes it from here, with the location in structured form.
    diagnostic_hook_(diagnostic);
    return;
  }
  io_->errorStream() << DiagnosticSink::format(diagnostic) << '\n';
}

void Engine::loadProgram(const ParsedProgram& program) {
  for (const Clause& clause : program.clauses) {
    database_.addClause(clause);
  }
}

void Engine::checkCallSites(const ParsedProgram& program) {
  prologd::checkCallSites(program, database_,
                          [this](const PrologError& diagnostic) { report(diagnostic); });
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
    }, query.location);
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
  }, query.location);

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
  // The built-ins *are* the definitions (ADR-018): a library used to be loaded
  // here as well (`НЕ`, `РАВНО`, `МЕНЬШЕ`, `СЛОЖЕНИЕ`, `ПС`, `ДЛИНА`), but
  // `findBuiltin` answers every one of those names, so the clauses could only
  // be seen by reading the database directly — `?СКОЛЬКО(НЕ, А)` answered 2,
  // a number that described nothing callable.  A future build without a
  // dispatch table would want the bootstrap back, in a file that says exactly
  // that and is not loaded by default (task_43).
}

}  // namespace prologd
