# Status tracker

Last updated: after the Windows/VS 2026 verification and the GUI protocol
session.

## Overall

* Phase: feature-complete core, verified on Windows; the PySide6 front-end has
  started (protocol + skeleton).
* Build: the `windows-msvc` preset (Visual Studio 18 2026, MSVC 19.51) build is
  green locally; the Linux presets, including `-Werror`, build cleanly.
* Tests: 108/108 pass in about a second, including 8 command-line/integration
  tests and the JSON protocol session.
* CLI: `build/windows-msvc/src/cli/Release/prologd` runs files (positional, `-s`
  or `--source`), stdin, the REPL and the `--protocol json` session for
  front-ends.
* GUI: `src/gui` (PySide6) drives the executable through the JSON protocol; the
  protocol client is verified headlessly, the window itself still needs a
  machine with PySide6.
* Documentation: `doc/help.typ`, `doc/technical.typ`, `doc/prologd-diff.typ`
  written (Russian); `cmake --build build --target docs` compiles them when
  `typst` is installed.

## What works now

* UTF-8 lexer with Cyrillic support, reserved Russian built-in names and
  trailing-dot floats (`1.`).
* Recursive-descent parser with semantic error categories, `(A, B)`
  conjunction and source-ordered statements.
* Value-based immutable terms with lists encoded as `./2` plus `[]`.
* Unification with an undo trail; atoms and strings are interchangeable;
  arithmetic expressions are evaluated eagerly on binding.
* Resolution engine over a *persistent environment chain* (ADR-004): O(1) choice
  points, standard cut, transparent `ВЫП/1`, `НЕ/1`, `ИЛИ/2`, `РАВНО/2`,
  `ЛОЖЬ`, `ТРАССА`/`НЕТ_ТРАССЫ`, `ТИХО`, `ВЕРСИЯ`, `ПС`, `ЖДИ`.
* Arithmetic: hand-written `BigInt`, `#expr#`, `БОЛЬШЕ`/`МЕНЬШЕ`, `СЛОЖЕНИЕ`,
  `УМНОЖЕНИЕ/3,4`, `ABS`, `SQRT`, `SIN`, `COS`, `TAN`, `EXP`, `int`, `float`,
  `СЛУЧ`, `ЦЕЛВЕЩ`, `СТРЦЕЛ`, `СТРВЕЩ`, `СТРСПИС`.
* Strings (code-point based): `БУКВА`, `ЦИФРА`, `СЦЕП`, `КОПИЯ`, `ДЛИНА`.
* I/O: `ВЫВОД`, `ВВКОД`, `ВВОДЦЕЛ`, `ВВОДВЕЩ`, `ВВОДСИМВ`, `ВВОДСТР`,
  `ЧТЕНИЕ_ИЗ`, `ЗАПИСЬ_В`, preloaded `$...` input lines.
* Program database: `СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`.
* Graphics over `GraphicsBackend` (null and recording implementations).
* `НАЙТИВСЁ/3` reproduces the required examples.
* `ИМПОРТ` loader: import-once, include paths, cycle detection, root containment.
* CLI11 front-end with conventional options (positional files, `-s/--source`,
  `-I/--include`, `-q`, `-t`, `--help`, `--version`); UTF-8 console setup on
  Windows; diagnostics in the `file:line:column: error: message` form.
* Examples ported to the new syntax (`examples/lessons/lesson_*.pld`,
  `examples/*.pld`) with golden tests; `examples/import_demo.pld` demonstrates
  `ИМПОРТ` and `-I`.
* CMake presets and a GitHub Actions workflow (Linux GCC/Clang, Windows MSVC).
* Windows verification: the library, CLI and test binary cross-compile to valid
  PE32+ executables for `x86_64-windows-gnu` (Zig toolchain); the MSVC build and
  runtime tests are delegated to CI.

## Task board

| Task | Status | Notes |
|------|--------|-------|
| task_00_recon_and_plan | done | |
| task_01_bootstrap_build | done | FetchContent Catch2 + CLI11 into `src/3rdparty` |
| task_02_core_terms | done | lists as `./2` + `[]` |
| task_03_bigint | done | own implementation, ADR-003 |
| task_04_lexer | done | `_Name`, trailing-dot floats |
| task_05_parser_diagnostics | done | semantic error categories; `(A,B)` conjunction |
| task_06_unification_trail | done | eager expression evaluation |
| task_07_engine | done | persistent environment chain (ADR-004) |
| task_08_arithmetic | done | |
| task_09_builtins_control_types | done | |
| task_10_builtins_strings | done | code-point positions |
| task_11_builtins_io | done | file redirect covered by tests |
| task_12_builtins_database | done | name-wide clause enumeration |
| task_13_findall | done | required examples pass |
| task_14_modules_import | done | loader + tests (cycles, root, include path) |
| task_15_graphics_stubs | done | |
| task_16_cli | done | conventional CLI (ADR-012); Ctrl+C stop, exit codes and `--protocol json` added |
| task_17_docs_typst | done | three Russian documents + `doc/README.md` |
| task_18_examples_acceptance | done | lessons ported; golden tests |
| task_19_windows_portability | done | verified locally on VS 2026: build + 108/108 tests (ADR-013); the CI image still has to be confirmed |
| task_20_gui_future | superseded | the Qt C++ plan became PySide6 over a JSON protocol (ADR-014) |
| task_21_gui_pyside | in progress | protocol, `IoContext` input seam, `externalStop`, `src/gui` skeleton |
| task_22_gui_editor | not started | highlighting (separate Cyrillic/Latin colours), line numbers, font zoom, comment/uncomment |
| task_23_gui_keyword_source | not started | `--list-keywords` + `keywords` in `ready`; removes the third copy of the built-in list |
| task_24_gui_completion | not started | completion from the keyword source plus the document's own predicates |
| task_25_gui_files_tabs | not started | tabs, untitled buffers, save prompts, split editor |
| task_26_gui_toolbar | not started | menus, toolbar, icon audit (27 icons present, 18 to draw) |
| task_27_gui_panels | not started | output and input panes, output bottom/right |
| task_28_gui_run_step | not started | run, step (new engine seam + protocol v2), stop, error line |
| task_29_gui_settings | not started | settings dialog and persistence |
| task_30_gui_formatter | not started | soft/hard formatting in prlib + protocol |
| task_31_gui_shortcuts | not started | layout-independent `Ctrl`+ key combinations |
| task_32_import_search_report | not started | `ИМПОРТ` failure names the directories tried |

