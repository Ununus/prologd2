#include "prlib/big_int.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace prologd {

namespace {
constexpr std::uint32_t kBase = 1'000'000'000u;
}  // namespace

BigInt::BigInt(int64_t value) {
  if (value == 0) {
    return;
  }
  std::uint64_t magnitude = 0;
  if (value < 0) {
    negative_ = true;
    // Negating INT64_MIN in signed arithmetic is UB; use unsigned.
    magnitude = static_cast<std::uint64_t>(-(value + 1)) + 1u;
  } else {
    magnitude = static_cast<std::uint64_t>(value);
  }
  while (magnitude > 0) {
    limbs_.push_back(static_cast<std::uint32_t>(magnitude % kBase));
    magnitude /= kBase;
  }
}

BigInt::BigInt(std::string_view decimal) {
  auto parsed = tryParse(decimal);
  if (!parsed) {
    throw std::invalid_argument("BigInt: invalid decimal string: " + std::string(decimal));
  }
  *this = *parsed;
}

std::optional<BigInt> BigInt::tryParse(std::string_view decimal) {
  if (decimal.empty()) {
    return std::nullopt;
  }
  std::size_t pos = 0;
  bool negative = false;
  if (decimal[pos] == '+' || decimal[pos] == '-') {
    negative = decimal[pos] == '-';
    ++pos;
  }
  if (pos >= decimal.size()) {
    return std::nullopt;
  }
  BigInt result;
  for (; pos < decimal.size(); ++pos) {
    const char ch = decimal[pos];
    if (ch < '0' || ch > '9') {
      return std::nullopt;
    }
    result.mulAddSmall(result.limbs_, 10, static_cast<std::uint32_t>(ch - '0'));
  }
  result.negative_ = negative && !result.limbs_.empty();
  return result;
}

void BigInt::trim() {
  while (!limbs_.empty() && limbs_.back() == 0) {
    limbs_.pop_back();
  }
  if (limbs_.empty()) {
    negative_ = false;
  }
}

int BigInt::compareMagnitude(const std::vector<std::uint32_t>& a,
                             const std::vector<std::uint32_t>& b) {
  if (a.size() != b.size()) {
    return a.size() < b.size() ? -1 : 1;
  }
  for (std::size_t i = a.size(); i-- > 0;) {
    if (a[i] != b[i]) {
      return a[i] < b[i] ? -1 : 1;
    }
  }
  return 0;
}

std::vector<std::uint32_t> BigInt::addMagnitude(const std::vector<std::uint32_t>& a,
                                                const std::vector<std::uint32_t>& b) {
  const std::size_t n = std::max(a.size(), b.size());
  std::vector<std::uint32_t> result;
  result.reserve(n + 1);
  std::uint64_t carry = 0;
  for (std::size_t i = 0; i < n; ++i) {
    const std::uint64_t sum = carry + (i < a.size() ? a[i] : 0u) + (i < b.size() ? b[i] : 0u);
    result.push_back(static_cast<std::uint32_t>(sum % kBase));
    carry = sum / kBase;
  }
  if (carry != 0) {
    result.push_back(static_cast<std::uint32_t>(carry));
  }
  return result;
}

std::vector<std::uint32_t> BigInt::subMagnitude(const std::vector<std::uint32_t>& a,
                                                const std::vector<std::uint32_t>& b) {
  std::vector<std::uint32_t> result;
  result.reserve(a.size());
  std::int64_t borrow = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    std::int64_t diff = static_cast<std::int64_t>(a[i]) - borrow -
                        (i < b.size() ? static_cast<std::int64_t>(b[i]) : 0);
    if (diff < 0) {
      diff += static_cast<std::int64_t>(kBase);
      borrow = 1;
    } else {
      borrow = 0;
    }
    result.push_back(static_cast<std::uint32_t>(diff));
  }
  while (!result.empty() && result.back() == 0) {
    result.pop_back();
  }
  return result;
}

std::vector<std::uint32_t> BigInt::mulMagnitude(const std::vector<std::uint32_t>& a,
                                                const std::vector<std::uint32_t>& b) {
  if (a.empty() || b.empty()) {
    return {};
  }
  std::vector<std::uint32_t> result(a.size() + b.size(), 0);
  for (std::size_t i = 0; i < a.size(); ++i) {
    std::uint64_t carry = 0;
    const std::uint64_t ai = a[i];
    for (std::size_t j = 0; j < b.size(); ++j) {
      const std::uint64_t cur = result[i + j] + ai * b[j] + carry;
      result[i + j] = static_cast<std::uint32_t>(cur % kBase);
      carry = cur / kBase;
    }
    std::size_t k = i + b.size();
    while (carry != 0) {
      const std::uint64_t cur = result[k] + carry;
      result[k] = static_cast<std::uint32_t>(cur % kBase);
      carry = cur / kBase;
      ++k;
    }
  }
  while (!result.empty() && result.back() == 0) {
    result.pop_back();
  }
  return result;
}

