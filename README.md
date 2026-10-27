# prologd2

<p align="center">
  <img src="doc/prologd2.png" width="64" height="64" alt="Логотип Пролог-Д">
</p>

Переписанный интерпретатор логического программирования **PrologD** на C++23: синтаксис, близкий к ISO, нативная поддержка UTF-8 и встроенные предикаты на русском языке. Новый графический интерфейс на PySide6.

## История

Пролог-Д — учебная реализация Пролога для персональных компьютеров с
ограниченными ресурсами. Основные работы:

1. Григорьев С. Г., Морозов М. М. Давайте попробуем Пролог // Информатика и
   образование. — 1987. — № 4. — С. 14–17.
2. Григорьев С. Г. Реализация системы логического программирования для
   персональных компьютеров с ограниченными ресурсами и её применения:
   диссертация на соискание учёной степени доктора технических наук по
   специальности «Математическое и программное обеспечение вычислительных
   машин, комплексов и компьютерных сетей». — 1992.

Исходный код оригинального Пролог-Д: <https://github.com/Ununus/prologd>.

## Linux .deb пакет
### Установка
```sh
sudo apt install dist/prologd_<version>_amd64.deb
```
Запуск
```sh
/opt/prologd/prologu --version
prologd-gui
# Открыть первый урок
prologd-gui /opt/prologd/examples/lessons/lesson_01.pld
# Файл настроек (после первого запуска)
ls ~/.config/PrologD/gui/gui.ini
```
### Удаление
```sh
sudo apt remove prologd
```
Настройки (`~/.config/PrologD/gui/gui.ini`) пакет не трогает. Если нужно удалить и их:
```sh
rm -f ~/.config/PrologD/gui/gui.ini
rmdir ~/.config/PrologD/gui ~/.config/PrologD
```
`apt remove` оставляет запись dpkg в состоянии `rc`; `sudo apt purge prologd` убирает и её.

## Обзор языка

```prolog
% факты
студент(вова, корчагин).
студент(данил, ахмеров).

% запрос (переменные начинаются с заглавной буквы)
?НАЙТИВСЕ(Имя, студент(Имя, Фамилия), Список).
% Список=[вова,данил]
```

* Переменные: `Name`, `_Name`; `_` — анонимная.
* Атомы: имена со строчной буквы или `'атомы в кавычках'`.
* Строка — отдельный тип, который **унифицируется** с атомами.
* Поддерживаются английские псевдонимы стандартных предикатов: `findall`, `bagof`, `sub_string` и другие.
* Русские имена встроенных предикатов из оригинального Пролог-Д (`БОЛЬШЕ`, `СЛОЖЕНИЕ`, `НАЙТИВСЕ`, …) —
  зарезервированные атомы.
* Предложения заканчиваются `.`; правила записываются через `:-`; запросы начинаются с `?` или `?-`, `;` — дизъюнкция.
* Поддерживаются арифметические выражения двух видов `X = #выражение#` и `X is выражение`,
  операторы `+ - * / mod div`.
* Списки: `[a, b | T]`, `[]`.

Полный справочник — в `doc/help.typ`.

### Примеры программ

* В каталоге `examples/` лежат демонстрационные примеры.
* `examples/lessons/` содержит двенадцать уроков.
* Подробнее: `examples/README.md` и `examples/lessons/README.md`.

### Стандартная библиотека

* `stdlib/` содержит библиотеку, которая поставляется с данным диалектом.
* `stdlib/iso.pld` реализует часть предикатов ISO в виде библиотечных предикатов.
* Подключается директивой `:- ИМПОРТ("iso.pld").`
* В `examples/stdlib.pld` можно посмотреть работу со стандартной библиотекой.
* Подробнее: `stdlib/README.md`.

# Development

## Quick start

```sh
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build
```

The console interpreter is `build/src/cli/prologu`.

```sh
# Run a program file
./build/src/cli/prologu -s examples/findall.pld
# Or read the program from stdin
./build/src/cli/prologu < examples/findall.pld
# Help
./build/src/cli/prologu -h
```

Start the GUI:
```sh
python ./src/gui/main.py
```

Run the tests:
```sh
python3 -m venv .venv
.venv/bin/pip install -r src/gui/requirements.txt
export QT_QPA_PLATFORM=offscreen
export PROLOGD_TEST_EXE=$PWD/build/linux-release/src/cli/prologu
.venv/bin/python src/gui/tests/test_window.py
.venv/bin/python src/gui/tests/protocol_smoke.py
```

### Windows

Prerequisites: Git, CMake 3.24 or newer, and Visual Studio 2026 with the
"Desktop development with C++" workload. The first configure downloads Catch2
and CLI11 through CMake FetchContent, so it needs network access. The build and
the portable package (task_61) require Windows 10 (1903) or newer, 64-bit: the
UTF-8 manifest element (`<activeCodePage>`) is understood from 1903; the window needs Windows 10
because of Qt 6 and Python 3.14.

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

