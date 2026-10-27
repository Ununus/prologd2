#include "prlib/formatter.hpp"

#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "prlib/lexer.hpp"
#include "prlib/parser.hpp"
#include "prlib/utf8.hpp"

namespace prologd {

namespace {

constexpr std::size_t kNone = static_cast<std::size_t>(-1);

using TokenList = std::vector<Token>;

// ---------------------------------------------------------------------------
// Text helpers
// ---------------------------------------------------------------------------

std::size_t codePointCount(std::string_view text) {
  std::size_t count = 0;
  std::size_t offset = 0;
  while (offset < text.size()) {
    const DecodeResult decoded = decodeCodePoint(text, offset);
    offset += decoded.valid && decoded.length != 0 ? decoded.length : 1;
    ++count;
  }
  return count;
}

bool isHorizontalSpace(char ch) {
  return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\f' || ch == '\v';
}

std::string_view trimRight(std::string_view text) {
  while (!text.empty() && isHorizontalSpace(text.back())) {
    text.remove_suffix(1);
  }
  return text;
}

bool isBlankLine(std::string_view text) {
  for (const char ch : text) {
    if (!isHorizontalSpace(ch)) {
      return false;
    }
  }
  return true;
}

/// True when a gap holds a blank line of its own.  The first line of a gap
/// continues the line the previous token ended on, and the last one is the
/// indentation in front of the next token — neither is a blank line the author
/// left between two goals.
bool hasInteriorBlank(std::string_view gap) {
  std::size_t line_count = 1;
  for (const char ch : gap) {
    if (ch == '\n') {
      ++line_count;
    }
  }
  if (line_count < 3) {
    return false;
  }
  std::size_t line_start = 0;
  std::size_t line_number = 0;
  for (std::size_t i = 0; i <= gap.size(); ++i) {
    if (i != gap.size() && gap[i] != '\n') {
      continue;
    }
    const std::string_view line = gap.substr(line_start, i - line_start);
    line_start = i + 1;
    ++line_number;
    if (line_number == 1 || line_number == line_count) {
      continue;
    }
    if (isBlankLine(line)) {
      return true;
    }
  }
  return false;
}

/// The comment of a gap line, from its `%` to the end of the line.  Empty when
/// the line has none.  Between two tokens there is nothing but whitespace and
/// comments, so the first `%` of such a line starts a comment.
std::string_view commentOf(std::string_view line) {
  const std::size_t percent = line.find('%');
  return percent == std::string_view::npos ? std::string_view{} : line.substr(percent);
}

/// The raw span of a token in the source.  Every kind but a string and a quoted
/// atom copies its lexeme into `text`, so the text *is* the raw bytes; those two
/// are decoded (escapes and doubled quotes), so their span is measured again.
std::size_t rawLength(std::string_view source, std::size_t begin, const Token& token) {
  if (token.kind == TokenKind::String || token.kind == TokenKind::QuotedAtom) {
    const char quote = token.kind == TokenKind::String ? '"' : '\'';
    // A string constant of the old dialect is a bare capitalised name with no
    // quotes at all (task_67, modes 1 and 2).  Scanning for a quote there ran to
    // the next one in the file — or to the end of the line — and the formatted
    // text grew by an order of magnitude; the decoded text *is* the raw name.
    if (begin >= source.size() || source[begin] != quote) {
      return token.text.size();
    }
    const bool doubled = token.kind == TokenKind::QuotedAtom;
    std::size_t i = begin + 1;
    while (i < source.size()) {
      const char ch = source[i];
      if (doubled) {
        if (ch == '\'' && i + 1 < source.size() && source[i + 1] == '\'') {
          i += 2;
          continue;
        }
      } else if (ch == '\\' && i + 1 < source.size() &&
                 (source[i + 1] == '"' || source[i + 1] == '\\')) {
        i += 2;
        continue;
      }
      ++i;
      if (ch == quote || ch == '\n') {
        break;
      }
    }
    return i - begin;
  }
  return token.text.size();
}

/// Line starts of the source, so a `SourceLocation` (bytes within its line)
/// becomes a byte offset.
struct LineStarts {
  std::vector<std::size_t> starts{0};

