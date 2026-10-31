#include <catch2/catch_test_macros.hpp>

#include <cmath>
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

  // The conversion is exact for every finite double, not just for the small
  // ones.  The limb loop it used to run divided the magnitude by the base in
  // `double`, and above 2^53 that dropped low digits: `1e300` came back as an
  // integer a few digits short of it, so `РАВНО` could pair a whole number with
  // the wrong real.  Each expectation below is the number the double holds.
  const double large = std::ldexp(1.0, 100);
  REQUIRE(BigInt::fromDouble(large).toString() == "1267650600228229401496703205376");
  // The next double after 2^100 is 2^100 + 2^48.
  REQUIRE(BigInt::fromDouble(std::nextafter(large, INFINITY)).toString() ==
          "1267650600228229682971679916032");
  // `1e300` is not that decimal number: the double nearest to it is the one
  // whose digits these are, and the conversion must give exactly them.
  REQUIRE(BigInt::fromDouble(1e300).toString() ==
          "100000000000000005250476025520442024870446858110815915491585411551180245798890819578"
          "637137508044786404370444383288387817694252323536043057564479218478670698284838720092"
          "657580373783023379478809005936895323497079994508111903896764088007465274278014249457"
          "9258788820056842838115669472196386865459400540160");
}