## Test suite

108 tests, about a second: 100 Catch2 cases plus 8 command-line and
integration tests (seven option tests and the JSON protocol session). Groups:
BigInt, lexer, parser, unification, engine, every built-in group, `НАЙТИВСЁ`,
module loader, the I/O seams, typical tasks (factorial, Fibonacci, GCD,
insertion sort, 4-queens, knapsack), ported lesson/example programs (golden
output) and the CLI (`-s`, `--source`, `--source=`, positional, `-I`, `--help`,
`--version`, `--protocol json`).

## Known gaps / next steps

1. The GitHub Actions Windows job still has to run on an image that provides
   VS 2026; locally the MSVC 2026 build and the whole suite are green.
2. `--dump-ast` and `--dump-clauses` (task_16) are dropped: the parser produces a
   `ParsedProgram`, not a tree worth printing, and no workflow asked for them.
3. Note for anyone building from CMake Tools: Catch2 test discovery decodes the
   test executable's stdout with the console code page, so on a cp437/cp1252
   machine the Cyrillic test names land in `prlib_tests-*_tests.cmake` mangled
   and ctest reports 32 "No test cases matched" failures.  Build, or regenerate
   that file, from a UTF-8 console (`chcp 65001`).  Verified fix for later: the
   decoding happens only for piped output — `execute_process(... OUTPUT_FILE
   ...)` keeps the bytes untouched — so a project-local discovery step that
   writes the `--list-tests --reporter json` listing to a file would make the
   names immune to the console code page.
4. Optional: first-argument clause indexing if a real program needs more speed.
5. Optional: `is/2` and infix comparison operators next to `#expr#`.
6. GUI: task_21 is the skeleton only (protocol, `src/gui` window with an editor,
   a query line and an output pane).  The feature work is task_22–task_31, see
   the board above.

## Open questions for the user

1. String positions are code-point based (not CP1251 bytes) --- confirmed as the
   intended UTF-8 behaviour unless told otherwise.

Resolved on 2026-09-29 (GUI planning):

* formatter (task_30): trailing whitespace is removed, the continuation indent
  is one tab, the soft width is 80 columns;
* shortcuts (task_31): the modifier is `Ctrl`, not `Alt` (which focuses the menu
  bar), and `?`/`:` get both physical keys --- `Ctrl+/` + `Ctrl+7` and `Ctrl+;` +
  `Ctrl+6`;
* split editor (task_25): two independent panes, each with its own tab bar;
* running a buffer (task_28): a modified buffer is loaded as text whose `name`
  is the file's path, so `ИМПОРТ` resolves exactly as it does for the saved
  file;
* the working folder (task_29) is a search directory passed as `-I`, so it is
  searched alongside the importing file's own directory — before and after an
  untitled buffer is saved (task_32 reports what was tried).

## Session log

* Planning session: reference extraction, architecture, ADRs, task breakdown.
* Implementation session: full core (tasks 01--16), working CLI.
* Bug-fix session: persistent environment chain (ADR-004) fixed lost
  continuations and made deep recursion linear.
* Examples/docs/CI session: ported all lessons and examples with golden tests,
  wrote the three Typst documents and `doc/README.md`, added CMake presets,
  GitHub Actions CI and Windows UTF-8 console setup.
* Diagnostics/CLI session: replaced the historical numeric error codes with
  semantic categories and compiler-style diagnostics (ADR-011); the CLI now
  follows plain CLI11 conventions (ADR-012); added CLI integration tests.
  `ai/` stays outside version control (user decision).
* Windows session: retargeted the preset, README and CI to Visual Studio 2026
  and dropped VS 2022; fixed two Cyrillic-path defects (the UTF-8 active code
  page manifest for `prologd`/`prlib_tests`, and `toUtf8Path`/`toUtf8PathGeneric`
  instead of `path::string()`); verified the release build and the whole suite on
  MSVC 19.51 (ADR-013); fixed the `docs` target, which never created
  `build/doc` and therefore always failed with typst `os error 3`.
* GUI session: added `--protocol json` to the CLI, the `IoContext` input seam
  and `EngineOptions::externalStop` to prlib (Ctrl+C included), and the PySide6
  skeleton plus a headless protocol test in `src/gui` (ADR-014, task_21).
* GUI planning session: read the previous Qt front-end
  (`ai/_ref/prolog/src/gui/`, kept locally and git-ignored) for reference —
  highlighting, actions, panes and the formatter — and broke the requested
  feature list down into task_22–task_31.