  static LineStarts of(std::string_view text) {
    LineStarts table;
    for (std::size_t i = 0; i < text.size(); ++i) {
      if (text[i] == '\n') {
        table.starts.push_back(i + 1);
      }
    }
    return table;
  }

  [[nodiscard]] std::size_t offset(const SourceLocation& location) const {
    if (location.line == 0 || location.line > starts.size()) {
      return 0;
    }
    return starts[location.line - 1] + (location.column > 0 ? location.column - 1 : 0);
  }
};

// ---------------------------------------------------------------------------
// The text being built, with its current column
// ---------------------------------------------------------------------------

class Builder {
 public:
  void append(std::string_view text) {
    text_.append(text);
    const std::size_t newline = text.rfind('\n');
    if (newline == std::string_view::npos) {
      column_ += codePointCount(text);
    } else {
      column_ = codePointCount(text.substr(newline + 1));
    }
  }

  void append(char ch) { append(std::string_view(&ch, 1)); }

  void newline(std::string_view indent = {}) {
    text_ += '\n';
    text_ += indent;
    column_ = codePointCount(indent);
  }

  [[nodiscard]] std::size_t column() const { return column_; }
  [[nodiscard]] bool empty() const { return text_.empty(); }
  [[nodiscard]] std::string take() { return std::move(text_); }

 private:
  std::string text_;
  std::size_t column_ = 0;
};

/// No trailing whitespace survives, and no `\r` either.
std::string stripLineEnds(std::string text) {
  std::string out;
  out.reserve(text.size());
  std::size_t line_start = 0;
  for (std::size_t i = 0; i <= text.size(); ++i) {
    if (i != text.size() && text[i] != '\n') {
      continue;
    }
    out.append(trimRight(std::string_view(text).substr(line_start, i - line_start)));
    if (i < text.size()) {
      out += '\n';
    }
    line_start = i + 1;
  }
  return out;
}

/// The last cleanup a whole document gets: no trailing whitespace, exactly one
/// newline at the end.
std::string tidyUp(std::string text) {
  std::string out = stripLineEnds(std::move(text));
  while (!out.empty() && out.back() == '\n') {
    out.pop_back();
  }
  if (!out.empty()) {
    out += '\n';
  }
  return out;
}

// ---------------------------------------------------------------------------
// One statement of the token stream
// ---------------------------------------------------------------------------

struct Statement {
  std::size_t first = 0;
  /// The final dot, or — for a fragment that breaks off mid-body — the last
  /// token there is.
  std::size_t last = 0;
  bool terminated = false;
  bool directive = false;     ///< starts with `:-` (a directive)
  bool query = false;         ///< starts with `?`
  std::size_t colon = kNone;  ///< the `:-`/`<-` of a clause
  std::size_t body_begin = kNone;  ///< first token of the first goal
  /// Top-level `,`/`;` of the body: the points a line may break at.
  std::vector<std::size_t> separators;
};

// ---------------------------------------------------------------------------
// The formatter proper
// ---------------------------------------------------------------------------

class Formatter {
 public:
  Formatter(std::string_view source, const FormatOptions& options)
      : source_(source), options_(options) {
    const std::string unit = options.indent_unit == IndentUnit::Tab ? "\t" : "    ";
    for (std::size_t i = 0; i < options.indent_steps; ++i) {
      indent_ += unit;
    }
  }

  /// Lays out the statements of `tokens`, and the comments between them.  The
  /// bytes from `end_offset` on are *not* touched: a fragment is formatted up
  /// to its cut, and the rest is somebody else's business (the caller copies
  /// it).
  std::string run(const TokenList& tokens, std::size_t end_offset) {
    tokens_ = &tokens;
    begin_.resize(tokens.size());
    end_.resize(tokens.size());
    const LineStarts lines = LineStarts::of(source_);
    for (std::size_t i = 0; i < tokens.size(); ++i) {
      begin_[i] = lines.offset(tokens[i].location);
      end_[i] = begin_[i] + rawLength(source_, begin_[i], tokens[i]);
    }
    statements_ = buildStatements();
    for (std::size_t s = 0; s < statements_.size(); ++s) {
      const Statement& statement = statements_[s];
      if (s == 0) {
        emitLeadGap(0, begin_[statement.first], /*at_start=*/true, /*at_eof=*/false);
      } else {
        const Statement& previous = statements_[s - 1];
        emitLeadGap(end_[previous.last], begin_[statement.first], /*at_start=*/false,
                    /*at_eof=*/false);
      }
      emitStatement(s);
    }
    const std::size_t tail_from = statements_.empty() ? 0 : end_[statements_.back().last];
    if (tail_from < end_offset) {
      // With no statements the whole text is this gap, so its first line is
      // content too — not the continuation of a line no statement ended.
      emitLeadGap(tail_from, end_offset, /*at_start=*/statements_.empty(), /*at_eof=*/true);
    }
    return builder_.take();
  }

