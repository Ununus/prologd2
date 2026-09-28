#pragma once

#include <cstdint>
#include <string>

namespace prologd {

/// A position in a source file, used by diagnostics and clause metadata.
struct SourceLocation {
  std::string file;
  std::uint32_t line = 1;
  std::uint32_t column = 1;

  [[nodiscard]] std::string toString() const {
    return file + ":" + std::to_string(line) + ":" + std::to_string(column);
  }
};

}  // namespace prologd
