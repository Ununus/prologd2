# PrologD 2.0

A modern C++23 re-implementation of the **PrologD** logic programming
interpreter: UTF-8 native, console first, with Russian built-in predicates,
arbitrary precision integers and the `НАЙТИВСЁ/3` (`findall`) predicate.

The original PrologD sources (CP1251, C++/Qt) are not bundled with this
repository. Planning, task breakdown and architecture notes live in the local
`ai/` working folder (not versioned); user and technical documentation is in
`doc/`.

## Quick start

```sh
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build
```

The console interpreter is `build/src/cli/prologd`.

```sh
# Run a program file
./build/src/cli/prologd -s examples/findall_demo.pld

# Or read the program from stdin
./build/src/cli/prologd < examples/findall_demo.pld
```

### Windows

Prerequisites: Git, CMake 3.24 or newer, and Visual Studio 2026 with the
"Desktop development with C++" workload. The first configure downloads Catch2
and CLI11 through CMake FetchContent, so it needs network access.

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

The executable is `build\src\cli\Release\prologd.exe`.

## Language at a glance

```prolog
% facts and rules
студент(вова, корчагин).
студент(данил, ахмеров).

член(X, [X|_]).
член(X, [_|T]) :- член(X, T).

% a query (variables start with an upper-case letter)
?НАЙТИВСЁ(И, студент(И, Ф), А).
```

* Variables: `Name`, `_Name`; `_` is anonymous.
* Atoms: lower-case names or `'quoted atoms'`.
* Russian built-in predicate names (`БОЛЬШЕ`, `СЛОЖЕНИЕ`, `НАЙТИВСЁ`, …) are
  reserved atoms.
* Clauses end with `.` or `;`; rules use `:-` or `<-`; queries start with `?`.
* Arithmetic expressions are written `#expr#` and support `+ - * / mod div`.
* Lists: `[a, b | T]`, `[]`.

See `doc/help.typ` for the full reference and `doc/prologd-diff.typ` for the
differences from the original PrologD (most importantly: single-letter
variables are gone, and CP1251 was replaced by UTF-8).

## Command line

```
Usage: prologd [options] [files...]

-s, --source FILE     interpret a source file (repeatable)
-I, --include DIR     add a module search directory
-i, --input FILE      read program input from this file
-o, --output FILE     write program output to this file
-e, --error FILE      write diagnostics to this file
-q, --questions       echo queries before executing them
-t, --trace           start with tracing enabled
-h, --help            show help and exit
    --version         show version and exit
```

Source files can also be given as positional arguments:

```sh
prologd examples/findall_demo.pld
prologd --source examples/findall_demo.pld
```

Lines starting with `$` in a source file are preloaded as program input (the
historical test-harness feature). Diagnostics use the usual compiler format:
`file:line:column: error: message`.

## Project layout

```
CMakeLists.txt        top-level build
CMakePresets.json     configure/build/test presets (Linux, Windows)
src/prlib/            interpreter library
src/cli/              console front-end
src/tests/            Catch2 test suite and CLI integration tests
src/3rdparty/         FetchContent dependencies (gitignored)
doc/                  Typst documentation (Russian)
examples/             example PrologD programs
.github/workflows/    CI (Linux GCC/Clang, Windows MSVC)
ai/                   local plan/tasks/notes (gitignored, not versioned)
```

## Status

Implemented: lexer, parser with diagnostics, unification with trail, the
resolution engine (backtracking, cut, meta-call, negation, disjunction),
arithmetic with a hand-written `BigInt`, all documented built-in predicate
groups (control, types, conversions, strings, I/O, program database, graphics
stubs), `НАЙТИВСЁ/3`, the module loader (`ИМПОРТ`) and the CLI.

Ported examples live in `examples/` (lessons, typical tasks, the teacher's
`НАЙТИВСЁ` demo) and are covered by golden tests. Documentation is in `doc/`
(`help.typ`, `technical.typ`, `prologd-diff.typ`); build the PDFs with
`cmake --build build --target docs` when Typst is installed.

CI builds and tests on Linux (GCC and Clang) and Windows (MSVC); see
`.github/workflows/ci.yml` and `CMakePresets.json`. Current status and the task
board are kept in the local (unversioned) `ai/status.md`.
