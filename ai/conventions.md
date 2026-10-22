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
also has an English spelling in lower case (`НАЙТИВСЕ`/`findall`), registered from
the one table in `builtins.cpp`; `test_aliases.cpp` fails if a Russian name has no
row there.  That test names the exceptions one by one, and there are two kinds:
names the engine or the parser answers (`ВЫП`/`call`, `ИМПОРТ`/`import`), and the
names whose English twin *is* a predicate of its own: `ИЛИ/2` (task_83) — the word
of the original dialect, kept so that programs written for it load, with `first`
(the alias of `ПЕРВОЕ`) as the English vocabulary and `or` retired — and `КОПИЯ/4`
(task_84), which lost `substring` because the ISO predicate of the same work is
`sub_string/5`, with positions from zero.  A built-in is described **in `doc/builtins.json`** (one record: summary,
argument modes, the `help.typ` section, the English spelling) — so a new built-in is
added to `builtins.cpp`, to the lexer's reserved set *and* to `doc/builtins.json`,
and `src/gui/tests/test_reference.py` fails when the three disagree.  The
correspondence table in `doc/help.typ` (appendix 17) is built from that file, not
edited by hand.  Names the engine or the parser answers
(`ВЫП`/`call`, `ИМПОРТ`/`import`) are listed in `keywords.cpp`/`parser.cpp`
instead.  An English name that no Russian name owns follows one rule: bare only
where the standard means the same thing (`var`, `integer`, `float`, `compare`),
`is_` for a check of ours (`is_text`, `is_list`, `is_letter`, `is_digit`,
`is_whole`, `is_number`), and `X_to_Y` with the short stems `int`, `float`,
`str`, `list` for a conversion (`int_to_float`, `str_to_int`).

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
* Every diagnostic carries a `Severity`.  `Error` stops a load or a query;
  `Warning` is advice — it never changes a load's success or an exit code
  (`DiagnosticSink::hasErrors` counts errors only, and `--no-warnings` drops only
  warnings).  A new check has to answer two questions before it is written: what
  severity, and what the position points at.  The position names the thing to
  fix — the opening bracket, the end of the clause, the goal — never "wherever
  the parser happened to be".
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
  * engine: backtracking order, cut, failure, deep recursion, `ВЫП`, `НЕ`, `ПЕРВОЕ`;
  * arithmetic: each operator, mixed int/float, division by zero, big values;
  * one test file per built-in predicate group;
  * `НАЙТИВСЕ/3` with the exact examples from the requirements;
  * typical tasks: factorial, Fibonacci, GCD, sorting, N-queens, water jugs,
    knapsack, monkey & bananas.
* Golden tests: the ported `test.txt` corpus is executed by a Catch2 generator
  (`TEST`/`INPUT`/`EXPECTED`/`END` format) once the porting task is complete.
* Long-running test programs must be bounded (iteration limits) so CI stays fast.

## Versioning

* The version has **one source**: `project(prologd VERSION x.y.z)` in `CMakeLists.txt`.
  CMake injects it into the generated `src/prlib/src/version.cpp`, so it reaches
  `--version`, the `ready` event of the protocol (the window shows it in «О программе» and
  in the status bar, and keeps no copy of its own) and the built-in `ВЕРСИЯ/0`, which prints
  the version with `PROLOGD_BUILD_DATE` — a `string(TIMESTAMP … UTC)` taken when CMake
  configures, so a bump is a reconfigure (the build does that by itself).
