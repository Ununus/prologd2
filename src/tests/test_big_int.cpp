#include <catch2/catch_test_macros.hpp>

#include <string>

#include "prlib/big_int.hpp"

using prologd::BigInt;

TEST_CASE("BigInt parses and prints decimals") {
  REQUIRE(BigInt("0").toString() == "0");
  REQUIRE(BigInt("42").toString() == "42");
  REQUIRE(BigInt("-42").toString() == "-42");
  REQUIRE(BigInt("+42").toString() == "42");
  REQUIRE(BigInt("1000000000").toString() == "1000000000");
  REQUIRE(BigInt("123456789012345678901234567890").toString() ==
          "123456789012345678901234567890");
  REQUIRE_FALSE(BigInt::tryParse("").has_value());
  REQUIRE_FALSE(BigInt::tryParse("12a").has_value());
  REQUIRE_FALSE(BigInt::tryParse("-").has_value());
}

TEST_CASE("BigInt arithmetic matches native for small values") {
  for (long long a = -50; a <= 50; a += 7) {
    for (long long b = -50; b <= 50; b += 5) {
      const BigInt left(a);
      const BigInt right(b);
      REQUIRE((left + right).toInt64() == a + b);
      REQUIRE((left - right).toInt64() == a - b);
      REQUIRE((left * right).toInt64() == a * b);
      if (b != 0) {
        REQUIRE((left / right).toInt64() == a / b);
        REQUIRE((left % right).toInt64() == a % b);
      }
    }
  }
}

TEST_CASE("BigInt division and modulo semantics") {
  REQUIRE((BigInt(-7) / BigInt(2)).toString() == "-3");
  REQUIRE((BigInt(-7) % BigInt(2)).toString() == "-1");
  REQUIRE((BigInt(7) / BigInt(-2)).toString() == "-3");
  REQUIRE((BigInt(7) % BigInt(-2)).toString() == "1");
  REQUIRE_THROWS_AS(BigInt(1) / BigInt(0), std::domain_error);
  REQUIRE_THROWS_AS(BigInt(1) % BigInt(0), std::domain_error);
}

TEST_CASE("BigInt large multiplication") {
  const BigInt value("123456789123456789123456789");
  REQUIRE((value * value).toString() ==
          "15241578780673678546105778281054720515622620750190521");
}

TEST_CASE("BigInt factorial 111 digits match the original test") {
  BigInt factorial(1);
  for (int i = 2; i <= 111; ++i) {
    factorial *= BigInt(i);
  }
  REQUIRE(factorial.toString() ==
          "176295255109024466387216104710707578876140953602656551604157"
          "406334734695508724831643655557459846231577319604766283797891"
          "314584749719987162332009625414533120000000000000000000000000"
          "0");}

TEST_CASE("BigInt comparison and abs") {
  REQUIRE(BigInt(-5) < BigInt(3));
  REQUIRE(BigInt(5) > BigInt(-3));
  REQUIRE(BigInt(-5) < BigInt(-3));
  REQUIRE(BigInt(5) == BigInt(5));
  REQUIRE(BigInt(-5).abs() == BigInt(5));
  REQUIRE((-BigInt(5)).toString() == "-5");
  REQUIRE(BigInt(0).sign() == 0);
  REQUIRE(BigInt(-3).isNegative());
}

TEST_CASE("BigInt double conversion") {
  REQUIRE(BigInt(42).toDouble() == 42.0);
  REQUIRE(BigInt::fromDouble(42.9).toString() == "42");
  REQUIRE(BigInt::fromDouble(-42.9).toString() == "-42");
  const BigInt value("123456789012345678901234567890");
  REQUIRE(BigInt::fromDouble(value.toDouble()).digitCount() > 20);
}
