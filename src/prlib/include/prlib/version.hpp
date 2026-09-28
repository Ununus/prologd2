#pragma once

#include <string_view>

namespace prologd {

/// Semantic version of the interpreter, injected by CMake.
std::string_view versionString();

/// Human readable build date, injected by CMake.
std::string_view buildDateString();

}  // namespace prologd