* The **product name** sits beside the number — `set(PROLOGD_PRODUCT_NAME "Пролог-У")` —
  and is injected the same way, through the generated source and *not* a `-D` macro: a
  non-ASCII value on the compiler's command line travels through a response file in the
  machine's ANSI code page.  One function, `versionBanner()` (`Пролог-У 2.4.0
  (2026-10-20)`), is what both `--version` and `ВЕРСИЯ/0` print, so the two cannot drift
  (task_76).  Consequence for scripts: `--version` is a *sentence*, so the number has to
  be read out of it (`tools/build_portable.ps1` matches `\d+\.\d+\.\d+`).
* The **protocol version is a counter of its own** (`PROTOCOL_VERSION` in
  `src/gui/prologd_gui/protocol.py`, 13 as of 2.2.0, pinned by `protocol_smoke.py` and
  `test_formatter.py`): it moves when the protocol moves, not when the program does.
* The **naming mode** is a property of a *file*, never of a build: the first line
  `:- ИМЕНА(N).` beats `--vars` and the window's row, and an imported file is read in
  its own mode.  The rule lives once, in C++ (`readVariableMarker` in
  `src/prlib/src/lexer.cpp`, used by the loader *and* the formatter); the window
  repeats it for colouring alone (`tokens.mode_from_first_line`) and
  `src/gui/tests/test_variable_modes.py` checks that repetition against the
  interpreter's own reading of the same first lines.  There are **two** modes since
  task_77: `0` ISO and `1` the old dialect — one-letter variables, unquoted string
  constants and apostrophe names.  `2` is a *spelling* of `1`, accepted everywhere a
  number names a mode (`variableModeFromNumber` in C++, `tokens.MODE_NUMBERS` in
  Python, and the settings row answers a stored `2` as `1` instead of falling back
  to ISO): the two were one dialect all along, because the original reads `число'`
  in a file that declares nothing.
* The **original engine** (`Ununus/prologd`) is built as a *nested* CMake project by
  `-DBUILD_WITH_PROLOGD=ON` (task_78) and written beside ours
  (`src/cli/<config>/prologd.exe`).  It is deliberately not pulled into this graph: its
  targets are named `prlib` and `prologd_json` — both names this tree already uses — it
  is C++17 where this tree is C++23, and its sources are CP1251.  Three facts about it
  cost real time to find, and a front-end or a script has to know all three:
  * it answers **protocol 13 as a *subset* of ours** (its own `src/protocol.cpp` says
    so), so the protocol number cannot tell the two engines apart — a capability table
    per engine is the only honest way (task_79);
  * its command line has no `--version`, and **every option needs the `=` form**: `--source=FILE`
    and `-s=FILE` work, while `-s FILE`, `-sFILE` and a bare file name are all `Invalid argument`
    (its `--help` prints `-s, --source=FILE`, which reads as if the separated form were fine — it
    is not; measured 2026-10-13, after an earlier note got this wrong).  `--list-keywords` is the
    one command both engines answer;
  * it maps every line it reads back to CP1251 (`run_line` in `src/prologdc.cpp`), so one
    character CP1251 cannot carry — `—`, `«`, `»`, `…` — turns the whole line into
    `Недопустимый символ`.  A file that must run on it stays ASCII plus Russian letters.
* The **engine table** (`src/gui/prologd_gui/engines.py`, task_79) is the one place that says what an
  engine can do, and the window asks it rather than guessing from the protocol number.  A capability
  (`FORMAT`, `STEP`, `TRACE`, `GRAPHICS`, `LIMITS`, `NAMING`) is declared where the *demand* is —
  `Action.needs` for a menu or toolbar entry, `settings.GATED_ROWS` for a row of the dialog — and
  `src/gui/tests/test_engines.py` fails in both directions: a requirement no engine has, and a
  capability no command or row asks about (prose dressed as a table).  Which engine a launch uses is
  `engines.launch(pin, chosen)` — `--exe` (or the value task_46's removed «Интерпретатор» row still
  holds) names the *folder* both engines are built in **and**, when its file name is one of them, the
  engine; `view/engine` is the stored choice, written by the button at the right end of the toolbar.
  A switch **stops the session** rather than asking the run to end: a live process belongs to the
  engine being left, and its events would land in the output of a window that says it runs the other
  one.  The button's picture is the engine that is *running* (`u.png` / `d.png`), so the toolbar
  says which program it belongs to; the tooltip names the other one.  A capability also decides
  *reading*: «Имена переменных» is a fallback for a file that declares none, so under an engine
  without `NAMING` a marker-less file is coloured, completed and sent as the old dialect
  (`window._default_variable_mode`, one door: `_apply_dialect`).  A file with a `:- ИМЕНА(N).`
  first line keeps its own mode on either engine — the dialect belongs to the file.
