#pragma once

#include "prlib/term.hpp"

namespace prologd {

class Bindings;

/// The standard order of terms (ISO 13211-1 §8.4), as the numbers `-1`, `0`
/// and `1` stand for «меньше», «равно» and «больше» (task_90).
///
/// The kinds are ordered variables < numbers < text < compounds; numbers are
/// compared by value, text by code point, variables by age (their id), and two
/// compounds by arity, then by name, then argument by argument.  Text means an
/// atom *or* a string: the dialect unifies the two, so they are one value here
/// as well (the one place where this order differs from ISO, where a string is
/// a list of codes and sorts after every atom).
///
/// A term that contains itself is compared as far as it can be: a pair of
/// compound cells seen twice is taken as equal, the guard `ПОЛНЫЙ` uses for the
/// same reason.
int compareStandardOrder(const Bindings& bindings, const Term& first, const Term& second);

}  // namespace prologd
