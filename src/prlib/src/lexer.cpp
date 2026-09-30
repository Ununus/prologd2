#include "prlib/lexer.hpp"

#include <array>

#include "prlib/utf8.hpp"

namespace prologd {

namespace {

const std::unordered_set<std::string> kReservedBuiltins = {
    // Control / logic, with the English spelling of each name (task_39).
    "ЛОЖЬ", "ТРАССА", "НЕТ_ТРАССЫ", "ВЫП", "НЕ", "ИЛИ", "РАВНО", "ТИХО",
    "ВЕРСИЯ", "ПС",
    "fail", "trace", "no_trace", "call", "not", "or", "equal", "quiet",
    "version", "nl",
    // Arithmetic
    "БОЛЬШЕ", "МЕНЬШЕ", "СЛОЖЕНИЕ", "УМНОЖЕНИЕ", "СЛУЧ", "float", "mod", "div",
    "greater", "less", "plus", "mul", "random", "abs", "sqrt", "sin",
    "cos", "tan", "exp", "is_whole", "is_number",
    // I/O
    "ЧТЕНИЕ_ИЗ", "ЗАПИСЬ_В", "ВВКОД", "ВВОДЦЕЛ", "ВВОДВЕЩ", "ВВОДСИМВ",
    "ВВОДСТР", "ВЫВОД", "ЖДИ",
    "see", "tell", "put_code", "read_int", "read_float", "read_char",
    "read_string", "write", "wait",
    // Strings
    "БУКВА", "ЦИФРА", "СЦЕП", "КОПИЯ", "ДЛИНА",
    "is_letter", "is_digit", "concat", "substring", "strlen",
    // Type tests and conversions
    "ПЕР", "ЦЕЛ", "ВЕЩ", "СИМВ", "СПИСОК", "СТРСПИС", "СТРЦЕЛ", "СТРВЕЩ",
    "ЦЕЛВЕЩ",
    "var", "integer", "is_text", "is_list", "str_to_list", "str_to_int",
    "str_to_float", "int_to_float",
    // Database
    "СКОЛЬКО", "ПРЕДЛ", "ТЕРМ", "ДОБ", "УДАЛЕНИЕ",
    "clause_count", "clause_at", "univ", "assert", "retract",
    // Graphics
    "ТОЧКА", "ЛИНИЯ", "ОКРУЖНОСТЬ", "ЗАКРАСКА",
    "point", "line", "circle", "fill",
    // Newcomers
    "НАЙТИВСЕ", "ИМПОРТ", "findall", "import",
};

/// Spellings the dialect has retired.  They stay reserved so that a call to
/// one is still parsed as a goal and reaches the checks, which know what to
/// say about it.  They are deliberately *not* in `kReservedBuiltins`: the
/// keyword table, completion and `--list-keywords` must not offer them.
const std::unordered_set<std::string> kRetiredBuiltinNames = {
    // The ported help spelled findall with ё for a while; the original manual
    // and the task spelled it without.
    "НАЙТИВСЁ",
};

}  // namespace

const std::unordered_set<std::string>& reservedBuiltinNames() { return kReservedBuiltins; }

bool isReservedBuiltinName(std::string_view name) {
  const std::string text(name);
  return kReservedBuiltins.count(text) != 0 || kRetiredBuiltinNames.count(text) != 0;
}

Lexer::Lexer(std::string_view source, std::string file_name)
    : source_(stripByteOrderMark(source)), file_name_(std::move(file_name)) {}

char Lexer::peek(std::size_t lookahead) const {
  const std::size_t index = offset_ + lookahead;
  return index < source_.size() ? source_[index] : '\0';
}

SourceLocation Lexer::here() const {
  return SourceLocation{file_name_, line_, column_};
}

void Lexer::advanceByte(std::size_t count) {
  for (std::size_t i = 0; i < count && offset_ < source_.size(); ++i) {
    if (source_[offset_] == '\n') {
      ++line_;
      column_ = 1;
    } else {
      ++column_;
    }
    ++offset_;
  }
}

Token Lexer::makeToken(TokenKind kind, std::string text, SourceLocation location) const {
  Token token;
  token.kind = kind;
  token.text = std::move(text);
  token.location = std::move(location);
  return token;
}

Token Lexer::lexIdentifier(DiagnosticSink* sink) {
  (void)sink;
  const SourceLocation start = here();
  const std::size_t begin = offset_;
  DecodeResult first = decodeCodePoint(source_, offset_);
  while (!atEnd()) {
    const DecodeResult decoded = decodeCodePoint(source_, offset_);
    if (!decoded.valid || !isNameCharacter(decoded.code_point)) {
      break;
    }
    advanceByte(decoded.length);
  }
  std::string text(source_.substr(begin, offset_ - begin));
  if (text.empty() || text.front() == '_') {
    return makeToken(TokenKind::Variable, std::move(text), start);
  }
  const bool startsUpper = first.valid && isUpperCaseLetter(first.code_point);
  if (startsUpper && !isReservedBuiltinName(text)) {
    return makeToken(TokenKind::Variable, std::move(text), start);
  }
  if (sink != nullptr && startsUpper && isReservedBuiltinName(text)) {
    // Reserved names are atoms on purpose; nothing to report.
  }
  return makeToken(TokenKind::Identifier, std::move(text), start);
}

Token Lexer::lexNumber(DiagnosticSink* sink) {
  const SourceLocation start = here();
  bool has_dot = false;
  bool has_exponent = false;
  const std::size_t begin = offset_;
  while (!atEnd()) {
    const char ch = peek();
    if (isAsciiDigit(static_cast<unsigned char>(ch))) {
      advanceByte(1);
      continue;
    }
    if (ch == '.' && !has_dot && !has_exponent) {
      // `12.3` is a decimal fraction; `12.` (a dot not followed by a digit) is a
      // trailing-dot float, as in the original PrologD (`1.` means 1.0).  A dot
      // that follows the closing parenthesis of a clause is lexed separately
      // because the number has already ended.
      if (isAsciiDigit(static_cast<unsigned char>(peek(1)))) {
        has_dot = true;
        advanceByte(1);
        continue;
      }
      if (peek(1) != '.' && peek(1) != '\0') {
        has_dot = true;
        advanceByte(1);
      }
      break;
    }
    if ((ch == 'e' || ch == 'E') && !has_exponent) {
      const char sign = peek(1);
      const char digit = (sign == '+' || sign == '-') ? peek(2) : sign;
      if (isAsciiDigit(static_cast<unsigned char>(digit))) {
        has_exponent = true;
        advanceByte(1);
        if (sign == '+' || sign == '-') {
          advanceByte(1);
        }
        continue;
      }
    }
    break;
  }
  // `12.123.123` and similar malformed literals.
  if (!has_exponent && peek() == '.' &&
      isAsciiDigit(static_cast<unsigned char>(peek(1)))) {
    // Consume the rest of the malformed literal so recovery is clean.
    while (!atEnd() && (isAsciiDigit(static_cast<unsigned char>(peek())) || peek() == '.')) {
      advanceByte(1);
    }
    if (sink != nullptr) {
      PrologError error;
      error.code = ErrorCode::InvalidNumberLiteral;
      error.message = std::string(errorCodeText(error.code));
      error.location = start;
      error.isParseError = true;
      sink->report(std::move(error));
    }
    return makeToken(TokenKind::Float, std::string(source_.substr(begin, offset_ - begin)),
                     start);
  }
  const TokenKind kind = (has_dot || has_exponent) ? TokenKind::Float : TokenKind::Integer;
  return makeToken(kind, std::string(source_.substr(begin, offset_ - begin)), start);
}

Token Lexer::lexString(DiagnosticSink* sink) {
  const SourceLocation start = here();
  advanceByte(1);  // opening quote
  std::string value;
  bool terminated = false;
  while (!atEnd()) {
    const char ch = peek();
    if (ch == '"') {
      advanceByte(1);
      terminated = true;
      break;
    }
    if (ch == '\\' && (peek(1) == '"' || peek(1) == '\\')) {
      value.push_back(peek(1));
      advanceByte(2);
      continue;
    }
    if (ch == '\n') {
      break;
    }
    value.push_back(ch);
    advanceByte(1);
  }
  if (!terminated && sink != nullptr) {
    PrologError error;
    error.code = ErrorCode::InvalidStringLiteral;
    error.message = std::string(errorCodeText(error.code));
    error.location = start;
    error.isParseError = true;
    sink->report(std::move(error));
  }
  return makeToken(TokenKind::String, std::move(value), start);
}

Token Lexer::lexQuotedAtom(DiagnosticSink* sink) {
  const SourceLocation start = here();
  advanceByte(1);  // opening quote
  std::string value;
  bool terminated = false;
  while (!atEnd()) {
    const char ch = peek();
    if (ch == '\'') {
      if (peek(1) == '\'') {  // escaped quote
        value.push_back('\'');
        advanceByte(2);
        continue;
      }
      advanceByte(1);
      terminated = true;
      break;
    }
    if (ch == '\n') {
      break;
    }
    value.push_back(ch);
    advanceByte(1);
  }
  if (!terminated && sink != nullptr) {
    PrologError error;
    error.code = ErrorCode::InvalidStringLiteral;
    error.message = "Незакрытая кавычка в имени константы";
    error.location = start;
    error.isParseError = true;
    sink->report(std::move(error));
  }
  return makeToken(TokenKind::QuotedAtom, std::move(value), start);
}

std::vector<Token> Lexer::tokenize(DiagnosticSink& sink) { return tokenizeImpl(&sink); }

std::vector<Token> Lexer::tokenize() { return tokenizeImpl(nullptr); }

std::vector<Token> Lexer::tokenizeImpl(DiagnosticSink* sink) {
  std::vector<Token> tokens;
  while (!atEnd()) {
    const char ch = peek();
    if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n' || ch == '\f' || ch == '\v') {
      advanceByte(1);
      continue;
    }
    if (ch == '%') {
      while (!atEnd() && peek() != '\n') {
        advanceByte(1);
      }
      continue;
    }
    const SourceLocation start = here();
    const unsigned char byte = static_cast<unsigned char>(ch);
    if (byte >= 0x80) {
      const DecodeResult decoded = decodeCodePoint(source_, offset_);
      if (decoded.valid && isLetter(decoded.code_point)) {
        tokens.push_back(lexIdentifier(sink));
        continue;
      }
      advanceByte(decoded.length);
      if (sink != nullptr) {
        PrologError error;
        error.code = ErrorCode::InvalidCharacter;
        error.message = std::string(errorCodeText(error.code));
        error.location = start;
        error.isParseError = true;
        sink->report(std::move(error));
      }
      tokens.push_back(makeToken(TokenKind::Unknown, std::string(1, ch), start));
      continue;
    }
    if (ch == '_') {
      tokens.push_back(lexIdentifier(sink));
      continue;
    }
    if (isAsciiLetter(static_cast<char32_t>(ch))) {
      tokens.push_back(lexIdentifier(sink));
      continue;
    }
    if (isAsciiDigit(static_cast<char32_t>(ch))) {
      tokens.push_back(lexNumber(sink));
      continue;
    }
    switch (ch) {
      case ',': advanceByte(1); tokens.push_back(makeToken(TokenKind::Comma, ",", start)); break;
      case '.': advanceByte(1); tokens.push_back(makeToken(TokenKind::Dot, ".", start)); break;
      case ';': advanceByte(1); tokens.push_back(makeToken(TokenKind::Semicolon, ";", start)); break;
      case '?': advanceByte(1); tokens.push_back(makeToken(TokenKind::Question, "?", start)); break;
      case '!': advanceByte(1); tokens.push_back(makeToken(TokenKind::Bang, "!", start)); break;
      case '#': advanceByte(1); tokens.push_back(makeToken(TokenKind::Hash, "#", start)); break;
      case '+': advanceByte(1); tokens.push_back(makeToken(TokenKind::Plus, "+", start)); break;
      case '-': advanceByte(1); tokens.push_back(makeToken(TokenKind::Minus, "-", start)); break;
      case '*': advanceByte(1); tokens.push_back(makeToken(TokenKind::Star, "*", start)); break;
      case '/': advanceByte(1); tokens.push_back(makeToken(TokenKind::Slash, "/", start)); break;
      case '(': advanceByte(1); tokens.push_back(makeToken(TokenKind::LParen, "(", start)); break;
      case ')': advanceByte(1); tokens.push_back(makeToken(TokenKind::RParen, ")", start)); break;
      case '[': advanceByte(1); tokens.push_back(makeToken(TokenKind::LBracket, "[", start)); break;
      case ']': advanceByte(1); tokens.push_back(makeToken(TokenKind::RBracket, "]", start)); break;
      case '|': advanceByte(1); tokens.push_back(makeToken(TokenKind::Bar, "|", start)); break;
      case ':':
        if (peek(1) == '-') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::ColonDash, ":-", start));
        } else {
          advanceByte(1);
          if (sink != nullptr) {
            PrologError error;
            error.code = ErrorCode::InvalidCharacter;
            error.message = std::string(errorCodeText(error.code));
            error.location = start;
            error.isParseError = true;
            sink->report(std::move(error));
          }
          tokens.push_back(makeToken(TokenKind::Unknown, ":", start));
        }
        break;
      case '<':
        if (peek(1) == '-') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::Arrow, "<-", start));
        } else {
          advanceByte(1);
          if (sink != nullptr) {
            PrologError error;
            error.code = ErrorCode::InvalidCharacter;
            error.message = std::string(errorCodeText(error.code));
            error.location = start;
            error.isParseError = true;
            sink->report(std::move(error));
          }
          tokens.push_back(makeToken(TokenKind::Unknown, "<", start));
        }
        break;
      case '"':
        tokens.push_back(lexString(sink));
        break;
      case '\'':
        tokens.push_back(lexQuotedAtom(sink));
        break;
      default:
        advanceByte(1);
        if (sink != nullptr) {
          PrologError error;
          error.code = ErrorCode::InvalidCharacter;
          error.message = std::string(errorCodeText(error.code));
          error.location = start;
          error.isParseError = true;
          sink->report(std::move(error));
        }
        tokens.push_back(makeToken(TokenKind::Unknown, std::string(1, ch), start));
        break;
    }
  }
  tokens.push_back(makeToken(TokenKind::EndOfFile, "", here()));
  return tokens;
}

}  // namespace prologd
