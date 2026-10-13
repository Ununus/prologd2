# PrologD 2.0

A modern C++23 re-implementation of the **PrologD** logic programming
interpreter: UTF-8 native, console first, with Russian built-in predicates,
arbitrary precision integers and the `НАЙТИВСЕ/3` (`findall`) predicate.

The original PrologD sources (CP1251, C++/Qt) are not bundled with this
repository; the previous implementation is published at
<https://github.com/Ununus/prologd>. The working folder of the AI agent that
built this rewrite — plan, task breakdown, architecture decisions and the
development journal, in English — is `ai/`; it is developer material, not user
documentation. User and technical documentation is in `doc/` (Russian, Typst).

## Quick start

```sh
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build
```

The console interpreter is `build/src/cli/prologu`.

```sh
# Run a program file
./build/src/cli/prologu -s examples/findall_demo.pld

# Or read the program from stdin
./build/src/cli/prologu < examples/findall_demo.pld
```

### Windows

Prerequisites: Git, CMake 3.24 or newer, and Visual Studio 2026 with the
"Desktop development with C++" workload. The first configure downloads Catch2
and CLI11 through CMake FetchContent, so it needs network access.  The build and
the portable package (task_61) require Windows 10 (1903) or newer, 64-bit: the
UTF-8 manifest element (`<activeCodePage>`) is understood from 1903, the window
needs Windows 10 because of Qt 6 and Python 3.14, and Windows 7 is out of
support since 2020 (ADR-013).

```powershell
cmake -S . -B build -G "Visual Studio 18 2026" -A x64
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

The same with the bundled presets:

```powershell
cmake --preset windows-msvc
cmake --build --preset windows-msvc
ctest --preset windows-msvc
```

The executable is `build\src\cli\Release\prologu.exe`.

The portable package — interpreter, window, the five documents, the lessons and
the standard library — is built by one script:

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_portable.ps1
```

It runs the Release build, `ctest`, the `docs` target and PyInstaller (`--onedir`,
leaving out the Qt modules the window never loads), lays the folder out as
`dist\prologd-<version>-win64` with the Visual C++ runtime beside the executables,
checks it (`tools/check_dependencies.py`, plus the interpreter and the window itself)
and writes the zip.  `-SkipTests`, `-SkipFreeze`, `-NoTrim` and `-NoZip` shorten a
round; what a person still has to do is listed in
`ai/task_61_portable_windows_build.md` section 7.

## Language at a glance

```prolog
% facts
студент('Вова', 'Корчагин').
студент('Данил', 'Ахмеров').

% a query (variables start with an upper-case letter)
?НАЙТИВСЕ(Имя, студент(Имя, Фамилия), Список).
% Список=[Вова,Данил]; the bindings the goal made are undone, so Имя and
% Фамилия come back free and print as `_1`
```

* Variables: `Name`, `_Name`; `_` is anonymous.
* Atoms: lower-case names or `'quoted atoms'`.
* Russian built-in predicate names (`БОЛЬШЕ`, `СЛОЖЕНИЕ`, `НАЙТИВСЕ`, …) are
  reserved atoms.
* Clauses end with `.` or `;`; rules use `:-` or `<-`; queries start with `?`.
* Arithmetic expressions are written `#expr#` and support `+ - * / mod div`.
* Lists: `[a, b | T]`, `[]`.

See `doc/help.typ` for the full reference and `doc/prologd-diff.typ` for the
differences from the original PrologD (most importantly: single-letter
variables are gone, and CP1251 was replaced by UTF-8).

## Lessons

`examples/lessons` holds the course: twelve lessons, from facts and queries to
graphics, plus an appendix about debugging.  A lesson is a runnable program whose
comments carry its own expected output (lines starting with `%!`), and the check in
`src/tests/test_lessons.cpp` runs every lesson and compares - so a lesson cannot
drift away from the interpreter unnoticed.

Start with `examples/lessons/README.md` (the index) or `doc/lessons.typ`; two
lessons need a little more than a plain run, and the index says which.  The
superseded originals are kept in `examples/lessons/_old/`.

## Standard library

`stdlib/` holds the library the dialect ships — the list predicates
(`member`, `length`, `min_list`, `append`, `reverse`, `flatten`, `permutation`,
…), the set predicates built on lists (`set`, `subset`, `intersect`, …), the
sorting techniques (`msort`, `quicksort`, `mergesort`, `treesort`, …), the string
helpers (`words`, `join`, `trim`, `replace`, `to_numbers`) and the integer
predicates (`between`, `gcd`, `lcm`, `power`, `factorial`, `is_prime`, `primes`).
The interpreter searches `stdlib` beside itself, last — after the importing file's
folder and after every `-I` — so a file that ships with the interpreter needs no
flag:

```prolog
:- ИМПОРТ("lists.pld").
```

