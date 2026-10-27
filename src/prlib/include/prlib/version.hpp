#pragma once

#include <string>
#include <string_view>

namespace prologd {

/// What the program calls itself on the command line: `prologd`, injected by CMake.
std::string_view productName();

/// Semantic version of the interpreter, injected by CMake.
std::string_view versionString();

/// The day the release was cut, `YYYY-MM-DD`, injected by CMake.
///
/// A *release* date and not a build date: `--version` has to be the same string on
/// every machine that builds the same tag.
std::string_view releaseDateString();

/// `prologd 2.6.1 (2026-10-25)` — what `--version` prints.
std::string versionBanner();

/// The version the *language* reports through `ВЕРСИЯ`.
///
/// It does not follow the interpreter's own version and never will: the number is
/// part of the dialect as the course's programs know it, and a lesson that prints it
/// has to keep printing it after a release.  `2.6.1` is what the program is;
/// `27.1` is what the language is.
inline constexpr std::string_view kDialectVersion = "27.1";

}  // namespace prologd