std::vector<std::uint32_t> BigInt::mulMagnitudeSmall(const std::vector<std::uint32_t>& a,
                                                     std::uint32_t factor) {
  if (a.empty() || factor == 0) {
    return {};
  }
  std::vector<std::uint32_t> result;
  result.reserve(a.size() + 1);
  std::uint64_t carry = 0;
  for (std::uint32_t limb : a) {
    const std::uint64_t cur = static_cast<std::uint64_t>(limb) * factor + carry;
    result.push_back(static_cast<std::uint32_t>(cur % kBase));
    carry = cur / kBase;
  }
  while (carry != 0) {
    result.push_back(static_cast<std::uint32_t>(carry % kBase));
    carry /= kBase;
  }
  return result;
}

void BigInt::mulAddSmall(std::vector<std::uint32_t>& magnitude, std::uint32_t factor,
                         std::uint32_t addend) {
  std::uint64_t carry = addend;
  for (std::uint32_t& limb : magnitude) {
    const std::uint64_t cur = static_cast<std::uint64_t>(limb) * factor + carry;
    limb = static_cast<std::uint32_t>(cur % kBase);
    carry = cur / kBase;
  }
  while (carry != 0) {
    magnitude.push_back(static_cast<std::uint32_t>(carry % kBase));
    carry /= kBase;
  }
}

