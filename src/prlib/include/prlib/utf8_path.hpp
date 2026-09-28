#pragma once

#include <filesystem>
#include <string>
#include <string_view>

namespace prologd {

/// Build a filesystem path from a UTF-8 string.
///
/// On POSIX the bytes are used as-is.  On Windows the native narrow encoding is
/// not UTF-8, so the string is converted through `char8_t`/`std::filesystem`,
/// which performs the UTF-8 to UTF-16 conversion.  Use this helper for every
/// path that comes from user input (file names, `ИМПОРТ` arguments, command
/// line arguments).
inline std::filesystem::path fromUtf8Path(std::string_view text) {
#if defined(_WIN32)
  const auto* bytes = reinterpret_cast<const char8_t*>(text.data());
  return std::filesystem::path(std::u8string(bytes, text.size()));
#else
  return std::filesystem::path(text);
#endif
}

}  // namespace prologd
