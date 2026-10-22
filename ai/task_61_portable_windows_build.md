# task_61 — portable Windows build

**Status:** in progress (2026-10-04) — everything is built and checked except the
manual GUI clicks (§7.1) and the clean machine, which the user confirmed on
2026-10-03; the folder and the zip are made by `tools/build_portable.ps1` (§6).  The
installer is the next task (§8.8).
**Depends on:** task_16 (`-s`, `-I`, `--version`, `--list-keywords`), task_17 and
task_35 (the `docs` target — five PDFs), task_45 (graphics window), task_46
(`execution/interpreter`, `execution/import_paths`), task_58–60 (the window as it
stands), ADR-013 (MSVC 2026 — the build we ship)
**Milestone:** M17 (portable build; the line was added to `plan.md` §5)

## Goal

One folder, copied to a clean Windows machine — **no Python, no Qt, no Visual
Studio, no source tree** — and it works:

```
prologd-2.0.0-win64\
  prologd.exe          interpreter (console, UTF-8, --version → 2.0.0)
  vcruntime140.dll     the Visual C++ runtime — three DLLs beside the exe (§2)
  vcruntime140_1.dll
  msvcp140.dll
  prologd-gui.exe      the graphics window
  _internal\           whatever the freezer puts there (Python, Qt, Qt plugins)
  gui.ini              window settings — beside the exe, not in AppData (§4)
  doc\                 five PDFs (help, technical, prologd-diff, gui, lessons)
                       and their *.typ sources beside them (§5)
  examples\            lessons, typical tasks, lib (no lessons\_old)
  ЧИТАЙ_МЕНЯ.txt       a dozen lines: how to start, where the settings live,
                       what to require
```

Done means §7 (a machine without build tools), not "it built without errors".

## User decisions (2026-10-03)

Short: PyInstaller with `--onedir`, the Visual C++ DLLs beside the exe, `_old` is not
shipped, `doc/*.typ` **is** shipped, `gui.ini` sits beside the exe in the portable
build, `examples/lib` is shipped but **is not added to the import search path**
(lesson 11 asks the reader to add the directory by hand — the earlier decision was
reverted on 2026-10-03, see §4), the folder is `prologd-2.0.0-win64`, plus a zip.
The full list is §8 and is what §2, §4, §5 and §6 implement; the installer stays open
and is the next task, not this one.

## Facts this rests on (checked 2026-10-03 on this machine)

* `prologd.exe` is 944 KiB; its import table names `VCRUNTIME140.dll`, `MSVCP140.dll`
  and `api-ms-win-crt-*`.  Two of those are files we ship (§2), while
  `api-ms-win-crt-*` are API-set names, not files: Windows resolves them through
  `apisetschema.dll`, and the UCRT itself is part of Windows 10 (checked here: zero
  `api-ms-win-*.dll` files in `System32`, `ucrtbase.dll` present).  On Windows 7 the
  UCRT would have to be installed separately — §9.
* The UTF-8 manifest is **baked into** the exe (`src/utf8.manifest` is handed to the
  linker; the image contains the string `activeCodePage`), so no separate `.manifest`
  is shipped.
* No path of the build tree leaked into the exe (checked by searching for the string).
* The window is Python 3.14.5 + PySide6 6.11.2 — this machine's `.venv`.  **Neither
  PyInstaller nor Nuitka, cx_Freeze or `pyside6-deploy` is installed**, so a freezer
  has to be added (into `.venv`, through a separate requirements file — not
  `src/gui/requirements.txt`, which students read).
* PyInstaller 6.22.3 (PyPI): Python 3.8–3.15 (3.14 fits), PySide6 works out of the
  box, it copies the Visual C++ DLLs itself, and there is **no cross-compilation** —
  a Windows build is made on Windows (which suits us: the build is on Windows anyway).
* `src/gui/assets/prologd2.ico` is already in the repository (16 958 bytes), so the
  exe icon exists.
