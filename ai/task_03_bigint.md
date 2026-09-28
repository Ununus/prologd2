# task_03 — BigInt (arbitrary-precision integers)

**Status:** done
**Depends on:** task_01
**Milestone:** M1

## Goal

Implement the long arithmetic required by PrologD without external
dependencies (ADR-003).

## Deliverables

- [ ] `include/prlib/big_int.hpp`, `src/big_int.cpp`
  * sign + magnitude, base 10^9 limbs, `std::vector<std::uint32_t>`.
  * Constructors from `std::int64_t`, `std::string_view` (decimal, optional
    sign), and copy/move.
  * `operator+ - * / %`, unary `-`, `+= -= *= /= %=`.
  * Comparison `<=>`, `==`, `<`, `isZero`, `isNegative`, `sign()`.
  * `abs()`, `toString()`, `toDouble()` (with overflow to `inf` like the
    original), `fromDouble()`.
  * `toInt64()` with saturation for the APIs that need `long long`
    (graphics, sleep, random).
  * `hashValue` if needed by containers.
- [ ] `include/prlib/big_int_math.hpp` — `bigintSqrt`, `bigintPow` only if
      needed by `SQRT`/`EXP`; otherwise document `SQRT` on integers as the
      original does (integer square root of the double value).

## Design notes

* Division: schoolbook long division; `/` truncates toward zero and `%` has the
  sign of the dividend (C++ semantics), matching the original `cpp_int`.
* `toString` avoids `std::to_chars` for portability; format the top limb without
  padding and the rest with 9 digits.
* Performance is not critical, but arithmetic in loops (factorial 1333) must
  finish in well under a second.

## Tests

- [ ] `test_big_int.cpp`
  * round-trip `fromString`/`toString` for many magnitudes and signs;
  * `+ - *` against `__int128` for values in range (randomised, seeded);
  * `/` and `%` against native `long long` for in-range values including all
    sign combinations;
  * division by zero throws `std::domain_error`;
  * `toDouble`/`fromDouble` round-trip for representable values;
  * the three long-arithmetic scenarios from the old `test.txt`
    (`111!`, `1333!`, `2^?`-style sums) computed correctly;
  * `abs`, comparisons, zero handling (`-0` normalises to `0`).

## Acceptance

All BigInt tests pass, including the large factorial values that appear in the
original `prologd_test/test.txt` (`LONG ARITH`, `LONG ARITH 2`, `LONG ARITH 3`).
