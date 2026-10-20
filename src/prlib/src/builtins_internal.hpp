#pragma once

// Internal declarations shared by the built-in predicate implementation files.
// This header is private to prlib and is not installed.

#include <optional>
#include <string>
#include <string_view>

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
/// `badArguments(predicate)`.  This is the rule of `БОЛЬШЕ`/`МЕНЬШЕ`; the
/// standard order of `СОРТИРОВКА`, `@<` and `compare/3` is
/// `compareStandardOrder` in `prlib/order.hpp` (task_90).
int compareOrder(Engine& engine, const Term& first, const Term& second,
                 std::string_view predicate);

[[noreturn]] void badArguments(std::string_view predicate);

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

// ---------------------------------------------------------------------------
// The standard order of terms
// ---------------------------------------------------------------------------

BuiltinResult builtinCompare(Engine&, std::span<const Term>);

// ---- findall ----
BuiltinResult builtinFindAll(Engine&, std::span<const Term>);

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
