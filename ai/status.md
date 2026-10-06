# Status tracker

Last updated: after the portable-build task (task_61) and the rounds that followed — parts
77--94: the two emblems on the first page of every document, `technical.typ` checked against
the C++ sources (nine more listings, the grammar brought in line with `parser.cpp`), the
"привычный/обычный Prolog" wording replaced by ISO Prolog, the whole `ai/` folder translated
into English, the last `$` taken out of the interpreter (part 81), three built-ins —
`СОРТИРОВКА/2`, `ПОЛНЫЙ/1`, `ДЛЯВСЕХ/2` — added in place of `bagof`/`setof` (part 82,
ADR-025), the examples folder given a map and a `problems/` shelf (part 83), the standard
library started as `stdlib/` with `lists.pld`, `sets.pld`, `sorts.pld` and a checked demo
(part 84), that library grown to five files, documented in a sixth document and found by the
interpreter beside itself without a flag (part 85, ADR-026), its own texts given a single
space after a sentence, with `tail/2` beside `head/2` (part 86), and the differences
document relieved of the `$` item while the «не A, а B» turns became plain statements
(part 87), and the window's «Проблемы» tab turned into a table whose rows wrap and open
their line on a double-click, with long paths shortened in the output and in the settings
list (part 88), the console made to name the place of a runtime error, which it used to
print as a bare message (part 89), a click on a row of «Проблемы» made to bring the
tab of that file to the front (part 90), and the GUI given a small refactoring pass —
one duplicated clearing body out, and the two tables set on one shared base (part 91), and the
goal field given its own switch while a run learned to show the hidden output panel
(part 92), and that panel made a strip again after it had taken half of the editor column
(part 93), and the version raised to **2.1.0** with a fresh portable package built for it
(part 94).

## Overall

* Phase: the core is feature-complete and verified on Windows; the PySide6 window is a
  full front end (task_21 -- task_60), not a skeleton: files and tabs, the code editor,
  completion, the built-in reference, stepping and tracing, the graphics window, the
  output panel with its answer table and the settings dialog are all in.  The only thing
  left on the board is `task_46`'s named profiles.
* Build: the `windows-msvc` preset (Visual Studio 18 2026, MSVC 19.51) is green locally,
  tests included; the Linux presets, including `-Werror`, build cleanly.
* Tests: 316/316 in about six seconds — 299 Catch2 cases plus 17 command-line and
  integration tests.  The window has its own 23 offscreen scripts plus `protocol_smoke.py`;
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

* UTF-8 lexer with Cyrillic support, 116 reserved built-in names — every Russian one with
  an English alias — and trailing-dot floats (`1.`).
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
* Lists: `СОРТИРОВКА/2` (`sort`) — ascending, repeats dropped, in the dialect's own
  order; `ПОЛНЫЙ/1` (`ground`) — no free variable anywhere, cycle-safe; `ДЛЯВСЕХ/2`
  (`forall`) — no solution of the condition fails the action (ADR-025).
* I/O: `ВЫВОД`, `ВЫВОДПС`, `ВВКОД`, `ВВОДЦЕЛ`, `ВВОДВЕЩ`, `ВВОДСИМВ`, `ВВОДСТР`,
  `ЧТЕНИЕ_ИЗ`, `ЗАПИСЬ_В`; the front-end's answer is a piece of the input stream
  (ADR-023).