* Three paths inside the window are computed **from the source tree** and would find
  nothing in a frozen build (this is what §4 fixes):
  * `main.py:default_executable()` — `build/windows-msvc/.../prologd.exe` from
    `Path(__file__).resolve().parents[2]`;
  * `assets.DEFAULT_DIRECTORY` = `Path(__file__).resolve().parent.parent / "assets"`
    (the module docstring already noted that a frozen build would look inside
    `sys._MEIPASS`);
  * `window._open_document` — `Path(__file__).resolve().parents[3] / "doc" / f"{name}.pdf"`
    (that is `Shift+F1`, the manual and the other documents).
* Window settings: `%LOCALAPPDATA%\PrologD\gui\gui.ini`, with `--settings FILE`
  overriding the path (`settings.py`, `main.py`).
* `examples/lib` is the search directory for lesson 11; in the window it is the
  `execution/import_paths` field.  It is shipped (the lesson enables it), but the
  window does not add it to the search list (§4).
* The PDFs are **not in git**: the `docs` target makes them (`typst`, 0.15.1 here), so
  they have to reach the package built, not from the repository.
* A "clean machine" cannot be imitated locally: this machine's `System32` has
  `vcruntime140.dll` and `msvcp140.dll` 14.51 (Visual Studio is installed), so a
  forgotten DLL would not show up here.  Hence §7: a static import check plus Windows
  Sandbox or a virtual machine.

---

## §1. The layout of the package and what goes into it

**In it** (§8): `prologd.exe` with the three Visual C++ DLLs beside it, the window
with its own runtime, five PDFs **and their `doc/*.typ` sources** (the package
explains itself), `examples/**` without `examples/lessons/_old/` (that is porting
material, not a lesson), `ЧИТАЙ_МЕНЯ.txt`, and the zip of the
`prologd-2.0.0-win64` folder.

**Deliberately not in it** (§8): the installer (the next task), code signing,
auto-update, a Linux build, and static Qt linking (which would drag in the LGPL/GPL
question — Qt stays a DLL beside the exe, as in every PySide6 build).

## §2. The interpreter: the Visual C++ DLLs beside the exe

**User decision: ship the DLLs beside the exe to start with.**  The build does not
change at all; three files go into the package folder — `vcruntime140.dll`,
`vcruntime140_1.dll`, `msvcp140.dll` from
`…\VC\Redist\MSVC\14.51.36231\x64\Microsoft.VC145.CRT\`.  Copying them is a step of
the §6 script, not manual work.

**Alternative for later** (not in this task): a static CRT — one line in
`CMakeLists.txt`,
`set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")`, and the exe
is self-contained.  If the three files are to go after the first package, that is a
separate measurement: whether Catch2 and CLI11 still build, whether `ctest` stays
307/307, and how the exe size changes.

**Check (§7.3):** every name in the import table of `prologd.exe` is either a system
name (`api-ms-win-*`, `KERNEL32`, …) or a file of the package folder.

## §3. The window: PyInstaller (recommendation) and the alternatives

**The recommendation is PyInstaller with `--onedir` (a folder, not `--onefile`).**
Reasons: official hooks for PySide6, Python 3.14 supported, it copies the Visual C++
DLLs itself, `--onedir` does not unpack into `%TEMP%` on every start (it starts
faster, and the folder stays what the user sees), and antivirus software objects to
`--onefile`.  The starting command:

```
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean --onedir --windowed ^
    --name prologd-gui --icon src\gui\assets\prologd2.ico ^
    --add-data "src\gui\assets;assets" ^
    --paths src\gui  src\gui\main.py
```

`--windowed` removes the console (otherwise a black window flashes on start), so the
window must not depend on stdout — and it does not (diagnostics go to a panel).  Keep
a `--console` variant beside it for debugging a build.

**Alternatives** (to be written into an ADR with the reason for rejecting them):
**Nuitka** (`--standalone --enable-plugin=pyside6`) compiles, starts faster, but
builds much longer and needs a compiler; **cx_Freeze** is simpler and has fewer Qt
hooks; **`pyside6-deploy`** is Qt's wrapper around Nuitka.  All three produce the same
folder, so switching later does not touch §4.

