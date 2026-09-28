#pragma once

#include <compare>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace prologd {

/// Arbitrary precision signed integer.
///
/// Representation: sign + magnitude, magnitude stored as little-endian limbs in
/// base 10^9.  Base 10^9 was chosen so that decimal conversion is exact and
/// cheap, and so that a product of two limbs plus carry fits into `uint64_t`
/// (which keeps the implementation portable to MSVC, where `__int128` is not
/// available).
class BigInt {
 public:
  BigInt() = default;
  BigInt(int64_t value);  // NOLINT(google-explicit-constructor): numeric literal

  /// Parse a decimal string with an optional leading `+`/`-`.
  /// Throws `std::invalid_argument` when the input is not a valid decimal.
  explicit BigInt(std::string_view decimal);

  static std::optional<BigInt> tryParse(std::string_view decimal);

  [[nodiscard]] bool isZero() const noexcept { return limbs_.empty(); }
  [[nodiscard]] bool isNegative() const noexcept { return negative_; }
  [[nodiscard]] int sign() const noexcept {
    return limbs_.empty() ? 0 : (negative_ ? -1 : 1);
  }

  [[nodiscard]] BigInt abs() const;
  [[nodiscard]] BigInt operator-() const;

  BigInt& operator+=(const BigInt& other);
  BigInt& operator-=(const BigInt& other);
  BigInt& operator*=(const BigInt& other);
  BigInt& operator/=(const BigInt& other);
  BigInt& operator%=(const BigInt& other);

  friend BigInt operator+(BigInt lhs, const BigInt& rhs) { return lhs += rhs; }
  friend BigInt operator-(BigInt lhs, const BigInt& rhs) { return lhs -= rhs; }
  friend BigInt operator*(BigInt lhs, const BigInt& rhs) { return lhs *= rhs; }
  friend BigInt operator/(BigInt lhs, const BigInt& rhs) { return lhs /= rhs; }
  friend BigInt operator%(BigInt lhs, const BigInt& rhs) { return lhs %= rhs; }

  friend std::strong_ordering operator<=>(const BigInt& lhs, const BigInt& rhs);
  friend bool operator==(const BigInt& lhs, const BigInt& rhs) = default;

  /// Decimal representation, without a leading `+`; `0` for zero.
  [[nodiscard]] std::string toString() const;

  /// Conversion to `double`; large magnitudes saturate to infinity.
  [[nodiscard]] double toDouble() const;

  /// Conversion to `int64_t`, saturating on overflow.
  [[nodiscard]] int64_t toInt64() const;

  /// Build from a `double`, truncating the fractional part toward zero.
  [[nodiscard]] static BigInt fromDouble(double value);

  /// Number of significant decimal digits (0 for zero).
  [[nodiscard]] std::size_t digitCount() const;

 private:
  static constexpr std::uint32_t kBase = 1'000'000'000u;
  static constexpr int kBaseDigits = 9;

  bool negative_ = false;
  std::vector<std::uint32_t> limbs_;  // little-endian, canonical

  void trim();
  static int compareMagnitude(const std::vector<std::uint32_t>& a,
                              const std::vector<std::uint32_t>& b);
  static std::vector<std::uint32_t> addMagnitude(const std::vector<std::uint32_t>& a,
                                                 const std::vector<std::uint32_t>& b);
  /// Requires `a >= b`.
  static std::vector<std::uint32_t> subMagnitude(const std::vector<std::uint32_t>& a,
                                                 const std::vector<std::uint32_t>& b);
  static std::vector<std::uint32_t> mulMagnitude(const std::vector<std::uint32_t>& a,
                                                 const std::vector<std::uint32_t>& b);
  static std::vector<std::uint32_t> mulMagnitudeSmall(const std::vector<std::uint32_t>& a,
                                                      std::uint32_t factor);
  static void divModMagnitude(const std::vector<std::uint32_t>& a,
                              const std::vector<std::uint32_t>& b,
                              std::vector<std::uint32_t>& quotient,
                              std::vector<std::uint32_t>& remainder);
  static void mulAddSmall(std::vector<std::uint32_t>& magnitude, std::uint32_t factor,
                          std::uint32_t addend);
};

/// Absolute value, usable as `abs(x)` with argument-dependent lookup.
[[nodiscard]] inline BigInt abs(const BigInt& value) { return value.abs(); }

}  // namespace prologd
