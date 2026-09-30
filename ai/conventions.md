# Coding and process conventions

## Language and standard

* C++23 (`CMAKE_CXX_STANDARD 23`, no compiler extensions).
* Target compilers: GCC ≥ 13, Clang ≥ 17, MSVC ≥ 19.51 (Visual Studio 2026).
  Visual Studio 2022 is no longer supported (ADR-013).
* Use the standard library; avoid raw `new`/`delete`, raw owning pointers and
  C-style casts. `reinterpret_cast` is forbidden in new code.
* Prefer `std::string`, `std::string_view`, `std::vector`, `std::optional`,
  `std::variant`, `std::expected` (where available) and `std::span`.

## Naming

| Entity | Convention | Example |
|--------|-----------|---------|
| Namespace | lower case | `prologd` |
| Type / class | `CamelCase` | `TermStore`, `BigInt` |
| Function / method | `camelCase` | `unifyTerms`, `parseClause` |
| Member variable | `snake_case_` (trailing underscore) | `bindings_` |
| Local variable | `snake_case` | `choice_point` |
| Constant / enumerator | `CamelCase` for scoped enum values, `kCamelCase` for constants | `TokenKind::LeftParen`, `kMaxArity` |
| File | `snake_case.hpp` / `snake_case.cpp` | `term_store.hpp` |

Built-in predicate names are Russian and must be written with UTF-8 in string
literals. Never split a multi-byte character.  Every built-in with a Russian name
also has an English spelling in lower case (`НАЙТИВСЁ`/`findall`), registered from
the one table in `builtins.cpp`; `test_aliases.cpp` fails if a Russian name has no
row there, and the correspondence table in `doc/help.typ` (appendix 17) must be
regenerated when the table changes.  Names the engine or the parser answers
(`ВЫП`/`call`, `ИМПОРТ`/`import`) are listed in `keywords.cpp`/`parser.cpp`
instead.

## File layout

* Public headers: `src/prlib/include/prlib/<name>.hpp`.
* Implementation: `src/prlib/src/<name>.cpp`.
* One class per header pair where practical; free functions grouped by topic.
* Every header starts with `#pragma once` and includes what it uses.
* Tests: `src/tests/test_<topic>.cpp` plus `test_main.cpp` if a custom main is
  needed.

## Errors and diagnostics

* Parse and evaluation errors use a single `PrologError` type carrying an
  `ErrorCode` category, a `std::string message` and a `SourceLocation`
  (file, line, column).
* `ErrorCode` is a *semantic* category (lexical, syntax, runtime), not the
  historical PrologD numbering. The numbers are gone; categories may be added
  freely and the user-facing text comes from `errorCodeText`.
* The CLI prints diagnostics in the usual compiler shape:
  `<file>:<line>:<column>: error: <message>`.
* Error messages are lower-case Russian phrases without a trailing period, so
  they read well after the `error: ` prefix; predicate-specific messages use the
  form `<ПРЕДИКАТ>: <пояснение>`.
* No exceptions for control flow inside the engine; exceptions are reserved for
  unrecoverable I/O and for engine-internal guards that must not be swallowed.
* Every user-visible string is UTF-8; the process sets the UTF-8 code page on
  Windows (`SetConsoleOutputCP(CP_UTF8)` in the CLI).

## Python (the GUI in `src/gui`)

* PEP 8, four-space indentation, `from __future__ import annotations` and type
  hints on public functions.
* The only dependency is PySide6.  Qt-free modules (`protocol.py`) must stay
  importable without it so the wire format can be tested headlessly.
* Comments and identifiers are English; strings the *user* sees in the GUI are
  Russian, like the interpreter's diagnostics and `doc/*.typ`.
* Tests: `src/gui/tests/*.py`, runnable with a bare interpreter
  (`python src/gui/tests/protocol_smoke.py`), not with a test framework.

## Testing policy

* Front-end test scripts (`src/gui/tests/*.py`) print **ASCII only** — use
  `ascii(value)` for a value that may contain Cyrillic.  The reason is not
  tidiness: when their output is piped (through `Select-String`, `grep`, a
  redirect) Python encodes stdout with the *ANSI code page*, and on a cp1252
  machine a raw Cyrillic message raises `UnicodeEncodeError` while printing the
  failure — hiding the failure it was reporting.  Unpiped output goes to the
  console code page (65001 here) and would have worked, which is exactly why the
  trap is easy to walk into.

Tests are written **together with** the feature, never after.

* Framework: Catch2 v3 via `FetchContent`.
* A feature is not done until it has tests. Required test groups:
  * parser: one test per error category;
  * unification: variables, atoms, numbers, structures, lists, occurs cases;
  * engine: backtracking order, cut, failure, deep recursion, `ВЫП`, `НЕ`, `ИЛИ`;
  * arithmetic: each operator, mixed int/float, division by zero, big values;
  * one test file per built-in predicate group;
  * `НАЙТИВСЁ/3` with the exact examples from the requirements;
  * typical tasks: factorial, Fibonacci, GCD, sorting, N-queens, water jugs,
    knapsack, monkey & bananas.
* Golden tests: the ported `test.txt` corpus is executed by a Catch2 generator
  (`TEST`/`INPUT`/`EXPECTED`/`END` format) once the porting task is complete.
* Long-running test programs must be bounded (iteration limits) so CI stays fast.

## Commit / change hygiene

* Keep the build green: `cmake --build build` and `ctest --test-dir build` must
  pass before a task is marked done.
* Update `ai/status.md` and the task file status after every work session.
* Any deviation from this plan is recorded in `ai/decisions.md`.

## Documentation

* `doc/*.typ` is Russian; code fences and identifiers stay as-is.
* User help (`help.typ`) is updated in the same change that adds a predicate.
* `technical.typ` describes invariants and algorithms in a scientific style
  (problem statement, model, algorithm, complexity, limitations).
* `prologd-diff.typ` lists every syntax/behaviour change relative to PrologD,
  with a short before/after example per item.

## The original material

The previous implementation of PrologD (the CP1251 sources, the user help, the
examples, the test corpus and the Qt GUI) is published at
<https://github.com/Ununus/prologd>. No local copy is kept in `ai/`; consult the
repository instead.
