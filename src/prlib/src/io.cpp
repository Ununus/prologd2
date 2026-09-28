#include "prlib/io.hpp"

#include <utility>

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
  at_line_start_ = text.back() == '\n';
}

void IoContext::newline() {
  *output_ << '\n';
  output_->flush();
  at_line_start_ = true;
}

void IoContext::pushPreloadedLine(std::string line) { preloaded_.push_back(std::move(line)); }

bool IoContext::fetchLine(std::string& line) {
  if (!preloaded_.empty()) {
    line = std::move(preloaded_.front());
    preloaded_.pop_front();
    return true;
  }
  if (input_from_file_) {
    return static_cast<bool>(std::getline(file_input_, line));
  }
  return static_cast<bool>(std::getline(*base_input_, line));
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
    if (!fetchLine(line)) {
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
  if (!fetchLine(line)) {
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
    if (!fetchLine(line)) {
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
  if (path.empty() || path == "con:" || path == "con") {
    return true;
  }
  file_input_.open(path);
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
  if (path.empty() || path == "con:" || path == "con") {
    output_ = base_output_;
    return true;
  }
  file_output_.open(path);
  if (!file_output_.is_open()) {
    return false;
  }
  output_to_file_ = true;
  output_name_ = path;
  output_ = &file_output_;
  return true;
}

}  // namespace prologd
