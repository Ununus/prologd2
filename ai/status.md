# Status tracker

Last updated: after the graphics window of task_45 (protocol 10), the interface
cleanups of task_48 (icons, the toolbar, the search menu), the formatter's round of
task_47 (the lessons in one style, the head on its own line, the mode control back
on the toolbar), task_49 (four window defects and the live output), and task_46's
interpreter path and process directory (the two rows that pick the binary and
where its files go).

## Overall

* Phase: feature-complete core, verified on Windows; the PySide6 front-end has
  started (protocol + skeleton).
* Build: the `windows-msvc` preset (Visual Studio 18 2026, MSVC 19.51) build is
  green locally; the Linux presets, including `-Werror`, build cleanly.
* Tests: 268/268 pass in about five seconds: 254 Catch2 cases plus 14 command-line
  and integration tests (seven option tests, two `--list-keywords` tests, the
  import-search report, the JSON protocol session, the engine-limit cases, the
  diagnostics cases and the formatter round-trip).
  or `--source`), stdin, the REPL and the `--protocol json` session for
  front-ends.
* GUI: `src/gui` (PySide6) drives the executable through the JSON protocol; the
  window, the protocol and the stepping are covered by twenty-one offscreen scripts
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
  points, standard cut, transparent `ВЫП/1`, `НЕ/1`, `ПЕРВОЕ/2`, `РАВНО/2`,
  `ЛОЖЬ`, `ТРАССА`/`НЕТ_ТРАССЫ`, `ТИХО`, `ВЕРСИЯ`, `ПС`, `ЖДИ`.
* Arithmetic: hand-written `BigInt`, `#expr#`, `БОЛЬШЕ`/`МЕНЬШЕ`, `СЛОЖЕНИЕ`,
  `УМНОЖЕНИЕ/3,4`, `abs`, `sqrt`, `sin`, `cos`, `tan`, `exp`, `is_whole`,
  `is_number`, `СЛУЧ`, `ЦЕЛВЕЩ`, `СТРЦЕЛ`, `СТРВЕЩ`, `СТРСПИС`.
* Strings (code-point based): `БУКВА`, `ЦИФРА`, `СЦЕП`, `КОПИЯ`, `ДЛИНА` (each
  with an English name too — appendix 17 of the manual).
* I/O: `ВЫВОД`, `ВВКОД`, `ВВОДЦЕЛ`, `ВВОДВЕЩ`, `ВВОДСИМВ`, `ВВОДСТР`,
  `ЧТЕНИЕ_ИЗ`, `ЗАПИСЬ_В`, preloaded `$...` input lines.
