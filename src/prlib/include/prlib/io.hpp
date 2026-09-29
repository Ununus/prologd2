#pragma once

#include <cstddef>
#include <deque>
#include <fstream>
#include <functional>
#include <istream>
#include <optional>
#include <ostream>
#include <string>
#include <string_view>

#include "prlib/utf8.hpp"

namespace prologd {

/// What the interpreter is waiting for when it reads the interactive stream.
///
/// A front-end uses this to decide what to ask the user: a dialog for a whole
/// line, a single-character prompt, or a token field.
enum class InputRequestKind { Token, Line, CodePoint };

/// Answers one interactive read. Returning `std::nullopt` means end of input.
using InputRequestHandler = std::function<std::optional<std::string>(InputRequestKind)>;

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

  /// Route interactive reads through `handler` instead of the base input
  /// stream.  A GUI uses it to pop up an input dialog; the JSON protocol uses
  /// it to emit an `input_request` event and wait for the reply.  Redirection
  /// set up by `ЧТЕНИЕ_ИЗ` still wins, and preloaded lines are consumed first.
  /// Pass an empty function to read the base stream again.
  void setInputRequestHandler(InputRequestHandler handler);
  [[nodiscard]] bool hasInputRequestHandler() const noexcept {
    return static_cast<bool>(input_handler_);
  }

  /// Route trace text (`ТРАССА`) through `sink` instead of the output stream,
  /// one line per call, newline included.  A front-end uses it to colour the
  /// trace apart from the program's own output (the JSON protocol emits
  /// `trace` events) or to give it a pane of its own; the console leaves it
  /// unset and reads the trace in the output stream as it always has.  A set
  /// sink wins over `ЗАПИСЬ_В`, because the trace is for the reader, not for
  /// the program's output file.
  void setTraceSink(std::function<void(std::string_view)> sink);
  [[nodiscard]] bool hasTraceSink() const noexcept {
    return static_cast<bool>(trace_sink_);
  }
  /// One line of trace text, wherever it goes.
  void writeTrace(std::string_view text);

  // ---- redirection ----
  /// Switch input to `path`; empty or `con:` restores the base stream.
  bool openInput(const std::string& path);
  /// Switch output to `path`; empty or `con:` restores the base stream.
  bool openOutput(const std::string& path);
  [[nodiscard]] const std::string& inputName() const noexcept { return input_name_; }
  [[nodiscard]] const std::string& outputName() const noexcept { return output_name_; }

  [[nodiscard]] std::ostream& errorStream() noexcept { return *error_; }

 private:
  bool fetchLine(std::string& line, InputRequestKind kind);
  [[nodiscard]] static bool isSpace(char ch);

  InputRequestHandler input_handler_;
  std::function<void(std::string_view)> trace_sink_;

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
