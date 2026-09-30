# Status tracker

Last updated: after the Windows/VS 2026 verification and the GUI protocol
session.

## Overall

* Phase: feature-complete core, verified on Windows; the PySide6 front-end has
  started (protocol + skeleton).
* Build: the `windows-msvc` preset (Visual Studio 18 2026, MSVC 19.51) build is
  green locally; the Linux presets, including `-Werror`, build cleanly.
* Tests: 199/199 pass in about four seconds: 187 Catch2 cases plus 12 command-line
  and integration tests (seven option tests, two `--list-keywords` tests, the
  import-search report, the JSON protocol session and the engine-limit cases).
* CLI: `build/windows-msvc/src/cli/Release/prologd` runs files (positional, `-s`
  or `--source`), stdin, the REPL and the `--protocol json` session for
  front-ends.
* GUI: `src/gui` (PySide6) drives the executable through the JSON protocol; the
  window, the protocol and the stepping are covered by fifteen offscreen scripts
  (`src/gui/tests/`), which need no display.
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
  `УМНОЖЕНИЕ/3,4`, `abs`, `sqrt`, `sin`, `cos`, `tan`, `exp`, `is_whole`,
  `number`, `СЛУЧ`, `ЦЕЛВЕЩ`, `СТРЦЕЛ`, `СТРВЕЩ`, `СТРСПИС`.