**Also:** the name `prologd-gui.exe` beside `prologd.exe` is how the window finds the
interpreter without settings (§4), and the user sees two understandable programs.

**First run (2026-10-03).**  `pip install -r src/gui/requirements-build.txt` (a new
file, so that it is not confused with `requirements.txt`, which students read), then
the command above: a **27 s** build, `dist/prologd-gui` at **112.9 MiB**, 252 files,
`prologd-gui.exe` 2.3 MiB.  All 47 icons and `prologd2.png` landed in
`_internal/assets`, so `paths.resource("assets")` works in a frozen build.  Together
with `prologd.exe`, the DLLs, `doc`, `examples` and the read-me the folder became
`dist/prologd-2.0.0-win64`, **297 files, 116.3 MiB**.

**With the script (2026-10-03).**  The same package after the trim (§6) is **280 files,
95.4 MiB** — 20.9 MiB lighter; the zip is **37.5 MiB**.  After the first-page logos
went into the documents the package is **282 files, 95.5 MiB** and the zip **37.7 MiB**.
The big remainder is deliberate: `opengl32sw.dll` 19.7 MiB (the software OpenGL
fallback), `Qt6Core` 9.9 + `Qt6Gui` 9.1 + `Qt6Widgets` 6.2 and `python314.dll` 6.5.
`libcrypto-3.dll` (5.0) and `libssl-3.dll` also stayed: Python's `_ssl.pyd` pulls them,
not Qt, and dropping half a module/library pair for six megabytes was not worth it.

## §4. Code changes: the layout instead of the source tree

One small module (say `src/gui/prologd_gui/paths.py`) with two functions —
`data_root()` (beside the exe in a frozen build, the repository root in the sources)
and `resource(name)` (inside `sys._MEIPASS` for data the freezer added) — and the
places from the facts move onto it:

* `default_executable()`: the **first** candidate is `prologd.exe` beside the window,
  then the old build paths (so working in the sources does not change at all);
* `assets.DEFAULT_DIRECTORY`: `sys._MEIPASS/assets` if the freezer put it there;
* `_open_document`: `<data_root>/doc/<name>.pdf`; when the file is missing, the
  message must name *this* path, not a path in the build tree;
* `reference.DEFAULT_PATH`: `doc/builtins.json` — the window **reads** it too (`F1` and
  the completion summaries), so it is looked up through `paths.builtins()` and travels
  in the package with the documents.  §4 was about three places, but there were four:
  `doc/builtins.json` turned up while doing the work;
