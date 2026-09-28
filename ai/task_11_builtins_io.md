# task_11 — Built-ins: input/output

**Status:** done
**Depends on:** task_09
**Milestone:** M5

## Goal

Implement the I/O predicates and the stream abstraction so tests can drive
input/output deterministically.

## Deliverables

- [ ] `include/prlib/io.hpp`, `src/io.cpp`
  * `IIOStreams` interface / `IoContext` owning the current input and output
    streams, current file names, and the interactive input provider.
  * `ConsoleIo` (stdin/stdout), `FileIo` (open/close), `StringIo` (in-memory,
    used by tests).
  * Newline handling identical to the original: `ВЫВОД` writes no newline; the
    solution printer inserts a newline before `ДА`/`НЕТ` if needed.
- [ ] `src/builtins_io.cpp`
  * `ВЫВОД/1..n` (variable arity, up to a documented maximum, original allowed
    arbitrary counts — implement as a variadic dispatch by arity).
  * `ПС/0` (library clause via `ВВКОД`), `ЖДИ/1`, `ВВКОД/1`.
  * `ВВОДЦЕЛ/1,2`, `ВВОДВЕЩ/1,2`, `ВВОДСИМВ/1,2`, `ВВОДСТР/1,2`.
  * `ЧТЕНИЕ_ИЗ/1`, `ЗАПИСЬ_В/1` (open/close/query current file; `""`/`con:` =
    console; append `.pld` when the name has no extension, as documented).
  * `ТИХО` interaction with solution printing.
- [ ] `$`-prefixed preloaded input lines: parse them out of the source before
  interpretation (test harness feature from the original CLI); support also
  `-i FILE`.

## Design notes

* Reading semantics: if a file input stream is open, use `operator>>`
  token extraction for `ВВОДЦЕЛ/ВВОДВЕЩ/ВВОДСИМВ` and `getline` for
  `ВВОДСТР`; with console input and captions, print the caption through the
  output stream (the original called `pldout(caption)`).
* `ВВОДЦЕЛ(3.3)` must raise `ВВОДЦЕЛ: Недопустимый тип аргументов` (the
  original threw when the first argument was neither integer nor unbound
  variable); reproduce the message and code.
* `ВВКОД` in the original reads a single byte; in UTF-8 mode define it as
  reading one Unicode code point and writing the UTF-8 encoding of the code
  point. Document in `prologd-diff.typ`.
* File paths use `std::filesystem`; on Windows accept both `/` and `\`.

## Tests

- [ ] `test_builtins_io.cpp` using `StringIo`:
      * `ВЫВОД` of int/float/atom/string/list/compound, no trailing newline;
      * `ПС` newline; `ВВКОД` write/read;
      * `ВВОДЦЕЛ`/`ВВОДВЕЩ`/`ВВОДСИМВ`/`ВВОДСТР` with preloaded input and with a
        temp file;
      * `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` round-trip through a temp file;
      * error cases from the original `prologd_test/test.txt` (`Input Int Error`,
        `Input Float Err`);
      * `ТИХО` suppresses `ДА`/`НЕТ` but not `ВЫВОД`.

## Acceptance

The `Input Int`, `Input Float`, `Input`, `Output`, `QUIET` scenarios from the
original corpus reproduce after variable renaming.