void BigInt::divModMagnitude(const std::vector<std::uint32_t>& a,
                             const std::vector<std::uint32_t>& b,
                             std::vector<std::uint32_t>& quotient,
                             std::vector<std::uint32_t>& remainder) {
  quotient.clear();
  remainder.clear();
  if (b.empty()) {
    throw std::domain_error("BigInt: division by zero");
  }
  if (compareMagnitude(a, b) < 0) {
    remainder = a;
    return;
  }
  if (b.size() == 1) {
    // Fast path: divide by a single limb.
    const std::uint64_t divisor = b[0];
    quotient.assign(a.size(), 0);
    std::uint64_t rem = 0;
    for (std::size_t i = a.size(); i-- > 0;) {
      const std::uint64_t cur = rem * kBase + a[i];
      quotient[i] = static_cast<std::uint32_t>(cur / divisor);
      rem = cur % divisor;
    }
    while (!quotient.empty() && quotient.back() == 0) {
      quotient.pop_back();
    }
    if (rem != 0) {
      remainder.push_back(static_cast<std::uint32_t>(rem));
    }
    return;
  }

  quotient.assign(a.size(), 0);
  std::vector<std::uint32_t> rem;
  for (std::size_t i = a.size(); i-- > 0;) {
    // rem = rem * kBase + a[i]
    rem = mulMagnitudeSmall(rem, kBase);
    // rem fits in a vector; add the limb.
    std::uint64_t carry = a[i];
    for (std::size_t k = 0; k < rem.size() && carry != 0; ++k) {
      const std::uint64_t cur = rem[k] + carry;
      rem[k] = static_cast<std::uint32_t>(cur % kBase);
      carry = cur / kBase;
    }
    while (carry != 0) {
      rem.push_back(static_cast<std::uint32_t>(carry % kBase));
      carry /= kBase;
    }
    // Binary search the largest digit d with b * d <= rem.
    std::uint32_t lo = 0;
    std::uint32_t hi = kBase - 1;
    while (lo < hi) {
      const std::uint32_t mid = lo + (hi - lo + 1) / 2;
      const std::vector<std::uint32_t> product = mulMagnitudeSmall(b, mid);
      if (compareMagnitude(product, rem) <= 0) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    if (lo != 0) {
      quotient[i] = lo;
      const std::vector<std::uint32_t> product = mulMagnitudeSmall(b, lo);
      rem = subMagnitude(rem, product);
    }
  }
  while (!quotient.empty() && quotient.back() == 0) {
    quotient.pop_back();
  }
  remainder = rem;
}

BigInt BigInt::abs() const {
  BigInt result = *this;
  result.negative_ = false;
  return result;
}

BigInt BigInt::operator-() const {
  BigInt result = *this;
  if (!result.limbs_.empty()) {
    result.negative_ = !result.negative_;
  }
  return result;
}

BigInt& BigInt::operator+=(const BigInt& other) {
  if (negative_ == other.negative_) {
    limbs_ = addMagnitude(limbs_, other.limbs_);
  } else {
    const int cmp = compareMagnitude(limbs_, other.limbs_);
    if (cmp >= 0) {
      limbs_ = subMagnitude(limbs_, other.limbs_);
    } else {
      limbs_ = subMagnitude(other.limbs_, limbs_);
      negative_ = other.negative_;
    }
  }
  trim();
  return *this;
}

BigInt& BigInt::operator-=(const BigInt& other) {
  return *this += (-other);
}

BigInt& BigInt::operator*=(const BigInt& other) {
  const bool negative = negative_ != other.negative_;
  limbs_ = mulMagnitude(limbs_, other.limbs_);
  negative_ = negative;
  trim();
  return *this;
}

BigInt& BigInt::operator/=(const BigInt& other) {
  if (other.isZero()) {
    throw std::domain_error("BigInt: division by zero");
  }
  const bool negative = negative_ != other.negative_;
  std::vector<std::uint32_t> quotient;
  std::vector<std::uint32_t> remainder;
  divModMagnitude(limbs_, other.limbs_, quotient, remainder);
  limbs_ = std::move(quotient);
  negative_ = negative;
  trim();
  return *this;
}

BigInt& BigInt::operator%=(const BigInt& other) {
  if (other.isZero()) {
    throw std::domain_error("BigInt: modulo by zero");
  }
  const bool negative = negative_;
  std::vector<std::uint32_t> quotient;
  std::vector<std::uint32_t> remainder;
  divModMagnitude(limbs_, other.limbs_, quotient, remainder);
  limbs_ = std::move(remainder);
  negative_ = negative;
  trim();
  return *this;
}

std::strong_ordering operator<=>(const BigInt& lhs, const BigInt& rhs) {
  if (lhs.negative_ != rhs.negative_) {
    return lhs.negative_ ? std::strong_ordering::less : std::strong_ordering::greater;
  }
  const int cmp = BigInt::compareMagnitude(lhs.limbs_, rhs.limbs_);
  if (cmp == 0) {
    return std::strong_ordering::equal;
  }
  const bool less = cmp < 0;
  if (lhs.negative_) {
    return less ? std::strong_ordering::greater : std::strong_ordering::less;
  }
  return less ? std::strong_ordering::less : std::strong_ordering::greater;
}

std::string BigInt::toString() const {
  if (limbs_.empty()) {
    return "0";
  }
  std::string result;
  if (negative_) {
    result.push_back('-');
  }
  result += std::to_string(limbs_.back());
  for (std::size_t i = limbs_.size() - 1; i-- > 0;) {
    std::string chunk = std::to_string(limbs_[i]);
    result.append(static_cast<std::size_t>(kBaseDigits) - chunk.size(), '0');
    result += chunk;
  }
  return result;
}

double BigInt::toDouble() const {
  double result = 0.0;
  for (std::size_t i = limbs_.size(); i-- > 0;) {
    result = result * static_cast<double>(kBase) + static_cast<double>(limbs_[i]);
  }
  return negative_ ? -result : result;
}

int64_t BigInt::toInt64() const {
  constexpr std::uint64_t kMax = static_cast<std::uint64_t>(std::numeric_limits<int64_t>::max());
  const std::uint64_t kMinMagnitude = kMax + 1u;
  std::uint64_t magnitude = 0;
  bool overflow = false;
  for (std::size_t i = limbs_.size(); i-- > 0;) {
    const std::uint64_t next = magnitude * kBase + limbs_[i];
    if (magnitude > (std::numeric_limits<std::uint64_t>::max() - limbs_[i]) / kBase) {
      overflow = true;
      break;
    }
    magnitude = next;
  }
  if (overflow) {
    return negative_ ? std::numeric_limits<int64_t>::min() : std::numeric_limits<int64_t>::max();
  }
  if (negative_) {
    if (magnitude >= kMinMagnitude) {
      return std::numeric_limits<int64_t>::min();
    }
    return -static_cast<int64_t>(magnitude);
  }
  if (magnitude > kMax) {
    return std::numeric_limits<int64_t>::max();
  }
  return static_cast<int64_t>(magnitude);
}

BigInt BigInt::fromDouble(double value) {
  if (!std::isfinite(value) || value == 0.0) {
    return BigInt();
  }
  const bool negative = value < 0.0;
  double magnitude = std::floor(std::abs(value));
  BigInt result;
  std::vector<std::uint32_t>& limbs = result.limbs_;
  while (magnitude >= 1.0) {
    const double chunk = std::fmod(magnitude, static_cast<double>(kBase));
    limbs.push_back(static_cast<std::uint32_t>(chunk));
    magnitude = (magnitude - chunk) / static_cast<double>(kBase);
  }
  result.negative_ = negative;
  result.trim();
  return result;
}

std::size_t BigInt::digitCount() const {
  if (limbs_.empty()) {
    return 0;
  }
  std::size_t count = (limbs_.size() - 1) * static_cast<std::size_t>(kBaseDigits);
  count += std::to_string(limbs_.back()).size();
  return count;
}

}  // namespace prologd