 private:
  [[nodiscard]] std::string_view tokenText(std::size_t index) const {
    return source_.substr(begin_[index], end_[index] - begin_[index]);
  }

  /// The bytes between two adjacent tokens: whitespace, and comments.
  [[nodiscard]] std::string_view gapBetween(std::size_t left, std::size_t right) const {
    return source_.substr(end_[left], begin_[right] - end_[left]);
  }

  /// Splits the tokens into statements; the last one has no dot when the text
  /// is a fragment that breaks off in the middle of a body.
  std::vector<Statement> buildStatements() const {
    std::vector<Statement> statements;
    const TokenList& tokens = *tokens_;
    std::size_t i = 0;
    while (i < tokens.size()) {
      if (tokens[i].kind == TokenKind::EndOfFile) {
        // The end-of-file marker is not a statement.  Counted as one, it made
        // the text after the last real dot a *gap between statements*, whose
        // last line is «the indentation of the next statement» — and that line
        // was dropped: a file whose last line has no newline lost its last
        // comment (task_114).
        break;
      }
      Statement statement;
      statement.first = i;
      statement.directive = tokens[i].kind == TokenKind::ColonDash;
      statement.query = tokens[i].kind == TokenKind::Question;
      std::size_t depth = 0;
      bool in_hash = false;
      std::size_t colon = kNone;
      std::size_t dot = kNone;
      for (std::size_t j = i; j < tokens.size(); ++j) {
        const TokenKind kind = tokens[j].kind;
        if (kind == TokenKind::Hash) {
          in_hash = !in_hash;
        } else if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
          ++depth;
        } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
          depth = depth > 0 ? depth - 1 : 0;
        } else if (!in_hash && depth == 0) {
          if (kind == TokenKind::Dot) {
            dot = j;
            break;
          }
          if (j != i && colon == kNone &&
              (kind == TokenKind::ColonDash || kind == TokenKind::Arrow)) {
            colon = j;
          }
        }
      }
      statement.terminated = dot != kNone;
      statement.last = dot != kNone ? dot : tokens.size() - 1;
      if (statement.directive) {
        statement.colon = i;
        statement.body_begin = i + 1;
      } else if (statement.query) {
        statement.body_begin = i + 1;
      } else if (colon != kNone) {
        statement.colon = colon;
        statement.body_begin = colon + 1;
      }
      const std::size_t body_end = statement.terminated ? statement.last : tokens.size();
      if (statement.body_begin != kNone && statement.body_begin < body_end) {
        std::size_t body_depth = 0;
        bool body_hash = false;
        for (std::size_t j = statement.body_begin; j < body_end; ++j) {
          const TokenKind kind = tokens[j].kind;
          if (kind == TokenKind::Hash) {
            body_hash = !body_hash;
          } else if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
            ++body_depth;
          } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
            body_depth = body_depth > 0 ? body_depth - 1 : 0;
          } else if (!body_hash && body_depth == 0 &&
                     (kind == TokenKind::Comma || kind == TokenKind::Semicolon ||
                      kind == TokenKind::IfThen)) {
            statement.separators.push_back(j);
          }
        }
      }
      statements.push_back(std::move(statement));
      i = dot != kNone ? dot + 1 : tokens.size();
    }
    return statements;
  }

  // ---- gaps --------------------------------------------------------------

  /// The text between two statements — and before the first, and after the
  /// last.  Comments stay on lines of their own, runs of blank lines collapse
  /// into one blank line, and nothing else survives.
  void emitLeadGap(std::size_t from, std::size_t to, bool at_start, bool at_eof) {
    if (to <= from) {
      return;
    }
    const std::string_view text = source_.substr(from, to - from);
    std::vector<std::string> comments;
    std::vector<bool> blank_before;
    bool pending_blank = false;
    std::size_t line_start = 0;
    std::size_t line_number = 0;
    std::size_t line_count = 1;
    for (const char ch : text) {
      if (ch == '\n') {
        ++line_count;
      }
    }
    for (std::size_t i = 0; i <= text.size(); ++i) {
      if (i != text.size() && text[i] != '\n') {
        continue;
      }
      const std::string_view line = text.substr(line_start, i - line_start);
      line_start = i + 1;
      ++line_number;
      if (line_number == 1 && !at_start) {
        // The rest of the line the previous statement ended on: a trailing
        // comment can live there, and stays there.
        const std::string_view comment = commentOf(line);
        if (!comment.empty()) {
          builder_.append(' ');
          builder_.append(trimRight(comment));
        }
        continue;
      }
      if (line_number == line_count && !at_eof) {
        // The last part of a gap between statements is the beginning of the
        // next statement's line: indentation, not a blank line.  At the end of
        // the text there is no next statement — the line is content, and a file
        // that does not end with a newline kept all but its last comment
        // (task_114).
        break;
      }
      if (isBlankLine(line)) {
        pending_blank = true;
        continue;
      }
      comments.push_back(std::string(trimRight(line)));
      blank_before.push_back(pending_blank);
      pending_blank = false;
    }
    if (!builder_.empty()) {
      builder_.newline();
    }
    for (std::size_t i = 0; i < comments.size(); ++i) {
      if (blank_before[i]) {
        builder_.newline();
      }
      builder_.append(comments[i]);
      builder_.newline();
    }
    if (!at_eof && pending_blank) {
      builder_.newline();
    }
  }

  /// A gap that must be broken: the comments of the gap each go on a line of
  /// their own, one blank line is kept, and then the goal starts, indented.
  /// The builder is left at the beginning of the goal's line.
  void emitBrokenGap(std::size_t left, std::size_t right) {
    const std::string_view gap = gapBetween(left, right);
    std::vector<std::string> comments;
    std::vector<bool> blank_before;
    bool pending_blank = false;
    std::size_t line_start = 0;
    std::size_t line_number = 0;
    std::size_t line_count = 1;
    for (const char ch : gap) {
      if (ch == '\n') {
        ++line_count;
      }
    }
    for (std::size_t i = 0; i <= gap.size(); ++i) {
      if (i != gap.size() && gap[i] != '\n') {
        continue;
      }
      const std::string_view line = gap.substr(line_start, i - line_start);
      line_start = i + 1;
      ++line_number;
      if (line_number == 1) {
        // The rest of the separator's own line: a trailing comment.
        const std::string_view comment = commentOf(line);
        if (!comment.empty()) {
          builder_.append(' ');
          builder_.append(trimRight(comment));
        }
        continue;
      }
      if (line_number == line_count) {
        break;  // the indentation in front of the next goal
      }
      if (isBlankLine(line)) {
        pending_blank = true;
        continue;
      }
      const std::string_view comment = commentOf(line);
      if (comment.empty()) {
        continue;
      }
      comments.push_back(std::string(trimRight(comment)));
      blank_before.push_back(pending_blank);
      pending_blank = false;
    }
    builder_.newline();
    for (std::size_t i = 0; i < comments.size(); ++i) {
      if (blank_before[i]) {
        builder_.newline();
      }
      builder_.append(indent_);
      builder_.append(comments[i]);
      builder_.newline();
    }
    if (pending_blank) {
      builder_.newline();
    }
    builder_.append(indent_);
  }

  /// True when the goal `[begin, end)` fits into what is left of the line,
  /// counting the `,`/`.` that follows it.  A goal that carries a line break of
  /// its own is left exactly as it is.
  bool goalFits(std::size_t begin, std::size_t end, std::size_t column,
                std::size_t before) const {
    std::size_t length = before;
    for (std::size_t i = begin; i < end; ++i) {
      if (i != begin) {
        const std::string_view gap = gapBetween(i - 1, i);
        if (gap.find('\n') != std::string_view::npos) {
          return true;
        }
        length += codePointCount(gap);
      }
      length += codePointCount(tokenText(i));
    }
    length += 1;  // the `,` or the `.` that closes the goal
    return column + length <= options_.width;
  }

  // ---- statements --------------------------------------------------------

  void emitStatement(std::size_t index) {
    const Statement& statement = statements_[index];
    if (statement.query) {
      builder_.append("?");
      emitFirstBodyGap(statement);
      emitGoals(statement);
      return;
    }
    if (statement.directive) {
      builder_.append(tokenText(statement.first));  // `:-`
      emitFirstBodyGap(statement);
      emitGoals(statement);
      return;
    }
    if (statement.colon == kNone) {
      const std::size_t last_token =
          statement.terminated ? statement.last - 1 : statement.last;
      if (last_token >= statement.first) {
        emitTokenRange(statement.first, last_token);
      }
      if (statement.terminated) {
        emitDot(statement);
      }
      return;
    }
    if (statement.colon > statement.first) {
      emitTokenRange(statement.first, statement.colon - 1);
    }
    builder_.append(tokenText(statement.colon));
    emitFirstBodyGap(statement);
    emitGoals(statement);
  }

  void emitTokenRange(std::size_t a, std::size_t b) {
    for (std::size_t i = a; i <= b; ++i) {
      if (i != a) {
        builder_.append(gapBetween(i - 1, i));
      }
      builder_.append(tokenText(i));
    }
  }

  /// The gap between `:-`/`?` and the first goal.  The corpus writes a clause
  /// glued (`голова:-тело`), a query glued (`?цель`), and a directive with one
  /// space (`:- ИМПОРТ(...)`).  «Мягкое» joins here too, breaking only when the
  /// line would not fit; a comment and a blank line the author left force the
  /// break in every mode but «в одну строку».
  ///
  /// «Жёсткое» breaks here as well **when the statement has a head**: the head
  /// stands alone and every goal of the body gets a line of its own, so the first
  /// goal is not the one glued to the head where a reader skips it (task_47).  A
  /// directive and a query have no head, and `:-` or `?` alone on a line is noise,
  /// so they keep their single space — and they keep their line: neither the soft
  /// nor the hard mode breaks a query or a directive at all (`emitGoalGap`).
  void emitFirstBodyGap(const Statement& statement) {
    const std::size_t body_end = statement.terminated ? statement.last : tokens_->size();
    if (statement.body_begin == kNone || statement.body_begin >= body_end) {
      return;
    }
    const std::size_t after = statement.body_begin - 1;
    const std::string join = statement.directive ? " " : "";
    const std::string_view gap = gapBetween(after, statement.body_begin);
    const bool has_comment = gap.find('%') != std::string_view::npos;
    const bool has_blank = hasInteriorBlank(gap);
    const bool has_head = !statement.directive && !statement.query;
    bool broken = has_comment;
    if (options_.mode == FormatMode::Soft && !statement.query && !statement.directive &&
        (has_blank || !goalFits(statement.body_begin, goalEnd(statement, 0),
                                builder_.column(), join.size()))) {
      broken = true;
    }
    if (options_.mode == FormatMode::Hard && (has_blank || has_head)) {
      broken = true;
    }
    if (!broken) {
      builder_.append(join);
      return;
    }
    emitBrokenGap(after, statement.body_begin);
  }

  /// The token one past the last token of the goal that `statement` lists as
  /// its `ordinal`-th.
  [[nodiscard]] std::size_t goalEnd(const Statement& statement,
                                    std::size_t ordinal) const {
    if (ordinal < statement.separators.size()) {
      return statement.separators[ordinal];
    }
    return statement.terminated ? statement.last : tokens_->size();
  }

  void emitGoals(const Statement& statement) {
    const std::size_t body_end = statement.terminated ? statement.last : tokens_->size();
    if (statement.body_begin == kNone || statement.body_begin >= body_end) {
      if (statement.terminated) {
        emitDot(statement);
      }
      return;
    }
    std::size_t goal_start = statement.body_begin;
    for (std::size_t s = 0; s <= statement.separators.size(); ++s) {
      const std::size_t separator =
          s < statement.separators.size() ? statement.separators[s] : kNone;
      const std::size_t goal_end = separator != kNone ? separator : body_end;
      if (goal_start < goal_end) {
        emitTokenRange(goal_start, goal_end - 1);
      }
      if (separator == kNone) {
        break;
      }
      if ((*tokens_)[separator].kind == TokenKind::Semicolon ||
          (*tokens_)[separator].kind == TokenKind::IfThen) {
        builder_.append(' ');
      }
      builder_.append(tokenText(separator));
      const std::size_t next_goal = separator + 1;
      if (next_goal >= body_end) {
        break;
      }
      const bool fits =
          goalFits(next_goal, goalEnd(statement, s + 1), builder_.column(), 1);
      emitGoalGap(separator, next_goal, fits, statement.query || statement.directive);
      goal_start = next_goal;
    }
    if (statement.terminated) {
      emitDot(statement);
    }
  }

  /// The gap after a separator.  This is where the modes part: «жёсткое»
  /// breaks at every separator, «в одну строку» joins whatever it can and lets
  /// the line be as long as it wants, and «мягкое» builds the line again —
  /// goals are packed up to the width, and only a comment, a blank line the
  /// author left or the width itself forces a break.
  ///
  /// The author's own single newlines are *not* kept in the soft mode: they
  /// cannot be told apart from the ones this formatter wrote itself, and keeping
  /// them is exactly what used to make «из жёсткого обратно в мягкое» impossible.
  /// Rebuilding the lines makes the soft shape canonical, so formatting a hard
  /// layout with it converts the program back.
  ///
  /// `single_line` marks a query or a directive.  Neither has a head or a body
  /// to lay out — one is a question, the other an instruction — and the tools
  /// that run them read a *line*: the window's margin marker is line-local by
  /// design (task_36), so a break inside a query is a question nobody can click.
  /// The width therefore never opens them; a comment or a blank line the author
  /// left still does (task_47).
  void emitGoalGap(std::size_t separator, std::size_t next_goal, bool fits,
                   bool single_line) {
    const std::string_view gap = gapBetween(separator, next_goal);
    const bool has_comment = gap.find('%') != std::string_view::npos;
    bool broken = false;
    switch (options_.mode) {
      case FormatMode::Hard:
        broken = !single_line;
        break;
      case FormatMode::Line:
        broken = has_comment;
        break;
      case FormatMode::None:
      case FormatMode::Soft:
        broken = has_comment || hasInteriorBlank(gap) || (!single_line && !fits);
        break;
    }
    if (!broken) {
      builder_.append(' ');
      return;
    }
    emitBrokenGap(separator, next_goal);
  }

  /// The dot that closes a statement: the whitespace in front of it is dropped,
  /// a comment stays where the author put it.
  void emitDot(const Statement& statement) {
    if (statement.last > statement.first) {
      const std::string_view gap = gapBetween(statement.last - 1, statement.last);
      const std::string_view comment = commentOf(gap);
      if (!comment.empty()) {
        builder_.append(' ');
        builder_.append(trimRight(comment));
        builder_.newline(indent_);
      }
    }
    builder_.append(tokenText(statement.last));
  }

  std::string_view source_;
  FormatOptions options_;
  std::string indent_;
  const TokenList* tokens_ = nullptr;
  std::vector<std::size_t> begin_;
  std::vector<std::size_t> end_;
  std::vector<Statement> statements_;
  Builder builder_;
};