The portable package is built by one script:
```powershell
powershell -ExecutionPolicy Bypass -File tools\build_portable.ps1
```
Additional options:
* `-SkipTests` — do not run `ctest`
* `-SkipFreeze` — do not rebuild the GUI
* `-NoTrim` — do not discard unnecessary Qt modules
* `-NoZip` — do not create a zip archive

It runs the Release build, `ctest`, the `docs` target and PyInstaller (`--onedir`,
leaving out the Qt modules the window never loads), lays out the folder as
`dist\prologd-<version>-win64` with the Visual C++ runtime beside the executables,
checks it (`tools/check_dependencies.py`, plus the interpreter and the window itself)
and writes the zip.

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
    --vars 0|1        how names are read: 0 = ISO (default), 1 = the old dialect
    --no-warnings     do not print warnings (they never change the exit code)
    --max-depth N     recursion depth limit for one query (0 = unlimited)
    --max-steps N     step limit for one query (0 = unlimited)
    --max-findall N   solution limit for one НАЙТИВСЕ (0 = unlimited)
    --format[=MODE]   print the source formatted and exit: soft, hard or line
    --format-width N  soft mode: what has to fit on one line (default 80)
    --format-indent N continuation indent in units (default 1)
    --format-unit U   indent unit: tab (default) or spaces
    --names 0|1|2     print the source with its names in the other mode and exit
    --dialect ru|en   print the built-in names and their signs in the other
                      language and exit
    --protocol FORM   front-end protocol: text (default) or json
    --list-keywords   print the reserved names as name/arity and exit
-h, --help            show help and exit
    --version         show version and exit
```

Source files can also be given as positional arguments:

```sh
prologu examples/findall.pld
prologu --source examples/findall.pld
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
`src/gui/README.md` for the full contract. The contract is at version **16** —
a front-end can read the number from `ready` and know what it is talking to.
Version 2 added the reserved names and their arities to `ready`, so a front-end
never keeps its own copy of the built-in list (`prologu --list-keywords` prints
the same table); the later versions are listed one by one in the contract.

## Project layout

```
CMakeLists.txt        top-level build
CMakePresets.json     configure/build/test presets (Linux, Windows, macOS)
src/prlib/            interpreter library
src/cli/              console front-end
src/gui/              PySide6 front-end (drives the CLI over the JSON protocol)
src/tests/            Catch2 test suite and CLI integration tests
src/3rdparty/         FetchContent dependencies (gitignored)
doc/                  Typst documentation (Russian)
examples/             example PrologD programs (demo, problems, lessons, lib)
stdlib/               standard library, shipped beside the executable
.github/workflows/    CI (Linux GCC, Windows MSVC, macOS AppleClang)
ai/                   plan, task breakdown and notes for the AI agent
```

## Status

The working folder of the AI agent that
built this rewrite — plan, task breakdown, architecture decisions and the
development journal, in English — is `ai/`; it is developer material, not user
documentation. User and technical documentation is in `doc/` (Russian, Typst).

Implemented: lexer, parser with diagnostics, unification with trail, the
resolution engine (backtracking, cut, meta-call, negation, disjunction),
arithmetic with a hand-written `BigInt`, all documented built-in predicate
groups (control, types, conversions, strings, I/O, program database, graphics
stubs), `НАЙТИВСЕ/3` with `ВСЕРЕШ/3` (`bagof`) and `МНОРЕШ/3` (`setof`), the
module loader (`ИМПОРТ`) and the CLI.

Examples live in `examples/` — one demo per predicate of the language surface, the
problems (`factorial`, the Hanoi tower, `knapsack`), the lessons and the library —
and are covered by golden tests: a lesson or a demo carries its own expected output
in `%!` lines, and `src/tests/test_lessons.cpp` compares the two.  The library the
dialect ships is in `stdlib/`, beside the executable, and has its own runnable tour
(`examples/stdlib.pld`) checked the same way. The PySide6 front-end in
`src/gui` drives the interpreter through the JSON protocol: tabs, syntax
highlighting that tells Latin names from Cyrillic ones, completion built from
the reserved names and the program's own, run/stop with a fresh interpreter per
run, and the usual file handling (save prompts, line endings and encodings kept).
Documentation is in `doc/` (`help.typ`, `library.typ`, `gui.typ`, `technical.typ`,
`lessons.typ`); `cmake --build build --target docs` writes the PDFs into the same
directory when Typst is installed.

CI builds and tests on Linux (GCC), Windows (MSVC) and macOS (AppleClang); see
`.github/workflows/ci.yml`, `.github/workflows/macos.yml` and `CMakePresets.json`.
Current status and the task board are kept in `ai/status.md`.

## License

MIT — see [LICENSE](LICENSE).
