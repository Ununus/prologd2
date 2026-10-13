#pragma once

#include <string>
#include <string_view>

namespace prologd {

/// The product the engine calls itself (task_76: «Пролог-У»), injected by CMake.
std::string_view productName();

/// Semantic version of the interpreter, injected by CMake.
std::string_view versionString();

/// Human readable build date, injected by CMake.
std::string_view buildDateString();

/// `Пролог-У 2.3.0 (2026-10-13)` — what `--version` and the built-in `ВЕРСИЯ` print.
///
/// One function for the two callers on purpose: they printed the same string before
/// it existed, in two copies, and a version bump had to find both (task_76).
std::string versionBanner();

}  // namespace prologd
