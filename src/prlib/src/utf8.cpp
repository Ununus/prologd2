#include "prlib/utf8.hpp"

namespace prologd {

namespace {

// Cyrillic blocks handled explicitly so the classification does not depend on
// the process locale (which is unreliable on Windows).
constexpr CodePoint kCyrillicCapitalA = 0x0410;  // А
constexpr CodePoint kCyrillicCapitalYa = 0x042F;  // Я
constexpr CodePoint kCyrillicSmallA = 0x0430;    // а
constexpr CodePoint kCyrillicSmallYa = 0x044F;    // я
constexpr CodePoint kCyrillicCapitalYo = 0x0401;  // Ё
constexpr CodePoint kCyrillicSmallYo = 0x0451;    // ё

}  // namespace

DecodeResult decodeCodePoint(std::string_view text, std::size_t offset) {
  DecodeResult result;
  if (offset >= text.size()) {
    result.valid = false;
    result.length = 0;
    return result;
  }
  const auto byte = static_cast<unsigned char>(text[offset]);
  if (byte < 0x80) {
    result.code_point = byte;
    result.length = 1;
    result.valid = true;
    return result;
  }
  std::size_t length = 0;
  CodePoint code_point = 0;
  if ((byte & 0xE0) == 0xC0) {
    length = 2;
    code_point = byte & 0x1Fu;
  } else if ((byte & 0xF0) == 0xE0) {
    length = 3;
    code_point = byte & 0x0Fu;
  } else if ((byte & 0xF8) == 0xF0) {
    length = 4;
    code_point = byte & 0x07u;
  } else {
    // Continuation byte or invalid lead: fall back to Latin-1.
    result.code_point = byte;
    result.length = 1;
    result.valid = false;
    return result;
  }
  if (offset + length > text.size()) {
    result.code_point = byte;
    result.length = 1;
    result.valid = false;
    return result;
  }
  for (std::size_t i = 1; i < length; ++i) {
    const auto continuation = static_cast<unsigned char>(text[offset + i]);
    if ((continuation & 0xC0) != 0x80) {
      result.code_point = byte;
      result.length = 1;
      result.valid = false;
      return result;
    }
    code_point = (code_point << 6) | (continuation & 0x3Fu);
  }
  result.code_point = code_point;
  result.length = length;
  result.valid = true;
  return result;
}

std::vector<CodePoint> utf8Decode(std::string_view text) {
  std::vector<CodePoint> result;
  result.reserve(text.size());
  std::size_t offset = 0;
  while (offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    if (decoded.length == 0) {
      break;
    }
    result.push_back(decoded.code_point);
    offset += decoded.length;
  }
  return result;
}

std::string utf8Encode(CodePoint code_point) {
  std::string result;
  if (code_point <= 0x7F) {
    result.push_back(static_cast<char>(code_point));
  } else if (code_point <= 0x7FF) {
    result.push_back(static_cast<char>(0xC0 | (code_point >> 6)));
    result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
  } else if (code_point <= 0xFFFF) {
    result.push_back(static_cast<char>(0xE0 | (code_point >> 12)));
    result.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
    result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
  } else {
    result.push_back(static_cast<char>(0xF0 | (code_point >> 18)));
    result.push_back(static_cast<char>(0x80 | ((code_point >> 12) & 0x3F)));
    result.push_back(static_cast<char>(0x80 | ((code_point >> 6) & 0x3F)));
    result.push_back(static_cast<char>(0x80 | (code_point & 0x3F)));
  }
  return result;
}

bool utf8IsValid(std::string_view text) {
  std::size_t offset = 0;
  while (offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    if (!decoded.valid || decoded.length == 0) {
      return false;
    }
    offset += decoded.length;
  }
  return true;
}

std::size_t utf8Length(std::string_view text) {
  std::size_t count = 0;
  std::size_t offset = 0;
  while (offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    if (decoded.length == 0) {
      break;
    }
    offset += decoded.length;
    ++count;
  }
  return count;
}

std::string utf8FromCodePoints(const std::vector<CodePoint>& code_points) {
  std::string result;
  result.reserve(code_points.size());
  for (CodePoint code_point : code_points) {
    result += utf8Encode(code_point);
  }
  return result;
}

std::size_t utf8ByteOffset(std::string_view text, std::size_t index) {
  std::size_t offset = 0;
  std::size_t current = 0;
  while (offset < text.size() && current < index) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    if (decoded.length == 0) {
      break;
    }
    offset += decoded.length;
    ++current;
  }
  return offset;
}

std::string utf8Substr(std::string_view text, std::size_t start, std::size_t count) {
  const std::size_t begin = utf8ByteOffset(text, start);
  if (begin >= text.size()) {
    return {};
  }
  const std::size_t end = utf8ByteOffset(text, start + count);
  return std::string(text.substr(begin, end - begin));
}

std::string_view stripByteOrderMark(std::string_view text) {
  constexpr std::string_view kBom = "\xEF\xBB\xBF";
  if (text.size() >= kBom.size() && text.substr(0, kBom.size()) == kBom) {
    return text.substr(kBom.size());
  }
  return text;
}

bool isAsciiDigit(CodePoint code_point) { return code_point >= U'0' && code_point <= U'9'; }

bool isAsciiLetter(CodePoint code_point) {
  return (code_point >= U'A' && code_point <= U'Z') ||
         (code_point >= U'a' && code_point <= U'z');
}

bool isUpperCaseLetter(CodePoint code_point) {
  if (code_point >= U'A' && code_point <= U'Z') {
    return true;
  }
  if (code_point == kCyrillicCapitalYo) {
    return true;
  }
  return code_point >= kCyrillicCapitalA && code_point <= kCyrillicCapitalYa;
}

bool isLowerCaseLetter(CodePoint code_point) {
  if (code_point >= U'a' && code_point <= U'z') {
    return true;
  }
  if (code_point == kCyrillicSmallYo) {
    return true;
  }
  return code_point >= kCyrillicSmallA && code_point <= kCyrillicSmallYa;
}

bool isLetter(CodePoint code_point) {
  if (isAsciiLetter(code_point) || isUpperCaseLetter(code_point) ||
      isLowerCaseLetter(code_point)) {
    return true;
  }
  // Treat other Latin/Greek/etc. letters as letters when they are not
  // punctuation or symbols; this keeps e.g. accented names usable as atoms.
  return (code_point >= 0x00C0 && code_point <= 0x024F);
}

bool isNameCharacter(CodePoint code_point) {
  return isLetter(code_point) || isAsciiDigit(code_point) || code_point == U'_';
}

std::string upperCaseFirst(std::string_view name) {
  const DecodeResult first = decodeCodePoint(name, 0);
  if (!first.valid || !isLowerCaseLetter(first.code_point)) {
    return std::string(name);
  }
  CodePoint upper = first.code_point;
  if (upper >= U'a' && upper <= U'z') {
    upper = upper - U'a' + U'A';
  } else if (upper == kCyrillicSmallYo) {
    upper = kCyrillicCapitalYo;
  } else {
    upper = upper - kCyrillicSmallA + kCyrillicCapitalA;
  }
  return utf8Encode(upper) + std::string(name.substr(first.length));
}

}  // namespace prologd
