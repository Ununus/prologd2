#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/big_int.hpp"

namespace prologd {

/// Identity of a logic variable.  Unique for the lifetime of an Engine.
using VarId = std::uint32_t;

/// The kind of a term.
enum class TermKind : std::uint8_t {
  Var,       ///< logic variable
  Atom,      ///< symbolic constant
  Int,       ///< arbitrary precision integer
  Float,     ///< IEEE double
  String,    ///< "..." string literal (distinct from an atom)
  Compound,  ///< functor with one or more arguments, includes list cells
};

struct Term;

/// Payload of a compound term.
struct CompoundTerm {
  std::string name;
  std::vector<Term> args;
};

/// Immutable term value.
///
/// Subterms of a compound are held through a `shared_ptr` to a `CompoundTerm`,
/// which keeps copying a term cheap and breaks the recursive type in a way that
/// is safe on every supported compiler.
///
/// Lists are represented as compounds with the reserved functor "." and arity 2;
/// the empty list is the atom "[]".  This mirrors standard Prolog internally and
/// keeps unification uniform.  Use the `makeList`/`isListCell`/`isNil` helpers
/// rather than comparing names by hand.
struct Term {
  TermKind kind = TermKind::Atom;

  /// Variable id (only for `TermKind::Var`).
  VarId var = 0;

  /// Atom name, string contents, or variable name (for diagnostics).
  std::string text;

  /// Integer payload (only for `TermKind::Int`).
  BigInt integer;

  /// Float payload (only for `TermKind::Float`).
  double real = 0.0;

  /// Compound payload (only for `TermKind::Compound`).
  std::shared_ptr<const CompoundTerm> compound;

  [[nodiscard]] bool isVar() const { return kind == TermKind::Var; }
  [[nodiscard]] bool isAtom() const { return kind == TermKind::Atom; }
  [[nodiscard]] bool isInt() const { return kind == TermKind::Int; }
  [[nodiscard]] bool isFloat() const { return kind == TermKind::Float; }
  [[nodiscard]] bool isString() const { return kind == TermKind::String; }
  [[nodiscard]] bool isCompound() const { return kind == TermKind::Compound; }
  [[nodiscard]] bool isNumber() const {
    return kind == TermKind::Int || kind == TermKind::Float;
  }
};

/// Reserved functor / atom used by the list encoding.
inline constexpr std::string_view kListFunctor = ".";
inline constexpr std::string_view kNilAtom = "[]";

/// Reserved functor of the wrapper the parser builds around a `#...#`
/// arithmetic expression.  It starts with `#`, so no identifier can spell it:
/// a user program cannot forge a wrapper by accident.
inline constexpr std::string_view kExpressionFunctor = "#expr";

Term makeVar(VarId id, std::string_view name = {});
Term makeAtom(std::string_view name);
Term makeInt(BigInt value);
Term makeInt(std::int64_t value);
Term makeFloat(double value);
Term makeString(std::string_view value);
Term makeCompound(std::string_view name, std::vector<Term> args);
Term makeList(Term head, Term tail);
Term makeNil();
Term makeListFromVector(const std::vector<Term>& elements, Term tail = makeNil());

/// True for the empty-list atom.
bool isNil(const Term& term);
/// True for a compound with the list functor and two arguments.
bool isListCell(const Term& term);
/// True for a list cell or the empty list.
bool isList(const Term& term);
/// True for a compound that is not a list cell.
bool isStruct(const Term& term);

/// Number of elements in a proper list; `nullopt` for an improper list.
[[nodiscard]] std::size_t listLength(const Term& list, bool* proper = nullptr);
/// Expand a proper list into a vector; returns false for improper/tail lists.
bool listToVector(const Term& list, std::vector<Term>& out);
/// Expand a list of unknown tail into elements and the tail.
bool listToVectorWithTail(const Term& list, std::vector<Term>& elements, Term& tail);

/// Structural equality of ground terms (variables compare by id).
bool structurallyEqual(const Term& lhs, const Term& rhs);

/// Compares two numbers by value, exactly: the answer is `-1`, `0` or `1`.
///
/// Both terms must be `Int` or `Float`.  Two integers compare as integers (they
/// can be wider than a `double`), and a mixed pair compares the integer with the
/// real *exactly*, narrowing neither side: `2 ** 100` and its own nearest
/// `double` are different numbers, and this says so.  `РАВНО` (through `== 0`),
/// `БОЛЬШЕ`, `МЕНЬШЕ` and the standard order of terms all take their answer
/// from here, so they cannot disagree about one pair — which is what the
/// `double` comparison they used to share could do.
///
/// NaN stands before every number and equals itself, as ISO has it; the dialect
/// produces none of its own (`sqrt(-1)` is an error), so this is the answer for
/// a real that came from outside through `СТРВЕЩ`.
int compareNumbers(const Term& left, const Term& right);

/// Human readable functor key, `name/arity`.
std::string functorKey(std::string_view name, std::size_t arity);

}  // namespace prologd
