#include "prlib/term_print.hpp"

#include <cmath>
#include <unordered_map>

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
};

}  // namespace

std::string formatTerm(const Term& term, const Bindings& bindings,
                       const PrintOptions& options) {
  TermWriter writer(bindings, options);
  return writer.write(term);
}

}  // namespace prologd
