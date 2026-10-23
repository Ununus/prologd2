#include "prlib/formatter.hpp"

#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "prlib/lexer.hpp"
#include "prlib/parser.hpp"
#include "prlib/engine.hpp"
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
// Renaming for the other naming mode (task_99)
// ---------------------------------------------------------------------------

/// True when the old dialect would read this *atom* as a variable rather than as
/// a name: its variables are one letter, or a letter with a trailing `_` (`д`,
/// `Б`, `A_`), which is exactly the shape of a one-letter atom in ISO — `?одно(а,
/// а).` asks about a constant, while the old dialect would ask about a variable
/// and answer `а=_1`.  A reserved name is a predicate in every mode, so it is
/// never one of these.
bool oldReadsAsVariableName(std::string_view name) {
  if (isReservedBuiltinName(name)) {
    return false;
  }
  const std::size_t codepoints = utf8Length(name);
  return codepoints == 1 || (codepoints == 2 && name.back() == '_');
}

/// The ISO spelling of every old-dialect variable, or the old spelling of every
/// ISO one — the map `planNames` feeds the printer with.
///
/// The rules are the lexer's, read backwards.  Into ISO: the base of a name is it
/// with the first letter up and the apostrophe off (`X'` → `X`, `var1'` → `Var1`),
/// while a name that starts with `_` is an ISO variable as it stands.  A base that
/// one variable has is printed bare; a base that several share (`X`, `x`, `X'`,
/// `x'`) is numbered in the order the variables are first written (`X_1`…`X_4`),
/// and so is a base that is a reserved name — a reserved word is a predicate, not
/// a variable, in ISO.  Back into the old dialect is simpler: one letter, a letter with
/// a trailing `_` and `_имя` are variables in both, and everything else gets the
/// apostrophe that makes it one there.
std::unordered_map<std::string, std::string> variableNames(const TokenList& tokens,
                                                           VariableMode from,
                                                           VariableMode to) {
  std::unordered_map<std::string, std::string> names;
  if (from == to) {
    return names;
  }
  std::vector<std::string> written;  // the distinct names, in order of appearance
  for (const Token& token : tokens) {
    if (token.kind != TokenKind::Variable) {
      continue;
    }
    if (std::find(written.begin(), written.end(), token.text) == written.end()) {
      written.push_back(token.text);
    }
  }
  if (to == VariableMode::Old) {
    for (const std::string& name : written) {
      const bool old_spelling = name == "_" || name.front() == '_' ||
                                utf8Length(name) == 1 ||
                                (utf8Length(name) == 2 && name.back() == '_');
      names.emplace(name, old_spelling ? name : name + "'");
    }
    return names;
  }
  std::vector<std::string> bases;
  bases.reserve(written.size());
  std::unordered_map<std::string, std::size_t> shared;
  for (const std::string& name : written) {
    std::string base = name;
    if (!base.empty() && base.back() == '\'') {
      base.pop_back();
    }
    if (base.empty() || base.front() == '_') {
      // `_` stays anonymous, and `_имя` is a variable in ISO as it is written.
    } else {
      base = upperCaseFirst(base);
    }
    ++shared[base];
    bases.push_back(std::move(base));
  }
  std::unordered_map<std::string, std::size_t> used;  // base -> the next number
  std::unordered_set<std::string> taken;              // every name already handed out
  for (std::size_t i = 0; i < written.size(); ++i) {
    const std::string& base = bases[i];
    const bool anonymous_or_underscore = base.empty() || base.front() == '_';
    if (anonymous_or_underscore) {
      // `_` stays anonymous, and `_имя` is a variable in ISO as it is written.
      names.emplace(written[i], base);
      continue;
    }
    const bool alone = shared[base] == 1 && !isReservedBuiltinName(base);
    std::string name = alone ? base : base + "_" + std::to_string(++used[base]);
    while (!taken.insert(name).second) {
      // `X_1` may be the base of a variable of its own; the next number is free.
      name = base + "_" + std::to_string(++used[base]);
    }
    names.emplace(written[i], std::move(name));
  }
  return names;
}

// ---------------------------------------------------------------------------
// The formatter proper
// ---------------------------------------------------------------------------

