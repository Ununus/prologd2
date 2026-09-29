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
| task_26_gui_toolbar | done | one action table (48 commands, 12 disabled with a reason) feeding the menu bar, the toolbar and the context menu; icon audit in `src/gui/README.md` (41 names referenced, 27 drawn) |
| task_27_gui_panels | not started | output and input panes, output bottom/right |
| task_28_gui_run_step | not started | run, step (new engine seam + protocol v2), stop, error line |
| task_29_gui_settings | not started | settings dialog and persistence |
| task_30_gui_formatter | not started | soft/hard formatting in prlib + protocol |
| task_31_gui_shortcuts | not started | layout-independent `Ctrl`+ key combinations |
| task_32_import_search_report | done | `ИМПОРТ` failure names the directories tried, with reasons |
| task_33_gui_search_replace | not started | find/replace bar for the five «Поиск» entries, which are already in the menus (disabled) |

## Test suite

119 tests, about a second: 108 Catch2 cases plus 11 command-line and
integration tests (seven option tests, two `--list-keywords` tests, the
import-search report and the JSON protocol session). Groups:
BigInt, lexer, keywords, parser, unification, engine, every built-in group, `НАЙТИВСЁ`,
module loader (including the import search report), the I/O seams, typical tasks
(factorial, Fibonacci, GCD, insertion sort, 4-queens, knapsack), ported
lesson/example programs (golden output) and the CLI (`-s`, `--source`,
`--source=`, positional, `-I`, `--help`, `--version`, `--list-keywords`,
`--protocol json`).

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
   code page, so on a cp437/cp1252 machine non-ASCII test *names* would land in
   `prlib_tests-*_tests.cmake` mangled and ctest would report "No test cases
   matched".  The test names are ASCII now, which removes the failure mode; the
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
   Open for the next session: search and replace has **no task file** although
   the feature list asks for it (the menu entries are there, disabled), the
   output panel still has one position and one font size (task_27), and
   `setWindowIcon` is never called, so the window uses the default Qt icon.

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