```sh
prologu -s examples/stdlib_demo.pld
# from a source tree, where nothing sits beside the interpreter:
prologu -I stdlib -s examples/stdlib_demo.pld
```

`examples/stdlib_demo.pld` is a runnable tour of every predicate, with its own
expected output in `%!` lines; `doc/library.typ` is the reference (`test_stdlib.cpp`
fails if a predicate has no line there) and `stdlib/README.md` is the map plus the
table `old name -> new name` for programs written against the first PrologD library.
The built-in `СОРТИРОВКА` already sorts and de-duplicates; the sorts in
`sorts.pld` are the study versions, kept because they show the techniques.

## Command line

```
Usage: prologu [options] [files...]

-s, --source FILE     interpret a source file (repeatable)
-I, --include DIR     add a module search directory
-i, --input FILE      read program input from this file
-o, --output FILE     write program output to this file
-e, --error FILE      write diagnostics to this file
-q, --questions       echo queries before executing them
-t, --trace           start with tracing enabled
    --no-warnings     do not print warnings (they never change the exit code)
    --max-depth N     recursion depth limit for one query (0 = unlimited)
    --max-steps N     step limit for one query (0 = unlimited)
    --max-findall N   solution limit for one НАЙТИВСЕ (0 = unlimited)
    --format[=MODE]   print the source formatted and exit: soft, hard or line
    --format-width N  soft mode: what has to fit on one line (default 80)
    --format-indent N continuation indent in units (default 1)
    --format-unit U   indent unit: tab (default) or spaces
    --protocol FORM   front-end protocol: text (default) or json
    --list-keywords   print the reserved names as name/arity and exit
-h, --help            show help and exit
    --version         show version and exit
```

Source files can also be given as positional arguments:

```sh
prologu examples/findall_demo.pld
prologu --source examples/findall_demo.pld
```

Diagnostics use the usual compiler format:
`file:line:column: error: message`.

Exit codes: `0` success, `1` usage error, `2` a source file could not be loaded
 or parsed, `3` a runtime error (including an interrupted query).

### Front-end protocol

`prologu --protocol json` replaces the human-readable console with a session
for front-ends: requests are JSON objects on stdin, events are JSON objects on
stdout, one per line. `-i`/`-o`/`-e` are refused in this mode — the protocol
owns both streams. The Python/PySide6 GUI in `src/gui` is built on it; see
`src/gui/README.md` for the full contract. Protocol version 2 adds the reserved
names and their arities to the `ready` event, so a front-end never keeps its own
copy of the built-in list (`prologu --list-keywords` prints the same table).

## Project layout

```
CMakeLists.txt        top-level build
CMakePresets.json     configure/build/test presets (Linux, Windows)
src/prlib/            interpreter library
src/cli/              console front-end
src/gui/              PySide6 front-end (drives the CLI over the JSON protocol)
src/tests/            Catch2 test suite and CLI integration tests
src/3rdparty/         FetchContent dependencies (gitignored)
doc/                  Typst documentation (Russian)
examples/             example PrologD programs (demo, problems, lessons, lib)
stdlib/               standard library, shipped beside the executable
.github/workflows/    CI (Linux GCC/Clang, Windows MSVC)
ai/                   plan, task breakdown and notes for the AI agent
```

## Status

Implemented: lexer, parser with diagnostics, unification with trail, the
resolution engine (backtracking, cut, meta-call, negation, disjunction),
arithmetic with a hand-written `BigInt`, all documented built-in predicate
groups (control, types, conversions, strings, I/O, program database, graphics
stubs), `НАЙТИВСЕ/3`, the module loader (`ИМПОРТ`) and the CLI.

Examples live in `examples/` — one demo per predicate of the language surface, the
problems (`factorial`, the Hanoi tower, `knapsack`), the lessons and the library —
and are covered by golden tests: a lesson or a demo carries its own expected output
in `%!` lines, and `src/tests/test_lessons.cpp` compares the two.  The library the
dialect ships is in `stdlib/`, beside the executable, and has its own runnable tour
(`examples/stdlib_demo.pld`) checked the same way. The PySide6 front-end in
`src/gui` drives the interpreter through the JSON protocol: tabs, syntax
highlighting that tells Latin names from Cyrillic ones, completion built from
the reserved names and the program's own, run/stop with a fresh interpreter per
run, and the usual file handling (save prompts, line endings and encodings kept).
Documentation is in `doc/` (`help.typ`, `library.typ`, `gui.typ`, `technical.typ`,
`prologd-diff.typ`, `lessons.typ`); `cmake --build build --target docs` writes the
PDFs into the same directory when Typst is installed.

CI builds and tests on Linux (GCC and Clang) and Windows (MSVC); see
`.github/workflows/ci.yml` and `CMakePresets.json`. Current status and the task
board are kept in `ai/status.md`.