* Strings (code-point based): `БУКВА`, `ЦИФРА`, `СЦЕП`, `КОПИЯ`, `ДЛИНА` (each
  with an English name too — appendix 17 of the manual).
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
* PySide6 front-end (`src/gui`): the `prologd` interpreter in its own process over
  the line-delimited JSON protocol (version 2 carries the reserved names), a code
  editor with highlighting, completion, line numbers, zoom and settings, tabs and
  files with save prompts and encodings, an input field with a queue of prepared
  answers, a split editor over one shared document set, and — with task_26 — one
  action table feeding the menu bar, the toolbar and the context menu.
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
| task_17_docs_typst | done | four Russian documents + `doc/README.md`; the PDFs are written into `doc/` (git-ignored) |
| task_18_examples_acceptance | done | lessons ported; golden tests |
| task_19_windows_portability | done | verified locally on VS 2026: build + 108/108 tests (ADR-013); the CI image still has to be confirmed |
| task_20_gui_future | superseded | the Qt C++ plan became PySide6 over a JSON protocol (ADR-014) |
| task_21_gui_pyside | in progress | protocol, `IoContext` input seam, `externalStop`, `src/gui` skeleton |
| task_22_gui_editor | done | tokenizer, palette, highlighter, line numbers, Ctrl+K/U, zoom and the settings store are in and tested; find/replace and duplicate line come with the task_26 menus, saving a file with task_25 |
| task_23_gui_keyword_source | done | `--list-keywords` + `keywords` in `ready` (protocol 2); one source for the built-in list |
| task_24_gui_completion | done | popup over the reserved names *and* the document's own names, with arities; no completion in a comment, string or `#…#`; `Ctrl+Space` |
| task_25_gui_files_tabs | done | tabs, files, save prompts, encodings, input queue, drop anywhere and the split editor (two panes, one text per document) |
| task_26_gui_toolbar | done | one action table (48 commands, 12 disabled with a reason) feeding the menu bar, the toolbar and the context menu; icon audit in `src/gui/README.md` (48 names referenced, 42 drawn, 6 left: the «Вид» switches) |
| task_27_gui_panels | done | movable panel (`F4`, `Ctrl+F4`), output pane (colour by kind, visible half-lines, bounded history, auto-scroll, save to a file), input console with the queue switch, status-bar details and the two-state run/stop |
| task_28_gui_run_step | done | `EngineOptions::stepHook` + `StepInfo`, protocol 3 (`step`/`trace` events, `step` request, positions on `error`), the step strip with the call stack, the trace line in the editor, `F10`/`Shift+F10`/`F5`, error and trace lines from structured positions |
| task_29_gui_settings | not started | settings dialog and persistence |
| task_30_gui_formatter | not started | soft/hard formatting in prlib + protocol |
| task_31_gui_shortcuts | not started | layout-independent `Ctrl`+ key combinations |
| task_32_import_search_report | done | `ИМПОРТ` failure names the directories tried, with reasons |
| task_33_gui_search_replace | done | `search.py` (plain-text, Qt-free) + the find bar: question from the selection or the word at the caret, `F3`/`Shift+F3` with the wrap reported, three switches, «Заменить всё» as one undo step, the matches lit in every view; `test_search.py` has 16 checks |
| task_34_builtin_branches | done | every built-in branch-tested in Catch2 (186 cases); the sweep found and fixed five defects: two in the float built-ins (`nan` instead of a failure), the integer/real comparison, the cyclic term that ended the process, the ignored read prompt, the unchecked graphics arguments and the code points that were written as invalid UTF-8 |
| task_35_lessons_rework | done | the course in `examples/lessons` is rewritten for the current dialect, one commit per lesson, from the plan in `ai/task_35_lessons_rework.md`; `test_lessons.cpp` runs every lesson (12 + the debug appendix) and compares its whole output with the `%!` lines the lesson itself carries, so a lesson cannot drift again; the old files are in `lessons/_old/`; the index is `examples/lessons/README.md` and the fifth Typst document `doc/lessons.typ` (the `docs` target builds it); writing the expectations found and fixed mistakes in the source material (a non-terminating `нод/3`, descending sorts, a hanging `?длина(Х, 2)`, a failed read that leaves the rest of its line) and taught the check two tricks: input files for lesson 7 and include paths for lesson 11 |
| task_36_gui_query_markers | not started | run one question from the editor margin: a marker next to `?Goal.` and `% ?Goal.`, the `%?` colour, and a `questions: false` load so the clicked query answers *alone*; the task file carries the rule for what counts as a statement (a lesson's commented query often has prose after the goal) and the finding that no lesson file has to change |
| task_37_gui_builtin_reference | not started | `doc/builtins.json` as the one machine-readable source for the built-in reference, a checker keeping it in step with `--list-keywords` and the sections of `help.typ`, a summary line under the completion popup and `Shift+F1` on the word under the caret (the English-alias work of task_39 would land in the same file) |
| task_38_engine_limits | done | recursion depth and long runs: the crash is gone (the chain and deep terms are released iteratively — the trigger was a *surviving* deep reference, a choice point whose base clause does not cut, or the solver's final environment), `maxDepth` turns runaway recursion into a diagnostic, the variable growth is documented instead of "fixed", and `tools/bench_engine.py` made the numbers reproducible |
| task_39_english_aliases | done | every built-in has an English spelling in lower case (one `kEnglishNames` table in `builtins.cpp`, 47 pairs, is the only place a pair is written; `test_aliases.cpp` walks it and fails on a Russian name without a row); the manual gained appendix 17 with the whole table, `prologd-diff.typ` §15 and `conventions.md` the rule; doing it showed that `int`/`float` were *checks*, not conversions (`integer`/`float` are the ISO type tests, `is_whole`/`number` the old ones, and the planned `to_int`/`to_float` were dropped) and `ДЛИНА` became `strlen`; 108 reserved names, one list for CLI, protocol and GUI |
| task_40_diagnostics | not started | severity (warnings that never change an exit code), positions that point at the opening bracket, a stated missing final dot, a warning for a variable written where a constant was meant, singleton variables, and call-site hints (unknown name with a suggestion, known name with the wrong arity) |
| task_41_semicolon_disjunction | approved | `;` as a real backtrackable disjunction (ISO precedence with `,`), the `;` sentence terminator retired with a diagnostic, `ИЛИ/2` left as the committed form and cross-referenced; the user gave the go-ahead on 2026-09-30, work not started |
| task_42_engine_hot_path | not started | the constant tax: no string per built-in call, no `"name/arity"` key per predicate call, clause indexing and atom interning only where the benchmark justifies them |
| task_43_language_surface | not started | `ВЫП/2..N` (`call/N`), a warning when two imported files define the same predicate, and the removal of the seven library clauses that every built-in already shadows (`?СКОЛЬКО(НЕ, А)` answers 2 today) |

## Test suite

199 tests, about four seconds: 187 Catch2 cases plus 12 command-line and
integration tests (seven option tests, two `--list-keywords` tests, the
import-search report, the JSON protocol session and the engine-limit cases). Groups:
BigInt, lexer, keywords, parser, unification, engine, every built-in group,
`НАЙТИВСЁ`, module loader (including the import search report), the I/O seams,
typical tasks (factorial, Fibonacci, GCD, insertion sort, 4-queens, knapsack),
ported lesson/example programs (golden output) and the CLI (`-s`, `--source`,
`--source=`, positional, `-I`, `--help`, `--version`, `--list-keywords`,
`--protocol json`).  Every built-in is covered branch by branch — see
`ai/task_34_builtin_branches.md`, which also lists what the sweep found.

The front-end has its own headless checks, run by hand (they need PySide6 or a
build, so CI does not run them yet): `src/gui/tests/protocol_smoke.py`,
`test_keywords.py` (the keyword table from both sides), `test_tokens.py` (the
highlighting rules, including a sweep over the example programs),
`test_highlighter.py` (the palette reaching the document),
`test_appearance.py` (forced light palette and contrast of every syntax colour),
`test_editor.py` (comment/uncomment and indent as single undo steps, the Tab and
Enter keys, zoom bounds, line-number width, the error marker),
`test_completion.py` (what is offered and in which order, and the popup driven
by real key events),
`test_documents.py` (line endings, byte-order marks, cp1251 round trips, the
untitled counter, the recent list),
`test_settings.py` (defaults, persistence, clamping, keys a later version adds),
`test_icons.py` (the icon audit: every referenced name has a file or is in the
documented `MISSING` set, a missing name has no file, `--icons DIR` works),
`test_session.py`
(request queueing and the clean-slate restart) and `test_window.py` (opening a
file does not run it; the documented keys are bound; zoom reaches the settings
file; menus, toolbar and context menu come from the action table; the recent
menu; the font-size control; save-before-run; the split panes), all invoked as
plain scripts.

## Known gaps / next steps

1. The GitHub Actions Windows job still has to run on an image that provides
   VS 2026; locally the MSVC 2026 build and the whole suite are green.
2. `--dump-ast` and `--dump-clauses` (task_16) are dropped: the parser produces a
   `ParsedProgram`, not a tree worth printing, and no workflow asked for them.
3. Catch2 test discovery decodes the test executable's stdout with the console
   code page, so a non-ASCII test *name* lands in `prlib_tests-*_tests.cmake`
   mangled and ctest reports "No test cases matched" for it.  Test names are
   ASCII for that reason (the *goals* are Russian as always), which is written
   down next to `catch_discover_tests` in `src/tests/CMakeLists.txt`; the
   underlying fix (a project-local discovery step writing `--list-tests
   --reporter json` to a *file*, which `execute_process(... OUTPUT_FILE ...)`
   leaves byte-exact) is still a possible improvement.
4. Optional: first-argument clause indexing if a real program needs more speed.
5. Optional: `is/2` and infix comparison operators next to `#expr#`.
6. GUI: task_21 is the skeleton only (protocol, `src/gui` window with an editor,
   a query line and an output pane); task_22 adds the code editor itself and
   task_23 the keyword source.  The rest is task_24–task_31, see the board above.
   The settings file is written to `%LOCALAPPDATA%\PrologD\gui\gui.ini`; the
   dialog that edits it is task_29, and `--settings FILE` overrides the path.
   Open for the next session: the rest of task_27 (the output pane's own
   behaviour — colour by kind, truncation, auto-scroll, save to a file — the input
   console and the status-bar details), the graphics window (no task file yet),
   and the output panel's own font size (task_29).

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
     behind `ДОБ`/`НАЙТИВСЁ` refuses a cyclic term with a diagnostic instead of
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
  first solution of its first goal, `ТИХО` being a per-query flag, `НАЙТИВСЁ`
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
  a commented-out query is not a test.
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
  can be read as an integer or as any number (`is_whole(4.0)`, `number(4)`),
  while ISO's `integer/1`/`float/1` are the type tests — so they are
  `is_whole`/`number` now and the planned `to_int`/`to_float` were dropped: an
  actual conversion is `ЦЕЛВЕЩ`/`num_to_float`, and inventing a second one
  without a caller would have been a name without a use.  `ДЛИНА` is `strlen`
  (not `length`, which ISO keeps for lists).  The manual gained appendix 17 with
  the whole table, `prologd-diff.typ` §15 and `conventions.md` gained the rule;
  the reserved-name list grew from 57 to 108 and `test_keywords.py` confirms
  that the CLI, the protocol and the GUI see the same names.  187 Catch2 cases,
  3 131 assertions, 199 ctest tests, all green.