class Formatter {
 public:
  Formatter(std::string_view source, const FormatOptions& options, VariableMode source_mode)
      : source_(source), options_(options), source_mode_(source_mode) {
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
      // The old dialect's underscore names may carry an apostrophe that the name
      // itself does not include (task_100).  It belongs to the token, or a rename
      // would leave it behind in the gap; printing an unconverted name keeps it.
      if (source_mode_ == VariableMode::Old && tokens[i].kind == TokenKind::Variable &&
          end_[i] < source_.size() && source_[end_[i]] == '\'') {
        ++end_[i];
      }
    }
    planNames(tokens);
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
      emitLeadGap(tail_from, end_offset, /*at_start=*/false, /*at_eof=*/true);
    }
    return builder_.take();
  }

 private:
  [[nodiscard]] std::string_view tokenText(std::size_t index) const {
    const auto replaced = replacements_.find(index);
    if (replaced != replacements_.end()) {
      return replaced->second;
    }
    return source_.substr(begin_[index], end_[index] - begin_[index]);
  }

  /// Fills `replacements_` when the caller asked for the other naming mode: the
  /// variables get their other spelling, an old-dialect string constant that is a
  /// bare capitalised name gets the quotes ISO needs (`Str` → `"Str"`), and an ISO
  /// atom the old dialect would read as a variable gets quotes too (`а` → `'а'`).
  /// Every other byte of the program is still copied as it is written (task_99).
  void planNames(const TokenList& tokens) {
    if (!options_.names_out.has_value() || *options_.names_out == source_mode_ ||
        options_.selection_only) {
      return;
    }
    const auto names = variableNames(tokens, source_mode_, *options_.names_out);
    for (std::size_t i = 0; i < tokens.size(); ++i) {
      if (tokens[i].kind == TokenKind::Variable) {
        const auto renamed = names.find(tokens[i].text);
        if (renamed != names.end()) {
          replacements_.emplace(i, renamed->second);
        }
      } else if (source_mode_ == VariableMode::Old && tokens[i].kind == TokenKind::String &&
                 (begin_[i] >= source_.size() || source_[begin_[i]] != '"')) {
        // A bare capitalised name is the old dialect's string constant (task_67);
        // ISO spells the same thing in quotes.
        replacements_.emplace(i, "\"" + tokens[i].text + "\"");
      } else if (source_mode_ == VariableMode::Iso && tokens[i].kind == TokenKind::Identifier &&
                 (begin_[i] >= source_.size() || source_[begin_[i]] != '\'') &&
                 oldReadsAsVariableName(tokens[i].text)) {
        // `?одно(а, а).` asks about one-letter *atoms* in ISO, and the old dialect
        // reads a one-letter name as a variable: without the quotes the question
        // would change its meaning (and answer `а=_1`).
        replacements_.emplace(i, "'" + tokens[i].text + "'");
      }
    }
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
      if (line_number == line_count) {
        // The last part of the gap is the beginning of the next statement's
        // line: indentation, not a blank line.
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
  VariableMode source_mode_ = VariableMode::Iso;
  std::string indent_;
  const TokenList* tokens_ = nullptr;
  std::vector<std::size_t> begin_;
  std::vector<std::size_t> end_;
  /// Token index -> the text to print in its place (task_99); empty when the
  /// names are printed as they are read.
  std::unordered_map<std::size_t, std::string> replacements_;
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

// ---------------------------------------------------------------------------
// The dialect conversion (task_101)
// ---------------------------------------------------------------------------

/// The pairs of built-in names in the two languages.  The alias table is the one
/// source of truth (task_39), so the conversion cannot invent a name the engine
/// does not answer to.  Two names are answered outside that table and are added
/// here: `ВЫП`/`call` (the solver) and `ИМПОРТ`/`import` (the parser).
const std::vector<BuiltinAlias>& dialectPairs() {
  static const std::vector<BuiltinAlias> pairs = [] {
    std::vector<BuiltinAlias> out;
    const std::span<const BuiltinAlias> aliases = builtinAliases();
    out.insert(out.end(), aliases.begin(), aliases.end());
    out.emplace_back("ВЫП", "call");
    out.emplace_back("ИМПОРТ", "import");
    return out;
  }();
  return pairs;
}

/// What a call of a built-in that has a sign spelling means.
enum class SignCall : std::uint8_t { None, Equal, Greater, Less, Not };

/// True when a token is a comparison sign — the group an operand of `=` never
/// contains unparenthesised, so a span holding one is not "one operand".
bool isComparisonSign(TokenKind kind) {
  switch (kind) {
    case TokenKind::Equal:
    case TokenKind::Less:
    case TokenKind::Greater:
    case TokenKind::LessEqual:
    case TokenKind::GreaterEqual:
    case TokenKind::NotEqual:
    case TokenKind::ArithEqual:
    case TokenKind::ArithNotEqual:
    case TokenKind::AtLess:
    case TokenKind::AtLessEqual:
    case TokenKind::AtGreater:
    case TokenKind::AtGreaterEqual:
    case TokenKind::NotGoal:
      return true;
    default:
      return false;
  }
}

/// A word that ends an operand: a term never contains one of these unparenthesised.
bool isOperandBoundary(TokenKind kind) {
  return isComparisonSign(kind) || kind == TokenKind::Comma || kind == TokenKind::Semicolon ||
         kind == TokenKind::IfThen || kind == TokenKind::Arrow ||
         kind == TokenKind::ColonDash || kind == TokenKind::Question ||
         kind == TokenKind::Dot || kind == TokenKind::Bar;
}

/// A word that ends a *term*: a comma, a disjunction, an arrow and the like.  A
/// term reaches across its comparison signs, so those are not separators here.
bool isSeparator(TokenKind kind) {
  return kind == TokenKind::Comma || kind == TokenKind::Semicolon ||
         kind == TokenKind::IfThen || kind == TokenKind::Arrow ||
         kind == TokenKind::ColonDash || kind == TokenKind::Question ||
         kind == TokenKind::Dot || kind == TokenKind::Bar;
}

/// What a call of a built-in means when it is also a sign, whichever of the two
/// languages its name is spelled in.
SignCall signCallOf(std::string_view name) {
  if (name == "РАВНО" || name == "equal") {
    return SignCall::Equal;
  }
  if (name == "БОЛЬШЕ" || name == "greater") {
    return SignCall::Greater;
  }
  if (name == "МЕНЬШЕ" || name == "less") {
    return SignCall::Less;
  }
  if (name == "НЕ" || name == "not") {
    return SignCall::Not;
  }
  return SignCall::None;
}

/// One direction of the dialect conversion, over a text whose tokens are known.
///
/// The rules are read off the parser's own spelling: `X = Y` *is* the term
/// `РАВНО(X, Y)`, `X > Y` is `БОЛЬШЕ(X, Y)`, and `X is Y` is `РАВНО(X, ЭКСПР(Y))`
/// — `is` differs from `=` only by the expression wrapper on its right operand,
/// which in this dialect is what `#…#` is.  So every call form and its sign are
/// two spellings of one term, and the conversion may trade one for the other
/// wherever the text parses.
class DialectConverter {
 public:
  DialectConverter(std::string_view source, const TokenList& tokens, Dialect target)
      : source_(source), tokens_(tokens), target_(target) {
    begin_.resize(tokens.size());
    end_.resize(tokens.size());
    const LineStarts lines = LineStarts::of(source);
    for (std::size_t i = 0; i < tokens.size(); ++i) {
      begin_[i] = lines.offset(tokens[i].location);
      end_[i] = begin_[i] + rawLength(source_, begin_[i], tokens[i]);
    }
    for (const BuiltinAlias& pair : dialectPairs()) {
      if (target == Dialect::English) {
        names_.emplace(pair.first, pair.second);
      } else {
        names_.emplace(pair.second, pair.first);
      }
    }
  }

  /// One past the last token that carries bytes: the `EndOfFile` token does not.
  std::size_t last() const {
    return !tokens_.empty() && tokens_.back().kind == TokenKind::EndOfFile ? tokens_.size() - 1
                                                                         : tokens_.size();
  }

  /// The index of the first token that starts at or after `offset` bytes.
  std::size_t firstTokenAt(std::size_t offset) const {
    std::size_t i = 0;
    while (i < last() && begin_[i] < offset) {
      ++i;
    }
    return i;
  }

  std::size_t beginOf(std::size_t index) const { return begin_[index]; }

  /// Where the bytes after the last token start.
  std::size_t endOfLast() const { return last() == 0 ? source_.size() : end_[last() - 1]; }

  /// The tokens `[from, to)` in the target dialect, with every byte outside the
  /// rewritten spans copied as it was written.
  std::string convert(std::size_t from, std::size_t to) const {
    if (from >= to) {
      return {};
    }
    std::string out;
    std::size_t cursor = begin_[from];
    std::size_t i = from;
    while (i < to) {
      // A prefix negation stands in front of the operand it applies to, and the
      // operand of `\+` reaches as far as the next `,`, `;` or `->` — its
      // precedence is looser than a comparison (task_55).
      if (target_ == Dialect::Russian && tokens_[i].kind == TokenKind::NotGoal) {
        const std::size_t end = termEnd(i + 1, to);
        if (i + 2 <= end) {
          out += source_.substr(cursor, begin_[i] - cursor);
          out += "НЕ(";
          out += convert(i + 1, end);
          out += ')';
          cursor = end_[end - 1];
          i = end;
          continue;
        }
      }
      // An infix sign ends the operand that starts here: `X = Y` is the term
      // `РАВНО(X, Y)`, and its two operands are the spans around the sign.
      if (target_ == Dialect::Russian) {
        const std::size_t at = firstSign(i, to);
        if (at != kNone && at > i) {
          const std::size_t end = rightOperandEnd(at, to);
          if (at + 1 < end) {
            const std::string call = signCall(i, at, end);
            if (!call.empty()) {
              out += source_.substr(cursor, begin_[i] - cursor);
              out += call;
              cursor = end_[end - 1];
              i = end;
              continue;
            }
          }
        }
      }
      // A call the target dialect writes as a sign.
      if (target_ == Dialect::English && tokens_[i].kind == TokenKind::Identifier) {
        const SignCall kind = signCallOf(tokens_[i].text);
        if (kind != SignCall::None) {
          std::size_t close = kNone;
          const std::string call = convertCall(i, to, kind, close);
          if (!call.empty()) {
            out += source_.substr(cursor, begin_[i] - cursor);
            out += call;
            cursor = end_[close];
            i = close + 1;
            continue;
          }
        }
      }
      out += source_.substr(cursor, begin_[i] - cursor);
      out += tokenText(i);
      cursor = end_[i];
      ++i;
    }
    out += source_.substr(cursor, end_[to - 1] - cursor);
    return out;
  }

 private:
  /// The token's text, renamed when it is a built-in of the other language.
  std::string tokenText(std::size_t i) const {
    if (tokens_[i].kind == TokenKind::Identifier) {
      const auto found = names_.find(tokens_[i].text);
      if (found != names_.end()) {
        return std::string(found->second);
      }
    }
    return std::string(source_.substr(begin_[i], end_[i] - begin_[i]));
  }

  /// `is` is a sign, not a name, unless it is called: `X is 1 + 1` and `is(X, Y)`
  /// are told apart by the bracket that follows.
  bool isIsSign(std::size_t index, std::size_t to) const {
    return tokens_[index].kind == TokenKind::Identifier && tokens_[index].text == "is" &&
           (index + 1 >= to || tokens_[index + 1].kind != TokenKind::LParen);
  }

  /// The index of the sign that ends the operand starting at `from`; `kNone` when
  /// the operand ends first — at a separator, at the bracket that closes an
  /// enclosing group, or at the end of the range.
  std::size_t firstSign(std::size_t from, std::size_t to) const {
    std::size_t depth = 0;
    for (std::size_t j = from + 1; j < to; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
        continue;
      }
      if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        if (depth == 0) {
          return kNone;
        }
        --depth;
        continue;
      }
      if (depth != 0) {
        continue;
      }
      if (kind == TokenKind::Equal || kind == TokenKind::Greater ||
          kind == TokenKind::Less || isIsSign(j, to)) {
        return j;
      }
      if (isOperandBoundary(kind)) {
        return kNone;
      }
    }
    return kNone;
  }

  /// One past the last token of the operand that follows the sign at `at`.
  std::size_t rightOperandEnd(std::size_t at, std::size_t to) const {
    std::size_t depth = 0;
    for (std::size_t j = at + 1; j < to; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
        continue;
      }
      if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        if (depth == 0) {
          return j;
        }
        --depth;
        continue;
      }
      if (depth == 0 && isSeparator(kind)) {
        return j;
      }
    }
    return to;
  }

  /// One past the last token of the *term* that starts at `from`: a term reaches
  /// across the comparison signs, so only a separator or the end of the range
  /// stops it (the operand of `\+` is a whole term).
  std::size_t termEnd(std::size_t from, std::size_t to) const {
    std::size_t depth = 0;
    for (std::size_t j = from; j < to; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
        continue;
      }
      if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        if (depth == 0) {
          return j;
        }
        --depth;
        continue;
      }
      if (depth == 0 && isSeparator(kind)) {
        return j;
      }
    }
    return to;
  }

  /// The text of `РАВНО(A, B)` — or of `>` and `<` — written with the sign the
  /// target dialect spells it with, or empty when the call is not one of those.
  std::string convertCall(std::size_t i, std::size_t to, SignCall kind,
                          std::size_t& close) const {
    close = kNone;
    if (i + 1 >= to || tokens_[i + 1].kind != TokenKind::LParen) {
      return {};
    }
    if (!cleanGap(i, i + 1)) {
      return {};
    }
    close = matchingParen(i + 1, to);
    if (close == kNone || !cleanSpan(i, close)) {
      return {};
    }
    const std::vector<std::pair<std::size_t, std::size_t>> args = splitArguments(i + 1, close);
    const std::size_t wanted = kind == SignCall::Not ? 1 : 2;
    if (args.size() != wanted) {
      return {};
    }
    for (const auto& [first, last] : args) {
      if (first >= last) {
        return {};
      }
    }
    const auto [a0, a1] = args[0];
    if (kind == SignCall::Not) {
      return "\\+ " + convert(a0, a1);
    }
    const auto [b0, b1] = args[1];
    // `is` is `=` with the expression wrapper around its right operand, and the
    // wrapper is what `#…#` is here: exactly one marked side is `is`.
    const std::pair<std::size_t, std::size_t> a_inside = hashInside(a0, a1);
    const std::pair<std::size_t, std::size_t> b_inside = hashInside(b0, b1);
    const bool a_marked = a_inside.second > a_inside.first;
    const bool b_marked = b_inside.second > b_inside.first;
    if (kind == SignCall::Equal) {
      if (b_marked && !a_marked && simple(a0, a1)) {
        return convert(a0, a1) + " is " + convert(b_inside.first, b_inside.second);
      }
      if (a_marked && !b_marked && simple(b0, b1)) {
        return convert(b0, b1) + " is " + convert(a_inside.first, a_inside.second);
      }
    }
    if (!simple(a0, a1) || !simple(b0, b1)) {
      return {};
    }
    const char* const sign = kind == SignCall::Equal ? " = "
                             : kind == SignCall::Greater ? " > "
                                                         : " < ";
    return convert(a0, a1) + sign + convert(b0, b1);
  }

  /// The call the sign at `at` becomes in the Russian dialect, with `start` as the
  /// first token of its left operand and `end` one past its right one.
  std::string signCall(std::size_t start, std::size_t at, std::size_t end) const {
    if (!simple(start, at) || !simple(at + 1, end)) {
      return {};
    }
    const std::string left = convert(start, at);
    const std::string right = convert(at + 1, end);
    if (isIsSign(at, end)) {
      const std::pair<std::size_t, std::size_t> inside = hashInside(at + 1, end);
      if (inside.second > inside.first) {
        return "РАВНО(" + left + ", #" + convert(inside.first, inside.second) + "#)";
      }
      return "РАВНО(" + left + ", #" + right + "#)";
    }
    if (tokens_[at].kind == TokenKind::Greater) {
      return "БОЛЬШЕ(" + left + ", " + right + ")";
    }
    if (tokens_[at].kind == TokenKind::Less) {
      return "МЕНЬШЕ(" + left + ", " + right + ")";
    }
    return "РАВНО(" + left + ", " + right + ")";
  }

  /// The tokens between the two `#` of a marked expression, when the range is
  /// exactly one marked expression; an empty pair otherwise.
  std::pair<std::size_t, std::size_t> hashInside(std::size_t from,
                                                 std::size_t to) const {
    if (to < from + 2 || tokens_[from].kind != TokenKind::Hash ||
        tokens_[to - 1].kind != TokenKind::Hash) {
      return {0, 0};
    }
    std::size_t depth = 0;
    for (std::size_t j = from + 1; j < to - 1; ++j) {
      if (tokens_[j].kind == TokenKind::LParen || tokens_[j].kind == TokenKind::LBracket) {
        ++depth;
      } else if (tokens_[j].kind == TokenKind::RParen || tokens_[j].kind == TokenKind::RBracket) {
        depth = depth > 0 ? depth - 1 : 0;
      } else if (depth == 0 && tokens_[j].kind == TokenKind::Hash) {
        return {0, 0};
      }
    }
    return {from + 1, to - 1};
  }

  /// True when the span is one operand: no separator and no comparison sign of
  /// its own stands at its top level, so it can be moved into a sign form.  `is`
  /// counts as a sign, and a span that opens with a call of its own would become
  /// a comparison when it is converted — `РАВНО(РАВНО(X, Y), Z)` has no spelling
  /// as `X = Y = Z`, and a chain is not a term.
  bool simple(std::size_t from, std::size_t to) const {
    if (from >= to) {
      return false;
    }
    if (tokens_[from].kind == TokenKind::Identifier &&
        signCallOf(tokens_[from].text) != SignCall::None && from + 1 < to &&
        tokens_[from + 1].kind == TokenKind::LParen) {
      return false;
    }
    std::size_t depth = 0;
    for (std::size_t j = from; j < to; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
      } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        depth = depth > 0 ? depth - 1 : 0;
      } else if (depth == 0 && (isSeparator(kind) || isComparisonSign(kind) ||
                                isIsSign(j, to))) {
        return false;
      }
    }
    return true;
  }

  /// The `)` that closes the `(` at `open`, or `kNone` when the range ends first.
  std::size_t matchingParen(std::size_t open, std::size_t to) const {
    std::size_t depth = 0;
    for (std::size_t j = open; j < to; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
      } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        --depth;
        if (depth == 0) {
          return j;
        }
      }
    }
    return kNone;
  }

  /// The top-level arguments of the call whose brackets are `open` and `close`.
  std::vector<std::pair<std::size_t, std::size_t>> splitArguments(std::size_t open,
                                                                  std::size_t close) const {
    std::vector<std::pair<std::size_t, std::size_t>> args;
    std::size_t start = open + 1;
    std::size_t depth = 0;
    for (std::size_t j = open + 1; j < close; ++j) {
      const TokenKind kind = tokens_[j].kind;
      if (kind == TokenKind::LParen || kind == TokenKind::LBracket) {
        ++depth;
      } else if (kind == TokenKind::RParen || kind == TokenKind::RBracket) {
        depth = depth > 0 ? depth - 1 : 0;
      } else if (depth == 0 && kind == TokenKind::Comma) {
        args.emplace_back(start, j);
        start = j + 1;
      }
    }
    args.emplace_back(start, close);
    return args;
  }

  /// True when nothing but whitespace stands between two neighbouring tokens: a
  /// comment inside a rewritten span would be lost, so such a call keeps its form.
  bool cleanGap(std::size_t left, std::size_t right) const {
    const std::string_view gap =
        source_.substr(end_[left], begin_[right] - end_[left]);
    return gap.find('%') == std::string_view::npos &&
           gap.find("/*") == std::string_view::npos;
  }

  /// True when no comment stands anywhere inside the tokens `[from, to]`.
  bool cleanSpan(std::size_t from, std::size_t to) const {
    for (std::size_t j = from; j < to; ++j) {
      if (!cleanGap(j, j + 1)) {
        return false;
      }
    }
    return true;
  }

  std::string_view source_;
  const TokenList& tokens_;
  Dialect target_ = Dialect::English;
  std::vector<std::size_t> begin_;
  std::vector<std::size_t> end_;
  /// The names of the language the text is written in, mapped to the target's.
  std::unordered_map<std::string, std::string_view> names_;
};