* Program database: `СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`.
* Graphics over `GraphicsBackend` (null and recording implementations).
* `НАЙТИВСЕ/3` reproduces the required examples.
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
| task_26_gui_toolbar | done | one action table (48 commands, 12 disabled with a reason) feeding the menu bar, the toolbar and the context menu; icon audit in `src/gui/README.md` (48 names referenced, 42 drawn, 6 left: the «Вид» switches — numbers as of task_26; task_47 and task_48 moved them) |
| task_27_gui_panels | done | movable panel (`F4`, `Ctrl+F4`), output pane (colour by kind, visible half-lines, bounded history, auto-scroll, save to a file), input console with the queue switch, status-bar details and the two-state run/stop |
| task_28_gui_run_step | done | `EngineOptions::stepHook` + `StepInfo`, protocol 3 (`step`/`trace` events, `step` request, positions on `error`), the step strip with the call stack, the trace line in the editor, `F10`/`Shift+F10`/`F5`, error and trace lines from structured positions |
| task_29_gui_settings | done | `settings.SETTINGS` — one record per preference (key, label, section, kind, default, bounds, hint) that drives the dialog's row, validation, `«Сбросить»` and the map_positions-style test; `settingsdialog.SettingsDialog` with sections `Редактор/Вид/Формат/Выполнение/Файлы/Вставки`, «ОК»/«Применить»/«Отмена»/«Сбросить»/«Импорт…»/«Экспорт…»; the window applies everything without a restart (`apply_settings`); new keys: `output/font_size` (unset = follow the editor), `output/line_limit`, `editor/completion_match_case`, `editor/current_line`, `execution/working_directory`, `execution/import_paths`, `files/autosave_minutes`, `files/recent_limit`; unknown keys preserved through a foreign file; the dark theme and the system colours are done, session restore and the small switches are done, and **RU/EN was dropped** (ADR-021); profiles and limits are `task_46`, the graphics window `task_45` |
| task_30_gui_formatter | done | `prlib/formatter.cpp` (whitespace-only, everything else copied byte for byte); three modes — **в одну строку**, **мягкое** (строки строятся заново: цели собираются до ширины) and **жёсткое** — chosen in «Правка → Формат» (the submenu moved back to the toolbar in task_47); `prologd --format[=soft|hard|line]` with `--format-width`, `--format-indent` and `--format-unit`; protocol **7**+**8** (`format` → `formatted`/`error`, answerable between queries; `loaded` when a run is over); the window's `Ctrl+I` with one undo step and the caret and selection mapped onto the new text; a source that does not parse is never rewritten |
| task_31_gui_shortcuts | done | `shortcuts.py` — a Qt-free table of `Ctrl`+**physical key** insertions, matched on `nativeScanCode()`: `:-.`, `()`, `[]`, `#`, `?`, `РАВНО(,)`, `БОЛЬШЕ(,)`, `МЕНЬШЕ(,)`, `СЛОЖЕНИЕ(,,)`, `УМНОЖЕНИЕ(,,)` and the simple symbols `/ - _ ! '' ""`; `:` and `?` carry two chords each (Russian `Shift+6`/`Shift+7`), a selection is *wrapped* by the bracket-like rows, every insert is one undo step, only `Ctrl` (plus `Shift`) is accepted — `Alt` and `Ctrl+Alt` are left to the window; the table is data in the settings file (`shortcuts/table`, JSON, one entry per insert with a list of chords) and «Справка → Шпаргалка по вставкам» lists it from the same object; zoom stays on the keypad, `|` has no chord (merge keeps `Ctrl+Shift+\`) |
| task_32_import_search_report | done | `ИМПОРТ` failure names the directories tried, with reasons |
| task_33_gui_search_replace | done | `search.py` (plain-text, Qt-free) + the find bar: question from the selection or the word at the caret, `F3`/`Shift+F3` with the wrap reported, three switches, «Заменить всё» as one undo step, the matches lit in every view; `test_search.py` has 17 checks |
| task_34_builtin_branches | done | every built-in branch-tested in Catch2 (186 cases); the sweep found and fixed five defects: two in the float built-ins (`nan` instead of a failure), the integer/real comparison, the cyclic term that ended the process, the ignored read prompt, the unchecked graphics arguments and the code points that were written as invalid UTF-8 |
| task_35_lessons_rework | done | the course in `examples/lessons` is rewritten for the current dialect, one commit per lesson, from the plan in `ai/task_35_lessons_rework.md`; `test_lessons.cpp` runs every lesson (12 + the debug appendix) and compares its whole output with the `%!` lines the lesson itself carries, so a lesson cannot drift again; the old files are in `lessons/_old/`; the index is `examples/lessons/README.md` and the fifth Typst document `doc/lessons.typ` (the `docs` target builds it); writing the expectations found and fixed mistakes in the source material (a non-terminating `нод/3`, descending sorts, a hanging `?длина(Х, 2)`, a failed read that leaves the rest of its line) and taught the check two tricks: input files for lesson 7 and include paths for lesson 11 |
| task_36_gui_query_markers | done | a blue triangle in the margin runs the question it stands at — `?Goal.` and `% ?Goal.` alike: the commented query of a lesson (its own lines still run whole), the `%?` line coloured as a question, and a `questions: false` load so the clicked query answers *alone*; the rule is not a parser and refuses a line it cannot read (commits e9c3beb/c38acc6/a99c906/cebd2c0); the first hands-on run added two fixes — a failed query marks no line of the program (`<query>`), and `Ctrl+C` copies from the focused pane |
| task_37_gui_builtin_reference | done | `doc/builtins.json` — one record per predicate (name, English aliases, kind, arities, group, `help.typ` section, one-line summary, argument modes), 59 records over all 108 names; `help.typ` builds its appendix table from the file, `test_reference.py` keeps the file in step with the interpreter and the manual, `reference.py` loads it for the window (a missing file is an empty reference); the completion popup shows the summary of the highlighted row, `F1` opens a dock with the whole record — and `Up`/`Down` now really walk the popup list (they moved the caret, contradicting the README) |
| task_38_engine_limits | done | recursion depth and long runs: the crash is gone (the chain and deep terms are released iteratively — the trigger was a *surviving* deep reference, a choice point whose base clause does not cut, or the solver's final environment), `maxDepth` turns runaway recursion into a diagnostic, the variable growth is documented instead of "fixed", and `tools/bench_engine.py` made the numbers reproducible |
| task_39_english_aliases | done | every built-in has an English spelling in lower case (one `kEnglishNames` table in `builtins.cpp`, 47 pairs, is the only place a pair is written; `test_aliases.cpp` walks it and fails on a Russian name without a row); the manual gained appendix 17 with the whole table, `prologd-diff.typ` §15 and `conventions.md` the rule; doing it showed that `int`/`float` were *checks*, not conversions (`integer`/`float` are the ISO type tests, `is_whole`/`is_number` the old ones, and the planned `to_int`/`to_float` were dropped) and `ДЛИНА` became `strlen`; 108 reserved names, one list for CLI, protocol and GUI; renamed on review: `number` → `is_number`, `num_to_float` → `int_to_float` |
| task_40_diagnostics | done | severity (an error stops a load or a query and keeps exit codes 2/3; a warning never changes either, and `--no-warnings` drops them) with `severity` on the wire (protocol 4) and amber warnings counted in the GUI; positions name what to fix (the opening bracket and its line, the end of a clause without its dot, the goal); a reserved name with an arity that exists nowhere is an error, an undefined predicate or a missing arity is a warning with a suggestion; singleton variables with separate advice for facts, rules and bodies |
| task_41_semicolon_disjunction | done | `;` is the backtrackable disjunction of ISO, `,` binds tighter, and a branch runs in a frame whose cut barrier sits above the alternative (a cut in a branch is local to it; `ПЕРВОЕ/2` — then still named `ИЛИ/2`, renamed in task_44 — stays the committed form, and lesson 4 shows both side by side); the sentence terminator is the dot alone, and a `;` written as one is an error that says what changed; `examples/factorial.pld` was the only file to convert; parse shapes, solver semantics and diagnostics are all pinned |
| task_42_engine_hot_path | done | the constant tax, measured: the two per-goal lookups stop building strings (`BuiltinKey` keyed by `string_view`; the database is a two-level `name -> (arity -> list)` map looked up with `std::less<>`, no `"name/arity"` key, `key_order_` gone) — interleaved six pairs on a dispatch-bound loop: median 1.45 s → 1.40 s, every pair faster, ≈ 4 %; clause indexing measured and deferred (ADR-017: a 100 000-clause scan costs ≈ 20 ms, lesson predicates have a handful of clauses, and the queens workload is a shape an index cannot prune); term interning bounded by that same ≈ 4 % and deferred; `tools/bench_engine.py` gained the `dispatch`, `structured` and `queens` workloads and `--only` |
| task_43_language_surface | done | `ВЫП/2..N` (`call/N`): the extra arguments are appended to the goal (callee dereferenced first; the keyword table says `ВЫП/+`; the checker expands the same term; `!` inside the argument stays a parse error and the manual no longer promises it); the module-collision warning — one per predicate fed by two files with no import path between them, silent for the diamond and for extending an imported module (ADR-019); the dead library is gone (`?СКОЛЬКО(НЕ, А)` answers 0; ADR-018) |
| task_44_names | done | the two names that promised something else: `ИЛИ/2` → `ПЕРВОЕ/2` (`or` → `first`) with the retired spelling removed from the language (a call is a load error naming the replacement), `НАЙТИВСЁ` → `НАЙТИВСЕ` (the spelling of the task and of the reference notes) with the retired spelling kept reserved, so its call is the ordinary suggestion «возможно, НАЙТИВСЕ/3»; the two `ИЛИ` library clauses removed so the old name cannot answer through the database; `doc/help.typ` §4.6, `prologd-diff.typ` §17/§18, lesson 4's section 5 |
| task_45_gui_graphics_window | done | the graphics predicates are *visible*: `BitmapGraphicsBackend` inside the engine (a 1024×768 buffer that answers `getPixel` locally and performs `ЗАКРАСКА` itself, reporting every primitive), protocol **10** (`graphics` events and `{"cmd":"graphics","snapshot":true}` → `bitmap`), a Qt-free `graphics.Canvas` with the palette, and `graphicswindow.GraphicsWindow` — a window of its own with «Вписать в окно»/«1 : 1», «Очистить», «Сохранить как PNG…» and a cell readout; the last disabled menu entry is gone (ADR-022).  The by-hand look at `examples/drawing.pld` found two defects (the ellipse was read as a box; an untouched canvas was transparent) |
| task_46_interpreter_options_and_limits | in progress | the limits are in: `Limits` + `applyTo` in the engine, `--max-findall`, protocol **9** (`limits` on `load`, a bad field is an `error` instead of a dead session), four dialog rows and a front-end deadline.  The core has **no limits of its own** (0 = «без предела», messages name a limit and its value only — ADR-020) and the window ships 0 / 1 000 000 / 1 000 000 / 0.  The **interpreter path** and the **process directory** are in too (2026-10-02): `execution/interpreter` (a `file` row; empty = «the one the window was started with», the row wins over `--exe`, the status bar names a non-default build) and `execution/process_directory` (`каталог файла` / `рабочая папка` / `свой каталог`; `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` open relative to it) — every session start goes through one gate, «Применить» restarts a live session on either change and reports a missing path.  Still open: profiles, and `--timeout-ms` (a text-mode deadline would need a clock in the solver — **dropped by decision**).  The last item of task_29's settings list, split out on 2026-10-01 |
| task_47_lessons_and_formatting | done | the corpus in one style and the formatter's round of fixes: 21 of the 25 shipped programs reformatted by `prologd --format` (soft, 80, one tab) with a new check that every shipped program *is* the standard shape, so the style cannot drift again; the hard mode puts the head of a clause on a line of its own (the first goal was the one glued to the head); the format mode returns to the toolbar right after «Форматировать» (icon `edit-format-set`) and leaves «Правка»; lesson 12's animation is a click away (`%?`) with a two-frame version runs in the check; and the reformat taught the formatter a rule — a **query and a directive are never broken**, because the margin marker that runs them is line-local (the pinned question counts caught it) |
| task_48_interface_cleanup | done | the round of small things the user asked for: five pictures left the tree (`help-about` — the same drawing as `prologd2`, the two `search-find-selected-*`, `view-toolbar`, `view-line-numbers`), `assets.MISSING` is down to four names, «Сохранить все» left the toolbar, the two «Найти выделенное» commands left «Поиск» with their icons; `Esc` now closes the graphics window → the find bar → the reference dock → the cheat sheet (one handler on the window, by *propagation*, so the completion popup and the find bar's field keep answering for themselves), and the graphics window opens itself on the **first primitive of a run** — once per run, so a window closed during an animation stays closed (task_45's window plus `_graphics_shown`) |
| task_49_gui_defects | done | five defects found by using the window, all fixed.  `Шаг → Стоп → Запуск` no longer answers «нет шага, который ждёт ответа» (the paused flag is cleared by the events that conclude a run — including the *error* a «Стоп» turns into while a step waits); an untouched unnamed tab comes back clean (the session record carries the unsaved flag; JSON, because a fourth tab-separated field cannot be told apart from text with a tab in it); the format `Запустить с трассировкой` no longer takes the window (the output is handed over once per turn of the event loop, and the pane trims its history in bulks — 200 000 lines: 21.9 s → 3.0 s, a 16 000-line trace: 2.2 s → 0.6 s); the main window remembers its size and place (`view/window_geometry`), which the graphics window had done since task_45; and the **output arrives as it is written** — `IoContext::setOutputLineSink` fires at a line end and the session emits one `output` event per line, so a lesson's countdown counts 3, 2, 1 instead of arriving as one block when the program is over |
| task_50_panel_tabs | done | the output panel is one `QTabWidget`: **Проблемы** (errors and warnings), **Вывод** (program output, the `>` echo, the trace), **Система** (the window's notes) and **Ввод** (the prepared answers with the per-request console under them).  Each title carries its count (`Вывод:5`, `Проблемы:0` …), «Проблемы» is painted by state (ordinary with none, orange warnings-only, red with an error), a run brings up «Вывод» and a diagnostic «Проблемы»; the panel defaults to the **bottom**; «Поле очереди ввода» is gone (the queue is a tab now); a full load writes `--- база знаний загружена (N мс) ---` into «Система», measured by the window's clock from «Запустить» to `loaded` |

## Test suite

268 tests, about five seconds: 254 Catch2 cases plus 14 command-line and
integration tests (seven option tests, two `--list-keywords` tests, the
import-search report, the JSON protocol session, the formatter round-trip and the
engine-limit and diagnostics cases). Groups:
BigInt, lexer, keywords, parser, unification, engine, every built-in group,
`НАЙТИВСЕ`, module loader (including the import search report), the I/O seams,
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
   Open for the next session, and no longer part of task_29: the **interpreter
   options, profiles and limits** (`task_46_interpreter_options_and_limits.md`).
   The graphics window (`task_45_gui_graphics_window.md`) is done, and task_29's
   own list is closed: «использовать системные цвета» was done with the three
   themes, and **RU/EN was dropped** on 2026-10-01 (ADR-021 — the window stays
   Russian).  Two of the user's ten «недочётов» are written down and both are
   done: `task_47_lessons_and_formatting.md` and `task_48_interface_cleanup.md`
   (its last loose end — the by-hand look at the redrawn icons in the dark theme —
   was confirmed by the user on 2026-10-02: «иконки в тёмной теме нормальные»).
   The batch of defects found by
   using the window (`task_49_gui_defects.md`) is closed as well: four fixes pinned
   by reproductions and the live output — `IoContext::setOutputLineSink` plus one
   `output` event per written line, so a countdown prints 3, 2, 1 while the program
   is still running.  What is left on the board is `task_46`'s remainder:
   **named profiles** (a table of sets — `-I`, limits, interpreter — with «Сделать
   текущей» in one click); the text-mode `--timeout-ms` was **dropped by decision**
   (a clock in the solver's hot path is a cost the front-end deadline avoids, and
   a console run has the shell's own timeout).

## Open questions for the user

1. String positions are code-point based (not CP1251 bytes) --- confirmed as the
   intended UTF-8 behaviour unless told otherwise.

Resolved on 2026-09-29 (GUI planning):

* formatter (task_30): trailing whitespace is removed, the continuation indent
  is one tab, the soft width is 80 columns;
* shortcuts (task_31): the modifier is `Ctrl`, not `Alt` (which focuses the menu
  bar), and `?`/`:` get both physical keys --- `Ctrl+/` + `Ctrl+7` and `Ctrl+;` +
  `Ctrl+6`;

Added on 2026-10-02 while implementing task_31:

* `Ctrl+Shift+\` stays «Объединить редакторы», so `|` gets **no** chord at all
  (the user's decision: the window command wins over the row);
* the extra combinations are the simple symbols (`/`, `-`, `_`, `!`, `''`,
  `""`) — no clause skeletons: `ФАКТ.`, `Правило(…) :- …` and the rest of the
  proposed shapes were dropped as writing the program for the user;
* the table is written into the settings file on the first run, which is what
  makes it readable and remappable *there* rather than in the code.
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




