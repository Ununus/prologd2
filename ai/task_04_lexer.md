# task_04 — UTF-8 lexer

**Status:** done
**Depends on:** task_02
**Milestone:** M2

## Goal

Implement a UTF-8 aware lexer for the PrologD surface language with precise
source locations.

## Deliverables

- [ ] `include/prlib/lexer.hpp`, `src/lexer.cpp`
  * `TokenKind`: `Identifier, Variable, Integer, Float, String, QuotedAtom,
    Comma, Dot, Semicolon, Question, ColonDash, Arrow, Bang, Hash, Plus, Minus,
    Star, Slash, LParen, RParen, LBracket, RBracket, Bar, EndOfFile`.
  * `Token { TokenKind kind; std::string text; SourceLocation loc; }` with the
    decoded UTF-8 bytes in `text` (never split code points).
  * Integer and float literals, including the original's rejection of malformed
    numbers (`12.123.123`, `--33`) with `ErrorCode::InvalidNumberFormat`.
  * String literal `"…"` with `ErrorCode::InvalidStringFormat` on an unterminated
    string.
  * Quoted atom `'…'` with `''` escaping per standard Prolog.
  * Comments `%…` to end of line.
  * `#` and `#` handled as plain tokens; the expression grammar is parsed by the
    parser.
  * Identifier classification:
    - `_` or `_Name` → `Variable`
    - first code point is an upper-case letter (Unicode-aware for Cyrillic and
      Latin) → `Variable`
    - name matches a reserved built-in → `Identifier` (atom), ADR-005
    - otherwise → `Identifier` (atom)
- [ ] `include/prlib/utf8.hpp` — decode/iterate code points, `isUpperLetter`,
      `isLowerLetter`, `isLetter`, `isDigit`, UTF-8 validation.
- [ ] `include/prlib/string_escape.hpp` — helpers to escape/unescape quoted
      atoms and strings.

## Design notes

* Treat digits as Unicode `Nd`-lite: at minimum ASCII `0-9` plus the Cyrillic
  digits are not used in practice; document ASCII-only digits.
* A name character is a letter, digit or `_`. Underscore inside a name is
  allowed.
* `:-` vs `:` alone: produce `ColonDash` only for `:-`; a lone `:` is an error
  (`InvalidCharacter`).
* The old scanner allowed `<` as the start of `<-`; `<-` must not be tokenised
  as a relational operator (the language has none).
* Keep `?` as a token; `? -` with whitespace should also parse as a query in
  the parser for convenience (documented).

## Tests

- [ ] `test_lexer.cpp`
  * every token kind, with positions;
  * Cyrillic identifiers and multi-byte code points in strings;
  * `_`, `_X`, `X`, `x`, `Ёж`, `'quoted atom'`;
  * reserved built-in names lex as identifiers, a random upper-case name lexes
    as a variable;
  * malformed numbers/strings yield the right `ErrorCode` and location;
  * comments and CRLF input.

## Acceptance

All lexer tests pass, including a round-trip test that re-concatenates token
text and compares with the (whitespace-normalised) input.
