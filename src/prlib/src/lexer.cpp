#include "prlib/lexer.hpp"

#include <array>

#include "prlib/utf8.hpp"

namespace prologd {

namespace {

const std::unordered_set<std::string> kReservedBuiltins = {
    // Control / logic, with the English spelling of each name (task_39).
    // `ИЛИ` is the one name here without an English twin: it is the word of the
    // original dialect, kept for the programs written for it, and its English
    // spelling `or` stays retired (task_44) — the English vocabulary is
    // `ПЕРВОЕ`/`first` (task_83).
    "ЛОЖЬ", "ТРАССА", "НЕТ_ТРАССЫ", "ВЫП", "НЕ", "ДЛЯВСЕХ", "ПЕРВОЕ", "ИЛИ",
    "РАВНО", "ТИХО", "ВЕРСИЯ", "ПС", "ЗАВЕРШЕНИЕ",
    "fail", "trace", "no_trace", "call", "not", "forall", "first", "equal",
    "quiet", "version", "nl", "halt",
    // Arithmetic.  The English predicates are capitals (`ABS/2`) and the
    // functions of an expression are lowercase (`abs(X)`), so both spellings are
    // reserved: one is a goal, the other is a name inside `#…#`.
    "БОЛЬШЕ", "МЕНЬШЕ", "СЛОЖЕНИЕ", "УМНОЖЕНИЕ", "СЛУЧ", "float", "mod", "div",
    "rem", "sign", "pi", "floor", "ceiling", "round", "truncate",
    "ABS", "SQRT", "SIN", "COS", "TAN", "EXP",
    "greater", "less", "plus", "mul", "random", "abs", "sqrt", "sin",
    "cos", "tan", "exp", "log", "is_whole", "is_number",
    // I/O
    "ЧТЕНИЕ_ИЗ", "ЗАПИСЬ_В", "ВВКОД", "ВВОДЦЕЛ", "ВВОДВЕЩ", "ВВОДСИМВ",
    "ВВОДСТР", "ВЫВОД", "ВЫВОДПС", "ЖДИ",
    "see", "tell", "put_code", "read_int", "read_float", "read_char",
    "read_string", "write", "writeln", "wait",
    // Strings
    "БУКВА", "ЦИФРА", "СЦЕП", "КОПИЯ", "ДЛИНА",
    "is_letter", "is_digit", "concat", "strlen",
    // `sub_string/5` is ISO's name for the work `КОПИЯ/4` does from one, and
    // `ПОДСТРОКА/5` is the same predicate in Russian (task_84): both are
    // reserved, and its old English alias `substring` is retired below.
    "ПОДСТРОКА", "sub_string",
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
    // The standard order of terms (task_90): the dialect's own name is `СРАВНЕНИЕ`,
    // and `compare` is its English spelling — the call the four `@` signs are sugar
    // for (task_94).
    "СРАВНЕНИЕ", "compare",
    // Newcomers
    "НАЙТИВСЕ", "ИМПОРТ", "findall", "import",
    // The canvas of a program (ADR-035): `:- ХОЛСТ(Высота, Ширина).`
    "ХОЛСТ", "canvas",
    // Collecting by groups (task_91): `ВСЕРЕШ`/`МНОРЕШ` are the dialect's names,
    // `bagof`/`setof` the English ones.
    "ВСЕРЕШ", "МНОРЕШ", "bagof", "setof",
    // The identity goal (part 158): `(A -> B ; ИСТИНА)` is the ISO reading of
    // «если — то», and the word `true` is its English spelling.
    "ИСТИНА", "true",
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
    // The marker of the naming modes, and its English spelling (task_107).  The
    // modes are gone: this dialect reads names the way ISO does, and there is
    // nothing to declare on a file's first line.  The names stay reserved so that
    // a file written for the old reader is told why it no longer loads instead of
    // being answered «не найдено».
    "ИМЕНА",
    "variables",
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
    {"\\==", "«\\==» — не оператор: «термы не совпадают» — это «НЕ(A = B)"},
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

Lexer::Lexer(std::string_view source, std::string file_name)
    : source_(stripByteOrderMark(source)), file_name_(std::move(file_name)) {}

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
  // A reserved name is a predicate whatever its case is (ADR-005).
  if (isReservedBuiltinName(text)) {
    return makeToken(TokenKind::Identifier, std::move(text), start);
  }
  // ISO's rule and the only one this dialect has: an upper-case initial makes a
  // variable, anything else a name.
  if (first.valid && isUpperCaseLetter(first.code_point)) {
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
    if (ch == '\n') {
      break;
    }
    if (ch == '\\') {
      const char escaped = peek(1);
      const char* decoded = nullptr;
      switch (escaped) {
        case 'n': decoded = "\n"; break;
        case 't': decoded = "\t"; break;
        case 'r': decoded = "\r"; break;
        case '\\': decoded = "\\"; break;
        case '"': decoded = "\""; break;
        default: break;
      }
      if (decoded == nullptr) {
        // A backslash that escapes nothing, which is almost always a typo.  The
        // message lists what there is, and one message per literal is enough:
        // three typos in a row are the same lesson.
        if (sink != nullptr) {
          PrologError error;
          error.code = ErrorCode::InvalidStringLiteral;
          if (escaped == '\0' || escaped == '\n') {
            error.message = "escape-последовательность не закончена: после «\\» нужен символ";
          } else {
            error.message = std::string("неизвестная escape-последовательность «\\") +
                            escaped + "»: в строке есть только \\n, \\t, \\r, \\\\ и \\\"";
          }
          error.location = here();
          error.isParseError = true;
          sink->report(std::move(error));
          sink = nullptr;
        }
        value.push_back(ch);
        advanceByte(1);
        continue;
      }
      value.push_back(*decoded);
      advanceByte(2);
      continue;
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
    if (ch == '/' && peek(1) == '*') {
      // `/* … */` — ISO's block comment (task_92).  It does not nest, as in ISO,
      // and the closing `*/` may sit lines away.  The text is skipped here; the
      // formatter leaves a file that has one exactly as it is written, so no
      // comment can be lost.
      const SourceLocation start = here();
      advanceByte(2);
      bool closed = false;
      while (!atEnd()) {
        if (peek() == '*' && peek(1) == '/') {
          advanceByte(2);
          closed = true;
          break;
        }
        advanceByte(1);
      }
      if (!closed) {
        reportInvalidSign(sink, start, "не закрыт комментарий «/*»");
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
      case '*':
        // `**` is ISO's power and a sign of its own: `2**3` must not read as
        // two multiplications.  `/` does the same for `//`, and `/*` never
        // reaches either case — block comments are read before this switch.
        if (peek(1) == '*') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::StarStar, "**", start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Star, "*", start));
        }
        break;
      case '^':
        // `^` is ISO's existential quantifier (task_91): `ВСЕРЕШ(Х, У^Ц, С)` says
        // «У of the goal does not matter», so the bag is not split by it.  It is
        // a token of its own so the parser can bind it tighter than `,`.
        advanceByte(1);
        tokens.push_back(makeToken(TokenKind::Caret, "^", start));
        break;
      case '/':
        // `//` is ISO's integer division, and `/*` never reaches this switch —
        // block comments are read before it.  Two signs, one token: `6 // 2` is
        // not `6 / / 2`, and `//` must not be read as two divisions.
        if (peek(1) == '/') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::SlashSlash, "//", start));
        } else {
          advanceByte(1);
          tokens.push_back(makeToken(TokenKind::Slash, "/", start));
        }
        break;
      case '(': advanceByte(1); tokens.push_back(makeToken(TokenKind::LParen, "(", start)); break;
      case ')': advanceByte(1); tokens.push_back(makeToken(TokenKind::RParen, ")", start)); break;
      case '[': advanceByte(1); tokens.push_back(makeToken(TokenKind::LBracket, "[", start)); break;
      case ']': advanceByte(1); tokens.push_back(makeToken(TokenKind::RBracket, "]", start)); break;
      case '|': advanceByte(1); tokens.push_back(makeToken(TokenKind::Bar, "|", start)); break;
      case '{':
        // Curly braces are ISO's dicts (`_{ключ: значение}`) and its `{Цель}`
        // shorthand for a call; the dialect has neither, and the bare
        // «недопустимый символ» leaves the reader guessing (task_82, stage 4).
        // Only the opener is explained: the closer would repeat the same
        // sentence for the same construct.
        advanceByte(1);
        reportInvalidSign(sink, start,
                          "фигурных скобок в Пролог-Д нет: словарей и «{Цель}» "
                          "здесь не бывает, а блок целей берут в круглые скобки");
        tokens.push_back(makeToken(TokenKind::Unknown, "{", start));
        break;
      case '}':
        advanceByte(1);
        reportInvalidSign(sink, start);
        tokens.push_back(makeToken(TokenKind::Unknown, "}", start));
        break;
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
        // match first: `=:=` and `=\=` are the arithmetic comparisons of ISO
        // (task_92), `=<` is «less or equal», while `==` belongs to other
        // Prologs and gets advice instead of a token.
        if (peek(1) == ':' && peek(2) == '=') {
          advanceByte(3);
          tokens.push_back(makeToken(TokenKind::ArithEqual, "=:=", start));
        } else if (peek(1) == '\\' && peek(2) == '=') {
          advanceByte(3);
          tokens.push_back(makeToken(TokenKind::ArithNotEqual, "=\\=", start));
        } else if (const ForeignOperator* foreign = foreignOperatorAt(source_, offset_);
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
        // `\=` is «не унифицируется» (task_92), and `\==` stays advice: identity
        // of terms is not a thing this dialect has.
        if (peek(1) == '+') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::NotGoal, "\\+", start));
        } else if (peek(1) == '=' && peek(2) != '=') {
          advanceByte(2);
          tokens.push_back(makeToken(TokenKind::NotEqual, "\\=", start));
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
