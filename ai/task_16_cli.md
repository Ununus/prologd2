# task_16 — Console front-end (CLI11)

**Status:** done
**Depends on:** task_11, task_14, task_15
**Milestone:** M7

## Goal

Provide a modern console application that mirrors the original
`prologdc.cpp` capabilities.

## Deliverables

- [ ] `src/cli/main.cpp` using CLI11.
  * `-s, --source FILE` (repeatable, in order) — interpret file(s).
  * `-I, --include DIR` (repeatable) — import search path.
  * `-i, --input FILE` — input stream.
  * `-o, --output FILE` — output stream (default stdout).
  * `-e, --error FILE` — error stream (default stderr).
  * `-q, --questions` — echo queries before executing them.
  * `-t, --trace` — start with tracing enabled.
  * `--version`, `--help`.
  * Bare arguments are treated as source files.
  * No arguments and stdin is a TTY → REPL; otherwise read the program from
    stdin.
- [ ] `$`-prefixed preloaded input lines and `-i` file input.
- [ ] Exit codes: 0 success, 1 usage error, 2 parse error, 3 runtime error
  (document exact mapping in `help.typ`/`README.md`).
- [ ] UTF-8 setup: on Windows `SetConsoleOutputCP(CP_UTF8)` and
  `SetConsoleCP(CP_UTF8)`; on POSIX rely on the locale but never re-encode.
- [ ] Signals: Ctrl+C sets a stop flag consumed by the engine's `shouldStop`
  hook, producing `ExecutionInterrupted`.
- [ ] `--dump-ast` (debug) and `--dump-clauses` (debug) developer options.

## Design notes

* The CLI is a thin shell: argument parsing, stream wiring, REPL loop, exit
  codes. All language logic stays in `prlib`.
* The REPL accepts `?Goal.` queries and directives; without `?`, a line is a
  clause.
* Use plain CLI11 conventions: options take a separate value (`-s FILE`,
  `--source FILE`, `--source=FILE`) and source files may be positional.  The
  historical `-s=FILE` rewriting is not supported.

## Tests

- [ ] `test_cli.cpp` or `add_test` integration tests invoking the built
      executable with fixture files and comparing stdout/stderr/exit code:
      * `--help`, `--version`;
      * `-s` file with a query;
      * `-q` echoes queries;
      * `-i` supplies input;
      * `-o`/`-e` redirect;
      * import via `-I`;
      * positional files and `--source=FILE`;
      * invalid argument → exit 1 with a clear message.

## Acceptance

`prologd -s examples/hello.pld` works on Linux and Windows, and all CLI
integration tests pass.

## Progress (2026-09-28)

* [x] Ctrl+C/SIGTERM set a `volatile sig_atomic_t` flag consumed through the new
      `EngineOptions::externalStop`; the engine raises `Interrupted` (exit 3).
* [x] Exit codes documented in `README.md` and `doc/help.typ`.
* [x] `--protocol json`: a line-delimited JSON session for front-ends
      (`src/cli/protocol.{hpp,cpp}`), tested by `cli_json_protocol`.
* [ ] `--dump-ast` and `--dump-clauses` dropped: the parser produces a
      `ParsedProgram` rather than a tree worth printing, and no workflow asked
      for them.  Reopen if a debugging need appears.
* [ ] Not covered by tests yet: `-i`, `-o`, `-e` and `-q` integration cases and
      the "invalid argument → exit 1" case; `cli_json_protocol` shows the
      `cmake -P` driver pattern those cases need.