* **Settings (user decision):** in a frozen build `gui.ini` sits beside the exe; in the
  sources it stays where it was, `%LOCALAPPDATA%\PrologD\gui\`.  The marker is
  `getattr(sys, "frozen", False)`; no new key.  A future installer will take AppData
  back for itself (or get a key of its own) when it arrives;
* **The import directory (user decision, final on 2026-10-03):** the window adds
  **nothing** to the search list — only what the user gave it (`--include` and the
  "additional import directories" field), and the directory of the importing file is
  tried by the engine before them.  `paths.import_directories` stays the single place
  where the list is cleaned: empty lines are dropped, duplicates are merged.
  * History: at first `examples/lib` was written into `gui.ini` on the first start —
    that turned out to be bad, because the folder gets copied around (memory stick →
    computer → back, the drive letter changes) and the recorded absolute path points
    at the old copy.  Then `<data_root>/examples/lib` was substituted on every start —
    nothing was remembered any more, but the substitution stayed invisible to the
    reader.
  * Reverted at the user's request: lesson 11 now says itself that the library
    directory has to be added by hand ("Правка → Настройки… → Выполнение →
    Дополнительные каталоги ИМПОРТ"), and that is **clearer for a student** — he sees
    the line he filled in and the path he chose.  The side benefit is the same as with
    deriving the path from `data_root()`: no absolute path is left in a setting to go
    stale when the folder moves.  The price: out of the box lesson 11 does not work
    until that step is done (it is described in the lesson, in
    `tools/portable-readme.txt` and in the package's `README.md`);

**Check (done):** `src/gui/tests/test_paths.py` — seven cases with `sys.frozen` /
`sys.executable` / `sys._MEIPASS` faked (a frozen build and the source tree, a missing
interpreter, the icons, the built-in reference, "a frozen build adds nothing of its
own" to the import line), plus a case in `test_window.py`: the window opens a PDF from
the package's `doc/`.  The other GUI suites stay green.

## §5. Documents and examples

* The five PDFs from the `docs` target go into the package's `doc/` (built before
  freezing: without `typst` the package would come out without documentation, and that
  must be a build error, not a silent skip).
* `doc/*.typ` goes beside the PDFs (user decision): the package explains itself, and
  `typst` is not needed to read it.  The two first-page logos travel with them
  (`prologd2.png`, `csu.png`) — without them the shipped sources do not compile.
* `doc/builtins.json` is mandatory: without it the `F1` reference and the completion
  summaries work but stay silent (the window tolerates a missing file on purpose).
* `examples/` — lessons, typical tasks, `lib/`; **`lessons/_old/` is not shipped**
  (user decision: that is porting material, not a lesson).
* The read-me `ЧИТАЙ_МЕНЯ.txt`: how to start the window and the interpreter, where
  `gui.ini` lives, that the window finds `prologd.exe` beside itself, that the lessons
  open from `examples`, and that **Windows 10 (1903) or newer, 64-bit** is required —
  and why (§9).

## §6. The build script

`tools/build_portable.ps1` (next to `check_dependencies.py` and `bench_engine.py`),
steps: Release build → `ctest` → `docs` → check that the PDFs are there → PyInstaller →
lay out the package → copy `prologd.exe`, the three DLLs, `examples`, `doc` (PDFs and
`.typ`) and the read-me → read the version (`prologd.exe --version`) and name the
folder `prologd-<version>-win64` (for 2.0.0 that is `prologd-2.0.0-win64`) → run the
automatable checks of §7 → zip the folder into `prologd-2.0.0-win64.zip` (the zip is a
user decision, it is wanted).

**Done (2026-10-03).**  The script is written and ran end to end; its parameters are
`-Configuration`, `-CrtDirectory` (by default the newest `Microsoft.VC*.CRT` under
Visual Studio), `-Version`, plus `-SkipTests`, `-SkipFreeze`, `-NoTrim`, `-NoZip` for a
short round.  What it checks itself (§7): the interpreter answers `--version` and lists
122 keyword lines, lesson 1 and `import_demo.pld` with `-I examples\lib` end with exit
code 0, `check_dependencies.py` finds no suspicious imports, and the window starts
(with `QT_QPA_PLATFORM=offscreen`, so nothing flashes on the desktop) and writes
`gui.ini` beside itself — the script then deletes that file, so the package travels
without it.

**The trim, and why `--exclude-module` is not enough.**  The PySide6 hook puts every Qt
module into the build, and a QWidget window never loads some of them.  A standard
exclusion (`--exclude-module`) only removes the `qml/` directory (1.7 MiB) and QML/Quick
(12.5 MiB in 5 files), `Qt6Pdf` (4.4 MiB), `Qt6VirtualKeyboard` and `Qt6Network` with TLS
(`libcrypto-3.dll`, 5.0 MiB) — about **27 MiB of 110** — while the DLLs themselves stay:
measured, `Qt6Qml`, `Qt6QmlModels`, `Qt6QmlMeta`, `Qt6QmlWorkerScript`, `Qt6Quick`,
`Qt6Pdf`, `Qt6VirtualKeyboard` and `Qt6Network` all remained.  So the script removes them
(and the three plugins that are useless without them — `qtvirtualkeyboardplugin.dll`,
`imageformats\qpdf.dll`, `generic\qtuiotouchplugin.dll`) **by name from the laid-out
package**: **19.2 MiB** in total.  Two independent judges assess the trim:
`check_dependencies.py` (its first run without this step reported exactly two SUSPECTS —
`qpdf.dll` and `qtuiotouchplugin.dll`, exactly the ones removed) and the offscreen start
of the window, where an excess trim shows up as "SUSPECTS" (`Qt6Gui` or `qwindows.dll`
referring to a dropped file).  `opengl32sw.dll` (19.7 MiB) stays on purpose: it is the
software OpenGL fallback for a machine without a working driver — a school computer, a
virtual machine or RDP.

**Two traps for whoever edits the script.**  First: `Get-ChildItem` with a wildcard
inside the path returns matches of that path, not the contents of the directory it
names; and `-Filter 'Microsoft.VC*.CRT'` (a Win32 mask) found nothing where
`Where-Object { $_.Name -like … }` did.  The second one is nastier: a loop variable
named like a typed script parameter is coerced to that type — `foreach ($version in …)`
with `[string]$Version` turned a `DirectoryInfo` into a string, so `$version.FullName`
was empty, and the error pointed at a different line ("Cannot bind argument to parameter
'Path'").  The variable is now `$redistVersion`, and the header has a `trap` that prints
the file and the line number.

**Checked by hand (what the script is supposed to do).**  Order: PyInstaller → a copy of
`prologd.exe`, three DLLs from `…\VC\Redist\MSVC\14.51.36231\x64\Microsoft.VC145.CRT\`,
five PDFs with their `.typ` and `doc/builtins.json`, `examples` without `lessons/_old`,
`tools/portable-readme.txt` → `ЧИТАЙ_МЕНЯ.txt`, the folder name from
`prologd.exe --version`.  Notes for the future: copy the PDFs **by name**, not "all
`.pdf`" — a stray `doc/style.pdf` from an old target was in the tree (now deleted) and
rode into the first build; the read-me and the dependency checker are written once (in
`tools/`), not generated by the script.

**The first start in a new place (measured 2026-10-03).**  The user noticed that the
first start takes about five seconds and later ones are faster.  Measured here: in an
already used folder the window is ready in **0.16–0.19 s**, in a freshly copied one the
first start takes **0.43 s**, then 0.17 s.  The effect is the same, only the disk here is
fast: the first start of a *new copy* reads every file (296 files, 110 MiB at the time of
the measurement; the package is now 282 files, 95.5 MiB) from the disk, and antivirus
(Windows Defender) inspects every `.exe`/`.dll`/`.pyd` once; the second start takes
everything from the OS cache and remembers the verdict.  From a memory stick, or from a
folder the Sandbox has just copied, reading is tens of times slower — those are the
seconds.  Our own work on the first start is measured and negligible:
`prologd --list-keywords` 0.00–0.01 s (one child process at start), writing `gui.ini`
(the paste table, a few dozen KB).  And `--onedir` unpacks nothing: `--onefile` would
unpack 110 MiB into `%TEMP%` on **every** start.

## §7. Checks (the heart of the task)

1. **Copy elsewhere.**  Put the folder in `%TEMP%\prologd-portable` and start it there:
   the window must find `prologd.exe` beside itself, find nothing in the source tree,
   and work (open lesson 1, `F5`, click a marker, `drawing.pld` and the graphics
   window, "About", `Shift+F1` — a PDF **from the package**, `F1` on a built-in name —
   the entry from the package's `doc/builtins.json`).
2. **The interpreter alone.**  From `cmd.exe` (not PowerShell — it encodes pipes as
   ASCII): `prologd.exe --version` → `2.0.0`; `--list-keywords` → 110 names;
   `prologd.exe -s examples\lessons\lesson_01.pld` — the output matches the lesson's
   `%!` lines; `prologd.exe -I examples\lib -s examples\import_demo.pld` → `Дважды=42`.
3. **Dependencies, statically.**  Parse the import table of `prologd.exe` with a Python
   script and check that every name is either a system name (`api-ms-win-*`,
   `KERNEL32`, …) or a file of the package.  The same for `prologd-gui.exe` in
   `_internal`.
4. **Nothing from the tree.**  Search the package files for strings with this
   repository's path (`C:\Users\...\prologd2`) — there must be none; if they turn up
   inside Qt or Python `.pyc` files, explain where exactly and why it is not a path to
   our data.
5. **A machine without tools.**  Windows Sandbox (if the edition allows) or a virtual
   machine: copy the folder, start the window, run lessons 1 and 11; also record the
   version of the checking system — it must be Windows 10 1903 or newer, otherwise the
   check says nothing about the systems we support (§9).  **On the developer machine
   this check does not exist** — the Visual C++ DLLs are in `System32`, and Qt/Python
   sit next to the sources too.
   **Confirmed by the user on 2026-10-03:** a clean Windows 11 in Windows Sandbox,
   build 24H2 26100.9457 — "it started and works"; and **Windows 10 22H2**, build
   19045.6456 — "it started and worked".  Those are exactly the two systems §9 limits
   us to (19045 ≥ 1903, so the UTF-8 manifest is understood).
6. **The sources are not broken.**  The usual checks on the tree: `ctest` 307/307, the
   23 `.py` suites of `src/gui/tests` plus `protocol_smoke.py`, and `docs` (`typst`
   exits 0).

**What is already checked (2026-10-03).**  §7.2 — `prologd.exe --version` = `2.0.0`,
`--list-keywords` = 122 `name/arity` lines (110 distinct names), lesson 1's output
matches its `%!` lines (16 of 16).  §7.3 — `tools/check_dependencies.py`: "every
non-system import is a file of the package", no suspects.  §7.1 — the window started
from the built folder finds `prologd.exe` beside itself and creates `gui.ini` beside
itself; it adds **nothing of its own** to the import search list (2026-10-03, §4),
while `examples/lib` is in the package for lesson 11; without `prologd.exe` beside it
it does not exit silently but shows an explanatory window (that was added to `main.py`
during the checks: in a `--windowed` build there is nowhere to print).  Remaining: the
clicks (`F5`, a marker, `F1`, `Shift+F1`) — a human does those — and the clean machine
(§7.5), also a human.  The zip is no longer pending: the script makes it (§6), and the
last run produced `dist\prologd-2.0.0-win64.zip`, 37.7 MiB.

## §8. User decisions (2026-10-03)

1. **`--onedir`**, PyInstaller (§3) — a folder, not a single file.
2. **The Visual C++ DLLs are shipped beside** the exe (§2); a static CRT is a possible
   improvement after the first package.
3. **`examples/lessons/_old/` is not shipped**, `examples/lib` is (§5).
4. **`doc/*.typ` is shipped** beside the PDFs (§5).
5. **`gui.ini` in the portable build sits beside the exe** (§4); other builds keep
   `%LOCALAPPDATA%\PrologD\gui\gui.ini` as before.
6. **The window adds nothing of its own to the import search path** (§4).  First the
   decision was that `examples/lib` from the package is available at once — by writing
   it into the settings, then by substituting it on every start; on 2026-10-03 that was
   reverted: lesson 11 asks for the directory to be added by hand, which is clearer for
   a student.
7. **The folder is `prologd-2.0.0-win64`, and the zip is wanted** (§6).
8. **The installer is the next task**, not this one; it is then that we decide how it
   lives with `gui.ini` beside the exe.

## §9. The oldest Windows we support

**Windows 10 (1903) or newer, 64-bit.**  The reason is the window and the process, not
the interpreter:

* **Qt 6** supports Windows only from Windows 10 1809: the Qt "Supported Platforms"
  table says "Windows 10 (1809 or later)", and Windows 7 and 8.1 are not in Qt 6 at
  all.  The package's window is PySide6 6.11.2;
* **Python** inside the frozen build is 3.14, and CPython follows Microsoft's
  deadlines: a new version supports the systems whose extended support has not expired
  (PEP 11), and Windows 7 left it on 2020-01-14 while Windows 8.1 left on 2023-01-10.
  So Python 3.14 does not work on Windows 7 and cannot be frozen there;
* the **UTF-8 manifest** of `prologd.exe` — `<activeCodePage>UTF-8</activeCodePage>` —
  is understood from Windows 10 1903 (ADR-013).  On older systems the exe starts but
  the manifest is ignored: Cyrillic in the command line (`argv`) goes through the ANSI
  code page again — exactly what the manifest prevents.  This is the strictest of the
  three boundaries, hence 1903 in the read-me.

**The interpreter alone would need less.**  It needs only the UCRT, and the UCRT is
part of Windows 10 (see the facts: `ucrtbase.dll`, while `api-ms-win-crt-*` names are
resolved by the loader).  On Windows 7 the UCRT has to be installed separately
(KB2999226 or the Visual C++ redistributable), and that is a separate story we have not
tested.

**Consequences for the package:**

* the read-me says "Windows 10 (1903) or newer, 64-bit" and gives the reason in one
  line (Qt 6, Python 3.14 and our UTF-8 manifest);
* the three DLLs beside `prologd.exe` are sufficient on Windows 10+, because the UCRT
  is already in the system; §7.3 is what confirms it;
* Windows 7 is deliberately unsupported: out of support since 2020, nothing to test
  on, and the window would not start there anyway.

**For the future:** Qt 6.12 is the last branch that supports Windows 10 (a note in the
same Qt table).  The package pins PySide6 6.11.2, so on Windows 10 the portable build
keeps working; we would only lose it by moving to Qt 6.13+.

## §10. Три вида пакета (часть 143)

Один и тот же скрипт собирает три пакета, и разница только в том, что кладётся рядом с
окном (`-Engine`):

| `-Engine` | движки | примеры | документы | библиотека | имя папки |
|---|---|---|---|---|---|
| `both` (по умолчанию) | `prologu.exe` + `prologd.exe` | наши (`examples`) | шесть наших PDF | `stdlib` | `prologd-<наша версия>-win64` |
| `u` | `prologu.exe` | наши | шесть наших PDF | `stdlib` | `prologd-<наша версия>-win64` |
| `d` | `prologd.exe` | `examples/prologd` (файлы репозитория Пролог-Д) | `help.pdf` из его `help.typ`, его `builtins.json`, наш `gui.pdf` | нет | `prologd-<его версия>-win64`, то есть `prologd-1.27-win64` |

Версию `d`-пакета даёт строка `project("prologd" VERSION …)` из `CMakeLists.txt`
пиннутого движка: у него нет `--version` (`-s` он при этом печатает в `--help`, но
не принимает — работает только `--source=`).  Примеры его репозитория ссылаются на
библиотеку относительно текущей папки (`?ИМПОРТ("examples/lib/library.pld")`),
поэтому проверки запускают их из корня пакета.

Окно такого пакета открывается на единственном движке (сохранённое имя другого ему
не мешает — `paths.starting_engine`) и кнопки выбора движка не показывает: рядом
только один файл, и переключать нечего.

## Definition of done

* `tools/build_portable.ps1` builds the folder with one command on this machine, and a
  second run produces the same contents (no leftovers of the previous build).
* The folder copied elsewhere starts and passes §7.1–§7.2.
* §7.3–§7.4 are static, so they are visible without a clean machine; §7.5 is marked as
  not testable here and was tested where it could be.
* The changes of §4 are covered by tests; the 23 GUI suites and `ctest` are green.
* The decisions of §8 and §9 are recorded in ADR-024 (PyInstaller `--onedir`; the
  Visual C++ DLLs beside the exe; `gui.ini` beside the exe in a frozen build; the
  oldest system is Windows 10 1903), and the package is described in
  `src/gui/README.md` (the "Running" section — how to build the portable version).
* The folder has no `lessons/_old` and nothing superfluous;
  `prologd-2.0.0-win64.zip` lies next to it and unpacks into the same folder.
