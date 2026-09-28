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

/// Render a filesystem path as a UTF-8 string.
///
/// The mirror of `fromUtf8Path`.  `path::string()` uses the native narrow
/// encoding, which on Windows is the ANSI code page: it mangles the text, or
/// throws `No mapping for the Unicode character exists...`, as soon as the
/// path holds a character the code page cannot represent (Cyrillic on a 1252
/// machine, for example).  Use this helper for every path that becomes text
/// again: error messages, log lines and identity keys.
inline std::string toUtf8Path(const std::filesystem::path& path) {
  const std::u8string bytes = path.u8string();
  return std::string(reinterpret_cast<const char*>(bytes.data()), bytes.size());
}

/// Same as `toUtf8Path`, but with '/' as the directory separator.
inline std::string toUtf8PathGeneric(const std::filesystem::path& path) {
  const std::u8string bytes = path.generic_u8string();
  return std::string(reinterpret_cast<const char*>(bytes.data()), bytes.size());
}

}  // namespace prologd
