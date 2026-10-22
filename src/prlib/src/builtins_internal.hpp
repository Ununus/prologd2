#pragma once

// Internal declarations shared by the built-in predicate implementation files.
// This header is private to prlib and is not installed.

#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/engine.hpp"

namespace prologd::detail {

// ---- conversions and helpers (defined in builtins.cpp) ----

Term derefTerm(Engine& engine, const Term& term);
bool isUnbound(Engine& engine, const Term& term);
bool isTextual(Engine& engine, const Term& term);
std::optional<ArithValue> asNumeric(Engine& engine, const Term& term);
std::optional<BigInt> asInteger(Engine& engine, const Term& term);
std::optional<double> asFloat(Engine& engine, const Term& term);
std::optional<std::string> asText(Engine& engine, const Term& term);

Term integerTerm(const BigInt& value);
Term floatTerm(double value);

bool unifyInteger(Engine& engine, const Term& argument, const BigInt& value);
bool unifyFloat(Engine& engine, const Term& argument, double value);
bool unifyText(Engine& engine, const Term& argument, const std::string& value);

/// `-1`, `0` or `1` for two values in the dialect's own order: numbers among
/// themselves by value, text among itself by code point.  Anything else is
/// `badArguments(engine, predicate)`.  This is the rule of `БОЛЬШЕ`/`МЕНЬШЕ`; the
/// standard order of `СОРТИРОВКА`, `@<` and `compare/3` is
/// `compareStandardOrder` in `prlib/order.hpp` (task_90).
int compareOrder(Engine& engine, std::span<const Term> args, std::string_view predicate);

/// The short `"<predicate>: Недопустимый тип аргументов"`, for the failures where no
/// single argument is at fault (part 136).
///
/// Raised **through the engine**, not thrown directly: `Engine::raise` is what adds
/// the clause being solved, so the console prints `файл:строка:столбец:` and the
/// window can show the place (part 137).
[[noreturn]] void badArguments(Engine& engine, std::string_view predicate);

/// What a built-in expects of one argument: the kind is what `badArguments`
/// tests, and the kind also names the expectation in the message (`ArgKind::Text`
/// reads «строка или атом»).  `NumberOrText` is the rule of `СЦЕП` and of the
/// conversions; `Comparable` is the rule of `БОЛЬШЕ`/`МЕНЬШЕ`, which compare two
/// numbers, two texts or two lists of those (part 138).
enum class ArgKind { Number, NumberOrText, Integer, Text, List, Comparable };

/// `<predicate>: Недопустимый тип аргументов: аргумент <index> — <что подано>,
/// нужно <ожидаемое>`.  `index` is 1-based, the way the message counts, and an
/// unbound variable is named as such instead of being printed as `_N` (part 136).
///
/// `expected` overrides the kind's own wording; keep it short — a diagnostic is
/// one line.
[[noreturn]] void badArgument(Engine& engine, const Term& term, std::string_view predicate,
                              std::size_t index, ArgKind kind, std::string_view expected = {});

/// The same, with the culprit found among `args`: the first *bound* argument that
/// is not of `kind`, and failing that the first unbound one — nothing had the wrong
/// type, the variable was simply never bound, which is a different mistake and
/// used to get the same message.
///
/// When every argument fits, the short message is kept: then no single argument is
/// at fault (an improper list, a range, a digit that is not one), and pretending
/// otherwise would mislead.  So this never lies; it either says which argument is
/// wrong or says nothing more than before.
///
/// `index_base` is the number the first element of `args` carries in the predicate:
/// `1` when `args` is the whole argument list, and the right number when a caller
/// hands over a *slice* — `СОРТИРОВКА/3` checks its list, which is argument 2, and
/// the message must count the way the predicate does (task_95).
[[noreturn]] void badArguments(Engine& engine, std::span<const Term> args,
                               std::string_view predicate, ArgKind kind,
                               std::string_view expected = {},
                               std::size_t index_base = 1);

}  // namespace prologd::detail

