#pragma once

#include <cstddef>
#include <deque>
#include <fstream>
#include <istream>
#include <optional>
#include <ostream>
#include <string>
#include <string_view>

#include "prlib/utf8.hpp"

namespace prologd {

/// Stream context used by the I/O built-ins.
///
/// Keeps the "current input" and "current output" streams, which
/// `ЧТЕНИЕ_ИЗ`/`ЗАПИСЬ_В` can redirect to files.  Test code can point the base
/// streams at in-memory buffers.
class IoContext {
 public:
  IoContext(std::istream& input, std::ostream& output, std::ostream& error);

  // ---- output ----
  void write(std::string_view text);
  void newline();
  [[nodiscard]] bool atLineStart() const noexcept { return at_line_start_; }

  // ---- input ----
  /// Next whitespace-delimited token.
  std::optional<std::string> readToken();
  /// Remainder of the current line, or the next whole line.
  std::optional<std::string> readWholeLine();
  /// One Unicode code point.
  std::optional<CodePoint> readCodePoint();

  /// Preloaded input lines (the historical `$...` source feature).
  void pushPreloadedLine(std::string line);

  // ---- redirection ----
  /// Switch input to `path`; empty or `con:` restores the base stream.
  bool openInput(const std::string& path);
  /// Switch output to `path`; empty or `con:` restores the base stream.
  bool openOutput(const std::string& path);
  [[nodiscard]] const std::string& inputName() const noexcept { return input_name_; }
  [[nodiscard]] const std::string& outputName() const noexcept { return output_name_; }

  [[nodiscard]] std::ostream& errorStream() noexcept { return *error_; }

 private:
  bool fetchLine(std::string& line);
  [[nodiscard]] static bool isSpace(char ch);

  std::istream* base_input_;
  std::ostream* base_output_;
  std::ostream* output_;
  std::ostream* error_;

  std::ifstream file_input_;
  std::ofstream file_output_;
  bool input_from_file_ = false;
  bool output_to_file_ = false;
  std::string input_name_;
  std::string output_name_;

  std::deque<std::string> preloaded_;
  std::string current_line_;
  std::size_t current_pos_ = 0;
  bool has_current_line_ = false;

  bool at_line_start_ = true;
};

}  // namespace prologd