/// What the dialect conversion made of a text.
struct DialectConversion {
  std::string text;
  std::vector<PrologError> diagnostics;
  bool ok = false;
};

/// The `dialect` pass of `formatSource`: the words of one language printed in the
/// other, with everything else left as it is written (task_101).
///
/// The text is lexed and parsed first — a conversion of a program that does not
/// parse would be a guess — and the answer is parsed again before it is handed
/// back, so a rewrite can never turn a working file into a broken one.  The
/// marker line of a file (`:- ИМЕНА(0|1).`) is left exactly as it is: it is our
/// dialect's own word, and `variables(0)` would not be read as a marker.
DialectConversion convertDialect(std::string_view text, const FormatOptions& options) {
  DialectConversion out;
  out.text = std::string(text);
  const std::string_view source = stripByteOrderMark(text);
  VariableMode mode = options.variables;
  const std::optional<std::pair<VariableMode, std::size_t>> marker =
      readVariableMarker(source);
  if (marker.has_value()) {
    mode = marker->first;
  }
  Lexed lexed = lexAndParse(source, options.source_name, mode);
  out.diagnostics = lexed.sink.diagnostics();
  if (!lexed.parses) {
    return out;
  }
  DialectConverter converter(source, lexed.tokens, *options.dialect_out);
  const std::size_t first = marker.has_value() ? converter.firstTokenAt(marker->second) : 0;
  const std::size_t head_end = first < converter.last() ? converter.beginOf(first) : source.size();
  out.text = std::string(source.substr(0, head_end)) +
             converter.convert(first, converter.last()) + std::string(source.substr(converter.endOfLast()));
  out.ok = true;
  return out;
}

}  // namespace