namespace prologd {

// ---- control and logic ----
BuiltinResult builtinFalse(Engine&, std::span<const Term>);
BuiltinResult builtinTrace(Engine&, std::span<const Term>);
BuiltinResult builtinNoTrace(Engine&, std::span<const Term>);
BuiltinResult builtinQuiet(Engine&, std::span<const Term>);
BuiltinResult builtinVersion(Engine&, std::span<const Term>);
BuiltinResult builtinNot(Engine&, std::span<const Term>);
BuiltinResult builtinForall(Engine&, std::span<const Term>);
BuiltinResult builtinEqual(Engine&, std::span<const Term>);
BuiltinResult builtinNewline(Engine&, std::span<const Term>);
BuiltinResult builtinWait(Engine&, std::span<const Term>);

// ---- type tests ----
BuiltinResult builtinIsVar(Engine&, std::span<const Term>);
BuiltinResult builtinIsInt(Engine&, std::span<const Term>);
BuiltinResult builtinIsFloat(Engine&, std::span<const Term>);
BuiltinResult builtinIsSymbol(Engine&, std::span<const Term>);
BuiltinResult builtinIsList(Engine&, std::span<const Term>);
BuiltinResult builtinIsGround(Engine&, std::span<const Term>);

// ---- lists ----
BuiltinResult builtinSort(Engine&, std::span<const Term>);
BuiltinResult builtinSort3(Engine&, std::span<const Term>);

/// `elements` in the standard order (task_95, task_91): ascending or not, with
/// the repeats dropped or kept.  `СОРТИРОВКА/2`, `/3` and `МНОРЕШ/3` share this
/// one sort, so `setof` and `СОРТИРОВКА` cannot disagree about what «sorted»
/// means.
std::vector<Term> sortedTerms(Engine& engine, std::vector<Term> elements, bool ascending,
                              bool keepDuplicates);

// ---------------------------------------------------------------------------
// The standard order of terms
// ---------------------------------------------------------------------------

BuiltinResult builtinCompare(Engine&, std::span<const Term>);

// ---- findall ----
BuiltinResult builtinFindAll(Engine&, std::span<const Term>);
// ---- collecting by groups (task_91) ----
BuiltinResult builtinBagOf(Engine&, std::span<const Term>);
BuiltinResult builtinSetOf(Engine&, std::span<const Term>);

// ---- arithmetic ----
BuiltinResult builtinGreater(Engine&, std::span<const Term>);
BuiltinResult builtinLess(Engine&, std::span<const Term>);
BuiltinResult builtinAdd(Engine&, std::span<const Term>);
BuiltinResult builtinMul3(Engine&, std::span<const Term>);
BuiltinResult builtinMul4(Engine&, std::span<const Term>);
BuiltinResult builtinAbs(Engine&, std::span<const Term>);
BuiltinResult builtinSqrt(Engine&, std::span<const Term>);
BuiltinResult builtinSin(Engine&, std::span<const Term>);
BuiltinResult builtinCos(Engine&, std::span<const Term>);
BuiltinResult builtinTan(Engine&, std::span<const Term>);
BuiltinResult builtinExp(Engine&, std::span<const Term>);
BuiltinResult builtinToInt(Engine&, std::span<const Term>);
BuiltinResult builtinToFloat(Engine&, std::span<const Term>);
BuiltinResult builtinRandom(Engine&, std::span<const Term>);
BuiltinResult builtinConvertIntFloat(Engine&, std::span<const Term>);
BuiltinResult builtinStringToInt(Engine&, std::span<const Term>);
BuiltinResult builtinStringToFloat(Engine&, std::span<const Term>);
BuiltinResult builtinStringToList(Engine&, std::span<const Term>);

// ---- strings ----
BuiltinResult builtinIsLetter(Engine&, std::span<const Term>);
BuiltinResult builtinIsDigit(Engine&, std::span<const Term>);
BuiltinResult builtinConcat(Engine&, std::span<const Term>);
BuiltinResult builtinCopy(Engine&, std::span<const Term>);
BuiltinResult builtinSubString(Engine&, std::span<const Term>);
BuiltinResult builtinStringLength(Engine&, std::span<const Term>);

// ---- input/output ----
BuiltinResult builtinWrite(Engine&, std::span<const Term>);
BuiltinResult builtinWriteLine(Engine&, std::span<const Term>);
BuiltinResult builtinWriteCode(Engine&, std::span<const Term>);
BuiltinResult builtinReadInt(Engine&, std::span<const Term>);
BuiltinResult builtinReadFloat(Engine&, std::span<const Term>);
BuiltinResult builtinReadSymbol(Engine&, std::span<const Term>);
BuiltinResult builtinReadString(Engine&, std::span<const Term>);
BuiltinResult builtinSee(Engine&, std::span<const Term>);
BuiltinResult builtinTell(Engine&, std::span<const Term>);

// ---- program database ----
BuiltinResult builtinClauseCount(Engine&, std::span<const Term>);
BuiltinResult builtinClauseInfo(Engine&, std::span<const Term>);
BuiltinResult builtinTermConvert(Engine&, std::span<const Term>);
BuiltinResult builtinAssert(Engine&, std::span<const Term>);
BuiltinResult builtinRetract(Engine&, std::span<const Term>);

// ---- graphics ----
BuiltinResult builtinPoint(Engine&, std::span<const Term>);
BuiltinResult builtinLine(Engine&, std::span<const Term>);
BuiltinResult builtinCircle(Engine&, std::span<const Term>);
BuiltinResult builtinFill(Engine&, std::span<const Term>);

}  // namespace prologd
