#include "prlib/term_print.hpp"

#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <vector>

#include "prlib/engine.hpp"

namespace prologd {

std::string formatFloat(double value) {
  if (std::isnan(value)) {
    return "nan";
  }
  if (std::isinf(value)) {
    return value < 0 ? "-inf" : "inf";
  }
  std::string text = std::to_string(value);
  while (text.size() > 1 && text[text.size() - 2] != '.' && text.back() == '0') {
    text.pop_back();
  }
  return text;
}

namespace {

/// The compound nodes on the way to the node being written, outermost first.
///
/// A node that appears twice is a cycle: `?РАВНО(X, f(X)).` unifies `X` with a
/// term that contains `X`, and the original PrologD has no occurs check, so one
/// line at the prompt asks for exactly that.  Writing such a term has to stop at
/// the repeat — the alternative is following the term until the C++ stack runs
/// out, which is how this used to fail (and a cyclic *list* never ended at all,
/// because its cells are followed in a loop rather than by recursion).
class PathGuard {
 public:
  explicit PathGuard(std::vector<const CompoundTerm*>& path)
      : path_(path), mark_(path.size()) {}
  ~PathGuard() { path_.resize(mark_); }

  void push(const CompoundTerm* node) { path_.push_back(node); }

 private:
  std::vector<const CompoundTerm*>& path_;
  std::size_t mark_;
};

class TermWriter {
 public:
  TermWriter(const Bindings& bindings, const PrintOptions& options)
      : bindings_(bindings), options_(options) {}

  std::string write(const Term& term) {
    std::string out;
    append(out, term, 0);
    return out;
  }

 private:
  /// True when `node` is one of the compounds currently being written.
  [[nodiscard]] bool onPath(const CompoundTerm* node) const {
    return std::find(path_.begin(), path_.end(), node) != path_.end();
  }

  void append(std::string& out, const Term& term, std::size_t depth) {
    if (depth > options_.maxDepth) {
      out += "...";
      return;
    }
    const Term resolved = bindings_.deref(term);
    switch (resolved.kind) {
      case TermKind::Var: {
        const auto it = variable_names_.find(resolved.var);
        if (it != variable_names_.end()) {
          out += it->second;
        } else {
          const std::string name = "_" + std::to_string(++next_variable_);
          variable_names_.emplace(resolved.var, name);
          out += name;
        }
        break;
      }
      case TermKind::Atom:
        out += resolved.text;
        break;
      case TermKind::String:
        out += resolved.text;
        break;
      case TermKind::Int:
        out += resolved.integer.toString();
        break;
      case TermKind::Float:
        out += formatFloat(resolved.real);
        break;
      case TermKind::Compound:
        appendCompound(out, resolved, depth);
        break;
    }
  }

  void appendCompound(std::string& out, const Term& term, std::size_t depth) {
    if (term.compound == nullptr) {
      out += "<null>";
      return;
    }
    // A node that is already being written is a cycle; write `...` for it and
    // leave it at that.
    if (onPath(term.compound.get())) {
      out += "...";
      return;
    }
    PathGuard guard(path_);
    guard.push(term.compound.get());
    // Arithmetic expression: evaluate when possible.
    if (term.compound->name == "$expr" && term.compound->args.size() == 1 &&
        options_.evaluate) {
      try {
        const Term value = options_.evaluate(term);
        append(out, value, depth + 1);
      } catch (const PrologRuntimeError& error) {
        if (error.error().code != ErrorCode::InvalidArithmeticExpression) {
          throw;
        }
        out += "#_?_#";
      }
      return;
    }
    // Proper/improper list.
    if (term.compound->name == kListFunctor && term.compound->args.size() == 2) {
      out += '[';
      Term current = term;
      bool first = true;
      for (;;) {
        const Term head = bindings_.deref(current.compound->args[0]);
        if (!first) {
          out += ',';
        }
        append(out, head, depth + 1);
        first = false;
        const Term tail = bindings_.deref(current.compound->args[1]);
        if (isListCell(tail)) {
          // The cells are followed in a loop, so the depth limit does not bound
          // this: `?РАВНО(X, [1|X]).` is a list that contains itself.
          if (onPath(tail.compound.get())) {
            out += "|...";
            break;
          }
          guard.push(tail.compound.get());
          current = tail;
          continue;
        }
        if (!isNil(tail)) {
          out += '|';
          append(out, tail, depth + 1);
        }
        break;
      }
      out += ']';
      return;
    }
    // Control constructs print the way they are written: `(A, B)`, `(A ; B)`.
    // A conjunction or a disjunction reaches a query echo, a trace line and a
    // step point, and `;(a,b)` is not what the program says.
    if ((term.compound->name == "," || term.compound->name == ";") &&
        term.compound->args.size() == 2) {
      out += '(';
      append(out, term.compound->args[0], depth + 1);
      out += term.compound->name == "," ? ", " : " ; ";
      append(out, term.compound->args[1], depth + 1);
      out += ')';
      return;
    }
    out += term.compound->name;
    out += '(';
    for (std::size_t i = 0; i < term.compound->args.size(); ++i) {
      if (i != 0) {
        out += ',';
      }
      append(out, term.compound->args[i], depth + 1);
    }
    out += ')';
  }

  const Bindings& bindings_;
  const PrintOptions& options_;
  std::unordered_map<VarId, std::string> variable_names_;
  std::size_t next_variable_ = 0;
  std::vector<const CompoundTerm*> path_;
};

}  // namespace

std::string formatTerm(const Term& term, const Bindings& bindings,
                       const PrintOptions& options) {
  TermWriter writer(bindings, options);
  return writer.write(term);
}

}  // namespace prologd
