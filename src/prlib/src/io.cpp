#include "prlib/io.hpp"

#include <utility>

#include "prlib/utf8_path.hpp"

namespace prologd {

IoContext::IoContext(std::istream& input, std::ostream& output, std::ostream& error)
    : base_input_(&input), base_output_(&output), output_(&output), error_(&error) {}

bool IoContext::isSpace(char ch) {
  return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n' || ch == '\f' || ch == '\v';
}

void IoContext::write(std::string_view text) {
  if (text.empty()) {
    return;
  }
  *output_ << text;
  output_->flush();
  const bool line_ended = text.find('\n') != std::string_view::npos;
  at_line_start_ = text.back() == '\n';
  if (line_ended && output_line_sink_) {
    output_line_sink_();
  }
}

void IoContext::newline() {
  *output_ << '\n';
  output_->flush();
  at_line_start_ = true;
  if (output_line_sink_) {
    output_line_sink_();
  }
}

void IoContext::setInputRequestHandler(InputRequestHandler handler) {
  input_handler_ = std::move(handler);
}

void IoContext::setTraceSink(std::function<void(std::string_view)> sink) {
  trace_sink_ = std::move(sink);
}

void IoContext::setOutputLineSink(std::function<void()> sink) {
  output_line_sink_ = std::move(sink);
}

void IoContext::writeTrace(std::string_view text) {
  if (trace_sink_) {
    trace_sink_(text);
    return;
  }
  write(text);
  newline();
}

bool IoContext::fetchLine(std::string& line, InputRequestKind kind) {
  if (input_from_file_) {
    if (!std::getline(file_input_, line)) {
      return false;
    }
    // A byte order mark at the very start of a stream is a marker, not data —
    // the same helper strips it from a source (Notepad writes the mark into a
    // data file just as readily).  Anywhere but the start it is text.
    if (!file_stream_started_) {
      file_stream_started_ = true;
      line.assign(stripByteOrderMark(line));
    }
    return true;
  }
  if (input_handler_) {
    return fetchChunkLine(line, kind);
  }
  if (!std::getline(*base_input_, line)) {
    return false;
  }
  if (!base_stream_started_) {
    base_stream_started_ = true;
    line.assign(stripByteOrderMark(line));
  }
  return true;
}

/// One line out of the front-end's answer (task_54).
///
/// The answer is a *piece of the input stream*, so the rules are the file's:
/// a `\n` separates lines, the end of the piece ends its last line, and the
/// separator is never text.  That is why the `\n`s do not reach `ВВОДСТР` (nor
/// code 10 `ВВКОД`), why `a\n` is one line and not one plus an empty one — the
/// next read asks the front-end instead — and why the remainder rules inside a
/// line («остаток строки») keep working: only `current_line_` above ever sees
/// a line, never the piece.
bool IoContext::fetchChunkLine(std::string& line, InputRequestKind kind) {
  if (pending_pos_ < pending_.size()) {
    // The piece in hand still has a line to give: its separator, or its end.
    const std::size_t separator = pending_.find('\n', pending_pos_);
    if (separator == std::string::npos) {
      line = pending_.substr(pending_pos_);
      pending_pos_ = pending_.size();
      return true;
    }
    std::size_t end = separator;
    if (end > pending_pos_ && pending_[end - 1] == '\r') {
      --end;  // CRLF is one separator, as it is for a file
    }
    line = pending_.substr(pending_pos_, end - pending_pos_);
    pending_pos_ = separator + 1;
    return true;
  }

  const std::optional<std::string> answer = input_handler_(kind);
  if (!answer) {
    return false;  // end of input, as before
  }
  // An answer is a stream of its own, so it may begin with a mark too.
  pending_.assign(stripByteOrderMark(*answer));
  pending_pos_ = 0;
  if (pending_.empty()) {
    // An empty answer is one empty line — the behaviour a one-line front-end
    // and a file holding an empty line already shared.
    line.clear();
    return true;
  }
  return fetchChunkLine(line, kind);
}

std::optional<std::string> IoContext::readToken() {
  for (;;) {
    if (has_current_line_) {
      while (current_pos_ < current_line_.size() && isSpace(current_line_[current_pos_])) {
        ++current_pos_;
      }
      if (current_pos_ < current_line_.size()) {
        const std::size_t begin = current_pos_;
        while (current_pos_ < current_line_.size() && !isSpace(current_line_[current_pos_])) {
          ++current_pos_;
        }
        return current_line_.substr(begin, current_pos_ - begin);
      }
    }
    std::string line;
    if (!fetchLine(line, InputRequestKind::Token)) {
      has_current_line_ = false;
      return std::nullopt;
    }
    current_line_ = std::move(line);
    current_pos_ = 0;
    has_current_line_ = true;
  }
}

std::optional<std::string> IoContext::readWholeLine() {
  if (has_current_line_ && current_pos_ < current_line_.size()) {
    std::string rest = current_line_.substr(current_pos_);
    current_pos_ = current_line_.size();
    return rest;
  }
  std::string line;
  if (!fetchLine(line, InputRequestKind::Line)) {
    has_current_line_ = false;
    return std::nullopt;
  }
  has_current_line_ = true;
  current_line_.clear();
  current_pos_ = 0;
  return line;
}

std::optional<CodePoint> IoContext::readCodePoint() {
  for (;;) {
    if (has_current_line_ && current_pos_ < current_line_.size()) {
      const DecodeResult decoded = decodeCodePoint(current_line_, current_pos_);
      if (decoded.length == 0) {
        return std::nullopt;
      }
      current_pos_ += decoded.length;
      return decoded.code_point;
    }
    std::string line;
    if (!fetchLine(line, InputRequestKind::CodePoint)) {
      has_current_line_ = false;
      return std::nullopt;
    }
    current_line_ = std::move(line);
    current_pos_ = 0;
    has_current_line_ = true;
  }
}

bool IoContext::openInput(const std::string& path) {
  file_input_.close();
  input_from_file_ = false;
  input_name_.clear();
  has_current_line_ = false;
  // Each newly opened file may begin with a mark of its own.  A piece waiting
  // from the front-end is deliberately *not* dropped: it is read again when
  // the input returns to the base stream.
  file_stream_started_ = false;
  if (path.empty() || path == "con:" || path == "con") {
    return true;
  }
  // The name arrives from the program's own text, which is UTF-8, while a narrow
  // `open` reads its argument in the process's ANSI code page: on a machine whose
  // ANSI page has no Cyrillic, `ЧТЕНИЕ_ИЗ("файл.txt")` would ask for `????.txt`.
  // The helper is what makes the name mean what it says (part 133).
  file_input_.open(fromUtf8Path(path));
  if (!file_input_.is_open()) {
    return false;
  }
  input_from_file_ = true;
  input_name_ = path;
  return true;
}

bool IoContext::openOutput(const std::string& path) {
  file_output_.close();
  output_to_file_ = false;
  output_name_.clear();
  // The stream that was just closed must not stay the current one.  A redirect
  // that fails returns the output to the base stream, the way a failed
  // `ЧТЕНИЕ_ИЗ` returns the input to the keyboard — otherwise everything written
  // afterwards (the program's own output *and* the interpreter's answers) goes
  // into a closed file and disappears without a word.
  output_ = base_output_;
  if (path.empty() || path == "con:" || path == "con") {
    return true;
  }
  file_output_.open(fromUtf8Path(path));
  if (!file_output_.is_open()) {
    return false;
  }
  output_to_file_ = true;
  output_name_ = path;
  output_ = &file_output_;
  return true;
}

}  // namespace prologd
