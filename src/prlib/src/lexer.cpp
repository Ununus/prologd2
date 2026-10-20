#include "prlib/lexer.hpp"

#include <array>

#include "prlib/utf8.hpp"

namespace prologd {

namespace {

const std::unordered_set<std::string> kReservedBuiltins = {
    // The marker that sets how names are read (task_67).  Reserved in every mode,
    // or the loader could not recognise it: a capitalised name is a variable in
    // mode 0 and a string constant in modes 1 and 2.
    "ИМЕНА",
    "variables",
    // Control / logic, with the English spelling of each name (task_39).
    // `ИЛИ` is the one name here without an English twin: it is the word of the
    // original dialect, kept for the programs written for it, and its English
    // spelling `or` stays retired (task_44) — the English vocabulary is
    // `ПЕРВОЕ`/`first` (task_83).
    "ЛОЖЬ", "ТРАССА", "НЕТ_ТРАССЫ", "ВЫП", "НЕ", "ДЛЯВСЕХ", "ПЕРВОЕ", "ИЛИ",
    "РАВНО", "ТИХО", "ВЕРСИЯ", "ПС",
    "fail", "trace", "no_trace", "call", "not", "forall", "first", "equal",
    "quiet", "version", "nl",
    // Arithmetic
    "БОЛЬШЕ", "МЕНЬШЕ", "СЛОЖЕНИЕ", "УМНОЖЕНИЕ", "СЛУЧ", "float", "mod", "div",
    "greater", "less", "plus", "mul", "random", "abs", "sqrt", "sin",
    "cos", "tan", "exp", "is_whole", "is_number",
    // I/O
    "ЧТЕНИЕ_ИЗ", "ЗАПИСЬ_В", "ВВКОД", "ВВОДЦЕЛ", "ВВОДВЕЩ", "ВВОДСИМВ",
    "ВВОДСТР", "ВЫВОД", "ВЫВОДПС", "ЖДИ",
    "see", "tell", "put_code", "read_int", "read_float", "read_char",
    "read_string", "write", "writeln", "wait",
    // Strings
    "БУКВА", "ЦИФРА", "СЦЕП", "КОПИЯ", "ДЛИНА",
    "is_letter", "is_digit", "concat", "strlen",
    // `sub_string/5` is English on purpose (task_84): it is the ISO spelling of
    // what `КОПИЯ/4` does, and ISO has no Russian word for it.  Its old English
    // alias `substring` is retired below.
    "sub_string",
    // Type tests and conversions
    "ПЕР", "ЦЕЛ", "ВЕЩ", "СИМВ", "СПИСОК", "ПОЛНЫЙ", "СТРСПИС", "СТРЦЕЛ",
    "СТРВЕЩ", "ЦЕЛВЕЩ",
    "var", "integer", "is_text", "is_list", "ground", "str_to_list",
    "str_to_int", "str_to_float", "int_to_float",
    // Database
    "СКОЛЬКО", "ПРЕДЛ", "ТЕРМ", "ДОБ", "УДАЛЕНИЕ",
    "clause_count", "clause_at", "univ", "assert", "retract",
    // Graphics
    "ТОЧКА", "ЛИНИЯ", "ОКРУЖНОСТЬ", "ЗАКРАСКА",
    "point", "line", "circle", "fill",
    // Lists
    "СОРТИРОВКА", "sort",
    // The standard order of terms (task_90).  `compare/3` is English only: ISO
    // has no Russian word for it, and it is the call the four `@` signs are
    // sugar for.
    "compare",
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
    // The English spelling `КОПИЯ` used to answer to (task_84).  It is not the
    // ISO name of anything: the ISO predicate is `sub_string/5`, with positions
    // from zero, so a call to `substring/4` reaches the checks and is told so.
    "substring",
};

/// Operator spellings borrowed from other Prologs that this dialect does not
/// have (task_52).  `=` now means unification, so reading `=:=` as three
/// characters would be worse than useless: the advice names the Пролог-Д
/// spelling of the same thing.  **Longest first** — `\==` must win over `\=`.
struct ForeignOperator {
  std::string_view text;
  const char* hint;
};

constexpr ForeignOperator kForeignOperators[] = {
    {"=:=",
     "«=:=» — не оператор: выражение вычисляет «#…#», поэтому «1 + 1 =:= 2» — "
     "это «#1 + 1# = 2»"},
    {"=\\=", "«=\\=» — не оператор: «не равно» — это «НЕ(A = B)»"},
    {"\\==", "«\\==» — не оператор: «термы не совпадают» — это «НЕ(A = B)»"},
    {"\\=", "«\\=» — не оператор: «не унифицируется» — это «НЕ(A = B)»"},
    {"==", "«==» — не оператор: сравнение термов записывают унификацией — «A = B»"},
    {"<=", "«<=» — не оператор: «меньше или равно» записывают «=<»"},
};

/// The advice for one spelling.
std::string foreignOperatorHint(const ForeignOperator& entry) { return entry.hint; }

/// The foreign spelling that starts at `offset`, or `nullptr`.
const ForeignOperator* foreignOperatorAt(std::string_view source, std::size_t offset) {
  for (const ForeignOperator& entry : kForeignOperators) {
    if (source.compare(offset, entry.text.size(), entry.text) == 0) {
      return &entry;
    }
  }
  return nullptr;
}

}  // namespace

const std::unordered_set<std::string>& reservedBuiltinNames() { return kReservedBuiltins; }

bool isReservedBuiltinName(std::string_view name) {
  const std::string text(name);
  return kReservedBuiltins.count(text) != 0 || kRetiredBuiltinNames.count(text) != 0;
}

std::optional<VariableMode> variableModeFromNumber(int number) {
  switch (number) {
    case 0:
      return VariableMode::Iso;
    case 1:
    case 2:  // `2` is the old spelling of the old dialect (task_77)
      return VariableMode::Old;
    default:
      return std::nullopt;
  }
}

std::optional<std::pair<VariableMode, std::size_t>> readVariableMarker(
    std::string_view source) {
  const std::size_t newline = source.find('\n');
  const std::string_view first_line =
      source.substr(0, newline == std::string_view::npos ? source.size() : newline);
  DiagnosticSink quiet;
  Lexer lexer(first_line, "<marker>");
  const std::vector<Token> tokens = lexer.tokenize(quiet);
  if (quiet.hasErrors() || tokens.size() != 7) {
    return std::nullopt;
  }
  const bool shape = tokens[0].kind == TokenKind::ColonDash &&
                     tokens[1].kind == TokenKind::Identifier && tokens[1].text == "ИМЕНА" &&
                     tokens[2].kind == TokenKind::LParen &&
                     tokens[3].kind == TokenKind::Integer &&
                     tokens[4].kind == TokenKind::RParen && tokens[5].kind == TokenKind::Dot &&
                     tokens[6].kind == TokenKind::EndOfFile;
  if (!shape || tokens[3].text.size() != 1) {
    return std::nullopt;
  }
  const std::optional<VariableMode> mode = variableModeFromNumber(tokens[3].text[0] - '0');
  if (!mode.has_value()) {
    return std::nullopt;
  }
  return std::pair{*mode, newline == std::string_view::npos ? source.size() : newline};
}

Lexer::Lexer(std::string_view source, std::string file_name, LexerOptions options)
    : source_(stripByteOrderMark(source)), file_name_(std::move(file_name)),
      options_(options) {}

char Lexer::peek(std::size_t lookahead) const {
  const std::size_t index = offset_ + lookahead;
  return index < source_.size() ? source_[index] : '\0';
}

SourceLocation Lexer::here() const {
  return SourceLocation{file_name_, line_, column_};
}

void Lexer::reportInvalidSign(DiagnosticSink* sink, const SourceLocation& location,
                              std::string_view message) {
  if (sink == nullptr) {
    return;
  }
  PrologError error;
  error.code = ErrorCode::InvalidCharacter;
  error.message = message.empty() ? std::string(errorCodeText(error.code))
                                  : std::string(message);
  error.location = location;
  error.isParseError = true;
  sink->report(std::move(error));
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

/// The old dialect's variable names (task_67): one letter, optionally followed by a
/// single `_` — `д`, `Б`, `A_`, `X_`.  Anything longer is a string constant when it
/// is capitalised and an atom otherwise.
bool isOldVariableName(const DecodeResult& first, const std::string& text) {
  if (!first.valid || !isLetter(first.code_point)) {
    return false;
  }
  if (text.size() == first.length) {
    return true;
  }
  return text.size() == first.length + 1 && text.back() == '_';
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
  // A reserved name is a predicate whatever its case is, in every mode: the table
  // is the language's, and a mode is only a way of reading names (ADR-005).
  if (isReservedBuiltinName(text)) {
    return makeToken(TokenKind::Identifier, std::move(text), start);
  }
  // The old dialect's long variable names: a name followed by an apostrophe.  The
  // apostrophe is only a *suffix* — at the start of a token it is still the quote
  // of `'атом'` — which is why it is read here and not in `lexQuotedAtom`.
  if (peek() == '\'' && options_.variables == VariableMode::Old) {
    advanceByte(1);
    text.push_back('\'');
    return makeToken(TokenKind::Variable, std::move(text), start);
  }
  if (options_.variables != VariableMode::Iso) {
    // The old dialect's variables are one letter, upper or lower, with at most one
    // `_` after it (`д`, `Б`, `A_`) …
    if (isOldVariableName(first, text)) {
      return makeToken(TokenKind::Variable, std::move(text), start);
    }
    // … and a capitalised name is a string constant, the way the original kept
    // strings and symbolic constants in one storage.
    if (first.valid && isUpperCaseLetter(first.code_point)) {
      return makeToken(TokenKind::String, std::move(text), start);
    }
    return makeToken(TokenKind::Identifier, std::move(text), start);
  }
  const bool starts_upper = first.valid && isUpperCaseLetter(first.code_point);  if (starts_upper) {
    return makeToken(TokenKind::Variable, std::move(text), start);
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
      // A fraction needs a digit after the point: `12.3` is a real, `2.0` too,
      // while `12.` is the integer 12 followed by the sentence terminator
      // (task_52, as in ISO).  The trailing-dot float of the original PrologD
      // (`1.` for 1.0) is gone with it: a statement can now *end* with a number
      // — `?2 > 1.`, `X = 1.` — and the dot belongs to the terminator there.
      if (isAsciiDigit(static_cast<unsigned char>(peek(1)))) {
        has_dot = true;
        advanceByte(1);
        continue;
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
      case '-':
        // `->` is ISO's if-then (task_85).  It is an operator now, so it is read
        // here, before the table of foreign spellings — which used to answer it
        // with advice.  A lone `-` is the sign it always was.
        if (peek(1) == '>') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::IfThen, "->", start));
        } else if (const ForeignOperator* foreign = foreignOperatorAt(source_, offset_);
                   foreign != nullptr) {
          advanceByte(foreign->text.size());
          reportInvalidSign(sink, start, foreignOperatorHint(*foreign));
          tokens.push_back(makeToken(TokenKind::Unknown, std::string(foreign->text), start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Minus, "-", start));
        }
        break;
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
          reportInvalidSign(sink, start);
          tokens.push_back(makeToken(TokenKind::Unknown, ":", start));
        }
        break;
      case '<':
        // `<-` is a rule arrow and `<` is «less»; `<=` is the habit of other
        // languages, while ISO — and this dialect with it — spells «less or
        // equal» as `=<` (task_52), so `<=` only gets the advice.
        if (peek(1) == '-') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::Arrow, "<-", start));
        } else if (const ForeignOperator* foreign = foreignOperatorAt(source_, offset_);
                   foreign != nullptr) {
          advanceByte(foreign->text.size());
          reportInvalidSign(sink, start, foreignOperatorHint(*foreign));
          tokens.push_back(makeToken(TokenKind::Unknown, std::string(foreign->text), start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Less, "<", start));
        }
        break;
      case '>':
        if (peek(1) == '=') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::GreaterEqual, ">=", start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Greater, ">", start));
        }
        break;
      case '=':
        // `=` is unification (task_52) — the sugar over `РАВНО/2`.  Longest
        // match first: `=<` is «less or equal», while `=:=`, `=\=` and `==`
        // belong to other Prologs and get advice instead of a token.
        if (const ForeignOperator* foreign = foreignOperatorAt(source_, offset_);
            foreign != nullptr) {
          advanceByte(foreign->text.size());
          reportInvalidSign(sink, start, foreignOperatorHint(*foreign));
          tokens.push_back(makeToken(TokenKind::Unknown, std::string(foreign->text), start));
        } else if (peek(1) == '<') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::LessEqual, "=<", start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Equal, "=", start));
        }
        break;
      case '@':
        // The four standard-order signs of ISO (task_90), longest match first:
        // `@=<` and `@>=` before `@<` and `@>`.  A lone `@` is still an error.
        if (peek(1) == '=' && peek(2) == '<') {
          advanceByte(3);
          tokens.push_back(makeToken(TokenKind::AtLessEqual, "@=<", start));
        } else if (peek(1) == '>' && peek(2) == '=') {
          advanceByte(3);
          tokens.push_back(makeToken(TokenKind::AtGreaterEqual, "@>=", start));
        } else if (peek(1) == '<') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::AtLess, "@<", start));
        } else if (peek(1) == '>') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::AtGreater, "@>", start));
        } else {
          advanceByte(1);
          reportInvalidSign(sink, start);
          tokens.push_back(makeToken(TokenKind::Unknown, "@", start));
        }
        break;
      case '\\':
        // `\+` is the ISO spelling of `НЕ` (task_55): one token, not two, so
        // the parser sees a prefix operator and the formatter keeps it whole.
        if (peek(1) == '+') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::NotGoal, "\\+", start));
        } else if (const ForeignOperator* foreign = foreignOperatorAt(source_, offset_);
                   foreign != nullptr) {
          advanceByte(foreign->text.size());
          reportInvalidSign(sink, start, foreignOperatorHint(*foreign));
          tokens.push_back(makeToken(TokenKind::Unknown, std::string(foreign->text), start));
        } else {
          advanceByte(1);
          reportInvalidSign(sink, start);
          tokens.push_back(makeToken(TokenKind::Unknown, "\\", start));
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
        reportInvalidSign(sink, start);
        tokens.push_back(makeToken(TokenKind::Unknown, std::string(1, ch), start));
        break;
    }
  }
  tokens.push_back(makeToken(TokenKind::EndOfFile, "", here()));
  return tokens;
}

}  // namespace prologd