// ---------------------------------------------------------------------------
// The pieces `formatSource` works with
// ---------------------------------------------------------------------------

struct Lexed {
  DiagnosticSink sink;
  TokenList tokens;
  bool parses = false;
};

Lexed lexAndParse(std::string_view text, const std::string& name, VariableMode mode) {
  Lexed out;
  LexerOptions lexer_options;
  lexer_options.variables = mode;
  Lexer lexer(text, name, lexer_options);
  out.tokens = lexer.tokenize(out.sink);
  Parser parser(out.tokens,
                [count = VarId{0}](std::string_view) mutable { return ++count; },
                &out.sink);
  const ParsedProgram parsed = parser.parseProgram();
  out.parses = parsed.ok && !out.sink.hasErrors();
  return out;
}

/// Where every token starts in `source`.
std::vector<std::size_t> tokenBegins(const TokenList& tokens, std::string_view source) {
  std::vector<std::size_t> begins(tokens.size(), 0);
  const LineStarts lines = LineStarts::of(source);
  for (std::size_t i = 0; i < tokens.size(); ++i) {
    begins[i] = lines.offset(tokens[i].location);
  }
  return begins;
}

}  // namespace

FormatResult formatSource(std::string_view text, const FormatOptions& options) {
  FormatResult result;
  result.text = std::string(text);
  if (options.mode == FormatMode::None || text.empty()) {
    return result;
  }
  // A block comment can sit in the middle of a goal, where the layout pass
  // copies a gap and would drop it.  Until the formatter knows how to carry
  // one, a text that has `/*` is left exactly as it is written (task_92) — no
  // comment is ever lost, and the file keeps the shape its author gave it.
  if (text.find("/*") != std::string_view::npos) {
    return result;
  }
  const std::string_view source = stripByteOrderMark(text);
  // A file may say how its names are read in its first line (task_67), and that
  // line wins over the mode of the run — the same order the loader uses.  The
  // marker stays in the text: it is an ordinary statement, and the file keeps it
  // as its first line.
  VariableMode mode = options.variables;
  if (const auto marker = readVariableMarker(source)) {
    mode = marker->first;
  }
  Lexed lexed = lexAndParse(source, options.source_name, mode);
  result.diagnostics = lexed.sink.diagnostics();
  if (!lexed.parses && !options.selection_only) {
    return result;  // byte for byte, with the diagnostics
  }
  if (lexed.parses) {
    Formatter formatter(source, options);
    result.text = tidyUp(formatter.run(lexed.tokens, source.size()));
    result.changed = result.text != std::string(text);
    return result;
  }

  // A fragment whose last statement breaks off in the middle of a body.  What
  // parses is formatted, the rest is copied as it stands — so the cut has to
  // leave a parsable prefix behind, and the search walks the fragment's
  // top-level separators from the right.
  const std::vector<std::size_t> begins = tokenBegins(lexed.tokens, source);
  std::size_t last_dot = kNone;
  std::size_t depth = 0;
  bool in_hash = false;
  for (std::size_t i = 0; i < lexed.tokens.size(); ++i) {
    const TokenKind kind = lexed.tokens[i].kind;
    if (kind == TokenKind::Hash) {
      in_hash = !in_hash;
    } else if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
      ++depth;
    } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
      depth = depth > 0 ? depth - 1 : 0;
    } else if (kind == TokenKind::Dot && !in_hash && depth == 0) {
      last_dot = i;
    }
  }
  std::vector<std::size_t> cuts;
  depth = 0;
  in_hash = false;
  for (std::size_t i = last_dot == kNone ? 0 : last_dot + 1; i < lexed.tokens.size(); ++i) {
    const TokenKind kind = lexed.tokens[i].kind;
    if (kind == TokenKind::Hash) {
      in_hash = !in_hash;
    } else if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
      ++depth;
    } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
      depth = depth > 0 ? depth - 1 : 0;
    } else if (!in_hash && depth == 0 &&
               (kind == TokenKind::Comma || kind == TokenKind::Semicolon ||
                kind == TokenKind::IfThen)) {
      cuts.push_back(i);
    }
  }
  for (auto it = cuts.rbegin(); it != cuts.rend(); ++it) {
    const std::size_t cut = begins[*it];
    std::string candidate(source.substr(0, cut));
    candidate += '.';
    const Lexed check = lexAndParse(candidate, options.source_name, mode);
    if (!check.parses) {
      continue;
    }
    Lexed prefix = lexAndParse(source.substr(0, cut), options.source_name, mode);
    Formatter formatter(source, options);
    std::string formatted = formatter.run(prefix.tokens, cut);
    formatted += source.substr(cut);
    result.text = stripLineEnds(std::move(formatted));
    result.changed = result.text != std::string(text);
    // The fragment's own parse errors were about the part that is deliberately
    // left alone: a front-end must not report «не удалось разобрать» for a cut
    // it just handled.
    result.diagnostics.clear();
    return result;
  }
  // Nothing of the fragment is complete enough: leave it exactly as it is.
  return result;
}

}  // namespace prologd