* Bumping the program version means moving every *live* copy of the literal — grep for the
  old number rather than trusting memory:
  * the `cli_version` test in `src/tests/CMakeLists.txt` follows by itself now: its pattern
    is built from `${PROJECT_VERSION}` (before task_74 it held the literal, with escaped
    dots, and a grep for the number could not find it);
  * `examples/lessons/appendix_debug.pld` — the example line of the lesson about `ВЕРСИЯ`,
    which is the whole banner, product name and date included;
  * `src/gui/README.md` — the `ready` example, with the protocol number beside it (10 was
    left stale there for two protocol versions);
  * `tools/check_dependencies.py` — the default package path.
  The `ai/` notes that quote a version (`task_61`, the ADRs, the journal) are **records of
  what was true then** and stay as they are — the rule the old section numbers follow.
* The release routine (task_61, `tools/build_portable.ps1`): Release build → `ctest` →
  `docs` (six PDFs) → PyInstaller for the window → `dist/prologd-<version>-win64` (the name
  comes from `prologu.exe --version`, which the script reads itself and then checks again
  inside the package) → the script's own checks → zip.  `-SkipTests`, `-SkipFreeze`,
  `-NoTrim`, `-NoZip` shorten a round.
* Three package flavours (part 143), `-Engine`:
  * `both` (default) — `prologu.exe` + `prologd.exe`, our examples, our `stdlib`, six
    manuals;
  * `u` — ours only;
  * `d` — the original alone: `dist/prologd-<its version>-win64` (its number is the
    `project(... VERSION …)` line of the pinned `CMakeLists.txt`, because the engine has no
    `--version`), `examples/prologd` as `examples`, `doc/help.pdf` compiled from the pinned
    `help.typ`, the pinned `builtins.json` (the `F1` dock reads it), our `gui.pdf`, and no
    `stdlib` — our library is written in our dialect.  The window of such a package opens on
    that engine and has no engine switch (`paths.starting_engine`, `_sync_engine_button`).
    What each kind carries is the `$kinds` table at the top of the script (part 150); a new
    difference belongs there, not in another `if` inside a step.

## Commit / change hygiene

* Keep the build green: `cmake --build build` and `ctest --test-dir build` must
  pass before a task is marked done.
* An edit under `examples/` moves pinned numbers elsewhere, so `ctest` alone is
  not enough: `src/gui/tests/test_queries.py` counts the statements of every
  example file (refresh the table with `--print` when a lesson changed on purpose)
  and `test_lessons.cpp` runs them.  A lesson edit has already left that script
  red for a whole round.  Two folders are outside the corpus on purpose — the
  checks walk past them: `examples/lessons/_old` (the ported originals, task_47)
  and `examples/prologd` (the original dialect's own programs, task_86).  Both are
  skipped by their *first path component*, so a folder whose name merely begins
  with `prologd` is not caught by the skip.
* Inserting one section into `help.typ` renumbers every section after it, and those
  numbers are quoted outside the manual: `section` in `doc/builtins.json`, prose in
  `prologd-diff.typ` («таблица кодов, раздел 6.4»), the `%`-comments of the
  lessons, and the plans of tasks that have not started.  Grep the old numbers
  across the tree in the same change: `test_reference.py` only checks that a
  `section` is *some* heading of the manual, not that it is the right one.
* `.pld` sources stay within the alphabet the *original* engine reads: it refuses
  `—`, `–`, `−`, `…`, `№` and `§` even inside a `%` comment («Недопустимый
  символ»), although it reads UTF-8 like we do.  Write `-` and `...`.  `#…#`
  expressions and `/* */` comments are ours and need rewriting anyway before a
  file can be run by the original (part 142).
* Update `ai/status.md` and the task file status after every work session.
* Any deviation from this plan is recorded in `ai/decisions.md`.

## Documentation

* `doc/*.typ` is Russian; code fences and identifiers stay as-is.
* User help (`help.typ`) is updated in the same change that adds a predicate.
* `technical.typ` describes invariants and algorithms in a scientific style
  (problem statement, model, algorithm, complexity, limitations).
* `prologd-diff.typ` lists every syntax/behaviour change relative to PrologD,
  with a short before/after example per item.
* After editing a document, build the PDFs (`--target docs`) *and look* at the
  pages that carry the change — Typst reports syntax errors, not a table that
  overflows the margin or a paragraph that lost its spacing.

## The original material

The previous implementation of PrologD (the CP1251 sources, the user help, the
examples, the test corpus and the Qt GUI) is published at
<https://github.com/Ununus/prologd>. No local copy is kept in `ai/`; consult the
repository instead.
