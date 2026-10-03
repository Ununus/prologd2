# Status tracker

Last updated: after task_60 (a question is asked only when there is someone to ask — the
margin marker waits for `loaded`) and the two documentation rounds that followed, parts
69--70: the five Typst documents shortened and their title dropped towards the middle of
the page, the window's first program rewritten, the lessons' variables named by role, and
the window taught before the console in lessons 7, 10 and 11.

## Overall

* Phase: the core is feature-complete and verified on Windows; the PySide6 window is a
  full front end (task_21 -- task_60), not a skeleton: files and tabs, the code editor,
  completion, the built-in reference, stepping and tracing, the graphics window, the
  output panel with its answer table and the settings dialog are all in.  The only thing
  left on the board is `task_46`'s named profiles.
* Build: the `windows-msvc` preset (Visual Studio 18 2026, MSVC 19.51) is green locally,
  tests included; the Linux presets, including `-Werror`, build cleanly.
* Tests: 307/307 in about five seconds — 290 Catch2 cases plus 17 command-line and
  integration tests.  The window has its own 22 offscreen scripts plus `protocol_smoke.py`;
  they need PySide6, so CI runs the C++ suite only.
* Interpreter surface: `-s/--source` (repeatable), positional files, stdin, `-i`/`-o`/`-e`,
  `-q`, `-t`, `-I`, `--no-warnings`, `--max-depth`/`--max-steps`/`--max-findall`,
  `--format[=soft|hard|line]` with `--format-width`/`--format-indent`/`--format-unit`,
  `--list-keywords` and `--protocol json` (version 11).
* Documentation: five Russian Typst documents — `help.typ` (the reference),
  `technical.typ` (the design), `prologd-diff.typ` (what differs from the first
  Пролог-Д), `gui.typ` (the window) and `lessons.typ` (the course) — plus
  `doc/builtins.json`, whose records the manual's appendix table and the window's
  reference are both built from.  `cmake --build build --target docs` compiles them when
  `typst` is installed; the PDFs land next to the sources.

## What works now

* UTF-8 lexer with Cyrillic support, 110 reserved Russian built-in names, each with an
  English alias, and trailing-dot floats (`1.`).
* Recursive-descent parser with semantic error categories, `(A, B)` conjunction, `;` as
  the backtrackable disjunction, `\+` as the second spelling of `НЕ`, the short
  comparison signs as sugar over `РАВНО`/`МЕНЬШЕ`/`БОЛЬШЕ`, and source-ordered
  statements.
* Value-based immutable terms with lists encoded as `./2` plus `[]`.
* Unification with an undo trail; atoms and strings are interchangeable; arithmetic
  expressions are evaluated eagerly on binding.
* Resolution engine over a *persistent environment chain* (ADR-004): O(1) choice points,
  standard cut, transparent `ВЫП`, `НЕ`, `ПЕРВОЕ` (variadic), `РАВНО`, `ЛОЖЬ`,
  `ТРАССА`/`НЕТ_ТРАССЫ`, `ТИХО`, `ВЕРСИЯ`, `ПС`, `ЖДИ`, with a recursion-depth and a
  run-length limit that report instead of crashing.
* Arithmetic: hand-written `BigInt`, `#expr#`, `БОЛЬШЕ`/`МЕНЬШЕ`, `СЛОЖЕНИЕ`,
  `УМНОЖЕНИЕ/3,4`, `abs`, `sqrt`, `sin`, `cos`, `tan`, `exp`, `is_whole`, `is_number`,
  `СЛУЧ`, `ЦЕЛВЕЩ`, `СТРЦЕЛ`, `СТРВЕЩ`, `СТРСПИС`.
* Strings (code-point based): `БУКВА`, `ЦИФРА`, `СЦЕП`, `КОПИЯ`, `ДЛИНА` and the rest.
* I/O: `ВЫВОД`, `ВЫВОДПС`, `ВВКОД`, `ВВОДЦЕЛ`, `ВВОДВЕЩ`, `ВВОДСИМВ`, `ВВОДСТР`,
  `ЧТЕНИЕ_ИЗ`, `ЗАПИСЬ_В`, preloaded `$...` input lines; the front-end's answer is a
  piece of the input stream (ADR-023).