* Program database: `СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`.
* Graphics over `GraphicsBackend` (a null one, a recording one, and the window's bitmap).
* `НАЙТИВСЕ/3` reproduces the required examples.
* `ИМПОРТ` loader: import-once, include paths, cycle detection, root containment, and a
  failure that names the directories tried.
* CLI11 front-end with UTF-8 console setup on Windows and diagnostics in the
  `file:line:column: error: message` form, with severities.
* Examples live in `examples/` and are covered by golden tests: the course in
  `examples/lessons` is a program per lesson whose own `%!` lines are its expected
  output, the five demos beside it (`first_demo`, `sort_demo`, `ground_demo`,
  `forall_demo`, `stdlib_demo`) are checked the same way, and the tasks are in
  `examples/problems` (`factorial`, the Hanoi tower, `knapsack`).  `examples/README.md`
  is the map of the folder.  The standard library the dialect ships is `stdlib/` —
  beside the executable, imported with `-I stdlib` — and `stdlib_demo.pld` is its
  checked tour.
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
| task_63_graphics_rgb | done | the 0…15 palette is gone: a colour is `0xRRGGBB` (`0`…`16777215`, anything else an error), and the names plus `rgb/4` live in `stdlib/graphics.pld` |
| task_64_interrupt_during_a_run | open | a session solves a request *inside* `dispatch`, so `interrupt` written while a query solves is dispatched only after it — «Остановить» and «Предел времени» fall back on killing the process (the cure is a session that watches the stream while it solves) |
| task_65_output_in_slices | done | events reach the window in slices (`EVENTS_PER_TURN` = 250 per turn of the event loop), so a program that floods the panes or the picture can still be stopped; nothing is dropped, and over `FLOOD_EVENTS` (20 000/s) the pane says so once |
| task_66_output_limit | done | «Предел вывода» — the window counts the output events of a run (a text line, a drawing primitive, a trace line) and stops it past the cap; the stream's *decode* is bounded by bytes too |
| task_67_variable_modes | done | `--vars 0\|1\|2` and the lexer rule, the first-line marker `:- ИМЕНА(N).` with its own diagnostic, the window (row, highlighter, and the file's mode travelling with `load`/`query`/`format` — protocol 12), `examples/lessons/_old/` (six files) plus the three new old-format examples checked like lessons, and the documents |
| task_68_tab_context_menu | done | a right click on a tab shows a menu built from `actions.TAB_CONTEXT` — «Показать в проводнике» (`explorer /select,<path>` and its two cousins), with the picture of «Открыть…» and the keys `Ctrl+E`; the pointed-at tab is made current first, the entry follows the buffer's path, and the command goes through a replaceable seam |
| task_69_open_import | done | `F12` opens the file an `ИМПОРТ` directive names, in a tab: `paths.resolve_import` repeats the interpreter's search order (the importing file's folder, the `-I` folders, `stdlib`), the menu entry is enabled only while the caret sits on such a line, and `tokens.literal_text` unwraps the quoted name the editor's tokenizer hands over |
| task_70_variable_mode_row | done | the window's «Имена переменных» row lost «по первой строке файла» — it said exactly what «как в ISO» said (the marker beats the row in the engine *and* in the window, and mode 0 never travels on the wire); three items now with ISO as the default, and a settings file still holding the old `auto` reads as `0` |
| task_71_output_tab_menu | done | a right click on the output panel's «Вывод» tab offers «Очистить вывод» — the shared `clear_output` `QAction` of the action table (the one `Ctrl+L` reaches), offered on that tab alone and without switching tabs, because the command acts on the pane and not on the tab in front (the titles carry a counter, so the tab is told apart by the pane it shows) |
| task_72_pld_prose | done | the «это А, а не Б» construction is gone from twenty places in sixteen `.pld` files — statements only, the five exercise questions keep the contrast because it *is* the question; the teacher's own edits were finished (two more `%!` answers for the new students, a missing final newline, a typo), and `test_queries.py`'s `PINNED` was refreshed after being red since task_67 |

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
* the user's report «there is a problem with running files that have many questions and
  that produce some output» is **not a defect**: it is exactly why the whole run cannot be
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
  the user asked for after the stepping work ("let us check that all branches of the
  predicates work correctly").  The method was the point: drive the built `prologd.exe`
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
* Question-answering round, part 23: **«where the discrepancy is» in `КОПИЯ`**, from the
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
* GUI round, part 28: **task_36 — questions in the margin**.  In the margin left of the
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
* GUI round, part 29: **task_37 — the predicate reference inside the window**.  The built-in
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
* GUI round, part 37 (follow-up after the first hands-on look): **"Не сохранять" on
  an untitled buffer no longer resurrects its text**.  The first version wrote the tab
  list *before* asking about unsaved work, so a discarded draft came back on the next
  start — the answer "do not save" turned into a lie.  The list is now taken before the
  questions (buffer objects, not copies) and written only after a successful
  `close_all()`, and buffers answered with "Не сохранять" are dropped from it.  The
  reverse case was fixed along the way: a buffer saved into a file while the window
  closes is remembered as that file, not as «Без имени» with its text.
* GUI round, part 38: **the four switches that were left over** — the "small things"
  from the task_29 list, each a switch over behaviour that already existed:
  «Автоотступ» (`editor/auto_indent`), «Следить за выводом» (`view/follow_output`),
  «Спрашивать ввод» (`view/input_mode`: «в панели» / «в диалоге») and «Выводить
  вопросы при запуске» (`execution/run_questions` — also the `questions` flag of
  `load`, protocol 5).  Nothing else changed shape: `Enter` either continues a
  line's indentation or starts it at the margin (the indent unit stays with `Tab`);
  the output panel either keeps the end in view or stays put (it already stopped
  following when the reader scrolled up — the switch is about something else:
  "don't lead the eye away"); a program's question is answered either in the
  console below the output or in a window, regardless of what is on screen; a run
  either answers its own `?` lines or loads with rules alone — `run_program`'s
  `questions` argument now defaults from the settings, while clicking a marker in
  the margin still asks exactly its own question with an explicit
  `questions=False`.  The dialog grew to 32 rows (was 28), the file has 42 keys.
  Checks: one per switch (`test_editor.py`, `test_output.py`, `test_window.py`)
  and the defaults in `test_settings.py`.  251/251 ctest, 20 headless GUI scripts,
  five PDFs.
* GUI round, part 39: **the dark theme**.  The «Вид → Оформление» item became a
  submenu of three entries (light, dark, as in the system): three themes cannot be
  said with one switch, and the title «Системная тема (иначе светлая)» would have
  become untrue.  The dark theme is not an inversion of the light one but **a
  palette of its own**: one `theme.Palette` record per theme (page, a highlight of
  15 colours, error and step bars, search hits, current line, number strip,
  question marker, output colours), `appearance.qt_palette` turns it into the
  widget palette, and the editor, the buffers and the output panel read their
  colours from it too.  The 4.5 contrast (WCAG AA) is now checked not for one
  light palette but over the list `Palette.readable_pairs` — for both, and against
  the page the colour is actually painted on; the light one keeps 4.5 everywhere,
  and the check immediately found one exception: the trace colour was 4.48 and
  became a step darker (4.61).  The theme change is visible in the editor and *in
  the output panel*: each line's kind is remembered there (`_kinds`), so the
  history is repainted instead of staying written in the light theme's red on a
  dark page.  The command line has `--theme light|dark|system`; the value `dark`
  was added to the «Оформление» row's choices in the dialog (32 rows, as before),
  and the `view-theme` icon stayed in the audit as the picture of that submenu.
  251/251 ctest, 20 headless GUI scripts, five PDFs.
* GUI round, part 40: **"use the system colours"** — the last item of the colour
  page.  The "as in the system" option was half a theme: the widget palette came
  from the system while the highlight colours stayed light, and on a dark desktop
  that is exactly what the dark theme was introduced for.  Now `system` follows
  the desktop entirely: `appearance.apply_theme` returns the palette *and* the
  platform style, and `appearance.theme_palette("system")` yields the light or the
  dark palette according to `QStyleHints.colorScheme()` (if the platform is
  silent, by the window colour it gave).  Both answers — "what scheme the desktop
  has" and "what it set" — are read once, at the first `apply_theme`, because
  after our palette they speak about us: the check caught the old defect at once
  (under `system` it printed the "platform palette" #1e1e1e, i.e. our own dark
  one).  The style is remembered **by name**: installing another style deletes the
  previous object, and bringing it back gives `RuntimeError: Internal C++ object
  already deleted`.  The setting in the dialog is now called «как в системе —
  системные цвета»; the hint says that «тёмное» is a palette of its own while «как
  в системе» takes the desktop's colours.  251/251 ctest, 20 headless GUI scripts,
  five PDFs.
* Planning round, part 41: **two items of the task_29 list that were not a dialog
  row became tasks** — `task_45_gui_graphics_window.md` (graphics: a bitmap backend
  inside the engine, protocol 9 events and a snapshot, the canvas and a window of
  its own) and `task_46_interpreter_options_and_limits.md` (the interpreter path,
  the process working directory, profiles and per-program limits).  While they were
  being written it turned out that what task_29 recorded was pessimistic:
  `maxSteps`, `maxDepth`, `maxNestedDepth` and `maxFindAllSolutions` **already
  exist** in the engine and are exposed as `--max-steps`/`--max-depth`, so task_46
  is not new engine options but a session key, a wall-clock timeout and rows in
  the dialog; and graphics need not only an interface but an answer to `getPixel`
  in the middle of a built-in predicate — hence the decision to keep the pixels in
  the engine and send primitives.  An old defect in `doc/gui.typ` was fixed along
  the way: §9.3 promised 42 drawn icons and 7 missing (now 43 and 6,
  `execution-step-over` drawn 2026-10-01, `view-theme` the picture of the
  «Оформление» submenu), while §10 still called the output panel's separate font
  size undone — it has existed since task_29; §10 gained the graphics window and
  the profiles with links to the new tasks, and the README the exact audit numbers
  (49/43/6).
* GUI round, part 42: **task_46, the limits half**.  A program gone into infinite
  search must end by itself: a run now has four limits, each names itself, and a
  zero everywhere means "no limit".  The engine gained named defaults and a
  `Limits` with `applyTo(EngineOptions&)` — both the flags and the protocol go
  through it, so the settings row and the flag cannot diverge; `--max-findall`
  joined `--max-steps`/`--max-depth` (and `--max-findall 0` stopped meaning "zero
  solutions" — now it is "no limit", like its neighbours).  Protocol **9**: `load`
  has a `limits` object, applied *before* loading — the same load runs the program,
  and a limit set after it would arrive late for its own run.  The message names
  the limit, its value and where to raise it: «Превышен предел шагов выполнения:
  5000 (--max-steps; «Предел шагов» в настройках окна)», and the dialog row
  carries the same name.  `НАЙТИВСЕ` hitting a limit is *diagnostics*, not silent
  truncation: a shorter list that is later taken for the answer is worse than an
  error.  The dialog has four rows («Предел шагов», «Предел глубины», «Предел
  решений НАЙТИВСЕ», «Предел времени, с»), and the run itself writes into the
  panel the limits it went with.
  The timeout is solved **by the window's clock** (`QTimer` and an `interrupt`
  request), not in the engine: `steady_clock::now()` in a hot place is a cost on
  every solution, and it is the front end that knows about "too long for a lesson".
  Two verified consequences follow: a computing run ends by the deadline (the
  engine polls the stop flag on every step anyway), while a run waiting for `ВВОД`
  stands *outside* the solver and only «Остановить» breaks it — that is what
  task_46 records, and nothing else is promised.
  Along the way the protocol became more honest: a request with a field of the
  wrong type (`"maxSteps":-1`, or a string instead of a number) used to turn
  silently into a huge limit, and is now an `error` event with `kind":"protocol"`,
  and the session reads the next line — on such a request the process used to
  crash.
  252/252 ctest, 20 headless GUI scripts, five PDFs (`gui.pdf` — 27 pages, §6.3 on
  19–20; `help.pdf` — 30 pages, §15 on 24).
* GUI round, part 42 (follow-up after the review: **architecture, defaults and the
  RU/EN cancellation**).  Four edits of one evening.
  (1) **The interpreter knows nothing about the GUI**: the limit messages no
  longer name either a flag or a settings row — «Превышена глубина рекурсии: 200»,
  «Превышен предел шагов выполнения: 5000», «Превышен предел решений НАЙТИВСЕ:
  50».  ADR-020: a limit is an option of the *run*, not knowledge of the core;
  "where to raise it" is said by whoever set the number — the flag in `--help`,
  the row in the dialog.  In the window the run itself does that: the line
  «пределы: «Предел шагов» 5000 — строки в «Выполнении» настроек» before the
  start, and only about those limits that differ from the defaults (otherwise the
  panel would report the same two numbers on every run).  Tests guard both sides:
  the message has the limit and its value and not the word "settings".
  (2) **The core defaults — no limit** (0 for steps, depth and НАЙТИВСЕ): a fresh
  `prologd` runs a program to the end, and `--max-depth 0` stopped being a
  "removal" of something that was not there.  The only default left is
  `kDefaultMaxNestedDepth`, and it is not a limit for the user but a guard of the
  nested-solver stack (task_38).  The consequence is recorded honestly in the
  manual: without a limit nothing stops a runaway recursion, it grows until memory
  runs out (the frame chain is released iteratively, so it is memory, not the C++
  stack).  Hence `engine_limits.cmake` now passes `--max-depth 10000` itself.
  (3) **The window defaults** — 0 / 1 000 000 / 1 000 000 / 0: steps and the clock
  off, depth and solutions bounded by a number no teaching program will notice and
  a runaway one will not survive.  It is the window that takes the decision about
  what is safe for a lesson, because the core does not take it.
  (4) **RU/EN is cancelled** (ADR-021): the window stays Russian, no
  `QTranslator`; English stays with the language (the built-in names, task_39) and
  with the manual.  The item is closed in task_29 and in §10 of `gui.typ` — it is
  now named there as a decision, not a debt.
  252/252 ctest, 20 headless GUI scripts, five PDFs.
* GUI round, part 43: **task_45 — the graphics window**.  `ТОЧКА`, `ЛИНИЯ`,
  `ОКРУЖНОСТЬ` and `ЗАКРАСКА` drew into an empty implementation: the program drew
  a picture and the student saw nothing.  Now the screen is driven by the
  *interpreter* (`BitmapGraphicsBackend`: a 1024×768 buffer that itself answers the
  `TOCHKA(X, Y, Ц)` read and executes `ЗАКРАСКА` itself), and the window receives
  every drawn figure — protocol **10**: `graphics` events (a cell, a segment or a
  rectangle) and the request `{"cmd":"graphics","snapshot":true}`, answered by a
  `bitmap` of the whole screen (base64, four bytes per point).  The pixels stay
  inside for a reason: `ТОЧКА(X, Y, Цвет)` reads a point and `ЗАКРАСКА` the thing
  just drawn, all of it from inside a built-in predicate; a synchronous question to
  the shell in the middle of a predicate is not defined anywhere in the protocol.
  `graphics.py` (no Qt) repeats the same drawing rules — Bresenham, the rectangle
  outline, an ellipse by parametric equation, four-neighbour fill, edge clipping —
  and `test_graphics.py` compares the two implementations *pixel by pixel*: it
  draws the program, takes the finished raster from the interpreter and repeats
  the same events on the canvas.  `graphicswindow.py` is a window of its own
  (`Qt.Window`, otherwise a widget with a parent becomes a child and the drawing
  is embedded in the editor) with «Вписать в окно», «1 : 1» with scrolling,
  «Очистить», «Сохранить как PNG…» and the coordinates of the point under the
  cursor; the window's visibility and position are the machine keys
  `view/graphics_visible` and `view/graphics_geometry` (`saveGeometry` in base64:
  Qt knows about screens, and a rectangle would have had to be taught that anew).
  The menu no longer has disabled items: «Графическое окно» was the last one
  waiting for something.  Two defects were found exactly where the acceptance
  promised to find them — by eye on the drawing: the ellipse was read as a
  *rectangle* (`ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes four numbers as they are, while
  the parameter names from task_15 said `x1..y2`), so the face from
  `examples/drawing.pld` came out as a blue field rather than a face; and the empty
  canvas was *transparently black* (a `bytearray` is zeros, and zero alpha in
  `RGBA8888` is transparency), so the desktop shone through the drawing.  Both
  mistakes were invisible to the comparison of the two implementations: both drew
  the same and both wrongly.  264/264 ctest, 21 headless GUI scripts, five PDFs.
* GUI round, part 44: **task_47 and the first half of task_48 — what turned up
  while working with the lessons and the window**.  The user fixed lesson 12 by
  hand, and out of that grew three tasks (`task_47`, `task_48`, `task_49`) and
  thirteen remarks; this round closes the first and half of the second.
  **One style for the course.**  21 of the repository's 25 programs are aligned by
  the interpreter itself (`prologd --format`: soft mode, width 80, one tab) —
  before that the lessons were in three styles, and in `lesson_12` spaces stood
  next to tabs.  More important than the fix itself is the check: a new test "every
  shipped program is already in the standard shape" compares each file with its
  own formatted look and names the one that lagged behind — the style no longer
  has to be kept in one's head.  `examples/lessons/_old` is deliberately not
  aligned: it is a sample of the port, not its style.
  **What came out during the alignment.**  Formatting removes trailing spaces — in
  `%!` lines too — while `lesson_07` promised the line `Загадано число. ` with a
  space (the output itself printed it); the space was removed from the message in
  the rule, not from the promise, and a rule about it was written into
  `doc/lessons.typ`.  Lessons 7 and 12 held queries longer than the width, and
  soft mode *wrapped* them — but the triangle in the margin reads a line, so a
  query torn in two stopped being clickable; this was noticed not by eye but by
  the pinned numbers in `test_queries.py` (`lesson_07`: 19 → 18).  So the
  formatter gained a rule: **the width wraps neither a query nor a directive in
  any mode** (a comment and the author's blank line are wrapped), and it is pinned
  in `test_formatter.cpp` at widths 20 and 80.  Two promises of `lesson_12` lagged
  behind the hand-rewritten lesson (the list of frame and garden shapes), and the
  animation was commented out and printed nothing: everything was taken from the
  working interpreter, and a two-frame animation (80 ms) was put next to it so
  that the promise "animation finished" stayed true; 250 frames were left as the
  `%?` question, which runs on a click on the triangle.
  **Hard mode** wraps after `:-` too: the clause head stands alone, and the body
  goals start on the next line — before, the first goal hid at the end of the head
  line, exactly where it is skipped.  For facts, queries and directives the shape
  does not change: they have no head, and a `:-` on a line of its own is noise.
  **The formatting mode** came back to the toolbar, right after «Форматировать»:
  a `QToolButton` with a list of three modes and "selection only" (the
  `edit-format-set` icon, drawn long ago and unused by anyone), and the «Правка →
  Формат» submenu is gone — a control has one place.
  **Fewer icons and commands** (task_48): `help-about.png` was the same drawing as
  `prologd2.png` («О программе» now wears the application icon), the «Номера
  строк» and «Панель инструментов» switches stayed words (their pictures were
  removed), «Сохранить все» moved from the toolbar into «Файл», and the «Найти
  выделенное» and «Найти выделенное назад» commands left «Поиск» together with
  their icons.  The icon audit is now 45 names, 41 drawn, 4 waiting (and
  `execution-restart`, drawn and unused by anyone).
  Tests: 267/267 ctest (253 Catch2 cases — three new: the hard head form, a query
  with a directive on one line, «все программы уже в стандартном виде»), 21
  headless GUI scripts (`test_queries.py` with an updated list of questions,
  `test_window.py` with the mode button on the toolbar and without «Сохранить
  все»), five PDFs.  The remark about `window.close()` was also paid for with
  time: a script that closes a window with unsaved edits opens a real modal
  question and hangs the run — session restore must be checked through
  `_store_session` and a second `MainWindow`, not by closing the first.
* GUI round, part 45: **task_48 — the second half: one `Esc` and a window that
  opens itself**.  The request was exactly this: «`Esc` closes windows and panels in
  the order: graphics window → search and replace → predicate help → insert cheat
  sheet» and «the graphics window opens by itself on the first drawing primitive of
  a run, and never again in that run».
  **`Esc`.**  There is one handler, on the main window (`MainWindow.keyPressEvent`
  plus `_escape_closes_something`), and the order is a chain of `if`s: the graphics
  window, the search bar, the help panel, the insert cheat sheet; when there is
  none of those, the key is not ours and the event goes on — the test tells this
  apart, because a press counts as handled only when something closed.  It is done
  by **propagating the event**, not with a `QShortcut`, and that is not a detail: a
  shortcut is handled *before* the focused widget and would have taken `Esc` from
  the completion list (it closes on `Esc`) and from the «Найти» field (the key was
  pressed there, so closing the bar is what it means).  Those two places answer for
  themselves, such a key never reaches the window, and that is what `doc/gui.typ`
  §4.1 records.  The graphics window has its own `Esc`: it has its own keyboard
  focus (it may sit on a second screen), and this key does not reach the main
  window; it closes through `close()`, i.e. by the same path as the cross, so it
  does not disagree with the menu tick.
  **The window that opens itself.**  `_on_drawn` shows the window if the
  `_graphics_shown` flag is empty; the flag is cleared by `run_program` and set by
  `show_graphics_window` (whoever showed it — the tick, the settings or the run
  itself), and hiding the window does not clear it.  That yields both halves of
  the request: the drawing is visible without hunting for the tick, and a window
  closed during a long animation stays closed until the end of the run.  The
  moment is chosen by the first *figure*, not by the start of the run: a program
  that draws nothing does not open the window.  Nothing had to be caught up —
  `show_graphics_window` asks for a snapshot anyway, so a window opened in the
  middle of a drawing gets it whole.
  Tests: two new in `test_window.py`, one per half.  The `Esc` order is checked by
  a real press into the *editor* (so that the event propagates), and "a closed
  window does not open again" by the program `?ТОЧКА(1, 1, 1), ЖДИ(200), ТОЧКА(6,
  6, 6).`: the close has to fall *between* the two figures, otherwise the check
  would pass without the flag.  267/267 ctest, 21 headless GUI scripts, five PDFs.
* GUI round, part 46: **task_49 — four defects found by working with the window,
  and the main window's size**.  The user added one phrase to the request to
  continue («the graphics window keeps its size and position, while the main window
  does not») — and it became the fifth item of the task.
  **`Шаг` → `Стоп` → `Запуск`.**  The window thought the run was still at a step
  point, and «Запуск» went down the "continue" path, i.e. sent `step` to an
  interpreter that was waiting for no one: the session answered with exactly that
  error "no step waiting for an answer", and the program did not start.  The state
  lives in the *session* (`_paused`), and it is cleared by the events a run ends
  with: `result`, `loaded`, an error and the process ending.  The reproduction
  refined the last pair: a polite «Стоп» finishes the *request*, not the process,
  so the clearing event turns out to be the error of the interrupted request —
  without this case the check fails (and it also requires the process to be alive,
  otherwise «Стоп» could pass for the end of the session).
  **Two tabs named «Без имени».**  The reproduction decided which of the two rules
  was wrong: the restore was wrong — the `*` was given to the tab the user had not
  touched (the welcome program of the first tab, with an empty second one next to
  it; with a single tab everything looked right only because an empty tab is not
  stored at all).  The session is written *after* the close questions, i.e. after
  every edit has already been resolved: a tab that came back as text is one the
  user did not touch.  So a tab record now carries an "has unsaved" mark, and it
  is in **JSON** — a fourth field through a tab could not be told apart from a
  line of the old form whose text contains a tab (and a program's text always
  does).
  **A hang on tracing.**  The cause was sought by measurement, not by guessing,
  and the scoreboard came out like this: the output panel, 20 000 lines — 0.68 s
  before and 0.26 s after; 200 000 lines with a limit of 50 000 — **21.9 s** before
  and **3.0 s** after; tracing a deep recursion (16 002 lines) in full — 2.2 s
  before and 0.6 s after.  Two costs had added up: the window paid a Python call
  per *line*, and the panel trimmed the history line by line, i.e. a square
  (removing from the start of a document costs about the same no matter how much
  you remove).  Now the window hands out output in a batch once per event-loop
  turn and merges same-kind neighbours (this is not a throttle: nothing is lost
  and nothing waits on a clock — a lost log line is worse than a slow one), and
  the panel cuts the history in chunks of a tenth of the limit.  A negative result
  is recorded too: the batch alone does not save it (20 000 lines in one insertion
  is also 27 µs per line), scrolling is not the cost (32 µs per line with
  following off), and the cursor is not the cost (a new cursor per insertion: 7 µs
  versus 5 for a permanent one).
  **The main window's size.**  The graphics window has remembered its own with
  `saveGeometry()` since task_45, while the main one — the one moved first —
  remembered nothing.  Now both go through one module, `prologd_gui.geometry`, and
  the key `view/window_geometry` is a machine one (it is the window's record about
  itself, not a dialog row).  The check puts the window at 720×520 at (60, 40),
  closes it, opens it again with the same settings file and requires the same
  numbers, and without a record the old size 1000×700; and it does *not* take 910
  points of width, because the offscreen platform's screen is 800×800 and
  `restoreGeometry` rightly clamps a size that does not fit the screen.  The
  reproductions are pinned by tests and checked "in reverse": with the fix hidden
  each of them fails (`git stash` on one file), with the fix it passes.
  Tests: 267/267 ctest, 21 headless GUI scripts (four new checks in
  `test_window.py`, one in `test_documents.py`, an updated one in
  `test_output.py`), five PDFs.  Left in task_49: live output — `IoContext` hands
  out a line, the session sends an event per line, and the count prints 3, 2, 1.
* GUI round, part 47: **task_49 closed — live output**.  The task's last item was
  born out of the lesson's animation: the program prints a line, sleeps, prints
  the next, and the window showed it as one block at the end of the run, so the
  count in lesson 12 looked like a jump to the last number.
  The seam is made in `IoContext`: `setOutputLineSink` — "the line being written is
  finished" — and it fires on `ПС` and on the newline the `ВЫВОД` itself carries
  (because the line then ends although no prompt was printed).  The hook says
  *when*, never *what*: the text is taken by the owner from its own stream, so the
  console does not change by a byte, and a program that redirected its output to a
  file reports nothing.  The session installs the hook after `setTraceSink` and
  answers it with `flush()` — the very one that already sent `output` at the end
  of a request; the granularity became per line, the event's shape and the order
  of the text did not.
  Measurement (a program printing three lines with `ЖДИ(60)` between them): without
  the hook `loaded@0.15` and after it **one** `output@0.15` with all three lines;
  with the hook `output@0.01`, `output@0.08`, `output@0.14`, and only then
  `loaded@0.14`.  Checks: `test_io_context.cpp` (the hook stays silent on an
  unfinished line and on a context without an owner), a section in
  `protocol_session.cmake` (four lines, each *before* `loaded`, and the positions
  `one < two < three < loaded`), `protocol_smoke.py`, `test_stepping.py` and a new
  `test_window.py::test_the_output_arrives_while_the_program_runs` (the first line
  is in the panel while the run goes on, the third is not there yet, «Запустить»
  is disabled — and afterwards there is a third and the run's end).  Two old
  checks expected one block per joined line and were updated: the text is the
  same, the granularity finer.
  Tests: 268/268 ctest, 21 headless GUI scripts, five PDFs.
* GUI round, part 48: **the icons in the dark theme accepted** — the user looked
  at the redrawn icons: «the icons in the dark theme look fine», nothing left to draw.
  This closes the last tail of `task_48`, and only `task_46` remains on the board
  (the interpreter path, the process working directory, profiles) plus the
  decision whether the text mode needs `--timeout-ms`.
* GUI round, part 49: **task_46 — the interpreter path and the process working
  directory; `--timeout-ms` decided and deferred**.  The user picked the first two
  items and refused the fourth.
  **The interpreter.**  The `execution/interpreter` row is a new `file` type in
  the settings table (with its own «Обзор…»: it picks a file, not a directory); an
  empty string means "the one the window is running with", and a filled one
  overrides `--exe`, which stays the fallback (it, as before, looks for a fresh
  build).  `main.py` now checks the path that will *really* run — otherwise on a
  teacher's machine, where its own `prologd.exe` lies next to the window, the
  check of the build path would wrongly refuse.  The session gained
  `set_executable`/`executable`, and the window gained one gateway,
  `_start_session`, through which all three places that create a session pass
  (run, query, formatting): a nonexistent path is reported in the panel before any
  start, not as half a launched process.  The status line names the interpreter
  when a different one is chosen (`prologd: …` on the right) — so the window shows
  that a build other than the usual one is at work.
  **The process working directory.**  `execution/process_directory` — a choice of
  three: «каталог файла программы» (a saved file writes next to itself), «рабочая
  папка окна» (the previous behaviour) and «свой каталог»
  (`execution/process_directory_path`).  This is not «Рабочая папка (ИМПОРТ)» —
  that row goes into `-I` as a *search* directory, while this one is
  `QProcess.setWorkingDirectory`: `ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ` and the rest of the
  relative paths are counted from it.  Before, all of this wrote to wherever the
  window was launched from (inherited from the parent), i.e. for every student to
  a different place.
  **«Применить».**  Changes in either of the two items cannot reach a live process
  (the program and the directory are fixed by the start), so a live session is
  restarted — and the status line says so; a path that does not exist does not
  touch the live session and writes «интерпретатор не найден».
  **`--timeout-ms`** — decided not to do it: a clock in the solver's hot place
  would be a cost on every solution, the window's time limit already covers it,
  and the console run has the shell's timeout.
  Checks: `test_settings.py` (defaults and the round trip of the new keys, a bad
  choice falls into `file`), `test_settingsdialog.py` (the file row asks for a
  file, not a directory; the choice of three), three new in `test_window.py` (a
  copy of the exe as a "different" interpreter — the row reaches the session, the
  run goes by the copy, the status line names it; a nonexistent path is reported
  in the panel and starts no session; `ЗАПИСЬ_В` writes into the chosen directory
  — both a fixed one and "next to the file").  Left in task_46: profiles.
* GUI round, part 50: **a small cleanup of the settings**.  The user asked to
  merge the superfluous and clarify the labels.
  **One row instead of two for `ИМПОРТ`.**  «Рабочая папка (ИМПОРТ)» was merged
  into «Дополнительные каталоги ИМПОРТ»: there was one directory plus a list, now
  one list (`execution/import_paths`); the `execution/working_directory` key
  disappeared from the table, and `_import_directories` builds `-I` from the
  command line and this list.  An old settings file keeps the former key as an
  unknown one (the promise "unknown keys survive"), but it is no longer read.
  **The list buttons** «Добавить»/«Убрать» — without text: the icons stayed
  (`settings-add`/`settings-remove`), the text moved into the hint.
  **«Свой каталог процесса»** is inactive until «свой каталог» is chosen in
  «Рабочий каталог процесса» — the field and its "…" are disabled by one row; the
  dialog keeps a row wrapper (`_row_holders`) and hooks it to the selection
  change.
  **The time limit — in milliseconds.**  The key `execution/timeout_seconds` →
  `execution/timeout_milliseconds`, the row «Предел времени, мс» (ceiling — an
  hour, 3 600 000), the hint "by time" instead of "by the clock",
  `_arm_timeout`/`_on_timeout` set the timer and write "N ms".
  **Hints and labels.**  «Сохранять перед запуском» was clarified (it saves the
  current file); «Восстанавливать вкладки»'s hint lost the part about «Без
  имени»; the theme «как в системе — системные цвета» → «системное» (and in the
  «Оформление» menu — «Системное»).
  The checks were updated for the new state (`test_settings.py`,
  `test_settingsdialog.py` — among them a new "the path is inactive until «свой
  каталог»", `test_window.py` — the limit in ms and the `-I` list,
  `test_appearance.py`).  21 headless GUI scripts, five PDFs.
* GUI round, part 51: **the `questions` flag split into "run" and "print"**.  One
  switch, «Выводить вопросы при запуске», did two things at once, and the user
  asked to separate them.  Now «Выполнять вопросы при запуске»
  (`execution/run_questions`, was and remains `questions` on the wire) decides
  whether the program's `?` lines are run at startup, and «Печатать вопросы при
  запуске» (`execution/print_questions`, off by default) prints the question
  itself — `?цель.` — before its answer, like `-q` on the command line.  This is
  **protocol 11**: `load` gained `printQuestions`; the echo is done by the session
  in `runQuery` (an `output` event before `result`), not by the window.  For the
  question line to print *variable names* rather than `_1`, `Engine::queryText`
  (shared by `-q` and the protocol) hands the printer a name dictionary through
  the new `PrintOptions::variableName` field — `ВЫВОД` and the rest of the
  printing still write `_N`, as the manual promises.  `-q` already wrote
  `?факт(_1).` — now both it and the window write `?факт(X).`.
  Checks: `protocol_session.cmake` (the echo before the answer),
  `test_formatter.py` and `protocol_smoke.py` (protocol 11), `test_settings.py`
  (the `print_questions` default), a new
  `test_window.py::test_print_questions_echoes_the_question_line`.  268/268
  ctest, 21 headless GUI scripts, five PDFs.
* GUI round, part 52: **help: multi-line display, the alias by the name, unified
  argument names**.  The user asked for three things about the help and the
  reference view.
  **Multi-line display in completion.**  The label under the list showed one line
  `имя — сводка`; now `Reference.detail_lines` assembles «имя (алиас) — сводка»,
  then the call variants, and the label wraps the text at 460 px (`setWordWrap` +
  `setMaximumWidth` before `adjustSize` — otherwise the label sizes itself to one
  long line).
  **The alias by the name.**  The line "английское имя: …" was removed from `F1`;
  the English name stands next to the Russian one in parentheses: `ВВКОД
  (put_code) — …`.  The record's first line is shared by the doc window and the
  view (`reference.record_title`).
  **Argument names.**  `builtins.json` and `doc/help.typ` were moved to one
  vocabulary: `Ц` — integer, `Вещ` — real, `Пер` — variable, `Стр` — string,
  `Терм` — term, `Спис` — list (it used to be `X`, `с`, `ц1`, `П`, `S`, `N`,
  `Строка` mixed together).  Checking the variants against the code found one
  typo: in `УМНОЖЕНИЕ(ц1, П2, ц3, ц4)` the divisor was `ц2` while the code has
  `ц1` (for a free second argument); `СЛУЧ` was split into three variants (seed /
  random integer / range), and `ВВКОД` into two by the argument's role.  The
  summaries were clarified where they referred to the old names (`УМНОЖЕНИЕ`).
  The checks were updated (`test_completion.py` — multi-line text with an alias,
  `test_window.py` — `F1` without "английское имя", with the new names).
  `test_reference.py`, `test_completion.py`, `test_window.py` are green, five
  PDFs.
* GUI round, part 53: **task_50 — the output panel with tabs**.  The user asked
  to turn the output panel into four tabs: **Проблемы**, **Вывод**, **Система**,
  **Ввод**.
  **Tabs.**  The panel is one `QTabWidget` (`_panel_tabs`); the three read-only
  panes are still that same `panels.OutputPane` (bounded history, colours by
  kind, a line tail), and «Ввод» is the queue of prepared answers with the query
  console beneath it.  The kind of a line decides the tab:
  `OUTPUT`/`ECHO`/`TRACE` → Вывод, `NOTE` → Система, `ERROR`/`WARNING` →
  Проблемы (`panels.KIND_TAB`, routing in `_feed_pane`).  «Сохранить вывод…»
  writes the Вывод tab.
  **Counted titles and colour.**  The tab title carries a count: `Вывод:5`,
  `Проблемы:0`, `Система:3`, `Ввод:2` (Ввод counts the queue's non-empty lines
  and updates on `textChanged`).  The word «Проблемы» is coloured by state: the
  normal colour when empty, orange with warnings only, red when there is an
  error (`_error_count`/`_warning_count`, `tabTextColor`).
  **Focus.**  A run shows Вывод; diagnostics (both a warning and an error)
  switch to Проблемы (`_show_panel_tab`); the query console raises the Ввод tab
  when the program asks.
  **Removed.**  The «Поле очереди ввода» setting (`view/input_queue`) and its
  menu row are gone — the queue is a tab now; `view/output_sizes` disappeared
  (there is no inner splitter any more); the panel is **at the bottom** by
  default.
  **Load timer.**  After a file runs to completion, Система gets
  `--- база знаний загружена (N мс) ---` — the time is measured by the window's
  `QElapsedTimer` from «Запустить» to the `loaded` event (protocol 8).
  Checks: `test_window.py` — the new
  `test_the_panel_has_four_tabs_with_counts` (tabs, counts, colour, focus on
  diagnostics) and `test_a_run_focuses_the_output_and_the_system_notes_the_time`;
  the earlier runs were moved to `system_text()`/`problems_text()` (notes and
  diagnostics are no longer in Вывод).  `test_settings.py`/`test_settingsdialog.py`
  — without `input_queue`, default `bottom`.  All GUI suites are green.

* GUI round, part 54: **settings — the «Подсветка» section**.  The user asked the
  settings to show what is highlighted with what, and with which hex in each
  theme.
  The dialogue gained a **«Подсветка»** page, right after «Вид»: a table
  `what is highlighted · light · dark` in which each of the 15 syntax roles
  (`Комментарий`, `Вопрос в комментарии`, `Строка`, `Атом в кавычках`,
  `Служебное имя`, `Целое`/`Вещественное`, `Знаки препинания`, `Вопрос`,
  `Выражение`, `Атом`/`Переменная` in Latin and Cyrillic, `Имя из двух
  алфавитов`) is shown with its hex in both themes; the hex is filled with its
  colour (the text is black or white by brightness), and the page is read-only —
  the whole set is changed with «Вид → Оформление».  The data is Qt-free:
  `theme.SYNTAX_LABELS` (field name → caption) and `theme.syntax_rows()` (role,
  light hex, dark hex) — the dialogue and the test read the same thing, so a new
  role in `Theme` lands on the page by itself.
  Checks: `test_settingsdialog.py` — the «Подсветка» page in the list after
  «Вид» and the new
  `test_the_syntax_page_lists_every_colour_in_both_themes` (15 roles, both
  themes, the first row is a comment).  `test_appearance.py`/`test_settings.py`
  are green.

* GUI round, part 55: **«Подсветка» became editable**.  The user asked «can we make
  them editable?» — yes, we could.
  Each hex cell on the «Подсветка» page is now a **swatch button**: a click opens
  a colour chooser (the replaceable `_ask_color` — a modal `QColorDialog` hangs
  a headless test), and the chosen hex is painted on the button.  «Применить»
  writes **only the changed** roles to the settings, per theme: the keys
  `syntax/light` and `syntax/dark` (JSON `поле: "#rrggbb"`, in `MACHINE_KEYS`);
  «Вернуть встроенные цвета» resets both.  Reading cleans out junk:
  `Settings.syntax_overrides` takes only known fields with a valid hex
  (`theme.clean_hex`), and `Settings.palette` overlays them on the allowed
  palette through `theme.apply_syntax_overrides` — the `system` theme takes the
  override of the palette the desktop chose; the chrome (page, bars, output
  colours) is untouched.
  Checks: `test_settings.py` —
  `test_syntax_overrides_round_trip_and_reach_the_palette` (round trip, junk
  cleanup, the override reaches the palette and does not move the chrome),
  `test_settingsdialog.py` — `test_a_colour_can_be_changed_and_applied` (click on
  the swatch, «Применить» writes, «Вернуть встроенные» erases).  The full
  `test_settings.py`/`test_settingsdialog.py` are green (52 keys — 38 in the
  dialogue, 14 machine), the window's palette tests are green.

* GUI round, part 56: **the simplified palette became the default**.  The user
  picked a set of his own in «Настройки → Подсветка» (fewer different colours,
  Russian and English alike) and asked to ship it.
  In `theme.py` both palettes were updated: `query_comment` = the comment colour,
  `quoted_atom` = the string colour, `keyword` = the colour of
  `query`/`expression`, `atom_latin == atom_cyrillic` (violet `#4f1473` /
  `#d47bdc`), `variable_latin == variable_cyrillic` (red `#b62222` / `#ff7878`),
  `mixed` — the bright-red flag `#e30004` in both themes; `string` and
  `punctuation` were refined.  `mixed` was moved out of the WCAG check in
  `readable_pairs` — it is a signal, not text.  Checks: `test_appearance.py`
  (contrast), `test_highlighter.py` (the comment about the alphabets was
  updated), `test_settings.py`, `test_settingsdialog.py`, `test_window.py` — all
  green.

* GUI round, part 57: **the goal line — history and completion**.  The user
  asked the goal field (the `?цель(X).` line under the editor) for two things:
  history and suggestions, as in the main editor.
  `editor.QueryLine` (a `QLineEdit` subclass) appeared instead of a bare field:
  **history** — `Up`/`Down` walk the submitted goals (up to 20, the oldest are
  evicted; an empty or immediately repeated one is not recorded; `Down` past the
  newest returns the draft); **completion** — the same
  `completion.CompletionModel` as the editor's: reserved names + the predicates
  of the current document (`document_text` — the displayed buffer),
  `Ctrl+Пробел` or typing open a popup, `Enter`/`Tab` insert a call skeleton
  with the caret after `(`.  The placeholder gained the hint
  `… Enter: выполнить · ↑/↓: история · Ctrl+Пробел: подсказки`.  The window
  passes the field the keywords (`_on_ready`), `auto_complete_after` and
  `completion_match_case` (`apply_settings`).  Checks: the new
  `test_queryline.py` (4 checks — history, limit and dedup, suggestions and
  skeleton, Escape), `test_editor.py`/`test_window.py` green.

* GUI round, part 58: **the «Ввод» tab is the queue only; the query console sits
  under the goal line**.  The user asked to separate the input: leave the «Ввод»
  tab as the queue only (and never switch to it), and move the `LineEdit` that
  appears on a request under the goal line.
  The query console (`panels.InputPane`) left the «Ввод» tab for the editor
  column — under the goal line; on a question it appears there, and the panel
  stays on the tab the reader chose (usually «Вывод») — `_show_panel_tab(Ввод)`
  was removed from `_on_input_request`.  The «Ввод» tab is now only the queue of
  prepared answers (the `Ввод:N` count does not change).  Checks: the new
  `test_window.py::test_a_request_keeps_the_panel_on_the_output` (the console is
  not in the «Ввод» tab, the panel stays on «Вывод», the answer goes through),
  the full `test_window.py` is green.

* GUI round, part 59: **the query console — minimal height**.  The user noticed
  that the console, once it appeared, stretched over the whole column: its
  `QLineEdit` floated in the middle of a tall empty strip.  `panels.InputPane`'s
  vertical size policy became `Fixed` (always its own content, no stretching),
  and the `line` answer text area is capped at four lines instead of the default
  ~192 px.  Checks: the new
  `test_window.py::test_the_console_stays_one_field_high` (the `Fixed` policy and
  a height ≈ sizeHint after the window is shown), `test_output.py` and the full
  `test_window.py` are green.

* Interpreter round, part 60: **`\+` and a hint instead of `is/2`** (task_55,
  2026-10-02).  The answer to the user's question «there are 2 significant points left
  where Пролог-Д diverges from the others: `is` and `\+ Ц`»: `\+` was added, `is` was not.
  `\+` is one token (`TokenKind::NotGoal`: `peek(1) == '+'` in the lexer, a lone
  `\` stays an «недопустимый символ») and a term-level prefix in `parseTerm`,
  unfolding to `НЕ/1`; the priority is ISO: `\+ A, B` is `(\+ A), B`,
  `\+ (A, B)` negates the conjunction, `\+ \+ Ц` is double negation;
  `НАЙТИВСЕ(1, \+ РАВНО(1, 2), L)` answers `L=[1]`, and `\+ (ЛОЖЬ, РАВНО(B, 1)),
  ПЕР(B)` — `B=_1` (a binding inside a negation is undone).  The change does not
  touch the semantics, the dispatcher, `--list-keywords` or `doc/builtins.json`:
  it is syntax, and the call check sees the same `НЕ/1` (`walkGoal` expands it
  anyway).  The formatter reads `\+` as one token and does not break the line; in
  the GUI (`tokens.py`) it is also one punctuation mark, like `:-`.
  Instead of `is` — hints: `?is(X, #2+3#).` gets the warning «не найдено:
  is/2; «is» — не предикат: в Пролог-Д это «РАВНО(X, #2+3#)»» (the name is not
  reserved — a program may define its own `is/2`), and `?X is 2+3.` — the parse
  error ««is» — не оператор: выражение помечают «#…#», например
  «РАВНО(X, #2+3#)»»: without it an ISO reader heard only «Цель не может быть
  переменной».  A real operator was deliberately not added: `#…#` marks an
  expression (it is evaluated wherever a number is needed, and unification is
  reversible: `РАВНО(5, #2+3#)` — ДА), and `is` would introduce a second
  arithmetic — bare `2+3` in goals — that comparisons (`X < 2+1`, `=:=`) would
  have to get too, and those have already been given up (task_52).  Checks:
  274/274 ctest — six new Catch2 cases (lexer, parser with the `is` message,
  `\+` as `НЕ` in the control tests, the formatter) plus a test of the `is/2`
  warning text; the GUI `test_tokens.py` (a new `\+` pair) and `test_reference.py`
  are green.  The manual: §3.3 (about `is`), §4.4 and the appendix, both rows of
  the comparison table; `prologd-diff.typ` — §19, §20 and two rows in §14.

* The same day, continued: **the disjunction example and the wording about the
  dot**.  `prologd-diff.typ` §16 shows the task «в набор годятся и дешёвые
  инструменты, и надёжные» in three writings: two clauses with one head
  (Пролог-Д 1.0), `ИЛИ/2` (one branch) and `;` in the rule body (both branches).
  Runs on the built interpreter: `?НАЙТИВСЕ(Т, годится(Т), L)` gives
  `L=[молоток,отвёртка,тиски,струбцина]` for `;` and for the two clauses, but
  `L=[молоток]` for `ПЕРВОЕ`; a separate listing is about an alternative in the
  middle of a rule where the common «tail» used to be repeated (`со_скидкой` in
  two writings gives `L=[молоток,тиски]`).  The phrase in §17, cut off by the
  user's edit, was fixed too.  The messages about `;` where dialect 1.0 accepted
  it as a terminator, and about a missing dot, became prescriptive: «предложение
  должно заканчиваться точкой» (it was «не заканчивается»; the first wording,
  «предложение заканчивается точкой», the user rejected back in task_40) — a
  change in `parser.cpp`, two tests and the quotation in §16 of
  `prologd-diff.typ`.

* The same day, continued: **a missing dot is seen not only at the end of the
  file** (task_56).  The user's observation: with two facts in a row and no dot
  at the end of the first (`студент(вова, корчагин)` one line above
  `студент(данил, ахмеров).`) the output was `2:1: ошибка при разборе
  предложения`, and the helpful wording came only when the dot was missing from
  the very last clause.  The reason: a new line ends nothing, so the parser
  glued the two clauses together and stumbled on the name of the second — in the
  common branch of `parseClause`, where the message says nothing.  Now
  `beginsStatement(kind)` tells a token that can start a term/fact/rule/query
  from everything else: after a finished clause that means «нет точки», and
  `reportMissingDot()` shows the position at the *end of its own* clause (`1:42`
  in the example above, where `)` is the 42nd byte).  The same case in a query
  (`?- a(1)` × 2 lines) and in a rule.  The common wording stayed where the next
  clause cannot begin (`a(1), b(2).`) and where there is already an exact
  diagnostic (`p :- f(a "b").` — «непарные скобки»).  Checks:
  `студент(вова, корчагин)` + a second line — two new Catch2 cases (parser: fact,
  rule, query, «точка везде»; loader), ctest 276/276.

* The same day, continued: **the comparison table opens «Изменения языка», and
  Typst counts the section numbers**.  The user's request: move the table to the
  very beginning, as in the manual, and do without manual renumbering.
  The table is now the first section without a number
  (`#heading(numbering: none)`; the counter skips it, the chapters still start
  at 1), the headings have no digits (`#set heading(numbering: "1.")`), and
  references in the text take the number from the counter: `#sec(<sec:arith>)`
  and the like — `#ref` would also insert a word («Раздел 16»), but mid-sentence
  a number is needed.  Everything that used to be written by hand counted
  itself: `;` — section 14, `НАЙТИВСЕ` — 15, `ПЕРВОЕ` — 16, `\+` — 17, `is/2` —
  18 (in the text of §6/§12/§14/§16/§18 and in the table row).  Two inaccuracies
  as well: the «Дизъюнкция `;`» cell said «приоритет как у `,`», but in fact `,`
  binds *tighter* — the run `?НАЙТИВСЕ(X, (РАВНО(X, 1), РАВНО(X, 2) ;
  РАВНО(X, 3)), L).` gives `L=[3]` (in the reverse order it would be `L=[]`); the
  table now says «есть: `A ; B`, а `,` связывает крепче»; and `**сохранена**`
  (double stars in Typst emphasise nothing, only warn) became `*сохранена*`.
  The document was rebuilt: 22 pages, headings 1–19 with no digits in the
  source.

* Interpreter round, part 61: **`ПЕРВОЕ` takes any number of goals** (task_51,
  2026-10-02).  The answer to the user's question «right now `ПЕРВОЕ` has two arguments
  for us, is it hard to change it to any number, like `ВЫВОД`?», decided
  in favour of "arity 1 at minimum": in the whole pipeline (dispatcher, keyword table,
  call check, `--list-keywords`, the protocol event, completion) `variadic`
  already means "at least one argument", so no second field appeared anywhere.
  `builtinOr` became `builtinFirst` and walks `args` through `callOnce` — the
  first goal that has a solution is committed to; the hard-coded
  `isVariadicBuiltin` (two name comparisons) became the `kVariadicNames` table
  (`ВЫВОД`/`write`, `ПЕРВОЕ`/`first`), read by `findBuiltin`, `builtinArities`
  and `builtinNames`, and the line `add("ПЕРВОЕ", 2, …)` and `add` no longer lean
  on two names.  Two-argument calls answer as before, `;` is still disjunction,
  and the parser, engine, lexer and `checks.cpp` are untouched.  A check found
  one inaccuracy in the task statement itself: a one-argument `ПЕРВОЕ(Ц)` is a
  *commitment* to the first solution, not `ВЫП(Ц)`
  (`?НАЙТИВСЕ(X, ПЕРВОЕ(p(X)), L).` → `L=[1]`, while `ВЫП(p(X))` gives
  `L=[1,2]`), and the manual §4.6 now says so.  Arity 0 is a load error
  («ПЕРВОЕ не имеет арности 0», code 2).  The manual §4.5/§4.6,
  `technical.typ`, §«`ПЕРВОЕ` вместо `ИЛИ`» and the table row in
  `prologd-diff.typ`, `doc/builtins.json` (`arities: []`, `variadic`),
  `ai/porting_notes.md`, `gui/README.md`.  Checks: 278/278 ctest (a new Catch2
  case for variadics and the CLI test `ПЕРВОЕ/+`), six GUI suites
  (`test_reference`, `test_completion`, `test_keywords`, `test_queries`,
  `test_tokens`, `test_queryline`) green, three documents build with Typst.

* Interpreter round, part 62: **comparison signs are sugar over built-ins**
  (task_52, 2026-10-02).  The answer to «the same + ISO comparisons»: `=`, `<`, `>`,
  `>=`, `=<` are not new names but a second writing of `РАВНО`, `МЕНЬШЕ`,
  `БОЛЬШЕ`.  In `parser.cpp` there is one `kInfixOperators` table (`=`→`РАВНО`,
  `<`→`МЕНЬШЕ`, `>`→`БОЛЬШЕ`, `=<`→`НЕ(БОЛЬШЕ)`, `>=`→`НЕ(МЕНЬШЕ)`) and one
  layer between `#…#` and everything else: the signs bind tighter than `,` and
  `;` and looser than `#…#`, the chain `0 < X < 10` is a parse error with a
  single message (««<» — не цепочка: разбейте на два сравнения, «A < B, B < C»»),
  and `skipToTerminator` keeps the parser from saying the same thing a second
  time about «непарные скобки».  Everything below knows nothing about the signs:
  the dispatcher, call check, `--list-keywords`, the protocol and
  `doc/builtins.json` see the same predicates, so `НЕ(X = 1)`,
  `НАЙТИВСЕ(X, (X = 1), L)`, `ВЫП((X = A))` and `r([A = B])` parse without a
  single engine change.  Four things turned up along the way.  (1) **The number
  rule.**  The ported writing `1.` = 1.0 ate the terminator: `?2 > 1.` did not
  parse at all.  The user's decision is the ISO rule: `1.` is the integer `1`
  plus a dot, a real is written `1.0`; this is the only place in the task where
  the language changes (`#1.#` no longer loads), and it is recorded in `help.typ`
  §3.2 and in `prologd-diff.typ`.  (2) **`#…#` is an operand.**  `parseTerm`
  returned `parseArithmetic()` prematurely on `#`, and `r(#1 + 1# = 2)` fell with
  «непарные скобки»; now the operand is taken by `parseOperand`, and there is a
  test for it.  (3) **The hints are in the lexer** (`kForeignOperators`, longer
  writings first: `=:=`, `=\=`, `\==`, `\=`, `==`, `@=<`, `@>=`, `@<`, `@>`,
  `->`, `<=`): a foreign writing is explained where the sign stands, and
  `?X <= 1.` begins with ««<=» — не оператор: «меньше или равно» записывают
  «=<»», not with «Цель не может быть переменной».  (4) **GUI — highlighting
  only**: the signs became the `OPERATOR` kind, while `Ctrl+=` stayed on
  `РАВНО(`, as the user decided, so `shortcuts.py` did not change.  A weak spot
  left on purpose: `X < 2+1` (without `#…#`) gives the generic «ошибка при
  разборе предложения» — a hint about `#…#` could be added there separately, as
  with `is`.  The manual: `help.typ` §3.2/§3.3/§4.7/§5.1 and the table rows,
  `prologd-diff.typ` §9 and three rows of the «Краткая таблица», `technical.typ`,
  the variants in `doc/builtins.json`; lessons 3 and 4 got an example with the
  short writing (the user's decision: «both lesson 3 and lesson 4») — their `%!` lines
  are a golden answer to themselves, so `test_lessons.cpp` did not change.
  Checks: 285/285 ctest (seven new cases), 21 GUI suites (`test_*.py`) and
  `protocol_smoke.py`, five PDFs; the `test_queries.py` counters had to be
  refreshed — the lesson 4 edit in task_51 added a question (`24` → `25`) and the
  suite was already red on HEAD, and this round's examples shifted two more
  (`03`: `34` → `37`, `04`: `25` → `27`): the GUI suites must be run after any
  change to `examples/`.

* Interpreter round, part 63: **`ВЫВОДПС`/`writeln`** (task_53, 2026-10-03).
  The third variadic predicate — and the first check that the name table from
  task_51 really is data: the name, the English pair and «хотя бы один
  аргумент» cost two lines in `builtins.cpp` plus words in `kReservedBuiltins`,
  and the body is `builtinWriteLine` next to `builtinWrite` (the same loop plus
  one `newline()`; a second call per goal is not needed, `ВЫВОД` does not fail).
  Arity zero stayed with `ПС`, so there is no second writing for «просто перевод
  строки».  What cost the most was not the program but the numbering: §6.3 is new
  (the place was chosen by the user: right after `ПС`), everything from 6.3 to
  6.9 shifted by one, and the numbers also lived in three more places — a
  reference in `prologd-diff.typ` («таблица кодов»), the lesson 7 comments and
  the plan `task_54_input_stream.md`.  All three were fixed in the same round:
  the `section` of every `doc/builtins.json` entry must be a heading of the
  manual, so `test_reference.py` would have caught the mismatch — but only after
  the edit.  Lesson 7 shows the short writing (`?ВЫВОДПС("Сумма: ", 5).`), its
  counter in `test_queries.py` — `19` → `20`; in the English-names appendix the
  entry landed by itself (`ВЫВОДПС — writeln`).  Checks: 290/290 ctest (three new
  Catch2 cases and two CLI), `--list-keywords` — 110 names, 21 GUI suites and
  `protocol_smoke.py`, five PDFs, pages 16–18 and 33 looked at.

* Interpreter round, part 64: **the shell answer is a chunk of the input stream**
  (task_54, 2026-10-03).  There are four input sources — a file (`-i`,
  `ЧТЕНИЕ_ИЗ`), the standard stream, a `$` line of the source and the shell
  answer — and all but the last were read through `std::getline`: a line is what
  lies between two `\n`.  The answer, though, was put into the buffer whole, so
  it was in the window that `ВВОДСТР` returned `\n`s as text, the remainder
  after `ВВОДСИМВ` began with `\n`, and `ВВКОД` read code 10 between lines: a
  program verified against a file behaved differently in the window.  Now the
  chunk belongs to the stream — `IoContext` keeps its remainder and hands out one
  line at a time, asking the shell only when the remainder runs out.  The rest
  are consequences: `a\n` is one line, not a line and an empty one (the next read
  goes to the user); `""` — one empty line, as before; `а\n\nб` gives exactly what
  the same bytes in a file give, and this is pinned by two reads — from the chunk
  and from a temporary file.  The second item is the BOM: `stripByteOrderMark` at
  three entry points (the first line of the base stream, the first file of
  `ЧТЕНИЕ_ИЗ` and each chunk), because `Notepad` puts the mark into a new file by
  itself, and code `65279` as the first character of a line is not what a
  schoolchild expects; in the middle of a chunk the mark stays data.  The edit
  turned out to be in exactly one place: neither the solver, nor the call checks,
  nor the protocol changed (`input.text` could always contain `\n`), and the old
  test about the input handler did not catch this — in it every entry was one
  line.  The documents moved wider than the code: ADR-023, `technical.typ` §10,
  `help.typ` §6.5 (BOM) and §6.8 (the window chunk), `gui.typ` §6.1 — a paragraph
  described the window before task_50 («поле ввода под панелью вывода», a menu
  item that no longer exists) and promised that «ответ на `ВВОДСТР` может быть
  фразой»; now the exact meaning is there — one phrase is several lines of input.
  Plus `gui/README.md` and the «Спрашивать ввод» setting hint, which also called
  the field «под выводом».  Checks: 305/305 ctest (8 `IoContext` cases, 7 through
  built-in predicates, one case in `protocol_session.cmake` — two lines in one
  answer give one `input_request`), a GUI check with a «предатель» dialogue (the
  second line must not reach the window), five PDFs.

* I/O round, part 65: **a failed `ЗАПИСЬ_В` left the output on a closed stream**
  (task_57, 2026-10-03).  It was found while working on task_54, looking at
  `IoContext` as a whole: `openOutput` closed the current file **before** trying
  to open the new one, and `output_` was assigned only on success, so after a
  failed switch it stayed on the closed `file_output_`.  Writing to a closed
  `std::ofstream` is lost silently (the `badbit` flag, which nobody watches), and
  not only what the program printed disappeared but also **the interpreter's
  answers**: `ДА`, `НЕТ` and the bindings are printed by the same `IoContext`.
  This was hard to notice precisely because there is no diagnostic: `ЗАПИСЬ_В`
  is honestly false, and the output simply stops appearing.  The class's
  neighbour behaved correctly: a failed `ЧТЕНИЕ_ИЗ` returned reading to the
  keyboard, because `fetchLine` looks at `input_from_file_`, not at the stream
  pointer.  The fix is one line (`output_ = base_output_` right after the close):
  a failed switch returns the stream to where it would be without it.  The
  option «открыть сначала, потом закрывать прежний» was rejected — it would
  silently ignore the request, leaving the program writing to the previous file.
  Checks: a reproduction on the built `prologd.exe` (before the fix the `НЕТ` of
  the failed switch and the whole following goal disappeared), two new Catch2
  cases — through `ЗАПИСЬ_В`/`ВЫВОД` and at the `IoContext` level — and one
  sentence in `help.typ` §6.9 about where the output returns.  ctest 307/307.

* GUI round, part 66: **five requests about the window** (task_58, 2026-10-03) —
  and one broken suite at the start.  `test_icons.py` went red: the user redrew
  and renamed the icons, and the code and `assets.MISSING` did not follow them —
  and it noticed only the *extra* name (`view-split-editor` is drawn but stayed
  in the «ещё не нарисовано» list), while missing two lost pictures entirely:
  `view-output-right`/`view-output-bottom` were in the same list, so «есть файл
  или записано в MISSING» passed, and «Панель вывода» with «Сменить ориентацию
  сплита» stood quietly without icons.  The upshot: 49 names, 48 drawn, one
  `view-theme` waiting.  Then four things about how the window talks to the
  reader.  **`Shift+Del`** became a command (`delete_line` in the table, the
  «Удалить строку» item in «Правка», without an icon — `edit-del` is taken by the
  «Удалить» command): the line is taken whole, the caret goes to the first column
  of the shifted line, a selection removes all the affected lines but not the one
  it stopped at the start of, the last line of the file empties (a document cannot
  be left without a block) — and all of that with one `Ctrl+Z`.  **Occurrence
  highlighting** of the selected word: light `#e8ecf5` → `#cfe0f7`, dark `#2d3038`
  → `#3a4a63`.  The second number matters more: 15 units of lightness from the
  page `#1e1e1e` is «тускло», and it is the dark palette that a dark desktop gets
  through the «системное» appearance.  It was not measured before:
  `Palette.readable_pairs` checks the contrast of *text*, not of a backing with a
  background; now `test_appearance.py` has such a measurement too, so that
  «тусклое» does not come back silently.  **The «база знаний загружена» line**
  now appears after a click on a question marker in the margins, too: an early
  `return` in `_on_loaded` waited for the answer and carried the line away with
  it; now it is printed on `loaded` (before the `return`), and the order matches
  `F5`.  **Menu and panel**: the manual rose under «Справку по предикату», in
  «Выполнение» two switches `run_questions` and `print_questions` replaced
  `save_before_run` and write the same settings the dialogue shows
  (`_sync_actions` returns the value into the tick), the manual was removed from
  the panel, and the font size moved after «Настройки…».  **«О программе»**
  became «Графическая оболочка Пролог-Д 2.0» with the same АБВГД list of
  authors; the `--` column is aligned with spaces (the user's decision — no rich
  text), and the test checks that the `--` position is the same in all five
  lines.  Checks: three new `test_editor.py` cases, the backing measurement in
  `test_appearance.py`, four new requirements in `test_window.py`; ctest 307/307,
  all 21 GUI suites and `protocol_smoke.py`, five PDFs.

  **Follow-up after the first look.**  The user found what my check did not: in
  the editor `Shift+Del` did not work, while from the menu item it did.  The
  tests called the `delete_lines()` method instead of pressing the key, so they
  were green with a broken key.  The cause is somebody else's: `QTextControl`
  grabs `Shift+Del` as the platform writing of «Вырезать» (on Windows it is the
  second way, next to `Ctrl+X`, to write it), so a `QAction` with its own
  `Shift+Del` does not reach the editor, and the key itself arrives in
  `keyPressEvent` — where, with no selection, it did nothing.  The key is now
  handled in the editor, and the check presses the key.  Then three requests
  about the panel and the menu: the font-size field was removed from the panel
  entirely (scale is the wheel with `Ctrl` and three commands, the exact value is
  a settings row), «Очистить вывод» moved from the panel into «Выполнение» above
  «Графическое окно», and in «О программе» `--` was replaced by the en dash `–`.
  A rule about the ellipsis in an item title was recorded as well: it means «the
  command will ask something first» and is not put on one that acts at once (even
  if it opens its own window).  Two more small things from the same place:
  `Shift+Del` puts the deleted lines into the clipboard (the key took the
  platform meaning «вырезать» — what is cut must be pasteable), and the
  `edit-clear` icon of «Очистить вывод» was deleted together with its file: the
  drawing did not read as «очистить», and the item stayed textual (48 names, 47
  drawn, one `view-theme` waiting).

* GUI round, part 67: **the answer table** (task_59, 2026-10-03).  Option C, chosen
  by the user: the table is given to a separate query — a goal in the query line or
  a click on a question marker in the margins — while a whole run (`F5`) has no
  table and cannot have one: the answers of all a program's questions go into the
  text as one ribbon without separators.  The user showed this on his own example
  (two facts, `?студент(X, Y).`, `?цена(X, Y).` — six lines of output), and this
  also explained his yesterday's question about «running files with many
  questions»: not a defect but an impossibility to separate one answer from
  another by the text.  For the table to exist for a whole run too, the
  interpreter must send solutions as separate data — a `bindings` field in the
  `result` event (option B: edits to `protocol.cpp`/`protocol.py`,
  `protocol_session.cmake`, README and tests); recorded in `doc/gui.typ` §10, not
  done now.

  What is in the window: the fifth tab «Таблица» after «Ввода» (the title counts
  the solutions — `Таблица:3`), the «Выполнение → Формировать таблицу» switch
  above the two question switches of task_58, and the same
  `execution/answer_table` row in the dialogue, off by default.  The answer is
  assembled from the output of that single query: `_append_output` is the only
  funnel, and only `OUTPUT` lands in it (the «база знаний загружена» line is
  `NOTE`, errors are `ERROR`).  Collection has to start from the moment the query
  is sent, not from `loaded`: at a marker the program loads quietly, and the load
  output may arrive after the query — the shape rule saves it.

  The whole rule lives in the new Qt-free module `answers.py` (and is checked by
  `test_answers.py` without Qt): a binding is a line `Имя=значение`, where the
  name is a variable by the lexer's rules (`is_upper_letter` or a leading `_`, as
  in `tokens.py`) and the value is the rest of the line verbatim; **a repeated
  name starts a new solution** — this is exact, because `engine.cpp::runQuery`
  prints all the query's variables in its order and within one solution a name
  cannot repeat; the columns are in order of appearance.  From there too, from
  `runQuery`, follows the shape of the answer of a goal with no variables: `ДА`
  once or `НЕТ`, and within one query a word is not mixed with bindings — that is
  why `ДА`/`НЕТ` occupies one cell in the table with the title «Ответ», not a
  separate kind of empty tab.  Everything that does not look like a binding
  (printed by the program inside the answer) is `ignored`: it does not enter the
  table, it stays in «Вывод».

  Small things without which it would be worse: `Ctrl+C` over the table copies
  the selected cells (columns by tab, rows by newline) — `_copy` copies "from wherever
  the user is looking" and without a case for the table it would take the
  command off to the editor; a new run and `Ctrl+L` clear the table (it is a view
  of the last answer, not a history); diagnostics leave the panel on «Проблемах»,
  while the table waits on its own tab.  The table takes the output font size, the
  `zoomChanged` signal and the wheel with `Ctrl` — that is, `_apply_output_font`
  is now about five panes, not four.

  Checks: the new `test_answers.py` (12 cases: bindings, a repeated name,
  `ДА`/`НЕТ`, a program-printed `ДА` next to bindings, junk lines, an empty
  value, CRLF, names with `_`), nine cases in `test_window.py` (the switch in the
  menu and in the settings; the table at a marker and at the query line; two
  solution lines on the user's example; `ДА`/`НЕТ` in one cell; the switch off
  does nothing; diagnostics keep «Проблемы»; a run and `Ctrl+L` clean; the font
  size; `Ctrl+C`), and `test_the_panel_has_four_tabs_with_counts` became
  five-place.  A trap that cost one red run: `wait_for_result` waits for a word in
  the status line, and it holds the word of the **previous** answer — for a second
  query in one test `not window._busy` is needed.

* GUI round, part 68: **a question after the load** (task_60, 2026-10-03).  The
  user asked what happens when the line `?0 < 5 < 4.` is run — the window shows
  two errors, «от файла» and «от query».  It was analysed on the built
  interpreter: a click on a marker makes **two** requests — a quiet load of the
  file (`questions=false`) and the question itself as a separate `query` request.
  `questions=false` means "do not *run* the program's own `?` statements", but
  the file is still parsed whole, so the chain of comparisons is reported by the
  load, naming the file (a separate query has the name `<query>` — that is how
  the protocol tells «ошибка в файле, строка N» from «ошибка в присланной
  строке», task_36).  The query line does no load at all — there is one error
  there; if there was an `F5` before it, the file's error stays in «Вывод» next
  to the new one (only `run_program` cleans the panes).

  On the way something worse was found: a file that did not parse loads no base
  **at all** (the loader parses the whole text before adding anything), yet the
  question was still sent — and got the answer «НЕТ» plus the warning
  «`<query>:1:2: не найдено: факт/1`», that is, a wrong answer with an honest
  face and a complaint about the query instead of the file.

  The fix (the user's decisions): a marker asks **after a successful load**
  (`_pending_query`, sent from `_on_loaded`; a load error drops the question with
  a line in «Системе»), and the query line does not re-read the program — there
  is one base, and the goal asks the loaded one — but it loads the current text
  if there is nobody to ask (`_loaded` false).  The double error is gone by
  construction, «НЕТ» on an empty base no longer appears, and an error found in a
  question's comment still arrives once and is called `<query>`.  Documents:
  `gui.typ` §4.2 and §6, README (markers and the query line); checks — five new
  `test_window.py` cases.

* Documentation round, part 69: **five documents — shorter, tidier and with a
  correct number** (2026-10-03).  The user's requests: shorten `gui.typ`, check
  `technical.typ` for consistency (no shortening needed) and lower the title
  closer to the centre of the page.

  `gui.typ`: 1 103 lines → 956.  Every section has a short lead-in and then
  bullet points; all the hard facts stayed (48 icon references and 47 drawn,
  keys, settings keys, measured numbers, section references).  A check for words
  with mixed alphabets also found in §6.1 «dве строки» (a Latin `d`) — such
  words are no longer in the file.

  Two chapters were removed from `prologd-diff.typ` («`->` — не оператор» and
  «`is/2` — подсказка вместо оператора»): the document speaks only of the
  differences from the original Пролог-Д, and neither it nor the new
  implementation has those operators.  Their content moved to `help.typ`, which
  compares with ISO-Пролог, SWI-Prolog and GNU Prolog (§3.3 — `is/2` and two
  hints instead of an operator, §4.6 — «если-то» through `ПЕРВОЕ` next to
  `(Условие -> Тогда ; Иначе)`), and the old implementation is not mentioned
  there.

  `technical.typ` was not shortened but was put in order.  §1 «Постановка задачи»
  was dropped, sections 2--10 became 1--9, while the last two kept their old
  numbers — now they are 10 «Тестирование» and 11 «Ограничения», with no gap in
  the numbering; «раздел 5.6» and «см. 5.6» lead where they should.  **A number
  that turned out to be an artefact was fixed:** «полное сканирование 100 000
  предложений ≈ 20 мс» came from subtracting two runs that both scan the whole
  list (a query with no variables under `ТИХО` keeps looking for solutions after
  the first — `Engine::runQuery`), so the difference was noise.  Re-measured on
  this machine: loading 100 000 facts 0.25 s, and the scan — 1 000 clauses
  0.3 ms, 10 000 — 3.7 ms, 100 000 — 54 ms, that is ≈ 0.5 µs per failed attempt;
  with cut-off right after the call it is visible directly (`г(1)` without `!`
  costs as much as `г(0)`, with `!` — zero).  Fixed in `technical.typ` §5.7 and
  §11, ADR-017 and the task_42 report.

  In the same round: `lessons.typ` — a short `= 1. Как устроен урок` with run
  commands instead of two introductory sections, the numbering shifted; and the
  title in all five documents was lowered — before the title block stands
  `#v(6cm)`, that is about 40 % of the page height instead of the very edge.

  Checks: all five documents build (`typst=0`), first pages looked at.

* Documentation round, part 70: **the example program in the window and variable
  names in the lessons** (2026-10-03).  The user's requests: change the welcome
  program to `% пример программы` with `студент('Вова', 'Корчагин')` and the query
  `?студент(Имя, Фамилия).`, give the lessons' variables meaningful names where
  that helps the reader, and close the rough edges found while working with the
  window.

  The welcome program: quoted atoms (a capital without quotes is a variable,
  lesson 1), the variables are `Имя` and `Фамилия`.  The program is checked by
  running it: `Имя=Вова`, `Фамилия=Корчагин`, `Имя=Данил`, `Фамилия=Ахмеров`, no
  diagnostics, and it is already in canonical form (`prologd --format` changes
  nothing, that is, `Ctrl+I` does not rewrite the first text the user sees).  The
  window tests no longer look for the `% PrologD` prefix but compare the tab text
  with `WELCOME` itself; the same example (facts + two questions in a row) now
  stands in `gui.typ` §6.5 too — it shows why the table is built only for a
  separate query.

  Lessons: variable names were replaced with words where a variable has a role —
  `дед(Дед, Внук)`, `сумма(Предел, Сумма)`, `фак(Число, Часть, Факториал)`,
  `нод(Первое, Второе, Нод)`, `фиб(Число, Фибоначчи)`, `член(Элемент, [...])`,
  `НАЙТИВСЕ(Имя, студент(Имя, Фамилия), Список)` and so on through all the
  lessons.  The capitals «Х», «У», «_» and the coordinates `Х1`, `У1` are kept
  where they are indeed «любое значение»; the letters Д, К, М, Н in the runners
  problem — because the prose calls them by name, and the Cyrillic/Latin pair
  `Х` and `X` in the appendix — the very subject of item 2 of section 4.  Each
  edit dragged along `%!` lines (the answer prints the *name* of the variable),
  the prose that named the letters, and the text of the exercises with answers.

  Along the way: `examples/lib/library.pld` and `import_demo.pld` got the same
  names (`удвоить(Число, Дважды)`), followed by the regexp of the `cli_include`
  test (`Дважды=42`) and the `test_queries.py` acceptance (`?сумма(5, Сумма).`),
  and the quotations of the lesson lines — in `examples/lessons/README.md`,
  `doc/gui.typ` §4.2, `src/gui/README.md` and the comments of `editor.py`.  Two
  small wording fixes: the third place of `УМНОЖЕНИЕ/4` is called a summand, not a
  remainder (lesson 3), and `встав/3` stopped being «Встав/3» (lesson 5).
  `ded(Д, В) → дед(Дед, Внук)` in the appendix: the trace prints the solver's
  `_1`/`_2`, so its `%!` lines did not change.

  Separately — a remark in lesson 3 (the user's request): `РАВНО` and its sign `=`
  are not an assignment as in imperative languages but unification (lesson 2) —
  for a free variable a choice of value, for a bound one a check.  The example in
  the remark was verified by running it: `?РАВНО(14, #2 + 3 * 4#).` answers ДА,
  `?РАВНО(15, #2 + 3 * 4#).` — НЕТ.

  Then the rough edges the user found while working with the window (he also
  suggested closing them).  **Lesson 10:** a click on a marker loads the file
  anew and runs exactly one question, so questions that need the actions of
  earlier ones answer against the wrong base.  Checked: `?дважды(4, Итог)` gives
  НЕТ and the warning «не найдено: дважды/2» (the rule is created by the line
  `?ДОБ(...)`), and `?прим(Остался)` — quietly something else (`Остался=1`,
  `Остался=2` instead of `Остался=3`, `Остался=2`).  The behaviour was not
  changed (it is the decision of task_36/59: only the asked question must have an
  answer), an explanation was added to §4 of the lesson and to the pointer in the
  header.  **Lesson 11:** the module search directory is now described for the
  window first — «Настройки → Выполнение → Дополнительные каталоги ИМПОРТ»
  (`execution/import_paths`; every run raises a session with `-I`, so an added
  directory acts from the next «Запустить»), the `-I` key second.  **Lesson 7:**
  it is explained likewise that in the window the answers are typed in the
  console under the goal line or in the queue field, and the file
  `lesson_07.input.txt` is needed only by the command line.  The same
  explanations — in `examples/lessons/README.md` (the sections «Как читать урок»
  and «Вопросы на полях») and in `doc/lessons.typ` §1.

  Analysis of the user's question about the directive: `:- ДОБ(...)` has no marker
  at all (the rule accepts only `?` lines), and a click on a neighbouring question
  does not run it — the quiet load goes without a query runner, that is, it adds
  only clauses to the base.  Checked: `?дед(аня, Y).` on a click answers НЕТ and
  «не найдено: дед/2», while on F5 — `Y=витя`.  In `help.typ` §11 this was not
  written (its example is true for the console and for F5); `:- ИМПОРТ` is an
  exception, the loader itself parses it, so lesson 11's markers work.

  Checks: ctest 307/307; all 13 lessons run and verified against their `%!` (in
  the appendix — the warning «не найдено: любит/2», as its section 4 promises),
  every file byte-for-byte equal to the output of `prologd --format`; the question
  count 278 in 33 programs; 22 suites `src/gui/tests/test_*.py` and
  `protocol_smoke.py`, which must be run with `.venv\Scripts\python.exe` (the
  system `python` without PySide6 drops seven of them on
  `No module named 'PySide6'`); `docs` (five documents, `typst=0`).

* Planning round, part 71: **task_61 — a portable Windows build** (2026-10-03).
  The user's request: one folder for a clean machine — the window, the
  interpreter, the documents, the examples; and the question of which tool.  The
  task was written up (`ai/task_61_portable_windows_build.md`, M17, a row in
  `plan.md` §5 and on the board), the facts checked on this machine: `prologd.exe`
  is 944 KiB and imports `VCRUNTIME140.dll`/`MSVCP140.dll` (the UCRT is part of
  Windows 10+, these two DLLs are not), the UTF-8 manifest is baked into the
  image (`/MANIFESTINPUT:src/utf8.manifest`), the build-tree path did not get
  into the exe; in the window three paths are computed from the source tree
  (`default_executable`, `assets.DEFAULT_DIRECTORY`, `_open_document`);
  PyInstaller 6.22.3 supports Python 3.14 and PySide6, but neither it, nor Nuitka,
  nor cx_Freeze is installed.  The user's decisions: PyInstaller `--onedir`; the
  Visual C++ DLLs go alongside; `_old` is not included, `.typ` is; `gui.ini` in
  the portable build sits next to the exe (in the others — AppData, as now);
  `examples/lib` is written in at once; the folder `prologd-2.0.0-win64` and a
  zip.  The installer is the next task.

* Packaging round, part 72: **task_61 — the first frozen build** (2026-10-03).
  §4 was done: `prologd_gui/paths.py` answers two questions (the folder next to
  the exe in a build, the repository root in the sources; `sys._MEIPASS` for the
  icons), and the interpreter, icons, documents, settings, the ИМПОРТ row and —
  fourth, which the task did not have — `doc/builtins.json` for `F1` were moved to
  it; checks: `test_paths.py` (seven cases with substituted
  `sys.frozen`/`sys.executable`/`sys._MEIPASS`) and a case in `test_window.py`;
  all 23 GUI suites green, ctest 307/307.

  §2–§3 were done on the first pass: PyInstaller 6.22.3 was installed into `.venv`
  (`src/gui/requirements-build.txt` — separate from the student
  `requirements.txt`), the `--onedir --windowed` build takes 27 s and gives
  112.9 MiB in 252 files (`prologd-gui.exe` 2.3 MiB, in `_internal/assets` all 47
  icons).  The folder `dist/prologd-2.0.0-win64` — 297 files, 116.3 MiB: the
  window, `prologd.exe` and the three Visual C++ DLLs alongside, five PDFs with
  their `.typ` and `builtins.json`, `examples` without `lessons/_old`, the memo
  `ЧИТАЙ_МЕНЯ.txt` (from `tools/portable-readme.txt`).

  Checked: `tools/check_dependencies.py` parses the import table of every .exe and
  .dll of the distribution and answers «every non-system import is a file of the
  package» (the list of system DLLs was enlarged by what turned up in fact:
  `icuuc.dll` — ICU from Windows 10, `d2d1`/`dwrite`/`d3d12`/`uiautomationcore` —
  Qt backends); the window from this folder starts, finds the interpreter
  alongside and creates `gui.ini` next to itself, writing its `examples/lib` into
  `execution/import_paths`; `prologd.exe --version` = `2.0.0`, `--list-keywords`
  = 122 lines (110 names), the output of lesson 1 matches the `%!` lines.  During
  the check this was found and fixed: in a `--windowed` build there is nowhere to
  print, so «нет prologd.exe рядом» now speaks through the window rather than a
  line in stderr; the junk `doc/style.pdf` was removed from the tree (a leftover
  of a target that once built `style.typ` as a document) — it had got into the
  first build.

* Window round, part 73: **the answer table is on by default** (2026-10-03).  The
  user's request: «Формировать таблицу» must be on from the start, not waiting
  until it is found in «Выполнении».  Changed where the default is recorded: the
  line `Setting(ANSWER_TABLE, …)` and the `answer_table` property in `settings.py`
  (both read `False`), the documentation (`src/gui/README.md` — both the «Таблица
  ответа» section and the paragraph about the menu; `doc/gui.typ` §6.5 got a
  paragraph about the default and about the panel moving to the tab) and the check
  `test_the_answer_table_switch_is_in_the_menu_and_in_the_settings`, which held
  the old default: now it starts from a switch that is on and checks turning it
  off.  The table's behaviour did not change: it is built only for a separate
  query (the query line or a marker), the answer text still goes to «Вывод»,
  diagnostics leave the panel on «Проблемах», and an empty answer does not switch
  the tab.

  The same day the user checked the portable build on **a clean Windows 11 in
  Windows Sandbox, 24H2 26100.9457**: «it started and works».  This is §7.5 of
  task_61 — the only check that cannot happen on the developer's machine (here the
  Visual C++ DLLs are in `System32`, so a forgotten DLL cannot be seen).

* Portable round, part 74: **the portable build and moving the folder**
  (2026-10-03).  The user's question: `examples/lib` was written into
  `execution/import_paths` on the first run, but the build will be copied (a USB
  stick → a computer → back), and the absolute path from the first run will
  become foreign.  The decision: write nothing.  The rule moved into
  `paths.import_directories(configured)` — a frozen build appends its own
  `examples/lib` **on every run and last**, the user's directories come earlier
  and win on a same file name; in the source tree the behaviour did not change
  (there the search is still only over what is configured).  `seed_import_paths`
  was deleted, `_import_directories` in the window is now one line, the checks
  moved to `test_paths.py` («находит ли сборка свой курс», «дерево ищет только то,
  что ему сказали»).  It was clarified there too that `--icons` defaults to
  `src/gui/assets` in the tree and to its own copy inside the build folder — in
  `src/gui/README.md` and in the `tools/portable-readme.txt` memo («папку можно
  переносить куда угодно»).

* Portable round, part 75: **Windows 10 confirmed, and why the first run is
  slower** (2026-10-03).  The user checked the build on **Windows 10 22H2, build
  19045.6456** — «it started and worked»; together with Windows 11 from the
  Sandbox these are both systems the task's §9 limits to (19045 ≥ 1903, so the
  UTF-8 manifest is understood).  There was also a question: why does the first
  run take about five seconds while the following ones are faster.  Measured
  here: in an already used folder the window is ready in 0.16–0.19 s, in a freshly
  copied one the first run is 0.43 s, then 0.17 s.  The cause is not ours: the
  first run of a new copy reads all 296 files (110 MiB) from disk, and the
  antivirus checks every `.exe`/`.dll`/`.pyd` once; afterwards everything comes
  from the OS cache, and the check is remembered.  Our own cost on the first run
  was measured and is negligible (`prologd --list-keywords` — 0.00–0.01 s,
  writing `gui.ini` — a dozen KB), and `--onedir`, unlike `--onefile`, unpacks
  nothing.  A way to cut the reading was recorded too: by subtracting with
  `--exclude-module` QML/Quick, `Qt6Pdf`, `Qt6VirtualKeyboard` and `Qt6Network`
  with TLS go away — about 27 MiB of 110; `opengl32sw.dll` (19.7 MiB) stays
  deliberately, it is the fallback software OpenGL for a machine without a
  driver.  The subtraction will be done together with the §6 script and checked by
  `tools/check_dependencies.py`.

* Portable round, part 76: **the user's lessons, `$` as input lines, `Shift+Enter`
  and cancelling the `examples/lib` substitution** (2026-10-03).  Three requests at
  once: corrected lessons, «do not supply `examples/lib`» and «forbid `Shift+Enter`
  in the editor».

  *Lessons.*  `ctest` caught two things in them.  In `lesson_01.pld` the line about
  the interchangeability of a string and an atom began with `$` — and `$` in a
  source file is **not a comment** but a line of pre-prepared input data:
  `ModuleLoader::extractInputLines` cuts it out of the text before the lexer, so at
  a run it disappears silently (`exit=0`, no diagnostics), and if the lesson read
  anything, those words would go into the program as answers.  It became visible
  only because `--format` (and `Ctrl+I` in the window) lexes the whole text and
  does not format such a file: «недопустимый символ».  Replaced with `%`; trailing
  spaces in comments were removed as well (`lesson_01` — 3 lines, `lesson_11` — 3),
  the formatter trims them, and «программа уже в стандартном виде» fell.  Two more
  typos in `lesson_11` — «Выполенение» and «ИМПОРАТ» — were fixed.  After the edit
  `ctest` 307/307.

  *`examples/lib`.*  The decision of 2026-10-03 (part 74) was cancelled by the user
  himself: the window substitutes **nothing of its own** into the ИМПОРТ search
  list.  Lesson 11 now says itself that the library directory must be added by hand
  («Правка → Настройки… → Выполнение → Дополнительные каталоги ИМПОРТ»), and that
  is **more transparent for the pupil** — he sees the row he filled and the path he
  chose.  `paths.import_directories` stayed, but only for cleanup: empty lines and
  duplicates.  Updated: `test_paths.py` (it used to be «сборка ищет свой курс», now
  «сборка ищет только то, что добавил ученик, и ничего своего»),
  `src/gui/README.md`, `tools/portable-readme.txt` (there is now a step «укажите
  `examples\lib`») and §4/§7.1/§8 of task 61.

  *`Shift+Enter`.*  It was measured exactly how it breaks the numbering: Qt inserts
  a **line separator** `U+2028` with it — the widget draws a new line while
  `blockCount()` does not count it (`\n` — 2 blocks, `\v`/`\f`/NEL/`U+2028` — 1,
  `U+2029` — 2), so the numbers and the question markers in the margins drift away.
  The interpreter rejects `U+2028`, `U+2029` and NEL altogether («недопустимый
  символ»), and counts `\v`/`\f` as spaces.  Now `Enter` and `Shift+Enter` are one
  branch in `CodeEditor.keyPressEvent` (an ordinary newline with auto-indent;
  `Ctrl`/`Alt`+`Enter` still go to Qt), and «вставка» does not bring a separator:
  `CodeEditor.insertFromMimeData` and `documents.read_text` fold `U+2028`/`U+2029`
  into `\n` (`tokens.plain_newlines`, with the measurement recorded).  Cases in
  `test_editor.py` («`Shift+Enter` — строка, которую полянка считает», «вставка не
  приносит разделитель») and in `test_documents.py` (including the order: folding
  before CRLF is determined).  The outdated «(раздел 9.3)» was removed from
  `doc/gui.typ` §9.2 as well — section 9.3 no longer exists.

* Portable round, part 77: **the build script, the Qt-module subtraction and the
  zip** (2026-10-03).  The last item of §6 of task 61 — `tools/build_portable.ps1` —
  was written and run end to end: Release → `ctest` 307/307 → `docs` (five PDFs) →
  PyInstaller → layout → checks → zip; the parameters `-Configuration`,
  `-CrtDirectory`, `-Version`, and for a short round `-SkipTests`, `-SkipFreeze`,
  `-NoTrim`, `-NoZip`.  The script itself checks what can be checked without a
  human: `prologd.exe --version` and 122 keyword lines, running lesson 1 and
  `import_demo.pld` with `-I examples\lib`, the absence of suspicious imports from
  `tools/check_dependencies.py` and starting the window in `offscreen` (it writes
  `gui.ini` next to itself — the file is then deleted, the distribution travels
  without it).

  *Subtraction.*  One `--exclude-module` is not enough: the module exclusions
  removed only the `qml/` directory (1.7 MiB), while the DLLs — `Qt6Qml`,
  `Qt6QmlModels`, `Qt6QmlMeta`, `Qt6QmlWorkerScript`, `Qt6Quick`, `Qt6Pdf`,
  `Qt6VirtualKeyboard`, `Qt6Network` — stayed: the PySide6 hook collects DLLs per
  package, not per module.  The script takes them out by name from the laid-out
  distribution (plus three plugins useless without them), and two independent
  arbiters judge this step: `check_dependencies.py` (the first run without it gave
  exactly two SUSPECTS — `imageformats\qpdf.dll` and
  `generic\qtuiotouchplugin.dll`, the very ones deleted) and the window starting.
  19.2 MiB in total; `libcrypto-3.dll` and `libssl-3.dll` stayed deliberately:
  they are pulled by Python's own `_ssl.pyd`, and breaking the pair for six
  megabytes was not worth it.  The package — **280 files, 95.4 MiB** (it was 297
  and 116.3), the zip — **37.5 MiB**.  The packaging decision is recorded in
  ADR-024, a reference to the script — in `README.md`.

  *The gotchas are recorded in the script's comments.*  `Get-ChildItem` with a
  wildcard inside the path returns the matches of that path, not the contents of
  the directory; `-Filter` with a Win32 mask did not find `Microsoft.VC*.CRT`
  where `Where-Object { $_.Name -like … }` did.  And the most insidious one: a loop
  variable named like a typed parameter of the script (`foreach ($version in …)`
  with `[string]$Version`) is converted to the parameter's type —
  `DirectoryInfo` became a string, `$version.FullName` was empty, and the error
  pointed at somebody else's line.  Now the variable is `$redistVersion`, and the
  header has a `trap` that prints the file and the line number.

* Documentation round, part 78: **the project and university emblems on the first
  page** (2026-10-04).  The user's request: put `prologd2.png` and `csu.png` side
  by side in the top-left corner of the first page of all the documents.  They are
  drawn by the common `logos()` function in `doc/style.typ` — `place(top + left,
  stack(dir: ltr, spacing: 4mm, …))` — and each of the five documents calls it with
  one line right after the page setup, before the indent in front of the title.
  `place` takes no space in the flow, so the centred title did not move (verified
  by a render).  Measured there too: an `image` in Typst is a **block** element,
  and in an ordinary line the icons stack one under another (both `#h()` between
  them and `box(a + h + b)` give a column) — only `stack(dir: ltr)` or `grid`
  puts them side by side; `stack` was chosen.  The icons lie in `doc/` (copies of
  `src/gui/assets/prologd2.png` and `csu.png`) so that the `doc` folder builds by
  itself: in the distribution both the `*.typ` and the icons travel next to the
  PDFs — the build script copies them and checks that they are in place.
  `doc/README.md` describes both the emblems and why they lie in this directory.

  Along with the emblems, the user's edits that lay in the tree were committed:
  in `doc/help.typ` mentions of SWI-Prolog and GNU Prolog were removed (the
  examples were rewritten to `если/2` and `Т = иначе`), in
  `examples/lessons/appendix_debug.pld` — the «Нужно знать» and «Как читать
  приложение» header (the same shortening as earlier in lesson 11).  After them
  `ctest` 307/307, `test_reference`, `test_queries`, `test_formatter` are green;
  the pages were verified by a render (the emblems — only on the first page).  The
  package was rebuilt: **282 files, 95.5 MiB**, the zip — 37.7 MiB.

* Documentation round, part 79: **`technical.typ` checked against the sources,
  and the listings fitted to the panel width** (2026-10-04).  The request: «check
  the whole `technical.typ` --- it seems the grammar diverges; maybe we could add
  more detail and more listings from C++».

  *The grammar really did diverge* — and not only from the code: §7.2 said
  `Факт ::= Терм ('.' | ';')`, that is, it counted `;` as the end of a clause,
  whereas it is a disjunction.  `doc/help.typ` §4.5 is right, and the lexer with
  the parser even more so: `;` in place of a dot gives the error «`;` ---
  дизъюнкция; предложение должно заканчиваться точкой».  The grammar was
  rewritten after `parser.cpp`: the end of a clause is only `.`,
  `Тело ::= Дизъюнкция`, `Дизъюнкция ::= Конъюнкция {';' Конъюнкция}`,
  `Цель ::= '!' | Терм`, `Терм ::= '\+' Терм | Сравнение`,
  `Сравнение ::= Операнд [Знак Операнд]`, and the arithmetic layer was written out
  in full (`Сложение`/`ЗнакСл`/`Умножение`/`ЗнакУм`/`Множитель`) — in the old
  grammar `Выражение ::= '#' Сложение '#'` referred to an undefined `Сложение`.

  *What else was inaccurate (checked against the code).*  `EnvNode` in §5.1 showed
  four fields of seven (no `depth`, `location`, `goalFrame` — and it is exactly
  those that explain how a step and diagnostics learn the depth and the place);
  `ChoicePoint` in §5.2 was described with the words «снимок цепочки сред, номер
  предложения, отметка trail и барьер», while in the code it is also
  `Kind::Clause | Kind::Alternative` (a disjunction is a choice point too) and
  holds `clauses`, `goal`, `goal_index`; the unification of an integer with a real
  was called «сравниваются по значению», whereas the code compares **exactly**
  (`BigInt::fromDouble`, not a cast to `double`) and remembers the story about
  `16777217` and `16777216.0`; the exponent (`1e3`) was not mentioned for a
  numeric literal; nothing was said about `\+` (one token, not a `\` sign with
  `+`), nor about the `kForeignOperators` table with hints for `->`, `<=`, `=:=`,
  `==` and `@…`, nor about the order of input sources (`$` lines, a `ЧТЕНИЕ_ИЗ`
  file, the front-end answer, the base stream), nor about `kCoordinateLimit`.

  *More listings.*  Nine were added: `Bindings`; two branches of `Engine::unify`;
  `advanceEnv`; `ChoicePoint`; the disjunction branch from `resolveGoal`;
  `releaseEnvChain`; `CompoundDeleter`; the internals of `BigInt` (base, digits,
  `divModMagnitude`); `ForeignOperator`; the search order in
  `ModuleLoader::resolve`; `fetchChunkLine`; the `GraphicsBackend` interface.

  *The panel width was measured.*  A panel line fits **62 characters** (verified by
  a render: 62 — on one line, 64 — already wraps), and a wrap in a listing looks
  like a dangling comment tail.  All the `technical.typ` listings now fit in 62
  characters (71 lines used to be longer), the rule is recorded in `doc/README.md`.
  In the other four documents the longest is 11 lines — these are Пролог-Д examples
  with aligned `%` comments, and there the wrapping stays as it was before the
  panels.

  *Terminology.*  At the user's request the phrases «привычный» and «обычный» about
  other Prologs were replaced with ISO-Пролог (the word was already in the
  documents, no new term is introduced).  Six places in all.  In `technical.typ`:
  «`call/2` обычного Пролога» became «`call/2` ISO-Пролога» (`call/2` really is in
  ISO-Пролог — see the standard's list of higher-order predicates), and the heading
  «два места, где эта грамматика не совпадает с привычной по учебникам» —
  «расходится с первоначальным Прологом-Д в сторону ISO-Пролога»: the first item
  is about `;`, which the *old* Пролог-Д accepted, so here it is actually a match
  with ISO, and calling that a divergence from ISO would be untrue.  In `help.typ`:
  «привычную запись правил» (the introductory paragraph), «привычные конструкции
  Пролога» in the header of the comparison table, «привычную по ISO-Прологу
  запись» (became «запись `X is 2 + 3`, принятую в ISO-Прологе») and «привычная
  запись ISO-Пролога» at `\+` (became «запись ISO-Пролога»).  The remaining
  «обычные» and «привычные» words in the documents are about ordinary things, not
  Prologs (`обычный размер шрифта`, «диагностика в обычном для компиляторов виде»,
  «обычная цель», «обычными `long long`», «привычная клавиша справки»), and they
  are untouched; in `prologd-diff.typ` «ISO-подобную или просто привычную по
  другим языкам» was left — there it is about other languages, not Prologs.  After
  the edit: `docs` built (exit 0), ctest --- **307/307**.

* Documentation round, part 80: **the `ai/` folder speaks English** (2026-10-04).  The user
  asked for it in one sentence — say in the README what the folder is for, bring everything in
  it to English, and merge the duplicate sections while doing it.

  *What changed first.*  `ai/README.md` now says up front that this is the working folder of
  the AI agent and **not** user documentation, adds a reading order for a human (plan →
  decisions → conventions → reference notes → status → task files) and spells out the language
  rule with its single exception: Russian survives only as *quoted data of the language under
  test* — built-in predicate names, interpreter messages, GUI labels and menu paths, program
  text and its output, and sentences quoted from the Russian manual.  The root `README.md`
  says the same in one line and points a contributor at `ai/`.

  *What was translated.*  Fourteen task files were rewritten in place — `task_29`, `task_35`,
  `task_39`, `task_44`, `task_51`, `task_52`, `task_53`, `task_54`, `task_56`, `task_57`,
  `task_58`, `task_59`, `task_60`, `task_61` — together with `status.md` (the whole journal,
  parts 28--79) and the two READMEs.  In seven more files only the quoted user requests were
  translated (`task_31`, `task_34`, `task_36`, `task_37`, `task_48`, `task_49`, `task_55`), and
  six Russian titles were put into English (`task_44`, `task_50`--`task_55`).  The remaining
  files were checked line by line and left alone: their Cyrillic is data — `НАЙТИВСЕ`,
  «непарные скобки», «Проблемы», `?длина(Х, 2)`, `lesson_07_данные.txt`.

  *Compressing on the way,* as the user asked.  Duplicated sections were merged (in `task_58`
  the five goal bullets, two "Decisions" lists and the follow-up round became one Decisions
  section plus a §6; in `task_29` the settings list absorbed the inline "done 2026-10-01" notes
  and the round's findings), and stale statements were corrected where they were found:
  `task_61` carried the package as it was before the emblems (280 files / 95.4 MiB / zip
  37.5 MiB) and now says 282 / 95.5 / 37.7, and its count of GUI suites is 23, not 22;
  `task_35` still said "plan (waiting for answers)" when the round was finished; `task_53`
  promised §6.2 for `ВВОДПС` where the user had chosen §6.3.

  *How it was checked.*  After every file a short script counted the lines that still contain
  Cyrillic and listed them, so that what remains is quoted data and nothing else; the two big
  passes over `status.md` were verified by hashing the ranges above and below the edited one,
  and the file's own line count moved by about 1 %.  Nothing reads `ai/`: no code, no document,
  no test, so the project's state is exactly what part 79 left — `ctest` 307/307, five PDFs,
  and the portable package as task_61 describes it.

  *Left for later:* the journal keeps its Russian *quotations* where they are evidence (what
  `help.typ` used to say, what a message printed), which is the one place the rule allows
  them.

* Language round, part 81: **the last `$` leaves the interpreter** (2026-10-05).  One request —
  remove `$` from the interpreter completely, it is an artefact of the old implementation and
  there is no reason to support it — and now nothing in the tree spells `$`: neither the
  `$`-lines of a source nor the internal `$expr` functor.

  *What the `$` lines were.*  The feature came straight from the original CLI, where
  `prologdc.cpp` had `constexpr char input_signal_char = '$'`: a source line beginning with `$`
  was taken out of the text before the lexer saw it (`ModuleLoader::extractInputLines`) and
  pushed into `IoContext` as a *preloaded input line*, which `fetchLine` served before the
  `ЧТЕНИЕ_ИЗ` file, the front-end and the base stream.  A test-harness convenience, kept in the
  port and written into `help.typ` (§6.8 and the CLI section), `technical.typ` (§8 and §9),
  `gui.typ` (the fresh-run sentence), the root `README.md` and the window's notes.  All of it is
  gone: `pushPreloadedLine`, the `preloaded_` deque, the branch in `fetchLine`,
  `extractInputLines` and both of its call sites — `loadFile` and `loadSource`, which had the
  same feature on stdin.  A line that begins with `$` now behaves like any other forbidden sign:
  `файл:2:1: error: недопустимый символ`, exit code 2 (checked by hand on the built exe).
  Reading has three sources left, in this order: the `ЧТЕНИЕ_ИЗ` file, the front-end's answer,
  the base stream (`-i` or stdin).

  *The internal `$expr`.*  The parser wrapped every `#...#` in a compound named `$expr`, and
  five places compared that literal — the parser, the engine, `asNumeric`, the arithmetic checks
  and the printer.  It is now `kExpressionFunctor = "#expr"`, defined once in `term.hpp` beside
  `kListFunctor` and `kNilAtom`, so the five copies of the string became one name.  It is still
  unforgeable by an identifier (`#` cannot start one), and the printer still evaluates a wrapper
  or writes `#_?_#`.

  *What else moved with it.*  `test_io_context.cpp` lost its `preloaded lines are served before
  the input request handler` case — the one test that pinned the feature — so the Catch2 count is
  289 (was 290) and `ctest` is **306/306** in about six seconds.  Statements in the notes were
  put right where they described *current* behaviour (`task_54`'s table, pseudo-code, Decisions 4
  and "What must not change"; ADR-023's context and BOM bullet; `task_21`, `task_28`,
  `reference_notes.md`), and the two check-list items that had asked for the feature (`task_11`,
  `task_16`) are marked *(dropped in part 81)*.  The `$` in the character-code table of
  `help.typ` stays: it is code 36 of a character, not the feature.  The journal's own history
  (part 76 and the `$` lines it mentions) stays too — that is what a record is for.

  *Verified.*  Release build clean; `ctest` 306/306 (5.8 s); `docs` exit 0 with the five PDFs
  rebuilt; and by hand — a `$` line is an error, while `?X = #1 + 1#, ВЫВОД(X).` still answers
  `X=2`.

* Language round, part 82: **three built-ins — `СОРТИРОВКА/2`, `ПОЛНЫЙ/1`, `ДЛЯВСЕХ/2`**
  (2026-10-05).  The user asked whether `bagof`/`setof` could be added and what else was worth
  adding; the answer took the form of an analysis of what this machine can and cannot do, and
  ended in three deterministic predicates.  The reasoning that refused `bagof`/`setof` is
  ADR-025; here is what was built.

  *The code.*  `СОРТИРОВКА` (`sort`) is a built-in in a new file `builtins_lists.cpp`: the list
  is walked with the tail dereferenced at every step, anything that is not a proper, acyclic
  list of comparable elements is refused, the *whole* list is checked before the sort (so the
  type error never depends on which pairs the algorithm happens to compare), the sort is
  `std::stable_sort`, equal neighbours are dropped with `std::unique`, and the second argument
  is unified with the result.  Its comparison is not a copy of `БОЛЬШЕ`'s — it *is* `БОЛЬШЕ`'s,
  now exported as `detail::compareOrder` and shared by both (the old `compareGreater` keeps its
  behaviour and its messages, and `test_builtins_arith` still pins them).  `ПОЛНЫЙ` (`ground`)
  is a type test in `builtins.cpp` whose walk carries the printer's path guard, so a term that
  contains itself answers `ДА` instead of walking forever.  `ДЛЯВСЕХ` (`forall`) is
  `Engine::hasCounterexample` — a nested solve over the condition with a callback that stops at
  the first solution whose action does not solve — and the built-in on top of it is two lines.

  *The five places, three times.*  Every name went into the dispatch table with its English
  alias (`sort`, `ground`, `forall`), into the lexer's reserved set (both spellings), into
  `doc/builtins.json` (63 records now), into `help.typ` (new sections 3.7 and 4.8, a line in 9,
  and four rows in the SWI/GNU table — including an honest "`bagof`/`setof`: нет"), and into
  `prologd-diff.typ` (rows in the short table plus a section with было/стало).  `checks.cpp`
  learned that both arguments of `ДЛЯВСЕХ` are goals, so a misspelled name inside them is a
  warning — without that the call-site check would have been silent (now pinned by a test).

  *What the tests say.*  Ten new Catch2 cases: `sort` over numbers, over text (an atom and a
  string in one list), the `1`/`1.0` case, the unification of the second argument, and six
  refusals (mixed types, a compound, `[1 | 2]`, a non-list, a free variable, and a list that
  contains itself — the one a plain walk would follow forever); `forall` in five shapes plus
  "a number is not a goal" and the call-site warning; `ground` over the term kinds, the
  cyclic term included.  `ctest` is **316/316** (Catch2 299 plus the 17 CLI tests), and the GUI
  checks pass unchanged — `test_reference.py` now covers 63 records over 116 reserved names and
  knows the new `lists` group.

  *The lessons.*  `lesson_05` gained section 9 «Готовая сортировка» (its intro no longer claims
  that `СПИСОК/1` is the only list built-in), and `lesson_10` gained «Полный ли терм» and «Для
  всех» with a `хранить/1` guard in front of `ДОБ`, two exercises and two summary bullets.  Both
  lessons stay machine-checked: every new `%!` line was taken from a run of the built
  interpreter, and `test_lessons` compares the whole output.  The course tables
  (`doc/lessons.typ`, `examples/lessons/README.md`) name the new predicates in lessons 5 and 10;
  `doc/technical.typ` says why `ПОЛНЫЙ` reuses the printer's cycle guard, that `ДЛЯВСЕХ` is a
  nested solve, and that `СОРТИРОВКА` and `БОЛЬШЕ` share one order.  Nothing was renamed and no
  name collided: the course sorts with `вставсорт/2` and `быстрсорт/2`, which are not reserved.

* Examples round, part 83: **the examples folder gets a map and a `problems/` shelf**
  (2026-10-05).  The user asked to reformat `examples/*`: add examples for the predicates the
  dialect gained (`ПЕРВОЕ`, `СОРТИРОВКА`, `ПОЛНЫЙ`, `ДЛЯВСЕХ`), and put `factorial`, `monk*` and a
  new knapsack under `problems/`.

  *What moved and what is new.*  `factorial.pld`, `monk.pld` and `monkd.pld` moved into
  `examples/problems/` (with `git mv`, so the history follows) and got a header comment saying
  what the program is and how to run it; `problems/knapsack.pld` is new — subsets by recursion,
  the best one as «нет более дорогого» (the double negation of lesson 4), and the feasible sets
  collected with `НАЙТИВСЕ` and printed as a list.  Beside them sit four demos, one per
  predicate: `first_demo.pld` (the commit, and «если — то — иначе» as a rule), `sort_demo.pld`
  (the order, the repeats, the check by unification, `НАЙТИВСЕ` + `СОРТИРОВКА` as a set),
  `ground_demo.pld` (the whole term, the cyclic term, the guard in front of `ДОБ`) and
  `forall_demo.pld` (no counterexample, and the same thing written with `НЕ`).  Each carries
  `%!` lines, and `examples/README.md` is the map of the folder.

  *They cannot go stale.*  `test_lessons.cpp` grew a second golden test — `the example programs
  print what their comments promise` — over a new `checkedExamples()` list (`first_demo`,
  `sort_demo`, `ground_demo`, `forall_demo`, `problems/factorial`, `problems/knapsack`), with
  the comparison itself extracted into `checkPromises()` so lessons and examples share one
  implementation.  `problems/monk.pld` draws and `problems/monkd.pld` reads input, so those two
  stay in the parse-only list.

  *Three traps, all measured.*  Python's `write_text` made every new file CRLF on Windows, which
  the lesson checker rejects (a stray `\r` would end up in the expected text) and the formatter
  then rewrites; and a hand-written program is not in *the standard shape* the formatter
  produces, so the idempotency sweep failed on the first demo.  The routine for a new example is
  now: write it, then run `prologd --format -s file` and keep the output — `%!` lines are
  comments and survive it untouched (verified by comparing them before and after).  The third
  came from the window suite: `test_a_run_uses_the_tab_that_is_showing` builds its second tab by
  replacing `(6,Ф)` in the factorial example, and the canonical spelling has a space in
  `(6, Ф)`; the test now comments the example's `20!` query out as well, because `720` is a
  piece of `2432902008176640000`.

  *Every reference, once.*  The moved paths were followed through the docs and the tooling:
  `src/tests/test_lessons.cpp`, `src/gui/tests/test_window.py`, `doc/help.typ`,
  `doc/prologd-diff.typ`, `doc/lessons.typ`, `doc/gui.typ`, `src/gui/README.md`, `panels.py`,
  `examples/lessons/README.md`, the root `README.md`, `tools/portable-readme.txt` and the
  packaged-file check in `tools/build_portable.ps1`.  Older notes in this folder still name the
  old paths (`task_18_examples_acceptance.md`, parts 40, 41 and 76) — they are the record of
  what was true then.

  *Verified.*  `ctest` 317/317 (the new golden test is the 317th), the window suite green
  (`all window checks passed`), and `docs` exit 0.

* Standard library, part 84: **a `stdlib` folder, and the old `lists` ported into it**
  (2026-10-05).  The user asked to start the library the dialect ships: one folder in the root,
  which will travel beside the executable; the first PrologD `lists` adapted to it; a comment
  above every predicate and a blank line after its group; argument names that mean something;
  and anything writable better written better.

  *The name.*  `stdlib`, not `lib`: the folder *is* the standard library, the documents call it
  «стандартная библиотека», and the project has an `examples/lib` for lesson 11 already — two
  `lib` folders in one package is a question every reader asks once.  The files keep the Latin
  predicate names of the first library (`member`, `length`, `append`, …) with Russian argument
  names (`member(Элемент, Список)`): the names come from the library being ported, the course,
  the comments and the readers are Russian.

  *Three files.*  `lists.pld` — membership, length, edges, neighbours, min/max, append, reverse,
  flatten, delete/delete_all/select/permutation/substitute, prefix/suffix/sublist, print_list,
  read_numbers; `sets.pld` — set, unique, subset, equalset, unionset, intersect, difset;
  `sorts.pld` — selectsort, insertsort, bubblesort, quicksort, mergesort, treesort and their
  helpers.  The second and the third `:- ИМПОРТ` the first, so importing `sorts.pld` alone
  brings the whole library, and the folder is now on the formatter's sweep.

  *What the port had to change.*  `first/2` could not stay: `first` is the English name of the
  built-in `ПЕРВОЕ`, and a clause under a built-in name is never called — the engine answers
  with its own predicate and the clause is dead without a word — so the first element is
  `head/2`.  `больше/2` and `меньше/2` are gone: the built-ins compare, and since part 82 they
  share one order with `СОРТИРОВКА`, so a list of strings sorts the same way everywhere.
  `flatten/2` is a difference-list traversal (one pass instead of the old quadratic `add/3`
  chain) and its last clause asks `НЕ(СПИСОК(...))` — without that test a nested list has two
  readings and the predicate answers thirteen times where it has one answer.  `min_list/2` and
  `max_list/2` are tail-recursive with an accumulator and choose with `ПЕРВОЕ` instead of a cut;
  `intersect/3` and `difset/3` are one `НАЙТИВСЕ` over two `member` goals plus `СОРТИРОВКА`,
  where the old library had three mutually recursive helpers; `set/2` is now `СОРТИРОВКА` itself
  (unique and ascending — the old one kept the order of *last* occurrences, which no reader would
  guess), with `unique/2` as the order-preserving variant.  Argument order is consistent (the
  list first in `delete/3`, `delete_all/3`, `substitute/4`, as it already was in `select/3`), and
  `heapsort` was dropped: its `mergeheap` called `СЛУЧ` to choose a subtree, and a sort that
  answers differently on every run has no place in a library.  `stdlib/README.md` carries the
  `old name -> new name` table for programs written against the first library.

  *The demo is the test.*  `examples/stdlib_demo.pld` runs every predicate of the library and
  carries its answers as `%!` lines; `checkedExamples()` gained it, the golden test now hands the
  run `-I stdlib` (through a new `PROLOGD_STDLIB_DIR`) and `examples/stdlib_demo.input.txt` for
  `read_numbers` — the lesson `<name>.input.txt` idea extended to the examples.  The `%!` lines
  were measured, not typed: every question was run on its own and its output pasted, which is how
  `mergesort`'s wrong-way-round comparison in my first `merge/3` showed up as `[3,2,1,1]`
  instead of `[1,1,2,3]` — the demo earned its keep before it was committed.

  *Two traps.*  `create_file` writes CRLF on Windows and `prologd --format` keeps the file's
  line endings, so all four new files had to be converted to LF before the format sweep and the
  lesson checker would have them — the same trap part 83 hit from the Python side.  Worse,
  `src/gui/tests/test_queries.py` was **already red** when this round started: its `PINNED` table
  still named `factorial.pld`, `monk.pld`, `monkd.pld` and the counts lessons 5 and 10 had before
  the `ДЛЯВСЕХ` round, so it had been failing since parts 82 and 83 — `ctest` does not run that
  script and nobody looked.  The table is refreshed (39 programs, 351 questions) and the script
  is green again; `ai/conventions.md` already warned about this check and now has a second
  example of ignoring it.

  *Shipped.*  `tools/build_portable.ps1` copies `stdlib` into the package, expects
  `lists.pld`/`sets.pld`/`sorts.pld` among the needed files and runs the demo from the unpacked
  folder with `-I stdlib -i …`; `tools/portable-readme.txt` says what the folder is and how to
  add it to the window's ИМПОРТ list.  Nothing is seeded into that list behind the reader's back
  (the standing decision from part 74), so the reader adds `stdlib` themselves — the demo's own
  header says how, next to lesson 11's instruction.  The root `README.md` gained a «Standard
  library» section and a layout line, `examples/README.md` the new row.

  *Verified.*  `ctest` 317/317, `test_queries.py` green, the window suite green, and the
  formatter idempotent over both shipped folders.





* Standard library, part 85: **the library is found without a flag, and it grew**
  (2026-10-05).  Seven suggestions from my part-84 list came back answered "да" — goals
  as arguments (`map`, `filter`, `fold`), strings, `msort`, access by number, integers,
  a document, and a default search path — with one correction: the user asked for
  `head_n`, not `first_n`.  That correction is right for a reason worth remembering:
  `first` is the English alias of the built-in `ПЕРВОЕ`, and a name that stands next to
  it invites the mistake part 84 described.

  *The search path (ADR-026).*  `prologd.exe` now searches a `stdlib` folder beside
  itself, last: after the importing file's folder and after every `-I`.  The rule is
  `standardLibraryDirectory(directory)` — a pure function of the directory, with the OS
  lookup (`GetModuleFileNameW`, `/proc/self/exe`) kept apart — so the two new tests
  exercise it in a temporary folder instead of copying an interpreter anywhere.  The
  portable build now runs `stdlib_demo.pld` **without** `-I`, which is the promise kept
  where it counts: on the machine of someone who only unpacked the zip.

  *What joined the library.*  `lists.pld` gained `nth/3` (and `/4` with a counter, which
  no longer builds arithmetic on the way back), `head_n/3`, `last_n/3` (through
  `reverse` and `head_n`), `sum_list/2`, and the goal-taking `map/3`, `filter/3`,
  `fold/4` — each with its accumulator form, because that is the shape the library
  already had.  `sets.pld` is untouched; `sorts.pld` gained `msort/2`, the counterpart
  of `СОРТИРОВКА` (sorted, repeats kept, and the file's other sorts are now described as
  what they are — the study versions).  `strings.pld` is new: `trim`, `trim_left`,
  `trim_right`, `words`, `join` (space, any separator, accumulator), `replace`,
  `to_number`/`to_numbers` and `read_words`.  `math.pld` is new: `between`, `gcd`, `lcm`,
  `power`, `factorial`, `is_prime`, `primes`.  The three predicates part 84 pushed to
  "next round" — `split`, `чиспис` and `вводсписка/1` — are now `words/2`,
  `to_numbers/2` and `read_words/1`.

  *Two traps, both caught by measuring.*  `head_n` was wrong in the least interesting
  way: the base case demanded an empty list at counter zero, so "the first two of three"
  failed while "the first three of three" worked.  And `to_numbers` handed a non-text
  argument to `СТРЦЕЛ`, which answers a *type error* rather than a failure — the first
  element of the list decided whether the predicate failed politely or stopped the run.
  `СИМВ/1` in front of the conversion fixed it and the piece became `to_number/2`, which
  is worth having on its own.  Neither was found by reasoning; both were found by
  running the extended demo and reading what it printed.

  *The demo learned to recount its promises.*  It reads from its input file twice now
  (`read_words`, then `read_numbers`), so measuring each question on its own is wrong —
  the answers belong to a stream.  The measurement runs *prefixes* instead: the n-th
  answer is what the first n questions printed beyond the first n-1, and the finished
  file is compared with a whole run once more.  Sixty-two questions, eighty recorded
  lines.

  *A document, and a test that keeps it honest.*  `doc/library.typ` is the sixth
  document: what the folder is, how it is found, one table per file with every predicate
  and its arity, and a short «что менялось» section.  A reference that has fallen behind
  is worse than none, so `src/tests/test_stdlib.cpp` extracts `name/arity` from every
  clause head in `stdlib/*.pld` (bracket-depth aware, continuation lines skipped) and
  requires each to appear in the document — 96 of them today.  `stdlib/README.md` keeps
  the map and the `old name -> new name` table and now points at the document instead of
  repeating the list of predicates.

  *Verified.*  `ctest` 319/319 (the two new module-loader tests included), the library
  document's 96 assertions, `test_queries.py` green after a `PINNED` refresh (62
  questions in the demo), the window suite green, and `typst compile doc/library.typ`
  with a look at four of its ten pages.

* Standard library, part 86: **one space after a sentence, and `tail` beside `head`**
  (2026-10-05).  Two small things from the user, both about the library's own text.

  *Spacing.*  The library's files now use a single space after a sentence-ending period,
  the way the user asked.  The `.pld` files could not simply be edited by hand:
  `prologd --format` keeps a comment it does not reflow, so double spaces survived in
  exactly the lines that fit on one line, while `lists.pld` looked clean only because
  the formatter had reflowed it.  Four spots needed the hand — two in `sorts.pld`, one in
  the demo's header, one in `doc/library.typ` — and the `.typ` file is not the
  formatter's business at all.  Verified the only way that means anything: `--format`
  over every library file afterwards says `canonical` for all six, and the demo still
  prints exactly what its comments promise.  The rest of the repository (the course, the
  other documents, the user's own files) keeps its two spaces — they asked for the
  library, and the library is what changed.

  *`tail/2`.*  The user asked whether `last/2` should be called `tail/2`, since the pair
  of `head` is `tail`.  No: in this dialect's own comments `Хвост` is what follows
  `[Голова|Хвост]`, so `tail` would name the *rest* of the list, not its last element —
  and `last/2` is the standard name for that.  The pair the question was really after
  now exists: `tail/2` was added next to `head/2`, and `last/2` keeps its name.  The new
  predicate has its line in `doc/library.typ` (the completeness check would have failed
  without it) and its own question in the demo — sixty-three questions now, with the
  recorded answers still measured.

  *Verified.*  `ctest` 320/320, `test_queries.py` green after a `PINNED` refresh, and the
  six documents rebuilt.

* Documentation, part 87: **the `$` item dropped, and the «не A, а B» turns trimmed**
  (2026-10-05).  Two requests from the user.

  *Item 13 is gone.*  The section about `$`-prefixed input lines left
  `doc/prologd-diff.typ`.  The document lost exactly one page (26 -> 25), its following
  sections renumbered, and a search for quotations of those numbers found only the
  historical notes in `ai/` ("`prologd-diff.typ` §15" in `task_39_english_aliases.md`,
  and the journal itself) — they stay as the record of what was true then.  Nothing in
  the user documents referred to them: the two "раздел N" references that look like
  candidates (`gui.typ` §14, `technical.typ` §7.1) point at `help.typ`, whose numbering
  did not move.

  *The contrasts.*  The user's rule: phrases shaped «это не A, а B» / «это A, а не B»
  become plain statements of the fact.  The documents were swept for the *rhetorical*
  shape — the one that names what something is not before saying what it is — and
  eighteen of them were rewritten: `help.typ` (the definition of `;`, `ИМПОРТ` as a
  directive, `НЕ(…)` as a real goal, `\+` as a second spelling, the empty line, the
  rebuilding of lines, the limit), `gui.typ` (highlighting types and alphabets, output in
  batches, the colour readout, the answer table, why `F5` builds none), `technical.typ`
  (the disjunction is not a predicate) and the library's own texts (`library.typ`,
  `stdlib/README.md`, `strings.pld`, the demo header, `examples/README.md`).

  *What was kept, and why.*  A trailing qualifier that carries information stays: «в
  символах, а не в байтах», «неудача, а не ошибка», «в момент загрузки, а не в момент
  ответа», «по скан-коду, а не по символу» — there the negative half is a fact the
  reader needs, not a flourish.  `prologd-diff.typ` keeps its «добавка, а не замена»
  rows for the same reason: contrast is that document's genre, and the sweep left it
  alone.

  *Layout.*  Prose edits were checked to be layout-neutral rather than assumed: every
  document was rendered from both revisions and its page count compared — `help` 37,
  `gui` 31, `technical` 23, `library` 10, unchanged; `prologd-diff` 26 -> 25, exactly the
  removed section.  The junction page in `prologd-diff` (where section 13 now starts) was
  looked at: the heading sits at the top of a page, with nothing orphaned.

  *Verified.*  `ctest` 320/320, the demo still prints its promises, the library files are
  still canonical for `--format`, and the six documents build with exit 0.

* The window, part 88: **«Проблемы» is a table, and a row leads to its line**
  (2026-10-05).  Four requests from the user, all about reading a failure.

  *The table.*  The tab used to be a text pane fed with `*** parse: файл:2:8: …` lines;
  it is now `panels.ProblemsPane`, a `QTableWidget` with the columns «Тип», «Место» and
  «Сообщение».  The data was already there and was being thrown away: `_on_failed`
  receives kind, severity, message and position as fields of their own (protocol 3), and
  the window was putting them back together into a line that the next front-end would
  have had to parse apart again.  A row keeps the `Position` it came with, so the tab can
  *do* something with it: `problemActivated` carries it to the editor, which opens the
  file when it is not among the tabs, marks the line and puts the caret on it (the same
  road a fresh diagnostic takes).  «Тип» names an error the way the interpreter does
  (`parse`, `runtime`, `protocol`) and a warning as «предупреждение»; a row is coloured
  by severity, red or amber, and a theme change re-colours the rows already there.

  *A long message wraps.*  `setWordWrap(True)`, the message column stretched to the free
  width, and `resizeRowToContents` after every added row.  The rows are measured again
  120 ms after a column drag stops — a re-wrap is a layout pass per row, so it waits for
  the hand to let go — and on every resize of the pane.

  *The place is short.*  The old line already carried the full path, which is exactly what
  pushes the message off the screen.  The column shows `documents.short_path(файл,
  parts=1)` — `…\модуль.pld:2:15` — and the whole path travels in the cell's tooltip.
  `problems_text()` renders the rows back into the log the pane used to hold
  (`*** kind: file:line:column: message`, a warning under its own word), so every reader
  of that text — the window's own checks and the suite — kept working unchanged.

  *The settings list.*  «Настройки → Выполнение → Дополнительные каталоги ИМПОРТ» showed
  the *beginning* of each path (`C:\Users\vasla\…`), which is the same for all of them
  and hides the folder that was added.  The list now elides from the left
  (`Qt.TextElideMode.ElideLeft`) and each row carries the full path as its tooltip; Qt
  elides while painting, so a wider dialog reveals more of the path with no code of ours.

  *A trap worth recording.*  The pane's first version emptied itself with `reset()` — a
  *virtual* method of Qt's view — and `clearContents()`, the obvious body, calls back into
  it.  The result was a `RecursionError` inside the C++ call and a table that quietly
  ended up empty (the theme check found it: «no row 0»).  The method is now
  `clear_problems()`, and it empties the table with `setRowCount(0)`; `_reload()` does the
  same, and the note in `notes.md` says why.

  *Verified.*  `test_window.py` «all window checks passed» — with a new check: the three
  columns, the wrapping row, the shortened place with its tooltip, and the double-click
  that marks the line of the file that failed; `test_settingsdialog.py` green with the
  elide mode and the tooltip asserted; `ctest` 320/320; the six documents build with exit
  0.

* The console, part 89: **a runtime error names its place, in the console too**
  (2026-10-05).  A question from the user — «если в `library.pld` есть ошибка, мы её не
  увидим?» — turned into a check of every way an imported file can fail.

  *What was already true.*  A file that does not parse, that is missing, or that fails
  inside a nested import is reported with *that* file's name, line and column, and the load
  stops with exit code 2; the same diagnostic reaches the window as an `error` event
  carrying `file`/`line`/`column`, so the tab of the imported file is opened and the line
  marked.  A warning (an unknown predicate inside the module) is amber and changes nothing.
  `examples/lib/library.pld` itself runs clean — exit 0, no diagnostics.

  *The gap.*  A *runtime* error was printed as `error.what()` — the message alone: `деление
  на ноль` with nowhere to look, in the main file and in an imported one alike.  The place
  was known all along: `Engine::raise` puts `current_location_` (the clause being solved)
  into the `PrologError`, which is exactly what the protocol sends to the window, and
  `DiagnosticSink::format` already printed `file:line:column: error: message`.  Both catches
  in `src/cli/main.cpp` now use it, so the line reads
  `…/lib.pld:1:1: error: деление на ноль` and an error inside an imported file names that
  file in the console as well as in the window.  The exit code stays 3.

  *Pinned.*  `cli_diagnostics.cmake` gained a fourth promise — a runtime error exits 3 and
  names its clause, matched on the ASCII part of the line (`cli_runtime.pld:1:N: error:`),
  because `execute_process` decodes the child's output with the build console's code page —
  and `test_window.py` gained «a runtime error in an imported file opens it and marks its
  line», the other half of the promise the parse-error check already covered.

  *Documentation.*  `doc/help.typ`: the paragraph about a failed directive and the list of
  what a place points at now say that a runtime error carries a place too, and that the
  place is the clause that was being solved, wherever it lives.

  *Verified.*  `ctest` 320/320 (with the new case), `test_window.py` «all window checks
  passed», the six documents build with exit 0.

* The window, part 90: **a double-click brings the file's tab to the front**
  (2026-10-05).  A request from the user: «двойной щелчок по строке проблемы ещё
  открывал таб с нужным файлом, если таба нет — открывал сам файл».

  *What was missing.*  The click already took the editor to the line: the row keeps the
  `Position` it came with, `_diagnostic_buffer` finds the open tab or opens the file, and
  the line is marked with the caret on it.  What it did not do was *show* that tab —
  `show_line` moved the caret inside a view that another tab was covering — so a click on
  a diagnostic from a file the run itself had opened looked like nothing happened.
  `_open_problem` now calls `active_pane().set_current(buffer)` before the mark, which
  covers both halves at once: the tab that exists behind another file, and the one that
  had to be opened at all (every pane shows every open document, so the active pane always
  has it).

  *What moves the eyes, and when.*  A diagnostic never switches to a tab that is
  *already* open: it marks the line where it is, so a run cannot pull the user out of the
  program they are reading.  A file it has to *open* is shown at once, because showing
  what it opens is what opening a file does — the rule since task_50 — so the click and
  the diagnostic agree there.  The click is the one act that raises the tab of a file
  that already exists, which is exactly the case that used to leave the user looking at
  the program while the line was marked in a tab they could not see.

  *Pinned.*  The double-click check in `test_window.py` now pins the whole order: the run
  opened the module and marked line 2 (and it is showing, since opening shows a file),
  then the module's tab is hidden behind the program's and the click brings it back
  without opening the file a second time.  The «runtime error in an imported file» check
  (part 89) pins the diagnostic's half of the rule: the line is marked, and the file that
  had to be opened is the one showing.

  *Documentation.*  `doc/gui.typ` and `src/gui/README.md` describe the click in order:
  the file is opened if it is not open, its tab comes to the front, the line is marked.

  *Verified.*  `test_window.py` «all window checks passed», `ctest` 320/320, the six
  documents build with exit 0.

* The window, part 91: **a GUI pass — one duplicated body out, two tables on one base**
  (2026-10-05).  The user asked for a refactoring review: duplication, inaccuracies, and
  anything worth moving to a file of its own.

  *Duplication removed.*  Two instances, both in the window's tables and panes.

  - «Очистить вывод» and the clearing at the start of a run were the same six lines written
    twice under two docstrings.  `_reset_panels` now delegates to `clear_output`: one body,
    two names — the button, and the start of a run.

  - `TablePane` and `ProblemsPane` each carried their own `zoomChanged` signal, their own
    clamp-and-apply `set_font_size` and their own `Ctrl`+wheel handler — and the details had
    already drifted: the answer table emitted `zoomChanged` from `set_font_size` and kept one
    default row height, the problems table emitted it only from the wheel and re-measured its
    wrapping rows.  Both now subclass one `ZoomableTable` in `panels.py`: the signal, the
    clamped font, the wheel and the `font_size` accessor live in the base, and the single
    difference — how rows follow a new font — is the subclass's `_relayout_for_font`.

  *Inaccuracies.*  None user-visible were left: the stale comments the pass expected had
  already been rewritten in parts 88–90.  The real drift was behavioural — the two
  `set_font_size`s above disagreed about when to emit — and the shared base removes it by
  construction.

  *What stays put.*  The modules are cut along their seams (one file per concern: the editor,
  the panes, the tables and text panes, the buffers, the settings dialog, the session).  The
  one candidate for moving — the «where does a diagnostic point» block in `window.py`
  (`_diagnostic_buffer`, `_mark_error_line`, `_mark_trace_line`, `_open_problem`) — is ~120
  lines glued to the buffers, the panes and the status bar: splitting it off would import
  half the window back again, so it stays.  `ZoomableTable` is UI and belongs in `panels.py`
  beside its two users, not in a file of its own.

  *Verified.*  `test_window.py` «all window checks passed».

* The window, part 92: **the goal field's own switch, and a run that shows the panel**
  (2026-10-05).  Two requests from the user — and one trap the first of them walked into.

  *The goal field is a panel.*  The goal line and the console under it were two widgets
  stacked in the editor column; they are now one `QWidget` (`_query_panel`), because the new
  «Вид → Панель ввода цели» (`view/query_visible`, on by default) hides the two together —
  an answer box under nothing would be a puzzle.  The entry sits after «Панель вывода» in
  the menu and in the dialog's «Вид» section, and the panel is remembered the way the output
  panel is (`isHidden` rather than `isVisible`, so a window that was never shown does not
  read as hidden).  The console is that panel's second half, so the «Спрашивать ввод» rule
  grew the obvious third case: with the goal field hidden there is nowhere to put the
  console, and the question comes as a dialog — the fallback `F4` already had.

  *A run shows the output panel.*  `run_program` — and a goal typed into the line — reveals
  the output panel when the user had hidden it, because a run has output to show and a
  hidden panel made the answer look like nothing happened.  The *preference* is not written:
  `view/output_visible` stays as the user left it, so the next start begins with the panel
  hidden again — the rule the followed font size already follows (task_58), where a side
  effect of running writes nothing and only the user's own act does.

  *The trap.*  The first version of the reveal called `_sync_actions`, and the checkable
  entry's `setChecked(True)` emitted `toggled`, which ran its own handler — the one that
  *writes* the preference.  The user's «hidden» was overwritten by the act of showing the
  panel for a run, silently, and the new test caught it («the run wrote the preference»).
  `_sync_actions` now sets every checkable entry through `_set_checked`, which blocks the
  signal: the entry follows the state, the preference does not move.  The same trap existed
  in every `apply_settings` before this — harmless only because the value written back was
  the one just read.

  *Tests.*  `test_window.py` gained «the goal field hides from the menu, and a run shows the
  hidden output panel»: the switch and its persistence over a reopen; a run with both panels
  hidden revealing only the output one and writing no preference; a goal typed into the line
  doing the same.  Two older checks had hidden the output panel to force a question into a
  box, which a run no longer allows: «the dialog is the last resort» now presses `F4` *in the
  middle of* a run — the first question still has its armed console, the second finds the
  panel gone — and «cancelling input stops the run» hides the *goal field* instead, which is
  the third reason a question comes as a box and the one a run does not undo.

  *Documentation.*  `doc/gui.typ` (the layout, the goal line, the console's order, the
  dialog's rows and the menu) and `src/gui/README.md` (the goal field, the console, the
  settings table).

  *Verified.*  `test_window.py` «all window checks passed»; `test_settings.py`,
  `test_settingsdialog.py` and `test_shortcuts.py` green; the six documents build with
  exit 0.

* The window, part 93: **the goal panel is a strip again** (2026-10-05).  A report from the
  user: after part 92 the goal line shared the editor column's height with the editor, half
  and half.

  *Why.*  The switch of part 92 put the line and its console into one `QWidget`, and a plain
  `QWidget` has no vertical wish of its own: the editor column has room to spare, so the
  layout handed the new panel half of it and the line floated in the middle of a tall empty
  strip.  That is exactly the defect the *console* had before task_50 — its check even says
  so («its one field floating in the middle of a tall empty strip») — and the cure is the one
  it got then: a size policy.  `_query_panel` now asks for `Preferred`/`Maximum` (the pair
  `StepPane` and the find bar already use): as tall as its contents — the line, plus the
  console while a question waits — and not a pixel more.

  *Pinned, and measured.*  The part-92 check now shows the window and asserts both the
  panel's vertical policy and that its height is its own `sizeHint`, the shape the console's
  strip check has had since task_50.  The defect was reproduced by the hand as well: with the
  policy the strip is 24 px and the editor column 341 px; put back to a plain widget's
  `Preferred`/`Preferred`, the strip becomes 137 px and the column drops to 228 px — the
  editor lost a third of its height to a line of text.

  *Verified.*  `test_window.py` «all window checks passed».

* Version 2.1.0, part 94: **the first bump of the port's own number, and a package to go
  with it** (2026-10-05).  The user asked how a version is raised here, then chose 2.1.0.

  *One source, everything else reads it.*  The version lives only in
  `CMakeLists.txt` (`project(prologd VERSION …)`); CMake injects it into the generated
  `version.cpp`, and from there it reaches `--version`, the `ready` event of the protocol
  (the window shows it in «О программе» and in the status bar and keeps no copy) and the
  built-in `ВЕРСИЯ/0`, which prints it with `PROLOGD_BUILD_DATE` — the date CMake stamps
  when it configures, so a bump is a reconfigure.  The protocol number stays its own
  counter (11) and did not move.

  *The live copies of the literal moved with it* — found by grepping, not by memory:
  the `cli_version` test's `PASS_REGULAR_EXPRESSION` in `src/tests/CMakeLists.txt` (ctest
  fails without it), the example line in `examples/lessons/appendix_debug.pld`, the `ready`
  example of `src/gui/README.md` (where the protocol number had been stale at 10 for two
  protocol versions — now 11) and the default package path of `tools/check_dependencies.py`.
  The `ai/` notes that quote 2.0.0 (task_61, the ADRs, the journal) are records of what was
  true then and stay as they are.

  *The rule, written down.*  A «Versioning» section went into `ai/conventions.md`: the
  single source, the separate protocol counter, the grep-the-literal checklist, and the
  release routine of task_61 and `tools/build_portable.ps1`.

  *The package.*  `tools\build_portable.ps1` was run end to end: Release build → `ctest` →
  `docs` → PyInstaller for the window → `dist\prologd-2.1.0-win64` (**299 files,
  96.0 MiB**) → its eight check stages (the packaged `--version`, the keyword list, lesson
  1, the import demo and the standard library, every non-system import a file of the package,
  the packaged window starting and writing no `gui.ini` beside itself) →
  `prologd-2.1.0-win64.zip` (**37.9 MiB**).  The folder is named from
  `prologd.exe --version`, which the script reads itself and checks again inside the
  package, so nothing had to be passed to it — and the older `prologd-2.0.0-win64` pair stays
  in `dist/` beside the new one.

  *What the script does not do.*  Its last lines list the checks left for a person (task_61
  §7.1/§7.5): copy the folder somewhere else, open a lesson and press `F5`, click a margin
  marker, `Shift+F1`/`F1`, and try the folder on a machine without Visual Studio.

  *Verified.*  `prologd.exe --version` → `2.1.0`; `?ВЕРСИЯ.` → `PrologD 2.1.0 (2026-10-05)`;
  `ctest` 320/320; the portable script reached «Ready: …\dist\prologd-2.1.0-win64».

* Colour becomes `0xRRGGBB`, part 95: **the 0…15 palette goes, and the names move to the
  library** (2026-10-06).  task_63, asked for by the user.

  *What was already true.*  The engine never knew a palette: `GraphicsColor` is the colour
  *value* the program wrote, and only `src/gui/prologd_gui/graphics.py` turned a value into a
  pixel — reading anything above 15 as `0xRRGGBB` and everything below as an EGA entry.  So
  the change is subtractive in the window and additive in the library.

  *The engine guards the argument now.*  `builtins_graphics.cpp` gained `colour(...)` beside
  `coordinate(...)`: an integer in `0`…`0xFFFFFF`, or a `TypeMismatch` whose message names the
  range and the value («Цвет вне диапазона 0…16777215: 16777216»), and every colour argument
  of `ТОЧКА`/`ЛИНИЯ`/`ОКРУЖНОСТЬ`/`ЗАКРАСКА` goes through it.  The window had been masking,
  so `0xFF0000` and `0x1FF0000` drew the same pixel and still compared unequal on a read;
  instead of the mask, a value that is not a colour is refused.  Probed by hand: all four
  predicates exit 3 with that message, and `16777215` passes.

  *The names are a library file.*  `stdlib/graphics.pld` (the sixth file) holds `rgb/4` and
  eighteen colour names, each one an `rgb/4` call, so a colour has one definition that the
  library and the window's reader share.  `rgb/4` works both ways and is written as two
  guarded clauses: three components compute the colour, a bound colour gives the components
  back (`?ТОЧКА(X, Y, Ц), красный(Ц)` is a question, not a drawing).  The guards are
  load-bearing — an arithmetic expression over a free variable is an *error* in this dialect,
  not a failure, so without `ЦЕЛ(...)` the second clause could never be reached.  A call that
  leaves both the colour and a component free fails plainly: there is no generator for
  «colours like that» here.

  *The examples read like programs again.*  `examples/lessons/lesson_12.pld` and
  `examples/drawing.pld` bind the names (`жёлтый(Мяч), ОКРУЖНОСТЬ(Х, У, 10, Мяч)`) and the
  prose that taught «1 — чёрный, 4 — синий» is gone — it had been wrong for a while: `1`
  was blue in the palette, not black.  Lesson 12's `%!` lines were re-recorded from the
  interpreter, so the сад section now shows the numbers behind the names (`8421376`,
  `65280`), which is the lesson's own point made twice.  Both files say in their header how
  to run from the source tree (`-I stdlib`).

  *Both ends of the colour table moved together.*  `graphics.py` lost `EGA_PALETTE` and the
  palette branch of `color_for` (the value *is* the colour; the mask stayed as belt and
  braces for a front-end that hears a stray value), the graphics window's hover line shows
  `#rrggbb`, and `test_graphics.py` pins `color_for(4) == "#000004"` and a snapshot byte of
  `1`.  `doc/help.typ` §14, `doc/gui.typ`, `doc/builtins.json` (the colour argument of the
  four predicates), `doc/prologd-diff.typ` (a palette row in the comparison table),
  `doc/library.typ` (the new file's section, a nineteen-predicate table) and the two READMEs
  followed.

  *Traps.*  (1) `test_lessons.cpp` hands a lesson the include paths of the CLI: lesson 12
  imports the library now, so the list gained `PROLOGD_STDLIB_DIR` — the check mirrors
  `-I examples/lib -I stdlib`, it does not invent a search order.  (2) `test_reference.py`
  demands that every detail line of `doc/builtins.json` *starts with the predicate it
  describes*: the first wording of the new range line («Цвет — целое …») failed there, and
  it was rewritten to start with `ТОЧКА(X, Y, Цвет)`.  (3) `examples/stdlib_demo.pld` was
  left alone by decision — its table is per library file and the names are already shown by
  lesson 12 and `drawing.pld` — so `test_queries.py`'s `PINNED` did not move.

  *Left open.*  No test file pins the refusal yet: the graphics suite pins colour *values*
  (`3`, `4`, `9`, `15`), and the range error is covered by hand probes only.

  *Verified.*  `ctest` 320/320 (the formatter sweep over the new and rewritten files,
  `test_stdlib.cpp`'s every head in the document, lesson 12's promises); the six documents
  build; `test_graphics.py`, `test_reference.py`, `test_queries.py` and `test_window.py` all
  green; by hand: the four predicates refuse `16777216` and `-1` with the new message and
  accept `16777215`.

* The window and the graphics example, part 96: **a loop that outlived its own limit**
  (2026-10-06).  Three reports from the user, and one of them was a mistake of the previous
  round.

  *`drawing.pld` was rewritten wrongly.*  The task_63 rewrite replaced the example's colour
  numbers with library names — and the fifth argument of `зубы/5` is not a colour but the
  *number of teeth*: `зубы(220, 320, 20, 40, 10)` became `зубы(220, 320, 20, 40, Зелёный)`,
  that is 65 280 teeth, and the picture never ended.  Restored: a count is a count, the colours
  are the names (the unused `зелёный` binding went with it).  The file runs in 0.01 s again and
  prints `ДА`.

  *Why the window looked frozen.*  The interpreter is not a thread of the window but a
  **separate process** (`QProcess`, `session.py`), which is what makes a crash, a restart and
  Ctrl+C cheap.  The window still has to *read* everything that process writes, on its UI
  thread: a runaway drawing program writes one JSON event per primitive — the teeth loop was
  more than 300 000 of them — so the event loop is starved for as long as the flood lasts.  The
  process was fine; the front-end was saturated.  The fix for the case at hand is the example
  itself; a throttle for the graphics stream is not in the tree.

  *«Предел времени» printed its note and stopped nothing.*  The deadline fires, writes
  `--- предел времени: N мс, остановлено ---` and sends `interrupt` — and that was all it did.
  Measured with a probe against `--protocol json`: a session solves a `load` *inside*
  `dispatch` and reads its next request only once that request is over, so an `interrupt`
  written while a query is **solving** is never dispatched while the query runs, and the
  process stays busy for ever.  The case where the request *does* work is a query that is
  waiting — for input, or at a step point — which is exactly the case
  `test_stopping_a_query_asks_first_and_keeps_the_base` happens to cover, and why the gap
  survived two rounds.  `_on_timeout` now arms the same `STOP_GRACE_MS` deadline «Остановить»
  uses: the request first, the process after half a second.

  *The documents said the opposite.*  The comment in `protocol.cpp`, `window.py`'s
  `_arm_timeout`, the protocol bullet of `src/gui/README.md` and the paragraph in `doc/gui.typ`
  all claimed the request reaches a solver — or that it cannot reach a *waiting* program, which
  is the reverse of what was measured.  All four now say what happens.  The real cure — a
  session that watches the stream while it solves, so a solving run ends politely and keeps its
  base — is written down as **task_64** and not attempted here.

  *Verified.*  `ctest` 320/320; `test_graphics.py`, `test_reference.py`, `test_queries.py` and
  `test_window.py` green (the last with the new solving case: a counting program with a 300 ms
  limit must leave the session gone, with both notes in the pane); the six documents build;
  `drawing.pld` finishes in 0.01 s.

  *Also in the tree, not ours.*  The user's own edit of `examples/lessons/lesson_07.pld` moved
  its `?`-statement count (20 → 21) and left the file off the standard shape: `PINNED` in
  `test_queries.py` was refreshed, and the file is a fixed point of `--format` again.  The
  interrupted probe (a program reading input run without `-i`) is a reminded trap: a shipped
  example that reads must be run with its `<stem>.input.txt`, or the process waits for ever.

* The window survives a flood, part 97: **slices that slice, and a limit that stops the flood
  itself** (2026-10-06).  task_65 finished properly, task_66 added (both asked for by the user).

  *Why the window still froze.*  The first slicing bounded the *dispatch* of events but not their
  *decode*: `_on_stdout` fed the whole read to `Decoder.feed` in one call, so a multi-megabyte
  burst was still parsed in one go and the loop stayed busy.  The decode is now bounded too —
  `DECODE_BYTES_PER_TURN` (64 KiB) per turn, from a raw byte buffer — and the two half-turns
  (decode, then dispatch `EVENTS_PER_TURN` events) are both driven by the one-shot drain timer.
  The same round fixed a defect the change itself introduced: `_start_drain` checked only the
  event queue, and while the bytes were not yet decoded that queue was empty, so the drain never
  started at all (`test_session.py` caught it: «queued request lost»).

  *«Предел вывода» stops the flood by itself (task_66).*  A new row in «Выполнение»: how many
  output events — a line of the program's text, a drawing primitive, a trace line — one run may
  produce (`execution/max_output_events`, `0` = off).  The window counts what it receives and,
  past the cap, fires the same escalation as the deadline: the request, then the process after
  `STOP_GRACE_MS`.  It is the window's guard, not the engine's — which is exactly what a program
  that floods output needs, because it is the one the polite request never reaches (task_64).  The
  pane says «предел вывода: N событий, остановлено», and the run-note names the row.

  *Tests.*  The window cases are all bounded now, so no endless program can hang the suite again:
  a sleeping loop for the time limit, a 60 000-line counter for the flood, and
  `test_the_output_limit_stops_a_flood` for the new cap — a 100 000-line program with a 1 000-event
  cap must end by itself and leave the note in the pane.  A watchdog (`os._exit`) guards a long
  run.

  *The stop itself.*  Using the window still left «Остановить» unanswered while a flood was being
  *repainted*: the visible panes kept consuming the stream, so the event loop stayed busy and the
  `STOP_GRACE_MS` deadline — which needs the loop — never fired.  The panes are now fed no more the
  moment a stop is asked (`_on_output`, `_on_drawn`, `_on_trace`, `_on_flooded` return early), which
  frees the loop for the deadline.  A happy side effect pinned by the tests: a *bounded* flood drains
  within the grace, the `loaded` event lands, and the stop is a polite one — the session and the base
  survive.

  *Verified.*  `test_session.py`, `test_output.py`, `test_settings.py`, `protocol_smoke.py` and the
  four window tests green; the full `test_window.py` runs in the background; the six documents
  build.

* Name modes, part 98: **a file says how its names are read, and the old course proves it**
  (2026-10-06).  task_67 steps 2 and 4.

  *The marker (step 2).*  `:- ИМЕНА(0|1|2).` as the *first* line of a file is read by the loader
  before the lexer runs — a mode has to be known before a name is classified — and the line is then
  dropped: the real lexing starts at its newline, so every later line keeps its number and its
  diagnostics.  `ИМЕНА/1` is registered as a reserved built-in only so that the marker line lexes
  the same way in every mode, and the English alias `variables` had to be reserved with it:
  `reservedKeywords()` is built from the lexer's set, so without it `test_keywords.cpp` and
  `test_reference.py` both failed («records name things the interpreter does not have»).  Anywhere
  but the first line the directive reaches the built-in, which answers «режим имён задаётся первой
  строкой файла: `:- ИМЕНА(0|1|2).`» with the file, line and column.

  *The old corpus (step 4).*  `examples/lessons/_old/` is now the acceptance test for the mode: six
  of its eight files start with the marker, carry their old `?` questions uncommented and record
  what they print as `%!` lines, and `test_lessons.cpp` runs all of them (`checkedOldLessons`).  The
  questions were measured one file at a time — a prefix of the file per question, the difference is
  that question's answer — and a question that cannot be uncommented keeps its `%` with the reason
  written above it: `_old/lesson_1`'s `нод(30,125,н)` never finishes, `_old/lesson_4`'s `бинсорт`
  prints megabytes of a list and never finishes, `_old/lesson_5`'s `ферзи(8,A)` answers 92 rows and
  its `парламент(7,4,c)` never finishes, `_old/lesson_8`'s `рамка,шаг(12,12,3,1)` draws the whole
  frame and hangs.  Two files are not touched and stay out of the list: `_old/lesson_2` no longer
  loads at all (`РАВНО` called with one argument) and `_old/lesson_9` answers only after an
  interactive dialogue (`оценка` asks about every writer), which a checked file cannot have.

  *What the old answers look like.*  A `?` question of the old dialect prints one line per bound
  variable (`А=блондин`, `Б=с усами`, `В_=с портфелем`), ground success is `ДА`, failure is `НЕТ`,
  and the six files carry 79 `%!` lines between them.

  *The window and the flag (step 3).*  The mode has three consumers, and only one of them
  needs the window to work it out for itself: the highlighter, which cannot ask the
  interpreter on every keystroke.  So the rule lives once, in C++ — `readVariableMarker`
  moved out of `engine.cpp` into `lexer.cpp`, and the *formatter* reads the marker now too,
  which it never did — and the window repeats it in `tokens.mode_from_first_line` for
  colouring only.  `src/gui/tests/test_variable_modes.py` pins that repetition against the
  interpreter's own reading, asked by behaviour: `?РАВНО(д, 1).` answers `д=1` in modes 1
  and 2 and `НЕТ` in mode 0, and `Сумма'` answers in mode 2 alone.  The row «Имена
  переменных» in «Выполнение» is `auto` (follow the file) or a mode for a file that says
  nothing, the buffer watches its own first line, and `vars` travels with `load` and with
  `format` — **protocol 12**; `--format --vars N` is the same fallback on the command line.

  *The documents (step 5).*  `doc/prologd-diff.typ` gained the section, `doc/help.typ` the
  marker beside the flag it already documented, `doc/gui.typ` the settings row and what it
  changes, and `ai/conventions.md` the rule «a mode is per file, never per build» — with the
  note that only the C++ side owns the rule.

  *The user's three asks (part 98, continued).*  (1) A question clicked on a margin
  marker went out in the mode of the *run* — mode 0 by default — so
  `?студент(Вова, Корчагин).` of a mode-1 file read the two names as free variables and
  answered with the first student.  A `query` now carries `vars` as well, and the window
  sends the mode of the file in front of the user (`Buffer.variable_mode`,
  `Window._variable_mode`) for the goal line, the margin marker, an ordinary run and the
  formatting request.  (2) The old lessons write their names the way the old dialect did —
  bare (`Боря`, not `'Боря'`) — and every one of them was measured and re-shaped again.
  (3) The three examples the user added — `examples/lib/old_lib.pld` (mode 1),
  `examples/lib/old_lib_2.pld` (mode 2) and `examples/use_old_names.pld` (mode 0) — were
  rewritten with fuller descriptions, import through `lib/…` so no `-I` or settings fiddling
  is needed, and are checked: `use_old_names.pld` promises its four answers as `%!` lines and
  the two libraries are exercised through it.

  *Two real defects this round found.*  A *piped* run of `prologd` writes its Cyrillic in the
  ANSI code page, so reading the formatted text from `--format` through a pipe and writing it
  back **destroyed seven files** — they were restored from the repository and rebuilt over
  `--protocol json`, where non-ASCII travels as escapes.  And the formatter measured the raw
  span of a string constant by scanning for its closing quote, while a mode-1 string constant
  has no quotes at all (it is a bare capitalised name): the scan swallowed the rest of the
  line and the formatted old lessons came back twenty times longer than the input.  `rawLength`
  now returns the decoded name for that case, pinned by a case in `test_formatter.cpp`.

  *Verified.*  `ctest` 330/330 with the six old lessons in the suite (`test_formatter`,
  `protocol_session.cmake` and `test_reference.py` green); every converted file, run whole,
  prints exactly its `%!` lines; the window, highlighter, settings, formatter, session,
  tokenizer and protocol checks green, and the three touched documents compile.

* The tab menu, part 99: **a right click on a tab, and the file it shows** (2026-10-06).
  task_68, asked for by the user («давай пока сделаем контекстное меню с одним пунктом —
  показать в проводнике»), and finished the same day with the picture and the keys.

  *One item, one table.*  `actions.py` gained the action `reveal` and the list `TAB_CONTEXT`
  beside `CONTEXT`, so the tab menu is built from the same table as the menu bar, the toolbar
  and the editor's own menu — a title, an icon or an enabled state cannot exist twice.  The
  entry wears `file-open`, the picture of «Открыть…»: both commands open the same thing, and
  one drawing is better than two that drift apart.  Its keys are `Ctrl+E`.  They began as
  `Shift+Alt+R` — what VS Code uses for the same command — but that never reached the window:
  on Windows the keyboard-layout switch eats Alt chords and the editor typed a bare `R`, so a
  plain `Ctrl`+letter is the honest choice (`Ctrl+Shift+E` is the familiar alternative, free as
  well).  `Pane` asks for the
  menu (`CustomContextMenu` on the tab bar) and reports the clicked tab and the point; the
  menu belongs to the window, as every other command does.

  *The tab under the cursor.*  A right click does not switch tabs in Qt, so `_prepare_tab_menu`
  makes the pointed-at tab current before it builds the menu — otherwise «Показать в
  проводнике» would have acted on the tab that happened to be in front.  A saved file enables
  the entry, an unnamed buffer disables it.  The menu is built in a method of its own, because
  `exec` waits for a click no test can make, and the command goes through `Window._reveal_path`,
  a replaceable seam: a test must not open a file manager.  `paths.reveal_command` is the
  platform's own call — `explorer /select,<path>` as *one* argument (written apart, `explorer`
  opens «Документы»), `open -R` on macOS, `xdg-open` elsewhere — and no exit code is checked,
  because `explorer` reports failure even when it worked.

  *A defect the seam itself hid.*  The first version never defined `_reveal_path` — the edit
  that was meant to add it anchored on a line that occurs twice in the window — and the command
  crashed on the first click.  The test did not see it: it *assigned* the attribute after the
  window was built, which works whether or not the attribute is defined.  It now patches
  `paths.reveal` *before* the window is constructed, so the real `_reveal_in_file_manager` runs
  and a missing seam fails the test.  Two more slips of the same round: the board row was
  written twice (the tool had reported the first attempt as failed) and the journal entry was
  not written at all — both found by reading the file instead of trusting the report.

  *Verified.*  `test_paths.py` (the command of the platform), `test_window.py` (the menu acts
  on the clicked tab, the entry follows the buffer's path, the seam receives exactly that
  path), `test_icons.py` and `test_shortcuts.py` green around them.

  *Also in the tree, not ours.*  The user redrew fourteen icons of the window and asked for a
  commit; `src/gui/assets/csu.png` turned out to be referenced by nothing — the emblems the
  documents and the portable package use live in `doc/` — so it left with the same commit
  (`f8d116e`).

  *Why the key said nothing.*  The second key, `Ctrl+E`, was declared, connected and shown —
  and typing it in the editor did nothing, while a click on the menu entry worked.  A
  `QAction` fires its shortcut only while it belongs to a widget, and a menu that is built
  when it is opened holds the action only while it is open: the key had nowhere to fire.
  `_build_actions` now adds every action to the window itself, and
  `test_every_declared_key_belongs_to_a_widget` holds that — a key declared with no widget
  behind it is exactly the silence the first attempt looked like.

### 100. Клавиша `F12` ведёт к файлу строки `ИМПОРТ` (2026-10-06)

Директива `ИМПОРТ` называет файл, и до этого дня, чтобы его посмотреть, файл искали
руками — по каталогам `-I`, по `stdlib`, по папке программы.  Теперь `F12` на строке
директивы открывает нужный файл во вкладке.

Порядок поиска переписан из интерпретатора (`paths.resolve_import`): абсолютное имя —
само себя, иначе каталог *импортирующего* файла, затем «Дополнительные каталоги
ИМПОРТ», затем `stdlib` рядом с `prologd`.  Правило должно быть одно: окно,
открывающее не тот файл, который загрузит запуск, хуже отсутствия команды.  Окно не
повторяет порядок по памяти — оно зовёт ту же функцию, и `test_paths.py` держит его
(порядок, абсолютное имя, «нигде нет», и что файл рядом побеждает одноимённый в общем
каталоге).

Пункт включён только тогда, когда под курсором действительно строка с `ИМПОРТ`
(`_refresh_navigation_actions` из `_update_details`), и живёт в общей таблице
действий — отсюда и меню редактора, и клавиша.  Ненайденное имя называет себя в
«Системе»: у клавиши нет другого способа сказать, что она сработала.

*Строка читается токенизатором редактора, а он отдаёт литерал как написан.*  Первая
версия искала файл с именем `"library.pld"` — вместе с кавычками — и честно писала в
«Системе» «не найдено "library.pld"».  Лексер интерпретатора (C++) отдаёт литерал
раскодированным, окно (Python) — нет; разница невидима, пока значение не попадёт в
файловую систему.  `tokens.literal_text` снимает кавычки и разворачивает `\\`, `\"`,
`''`.

*Verified.*  `test_paths.py`, `test_window.py` (на строке с `ИМПОРТ` пункт доступен и
открывает библиотеку рядом с программой; в стороне — выключен), `test_tokens.py` —
зелёные; `doc/gui.typ` собирается без замечаний.

### 101. Строка «Имена переменных»: три пункта вместо четырёх (2026-10-06)

Учитель спросил, чем «по первой строке файла» отличается от «как в ISO: строчное
имя — атом», и заметил, что оба обещают ISO по умолчанию.  Разницы не было никакой:
маркер `:- ИМЕНА(N).` главнее настройки и в интерпретаторе, и в окне, а режим 0
вообще не уходит на провод, — значит, оба пункта давали один и тот же запрос и одно
и то же поведение для любого файла.  Строка выбора работает только для файла **без**
маркера, и там умолчание и есть ISO: «по первой строке файла» было вторым способом
сказать то же самое.

Теперь их три: «как в ISO: переменная с большой буквы» (умолчание), «по-старому:
одна буква — переменная» и «то же плюс имена с апострофом».  Правило не двинулось:
файл, объявивший маркер, читается по маркеру — диалект принадлежит файлу, а не
сборке и не настройке окна, и у импортируемого файла он свой.  Конфигурация, в
которой записано старое `auto`, читается как `0` (`_choice` при несовпадении
возвращает умолчание), так что для непомеченного файла у тех, кто окно уже
запускал, поведение не изменилось.

*Verified.*  `test_settings.py` (42 записи, умолчания внутри границ),
`test_variable_modes.py` (правило окна против интерпретатора), `test_window.py`
(кейс маркера дополнен проверкой умолчания строки) — зелёные; `typst compile
doc/gui.typ` без замечаний.

### 102. Меню вкладки «Вывод» (2026-10-06)

Учитель попросил контекстное меню над вкладкой «Вывод» с пунктом «очистить».
Панель вывода — свой `QTabWidget` (Проблемы, Вывод, Система, Ввод, Таблица), а не
`Pane` редактора, поэтому своей полосы вкладок у неё не было; теперь у неё те же две
строки настройки контекстного меню, а само меню собирает `_prepare_panel_tab_menu`.

Пункт — тот же `QAction` «Очистить вывод» из общей таблицы, что в меню «Выполнение» и
на `Ctrl+L`: команда не может существовать дважды, и новый кейс проверяет именно это.
Вкладку узнают по панели, которую она показывает: заголовки здесь со счётчиком
(`Вывод:5`), поэтому сравнение по надписи развалилось бы при первом же прогоне
программы.  Вкладку не переключают, в отличие от меню вкладки редактора: «Очистить
вывод» действует на панель, а не на то, что впереди.  У остальных вкладок панели
своей команды нет, и там правый клик не показывает меню вовсе — пустое меню хуже,
чем никакого.  Значок пункта — `execution-clear.png`: с task_58 «Очистить вывод» была
без картинки (первый вариант, `edit-clear`, забраковали — он читался не как
«очистить вывод»), и теперь одна картинка стоит у команды во всех местах.

*Verified.*  `test_window.py` (новый кейс «the output tab's menu clears the pane»),
`test_shortcuts.py` — зелёные; `typst compile doc/gui.typ` без замечаний.

### 103. Проза в примерах: «А, а не Б» — одно утверждение (2026-10-06)

Учитель поправил три файла старого формата сам (`use_old_names.pld`, `old_lib.pld`,
`old_lib_2.pld`: проза короче, у `студент/1` прибавилось два факта — `студент('Вася').`
и `студент(Гоша).`, — и появилась строка про `F12`) и попросил сократить в примерах
конструкции вида «это А, а не Б»: либо одно утверждение, либо два отдельных.

Две правки, которые без проверки прошли бы мимо: у `old_lib_2.pld` не было перевода
строки в конце файла, а ответы `use_old_names.pld` остались прежними — с двумя новыми
студентами их стало четыре (`Кто=Боря`, `Кто=Вова`, `Кто=Вася`, `Кто=Гоша`).
`test_lessons.cpp` такое и ловит: он сверяет весь вывод с `%!`-строками файла.

Конструкцию переписал в двадцати местах шестнадцати файлов — там, где это было
утверждение.  Вопросы-упражнения («Почему xor/4 записан двумя предложениями, а не
одним?») оставлены: в них контраст и есть вопрос.  Заодно попались зеркальные «это не
А, а Б» — переписаны так же.

*Нашлось по дороге.*  `src/gui/tests/test_queries.py` был красным с task_67: счётчики
старых уроков (`lesson_1` 15→24, `lesson_3` 1→5, `lesson_4` 3→13, `lesson_6` 2→3) и три
новых примера (`lib/old_lib.pld`, `lib/old_lib_2.pld`, `use_old_names.pld`) в `PINNED`
не попали.  Этот файл не входит в `ctest`, и красным его никто не видел; таблица
обновлена по `--print`.

*Verified.*  `ctest` 330/330 (в том числе сверка примеров с их `%!` и с выводом
форматтера), `test_queries.py` — 405 вопросов в 42 примерах, как в таблице.
