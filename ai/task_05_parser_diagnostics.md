# task_05 — Parser, AST/program construction and diagnostics

**Status:** done
**Depends on:** task_04
**Milestone:** M2

## Goal

Parse the full surface language into clauses/terms, and report syntax errors
with semantic error categories.

## Deliverables

- [ ] `include/prlib/parser.hpp`, `src/parser.cpp`
  * `Parser` consumes tokens for one source unit and emits `Clause`s and
    queries into the `Database` / a `Query` list.
  * Grammar (documented in `technical.typ`):
    ```
    Program    := { Clause | Directive | Query }
    Clause     := Head [ (':-' | '<-') Body ] ('.' | ';')
    Query      := ('?' | '?-') Body ('.' | ';')
    Directive  := ':-' Term ('.' | ';')        % e.g. :- ИМПОРТ("f.pld").
    Body       := Goal {',' Goal}
    Goal       := Term
    Term       := Expr | Primary
    Expr       := '#' AddExpr '#'
    Primary    := Atom | Variable | Integer | Float | String
                | List | Compound | '(' Term ')'
    Compound   := Name '(' Term {',' Term} ')'
    List       := '[' ']' | '[' Term {',' Term} [ '|' Term ] ']'
    ```
  * `#expr#` sub-parser with precedence: `+ -` (lowest), `* / mod div`
    (higher), parentheses, unary minus. Output: an arithmetic AST term
    (`ArithExpr` compound name or dedicated kind) consumed by task_08.
  * Callable-terms sugar: allowing `НЕ foo(x)` (no parentheses) is **not**
    required; keep `НЕ(foo(x))`.
- [ ] `include/prlib/diagnostics.hpp`, `src/diagnostics.cpp`
  * `PrologError` (see `conventions.md`), `DiagnosticSink` collecting errors and
    warnings, and a formatter producing `file:line:column: error: message`.
- [ ] Parser rejects, with the following categories:
  * unterminated string (3), malformed number (4), missing `-` in `:-` (6),
    list used as a predicate (9), misplaced `?` (10), `_` as a goal (11),
    misplaced `!` (12), unpaired list brackets (14), wrong list (15),
    unpaired function brackets (16), missing functor before `(` (17), sign
    outside `#…#` (18), bad arithmetic expression (32), bad function parse
    (38), bad sentence (20).
- [ ] `parseFile(path)` and `parseString(text, virtual_name)` entry points.

## Design notes

* A clause head must be an atom or compound; a list/variable/number head is an
  error (20 or 9).
* `[H|T]` desugars to list cells; `[a,b|T]` builds nested cells.
* The parser records `SourceLocation` for each clause and each goal so runtime
  errors and `ПРЕДЛ` can report origins.
* Error recovery: on error, skip to the next clause terminator so one bad line
  does not abort the whole file (matches the original line-by-line behaviour).

## Tests

- [ ] `test_parser.cpp`
  * happy path: facts, rules (`:-` and `<-`), queries, `;` terminators,
    nested compounds, lists with tails, quoted atoms, Cyrillic names;
  * one negative test per error class listed above, asserting `ErrorCode` and
    location;
  * arithmetic precedence and parentheses;
  * empty file, comment-only file, trailing whitespace, CRLF;
  * a program with `#2+2*2#` parses to the expected AST.
- [ ] `test_diagnostics.cpp`: formatted message matches `file:line:column: error: message`.

## Acceptance

Every syntax error in the original `prologd_test/test.txt` has a passing parser
test (the message may differ; the category must match).