/// The marker line of a converted answer (task_99).
///
/// A converted file always says which mode its names are written in — even an ISO
/// one, whose marker is otherwise the default it gets for free.  A source that had
/// no marker (it was read by `--vars`) gets one added above everything else, so the
/// answer does not depend on how the reader was started.
std::string withModeMarker(std::string text, VariableMode mode, bool had_marker) {
  const std::string line =
      std::string(":- ИМЕНА(") + (mode == VariableMode::Iso ? "0" : "1") + ").";
  if (!had_marker) {
    return line + "\n" + text;
  }
  const std::size_t eol = text.find('\n');
  return eol == std::string::npos ? line : line + text.substr(eol);
}

FormatResult formatSource(std::string_view text, const FormatOptions& options) {
  FormatResult result;
  const std::string original(text);
  result.text = original;
  // The dialect conversion (task_101) is a rewrite of words, not of layout, so it
  // runs first: the names and the layout then work on the text it produced.
  std::string converted;
  if (options.dialect_out.has_value() && !options.selection_only && !text.empty()) {
    DialectConversion dialect = convertDialect(text, options);
    result.diagnostics = dialect.diagnostics;
    if (!dialect.ok) {
      return result;  // byte for byte, with the diagnostics
    }
    converted = std::move(dialect.text);
    text = converted;
    result.text = converted;
  }
  if (options.mode == FormatMode::None || text.empty()) {
    result.changed = result.text != original;
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
  const std::optional<std::pair<VariableMode, std::size_t>> marker =
      readVariableMarker(source);
  if (marker.has_value()) {
    mode = marker->first;
  }
  Lexed lexed = lexAndParse(source, options.source_name, mode);
  result.diagnostics = lexed.sink.diagnostics();
  if (!lexed.parses && !options.selection_only) {
    return result;  // byte for byte, with the diagnostics
  }
  if (lexed.parses) {
    Formatter formatter(source, options, mode);
    result.text = tidyUp(formatter.run(lexed.tokens, source.size()));
    if (options.names_out.has_value() && !options.selection_only) {
      result.text = withModeMarker(result.text, *options.names_out, marker.has_value());
    }
    result.changed = result.text != original;
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
    Formatter formatter(source, options, mode);
    std::string formatted = formatter.run(prefix.tokens, cut);
    formatted += source.substr(cut);
    result.text = stripLineEnds(std::move(formatted));
    result.changed = result.text != original;
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
