#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace prologd {

/// One Unicode code point.
using CodePoint = char32_t;

/// Result of decoding one code point.
struct DecodeResult {
  CodePoint code_point = 0;
  std::size_t length = 1;  // bytes consumed; 1 for an invalid byte
  bool valid = false;
};

/// Decode the code point starting at `text[offset]`.
/// Invalid UTF-8 is decoded byte by byte as Latin-1 and reported as invalid.
DecodeResult decodeCodePoint(std::string_view text, std::size_t offset);

/// Decode the whole string into code points.
std::vector<CodePoint> utf8Decode(std::string_view text);

/// Encode one code point as UTF-8.
std::string utf8Encode(CodePoint code_point);

/// True when `text` is well-formed UTF-8.
bool utf8IsValid(std::string_view text);

/// Number of code points in `text` (invalid bytes count as one each).
std::size_t utf8Length(std::string_view text);

/// Wrap a sequence of code points into a UTF-8 string.
std::string utf8FromCodePoints(const std::vector<CodePoint>& code_points);

/// Code-point based substring. Positions are 0-based; an out-of-range start or
/// count is clamped, mirroring `std::string::substr` leniency is *not* used.
std::string utf8Substr(std::string_view text, std::size_t start, std::size_t count);

/// Byte offset of the code point at `index`, or `text.size()` when past the end.
std::size_t utf8ByteOffset(std::string_view text, std::size_t index);

/// Remove a leading UTF-8 byte order mark if present.
std::string_view stripByteOrderMark(std::string_view text);

bool isAsciiDigit(CodePoint code_point);
bool isAsciiLetter(CodePoint code_point);
bool isLetter(CodePoint code_point);
bool isUpperCaseLetter(CodePoint code_point);
bool isLowerCaseLetter(CodePoint code_point);
bool isNameCharacter(CodePoint code_point);

}  // namespace prologd
