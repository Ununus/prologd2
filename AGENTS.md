# AGENTS.md

Short instructions for coding agents.  The full record lives in `ai/` — read
`ai/README.md` first for the order (plan → decisions → conventions → status).
This file stays short on purpose: it is loaded into every request.

## What this repository is

A Prolog-D implementation, «Пролог-У»: the engine in `src/prlib`, the console
front-end `prologu`, and the PySide6 window in `src/gui`.  Windows appends `.exe` to
the program names.  `doc/*.typ` are the Russian manuals; `ai/` is the agent's journal,
not user documentation.

## Build and test

One command shape everywhere; only the preset name differs:

```sh
cmake --preset linux-release
cmake --build --preset linux-release
ctest --preset linux-release
```

Presets: `linux-release` (Ninja, Release), `linux-debug`, `linux-werror` (the same
build with `PROLOGD_WERROR=ON`; it has no test preset — `ctest --test-dir
build/linux-werror`), `windows-msvc` (Visual Studio, x64), `windows-ninja` and
`macos-release` (deployment target 14.4).  They fix the generator, the configuration
and the build folder (`build/<preset>`, gitignored), so no platform-specific flags are
needed; the multi-config Windows preset already passes `--config Release` through its
build and test presets.

GUI checks — every `src/gui/tests/test_*.py` plus `protocol_smoke.py` is a script of
its own (30 of them), and each needs a built interpreter:

```sh
export QT_QPA_PLATFORM=offscreen PYTHONUTF8=1
export PROLOGD_TEST_EXE=$PWD/build/linux-release/src/cli/prologu
.venv/bin/python src/gui/tests/test_window.py
```

PowerShell spells the same with `$env:QT_QPA_PLATFORM='offscreen'`,
`.venv\Scripts\python.exe` and `build\windows-msvc\src\cli\Release\prologu.exe`.
`.venv` in the repository root is the build Python: `src/gui/requirements.txt`, plus
`src/gui/requirements-build.txt` for PyInstaller.

Manuals: `cmake --build --preset <preset> --target docs` (needs Typst on `PATH`;
without it the target says so and builds nothing).  A PDF lands beside its `.typ` —
look at the changed pages.

Packages, one script per platform:

* Linux: `tools/build_deb.sh` (`--skip-tests`, `--skip-docs`, `--skip-freeze`,
  `--no-trim`) → `dist/prologd_<version>_amd64.deb`.
* Windows: `tools/build_portable.ps1`, then `tools/build_installer.ps1
  -SkipPackage` → `dist\prologd-<version>-win64.zip` and
  `dist\prologd-<version>-setup.exe`.
* macOS: the `.dmg` is built by `.github/workflows/release.yml` on a runner, not by
  hand.

A tag `v*` runs `release.yml`, which builds all three platforms and opens a **draft**
release; `ci.yml` (Linux, Windows) and `macos.yml` test every push to `main`.

## Rules that bite

* Sources are UTF-8 with **LF**.  Check after editing: `git ls-files --eol <file>`.
  The exception is `installer/prologd.iss`, which must keep its **BOM**: Inno reads a
  BOM-less script as ANSI and the Cyrillic turns to rubbish.
* `.pld` programs under `examples/` and `stdlib/` stay within the alphabet of the
  previous dialect: no `—`, `–`, `−`, `…`, `№`, `§`.  Write `-` and `...`.  (The
  engine itself reads them anywhere; the rule keeps the corpus comparable with the
  upstream snapshot in `examples/prologd/`.)
* PowerShell scripts here print **ASCII only** (PowerShell 5.1 reads a BOM-less script
  as ANSI).
* Do not edit `examples/prologd/` (byte-for-byte upstream), `src/3rdparty/` or
  `ai/_ref/`.
* Never pass multi-line Python to `powershell -c` or a here-string: the shell mangles
  quotes and hanging strings.  Write the snippet to a file and run the file.
* The version lives in `CMakeLists.txt` (`project(... VERSION ...)`).  The numbers in
  `installer/prologd.iss`, `tools/build_installer.ps1` and `doc/help.typ` are a
  default and two examples — bump them with it.  Packaging reads the version from
  `prologu --version`, never from a second copy.
* Records: after a session append a numbered part to `ai/status.md` (the number
  continues the last one) and update the task file; non-obvious choices go to
  `ai/decisions.md`.  Journal and code comments are English; `doc/*.typ`, lesson texts
  and diagnostics are Russian.
* Commit only when the user asks.  Commit messages are Russian, written through a
  UTF-8 file (`git commit -F`).
