# AGENTS.md

Short instructions for coding agents.  The full record lives in `ai/` — read
`ai/README.md` first for the order (plan → decisions → conventions → status).
This file stays short on purpose: it is loaded into every request.

## What this repository is

A Prolog-D implementation with **two engines**: ours, «Пролог-У» (`src/prlib`,
`prologu.exe`), and the original «Пролог-Д» (`prologd.exe`) built from the commit
pinned in `CMakeLists.txt` (`PROLOGD_ENGINE_COMMIT`, option `BUILD_WITH_PROLOGD`).
The PySide6 window (`src/gui`) hosts both; `doc/*.typ` are the Russian manuals.
`ai/` is the agent's journal, not user documentation.

## Commands

```powershell
cmake --preset windows-msvc
cmake --build build/windows-msvc --config Release
ctest --test-dir build/windows-msvc -C Release            # 378 tests
```

GUI checks — every `src/gui/tests/test_*.py` and `protocol_smoke.py` is a script of
its own:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; $env:PYTHONUTF8='1'
$env:PROLOGD_TEST_EXE=(Resolve-Path 'build\windows-msvc\src\cli\Release\prologu.exe').Path
.venv\Scripts\python.exe src\gui\tests\test_window.py
```

Manuals: `cmake --build build/windows-msvc --config Release --target docs`
(Typst is on `PATH`; a PDF lands beside its `.typ` — look at the changed pages).

Portable package: `.\tools\build_portable.ps1 -Engine both|u|d`.  `d` is the
original engine alone (`dist\prologd-1.27-win64`); its behaviour differences are the
`$kinds` table at the top of the script.

## Rules that bite

* Sources are UTF-8 with **LF**.  Check after editing: `git ls-files --eol <file>`.
* `.pld` programs stay within the alphabet the *original* engine reads: no `—`, `–`,
  `−`, `…`, `№`, `§` — it refuses them even inside comments.  Write `-` and `...`.
* `tools/build_portable.ps1` prints **ASCII only** (PowerShell 5.1 reads a BOM-less
  script as ANSI).
* Do not edit `examples/prologd/` (byte-for-byte upstream), `src/3rdparty/` or
  `ai/_ref/`.
* Never pass multi-line Python to `powershell -c` or a here-string: the shell mangles
  quotes and hanging strings.  Write the snippet to a file and run the file.
* Records: after a session append a numbered part to `ai/status.md` (the number
  continues the last one) and update the task file; non-obvious choices go to
  `ai/decisions.md`.  Journal and code comments are English; `doc/*.typ`, lesson
  texts and diagnostics are Russian.
* Commit only when the user asks.  Commit messages are Russian, written through a
  UTF-8 file (`git commit -F`).