* Program database: `СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`.
* Graphics over `GraphicsBackend` (a null one, a recording one, and the window's bitmap).
* `НАЙТИВСЕ/3` reproduces the required examples.
* `ИМПОРТ` loader: import-once, include paths, cycle detection, root containment, and a
  failure that names the directories tried.
* CLI11 front-end with UTF-8 console setup on Windows and diagnostics in the
  `file:line:column: error: message` form, with severities.
* Examples ported to the new syntax and covered by golden tests; the course in
  `examples/lessons` is a program per lesson whose own `%!` lines are its expected output.
* Windows verification: the library, CLI and test binary cross-compile to valid PE32+
  executables for `x86_64-windows-gnu` (Zig toolchain); the MSVC build and the whole suite
  run locally.

## Task board

Tasks 00--20 are the core, 21--60 the window and the language surface around it.  A note
says what the task *is* and which decision it left behind; the reasoning is in the round
entries of the session log below and in `ai/task_*.md`.

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
| task_16_cli | done | conventional CLI (ADR-012); Ctrl+C stop, exit codes, `--protocol json` |
| task_17_docs_typst | done | the Typst documents + `doc/README.md`; PDFs into `doc/` (git-ignored) |
| task_18_examples_acceptance | done | lessons ported; golden tests |
| task_19_windows_portability | done | the VS 2026 build and the whole suite are green locally (ADR-013); the CI image still has to be confirmed |
| task_20_gui_future | superseded | the Qt C++ plan became PySide6 over a JSON protocol (ADR-014) |
| task_21_gui_pyside | done | protocol, `IoContext` input seam, `externalStop`, `src/gui` — the skeleton that tasks 22--60 grew into a full front end |
| task_22_gui_editor | done | tokenizer, palette, highlighter, line numbers, Ctrl+K/U, zoom, the settings store |
| task_23_gui_keyword_source | done | `--list-keywords` + `keywords` in `ready` (protocol 2); one source for the built-in list |
| task_24_gui_completion | done | the popup over the reserved names *and* the document's own, with arities; `Ctrl+Space` |
| task_25_gui_files_tabs | done | tabs, files, save prompts, encodings, the input queue, the split editor |
| task_26_gui_toolbar | done | one action table feeding the menu bar, the toolbar and the context menu; the icon audit |
| task_27_gui_panels | done | the movable output panel, the input console, the status-bar details, the two-state run/stop |
| task_28_gui_run_step | done | `stepHook`/`StepInfo`, protocol 3, the step strip, the trace line, `F10`/`Shift+F10`/`F5` |
| task_29_gui_settings | done | `settings.SETTINGS` drives the dialog, its validation and «Сбросить»; the window applies everything without a restart; RU/EN dropped (ADR-021) |
| task_30_gui_formatter | done | `prlib/formatter.cpp` (whitespace only), three modes, `--format*`, protocol 7/8, the window's `Ctrl+I`; a source that does not parse is never rewritten |
| task_31_gui_shortcuts | done | `shortcuts.py` — a Qt-free table of `Ctrl`+physical key insertions, kept in the settings file and listed by «Справка → Шпаргалка по вставкам» |
| task_32_import_search_report | done | an `ИМПОРТ` failure names the directories tried, with reasons |
| task_33_gui_search_replace | done | `search.py` (Qt-free) + the find bar: `F3`/`Shift+F3` with the wrap reported, «Заменить всё» as one undo step |
| task_34_builtin_branches | done | every built-in branch-tested (186 cases); the sweep found and fixed five defects |
| task_35_lessons_rework | done | the course rewritten for the current dialect; `test_lessons.cpp` compares a lesson's whole output with its own `%!` lines |
| task_36_gui_query_markers | done | a blue triangle in the margin runs the question it stands at, *alone* (a `questions:false` load); the rule is not a parser |
| task_37_gui_builtin_reference | done | `doc/builtins.json` — one record per predicate, from which the manual's appendix table, `test_reference.py` and the window's `F1` dock are all built |
| task_38_engine_limits | done | deep recursion no longer crashes (the release is iterative), `maxDepth` reports instead, `tools/bench_engine.py` makes the numbers reproducible |
| task_39_english_aliases | done | one `kEnglishNames` table is the only place a pair is written; appendix 17 of the manual; 110 reserved names |
| task_40_diagnostics | done | severities, `severity` on the wire (protocol 4), positions that name what to fix, advice for a singleton variable, `--no-warnings` |
| task_41_semicolon_disjunction | done | `;` is the backtrackable disjunction of ISO, `,` binds tighter, a cut in a branch is local to it |
| task_42_engine_hot_path | done | the constant tax measured and halved (about 4 %); clause indexing and term interning measured and deferred (ADR-017) |
| task_43_language_surface | done | `ВЫП/2..N`; the module-collision warning (ADR-019); the dead library gone (ADR-018) |
| task_44_names | done | `ИЛИ/2` → `ПЕРВОЕ/2` and `НАЙТИВСЁ` → `НАЙТИВСЕ`, each retired spelling explained where it is called |
| task_45_gui_graphics_window | done | the graphics predicates are *visible*: a bitmap backend in the engine, protocol 10, a window with «Вписать в окно» and «Сохранить как PNG…» (ADR-022) |
| task_46_interpreter_options_and_limits | in progress | limits in the engine and four dialog rows (ADR-020), protocol 9, plus the interpreter path and the process directory; still open: named profiles (`--timeout-ms` dropped by decision) |
| task_47_lessons_and_formatting | done | the corpus in one style (21 of 25 shipped programs reformatted) with a check that every shipped program *is* the standard shape; a query and a directive are never broken |
| task_48_interface_cleanup | done | five pictures left the tree, `Esc` closes the graphics window → the find bar → the reference → the cheat sheet, and the graphics window opens itself on the first primitive |
| task_49_gui_defects | done | five defects found by using the window, all fixed: the paused flag, the clean unnamed tab, the trace that no longer takes the window, `view/window_geometry`, the output that arrives as it is written |
| task_50_panel_tabs | done | the output panel is one `QTabWidget` (Проблемы/Вывод/Система/Ввод) with counts in the titles and `--- база знаний загружена (N мс) ---` in «Системе» |
| task_51_variadic_first | done | `ПЕРВОЕ` takes any number of goals; one `kVariadicNames` table drives lookup, arities and names |
| task_52_infix_operators | done | the comparison signs are sugar over `РАВНО`/`МЕНЬШЕ`/`БОЛЬШЕ`, a chain is a parse error, a foreign operator is explained where it stands |
| task_53_writeln | done | `ВЫВОДПС`/`writeln` — `ВЫВОД` with a newline; manual §6.3, and 6.3--6.9 shifted by one everywhere they are quoted |
| task_54_input_stream | done | the front-end's answer is a piece of the input stream; a BOM is a marker, not data (ADR-023) |
| task_55_iso_negation_and_is_hint | done | `\+` is the second spelling of `НЕ/1`, with ISO precedence; `is/2` is not added — two hints name the replacement |
| task_56_missing_dot_between_statements | done | a missing dot is reported at the end of *its own* sentence whenever the next token can begin one |
| task_57_tell_failed_redirect | done | a failed `ЗАПИСЬ_В` left the output on a closed stream; one line returns it to where it was |
| task_58_gui_editor_menu_about | done | five requests: the icons, `Shift+Del`, the occurrences of the selection made visible, the loading line after a marker click, and the two question switches in «Выполнение» |
| task_59_gui_answer_table | done | the answer table for a *single* goal (variant C), **on by default since 2026-10-03**; the rule lives in `answers.py`, Qt-free |
| task_60_gui_ask_after_load | done | a question is asked only after `loaded` (`_pending_query`), and a load that fails drops it with one line in «Системе» |
| task_61_portable_windows_build | in progress | §4 (the window's own paths, `prologd_gui/paths.py`) and §2–§3 (PyInstaller, the first frozen folder, `tools/check_dependencies.py`) are done and checked; left: `tools/build_portable.ps1`, the zip and the clean-machine run (`ai/task_61_portable_windows_build.md`) |

## Test suite

307 tests, about five seconds: 290 Catch2 cases plus 17 command-line and integration
tests (seven option tests, five `--list-keywords` tests, the import-search report, the
JSON protocol session, the formatter round-trip and the engine-limit and diagnostics
cases).  Groups: BigInt, lexer, keywords, parser, unification, engine, every built-in
group, `НАЙТИВСЕ`, the module loader (including the import search report), the I/O seams,
the typical tasks (factorial, Fibonacci, GCD, insertion sort, 4-queens, knapsack), the
ported lesson and example programs (golden output) and the CLI.  Every built-in is covered
branch by branch — see `ai/task_34_builtin_branches.md`, which also lists what the sweep
found.

The front end has its own headless checks, run by hand (they need PySide6, so CI does not
run them yet): 23 scripts in `src/gui/tests/` plus `protocol_smoke.py`.  They cover the
reserved names and the colouring rules (`test_keywords.py`, `test_tokens.py`,
`test_highlighter.py`, `test_appearance.py`), the editor, its popup and its bars
(`test_editor.py`, `test_completion.py`, `test_search.py`, `test_shortcuts.py`), files,
settings and the paths of a packaged build (`test_documents.py`, `test_settings.py`,
`test_settingsdialog.py`, `test_icons.py`, `test_paths.py`), the interpreter on the wire
(`test_session.py`, `test_formatter.py`), and the window itself (`test_window.py`,
`test_queries.py`, `test_answers.py`, `test_output.py`, `test_stepping.py`,
`test_graphics.py`, `test_reference.py`, `test_queryline.py`).

## Known gaps / next steps

1. The GitHub Actions Windows job still has to run on an image that provides VS 2026;
   locally the MSVC 2026 build and the whole suite are green.
2. `--dump-ast` and `--dump-clauses` (task_16) are dropped: the parser produces a
   `ParsedProgram`, not a tree worth printing, and no workflow asked for them.
3. Catch2 test discovery decodes the test executable's stdout with the console code page,
   so a non-ASCII test *name* lands in `prlib_tests-*_tests.cmake` mangled and ctest
   reports "No test cases matched" for it.  Test names are ASCII for that reason (written
   down next to `catch_discover_tests` in `src/tests/CMakeLists.txt`); the underlying fix
   (a discovery step writing `--list-tests --reporter json` to a *file*) is still possible.
4. Optional: first-argument clause indexing if a real program needs more speed (ADR-017
   measured about 0.5 µs per failed head attempt).
5. Optional and deliberately out of scope of task_54: `ВВОД(Пер, Терминатор)` instead of
   `ВВОДСИМВ` plus `ВВОДСТР`.
6. Open on the board: `task_46`'s named profiles, and nothing else — task_61 (the
   portable Windows build, written down on 2026-10-03) has its script, its package, its
   zip and ADR-024 done; what it leaves to a person is a click-through of the frozen
   window and a run on a machine without Visual Studio (§7.1, §7.5 of its task file).
   The two «недочёта»   (task_47, task_48), the defects found by using the window (task_49), the four tasks of
   2026-10-02 (task_51 -- task_54) and the row of window requests (task_58 -- task_60) are
   all done.  The settings file is `%LOCALAPPDATA%\PrologD\gui\gui.ini` (or `--settings
   FILE`), the graphics window (task_45) is done, and task_29's own list is closed, RU/EN
   included (ADR-021).

## Open questions for the user

1. String positions are code-point based (not CP1251 bytes) — confirmed as the intended
   UTF-8 behaviour unless told otherwise.

Decided on 2026-09-29 while planning the GUI:

* formatter (task_30): trailing whitespace removed, the continuation indent one tab, the
  soft width 80 columns;
* shortcuts (task_31): the modifier is `Ctrl`, not `Alt` (which focuses the menu bar), and
  `?`/`:` get both physical keys — `Ctrl+/` + `Ctrl+7` and `Ctrl+;` + `Ctrl+6`;
* split editor (task_25): two independent panes, each with its own tab bar;
* running a buffer (task_28): a modified buffer is loaded as text whose `name` is the
  file's path, so `ИМПОРТ` resolves exactly as it does for the saved file;
* the working folder (task_29) is a search directory passed as `-I`, alongside the
  importing file's own directory — before and after an untitled buffer is saved;

Added on 2026-10-02 while implementing task_31:

* `Ctrl+Shift+\` stays «Объединить редакторы», so `|` gets **no** chord at all (the
  window command wins over the row);
* the extra combinations are the simple symbols (`/`, `-`, `_`, `!`, `''`, `""`) — no
  clause skeletons: `ФАКТ.` and `Правило(…) :- …` were dropped as writing the program for
  the user;
* the table is written into the settings file on the first run, which is what makes it
  readable and remappable *there* rather than in the code.

Added on 2026-10-03 while planning task_59:

* the answer table (task_59) is **variant C**: a table for a **single** goal only (a
  margin marker or the goal line), text output unchanged.  Variant B — a `bindings` field
  in the `result` event, the only way to tabulate a whole run — is recorded in
  `doc/gui.typ` §10 rather than built now;
* the user's report «есть проблема в запуске файлов, у которых много вопросов и которые
  что-то выводят» is **not a defect**: it is exactly why the whole run cannot be
  tabulated — the answers of several questions arrive as one stream of text with no
  separator.  A single goal is tabulated exactly instead.
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
  `build/doc` and therefore always failed with typst `os error 3`.  The PDFs now
  go to `doc/` next to their sources and are ignored by git.
* GUI session: added `--protocol json` to the CLI, the `IoContext` input seam
  and `EngineOptions::externalStop` to prlib (Ctrl+C included), and the PySide6
  skeleton plus a headless protocol test in `src/gui` (ADR-014, task_21).
* GUI planning session: read the previous Qt front-end
  (`ai/_ref/prolog/src/gui/`, kept locally and git-ignored) for reference —
  highlighting, actions, panes and the formatter — and broke the requested
  feature list down into task_22–task_31.
* GUI implementation session, part 1: task_23 (one source of truth for the
  reserved names: `--list-keywords`, protocol 2 with `keywords` in `ready`, the
  Qt-free `prologd_gui/keywords.py`) and task_32 (the loader reports the
  directories it searched).  The keyword tests immediately found that `ВЫП/1` is
  answered by the *engine* (`Solver::unifyGoal`) and never reaches the dispatch
  table, so the classification has an explicit list for such names.  `PySide6
  6.11.2` was installed into `.venv` (the abi3 wheel works on Python 3.14).
* GUI implementation session, part 2: running the skeleton by hand found two
  defects — a second **Запустить** printed every solution twice (state lives in
  the interpreter process, so a run must start a fresh one) and **Остановить**
  did not actually stop anything (`terminate()` does not end a console child on
  Windows and `kill()` was not waited for, so the next `start()` failed with
  "Process is already running").  Both fixed in `session.py`/`window.py` and
  covered by the new `src/gui/tests/test_session.py`.
* GUI implementation session, part 3: **Открыть** stopped running the program.
  It used to push the file into the live interpreter, so a run followed by an
  open — or two opens with a run between them — left two copies of the clauses;
  the factorial example then answered 64 times instead of once, which the user
  read as an endless loop.  Opening now only fills the editor, and a run loads a
  saved, unmodified buffer *by path* (so `ИМПОРТ` and the diagnostics use the
  file's own directory) or the editor text under the file's name.  The window
  exposes `open_path`/`run_program`/`stop_program`/`clear_output` and a `session`
  property, which is what `src/gui/tests/test_window.py` drives offscreen.
* GUI implementation session, part 4: syntax highlighting stopped being a colour
  scheme on paper.  `tokens.py` mirrors the lexer's rules (whitespace is not a
  token; nothing spans lines), `theme.py` keeps the palette as data and
  `highlighter.py` maps token to format in one pass per line instead of the
  reference's fifty regular expressions.  Running it by hand showed the syntax
  colours drowning in the desktop's dark theme, so the window now forces a light
  Fusion palette (`--theme light|system`), built by hand because
  `QStyle.standardPalette()` follows the platform since Qt 6.5.  A test measures
  the WCAG contrast of every colour; purple and green were darkened after the
  first measurement (worst ratio now 6.1).
* GUI implementation session, part 5: the editor proper.  `editor.py` adds a
  line-number margin, Ctrl+wheel zoom bounded 6…72 pt, Tab/Shift+Tab block
  indent, `Enter` continuation indent and the error-line marker task_28 will
  drive; a minimal `settings.py` (ini under `%LOCALAPPDATA%\PrologD\gui`, with
  `--settings FILE`) stores font, line numbers, indent and theme, and the tests
  are given a temporary file so they never touch the user's own.  Writing the
  test for comment/uncomment found a real defect: the command collapsed the
  selection, so `Ctrl+U` right after `Ctrl+K` acted on one line — the transformed
  lines now stay selected, which the test asserts.
* GUI implementation session, part 6: completion (task_24).  The popup offers
  the reserved names with their arities *and* the names the document itself uses,
  which is where the typing is actually saved — Prolog calls the name written a
  few lines above.  Collection is a line scan over the tokenizer's output, not a
  parse: the file may be unparsable mid-edit.  Three defects the tests found: a
  call with a list argument was measured as `член/4` (commas inside `[]` were
  counted as separators), Qt does not highlight a row in a list that arrives
  pre-filtered — so `Enter` on the fresh popup did nothing and inserted a newline
  — and typing in a comment was one rule away from offering names, which the
  tokenizer now decides instead.
* GUI hand-testing session, part 7: the user's own prime program printed `НЕТ`
  twice for `?простое(4).`.  The interpreter was right — the **window** appended a
  second `НЕТ` on the `result` event, which carries no text at all; the answer's
  text arrives as `output`.  Fixed, and the contract is now written down in
  `src/gui/README.md`, with the program itself as an offline regression test.
  Two smaller things from the same pass: the output pane and the query line were
  drawn in a hard-coded font, so the size the user set did not reach them — the
  font and the zoom now live in `ZoomablePlainTextEdit`, shared by the editor and
  the output and stored once.  And a piped run of a test that prints a Cyrillic
  message dies with `UnicodeEncodeError` (piped stdout uses the ANSI code page,
  1252 here, while the console is 65001) — the test messages are ASCII now, and
  the rule is in `ai/conventions.md`.
* GUI implementation session, part 8: task_25, first half — tabs, files and the
  prompts that keep work from disappearing.  `documents.py` (Qt-free) owns what a
  buffer knows about its file: name, path, line ending, encoding and the modified
  flag; `buffers.py` owns the `QTextDocument` and the editor per tab, which is
  also where the split editor's second *view* will go.  Two Qt facts cost real
  time here: `QPlainTextEdit.setDocument` refuses a document without
  `QPlainTextDocumentLayout` — Qt prints one warning and the pane stays *empty*
  while the document holds the text, so nothing looks like an error — and both
  modal questions (save on close, which encoding to use) had to become
  replaceable methods (`_ask_save`, `_ask_encoding`), because a headless test that
  forgets to replace one does not fail, it *hangs*.  The window and the tab bar
  share one order: `tabMoved` re-orders the buffer list, and a single empty buffer
  is a placeholder that the first opened file replaces.
* GUI hand-testing round, part 9: four things the user found and asked for.
  (1) The editor drew its text in the application font size on start and after
  opening a file, until the first zoom: a `QTextDocument` carries its *own*
  default font, and the plain text layout measures blocks with it, so the
  document has to be told the pane's font when it is handed over — the widget's
  font is not enough.  (2) Closing all tabs now walks through them: the tab being
  asked about is made current, disappears as soon as the question is answered, and
  the next one follows — asking about everything before closing anything kept the
  files but told nobody which file each question was about.  (3) A file dropped on
  the editor is now opened instead of pasted: a `QPlainTextEdit` accepts a file
  drop and inserts its text, so the window never saw the event; the pane reports
  the drop itself.  (The event must be sent to the pane's **viewport** — a scroll
  area delivers drag and drop there, which is why the first version of the test
  saw nothing.)  (4) `doc/gui.typ`: a fourth Typst paper describing the interface
  — keys, tabs and prompts, encodings, completion, what is *not* there yet.  Its
  tables had to be written as `#table(...)`: Typst has no pipe tables, and the
  markdown-like version rendered as literal text.
* GUI hand-testing round, part 10: the input mechanism was redesigned to the
  user's shape.  Under the output pane there is now an **input field**: its lines
  are the answers, one per request, split on newlines with blank lines dropped, and
  each answer is echoed into the output with `>` so it is visible what the program
  received.  The modal dialog is the *fallback* once the prepared lines run out
  (single line, `Enter` answers, like the query line), and **«Отмена» now stops the
  run** instead of answering an empty string: the flag makes the rest of that run
  ask nothing, and the next run starts clean.  The tests drive this through the
  same kind of replaceable seam as the save prompt (`_ask_input`), and the status
  line reports how many prepared lines are left.  A test detail worth keeping: the
  window's `status_text()` is what the tests wait on — waiting for the *output* was
  ambiguous, because the echo of an answer and the value the program prints are the
  same characters.
* GUI implementation session, part 11: **task_25 finished** — the split editor.
  A `Buffer` now owns one `QTextDocument` and *any number of views* of it; a `Pane`
  (`panes.py`) owns the views it shows.  `Ctrl+\` adds a second pane; both panes
  show the same set of documents in the same order but each keeps its own current
  tab, so the left can show one program while the right shows another, and every
  command follows the pane that was used last (clicking a view makes it active,
  and the status bar says which pane it is).  An edit in one pane appears in the
  other because it *is* the same text: `setDocument` shares the document, and a new
  view is told the pane's font as well (the Qt trap from part 9).  `Ctrl+Shift+\`
  merges, keeping every document open.  The panes and their widths are stored
  (`view/split`, `view/split_sizes`, `view/restore_split`) and come back on the
  next start — the documents themselves wait for «восстанавливать вкладки», which
  task_29 still owes.  Deliberate simplification: the panes share one document
  *set* rather than keeping a list each; the use case (two programs side by side)
  works the same and there is far less state to keep consistent.  `ВЫВОД` prints
  without a newline and `ПС` breaks the line — the window's own notes now start on a
  fresh line when the program left the cursor mid-line.
* GUI implementation session, part 12: **task_26** — one action table for the
  whole window, plus the menu bar, the toolbar and the icon audit.  `actions.py`
  describes 48 commands (title, icon, keys, checkable, implemented, and what a
  disabled entry waits for), and `MENUS`/`TOOLBAR`/`CONTEXT` are three views of
  it; `window.py` makes one `QAction` per entry and builds all three surfaces from
  that, so a shortcut or an enabled/disabled state cannot exist twice.  Twelve
  entries are visible but disabled and say why (formatter task_30, settings
  task_29, search/replace — *no task file exists*, output panel, split orientation
  and graphics window task_27, tracing and step task_28).  The toolbar keeps the
  reference grouping and an explicit 24 px icon size; the font size became an
  editable combo with a validator, because a size chosen by `Ctrl`+wheel (17 pt,
  23 pt) need not be in its list; the «Последние» submenu refills on open and
  prunes files that are gone.  The audit is in `src/gui/README.md`: 41 referenced
  icon names, 25 files present, 16 still to draw, and three files nothing refers
  to (`prologd2.png` is meant to be the window icon — `setWindowIcon` is still not
  called).  `test_icons.py` fails on a misspelled name and on a file that is still
  listed as missing.  Two things came out of the same pass: `closeEvent` now stops
  the interpreter (a close used to leave a live `prologd` behind, so the headless
  suite collected one process per test), and a *test* bug that looked exactly like
  a Qt stall: the status says `решение найдено` for an answer and `решения нет`
  for a failing one, so a helper waiting for the whole word `решение` never
  matched a failed query — the finished run looked like a hang for the whole
  timeout, and the file assertions after it were right all along.  The lesson
  (match a word *stem*; check the comparison before suspecting the event loop) is
  in the repo memory.  `doc/gui.typ` gained section 9 (menus, toolbar, icons) and
  a rewritten "not done yet" list; the Typst trap of the day: bold is one star —
  `**bold**` is not Markdown, it warns and bolds nothing.
* GUI hand-testing round, part 13: four requests from the user and one defect they
  found.  **«Разделить» and «Объединить» were broken**: the pane-dependent enabled
  state was computed once at start-up, so after `Ctrl+\` the «Объединить
  редакторы» entry stayed greyed out — and a disabled `QAction` fires no shortcut,
  so `Ctrl+Shift+\` did nothing and a split could not be undone without a restart
  (`_sync_pane_actions`, now called from both commands, with a test that drives
  them the way a key does).  Zoom gained the *keypad* keys `Ctrl+Num+` and
  `Ctrl+Num-` (Qt spells them `Num++`/`Num+-`, and they are different combinations
  from `Ctrl++`/`Ctrl+-`, which stay free for the task_31 skeleton insertions);
  «Очистить вывод» moved to the far right of the toolbar, since it acts on the
  output rather than on the program; and the user's two new icons
  (`file-save-all.png`, `execution-step-into.png`) left `assets.MISSING` — 41
  referenced names, 27 drawn, 14 to go.  Search and replace finally has a task
  file of its own (`ai/task_33_gui_search_replace.md`), which the five disabled
  «Поиск» entries name in their tooltips.  Two harness lessons from the same
  round: an offscreen screenshot of a split showed the second pane *without text*
  while both views really held it (the real Windows platform paints it — check on
  the real platform before believing an offscreen grab), and a synthetic `QTest`
  key is unreliable in a long headless run once several windows exist, so the
  regression test drives the commands through `trigger()` — the same path, and
  refused in exactly the cases where a dead shortcut would be.
* GUI implementation session, part 14: **task_27, first half — the window
  layout**.  The output and the input queue are now one *panel* inside a single
  `QSplitter` whose orientation is the only thing that changes: side by side with
  the editor when the panel is on the right, stacked under it at the bottom, the
  editor first in both cases.  `Ctrl+F4` turns it and `F4` shows or hides it (a
  checkable action, and `isHidden` again rather than `isVisible`, so a window that
  was never shown is not read as "the user hid the panel").  The side and the sizes
  of both splitters are remembered in four new settings keys
  (`view/output_position`, `view/output_visible`, `view/panel_sizes`,
  `view/output_sizes`) and restored on the next start; `childrenCollapsible` is off
  and each half has a minimum size, because a panel squeezed to zero pixels looks
  like a lost window rather than a hidden one.  Two entries left the disabled list
  (`output`, `split_orientation`), and «Графическое окно» now says there is no task
  for it instead of naming task_27, which never covered a drawing window.  The
  test drives the panel through `trigger()` (see part 13) and checks the turn, the
  travel of the input queue, hiding, the minimum sizes and a restart on the same
  settings file.  Still open in task_27: `panels.py` (colour by kind, truncation
  with the «вывод усечён» marker, auto-scroll that stops when the user scrolls up,
  save to a file), the input console as an alternative to the modal dialogs, the
  status-bar details and `src/gui/tests/test_output.py`.
* GUI hand-testing round, part 15: five requests from the user, and three real
  defects behind them.  (1) A tab now shows its state as a picture — `file` for a
  buffer that was never saved, `file-saved` once it has a file, `file-modified`
  while there are unsaved changes — and the title bar carries the *whole* path
  (the tab keeps the short name, or the tab bar becomes unreadable).  Chasing the
  first of those found that `mark_saved` said nothing when the modified flag was
  already clear, so a tab could keep the wrong picture: the picture is fetched when
  `changed` arrives, and `setModified(False)` on an unmodified document emits
  nothing — the signal is now sent unconditionally.  (2) The «Последние» submenu
  gives programs the file picture, «О программе» shows `prologd2.png` (a box of our
  own instead of `QMessageBox.about`, with the text in a Qt-free `about_text()` so
  a test can read it), and the window itself now carries that icon — the gap the
  README had recorded since task_26.  (3) Undo and redo follow the document of the
  tab that is showing: every document reports `undoAvailable`/`redoAvailable` and
  the slot reads the current one, because the buffers do not share an undo stack.
  Chasing that found two more: a tab click used to leave the title *and* the undo
  state stale (only an edit refreshed them — now `currentChanged` is connected),
  and the handler that resulted raised `IndexError` while a paned editor was being
  merged, because `_active_pane` was reset *after* the pane was dismantled; it is
  reset first, and the handler ignores the signal while the window is between
  states.  `Buffer.icon_name()` keeps the tab policy Qt-free, `actions.ICON_NAMES`
  now carries the four names that belong to no action so the icon audit checks
  them too (46 referenced, 31 drawn, 15 to go), and `test_window.py` grew three
  tests for the pictures, the title and the undo state.
* GUI hand-testing round, part 16: the rest of task_27 that does not need the input
  console, plus four smaller requests.  `panels.py` is new: `LineBuffer` splits
  chunks into lines and *holds* what has no newline yet — the classic defect of a
  pane fed by arbitrary chunks — and `OutputPane` colours by kind (program output
  plain, our echo in the query blue, our notes grey, diagnostics crimson; the kind
  is told by the window, never guessed from the text), keeps a bounded history
  (50 000 lines, dropped in one edit, with `*** вывод усечён ***` pinned first),
  and follows the end until the user scrolls up.  It is read-only, never wrapped,
  and writes through a document cursor, so the user's caret and selection are not
  taken away while a program prints.  The status bar grew a right-hand side:
  interpreter state, caret line and column (the pane forwards
  `cursorPositionChanged`), the file's line ending and encoding, and the exit code
  of the last run.  «Запустить» and «Остановить» now follow the session — a live
  interpreter is the only thing that can be stopped — which also means the run
  action is disabled right after `ready`; the test that triggered it stops the
  session first.  «Переносить длинные строки» is a new checkable entry in «Вид»:
  the *editor's* switch (stored as `editor/wrap`), because a log line cut in the
  middle cannot be read as data, and «Остановить» keeps only `Shift+F5` — the
  second combination was noise on a keyboard where it belongs to «Разделить».
  Scratch scripts now match a `.gitignore` rule (`src/gui/tests/_debug*.py`), one
  having been committed by accident earlier.  Two self-inflicted defects of the
  round: an edit swallowed the newline after a comment in `editor.py` and merged
  `dragEnterEvent` into the paragraph above it (caught by the next test run), and
  `test_output.py` first read the echo's colour from `layout().formats()`, which
  holds *block* formats — the colour is in the character format.
* GUI hand-testing round, part 17: the run state was split in two, as the user asked.
  It was one flag (`is_running`), which made a freshly opened window claim the
  interpreter was up, and made `Запустить` dead right after an answer.  Now the
  process being *up* and a computation being *in flight* are separate: `Запустить`
  needs the second (nothing is started while something is computing, and the answer
  frees it so the next press restarts the whole file) and `Остановить` the first
  (an idle interpreter still holds a knowledge base).  The window also stopped
  starting an interpreter just by being opened — the session comes up with the first
  run or with a goal typed into the query line, and until then `Остановить` is dead,
  which is what the user expected of a window that is merely open.  The stop now
  names what it interrupted: `--- остановлено ---` for a computation in flight,
  `--- база знаний выгружена ---` for an idle interpreter, and the load note became
  `--- загрузка базы знаний ---`.  The status bar shows `выполняется`,
  `база знаний загружена` or `интерпретатор остановлен`.  The test helper grew
  `ready=False` for the window that has only been opened (the default still starts a
  session, because most checks are about what happens after `ready`), and
  `test_the_run_state_drives_the_buttons` walks the whole path: nothing running →
  run → answer → stop (idle) → run → stop (in flight).
* GUI hand-testing round, part 18: the input console, and the real defect it
  uncovered.  The user asked whether it was a protocol limitation that
  `ВЫВОД("Введите символ")` appeared only *after* the answer to `ВВОДСИМВ`; driving
  the interpreter by hand over the bare protocol showed the order on the wire is
  right (`output`, then `input_request`, with a deliberate `flush()` between them in
  `protocol.cpp`), so the defect was in the window: the pane *held* an unfinished
  line until its newline arrived, and a prompt is exactly such a line.  The pane now
  writes an unfinished line at once and continues it in place (`Piece(text, kind,
  complete)` from `LineBuffer`), a change of kind still closes the line first, and
  the end of a run closes what is left; `test_output.py` carries the case the user
  reported.  The console is as the user asked: hidden while nothing is asked (an
  idle strip was taking room from the output and stretching its own label), shown
  with the question, the kind in the placeholder (`Слово — Enter`,
  `Строка — Ctrl+Enter`, `Символ — Enter`), a yellow frame (`#e0b400`) while it
  waits, `Ctrl+Enter` sending from the text area and `Enter` from the one-line
  field, and the answer echoed with `>`.  The prepared-lines field stays with a
  switch of its own («Вид → Поле очереди ввода»), and a *hidden* field is not read at
  all — hiding it is how the console takes over.  «Файл → Сохранить вывод…» writes
  the pane as UTF-8 text: the text, not the colours, because a log should be
  readable in any editor.  Two test mistakes of the round were mine: a new check
  expected one dialog request where the program asks twice, and the run that would
  have caught it was chained to the commit — so the commit did not happen and the
  tree waited, which is the right way round.
* GUI hand-testing round, part 19: **task_33, the find bar**, plus the icons the user
  drew.  `prologd_gui/search.py` is the engine and is Qt-free on purpose: what goes
  wrong in a search is arithmetic — an offset into a folded copy instead of into the
  text, a match counted twice, a wrap that never comes, a «Заменить всё» that finds
  its own output — and `test_search.py` hammers exactly that.  Case folding happens
  on a *slice* of the original, never on a copy of the whole text, so a fold that
  changes a string's length cannot shift the offsets after it.  `prologd_gui/findbar.py`
  is the strip (question, next/previous, count, the three switches, «Замена» behind a
  disclosure with «Заменить» and «Заменить всё»); it knows nothing about editors, so
  there is one place where a question becomes offsets, and that place is `search.py`.
  The bar is a widget of the window and not a dialog, for two reasons worth
  remembering: a modal box covers the text being searched, and a modal box cannot be
  driven from a headless test.  Three decisions of the round: a match the caret is
  *inside* is the one found (`search.match_at`), so `Ctrl+F` in the middle of `факт`
  stops on that `факт` while `F3` still moves on; the span of «Только в выделении» is
  taken *once*, when the switch goes on, because the search itself moves the selection
  it would otherwise be read from, and switched on with nothing selected it refuses
  instead of quietly meaning «everywhere»; and re-running the search never moves the
  caret — the first version moved it to the match it picked, so typing in the program
  threw the cursor into the next `факт`.  Two Qt traps: `QAction.triggered` hands the
  slot a `checked` boolean, so `"find": self.show_find` arrived as
  `show_find(False)` and opened an *empty* field (the entry is a lambda now, and the
  README says why), and the occurrence highlight of the selected word had to be
  suppressed while the search shows its own matches, or the pale occurrence colour was
  painted over the warm one and the *current* match stopped standing out.  The five
  «Поиск» entries left the disabled list, `search-find` got a name in the table
  (`actions.FIND_ICON`) instead of being renamed, and `edit-del` became the picture of
  «Удалить».  With the user's new pictures the audit is 48 names, 42 drawn, 6 to go
  (`assets.MISSING` is now only the «Вид» switches), which made two window checks
  stale — one asserted that `find` is disabled, another that `file-reload` has no
  picture — and one that could never pass: `test_the_output_can_be_saved` compared the
  file against `output_text()` *after* the pane had been told where it went, so the
  note about the save was already in the pane.  All thirteen GUI scripts are green.
* GUI hand-testing round, part 20: the find bar's *shape*, from the user's first look
  at it.  The three switches moved to a row of their own — beside the field they were
  the first thing squeezed out of a narrow window — and the strip's vertical size
  policy is now `Maximum`, so it is exactly as tall as its three rows.  With the
  default policy the layout shared the window's spare height with the editor and the
  search took half the program pane; a hidden row takes no room at all, so closing
  «Замена» gives the height back.  The rows are real widgets (`field_row`,
  `switch_row`, `replace_row`) rather than loose layouts, because then “which row did
  this widget end up on?” is a question a test can ask: `test_search.py` checks the
  parent of each switch and that the rows stack, and the same test fails if the size
  policy ever goes back to the default.

* GUI hand-testing round, part 21: **task_28 — stepping, the trace and the line an
  error is on**, the first round in a while that is mostly C++.  The engine got one
  seam, `EngineOptions::stepHook`, called at the four points the textual trace
  already had, with `StepInfo{action, goal, depth, location}` — and **no `Pause`**:
  a hook that wants the user to look at the point it was given simply *waits*,
  reading the next request, and the protocol reuses the re-entrant read loop
  `input_request` already had.  The solver has no continuation to suspend, and the
  loop a front-end already owns is exactly the pause (ADR-015).  The environment
  frames now carry their depth and the location of the clause they are solving,
  which is what a step point reports — and what let `Engine::raise` fill in a
  position, so a **runtime** error names its line as a parse error always did: the
  task asked to check for that and the check found the gap.  `IoContext` grew a
  trace sink, so `ТРАССА` goes to the front-end as `trace` events (and to the
  output stream as before when nothing asks), which is how the pane colours it
  apart from the program's own output.  Protocol 3 carries all of it: `step` events
  and the `step` request, `trace` events, `file`/`line`/`column` on `error`, and
  `step`/`trace` flags on `load` and `query`.  In the window: the step strip (action,
  goal, depth, position, and the call stack *the window rebuilds* from `call`/`exit`
  pairs), the trace line marked in a neutral colour, `F10`, `Shift+F10`, `F5` as
  «продолжить» — and the three commands enabled, because a paused step is a *usable*
  state and a disabled `QAction` fires no shortcut, the trap that already cost this
  project a round.  Diagnostics now come with their position: the window marks the
  line, puts the caret on it, and opens an `ИМПОРТ`ed file in a tab of its own
  rather than marking a line in whatever tab happens to be showing.  Coverage: six
  Catch2 cases, seven Qt-free checks in `test_stepping.py` against the built
  interpreter, five more in `test_window.py`, and the protocol session in cmake.
  Three findings worth their lines: the *same* test can pass in a UTF-8 console and
  fail under the VS Code task runner because `execute_process` decodes the child's
  stdout with the console code page, so the cmake expectations are ASCII-only now
  (the Cyrillic side lives in Catch2, which compares inside one process); a parser
  can report a line past the end of the file (`непарные скобки`), so a marked line
  is clamped to a line that exists — and the caret follows the clamped one; and
  «Остановить» still terminates the child instead of interrupting politely, which
  is recorded in the task file as a deliberate deviation rather than quietly
  half-implemented.
* Coverage round, part 22: **task_34 — every branch of every built-in**, the round
  the user asked for after the stepping work ("проверим что все ветки предикатов
  работают корректно").  The method was the point: drive the built `prologd.exe`
  over each predicate's arguments — bound, free, wrong type, out of range, and the
  empty list / empty string / end-of-input — write the expectations from what came
  back, and only then decide whether a surprising answer is a defect or the port's
  documented behaviour.  It found **six real defects**, five of them in code that
  had tests already:

  1. `SQRT(-4, X)` *succeeded* with `X=0` and `SQRT(-4.0, X)` with `X=nan`
     (`BigInt::fromDouble(nan)` is 0), and `EXP(X, -1.0)` (that is `ln(-1)`) bound
     `X=nan` — `SIN(X, 2.0)` and `COS(X, 2.0)` too.  A value the function does not
     have is a *failure* now, and the float mode checks `std::isfinite` before
     unifying.  This is a behaviour change, recorded in `doc/help.typ`.
  2. `РАВНО(16777217, 16777216.0)` was true and `РАВНО(16777217, 16777217.0)`
     false: the integer/real comparison narrowed the integer to `float` and then
     compared it with the double, so the two sides were compared at different
     precisions.  It now compares the numbers exactly (the real must be whole and
     `BigInt::fromDouble` must equal the integer), which also stops `10^20 + 1`
     from matching `10^20.0`.
  3. `?РАВНО(X, f(X)).` **ended the process** with a stack overflow — there is no
     occurs check, so one line at the prompt makes a cyclic term, and the printer
     followed it until the C++ stack ran out (a cyclic *list* did not end at all,
     because its cells are followed in a loop).  The printer now remembers the
     compound nodes it is inside and writes `...` at the repeat, and the copy
     behind `ДОБ`/`НАЙТИВСЕ` refuses a cyclic term with a diagnostic instead of
     recursing.  The default print depth also came down from 100000 to 2000, which
     is a stack-safety number, not a formatting choice.
  4. The second argument of `ВВОДЦЕЛ`/`ВВОДВЕЩ`/`ВВОДСИМВ`/`ВВОДСТР` — the prompt —
     was documented and silently dropped.  It is written before the read now, and
     a prompt that is not text is a type error like any other argument.
  5. Every graphics argument went through `*intArg(...)`: a real, an atom, a string
     or a list as a coordinate dereferenced an empty `std::optional`, which is
     undefined behaviour — the calls were *accepted* and drew with whatever was in
     memory.  Each non-free argument is checked now; a real is still truncated, as
     everywhere else.
  6. `ВВКОД(1114112)` and `ВВКОД(55296)` wrote bytes that are not UTF-8 at all
     (the JSON protocol cannot carry them back); a code point has to be a Unicode
     scalar value now.

  Everything else the sweep touched was the port behaving as `task_09`–`task_13`
  documented it, and is now pinned by tests: the truncating integer arguments
  (`СКОЛЬКО(прим, 1.5)`, `ПРЕДЛ(прим, 1.0, …)`, `ДОБ(…, 1.5)`, `ТОЧКА(1.5, …)`),
  `УДАЛЕНИЕ`'s clamp (0 and -1 mean the first clause, past the end means the last),
  numbering by name *across arities*, the snapshot a running enumeration keeps while
  the database is edited, `ПЕР`/`ЦЕЛ`/`ВЕЩ`/`СИМВ`/`СПИСОК` as a truth table over
  every term kind, `НЕ` undoing bindings but not `ДОБ`, `ИЛИ` committing to the
  first solution of its first goal, `ТИХО` being a per-query flag, `НАЙТИВСЕ`
  copying its template, and the token/line interplay of the reading predicates.
  Two new files carry it (`test_builtins_control.cpp`, `test_builtins_types.cpp`, both
  from `task_09`'s plan, which had never been written), and `test_builtins_io.cpp`,
  `test_builtins_database.cpp`, `test_builtins_string.cpp`, `test_builtins_arith.cpp`,
  `test_findall.cpp`, `test_graphics.cpp` and `test_unify.cpp` grew the rest:
  132 cases before the round, 186 after, 2733 assertions.  One harness lesson came
  out of it: test *names* have to be ASCII, because the discovery step reads the
  test binary's `--list-tests` output through the console code page — a Russian
  name reaches `ctest` double encoded and the test reports "No test cases matched"
  while the binary runs it fine (the rule is written next to `catch_discover_tests`
  now).  `doc/help.typ` gained the edges the tests pin — the domains of the float
  functions, the exact number comparison and cyclic terms, the prompt, the code
  point range, the string range rules, the type-test truth table, the database
  clamps and the graphics argument rule.
* Question-answering round, part 23: **«где расхождение» в `КОПИЯ`**, from the
  user's own lesson program.  The old interpreter answered `?сколько(идиотизм,"и",Q)`
  with `Q=3`; the port answers `Q=1`.  The difference is one branch: `КОПИЯ(с,П,Р,с4)`
  with **both position and length free**.  The program takes the prefix *before* the
  occurrence it found and counts there, which only adds up when the found occurrence
  is the **last** one — and the reference searched from the end (its `str0.rfind`)
  until commit `da51bbe` («Fix: КОПИЯ», 23.03.2023, by the original author) rewrote
  that line to `str0.find` while doing something else entirely (allowing a negative
  length and letting its sign choose the direction in the *other* search mode); the
  port was written from the post-fix reference, so it inherited `find`, and the
  lessons were never updated because their queries are commented out.  With
  `Х=1` the lesson's second clause (`РАВНО(Х,1),!`) fires and answers `1` — there is
  no bug in the new code, only a silent behaviour change in the old one.  Decision
  (the user's): **keep the left-to-right search** — it is what the current reference
  does — and bring lesson 3 in line with it instead of the other way round.  So
  `сколько/3` now counts the rest *after* the first occurrence (`1` is the case where
  the occurrence *is* the whole string), `замена/4` and `удаление/3` cut the first
  occurrence out and recurse, and the results are the ones the lesson wanted:
  `Н=3`, `Т=юбвюбвю` (all three `а` replaced), `Ю=бркдбр`, and `скобки` on the
  lesson's own example finally diagnoses the real reason instead of comparing two
  accidentally equal counts.  `doc/help.typ` §7.4 states the direction now (it was
  undocumented), `test_lessons.cpp` pins the rewritten lesson, and
  `ai/porting_notes.md` records the deviation from the original file.  Worth
  remembering: this is the second time a *lesson's* behaviour has been the only
  evidence for a built-in's semantics — the lessons are the acceptance material, and
  a commented-out query is not a test.  (Later the original sources were found on
  this machine, and the reference itself was checked: the 2025 build keeps the
  post-fix `find` branch, so it too answers `Н=3` — the «старый 3 против порта 1»
  framing above was the premise of that session, not an open discrepancy.)
* Lessons session, part 1: the course was stale — lesson 1 still answered with
  the old interpreter's values, lesson 7 never existed, and lessons 5 and 8 could
  not be run whole.  It is being rebuilt from the plan in
  `ai/task_35_lessons_rework.md`, one commit per lesson, and `test_lessons.cpp`
  now runs every listed lesson and compares its output with the `%!` lines the
  lesson carries.  Writing those expectations found real defects in the source
  material: a `нод/3` that never terminates (it hands the same pair back), sorts
  that came out descending, a `?длина(Х, 2)` that never stops, and a failed
  number read that leaves the rest of its line — which behaves differently in the
  CLI and in the test harness, so the lesson keeps that read last.  Lessons 1--7
  are done, `ctest` stays green (183 Catch2 cases, 194 tests); 8--12, the debug
  appendix, the index and `doc/lessons.typ` remain.
* Lessons session, part 2: the rest of the course is written - mathematics of
  lesson 3, recursion and the cut, lists, strings, input and output (the topic the
  old set never had), state search, constraint puzzles, metapredicates, modules and
  graphics - plus `appendix_debug.pld`.  Every lesson is now executed by ctest
  against the output its own comments promise, which is how the mistakes in the
  source material were found: a `нод/3` that never terminates, two sorts that came
  out descending, a `?длина(Х, 2)` trap, a failed number read that leaves the rest
  of its line, and my own slips (a trunk built as `линия/4` when the drawing rule
  wants `линия/5`; the board in `расставить/4` built two ways at once).  The check
  learned about input files and about include paths, and the course got its index
  (`examples/lessons/README.md`) and its place in the documentation
  (`doc/lessons.typ`, built by the `docs` target).  181 Catch2 cases, 2761
  assertions, 192 ctest tests, all green.
* Lessons session, part 3: the diamond `ИМПОРТ` example and the look of the
  documentation.  `examples/diamond/` shows a module reachable by three paths
  (`main` → `left`/`right` → `base`, plus a direct import) and proves it is loaded
  once — the shared predicate still has two clauses, not four.  It is pinned by
  `test_module_loader.cpp`, and lesson 11, the course index, `doc/lessons.typ`,
  `doc/help.typ` §8 and `import_demo.pld` all point at it.  The five Typst
  documents then got one shared look for listings (`doc/style.typ`): a fenced
  block becomes a panel whose left bar says what it is (prolog, cpp, shell
  commands, untagged text), picked up with `#import "style.typ": apply` and
  `#show: apply` — not `#include`, where the rules never reach the document.  Two
  real defects were fixed on the way: `**bold**` in `gui.typ` was a Markdown habit
  that Typst reads as an empty emphasis plus italics, and `lessons.typ` carried a
  «нужно знать» column that only repeated the order of the lessons.  182 Catch2
  cases, 2769 assertions, 193 ctest tests, all green.
* Planning round, part 24: three requests from the user were answered as analysis
  rather than code.  (1) English aliases for the built-ins: the mechanism is cheap
  (one registration call site, plus the lexer's reserved set, and the tests already
  enforce that the two agree) but the naming is not — `ДЛИНА` is a *string* length
  where ISO `length/2` is a list, `int`/`float` are already the conversions where
  ISO spells the *tests* that way, and a built-in shadows a user clause of the same
  name (`engine.cpp:282`).  The user's decision is that backward compatibility is
  not a blocker here, so the idea is parked with a full draft mapping in
  `ai/maybe/english_aliases.md`.  (2) A marker in the editor margin that runs one
  question, and (3) a built-in reference inside the window, are written up as
  `ai/task_36_gui_query_markers.md` and `ai/task_37_gui_builtin_reference.md`.
  Two findings from the analysis are already worth their lines: `%?` needs no
  lesson rewrite at all (a comment is ignored by the interpreter and
  `test_lessons.cpp` compares only the `%!` lines, so the thirteen commented
  queries become clickable as they are), and a single query needs the load to be
  *quiet* — `questions: false`, or the clicked answer arrives after the whole
  lesson's output; the seam is `ModuleLoader::setQueryRunner`.
* Engine review round, part 25: the user asked how the engine differs from other
  Prologs, where the shortcomings are and what can be improved.  The answer was
  read out of the code and measured with the built interpreter, and it found
  **one real defect**: a correct program that recurses ~32 000 deep prints its
  answer and then dies with `0xC00000FD` (`STATUS_STACK_OVERFLOW`) — the deep
  environment chain is released *recursively*, each `EnvNode` holding a
  `shared_ptr` to its parent, so the destructors walk the whole chain when the
  last reference to a deep frame goes (a popped choice point or the solver's own
  environment).  Threshold measured between 16 000 (fine) and 32 000 (dead), the
  same with a cut after the guard and with a 32 000-element list.  Memory was
  measured too: ≈ 2.8 KB per step, 280 MB at depth 100 000 and 1.24 GB at
  400 000, because `Bindings::freshVar` only appends (`clear()` has no caller) —
  while the *time* is fine (~5 µs per step, 400 000 steps in 2.05 s).  Also
  measured: `?СКОЛЬКО(НЕ, А)` answers 2 while `НЕ/1` is answered by a built-in,
  i.e. `Engine::initialize()`'s seven library clauses are unreachable; 100 000
  facts are scanned in 0.31 s against 0.26 s for the first one, so clause
  indexing is a constant, not a crisis; and `ИЛИ(p(X), q(X))` answers `X=1`,
  committing to the first goal instead of being a disjunction.  Six task files
  came out of it: 38 (limits), 39 (English aliases — the parked note became a
  task with the user's decisions: `integer`/`float` as tests, `to_int`/`to_float`
  as conversions, `strlen`, everything lowercase, the course Russian with an
  English appendix), 40 (diagnostics), 41 (`;` as disjunction, awaiting a
  go-ahead), 42 (the hot path) and 43 (`call/N`, module collisions, the dead
  library).  `ai/maybe/english_aliases.md` is gone — it is task_39 now.
* Engine limits session, part 26: **task_38**.  The crash is understood and
  fixed, and the trigger turned out to be narrower than the first report: it needs
  a *surviving* deep reference, not depth alone.  A base clause with a cut removes
  the choice point of the deepest frame, the chain is then walked up one frame at
  a time, and 200 000 levels passed without a murmur (that is why the old Catch2
  test, built on `счёт(0) :- !.`, had been green for months); without the cut the
  deepest choice point — or the solver's own final environment — holds the whole
  chain, and letting it go ran the destructors down every level: 0xC00000FD at
  ~32 000 frames, and a 20 000-cell list alone was enough.  Both chains are
  released iteratively now (`releaseEnvChain` in `engine.cpp`, `CompoundDeleter`
  in `term.cpp`): a node is unlinked from its parent (or has its arguments taken
  out) before it dies, and a worklist keeps the next link alive until its turn.
  The one place where a term's immutability is broken is its own release, and it
  is safe for the reason the term is immutable — the deleter runs only for the
  last owner.  The price is one extra allocation per compound (no `make_shared`),
  about 25 % on loading 100 000 facts, measured and written down.  Results, from
  `tools/bench_engine.py` (new, ASCII output, the instrument every later number
  should use): recursion depth 100 000 — 0.46 s, 193 MB, exit 0 (was
  0xC00000FD); 400 000 — 1.77 s, 753 MB, exit 0; a 60 000-cell list — 0.27 s,
  exit 0; 100 000 facts — 0.35 s against 0.26 s before.  `EngineOptions::maxDepth`
  (default 10 000, `--max-depth 0` for none) ends a runaway recursion with
  «Превышена глубина рекурсии (лимит N)» and exit code 3, next to the existing
  `maxSteps`; the CLI gained `--max-depth` and `--max-steps`.  Tests: the ctest
  case `cli_engine_limits` runs the executable on its own (100 000-deep
  recursion, a 60 000-cell list, the runaway guard — a regression here kills the
  process, so it must not run inside the test binary), the old deep-recursion
  Catch2 case now uses the *crashing* shape with `maxDepth = 0`, and a new one
  pins the diagnostic.  The variable growth was investigated and deliberately not
  "fixed": a clause copy's `VarId`s may be cited by bindings that outlive the
  trail mark, and `ДОБ` stores copies whose variables must survive the rollback
  that recycles everything else, so plain recycling would corrupt asserted
  clauses.  It is a documented ceiling now (`doc/technical.typ` §6.6, `doc/help.typ`
  §15) and visible in the bench; the weight of a term is task_42's business.  183
  Catch2 cases, 2 774 assertions, 195 ctest tests, all green.
- **2026-09-30 — task_39: an English spelling for every built-in.**  One table
  (`kEnglishNames`, 47 rows) is the only place a pair is written: the dispatch
  registration, `--list-keywords`, the lexer's reserved set and the GUI's
  completion all follow from it, so a name cannot be added in one place and
  forgotten in another (`test_aliases.cpp` walks the table and fails on a
  Russian built-in without a row).  The user's decisions: only lower case
  (`ABS`...`EXP` are `abs`...`exp` now, the old spellings are gone), the course
  stays Russian, the pairs live in an appendix.  Doing it turned up that
  `int/1` and `float/1` were never conversions — they *check* whether a value
  can be read as an integer or as any number (`is_whole(4.0)`, `is_number(4)`),
  while ISO's `integer/1`/`float/1` are the type tests — so they are
  `is_whole`/`is_number` now and the planned `to_int`/`to_float` were dropped: an
  actual conversion is `ЦЕЛВЕЩ`/`int_to_float`, and inventing a second one
  without a caller would have been a name without a use.  `ДЛИНА` is `strlen`
  (not `length`, which ISO keeps for lists).  The manual gained appendix 17 with
  the whole table, `prologd-diff.typ` §15 and `conventions.md` gained the rule;
  the reserved-name list grew from 57 to 108 and `test_keywords.py` confirms
  that the CLI, the protocol and the GUI see the same names.  187 Catch2 cases,
  3 131 assertions, 199 ctest tests, all green.
  Same day, after the user's review of the names: a bare English name is now
  reserved for the meaning the standard gives it (`var`, `integer`, `float`),
  `is_` marks a check of ours (`is_text`, `is_list`, `is_letter`, `is_digit`,
  `is_whole`, `is_number` — ISO `number/1` is deliberately absent, since it
  would promise a plain failure where ours raises a type error), and a
  conversion reads `X_to_Y` with the short stems (`int_to_float`, `str_to_int`,
  `read_int`).
- **2026-09-30 — task_40: diagnostics a beginner can use.**  A diagnostic now
  says whether it is an error or a warning: `PrologError` carries a `Severity`,
  `DiagnosticSink` counts warnings apart from errors, the text form prints
  `warning:`, `--no-warnings` drops them, the wire format went to protocol 4
  (`severity` on `error` events) and the GUI shows warnings amber and counts them
  beside the answer.  Positions now name what to fix: an unclosed bracket is
  reported at the bracket itself with its line, a statement without its final dot
  at the end of the clause, an unclosed quote at the quote.  Two checks run after
  parsing: a *reserved* name with an arity that exists nowhere is an error
  (`?УМНОЖЕНИЕ(2, 3).` says «УМНОЖЕНИЕ не имеет арности 2 (есть 3 и 4)» and exits
  2, where it used to answer НЕТ in silence — five tests that pinned that silence
  were rewritten), and, once the whole unit and its imports are loaded, an
  undefined predicate is a warning with a «возможно, имя/арность» suggestion
  within a small edit distance over code points, while a name called with an
  arity it does not have lists the ones it does.  A clause also audits its own
  variables: a name used once in a fact is «... — переменная, а не константа;
  запишите её в одинарных кавычках: 'Лена'», in a rule the message also offers
  `_Имя` as the other reading, and a body singleton is told to use `_`.  The
  corpus paid for the checks at once: the ported `examples/monkd.pld` had been
  calling ЗАКРАСКА with four arguments, and eight unused variables in
  `drawing.pld`, lessons 6 and 7 and monk/monkd were found and fixed.  198 Catch2
  cases (3 182 assertions), 211 ctest tests, all green; the course is silent
  except the debug appendix, which shows the unknown-name warning on purpose.
- **2026-09-30 — task_41: `;` is a disjunction.**  The sentence terminator is now
  the dot alone; `;` between goals is the backtrackable disjunction of ISO, with
  `,` binding tighter (`A, B ; C, D` is `(A, B) ; (C, D)`).  The solver expands a
  `;`/2 goal in place and pushes the right operand as an alternative choice point
  (`ChoicePoint::Kind::Alternative`), and a branch runs in a frame whose cut
  barrier sits above the alternative — a cut inside a branch prunes only what the
  branch created, which is the ISO rule and the reason `ИЛИ/2` stays the
  committed form.  Lesson 4's section about `ИЛИ` became «Дизъюнкция: точка с
  запятой и ИЛИ» and shows the two answers of `;` beside the single answer of
  `ИЛИ`.  A `;` where the dialect used to end a sentence is an error with the
  position of the `;` and a message that says what changed («;» — дизъюнкция;
  предложение не заканчивается точкой), while a `;` in a list or in an
  unparenthesised argument list has a message of its own.  `examples/factorial.pld`
  — the only file in the repository that used the old terminator — was converted;
  `help.typ` §1.1, the new §4.5 (§4.6/§4.7 renumbered), `prologd-diff.typ` §16
  with a row in its summary table, and `ai/porting_notes.md` follow.  A follow-up
  commit made `,`/2 and `;`/2 print infix — `(A ; B)` — which is what a query
  echo, a trace line and a step point carry.  206 Catch2
  cases (3 247 assertions), 219 ctest tests, all green.
* Naming round, part 25: **the two names that lied**.  `ИЛИ/2` was honest in the
  original dialect (there was no disjunction to contrast with), but after task_41
  the disjunction is `;`, and `ИЛИ` is the "take only the first" form — the name
  promised a choice the predicate never makes.  The user picked the full rename
  over a synonym, so `ПЕРВОЕ/2` / `first` replace `ИЛИ` / `or` outright.
  `НАЙТИВСЁ` had drifted from the source as well: `ai/task_13_findall.md` and
  `ai/reference_notes.md` spell it without ё (`?НАЙТИВСЕ(И,студент(И,Ф),А).`), so
  the name went back to `НАЙТИВСЕ`.  The retired spellings are handled by one new
  lexer set (`kRetiredBuiltinNames`: reserved, so an old call is still parsed as a
  goal, but *not* in `reservedBuiltinNames()`, so the keyword table, completion,
  syntax colouring and `--list-keywords` never offer them) plus, for a full
  rename, a `kRetiredNames` table in `checks.cpp` that turns the call into a load
  error before the unknown-name path: «`«ИЛИ» переименовано: теперь это
  «ПЕРВОЕ(Ц1, Ц2)», а дизъюнкция — «A ; B»`».  The retired `НАЙТИВСЁ` needs no
  table at all — it is one code point from `НАЙТИВСЕ`, so the ordinary suggestion
  machinery already answers «возможно, НАЙТИВСЕ/3» (verified by hand and pinned in
  `test_diagnostics.cpp`).  The two `ИЛИ` clauses left `Engine::initialize`'s
  library (they would have answered the retired name through the database);
  `prologd-diff.typ` gained §17 (the ё spelling) and §18 (the rename), and its §6
  lost the "the behaviour is preserved" sentence that task_41 had made false.
  223 ctest tests (2 new), 210 Catch2 cases (3 276 assertions), the GUI headless
  suite and all five Typst documents, all green.
* Performance round, part 26: **task_42, the constant tax — measured, and only
  what the measurement justified**.  Two per-goal string builders are gone:
  `findBuiltin` keyed a `BuiltinKey{std::string, arity}` per call (now a
  `string_view` key; every name in the table is a literal), and `Database` built
  `"name/arity"` per lookup (now a two-level `name -> (arity -> list)` map looked
  up with `std::less<>`, so a `string_view` finds a `std::string` key in place;
  `key_order_` and its prefix scans went with it, which is also what `ПРЕДЛ` and
  `УДАЛЕНИЕ` by name used).  The instrument mattered more than the change: a
  first A/B across two sessions showed "no difference" (1.70–1.72 s vs
  1.64–1.71 s), and only *interleaved* runs of the two binaries in one session —
  six pairs on a new synthetic loop of 14 trivial built-ins plus a recursive call
  per step — showed a real ≈ 4 % (median 1.45 s → 1.40 s), with every pair
  faster.  Clause indexing is deferred *with numbers* (ADR-017): 100 000 facts
  scan in ≈ 20 ms, structured-head facts in ≤ 10 ms, and the queens workload
  (14 clauses, heavy bodies, shallow-matching heads) is a shape an index cannot
  prune.  Term interning stays unattempted and is now bounded: the whole
  per-goal lookup class is 4 % on the most favourable program in the suite.
  `tools/bench_engine.py` grew the `dispatch`, `structured` and `queens`
  workloads and an `--only` filter; `doc/technical.typ` §6.7 carries the
  numbers.  223/223 ctest, 210 cases / 3 276 assertions, the GUI suite and the
  lessons unchanged.
* Language-surface round, part 27: **task_43 — the rest of the standard
  surface**.  `ВЫП/2..N` is `call/N` now: the extra arguments are appended to the
  goal (the goal first), the callee is dereferenced before the append, a free
  variable there is the usual «Цель должна быть предикатом», and the keyword
  table says `ВЫП/+`, so completion and `--list-keywords` follow.  Writing the
  behaviour probes found two open questions of the task and settled both: `!`
  *inside* the argument is a parse error («неверное использование "!"» — the
  argument is a term position), so the manual sentence promising a cut inside
  `ВЫП` was removed instead of made true, and the step hook shows the expanded
  goal one environment deeper (`цель(_1) @1`), never `ВЫП`.  The module-collision
  warning reports a predicate fed by two files with no import path between them —
  one warning, naming the predicate, both files and their clause counts — and
  stays silent for the diamond and for a file extending a module it imports; the
  import graph the loader already keeps tells the cases apart.  The dead library
  went: `Engine::initialize()` loads nothing, `?СКОЛЬКО(НЕ, А)` answers 0, and
  ADR-018 records why the seven clauses could never be selected.  229 ctest tests
  (5 new), 216 Catch2 cases / 3 304 assertions.
* GUI round, part 28: **task_36 — вопросы на полях**.  In the margin left of the
  line numbers every question now carries a blue triangle, and a click answers
  exactly that statement: the program is loaded *quietly* (`"questions": false`
  on `load`, protocol 5) so the pane holds the one answer and not the whole
  lesson, and the statement goes into the query line first, where it stays while
  the answer arrives.  The rule that decides which lines are questions lives in
  `queries.py` and is deliberately not a parser: shape first (`?` or `%` with `?`
  at the start of the line; the sentence ends at the first `.` outside strings,
  `#…#` and matched brackets), then *words* — every bare word must be a
  variable, a reserved name or a name the document itself uses, which is what
  refuses prose like `% ?длина(Х, 2) не завершится.`.  A live line's own words
  count as used (the line is part of the document), so the word check really
  guards commented questions; the sweep asserts that no live `?`-line anywhere
  in `examples/` is left without a marker and pins the counts per file.  A click
  during a run stops it first.  The first hands-on run of the feature produced
  two more fixes, both now tests: a failed query is named `<query>` — the window
  shows it in the pane and no longer marks line 1 of the program and pulls the
  caret there — and `Ctrl+C` copies the selection of the *focused* pane, so text
  can be copied out of the output at last.  The `%?` question-comment is orange
  (`#b45309`, contrast 5.02 — the tightest colour in the palette, still above
  the 4.5 threshold).  No lesson file was edited; 231/231 ctest, the 16 headless
  GUI scripts, all six Typst documents.
* GUI round, part 29: **task_37 — справка по предикату в окне**.  The built-in
  reference now has one source of data: `doc/builtins.json`, 59 records covering
  all 108 reserved names (the Russian name, its English spellings, kind, arities,
  the variadic flag, group, the `help.typ` section, a one-line summary and the
  argument modes).  The appendix of `help.typ` builds its table of English names
  from that file with `json()`, so a pair of names is written down once — the
  previous hand-written table was the only place where the same knowledge lived
  twice.  `src/gui/tests/test_reference.py` is the keeper: every name of
  `--list-keywords` has a record and no record is unknown, arities and kinds are
  the interpreter's (`ready`), an alias is listed once, every `section` is a
  heading of the manual, a variant starts with the predicate's own name, a
  summary is one non-empty line without a trailing period.  The window shows the
  record in two places: a label under the completion popup with the summary of
  the highlighted row, and the dock that `F1` opens with the summary, the English
  name, the section and *all* argument modes of the word under the caret.  `F1`
  was taken by the PDF manual, and the user decided: the in-window answer gets
  `F1`, the manual moves to `Shift+F1`.  Writing the label test found that
  `Up`/`Down` did not walk the popup list at all (they moved the caret, while
  the README's keyboard table promised the list) — now they do, and the label
  follows the row.  A checkout without `doc/builtins.json` still works: the
  popup has no descriptions and `F1` says the reference is unavailable.  New
  rule in `ai/conventions.md`: a built-in is added to `builtins.cpp`, to the
  lexer's reserved set *and* to `doc/builtins.json`.
* GUI round, part 30: **task_28 closed for good — the polite stop**.  The one item
  left open in 2026-09-29 — «Остановить» terminating the child instead of asking
  first — turned out to rest on a stale premise: the solver reads the stop flag at
  every step of its loop, the step pause answers `interrupt` by ending the pause,
  and a read waiting for input answers it by failing.  What the request *cannot*
  reach is a command that is already executing (the session reads between
  commands), so «Остановить» now asks first and takes the process down only after
  `STOP_GRACE_MS` (500 ms) — and the two outcomes of the button finally differ
  cleanly: stopping a *run* leaves the interpreter idle **with its base**, stopping
  an *idle* interpreter unloads it.  Interrupted queries end either as an error
  (solving) or as a failed read (input wait — «НЕТ»), and both conclusions are the
  stop's own: the window answers them with `--- остановлено ---` and marks no line.
  The marker click still stops immediately — the clicked query follows at once,
  and the stopped run's events must not land in the middle of it.  Two smaller
  truths fell out of the same pass: `run_program` sets its flags *after*
  `session.start()`, because the old process's `ended` event (delivered inside the
  stop that a restart performs) cleared them; and a text load is named after its
  tab — a saved file by its path, an unnamed buffer by its title («Без имени 2») —
  so a diagnostic in an unnamed buffer reads «Без имени 2:1:1» instead of
  «<buffer>:1:1», with the protocol's `<buffer>` still meaning «the showing tab»
  for a load that named nothing.  Tests: a new window case (stop at an input wait:
  the base stays, the pending request is dismissed, the next press unloads it), the
  in-flight stop now waits for its note, and the protocol session gained the
  `interrupt`-at-a-pause case.  All boxes of `ai/task_28_gui_run_step.md` are
  ticked.
* GUI round, part 31: **the strip, the pictures and the short path** — three things
  the user found by using the window.  (1) The step strip mixed two fonts:
  `set_font_size` reached only the goal and the stack, so the action, the depth and
  the position — and the buttons between them — stayed in the interface font, which
  reads as a defect the moment the zoom is used; the whole strip is the editor's
  monospace font now, and the test asks every `QLabel` of the strip for one size.
  (2) The two text buttons became the toolbar's own pictures
  (`execution-execute`, `execution-step-into`, `execution-abort`) through one small
  `_tool_button` helper that keeps the words and their keys in the tooltip
  («Продолжить (F5)», «Шаг (F10)», «Стоп»), because three words in a row of a
  program's own text read as a paragraph of prose; the same pass *added* the
  «Шаг» the strip never had (`stepped` → `step_into`), so a paused run can be
  driven on from the strip itself.  (3) A full path in the one-line status bar
  pushed everything else out of it: `documents.short_path` keeps the last two
  components («…\lessons\lesson_04.pld») for the four messages that name a file,
  while the window title keeps the whole path, which is where two files of one
  name are told apart; `test_documents.py` pins the helper.  The same look at the
  zoom found that the task_37 reference dock never followed the font size at all
  (`_on_zoom_changed` did not reach it) — fixed with the rest.  Sixteen
  `test_*.py` scripts (and the protocol smoke) green, 231/231 ctest, the `docs`
  target compiles the six PDFs; `doc/gui.typ` §2 and §6.2 and
  `src/gui/README.md` say all of it.  The first stepped run on an *opened* file
  found one more of the same family: the strip's «где» carried the whole path and
  ran up against its own buttons.  The label now shows the last two components
  (`…\examples\monk.pld:2:1`) with the whole path in its tooltip, and an
  `ElidedLabel` paints the tail with «…» in front when even that does not fit —
  Qt's own middle elision reads badly on a path (`…\e…2:1`), the cut is shown,
  and `text()` stays whole, which is what the tooltip and the tests read.
* GUI round, part 32: **task_30 — the formatter**, and the placement question was
  the whole design: laying out a clause needs to know where a body starts and
  which comma separates two *goals* rather than two arguments — that is the
  grammar, and the grammar lives in prlib, so the formatter went there and the
  window became its client (`prologd --format` is the same code on the command
  line).  `formatSource` returns `{text, changed, diagnostics}`; the mechanism is
  what keeps it safe: the text is lexed and parsed with the interpreter's own
  grammar, and the output is rebuilt from the *token stream*, inserting and
  removing whitespace only — every token is copied byte for byte, so quoting,
  `#expr#` bodies and Cyrillic names cannot be damaged and nothing is re-printed
  from the AST.  A source that does not parse comes back untouched with its
  diagnostics (the CLI exits 2 and writes nothing to stdout; the window reports
  «не удалось разобрать» and marks the line).  The canonical spacing it writes is
  the corpus's: `голова:-тело` glued, `:- цель.` for a directive with one space,
  `?цель.` glued, `, ` and ` ; ` between goals, no space before the dot, no
  trailing whitespace anywhere, at most one blank line between statements and the
  author's blank lines inside one.  The two acceptance shapes are byte-exact
  tests — with the head spelled lowercase, because a capital initial is a
  *variable* in this dialect and the task's `Правило` would not parse (the columns
  match, since the words are the same length).  Idempotence is a property test
  over every `.pld` under `examples/` in both modes; `src/tests/cli_format.cmake`
  runs the executable on a plain example and a lesson, re-formats its own output
  and compares the *programs'* output with the originals'.  Protocol went to 6:
  `format` is answered between queries with `formatted` (or `error` of kind
  `format`) and never touches the exit code — the request failed, the session did
  not.  In the window, `Ctrl+I` sends the buffer (or the selection, when «только
  выделенное» is on) and puts the answer back: one undo step around the
  replacement, the caret and the selection carried over by
  `prologd_gui/formatter.py` (a Qt-free difflib mapping, so a headless test can
  hammer it), and an edit that arrives while the answer is in flight cancels the
  format instead of discarding the edit.  A fragment formats *up to its last
  complete goal*: the cut is the last top-level separator whose prefix parses with
  a final dot, and the fragment's own parse errors are dropped then — they are
  about the part that was deliberately left alone.  The mode control
  («не менять»/«мягкое»/«жёсткое» and «только выделенное») sits on the toolbar
  until task_29's dialog owns the settings keys.  Sixteen new Catch2 cases plus the
  wire test bring the suite to 248/248 (234 Catch2 + 14 integration), the GUI
  scripts to seventeen `test_*.py`, and the manual gained §15 `--format` and
  `gui.typ` its §4.3.
* Formatter round, part 33: **the first look at the feature by the user**, and it
  found the one thing the task file could not state: the soft mode kept the
  author's line breaks, so `hard → soft` was impossible — after the hard mode
  there are no author breaks left, only hard ones, and soft faithfully kept those.
  The mode control also sat on the toolbar, where one command's setting does not
  belong.  Three changes, one of them a semantic one: soft now **builds the lines
  again** — goals are packed up to the width, and only the width, a comment or a
  blank line the author left forces a break — which makes the soft shape
  canonical and makes each format convert into any other (the way back from hard
  is `Ctrl+I` in the soft mode; pinned by a Catch2 round-trip and a wire test).
  «Не менять» left the surface (the command not being pressed *is* «не менять»)
  and «в одну строку» took its place: the goals of a body on one line, whatever
  the width, comments still owning their lines.  The mode selector moved from the
  toolbar into **Правка → Формат**, the submenu right under the command it belongs
  to; `actions.FORMAT_MODE` is a menu placeholder now, like `RECENT`, and the
  window builds the submenu where the menu is built.  The wire caught the change
  of the accepted modes (`line` in, `none` out) — protocol **7** — and a settings
  file written by the previous build reads its old `none` as the soft mode.  251
  ctest tests (237 Catch2 + 14), the 17 GUI scripts, the six PDFs; `gui.typ`
  §4.3/§9.1/§9.2, the README and `help.typ` §15 tell the same story.
* GUI round, part 34: **two defects from a fresh window**, both about waiting for
  something that never comes.  (1) Autocompletion worked only after the first run:
  the popup reads the reserved names from the session's `ready`, and a window that
  has merely been opened has no session — by design (part 17).  The window now
  starts the executable once at startup for `--list-keywords` and parses it with
  `Keywords.from_list_lines` (Qt-free; `test_keywords.py` proves the text form
  builds the same table the `ready` event carries, and the window test that the
  names are there with `ready=False`), so completion, colouring and the shortcut
  sheet work from the first keypress while no interpreter stays alive; the first
  real session replaces the table with the `ready` copy of the same data.
  (2) «Запуск на пустой программе зацикливается» — the interpreter was innocent
  (an empty file exits 0 in milliseconds; checked with the built executable); the
  *window* concluded a run on `result`, which arrives **per question**, so a
  program that asks none (an empty one, a file of facts) kept «выполняется» with a
  disabled «Запустить» forever.  The protocol grew `loaded` (version 8): a `load`
  is over when its program and its own `?`-statements ran.  The run state follows
  it, and the status says «выполнено» only when nothing else concluded the run —
  an answered question keeps its answer, an error keeps its message (the first
  version of that rule overwrote a runtime error's «ошибка: …» with «выполнено»,
  which the existing test caught immediately), and a margin click is concluded by
  its query as before.  Two new window checks (the names before the first run; an
  empty program and a facts-only program both finish), plus the keyword and
  round-trip additions; 251/251 ctest, the 17 GUI scripts, the six PDFs.
* GUI round, part 35: **task_31 — the insert table**, and the interesting part was
  what a *physical* key means.  Matched on `nativeScanCode()`, never on
  `event.text()`: the character is exactly what the two layouts disagree about, so
  the table works in any layout --- including the symbols ЙЦУКЕН has no key for
  (`[` is a letter there, `#` is `№`), because the chord is the key the *English*
  layout carries the symbol on, which is a position both layouts have.  `:` and
  `?` are the exceptions that prove it and therefore carry two chords each (the
  Russian `Shift+6`/`Shift+7`).  A selection is *wrapped* by the bracket-like rows
  and stays selected, everything is one undo step, and only `Ctrl` (plus the
  `Shift` a chord asks for) is accepted: `Alt` alone focuses the menu bar and
  `Ctrl+Alt` is `AltGr`, so both are left to the window.  The table is *data*
  (`shortcuts/table` in the ini, one entry per insert with a *list* of chords) and
  is written there on the first run; «Справка → Шпаргалка по вставкам» lists the
  same object, so a remapped chord cannot be described wrongly.  Two collisions
  decided the shape: `Ctrl+Shift+\` stays «Объединить редакторы» (the user's
  answer), so `|` has no chord, and the zoom stays on the keypad because the main
  row is the table.  Testing this found the one thing that could not be guessed:
  `VkKeyScanExW` says the Russian `/` is `Shift+\` (that very merge chord) and the
  Russian `"` is `Shift+2`, so those two symbols are reachable on their English
  positions only — the check writes both exceptions out with the reason instead of
  hiding them.  `test_shortcuts.py` (Qt-free plus an offscreen editor group and
  the Windows layout check) and two new window checks; 251/251 ctest, the 18 GUI
  scripts, the six PDFs.
* GUI round, part 36: **task_29 — the settings dialog**, run as option B (dialog +
  the "almost ready" keys).  The core is a single description table
  (`settings.SETTINGS`: key, label, section, kind, default, bounds, suffix, hint)
  that drives three things at once — the dialog's row, validation in
  `value_of`/`set_value`, and «Сбросить» — so a preference cannot be editable
  without being stored or stored without being documented; two checks hold that:
  one that every key the module defines is either in the table or on
  `MACHINE_KEYS` (geometry, recent files, the insert table), another that every
  row has a widget and every widget writes its key.  «Применить» writes only the
  rows that *differ*, and the reason is the one preference that follows another:
  `output/font_size` unset means «the output goes with the editor», exactly as
  before this round, and the first wheel over the panel (or a value in the
  dialog) gives it a size of its own for good — the wheel over the editor and
  over the output now mean two different things, which is what the split is for.
  Two traps of the round, both about Qt and tests: a `QDialog` *hangs* a headless
  run (so the modal `exec()` lives in one replaceable method and the folder list
  looks its chooser up through a closure — a bound method captured in the
  constructor kept pointing at the real `QFileDialog` and blocked the suite with
  no output), and a `zoomChanged` signal still connected to the wrong handler
  dragged the editor's font along with the output's.  The rest of the list from
  task_29 is named in the task file with reasons: the dark theme (a second syntax
  palette), RU/EN, session restore, interpreter profiles and the sandbox limits
  need machinery that does not exist yet.  251/251 ctest, 20 GUI scripts, five
  PDFs; `gui.typ` §8 (rewritten around the dialog), §9.1 and §10, the README's
  new «Settings» section.
* GUI round, part 36 (follow-up after the first hands-on run): **«Применить» had to
  become visible**.  Writing the file was not enough — the window behind a modal
  dialog is blocked for input but keeps painting, and it only re-read the settings
  after `exec()` returned, so «Применить» and «ОК» looked like the same button.
  The dialog now says what it did (`changesApplied`) and the window answers by
  re-reading every value, so the editor, the output panel and the search path
  change with the dialog still open.  The same signal closed a second gap it
  exposed: the insert table of task_31 lives in the same file, so «Вернуть
  встроенную таблицу» reached nothing until `apply_settings` started pushing
  `shortcuts/table` into the open buffers.  The window test now asserts the new
  font and the missing line numbers *inside* the dialog's own callback; 251/251
  ctest, 20 GUI scripts, five PDFs.
* GUI round, part 36 (second follow-up): **the dialog's layout**.  The buttons are
  built by hand now — «Сбросить», «Импорт…», «Экспорт…» on the left, «ОК»,
  «Отмена», «Применить» on the right — because a `QDialogButtonBox` orders its
  buttons by role and by the current style, which cannot express a decision.  And
  the pages share one label column: a `QFormLayout` sizes that column to the
  longest label *on its own page*, so the fields jumped sideways when the section
  changed; every label now takes the width of the widest one in the dialog
  (PySide6's `QFormLayout` has no column width to set) and the values fill their
  column.  251/251 ctest, 20 GUI scripts, five PDFs; both are pinned by
  `button_order()` and `label_column_width()` in `test_settingsdialog.py`.
* GUI round, part 37: **the tabs of the previous run come back** — the last item
  the user picked from what was still open in task_29.  A file tab is remembered
  by its **path** (the next start reads the file, so a change refused at the save
  prompt is not resurrected) and an untitled one by its **text**, up to a 256 KiB
  budget; a buffer that does not fit is dropped whole and counted, an empty «Без
  имени» is not stored at all, a stored path whose file has gone is skipped and
  named in the status line, and a restored untitled tab counts as unsaved work so
  the next close asks about it.  The store is written in `closeEvent` *before*
  the save questions, because «Отмена» leaves the window open.  The two new keys
  (`session/tabs`, `session/current`) are machine rows, so the dialog grew by
  exactly one *preference*: «Файлы → Восстанавливать вкладки при старте», on by
  default.  Qt-free record helpers in `documents.py` (round trip, budget, junk
  lines) and a window check that closes one window over three tabs and opens the
  next one over the same settings file; 251/251 ctest, 20 GUI scripts, five PDFs.
* GUI round, part 37 (follow-up after the first hands-on look): **«Не сохранять»
  на «Без имени» больше не воскрешает текст**. Первый вариант писал список
  вкладок *до* вопросов о несохранённом, и отброшенный черновик возвращался на
  следующем запуске — ответ «не сохранять» превращался в неправду. Теперь список
  берётся до вопросов (объекты буферов, а не копии), а записывается только после
  успешного `close_all()`, и буферы, получившие ответ «Не сохранять», из него
  выбрасываются. Попутно исправилось и обратное: буфер, сохранённый в файл при
  закрытии окна, запоминается как этот файл, а не как «Без имени» с текстом.
* GUI round, part 38: **четыре переключателя, которые оставались** — «малочи» из
  списка task_29, и каждый из них переключатель над уже существующим поведением:
  «Автоотступ» (`editor/auto_indent`), «Следить за выводом» (`view/follow_output`),
  «Спрашивать ввод» (`view/input_mode`: «в панели» / «в диалоге») и «Выводить
  вопросы при запуске» (`execution/run_questions` — он же флаг `questions` у
  `load`, протокол 5).  Ничего больше не поменяло форму: `Enter` либо продолжает
  отступ строки, либо начинает строку с края (единица отступа остаётся за `Tab`);
  панель вывода либо держит конец в виду, либо стоит на месте (она и раньше
  переставала следовать, когда читатель прокручивал вверх, — переключатель про
  другое: «не уводите взгляд»); вопрос программы отвечают либо в консоли под
  выводом, либо в окне, независимо от того, что на экране; прогон либо отвечает на
  свои `?`-строки, либо грузится одними правилами — у `run_program` аргумент
  `questions` теперь по умолчанию берётся из настроек, а нажатие на маркер в полях
  по-прежнему спрашивает ровно свой вопрос явным `questions=False`.  В диалоге
  стало 32 строки (было 28), в файле 42 ключа.  Проверки: по одной на каждый
  переключатель (`test_editor.py`, `test_output.py`, `test_window.py`) и значения
  по умолчанию в `test_settings.py`.  251/251 ctest, 20 headless-скриптов GUI,
  пять PDF.
* GUI round, part 39: **тёмная тема**.  Пункт «Вид → Оформление» стал подменю из
  трёх записей (светлое, тёмное, как в системе): одним переключателем три темы не
  сказать, а заголовок «Системная тема (иначе светлая)» стал бы неправдой.
  Тёмная тема — это не инверсия светлой, а **своя палитра**: одна запись
  `theme.Palette` на тему (страница, подсветка из 15 цветов, полосы ошибки и шага,
  находки поиска, текущая строка, полоса номеров, маркер вопроса, цвета вывода),
  `appearance.qt_palette` переводит её в палитру виджетов, а редактор, буферы и
  панель вывода читают цвета из неё же.  Контраст 4.5 (WCAG AA) проверяется теперь
  не для одной светлой палитры, а по списку `Palette.readable_pairs` — для обеих и
  против той страницы, на которой цвет действительно рисуется; светлая при этом
  держит 4.5 везде, а проверка сразу нашла одно исключение: цвет трассы был 4.48,
  он стал на шаг темнее (4.61).  Смена темы видна в редакторе и *в панели вывода*:
  там запоминается вид каждой строки (`_kinds`), поэтому история перекрашивается,
  а не остаётся написанной красным светлой темы на тёмной странице.  В параметрах
  командной строки `--theme light|dark|system`; значение `dark` внесено в выбор
  строки «Оформление» в диалоге (32 строки, как и было), значок `view-theme`
  остался в аудите как картинка этого подменю.  251/251 ctest, 20 headless-скриптов
  GUI, пять PDF.
* GUI round, part 40: **«использовать системные цвета»** — последний пункт цветовой
  страницы.  Вариант «как в системе» был половиной темы: палитра виджетов от
  системы, а цвета подсветки — светлые, и на тёмном рабочем столе это ровно то, от
  чего тёмная тема и заводилась.  Теперь `system` следует за рабочим столом
  целиком: `appearance.apply_theme` возвращает палитру *и* стиль платформы, а
  `appearance.theme_palette("system")` отдаёт светлую или тёмную палитру по
  `QStyleHints.colorScheme()` (если платформа молчит — по цвету окна, который она
  дала).  Оба ответа — «какая схема у стола» и «что он поставил» — читаются один
  раз, при первом `apply_theme`, потому что после нашей палитры они говорят уже о
  нас: проверка на этом сразу и поймала старый дефект (под `system` печаталась
  «палитра платформы» #1e1e1e, то есть наша же тёмная).  Стиль запоминается
  **именем**: установка другого стиля удаляет прежний объект, и вернуть его —
  `RuntimeError: Internal C++ object already deleted`.  Настройка в диалоге теперь
  называется «как в системе — системные цвета»; хинт говорит, что «тёмное» — это
  своя палитра, а «как в системе» берёт цвета рабочего стола.  251/251 ctest,
  20 headless-скриптов GUI, пять PDF.
* Planning round, part 41: **два пункта списка task_29, которые не были строкой в
  диалоге, стали задачами** — `task_45_gui_graphics_window.md` (графика: бэкенд с
  битмапом внутри движка, события протокола 9 и снимок, холст и своё окно) и
  `task_46_interpreter_options_and_limits.md` (путь к интерпретатору, рабочий
  каталог процесса, профили и пределы на программу).  Пока писались, выяснилось,
  что записанное в task_29 было пессимистично: `maxSteps`, `maxDepth`,
  `maxNestedDepth` и `maxFindAllSolutions` в движке **уже есть** и выведены в
  `--max-steps`/`--max-depth`, так что `task_46` — это не новые опции движка, а
  ключ сессии, таймаут по часам и строки в диалоге; а графике нужен не только
  интерфейс, но и ответ на `getPixel` посреди встроенного предиката — отсюда решение
  держать пиксели в движке и посылать примитивы.  Заодно починено старое в
  `doc/gui.typ`: §9.3 обещал 42 нарисованных значка и 7 недостающих (сейчас 43 и 6,
  `execution-step-over` нарисован 2026-10-01, `view-theme` — картинка подменю
  «Оформление»), а §10 всё ещё называл отдельный размер шрифта панели вывода
  невыполненным — он есть с task_29; в §10 встали графическое окно и профили с
  ссылками на новые задачи, а в README — точные числа аудита (49/43/6).
* GUI round, part 42: **task_46, половина про пределы**.  Программа, ушедшая в
  бесконечный поиск, должна кончаться сама: теперь у запуска есть четыре предела,
  каждый называет себя, а ноль всюду значит «без предела».  В движке появились
  именованные значения по умолчанию и `Limits` с `applyTo(EngineOptions&)` — через
  него идут и флаги, и протокол, так что строка настроек и флаг не могут разойтись;
  `--max-findall` встал рядом с `--max-steps`/`--max-depth` (и `--max-findall 0`
  перестал значить «ноль решений» — теперь это «без предела», как у соседей).
  Протокол **9**: у `load` есть объект `limits`, и он применяется *до* загрузки —
  программу выполняет та же загрузка, и предел, поставленный после неё, опоздал бы
  к своему прогону.  Сообщение называет предел, его значение и то, где его поднять:
  «Превышен предел шагов выполнения: 5000 (--max-steps; «Предел шагов» в настройках
  окна)», и строка в диалоге носит то же имя.  `НАЙТИВСЕ`, упёршийся в предел, — это
  *диагностика*, а не тихая обрезка: список покороче, который потом считают ответом,
  хуже ошибки.  В диалоге четыре строки («Предел шагов», «Предел глубины», «Предел
  решений НАЙТИВСЕ», «Предел времени, с»), а прогон сам пишет в панель, с какими
  пределами пошёл.
  Таймаут решён **по часам окна** (`QTimer` и запрос `interrupt`), а не в движке:
  `steady_clock::now()` в горячем месте — это плата за каждое решение, и о том, что
  «слишком долго для урока», знает всё-таки передний край.  Отсюда два проверенных
  следствия: считающий прогон кончается по сроку (движок и так опрашивает флаг
  остановки на каждом шаге), а прогон, ждущий `ВВОД`, стоит *вне* решателя, и его
  обрывает только «Остановить» — так и записано в task_46, а не обещано иначе.
  Попутно протокол стал честнее: запрос с полем не того типа (`"maxSteps":-1`, или
  строка вместо числа) раньше молча превращался в огромный предел, а теперь это
  событие `error` с `kind":"protocol"`, и сессия читает следующую строку — на таком
  запросе процесс раньше падал.
  252/252 ctest, 20 headless-скриптов GUI, пять PDF (`gui.pdf` — 27 страниц, §6.3
  на 19–20; `help.pdf` — 30 страниц, §15 на 24).
* GUI round, part 42 (follow-up после разбора: **архитектура, умолчания и отмена
  RU/EN**).  Четыре правки одного вечера.
  (1) **Интерпретатор ничего не знает о GUI**: сообщения пределов больше не
  называют ни флаг, ни строку настроек — «Превышена глубина рекурсии: 200»,
  «Превышен предел шагов выполнения: 5000», «Превышен предел решений НАЙТИВСЕ:
  50».  ADR-020: предел — опция *запуска*, а не знание ядра; «где поднять» говорит
  тот, кто поставил число — флаг в `--help`, строка в диалоге.  В окне это делает
  сам прогон: строка «пределы: «Предел шагов» 5000 — строки в «Выполнении»
  настроек» перед запуском, и только про те пределы, что отличаются от умолчаний
  (иначе панель сообщала бы одни и те же два числа на каждом запуске).  Тесты
  стерегут обе стороны: в сообщении есть предел и его значение и нет слова
  «настройках».
  (2) **Умолчания ядра — без предела** (0 у шагов, глубины и НАЙТИВСЕ): свежий
  `prologd` ведёт программу до конца, а `--max-depth 0` перестал быть «снятием»
  того, чего и не было.  Единственный оставшийся умолчания —
  `kDefaultMaxNestedDepth`, и он не предел для пользователя, а защита стека
  вложенных решателей (task_38).  Следствие записано в руководстве честно: без
  предела убежавшую рекурсию не останавливает ничто, она растёт, пока не кончится
  память (цепочка кадров освобождается итеративно, так что это память, а не стек
  C++).  Отсюда и `engine_limits.cmake` теперь сам передаёт `--max-depth 10000`.
  (3) **Умолчания окна** — 0 / 1 000 000 / 1 000 000 / 0: шаги и часы выключены,
  глубина и решения ограничены числом, которого не заметит ни одна учебная
  программа, а убежавшая — не переживёт.  Это окно берёт на себя решение о том,
  что для урока безопасно, потому что ядро его не принимает.
  (4) **RU/EN отменяется** (ADR-021): окно остаётся русским, никакого
  `QTranslator`; английский остаётся у языка (имена встроенных, task_39) и у
  руководства.  Пункт закрыт в task_29 и в §10 `gui.typ` — теперь он там назван
  решением, а не долгом.
  252/252 ctest, 20 headless-скриптов GUI, пять PDF.
* GUI round, part 43: **task_45 — графическое окно**.  `ТОЧКА`, `ЛИНИЯ`,
  `ОКРУЖНОСТЬ` и `ЗАКРАСКА` рисовали в пустую реализацию: программа рисовала
  картинку, а студент не видел ничего.  Теперь экран ведёт *интерпретатор*
  (`BitmapGraphicsBackend`: буфер 1024×768, который сам отвечает на `TOCHKA(X, Y,
  Ц)`-чтение и сам выполняет `ЗАКРАСКА`), а окно получает каждую нарисованную
  фигуру — протокол **10**: события `graphics` (ячейка, отрезок или прямоугольник)
  и запрос `{"cmd":"graphics","snapshot":true}`, на который приходит `bitmap` со
  всем экраном (base64, по четыре байта на точку).  Пиксели остаются внутри не
  зря: `ТОЧКА(X, Y, Цвет)` читает точку, а `ЗАКРАСКА` — то, что только что
  нарисовано, и всё это изнутри встроенного предиката; синхронный вопрос оболочке
  посреди предиката протокол не задаёт нигде.  `graphics.py` (без Qt) повторяет
  те же правила рисования — Брезенхам, контур прямоугольника, эллипс по
  параметрическому уравнению, заливка по четырём соседям, отсечение по краям, — и
  `test_graphics.py` сверяет две реализации *попиксельно*: рисует программу, берёт
  у интерпретатора готовый растр и повторяет те же события на холсте.
  `graphicswindow.py` — отдельное окно (`Qt.Window`, иначе виджет с родителем
  становится дочерним и рисунок встраивается в редактор) с «Вписать в окно»,
  «1 : 1» с прокруткой, «Очистить», «Сохранить как PNG…» и координатами точки под
  курсором; открытость и положение окна — машинные ключи `view/graphics_visible` и
  `view/graphics_geometry` (`saveGeometry` в base64: Qt знает про экраны, а
  прямоугольник пришлось бы этому учить заново).  Меню больше не имеет
  выключенных пунктов: «Графическое окно» — последний, который чего-то ждал.
  Два дефекта нашлись ровно там, где их и обещала найти приёмка — глазами на
  нарисованном: эллипс читался как *прямоугольник* (`ОКРУЖНОСТЬ(X, Y, R, Цвет)`
  передаёт четыре числа как есть, а имена параметров с task_15 говорили `x1..y2`),
  поэтому лицо из `examples/drawing.pld` выходило синим полем, а не лицом; и
  пустой холст был *прозрачно-чёрным* (`bytearray` — нули, а нулевая альфа в
  `RGBA8888` — прозрачность), из-за чего сквозь рисунок просвечивал рабочий стол.
  Обе ошибки были невидимы для сверки двух реализаций: обе рисовали одинаково и
  обе неправильно.  264/264 ctest, 21 headless-скрипт GUI, пять PDF.
* GUI round, part 44: **task_47 и первая половина task_48 — то, что нашлось при
  работе с уроками и окном**.  Пользователь поправил урок 12 руками, и из этого
  выросли три задачи (`task_47`, `task_48`, `task_49`) и тринадцать замечаний;
  этот заход закрывает первое и половину второго.
  **Один стиль курса.**  21 из 25 программ репозитория выровнены самим
  интерпретатором (`prologd --format`: мягкий режим, ширина 80, один таб) — до
  этого уроки были в трёх стилях, а в `lesson_12` рядом с табами стояли пробелы.
  Важнее самой правки проверка: новый тест «every shipped program is already in
  the standard shape» сверяет каждый файл со его же форматированным видом и
  называет тот, который отстал, — стиль теперь не надо держать в голове.
  `examples/lessons/_old` не выравнивается нарочно: это образец порта, а не его
  стиль.
  **Что вылезло при выравнивании.**  Форматирование убирает висячие пробелы — и
  в строках `%!` тоже, — а `lesson_07` обещал строку `Загадано число. ` с
  пробелом (сам вывод его печатал); пробел убран из сообщения в правиле, а не из
  обещания, и правило про это записано в `doc/lessons.typ`.  Уроки 7 и 12
  держали запросы длиннее ширины, и мягкий режим их *переносил* — а треугольник
  на полях читает строку, так что запрос, разорванный надвое, переставал быть
  кликабельным; это заметил не глаз, а пришпиленные числа в `test_queries.py`
  (`lesson_07`: 19 → 18).  Поэтому у форматтера появилось правило: **запрос и
  директиву ширина не переносит ни в одном режиме** (комментарий и пустая строка
  автора — переносят), и оно закреплено в `test_formatter.cpp` на ширине 20 и 80.
  Два обещания `lesson_12` отстали от переписанного руками урока (список фигур
  рамки и сада), а анимация была закомментирована и не печатала ничего: всё снято
  с работающего интерпретатора, а рядом встала анимация из двух кадров (80 мс),
  чтобы обещание «анимация окончена» осталось настоящим; 250 кадров остались
  вопросом `%?`, который выполняется щелчком по треугольнику.
  **Жёсткий режим** переносит и после `:-`: голова предложения стоит одна, а цели
  тела начинаются со следующей строки — раньше первая цель пряталась в конце
  строки с головой, там, где её как раз и пропускают.  У фактов, запросов и
  директив форма не меняется: головы у них нет, и `:-` на отдельной строке — шум.
  **Режим форматирования** вернулся на панель инструментов, сразу за
  «Форматировать»: кнопка `QToolButton` со списком трёх режимов и «только
  выделенное» (значок `edit-format-set`, нарисованный давно и никем не занятый),
  а подменю «Правка → Формат» ушло — у органа управления одно место.
  **Меньше значков и команд** (task_48): `help-about.png` был тем же рисунком, что
  `prologd2.png` («О программе» теперь носит значок приложения), переключатели
  «Номера строк» и «Панель инструментов» остались словами (их картинки убраны),
  «Сохранить все» ушла с панели в «Файл», а команды «Найти выделенное» и «Найти
  выделенное назад» — из «Поиска» вместе со своими значками.  Аудит значков теперь
  45 имён, 41 нарисовано, 4 ждут (и `execution-restart`, нарисованный и никем не
  занятый).
  Тесты: 267/267 ctest (253 случая Catch2 — три новых: жёсткая форма головы,
  запрос с директивой в одну строку, «все программы уже в стандартном виде»),
  21 headless-скрипт GUI (`test_queries.py` с обновлённым списком вопросов,
  `test_window.py` с кнопкой режима на панели и без «Сохранить все»), пять PDF.
  Замечание про `window.close()` тоже оплачено временем: скрипт, закрывающий окно
  с несохранёнными правками, открывает настоящий модальный вопрос и вешает прогон
  — проверять восстановление сессии надо через `_store_session` и второй
  `MainWindow`, а не через закрытие первого.
* GUI round, part 45: **task_48 — вторая половина: один `Esc` и окно, которое
  открывается само**.  Просьба была ровно такой: «`Esc` закрывает окна и панели в
  порядке: графическое окно → поиск и замена → справка по предикату → шпаргалка по
  вставкам» и «окно графики открывается само при первом рисующем примитиве
  запуска, и больше в этом запуске никогда».
  **`Esc`.**  Обработчик один и живёт на главном окне (`MainWindow.keyPressEvent`
  плюс `_escape_closes_something`), а порядок — это цепочка `if`: графическое окно,
  полоса поиска, панель справки, шпаргалка; когда ничего из этого нет, клавиша не
  наша, и событие уходит дальше — тест это различает, потому что нажатие считается
  обработанным только тогда, когда что-то закрылось.  Сделано **распространением
  события**, а не `QShortcut`, и это не деталь: сочетание клавиш обрабатывается
  *раньше* виджета с фокусом и отобрало бы `Esc` у списка подсказок (он закрывается
  по `Esc`) и у поля «Найти» (там клавишу и нажали, поэтому закрыть полосу — это
  то, что она значит).  Эти два места отвечают за себя сами, до окна такая клавиша
  не доходит, и так и записано в `doc/gui.typ` §4.1.  У графического окна свой
  `Esc`: у него своя клавиатурная фокусность (оно может стоять на втором экране),
  и до главного окна эта клавиша не доходит; закрывается оно через `close()`, то
  есть тем же путём, что и крестик, — с галочкой в меню они не расходятся.
  **Окно, которое открывается само.**  `_on_drawn` показывает окно, если флаг
  `_graphics_shown` пуст; флаг очищает `run_program`, ставит `show_graphics_window`
  (кто бы ни показал — галочка, настройки или сам запуск), а скрытие окна его не
  очищает.  Из этого и получаются обе половины просьбы: рисунок виден без поиска
  галочки, а окно, закрытое во время длинной анимации, остаётся закрытым до конца
  прогона.  Момент выбран по первой *фигуре*, а не по началу прогона: программа,
  которая ничего не рисует, окна не открывает.  Догонять пропущенное не пришлось —
  `show_graphics_window` и так спрашивает снимок, так что окно, открытое на
  середине рисунка, получает его целиком.
  Тесты: два новых в `test_window.py` — по одному на половину.  Порядок `Esc`
  проверяется настоящим нажатием в *редактор* (чтобы шло распространение события),
  а «закрытое окно не открывается снова» — программой `?ТОЧКА(1, 1, 1),
  ЖДИ(200), ТОЧКА(6, 6, 6).`: закрытие приходится *между* двумя фигурами, иначе
  проверка прошла бы и без флага.  267/267 ctest, 21 headless-скрипт GUI, пять PDF.
* GUI round, part 46: **task_49 — четыре дефекта, найденные работой с окном, и
  размер главного окна**.  Пользователь добавил одну фразу к просьбе продолжить
  («Графическое окно сохраняет свой размер и положение, а при этом главное окно не
  сохраняет») — она и стала пятым пунктом задачи.
  **`Шаг` → `Стоп` → `Запуск`.**  Окно считало, что прогон всё ещё стоит на точке
  шага, и «Запуск» шёл по пути «продолжить», то есть посылал `step` в
  интерпретатор, который никого не ждёт: сессия отвечала именно той ошибкой
  «нет шага, который ждёт ответа», и программа не запускалась.  Состояние живёт в
  *сессии* (`_paused`), и снимают его события, которыми прогон кончается:
  `result`, `loaded`, ошибка и конец процесса.  Репродукция уточнила последнюю
  пару: вежливое «Стоп» завершает *запрос*, а не процесс, поэтому очищающим
  событием оказывается ошибка прерванного запроса — без этого случая проверка
  падает (и она же требует, чтобы процесс был жив, иначе «Стоп» мог бы сойти за
  конец сессии).
  **Две вкладки «Без имени».**  Репродукция решила, какое из двух правил было
  неверным: неверно было восстановление — менять `*` получала вкладка, которую
  пользователь не трогал (приветственная программа первой вкладки, рядом с ней
  пустая вторая; с одной вкладкой всё выглядело правильно только потому, что
  пустая вкладка вообще не запоминается).  Сессия пишется *после* вопросов при
  закрытии, то есть после того, как каждая правка уже разрешена: вкладка, которая
  вернулась текстом, — та, которую пользователь не трогал.  Поэтому запись о
  вкладке везёт признак «есть несохранённое», и он теперь в **JSON** — четвёртое
  поле через табуляцию не отличить от строки старого образца, в тексте которой
  табуляция есть (а в тексте программы она есть всегда).
  **Зависание на трассировке.**  Причину искали измерением, а не догадкой, и табло
  получилось таким: панель вывода, 20 000 строк — 0,68 с до и 0,26 с после;
  200 000 строк с пределом 50 000 — **21,9 с** до и **3,0 с** после; трассировка
  глубокой рекурсии (16 002 строки) целиком — 2,2 с до и 0,6 с после.  Две цены
  сложились: окно платило вызов Python на *строку*, а панель — подрезку истории
  по строке на строку, то есть квадрат (удаление из начала документа стоит
  примерно одинаково, сколько ни удаляй).  Теперь окно отдаёт вывод пачкой раз в
  оборот цикла событий и склеивает соседей одного вида (это не дроссель: ничего не
  теряется и ничего не ждёт часов — потерянная строка журнала хуже медленной), а
  панель режет историю куском в десятую часть предела.  Отрицательный результат
  тоже записан: сама по себе пачка не спасает (20 000 строк одним вставлением —
  тоже 27 мкс на строку), прокрутка — не цена (32 мкс на строку с выключенным
  слежением), и курсор — не цена (новый курсор на вставку: 7 мкс против 5 у
  постоянного).
  **Размер главного окна.**  Графическое окно помнит своё с `saveGeometry()` с
  task_45, а главное — то, которое двигают первым, — не помнило ничего.  Теперь оба
  ходят через один модуль `prologd_gui.geometry`, и ключ `view/window_geometry` —
  машинный (это запись окна о себе, а не строка в диалоге).  Проверка ставит окно
  в 720×520 в (60, 40), закрывает, открывает заново с тем же файлом настроек и
  требует те же числа, а без записи — прежний размер 1000×700; и она *не* берёт
  910 точек ширины, потому что экран offscreen-платформы — 800×800, а
  `restoreGeometry` по-своему правильно зажимает размер, который в экран не влезает.
  Репродукции закреплены тестами и проверены «наоборот»: со спрятанной правкой
  каждая из них падает (`git stash` на одном файле), с правкой — проходит.
  Тесты: 267/267 ctest, 21 headless-скрипт GUI (четыре новых проверки в
  `test_window.py`, одна в `test_documents.py`, обновлённая в `test_output.py`),
  пять PDF.  Осталось в task_49: живой вывод — `IoContext` отдаёт строку, сессия
  шлёт событие на строку, и счёт печатается 3, 2, 1.
* GUI round, part 47: **task_49 закрыт — живой вывод**.  Последний пункт задачи
  родился из анимации урока: программа печатает строку, спит, печатает следующую, а
  окно показывало это одним блоком в конце прогона, поэтому счёт в уроке 12
  выглядел прыжком на последнее число.
  Шов сделан в `IoContext`: `setOutputLineSink` — «строка, которую пишут, кончилась»,
  и он срабатывает на `ПС` и на перевод строки, который несёт сам `ВЫВОД` (потому
  что строка тогда кончается, хотя приглашения никто не печатал).  Хук говорит
  *когда*, никогда *что*: текст берёт владелец из своего же потока, поэтому консоль
  не меняется ни на байт, а программа, уведшая вывод в файл, не сообщает ничего.
  Сессия ставит хук после `setTraceSink` и отвечает на него `flush()` — тем самым,
  который и раньше отправлял `output` в конце запроса; гранулярность стала
  построчной, форма события и порядок текста — нет.
  Измерение (программа печатает три строки с `ЖДИ(60)` между ними): без хука
  `loaded@0.15`, а за ним **одно** `output@0.15` со всеми тремя строками; с хуком
  `output@0.01`, `output@0.08`, `output@0.14`, и только потом `loaded@0.14`.
  Проверки: `test_io_context.cpp` (хук молчит на недописанной строке и на контексте
  без владельца), раздел в `protocol_session.cmake` (четыре строки, каждая *до*
  `loaded`, и позиции `one < two < three < loaded`), `protocol_smoke.py`,
  `test_stepping.py` и новая `test_window.py::test_the_output_arrives_while_the_program_runs`
  (первая строка в панели, пока идёт прогон, третьей ещё нет, «Запустить» выключена
  — а потом есть и третья, и конец прогона).  Две старые проверки ожидали один блок
  на строку-склейку и обновлены: текст тот же, крупность мельче.
  Тесты: 268/268 ctest, 21 headless-скрипт GUI, пять PDF.
* GUI round, part 48: **значки в тёмной теме приняты** — пользователь посмотрел
  перерисованные значки: «иконки в тёмной теме нормальные», дорисовывать нечего.
  Это закрывает последний хвост `task_48`, и на доске остаётся только `task_46`
  (путь к интерпретатору, рабочий каталог процесса, профили) плюс решение, нужен ли
  текстовому режиму `--timeout-ms`.
* GUI round, part 49: **task_46 — путь к интерпретатору и рабочий каталог процесса;
  `--timeout-ms` решён и отложен**.  Пользователь выбрал первые два пункта и
  отказался от четвёртого.
  **Интерпретатор.**  Строка `execution/interpreter` — новый тип `file` в таблице
  настроек (со своим «Обзор…»: выбирает файл, а не каталог); пустая строка значит
  «тот, с которым окно запущено», а заполненная главнее `--exe`, который остаётся
  запасным (сам он, как и раньше, ищет свежую сборку).  `main.py` проверяет теперь
  тот путь, который *действительно* запустится, — иначе на машине учителя, где
  рядом с окном лежит свой `prologd.exe`, проверка строительного пути ошибочно
  отказала бы.  Сессия получила `set_executable`/`executable`, и у окна появился
  один шлюз `_start_session`, через который проходят все три места, где сессия
  заводится (запуск, запрос, форматирование): несуществующий путь сообщается в
  панели до всякого старта, а не половиной запущенного процесса.  Строка состояния
  называет интерпретатор, когда строкой выбран другой (`prologd: …` справа), — то
  есть окно видно, что работает не та сборка.
  **Рабочий каталог процесса.**  `execution/process_directory` — выбор из трёх:
  «каталог файла программы» (сохранённый файл пишет рядом с собой), «рабочая папка
  окна» (прежнее поведение) и «свой каталог» (`execution/process_directory_path`).
  Это не «Рабочая папка (ИМПОРТ)» — та строка идёт в `-I` как каталог *поиска*,
  а эта — `QProcess.setWorkingDirectory`: от неё считаются `ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ`
  и остальные относительные пути.  Раньше всё это писало туда, откуда запущено окно
  (наследуется у родителя), то есть у каждого ученика — в другое место.
  **«Применить».**  Перемены в любом из двух пунктов не могут дойти до живого
  процесса (программа и каталог зафиксированы стартом), поэтому живая сессия
  перезапускается — и строка состояния об этом говорит; путь, которого нет, живую
  сессию не трогает и пишет «интерпретатор не найден».
  **`--timeout-ms`** — решено не делать: часы в горячем месте решателя были бы
  платой за каждое решение, предел времени окна это уже покрывает, а у консольного
  запуска есть таймаут оболочки.
  Проверки: `test_settings.py` (умолчания и круговорот новых ключей, битый выбор
  падает в `file`), `test_settingsdialog.py` (строка-файл спрашивает файл, а не
  каталог; выбор из трёх), три новые в `test_window.py` (копия exe как «другой»
  интерпретатор — строка доходит до сессии, прогон идёт копией, строка состояния
  её называет; несуществующий путь сообщается в панели и сессии не заводит;
  `ЗАПИСЬ_В` пишет в выбранный каталог — и фиксированный, и «рядом с файлом»).
  Осталось в task_46: профили.
* GUI round, part 50: **мелкая уборка настроек**.  Пользователь попросил свести
  лишнее и уточнить подписи.
  **Одна строка вместо двух для `ИМПОРТ`.**  «Рабочая папка (ИМПОРТ)» влита в
  «Дополнительные каталоги ИМПОРТ»: был один каталог плюс список, стал один
  список (`execution/import_paths`); ключ `execution/working_directory` исчез из
  таблицы, а `_import_directories` собирает `-I` из командной строки и этого
  списка.  Старый файл настроек хранит бывший ключ как незнакомый (обещание
  «незнакомые ключи выживают»), но он больше не читается.
  **Кнопки списка** «Добавить»/«Убрать» — без текста: остались иконки
  (`settings-add`/`settings-remove`), текст переехал в подсказку.
  **«Свой каталог процесса»** неактивен, пока в «Рабочем каталоге процесса» не
  выбран «свой каталог» — поле и его «…» выключаются одним рядом; диалог держит
  обёртку строки (`_row_holders`) и вешает её на смену выбора.
  **Предел времени — в миллисекундах.**  Ключ `execution/timeout_seconds` →
  `execution/timeout_milliseconds`, строка «Предел времени, мс» (потолок — час,
  3 600 000), подсказка «по времени» вместо «по часам», `_arm_timeout`/`_on_timeout`
  ставят таймер и пишут «N мс».
  **Подсказки и подписи.**  «Сохранять перед запуском» уточнён (сохраняет текущий
  файл); из подсказки «Восстанавливать вкладки» убрано про «Без имени»; тема
  «как в системе — системные цвета» → «системное» (и в меню «Оформление» —
  «Системное»).
  Проверки обновлены под новое (`test_settings.py`, `test_settingsdialog.py` — в
  том числе новая «путь неактивен до «свой каталог»», `test_window.py` — предел
  в мс и список `-I`, `test_appearance.py`).  21 headless-скрипт GUI, пять PDF.
* GUI round, part 51: **флаг `questions` разделён на «выполнять» и «печатать»**.
  Один переключатель «Выводить вопросы при запуске» делал две вещи сразу, и
  пользователь попросил их развести.  Теперь «Выполнять вопросы при запуске»
  (`execution/run_questions`, был и остался `questions` на проводе) решает,
  выполняются ли `?`-строки программы при запуске, а «Печатать вопросы при
  запуске» (`execution/print_questions`, по умолчанию выключен) печатает сам
  вопрос — `?цель.` — перед его ответом, как `-q` в командной строке.
  Это **протокол 11**: у `load` появился `printQuestions`; эхо делает сессия в
  `runQuery` (событие `output` перед `result`), а не окно.  Чтобы строка вопроса
  печаталась с *именами* переменных, а не `_1`, `Engine::queryText` (общий для
  `-q` и протокола) отдаёт печатнику словарь имён через новое поле
  `PrintOptions::variableName` — `ВЫВОД` и остальная печать по-прежнему пишут
  `_N`, как обещает руководство.  `-q` и раньше писал `?факт(_1).` — теперь и
  он, и окно пишут `?факт(X).`.
  Проверки: `protocol_session.cmake` (эхо до ответа), `test_formatter.py` и
  `protocol_smoke.py` (protocol 11), `test_settings.py` (умолчание `print_questions`),
  новая `test_window.py::test_print_questions_echoes_the_question_line`.  268/268
  ctest, 21 headless-скрипт GUI, пять PDF.
* GUI round, part 52: **справка: многострочный просмотр, алиас у имени, единые
  имена аргументов**.  Пользователь попросил три вещи про справку и просмотр
  справочника.
  **Многострочный просмотр при автодополнении.**  Метка под списком показывала
  одну строку `имя — сводка`; теперь `Reference.detail_lines` собирает
  «имя (алиас) — сводка», затем варианты вызова, а метка переносит текст по
  ширине 460 (`setWordWrap` + `setMaximumWidth` до `adjustSize` — иначе метка
  размерится на одну длинную строку).
  **Алиас у имени.**  Из `F1` убрана строка «английское имя: …»; английское имя
  стоит рядом с русским в скобках: `ВВКОД (put_code) — …`.  Первая строка записи
  общая для док-окна и просмотра (`reference.record_title`).
  **Имена аргументов.**  `builtins.json` и `doc/help.typ` переведены на одно
  словарное множество: `Ц` — целое, `Вещ` — вещественное, `Пер` — переменная,
  `Стр` — строка, `Терм` — терм, `Спис` — список (было `X`, `с`, `ц1`, `П`,
  `S`, `N`, `Строка` вперемешку).  Проверка вариантов против кода нашла одну
  опечатку: у `УМНОЖЕНИЕ(ц1, П2, ц3, ц4)` делитель был `ц2`, а в коде — `ц1`
  (для свободного второго аргумента); `СЛУЧ` разложен на три варианта (семя /
  случайное целое / диапазон), а `ВВКОД` на два по ролям аргумента.  Сводки
  уточнены там, где ссылались на старые имена (`УМНОЖЕНИЕ`).
  Проверки обновлены (`test_completion.py` — многострочный текст с алиасом,
  `test_window.py` — `F1` без «английское имя», с новыми именами).  `test_reference.py`,
  `test_completion.py`, `test_window.py` зелёные, пять PDF.

* GUI round, part 53: **task_50 — панель вывода с вкладками**.  Пользователь
  попросил превратить панель вывода в четыре вкладки: **Проблемы**, **Вывод**,
  **Система**, **Ввод**.
  **Вкладки.**  Панель — один `QTabWidget` (`_panel_tabs`); три read-only панели
  это всё тот же `panels.OutputPane` (ограниченная история, цвета по роду, хвост
  строки), а «Ввод» — очередь подготовленных ответов с консолью запроса под
  ней.  Род строки решает вкладку: `OUTPUT`/`ECHO`/`TRACE` → Вывод, `NOTE` →
  Система, `ERROR`/`WARNING` → Проблемы (`panels.KIND_TAB`, маршрутизация в
  `_feed_pane`).  «Сохранить вывод…» пишет вкладку Вывод.
  **Названия со счётом и цвет.**  В заголовке вкладки стоит счёт:
  `Вывод:5`, `Проблемы:0`, `Система:3`, `Ввод:2` (Ввод считает непустые строки
  очереди и обновляется по `textChanged`).  Слово «Проблемы» крашено по
  состоянию: обычный цвет, когда пусто, оранжевый при одних предупреждениях,
  красный, когда есть ошибка (`_error_count`/`_warning_count`, `tabTextColor`).
  **Фокус.**  Запуск показывает Вывод, диагностика (и предупреждение, и ошибка)
  переключает на Проблемы (`_show_panel_tab`); консоль запроса поднимает вкладку
  Ввод, когда программа спрашивает.
  **Убранное.**  Настройка «Поле очереди ввода» (`view/input_queue`) и её строка
  меню удалены — очередь теперь вкладка; `view/output_sizes` исчез (внутреннего
  сплиттера больше нет); панель по умолчанию **внизу**.
  **Таймер загрузки.**  После полного выполнения файла в Систему пишется
  `--- база знаний загружена (N мс) ---` — время меряет `QElapsedTimer` окна от
  «Запустить» до события `loaded` (протокол 8).
  Проверки: `test_window.py` — новая `test_the_panel_has_four_tabs_with_counts`
  (вкладки, счёт, цвет, фокус по диагностике) и
  `test_a_run_focuses_the_output_and_the_system_notes_the_time`; прежние прогоны
  переведены на `system_text()`/`problems_text()` (заметки и диагностика больше не
  в Выводе).  `test_settings.py`/`test_settingsdialog.py` — без `input_queue`,
  умолчание `bottom`.  Все GUI-свиты зелёные.

* GUI round, part 54: **настройки — секция «Подсветка»**.  Пользователь попросил
  показать в настройках, что чем подсвечено и каким hex в каждой теме.
  В диалоге появилась страница **«Подсветка»** — сразу после «Вид»: таблица
  `что подсвечено · светлая · тёмная`, в которой каждая из 15 ролей подсветки
  (`Комментарий`, `Вопрос в комментарии`, `Строка`, `Атом в кавычках`,
  `Служебное имя`, `Целое`/`Вещественное`, `Знаки препинания`, `Вопрос`,
  `Выражение`, `Атом`/`Переменная` латиницей и кириллицей, `Имя из двух
  алфавитов`) показана своим hex в обеих темах; hex залит своим цветом (текст —
  чёрный или белый по яркости), страница read-only — менять весь набор можно
  «Вид → Оформление».  Данные Qt-free: `theme.SYNTAX_LABELS` (имя поля → подпись)
  и `theme.syntax_rows()` (роль, светлый hex, тёмный hex) — диалог и тест читают
  одно и то же, так что новая роль в `Theme` сама попадает в страницу.
  Проверки: `test_settingsdialog.py` — страница «Подсветка» в списке после «Вид»
  и новая `test_the_syntax_page_lists_every_colour_in_both_themes` (15 ролей,
  обе темы, первый ряд — комментарий).  `test_appearance.py`/`test_settings.py`
  зелёные.

* GUI round, part 55: **«Подсветка» стала изменяемой**.  Пользователь спросил
  «сможем сделать изменяемые?» — да, смогли.
  Каждая hex-ячейка на странице «Подсветка» теперь **кнопка-свотч**: клик
  открывает выбор цвета (заменяемый `_ask_color` — модальный `QColorDialog`
  вешает headless-тест), и выбранный hex красится на кнопке.  «Применить» пишет
  в настройки **только изменённые** роли, по теме: ключи `syntax/light` и
  `syntax/dark` (JSON `поле: "#rrggbb"`, в `MACHINE_KEYS`); «Вернуть встроенные
  цвета» сбрасывает оба.  Чтение чистит мусор: `Settings.syntax_overrides`
  берёт только известные поля с валидным hex (`theme.clean_hex`), а
  `Settings.palette` накладывает их на разрешённую палитру через
  `theme.apply_syntax_overrides` — `system`-тема берёт override той палитры,
  которую выбрал рабочий стол; хром (страница, полосы, цвета вывода) не трогается.
  Проверки: `test_settings.py` — `test_syntax_overrides_round_trip_and_reach_the_palette`
  (круговорот, чистка мусора, override доходит до палитры и не двигает хром),
  `test_settingsdialog.py` — `test_a_colour_can_be_changed_and_applied` (клик по
  свотчу, «Применить» пишет, «Вернуть встроенные» стирает).  Полные
  `test_settings.py`/`test_settingsdialog.py` зелёные (52 ключа — 38 в диалоге,
  14 машинных), палитровые тесты окна зелёные.

* GUI round, part 56: **упрощённая палитра стала умолчанием**.  Пользователь
  подобрал в «Настройки → Подсветка» свой набор (меньше разных цветов, русский
  и английский — одинаково) и попросил зашить его в поставку.
  В `theme.py` обновлены обе палитры: `query_comment` = цвету комментария,
  `quoted_atom` = цвету строки, `keyword` = цвету `query`/`expression`,
  `atom_latin == atom_cyrillic` (фиолетовый `#4f1473` / `#d47bdc`),
  `variable_latin == variable_cyrillic` (красный `#b62222` / `#ff7878`),
  `mixed` — ярко-красный флаг `#e30004` в обеих темах; уточнены `string`,
  `punctuation`.  `mixed` выведен из WCAG-проверки в `readable_pairs` — это
  сигнал, а не текст.  Проверки: `test_appearance.py` (контраст), `test_highlighter.py`
  (комментарий про алфавиты обновлён), `test_settings.py`, `test_settingsdialog.py`,
  `test_window.py` — зелёные.

* GUI round, part 57: **строка цели — история и автодополнение**.  Пользователь
  попросил у поля цели (строка `?цель(X).` под редактором) две вещи: историю и
  подсказки, как в основном редакторе.
  Появился `editor.QueryLine` (подкласс `QLineEdit`) вместо голого поля:
  **история** — `Up`/`Down` ходят по отправленным целям (до 20, старые
  вытесняются; пустая и сразу повторённая не записываются; `Down` мимо самой
  новой возвращает черновик); **автодополнение** — тот же
  `completion.CompletionModel`, что у редактора: зарезервированные имена +
  предикаты текущего документа (`document_text` — показываемый буфер),
  `Ctrl+Пробел` или набор открывают попап, `Enter`/`Tab` вставляют каркас вызова
  с курсором после `(`.  Placeholder дополнен подсказкой
  `… Enter: выполнить · ↑/↓: история · Ctrl+Пробел: подсказки`.  Окно передаёт
  полю ключевые слова (`_on_ready`), `auto_complete_after` и `completion_match_case`
  (`apply_settings`).  Проверки: новый `test_queryline.py` (4 проверки — история,
  лимит и дедуп, подсказки и каркас, Escape), `test_editor.py`/`test_window.py`
  зелёные.

* GUI round, part 58: **вкладка «Ввод» — только очередь; консоль запроса — под
  строкой цели**.  Пользователь попросил разнести ввод: вкладку «Ввод» оставить
  только очередью (и не переключаться на неё), а появляющийся при запросе
  `LineEdit` перенести под строку цели.
  Консоль запроса (`panels.InputPane`) ушла из вкладки «Ввод» в редакторскую
  колонку — под строку цели; при вопросе она появляется там, а панель остаётся
  на вкладке, которую выбрал читатель (обычно «Вывод») — `_show_panel_tab(Ввод)`
  из `_on_input_request` убран.  Вкладка «Ввод» теперь только очередь
  подготовленных ответов (счёт `Ввод:N` не меняется).  Проверки: новая
  `test_window.py::test_a_request_keeps_the_panel_on_the_output` (консоль не во
  вкладке «Ввод», панель остаётся на «Вывод», ответ проходит), полный
  `test_window.py` зелёный.

* GUI round, part 59: **консоль запроса — минимальная высота**.  Пользователь
  заметил, что появившаяся консоль растягивается на всю колонку: её `QLineEdit`
  плавал в середине высокой пустой полосы.  У `panels.InputPane` вертикальная
  политика размера стала `Fixed` (всегда по своему содержимому, не растягивается),
  а текстовая область ответа `line` ограничена четырьмя строками вместо дефолтных
  ~192 px.  Проверки: новая `test_window.py::test_the_console_stays_one_field_high`
  (политика `Fixed` и высота ≈ sizeHint после показа окна), `test_output.py` и
  полный `test_window.py` зелёные.

* Interpreter round, part 60: **`\+` и подсказка вместо `is/2`** (task_55,
  2026-10-02).  Ответ на вопрос пользователя «осталось 2 существенных пункта,
  где Пролог-Д расходится с другими: `is` и `\+ Ц`»: `\+` добавлен, `is` — нет.
  `\+` — один токен (`TokenKind::NotGoal`: `peek(1) == '+'` в лексере, одинокий
  `\` остаётся «недопустимым символом») и префикс уровня терма в `parseTerm`,
  разворачивается в `НЕ/1`; приоритет ISO: `\+ A, B` — это `(\+ A), B`,
  `\+ (A, B)` — отрицание конъюнкции, `\+ \+ Ц` — двойное отрицание;
  `НАЙТИВСЕ(1, \+ РАВНО(1, 2), L)` отвечает `L=[1]`, а `\+ (ЛОЖЬ, РАВНО(B, 1)),
  ПЕР(B)` — `B=_1` (связывание внутри отрицания отменяется).  Семантики,
  диспетчера, `--list-keywords` и `doc/builtins.json` изменение не касается: это
  запись, и проверка вызовов видит тот же `НЕ/1` (`walkGoal` его и так
  раскрывает).  Формат читает `\+` как один токен и в строке не рвёт; в GUI
  (`tokens.py`) он тоже один знак препинания, как `:-`.
  Вместо `is` — подсказки: `?is(X, #2+3#).` получает предупреждение «не найдено:
  is/2; «is» — не предикат: в Пролог-Д это «РАВНО(X, #2+3#)»» (имя при этом не
  зарезервировано — своё `is/2` программа определить может), а `?X is 2+3.` —
  ошибку разбора ««is» — не оператор: выражение помечают «#…#», например
  «РАВНО(X, #2+3#)»»: без неё читатель ISO слышал только «Цель не может быть
  переменной».  Настоящий оператор не добавлен сознательно: `#…#` — признак
  выражения (вычисляется везде, где нужно число, а унификация обратима:
  `РАВНО(5, #2+3#)` — ДА), и `is` ввёл бы вторую арифметику — голые `2+3` в
  целях, — которую пришлось бы дать и сравнениям (`X < 2+1`, `=:=`), а от них уже
  решено отказаться (task_52).  Проверки: 274/274 ctest — шесть новых случаев
  Catch2 (лексер, парсер с сообщением про `is`, `\+` как `НЕ` в control-тестах,
  формат) плюс тест текста предупреждения `is/2`; GUI `test_tokens.py` (новая
  пара `\+`) и `test_reference.py` зелёные.  Руководство: §3.3 (про `is`), §4.4
  и приложение, обе строки сравнительной таблицы; `prologd-diff.typ` — §19, §20 и
  две строки в §14.

* Тот же день, продолжение: **пример с дизъюнкцией и формулировка про точку**.
  `prologd-diff.typ` §16 показывает задачу «в набор годятся и дешёвые
  инструменты, и надёжные» в трёх записях: два предложения с одним заголовком
  (Пролог-Д 1.0), `ИЛИ/2` (одна ветвь) и `;` в теле правила (обе ветви).
  Прогоны на собранном интерпретаторе: `?НАЙТИВСЕ(Т, годится(Т), L)` даёт
  `L=[молоток,отвёртка,тиски,струбцина]` для `;` и двух предложений, но
  `L=[молоток]` для `ПЕРВОЕ`; отдельный листинг — про альтернативу в середине
  правила, где раньше повторялся общий «хвост» (`со_скидкой` в двух записях даёт
  `L=[молоток,тиски]`).  Заодно исправлена фраза в §17, оборванная правкой
  пользователя.  Сообщения о `;` там, где диалект 1.0 принимал её как
  терминатор, и о пропущенной точке стали предписывающими: «предложение должно
  заканчиваться точкой» (было «не заканчивается»; первую формулировку,
  «предложение заканчивается точкой», пользователь забраковал ещё в task_40) —
  правка в `parser.cpp`, двух тестах и цитате в §16 `prologd-diff.typ`.

* Тот же день, продолжение: **пропущенная точка видна не только в конце файла**
  (task_56).  Наблюдение пользователя: у двух фактов подряд без точки в конце
  первого (`студент(вова, корчагин)` строкой выше `студент(данил, ахмеров).`)
  выдавалось `2:1: ошибка при разборе предложения`, а полезная формулировка —
  только когда точка пропущена у самого последнего предложения.  Причина: новый
  перевод строки ничего не заканчивает, поэтому парсер склеивал два предложения
  и спотыкался на имени второго — в общей ветке `parseClause`, где сообщение
  ничего не говорит.  Теперь `beginsStatement(kind)` отличает токен, с которого
  может начаться терм/факт/правило/запрос, от всего остального: после
  законченного предложения это значит «нет точки», и `reportMissingDot()`
  показывает позицию на *конце своего* предложения (`1:42` у примера выше, где
  `)` стоит 42-м байтом).  Тот же случай в запросе (`?- a(1)` × 2 строки) и в
  правиле.  Общая формулировка осталась там, где следующее предложение начаться
  не может (`a(1), b(2).`) и где уже есть точная диагностика (`p :- f(a "b").`
  — «непарные скобки»).  Проверки: `студент(вова, корчагин)` + вторая строка —
  два новых случая Catch2 (парсер: факт, правило, запрос, «точка везде»;
  загрузчик), ctest 276/276.

* Тот же день, продолжение: **таблица сравнения открывает «Изменения языка», а
  номера разделов считает Typst**.  Просьба пользователя: перенести таблицу в
  самое начало, как в руководстве, и обойтись без ручной перенумерации.
  Таблица теперь первый раздел без номера (`#heading(numbering: none)`; счётчик
  его пропускает, главы по-прежнему начинаются с 1), в заголовках цифр нет
  (`#set heading(numbering: "1.")`), а ссылки в тексте берут номер из счётчика:
  `#sec(<sec:arith>)` и т. п. — `#ref` подставил бы и слово («Раздел 16»), а в
  середине фразы нужно число.  Всё, что раньше было написано руками, посчиталось
  само: `;` — раздел 14, `НАЙТИВСЕ` — 15, `ПЕРВОЕ` — 16, `\+` — 17, `is/2` — 18
  (в тексте §6/§12/§14/§16/§18 и в строке таблицы).  Заодно две неточности:
  ячейка «Дизъюнкция `;`» говорила «приоритет как у `,`», а на самом деле `,`
  связывает *крепче* — прогон `?НАЙТИВСЕ(X, (РАВНО(X, 1), РАВНО(X, 2) ;
  РАВНО(X, 3)), L).` даёт `L=[3]` (при обратном порядке вышло бы `L=[]`), в
  таблице теперь «есть: `A ; B`, а `,` связывает крепче»; и `**сохранена**`
  (двойные звёздочки в Typst ничего не выделяют, только предупреждение) стало
  `*сохранена*`.  Документ пересобран: 22 страницы, заголовки 1–19 без цифр в
  исходнике.

* Interpreter round, part 61: **`ПЕРВОЕ` берёт любое число целей** (task_51,
  2026-10-02).  Ответ на вопрос пользователя «сейчас `ПЕРВОЕ` у нас с двумя
  аргументами, сложно ли заменить на любое количество, как у `ВЫВОД`?», решённый
  в пользу «от арности 1»: в целом тракте (диспетчер, таблица ключевых слов,
  проверка вызовов, `--list-keywords`, событие протокола, автодополнение)
  `variadic` уже значит «хотя бы один аргумент», поэтому нигде не появилось
  второго поля.  `builtinOr` стал `builtinFirst` и обходит `args` через
  `callOnce` — первая цель, у которой есть решение, фиксируется; зашитый
  `isVariadicBuiltin` (два сравнения имён) стал таблицей `kVariadicNames`
  (`ВЫВОД`/`write`, `ПЕРВОЕ`/`first`), из которой читают `findBuiltin`,
  `builtinArities` и `builtinNames`, а строка `add("ПЕРВОЕ", 2, …)` и `add`
  больше на два имени не опираются.  Двухаргументные вызовы отвечают как
  раньше, `;` по-прежнему дизъюнкция, а разбор, движок, лексер и `checks.cpp` не
  тронуты.  Проверкой нашлась одна неточность в самой формулировке задачи:
  одноаргументное `ПЕРВОЕ(Ц)` — это *фиксация* на первом решении, а не `ВЫП(Ц)`
  (`?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` → `L=[1]`, у `ВЫП(p(X))` — `L=[1,2]`), и в
  руководстве §4.6 теперь так и написано.  Арность 0 — ошибка загрузки
  («ПЕРВОЕ не имеет арности 0», код 2).  Руководство §4.5/§4.6,
  `technical.typ`, §«`ПЕРВОЕ` вместо `ИЛИ`» и строка таблицы в
  `prologd-diff.typ`, `doc/builtins.json` (`arities: []`, `variadic`),
  `ai/porting_notes.md`, `gui/README.md`.  Проверки: 278/278 ctest (новый случай
  Catch2 на вариадику и CLI-тест `ПЕРВОЕ/+`), шесть GUI-наборов
  (`test_reference`, `test_completion`, `test_keywords`, `test_queries`,
  `test_tokens`, `test_queryline`) зелёные, три документа собираются Typst.

* Interpreter round, part 62: **знаки сравнения — сахар над встроенными**
  (task_52, 2026-10-02).  Ответ на «он же + ISO-сравнения»: `=`, `<`, `>`, `>=`,
  `=<` — не новые имена, а вторая запись `РАВНО`, `МЕНЬШЕ`, `БОЛЬШЕ`.  В
  `parser.cpp` одна таблица `kInfixOperators` (`=`→`РАВНО`, `<`→`МЕНЬШЕ`,
  `>`→`БОЛЬШЕ`, `=<`→`НЕ(БОЛЬШЕ)`, `>=`→`НЕ(МЕНЬШЕ)`) и один слой между `#…#` и
  всем остальным: знаки связывают крепче `,` и `;` и слабее `#…#`, цепочка
  `0 < X < 10` — ошибка разбора с одним сообщением (««<» — не цепочка: разбейте
  на два сравнения, «A < B, B < C»»), а `skipToTerminator` не даёт парсеру
  сказать то же второй раз про «непарные скобки».  Всё, что ниже, о знаках не
  знает: диспетчер, проверка вызовов, `--list-keywords`, протокол и
  `doc/builtins.json` видят те же предикаты, поэтому `НЕ(X = 1)`,
  `НАЙТИВСЕ(X, (X = 1), L)`, `ВЫП((X = A))` и `r([A = B])` разбираются без
  единой правки в движке.  Четыре вещи нашлись по ходу.  (1) **Правило числа.**
  Перенесённая запись `1.` = 1.0 съедала терминатор: `?2 > 1.` не разбиралось
  вовсе.  Решение пользователя — правило ISO: `1.` это целое `1` и точка,
  вещественное пишут `1.0`; это единственное место задачи, где меняется язык
  (`#1.#` больше не загружается), и оно записано в `help.typ` §3.2 и в
  `prologd-diff.typ`.  (2) **`#…#` — операнд.**  `parseTerm` возвращал
  `parseArithmetic()` раньше времени на `#`, и `r(#1 + 1# = 2)` падало с
  «непарные скобки»; теперь операнд берёт `parseOperand`, и тест на это есть.
  (3) **Подсказки — в лексере** (`kForeignOperators`, длинные записи первыми:
  `=:=`, `=\=`, `\==`, `\=`, `==`, `@=<`, `@>=`, `@<`, `@>`, `->`, `<=`): чужая
  запись объясняется там, где стоит знак, и `?X <= 1.` начинается с ««<=» — не
  оператор: «меньше или равно» записывают «=<»», а не с «Цель не может быть
  переменной».  (4) **GUI — только подсветка**: знаки стали видом `OPERATOR`, а
  `Ctrl+=` остался за `РАВНО(`, как решил пользователь, поэтому `shortcuts.py` не
  изменился.  Слабое место, оставленное нарочно: `X < 2+1` (без `#…#`) даёт общее
  «ошибка при разборе предложения» — подсказку про `#…#` там можно добавить
  отдельно, как у `is`.  Руководство: `help.typ` §3.2/§3.3/§4.7/§5.1 и строки
  таблицы, `prologd-diff.typ` §9 и три строки «Краткой таблицы»,
  `technical.typ`, варианты в `doc/builtins.json`; уроки 3 и 4 получили пример
  с короткой записью (решение пользователя: «и урок 3, и урок 4») — их `%!`
  строки сами себе золотой ответ, поэтому `test_lessons.cpp` не менялся.
  Проверки: 285/285 ctest (семь новых случаев), 21 набор GUI (`test_*.py`) и
  `protocol_smoke.py`, пять PDF;
  счётчики `test_queries.py` пришлось освежить — правка урока 4 в task_51
  добавила вопрос (`24` → `25`), и набор был красным уже на HEAD, а примеры
  этого раунда сдвинули ещё два (`03`: `34` → `37`, `04`: `25` → `27`): наборы
  GUI надо гонять после любой правки `examples/`.

* Interpreter round, part 63: **`ВЫВОДПС`/`writeln`** (task_53, 2026-10-03).
  Третий вариадический предикат — и первая проверка того, что таблица имён из
  task_51 действительно данные: имя, английская пара и «хотя бы один аргумент»
  стоят двух строк в `builtins.cpp` плюс слова в `kReservedBuiltins`, а тело —
  `builtinWriteLine` рядом с `builtinWrite` (тот же цикл плюс один `newline()`;
  второй вызов цели не нужен, `ВЫВОД` не отказывает).  Нулевая арность осталась
  за `ПС`, поэтому второй записи для «просто перевод строки» нет.  Дороже всего
  обошлась не программа, а нумерация: §6.3 — новая (место выбрал пользователь:
  сразу после `ПС`), всё с 6.3 по 6.9 сдвинулось на один, а номера жили ещё в
  трёх местах — ссылка в `prologd-diff.typ` («таблица кодов»), комментарии урока
  7 и план `task_54_input_stream.md`.  Все три поправлены в этом же раунде: `section`
  каждой записи `doc/builtins.json` обязан быть заголовком руководства, так что
  расхождение поймал бы `test_reference.py` — но поймал бы уже после правки.
  Урок 7 показывает короткую запись (`?ВЫВОДПС("Сумма: ", 5).`), его счётчик в
  `test_queries.py` — `19` → `20`; в приложении английских имён запись встала
  сама (`ВЫВОДПС — writeln`).  Проверки: 290/290 ctest (три новых случая Catch2
  и два CLI), `--list-keywords` — 110 имён, 21 набор GUI и `protocol_smoke.py`,
  пять PDF, страницы 16–18 и 33 просмотрены.

* Interpreter round, part 64: **ответ оболочки — кусок входного потока**
  (task_54, 2026-10-03).  Источников ввода четыре — файл (`-i`, `ЧТЕНИЕ_ИЗ`),
  стандартный поток, строка `$` исходника и ответ оболочки, — и все, кроме
  последнего, читались через `std::getline`: строка есть то, что между двумя `\n`.
  Ответ же клался в буфер целиком, поэтому именно в окне `ВВОДСТР` возвращал
  `\n`-ы как текст, остаток после `ВВОДСИМВ` начинался с `\n`, а `ВВКОД` читал код
  10 между строками: программа, проверенная на файле, в окне вела себя иначе.
  Теперь кусок принадлежит потоку — `IoContext` держит его остаток и выдаёт по
  строке, спрашивая оболочку только когда остаток кончился.  Остальное —
  следствия: `a\n` это одна строка, а не строка и пустая (следующее чтение идёт к
  пользователю); `""` — одна пустая, как и было; `а\n\nб` даёт ровно то же, что те
  же байты в файле, и это закреплено двумя чтениями — из куска и из временного
  файла.  Второй пункт — BOM: `stripByteOrderMark` в трёх точках входа (первая
  строка базового потока, первого файла `ЧТЕНИЕ_ИЗ` и каждого куска), потому что
  `Notepad` ставит марку в новый файл сам, а код `65279` первым символом строки —
  не то, что ждёт школьник; в середине куска марка остаётся данными.  Правка
  оказалась ровно в одном месте: ни решатель, ни проверки вызовов, ни протокол не
  изменились (`input.text` всегда мог содержать `\n`), а старый тест про обработчик
  ввода этого не ловил — в нём каждая запись была одной строкой.  Документы поехали
  шире кода: ADR-023, `technical.typ` §10, `help.typ` §6.5 (BOM) и §6.8 (кусок
  окна), `gui.typ` §6.1 — абзац описывал окно до task_50 («поле ввода под панелью
  вывода», пункт меню, которого больше нет) и обещал, что «ответ на `ВВОДСТР` может
  быть фразой»; теперь там точный смысл — одна фраза это несколько строк ввода.
  Плюс `gui/README.md` и подсказка настройки «Спрашивать ввод», которая тоже
  называла поле «под выводом».  Проверки: 305/305 ctest (8 случаев `IoContext`,
  7 через встроенные предикаты, один случай в `protocol_session.cmake` — две строки
  в одном ответе дают один `input_request`), GUI-проверка с диалогом-«предателем»
  (вторая строка не должна дойти до окна), пять PDF.

* I/O round, part 65: **неудачный `ЗАПИСЬ_В` оставлял вывод на закрытом потоке**
  (task_57, 2026-10-03).  Нашлось при работе над task_54, когда смотрели на
  `IoContext` целиком: `openOutput` закрывал текущий файл **до** попытки открыть
  новый, а `output_` присваивался только при успехе, поэтому после неудачного
  переключения он оставался на закрытом `file_output_`.  Запись в закрытый
  `std::ofstream` теряется молча (флаг `badbit`, который никто не смотрит), и
  пропадало не только то, что печатала программа, но и **ответы интерпретатора**:
  `ДА`, `НЕТ` и связывания печатаются тем же `IoContext`.  Заметить это было
  трудно именно потому, что диагностики нет: `ЗАПИСЬ_В` честно ложен, а вывод
  просто перестаёт появляться.  Сосед по классу вёл себя правильно: неудачный
  `ЧТЕНИЕ_ИЗ` возвращал чтение к клавиатуре, потому что `fetchLine` смотрит на
  `input_from_file_`, а не на указатель на поток.  Правка — одна строка
  (`output_ = base_output_` сразу после закрытия): неудачное переключение
  возвращает поток туда, где он был бы и без него.  Вариант «сначала открыть,
  потом закрывать прежний» отвергнут — он тихо игнорировал бы просьбу, оставив
  программу писать в прежний файл.  Проверки: воспроизведение на собранном
  `prologd.exe` (до правки пропадали `НЕТ` неудачного переключения и вся
  следующая цель), два новых случая Catch2 — через `ЗАПИСЬ_В`/`ВЫВОД` и на уровне
  `IoContext` — и одна фраза в `help.typ` §6.9 о том, куда возвращается вывод.
  ctest 307/307.

* GUI round, part 66: **пять просьб по окну** (task_58, 2026-10-03) — и один
  сломанный набор в начале.  `test_icons.py` краснела: пользователь перерисовал и
  переименовал значки, а код и `assets.MISSING` за ними не пошли — причём заметила
  она только *лишнее* имя (`view-split-editor` нарисован, но остался в списке
  «ещё не нарисовано»), а двух потерянных картинок не заметила вовсе:
  `view-output-right`/`view-output-bottom` были в том же списке, поэтому «есть файл
  или записано в MISSING» проходило, и «Панель вывода» со «Сменить ориентацию
  сплита» тихо стояли без значков.  Итог: 49 имён, 48 нарисовано, ждёт один
  `view-theme`.  Дальше — четыре вещи про то, как окно говорит с читателем.
  **`Shift+Del`** стало командой (`delete_line` в таблице, пункт «Удалить строку» в
  «Правке», без значка — `edit-del` занят командой «Удалить»): строка берётся
  целиком, курсор встаёт в первый столбец съехавшей строки, выделение сносит все
  затронутые строки, но не ту, на начале которой остановилось, последняя строка файла
  пустеет (документ не может остаться без блока) — и всё это одним `Ctrl+Z`.
  **Подсветка вхождений** выделенного слова: светлая `#e8ecf5` → `#cfe0f7`, тёмная
  `#2d3038` → `#3a4a63`.  Второе число важнее: 15 единиц светлоты от страницы
  `#1e1e1e` — это «тускло», и именно тёмную палитру получает тёмный рабочий стол
  через «системное» оформление.  Раньше её не измеряли: `Palette.readable_pairs`
  проверяет контраст *текста*, а подложку с фоном — нет; теперь в
  `test_appearance.py` есть и такое измерение, чтобы «тусклое» не вернулось молча.
  **Строка «база знаний загружена»** появляется и после клика по маркеру вопроса на
  полях: ранний `return` в `_on_loaded` ждал ответа и уносил строку с собой; теперь
  она печатается по `loaded` (до `return`), и порядок совпадает с `F5`.
  **Меню и панель**: руководство поднялось под «Справку по предикату», в
  «Выполнении» вместо `save_before_run` — два переключателя `run_questions` и
  `print_questions`, которые пишут те же настройки, что показывает диалог
  (`_sync_actions` возвращает значение в галочку), с панели убрано руководство, а
  размер шрифта встал после «Настройки…».  **«О программе»** стало «Графическая
  оболочка Пролог-Д 2.0» с прежним списком авторов АБВГД; колонка `--` выровнена
  пробелами (решение пользователя — без rich text), и тест сверяет, что позиция `--`
  у всех пяти строк одна.  Проверки: три новых случая `test_editor.py`, измерение
  подложки в `test_appearance.py`, четыре новых требования в `test_window.py`; ctest
  307/307, все 21 набор GUI и `protocol_smoke.py`, пять PDF.

  **Доработка после первого взгляда.**  Пользователь нашёл то, чего не нашла моя
  проверка: `Shift+Del` в редакторе не работал, а из пункта меню — работал.  Тесты
  звали метод `delete_lines()`, а не нажимали клавишу, поэтому были зелёными при
  сломанной клавише.  Причина — чужая: `QTextControl` забирает `Shift+Del` как
  платформенную запись «Вырезать» (на Windows это второй, наряду с `Ctrl+X`, способ
  её записать), поэтому `QAction` со своим `Shift+Del` до редактора не доходит, а сам
  ключ приходит в `keyPressEvent` — где без выделения не делал ничего.  Ключ теперь
  обрабатывается в редакторе, а проверка нажимает клавишу.  Дальше три просьбы про
  панель и меню: поле размера шрифта убрано с панели целиком (масштаб — колесо с
  `Ctrl` и три команды, точное значение — строка настроек), «Очистить вывод»
  переехала из панели в «Выполнение» над «Графическим окном», а в «О программе»
  `--` заменено на короткое тире `–`.  Заодно записано правило многоточия в заголовке
  пункта: оно значит «команда сначала что-то спросит» и не ставится тому, что
  действует сразу (даже если открывает своё окно).  Ещё две мелочи оттуда же:
  `Shift+Del` кладёт удалённые строки в буфер обмена (клавиша взяла платформенное
  значение «вырезать» — вырезанное должно вставляться), а значок `edit-clear` у
  «Очистить вывод» удалён вместе с файлом: рисунок читался не как «очистить», и пункт
  остался текстовым (48 имён, 47 нарисовано, ждёт один `view-theme`).

* GUI round, part 67: **таблица ответа** (task_59, 2026-10-03).  Вариант C,
  выбранный пользователем: таблицу получает отдельный запрос — цель в строке
  запроса или клик по маркеру вопроса на полях, — а целому прогону (`F5`) таблицы
  нет и не может быть: ответы всех вопросов программы идут в текст одной лентой
  без разделителей.  Пользователь показал это на своём примере (два факта,
  `?студент(X, Y).`, `?цена(X, Y).` — шесть строк вывода), и это же объяснило его
  вчерашний вопрос про «запуск файлов с многими вопросами»: не дефект, а
  невозможность отделить один ответ от другого по тексту.  Чтобы таблица была и у
  целого прогона, интерпретатор должен присылать решения отдельными данными — поле
  `bindings` в событии `result` (вариант B: правка `protocol.cpp`/`protocol.py`,
  `protocol_session.cmake`, README и тестов); записано в `doc/gui.typ` §10, а не
  сделано сейчас.

  Что в окне: пятая вкладка «Таблица» после «Ввода» (заголовок считает решения —
  `Таблица:3`), переключатель «Выполнение → Формировать таблицу» над двумя
  переключателями вопросов task_58 и та же строка `execution/answer_table` в
  диалоге, по умолчанию выключено.  Ответ собирается из вывода того единственного
  запроса: `_append_output` — единственная воронка, и в неё попадает только `OUTPUT`
  (строка «база знаний загружена» — `NOTE`, ошибки — `ERROR`).  Собирать приходится
  с момента отправки запроса, а не с `loaded`: у маркера программа грузится тихо, и
  вывод загрузки может прийти уже после запроса — спасает правило формы.

  Правило целиком живёт в новом Qt-free модуле `answers.py` (и проверяется
  `test_answers.py` без Qt): связка — строка `Имя=значение`, где имя это переменная
  по правилам лексера (`is_upper_letter` или ведущий `_`, как в `tokens.py`),
  значение — остаток строки дословно; **повтор имени начинает новое решение** — это
  точно, потому что `engine.cpp::runQuery` печатает все переменные запроса в его
  порядке и внутри одного решения имя повториться не может; столбцы — в порядке
  появления.  Оттуда же, из `runQuery`, следует форма ответа цели без переменных:
  `ДА` один раз либо `НЕТ`, и слово со связками внутри одного запроса не
  смешивается — поэтому `ДА`/`НЕТ` занимает в таблице одну ячейку с заголовком
  «Ответ», а не отдельный вид пустой вкладки.  Всё, что не похоже на связку
  (напечатанное программой внутри ответа), — `ignored`: в таблицу не попадает, в
  «Выводе» остаётся.

  Мелочи, без которых было бы хуже: `Ctrl+C` над таблицей копирует выделенные
  ячейки (столбцы через табуляцию, строки через перевод строки) — `_copy` копирует
  «оттуда, куда смотрит пользователь» и без случая для таблицы увёл бы команду в
  редактор; новый запуск и `Ctrl+L` таблицу очищают (она вид последнего ответа, а
  не история); диагностика оставляет панель на «Проблемах», а таблица ждёт на своей
  вкладке.  Таблица берёт размер шрифта вывода, сигнал `zoomChanged` и колесо с
  `Ctrl` — то есть `_apply_output_font` теперь про пять панелей, а не про четыре.

  Проверки: новый `test_answers.py` (12 случаев: связки, повтор имени, `ДА`/`НЕТ`,
  напечатанное программой `ДА` рядом со связками, мусорные строки, пустое значение,
  CRLF, имена с `_`), девять случаев в `test_window.py` (переключатель в меню и в
  настройках; таблица у маркера и у строки запроса; две строки-решения на примере
  пользователя; `ДА`/`НЕТ` одной ячейкой; выключенный переключатель ничего не
  делает; диагностика держит «Проблемы»; запуск и `Ctrl+L` чистят; размер шрифта;
  `Ctrl+C`), а `test_the_panel_has_four_tabs_with_counts` стала пятиместной.
  Ловушка, стоившая одного красного прогона: `wait_for_result` ждёт слово в строке
  состояния, а она держит слово **прошлого** ответа — для второго запроса в одном
  тесте нужен `not window._busy`.

* GUI round, part 68: **вопрос после загрузки** (task_60, 2026-10-03).  Пользователь
  спросил, что происходит при запуске строки `?0 < 5 < 4.` — окно показывает две
  ошибки, «от файла» и «от query».  Разобрано на собранном интерпретаторе: клик по
  маркеру делает **два** запроса — тихую загрузку файла (`questions=false`) и сам
  вопрос отдельным запросом `query`.  `questions=false` значит «не *выполнять*
  собственные `?`-строки программы», но файл всё равно разбирается целиком, поэтому
  о цепочке сравнений сообщает загрузка, назвав файл (у отдельного запроса имя
  `<query>` — так протокол различает «ошибка в файле, строка N» и «ошибка в
  присланной строке», task_36).  Строка запроса загрузки не делает вовсе — там одна
  ошибка; если же перед ней был `F5`, ошибка файла остаётся в «Выводе» рядом с новой
  (панели чистит только `run_program`).

  По дороге нашлось хуже: файл, который не разобрался, не загружает базу **вовсе**
  (загрузчик разбирает текст целиком, прежде чем что-то добавить), а вопрос всё равно
  отправлялся — и получал ответ «НЕТ» плюс предупреждение «`<query>:1:2: не найдено:
  факт/1`», то есть неверный ответ с честным лицом и претензией к запросу вместо
  файла.

  Правка (решения пользователя): маркер спрашивает **после успешной загрузки**
  (`_pending_query`, отправка из `_on_loaded`; ошибка загрузки выбрасывает вопрос со
  строкой в «Системе»), а строка запроса не перечитывает программу — база одна, и
  цель спрашивает ту, что загружена, — но грузит текущий текст, если спрашивать не у
  кого (`_loaded` false).  Двойная ошибка снята по построению, «НЕТ» на пустую базу
  больше не появляется, ошибка найденного в комментарии вопроса по-прежнему приходит
  один раз и называется `<query>`.  Документы: `gui.typ` §4.2 и §6, README (маркеры и
  строка запроса); проверки — пять новых случаев `test_window.py`.

* Documentation round, part 69: **пять документов — короче, ровнее и с верным
  числом** (2026-10-03).  Просьбы пользователя: сократить `gui.typ`, проверить
  согласованность `technical.typ` (сокращать не надо) и опустить название ближе к
  центру страницы.

  `gui.typ`: 1 103 строки → 956.  У каждого раздела короткий зачин и дальше пункты;
  твёрдые факты остались все (48 ссылок на значки и 47 нарисованных, клавиши, ключи
  настроек, измеренные числа, ссылки на разделы).  Заодно проверка на слова со
  смешанными алфавитами нашла в §6.1 «dве строки» (латинская `d`) — таких слов в
  файле больше нет.

  Из `prologd-diff.typ` убраны две главы («`->` — не оператор» и «`is/2` — подсказка
  вместо оператора»): документ говорит только об отличиях от первоначального
  Пролога-Д, а в нём и в новой реализации этих операторов нет.  Их содержание
  переехало в `help.typ`, где сравнивает с ISO-Прологом, SWI-Prolog и GNU Prolog
  (§3.3 — `is/2` и две подсказки вместо оператора, §4.6 — «если-то» через `ПЕРВОЕ`
  рядом с `(Условие -> Тогда ; Иначе)`), и про старую реализацию там не говорится.

  `technical.typ` не сокращался, но приведён в порядок.  §1 «Постановка задачи»
  снят, разделы 2--10 стали 1--9, а два последних остались с прежними номерами —
  теперь это 10 «Тестирование» и 11 «Ограничения», разрыва в нумерации нет;
  «раздел 5.6» и «см. 5.6» ведут куда надо.  **Исправлено число, оказавшееся
  артефактом:** «полное сканирование 100 000 предложений ≈ 20 мс» вышло вычитанием
  двух прогонов, которые оба просматривают весь список (вопрос без переменных под
  `ТИХО` продолжает искать решения после первого — `Engine::runQuery`), поэтому
  разница была шумом.  Перемерено на этой машине: загрузка 100 000 фактов 0.25 с, а
  скан — 1 000 предложений 0.3 мс, 10 000 — 3.7 мс, 100 000 — 54 мс, то есть
  ≈ 0.5 мкс на неудачную попытку; с отсечением сразу после вызова это видно прямо
  (`г(1)` без `!` стоит столько же, сколько `г(0)`, с `!` — ноль).  Поправлены
  `technical.typ` §5.7 и §11, ADR-017 и отчёт task_42.

  В том же раунде: `lessons.typ` — короткий `= 1. Как устроен урок` с командами
  запуска вместо двух вводных разделов, нумерация сдвинута; и название во всех пяти
  документах опущено — перед блоком заголовка стоит `#v(6cm)`, то есть примерно 40 %
  высоты страницы вместо самой кромки.

  Проверки: все пять документов собираются (`typst=0`), первые страницы посмотрены.

* Documentation round, part 70: **пример программы в окне и имена переменных в
  уроках** (2026-10-03).  Просьбы пользователя: поменять приветственную программу
  на `% пример программы` с `студент('Вова', 'Корчагин')` и запросом
  `?студент(Имя, Фамилия).`, дать переменным уроков осмысленные имена там, где это
  помогает читателю, и закрыть шероховатости, найденные работой с окном.

  Приветственная программа: атомы в кавычках (заглавная буква без кавычек —
  переменная, урок 1), переменные — `Имя` и `Фамилия`.  Программа проверена
  запуском: `Имя=Вова`, `Фамилия=Корчагин`, `Имя=Данил`, `Фамилия=Ахмеров`, без
  диагностики, и она уже в канонической форме (`prologd --format` ничего не
  меняет, то есть `Ctrl+I` не переписывает первый текст, который видит
  пользователь).  Тесты окна больше не ищут префикс `% PrologD`, а сравнивают
  текст вкладки с самим `WELCOME`; тот же пример (факты + два вопроса подряд)
  стоит теперь и в `gui.typ` §6.5 — на нём видно, почему таблица строится только
  для отдельного запроса.

  Уроки: имена переменных заменены на слова там, где у переменной есть роль —
  `дед(Дед, Внук)`, `сумма(Предел, Сумма)`, `фак(Число, Часть, Факториал)`,
  `нод(Первое, Второе, Нод)`, `фиб(Число, Фибоначчи)`, `член(Элемент, [...])`,
  `НАЙТИВСЕ(Имя, студент(Имя, Фамилия), Список)` и так по всем урокам.  Прописные
  «Х», «У», «_» и координаты `Х1`, `У1` оставлены там, где это и есть «любое
  значение»; буквы
  Д, К, М, Н в задаче о бегунах — потому что проза называет их именами, а
  Cyrillic/Latin-пара `Х` и `X` в приложении — сам предмет пункта 2 раздела 4.
  Каждая правка тянула за собой `%!`-строки (в ответе печатается *имя*
  переменной), прозу, которая называла буквы, и текст упражнений с ответами.

  По дороге: `examples/lib/library.pld` и `import_demo.pld` получили те же имена
  (`удвоить(Число, Дважды)`), за ними — регулярка теста `cli_include` (`Дважды=42`)
  и приёмка `test_queries.py` (`?сумма(5, Сумма).`), а цитаты строк урока — в
  `examples/lessons/README.md`, `doc/gui.typ` §4.2, `src/gui/README.md` и
  комментарии `editor.py`.  Две мелкие поправки формулировок: третье место
  `УМНОЖЕНИЕ/4` названо слагаемым, а не остатком (урок 3), и `встав/3` перестало
  быть «Встав/3» (урок 5).  `ded(Д, В) → дед(Дед, Внук)` в приложении: трасса
  печатает `_1`/`_2` решателя, поэтому её `%!`-строки не изменились.

  Отдельно — ремарка в уроке 3 (просьба пользователя): `РАВНО` и его знак `=` не
  присваивание, как в императивных языках, а унификация (урок 2) — для свободной
  переменной подбор значения, для связанной проверка.  Пример в ремарке сверен
  запуском: `?РАВНО(14, #2 + 3 * 4#).` отвечает ДА, `?РАВНО(15, #2 + 3 * 4#).` —
  НЕТ.

  Следом — шероховатости, найденные пользователем при работе с окном (он же и
  предложил их закрыть).  **Урок 10:** щелчок по маркеру загружает файл заново и
  выполняет ровно один вопрос, поэтому вопросы, которым нужны действия
  предыдущих, отвечают не на ту базу.  Проверено: `?дважды(4, Итог)` даёт НЕТ и
  предупреждение «не найдено: дважды/2» (правило создаёт строка `?ДОБ(...)`), а
  `?прим(Остался)` — тихо другое (`Остался=1`, `Остался=2` вместо `Остался=3`,
  `Остался=2`).  Поведение менять не стали (это решение task_36/59: ответ должен
  быть только у спрошенного вопроса), объяснение добавлено в §4 урока и в
  указатель в шапке.  **Урок 11:** каталог поиска модулей теперь описан для окна
  первым делом — «Настройки → Выполнение → Дополнительные каталоги ИМПОРТ»
  (`execution/import_paths`; каждый запуск поднимает сессию с `-I`, поэтому
  добавленный каталог действует со следующего «Запустить»), ключ `-I` — вторым.
  **Урок 7:** так же объяснено, что в окне ответы набираются в консоли под
  строкой цели или в поле-очереди, а файл `lesson_07.input.txt` нужен только
  командной строке.  Те же пояснения — в `examples/lessons/README.md` (разделы
  «Как читать урок» и «Вопросы на полях») и в `doc/lessons.typ` §1.

  Разбор вопроса пользователя про директиву: у `:- ДОБ(...)` маркера нет вовсе
  (правило принимает только `?`-строки), а щелчок по соседнему вопросу её не
  выполняет — тихая загрузка идёт без query runner, то есть добавляет в базу
  только предложения.  Проверено: `?дед(аня, Y).` по щелчку отвечает НЕТ и
  «не найдено: дед/2», а по F5 — `Y=витя`.  В `help.typ` §11 про это не писали
  (его пример верен для консоли и для F5); `:- ИМПОРТ` — исключение, его разбирает
  сам загрузчик, поэтому маркеры урока 11 работают.

  Проверки: ctest 307/307; все 13 уроков прогнаны и сверены с их `%!` (в
  приложении — предупреждение «не найдено: любит/2», как и обещает его раздел 4),
  каждый файл побайтно равен выводу `prologd --format`; счёт вопросов 278 в 33
  программах; 22 набора `src/gui/tests/test_*.py` и `protocol_smoke.py`, которые
  надо запускать `.venv\Scripts\python.exe` (системный `python` без PySide6 роняет
  семь из них на `No module named 'PySide6'`); `docs` (пять документов, `typst=0`).

* Planning round, part 71: **task_61 — переносная сборка для Windows** (2026-10-03).
  Просьба пользователя: одна папка для чистой машины — окно, интерпретатор,
  документы, примеры; и вопрос, каким инструментом.  Задача написана
  (`ai/task_61_portable_windows_build.md`, M17, строка в `plan.md` §5 и на доске),
  факты проверены на этой машине: `prologd.exe` — 944 КиБ и импортирует
  `VCRUNTIME140.dll`/`MSVCP140.dll` (UCRT входит в Windows 10+, а эти две DLL — нет),
  UTF-8 манифест вшит в образ (`/MANIFESTINPUT:src/utf8.manifest`), путь дерева
  сборки в exe не попал; в окне три пути считаются от дерева исходников
  (`default_executable`, `assets.DEFAULT_DIRECTORY`, `_open_document`); PyInstaller
  6.22.3 поддерживает Python 3.14 и PySide6, но ни он, ни Nuitka, ни cx_Freeze не
  установлены.  Решения пользователя: PyInstaller `--onedir`; DLL Visual C++ кладём
  рядом; `_old` не кладём, `.typ` кладём; `gui.ini` в переносной сборке рядом с exe
  (в других — AppData, как сейчас); `examples/lib` прописать сразу; папка
  `prologd-2.0.0-win64` и zip.  Инсталлятор — следующая задача.

* Packaging round, part 72: **task_61 — первая замороженная сборка** (2026-10-03).
  §4 сделан: `prologd_gui/paths.py` отвечает на два вопроса (папка рядом с exe в
  сборке, корень репозитория в исходниках; `sys._MEIPASS` для значков), на него
  переведены интерпретатор, значки, документы, настройки, строка ИМПОРТ и — четвёртым,
  чего в задаче не было, — `doc/builtins.json` для `F1`; проверки: `test_paths.py`
  (семь случаев с подменёнными `sys.frozen`/`sys.executable`/`sys._MEIPASS`) и случай в
  `test_window.py`; все 23 набора GUI зелёные, ctest 307/307.

  §2–§3 сделаны на первом проходе: PyInstaller 6.22.3 поставлен в `.venv`
  (`src/gui/requirements-build.txt` — отдельно от студенческого `requirements.txt`),
  сборка `--onedir --windowed` занимает 27 с и даёт 112.9 МиБ в 252 файлах
  (`prologd-gui.exe` 2.3 МиБ, в `_internal/assets` все 47 значков).  Папка
  `dist/prologd-2.0.0-win64` — 297 файлов, 116.3 МиБ: окно, `prologd.exe` и три DLL
  Visual C++ рядом, пять PDF с их `.typ` и `builtins.json`, `examples` без
  `lessons/_old`, памятка `ЧИТАЙ_МЕНЯ.txt` (из `tools/portable-readme.txt`).

  Проверено: `tools/check_dependencies.py` разбирает таблицу импорта каждого .exe и
  .dll поставки и отвечает «every non-system import is a file of the package» (список
  системных DLL пополнен тем, что нашлось на деле: `icuuc.dll` — ICU из Windows 10,
  `d2d1`/`dwrite`/`d3d12`/`uiautomationcore` — бэкенды Qt); окно из этой папки
  запускается, находит интерпретатор рядом и создаёт `gui.ini` рядом с собой,
  прописывая в `execution/import_paths` свой `examples/lib`; `prologd.exe --version`
  = `2.0.0`, `--list-keywords` = 122 строки (110 имён), вывод урока 1 совпадает со
  строками `%!`.  При проверке нашлось и исправлено: в `--windowed` сборке некуда
  печатать, поэтому «нет prologd.exe рядом» теперь говорит окном, а не строкой в
  stderr; из дерева убран мусорный `doc/style.pdf` (остаток цели, которая когда-то
  собирала `style.typ` как документ) — он заехал в первую сборку.

* Window round, part 73: **таблица ответа включена по умолчанию** (2026-10-03).  Просьба
  пользователя: «Формировать таблицу» должна быть включена с самого начала, а не ждать,
  пока её найдут в «Выполнении».  Изменено там, где умолчание записано: строка
  `Setting(ANSWER_TABLE, …)` и свойство `answer_table` в `settings.py` (оба читали
  `False`), документация (`src/gui/README.md` — и раздел «Таблица ответа», и абзац про
  меню; `doc/gui.typ` §6.5 получил абзац про умолчание и про переход панели на
  вкладку) и проверка `test_the_answer_table_switch_is_in_the_menu_and_in_the_settings`,
  которая держала старое умолчание: теперь она начинается с включённого переключателя
  и проверяет выключение.  Поведение таблицы не менялось: она строится только для
  отдельного запроса (строка запроса или маркер), текст ответа так же идёт в «Вывод»,
  диагностика оставляет панель на «Проблемах», а пустой ответ не переключает вкладку.

  В тот же день пользователь проверил переносную сборку на **чистой Windows 11 в
  Windows Sandbox, 24H2 26100.9457**: «запустилась и работает».  Это §7.5 задачи
  task_61 — единственная проверка, которой не может быть на машине разработчика
  (здесь DLL Visual C++ лежат в `System32`, поэтому забытую DLL тут не увидеть).

* Portable round, part 74: **переносная сборка и перенос папки** (2026-10-03).  Вопрос
  пользователя: `examples/lib` записывался в `execution/import_paths` на первом
  запуске, а сборку будут копировать (флешка → компьютер → обратно), и абсолютный
  путь от первого запуска станет чужим.  Решение: ничего не записывать.  Правило
  переехало в `paths.import_directories(configured)` — замороженная сборка добавляет
  свой `examples/lib` **при каждом запуске и последним**, каталоги пользователя идут
  раньше и выигрывают при одинаковом имени файла; в дереве исходников поведение не
  изменилось (там по-прежнему поиск только по тому, что задано).  `seed_import_paths`
  удалён, `_import_directories` в окне теперь одна строка, проверки перенесены в
  `test_paths.py` («находит ли сборка свой курс», «дерево ищет только то, что ему
  сказали»).  Там же уточнилось, что `--icons` по умолчанию — это `src/gui/assets` в
  дереве и своя копия внутри папки сборки — в `src/gui/README.md` и в памятке
  `tools/portable-readme.txt` («папку можно переносить куда угодно»).

* Portable round, part 75: **Windows 10 подтверждена, и почему первый запуск
  медленнее** (2026-10-03).  Пользователь проверил сборку на **Windows 10 22H2,
  сборка 19045.6456** — «запустилась и работала»; вместе с Windows 11 из Sandbox это
  обе системы, которыми ограничивает §9 задачи (19045 ≥ 1903, значит манифест UTF-8
  понимают).  Там же запрос: почему первый запуск занимает секунд пять, а следующие
  быстрее.  Замерено здесь: в уже использованной папке окно готово через 0.16–0.19 с,
  в свежескопированной первый запуск — 0.43 с, дальше 0.17 с.  Причина не наша:
  первый запуск новой копии читает все 296 файлов (110 МиБ) с диска, и антивирус
  проверяет каждый `.exe`/`.dll`/`.pyd` по разу; дальше всё берётся из кэша ОС, а
  проверка помнится.  Своё при первом запуске измерено и ничтожно (`prologd
  --list-keywords` — 0.00–0.01 с, запись `gui.ini` — десяток КБ), а `--onedir` в
  отличие от `--onefile` ничего не распаковывает.  Записана и возможность сократить
  чтение: вычетом `--exclude-module` уходят QML/Quick, `Qt6Pdf`, `Qt6VirtualKeyboard`
  и `Qt6Network` с TLS — около 27 МиБ из 110; `opengl32sw.dll` (19.7 МиБ) остаётся
  сознательно, это запасной программный OpenGL для машины без драйвера.  Вычет будет
  делаться вместе со скриптом §6 и проверяться `tools/check_dependencies.py`.

* Portable round, part 76: **уроки пользователя, `$` как строки ввода, `Shift+Enter`
  и отмена подстановки `examples/lib`** (2026-10-03).  Три запроса за раз: поправленные
  уроки, «не подавать `examples/lib`» и «запретить `Shift+Enter` в редакторе».

  *Уроки.*  `ctest` поймал в них две вещи.  В `lesson_01.pld` строка про
  взаимозаменяемость строки и атома начиналась с `$` — а `$` в исходном файле это
  **не комментарий**, а строка заранее подготовленных данных для ввода:
  `ModuleLoader::extractInputLines` вырезает её из текста ещё до лексера, поэтому при
  запуске она исчезает молча (`exit=0`, диагностики нет), а если бы урок что-нибудь
  читал, эти слова ушли бы в программу как ответы.  Заметно стало только потому, что
  `--format` (и `Ctrl+I` в окне) лексет текст целиком и такой файл не форматирует:
  «недопустимый символ».  Заменено на `%`; заодно убраны хвостовые пробелы в
  комментариях (`lesson_01` — 3 строки, `lesson_11` — 3), форматтер их подрезает, и
  «программа уже в стандартном виде» падало.  Ещё две опечатки в `lesson_11` —
  «Выполенение» и «ИМПОРАТ» — исправлены.  После правки `ctest` 307/307.

  *`examples/lib`.*  Решение от 2026-10-03 (часть 74) отменено самим пользователем:
  окно не подставляет в список поиска ИМПОРТ **ничего своего**.  Урок 11 теперь сам
  говорит, что каталог библиотеки надо добавить руками («Правка → Настройки… →
  Выполнение → Дополнительные каталоги ИМПОРТ»), и так **прозрачней для ученика** — он
  видит строку, которую заполнил, и путь, который выбрал.  `paths.import_directories`
  остался, но только для чистки: пустые строки и повторы.  Обновлены
  `test_paths.py` (было «сборка ищет свой курс», стало «сборка ищет только то, что
  добавил ученик, и ничего своего»), `src/gui/README.md`, `tools/portable-readme.txt`
  (там теперь шаг «укажите `examples\lib`») и §4/§7.1/§8 задачи 61.

  *`Shift+Enter`.*  Замерено, чем именно он ломает нумерацию: Qt вставляет им
  **разделитель строк** `U+2028` — виджет рисует новую строку, а `blockCount()` её не
  считает (`\n` — 2 блока, `\v`/`\f`/NEL/`U+2028` — 1, `U+2029` — 2), поэтому номера и
  маркеры вопросов на полях уезжают.  Интерпретатор `U+2028`, `U+2029` и NEL вообще
  отвергает («недопустимый символ»), а `\v`/`\f` считает пробелами.  Теперь `Enter` и
  `Shift+Enter` — одна ветка в `CodeEditor.keyPressEvent` (обычный перевод строки с
  автоотступом; `Ctrl`/`Alt`+`Enter` по-прежнему уходят в Qt), а «вставка» не приносит
  разделитель: `CodeEditor.insertFromMimeData` и `documents.read_text` складывают
  `U+2028`/`U+2029` в `\n` (`tokens.plain_newlines`, с записанным замером).  Случаи в
  `test_editor.py` («`Shift+Enter` — строка, которую полянка считает», «вставка не
  приносит разделитель») и в `test_documents.py` (в том числе порядок: складывание
  раньше, чем определяется CRLF).  Заодно убран устаревший «(раздел 9.3)» из
  `doc/gui.typ` §9.2 — раздела 9.3 больше нет.




