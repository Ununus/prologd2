# task_116 — an installer with the `.pld` association

**Status:** done (2026-10-24) — parts 1–7, round-tripped on the owner's machine;
only the version bump before publishing is left
**Depends on:** task_61 (the portable package), task_29 (the session in `gui.ini`)
**Milestone:** 2.7.0

## What the owner asked for

An installed version of the window, and a `.pld` file associated with it, so a
double-click on a program opens it.  The owner's decisions, given with the request:

* **per-user install.**  The checkout already keeps its settings in
  `%LOCALAPPDATA%\PrologD\gui\gui.ini`, and the installed build is expected to do
  the same — so the settings of an installed build live in AppData, not beside the
  executable.
* **uninstall removes every artefact.**  A checkbox «удалить настройки» is part of
  the uninstall and is **on** by default; the portable folder's own `gui.ini` is not
  the installer's business.
* **no code signature yet.**  Discussed before and set aside: SmartScreen will say
  «неизвестный издатель», which is acceptable while the audience is small.
* `src/gui/assets/pld.ico` is the document icon, converted by an online service.

`C:\Program Files\Inno Setup 7` is installed on the owner's machine, so the
installer is Inno Setup: free, one command-line compiler (`iscc`), and it knows
about associations, registry keys and their removal on uninstall.

## Parts

1. **A file on the command line.**  `main.py` takes no positional argument today,
   and `QApplication(sys.argv[:1])` hides the rest from Qt, so
   `prologd-gui.exe "%1"` would open an empty window — the association would be
   decoration.  The window has to open *on* the file.
2. **Where the settings live.**  `paths.settings_path()` answered **any** packaged
   build with `data_root()/gui.ini`, which is what makes the folder portable and
   what an installed copy must not do.  The answer is the **folder the build runs
   from**, in three steps — no marker file (part 2 below says why the owner's
   «скопированная установленная папка должна думать, что она переносимая» is what
the folder rule gives for free).
3. **The installer.**  `installer/prologd.iss` and `tools/build_installer.ps1`,
   which reuses `build_portable.ps1 -Engine both` as its payload, so there is one
   layout and not a second copy of the file list.  `AppId` fixed for ever, version
   from `prologu.exe --version`, `PrivilegesRequired=lowest` (per-user, no UAC),
   `{localappdata}\Programs\PrologD`.
4. **The association itself** — a task with a checkbox, so an existing `.pld`
   owner is not robbed silently; `PrologD.Program` progid, `DefaultIcon` from
   `pld.ico`, `shell\open\command` = `"{app}\prologd-gui.exe" "%1"`, a second verb
   «Запустить в консоли» = `"{app}\prologu.exe" -s "%1"`, `App Paths` for both
   executables, `ChangesAssociations=yes` so the shell is told.
5. **The icon.**  `pld.ico` as it came: one image, 64 × 64, 32 bits, uncompressed
   BMP payload, no metadata (checked byte by byte — the file ends exactly where the
   image ends, and it holds no printable strings at all).  Windows wants 16/32/48
   and a 256 for the large views; a single 64 is scaled and looks soft at 16.  Done
   — see below.
6. **Documentation** — `ЧИТАЙ_МЕНЯ.txt` stays the portable read-me, the installer
   needs its own two lines, `src/gui/README.md` and `doc/gui.typ` say where the
   settings live in an installed build and what a double-click does.

## Part 1 — done

* `main.py` takes an optional positional `FILE`; the path is made absolute
  (`Path(...).resolve()`), because the shell passes one absolute and a terminal need
  not, and the tab, the recent list and the session all want one spelling.
* `MainWindow(..., path=...)` opens it **after** the session is restored, so a
  start with tabs comes back with the file as one more tab, and a file that is
  already among them comes to the front (`open_path` looks for an open copy first).
  The welcome program is created only when the window ends up with no buffer at
  all — a start must not come up empty when the file has gone, and the note
  `open_path` writes («не могу открыть …», in «Система») says why.
* Checks: `src/gui/tests/test_main.py` (new suite — the command line reaches the
  window, named absolutely, and options still parse around the positional) and
  `test_a_file_named_on_the_command_line_opens` in `test_window.py` (the file is
  the only tab; a missing one falls back to the welcome program).

## Part 2 — done: the folder decides, and no marker file

`paths.settings_path()` now answers a frozen build in this order (task_116):

1. a `gui.ini` that is **already beside the window** is kept — a portable copy the
   user has been running, whose settings must not move on an upgrade;
2. under `%LOCALAPPDATA%\Programs`, `%ProgramFiles%` or `%ProgramFiles(x86)%` the
   build is an **installed** one and answers AppData (`None`, so Qt picks it);
3. anywhere else it is **portable**: `gui.ini` beside itself, provided the folder
   can be written at all — a CD or a read-only share falls back to AppData instead
   of failing at every close.

The marker file the first plan had (`portable.txt`) is gone, and with it the
question «а кто его удалит при деинсталляции».  The owner's wish — «скопированная
установленная папка, например на флешку, должна подумать, что она переносимая» —
falls out of rule 2 as it stands: the copy is under no programs folder any more, so
it is portable.  The same rule covers the reverse: an installed copy is never asked
to write into its own folder.

`writable()` probes with a real file rather than `os.access`, because on Windows that
answers from the folder's read-only attribute and not from its permissions — a share
that refuses writes would pass and every close would then fail to remember the
session.

Checks in `test_paths.py`: an installed copy (a fake `%LOCALAPPDATA%\Programs`) answers
AppData; the same folder copied to a flash drive answers `gui.ini` beside itself;
`%ProgramFiles%` counts as an install location; a `gui.ini` that is already there wins
even inside an install location; and a folder that cannot be written falls back.

## Part 5 — done: the icon has every size

`tools/make_pld_icon.py` rebuilds `src/gui/assets/pld.ico` from `pld.png` (64 × 64,
transparent background): 16, 24, 32, 48, 64, **128 and 256**, each a PNG payload inside
the ICO container.  The large two are upscales and look soft — the owner's call, a soft
large icon beats a missing one.  Every payload is re-encoded, so the `Software`,
`exif`, `dpi`, `gamma` and `srgb` chunks the online converter left in the **PNG** do
not reach the icon; the result was checked byte by byte (seven images, nothing after
the last one, no printable strings) and the 16 × 16 was looked at: the red «Д» on the
page with its folded corner is legible.
## Part 3 — done: the compiler script

`installer/prologd.iss` (UTF-8 **with BOM** — without one Inno reads it as ANSI and the
Cyrillic turns to rubbish; LF) plus `tools/build_installer.ps1`, which calls
`build_portable.ps1 -Engine <engine>` and then `ISCC.exe --define=AppVersion=<version>
installer\prologd.iss`.

What the script says, and why:

* **per-user, no UAC**: `PrivilegesRequired=lowest`,
  `DefaultDirName={localappdata}\Programs\PrologD`.
* **the folder is fixed** (`DisableDirPage=yes`, `UsePreviousAppDir=no`): part 2
  decides «installed or portable» by the folder, so an install somewhere else would
  behave as a portable copy with its own `gui.ini`.
* **a permanent `AppId`** — the thing that makes 2.6.1 replace 2.6.0 instead of
  installing beside it.
* `MinVersion=10.0.18362` (1903), `ArchitecturesAllowed=x64compatible` — the same
  floor the read-me names.
* `[Languages]`: Russian first (the wizard opens in it), English second.
* `[Files]`: `dist\prologd-<version>-win64\*`, **without** `ЧИТАЙ_МЕНЯ.txt` — that
  file says the settings live beside the exe, which is true of the portable copy and
  not of an installed one.  `pld.ico` is installed beside the window for the registry
  entry only.
* the version is read from the **package folder name** and passed with `--define=`:
  one rule for both engines (the original one has no `--version` at all) and no way
  for the file name and the payload to disagree.  ISCC 7 takes `--define=name=value`;
  the `/Dname=value` of Inno 6 is gone.

ISCC 7.1.0 compiles it in 11 s to 28.4 MiB; the version resource of the result says
`Пролог-Д 2.0`, `2.6.0`.

## Part 4 — done: the association

* `[Tasks] associate` — checked by default (`checkedonce`), with the desktop icon as
  a second, unchecked task.
* A **foreign `.pld` is not taken**: `InitializeSetup` reads the current handler and,
  if it is not our progid, `InitializeWizard` calls `WizardSelectTasks('')`, so the box
  comes up unchecked; it can still be ticked by hand.
* `[Registry]`: `.pld` → `PrologD.Program`; the progid with a Russian description,
  `DefaultIcon={app}\pld.ico`, `shell\open\command` = `"{app}\prologd-gui.exe" "%1"`
  and a second verb «Запустить в консоли» = `"{app}\prologu.exe" -s "%1"`, guarded by
  `Check: FileExists(...)` so a `-Engine d` installer offers no verb for an engine it
  does not carry.  `App Paths` for `prologu.exe` and `prologd.exe` (value + `Path`),
  also guarded, so both are found from any console and Win+R without touching `PATH`.
* `ChangesAssociations=yes` tells the shell.
* **Uninstall** removes everything: our own files and icons (Inno), the progid and the
  `App Paths` keys (`uninsdeletekey`), `{app}\gui.ini` if someone left one there, and
  the `.pld` value — but only if it still points at our progid, so a user who gave the
  extension to another editor keeps that.  The settings folder
  `%LOCALAPPDATA%\PrologD` is offered with **«Yes» as the default answer** (the
  owner's «пусть удаляет всё»), and silent uninstalls never ask and never delete it.
* `[Run]` offers to start the window after installation.

`tools/build_installer.ps1` picks the package by **engine**, not by the newest folder:
`d` is 1.27 and `both` is 2.x, and the `d` package is built last in a release, so
«newest» chose the wrong one on the first run.
### Round trip (on the owner's machine, 2026-10-24)

`.pld` had no handler at all, so a silent install could be run and undone without
taking anything from anybody:

    dist\prologd-2.6.0-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

What appeared: `%LOCALAPPDATA%\Programs\PrologD` with both engines, `doc`, `examples`,
`stdlib`, `pld.ico` and **no** `ЧИТАЙ_МЕНЯ.txt`; `prologu --version` answers
`Пролог-У 2.6.0 (2026-10-24)`; the original engine solves `examples\prologd\factorial.pld`
(`ф=720`); `HKCU\Software\Classes\.pld` → `PrologD.Program`; the progid with its Russian
description, `open` = `"...\prologd-gui.exe" "%1"` and `console` = `"...\prologu.exe" -s "%1"`;
`App Paths` for both; an uninstall entry «Пролог-Д 2.0, 2.6.0».

`unins000.exe /VERYSILENT …` left: no folder, no progid, no `App Paths`, no uninstall
entry, and `%LOCALAPPDATA%\PrologD\gui\gui.ini` **untouched** — a silent uninstall never
asks and never deletes settings, which is what kept the owner's own settings safe
during the check.

One defect came out of it: the association value was deleted but the empty
`.pld` key stayed in `HKCU\Software\Classes`.  `RegDeleteKeyIfEmpty` after
`RegDeleteValue` fixes it, and the second round trip left not even the key.
### A stale payload behind a "the association does not work" report (2026-10-24)

The owner installed `prologd-2.6.0-setup.exe`, ticked the association box, and got the
right icon but no window on a double-click.

* **Cause 1 — the payload was older than the code.**  `dist\prologd-2.6.0-win64` was
  frozen at 04:20, `main.py` learned the `FILE` argument at 05:26, and the installer
  was built with `-SkipPackage`, so it shipped the *old* `prologd-gui.exe`.  The shell
  ran it with the file, `argparse` saw an unexpected positional and exited with code
  **2** — and a `--windowed` build has no console, so nothing was shown anywhere.  The
  icon was right because the registry was right: only the program was old.
* **Guard.**  `build_installer.ps1` now refuses `-SkipPackage` when anything under
  `src\gui` (`*.py`, `*.ico`, `*.png`) is newer than the package's `prologd-gui.exe`,
  and says which file and which times are to blame.
* **Cause 2 — a `gui.ini` beside the installed exe.**  The old build predated the
  folder rule of part 2, so running it wrote `gui.ini` **into the install folder**;
  rule 1 («a `gui.ini` that is already there wins») then kept the *new* build writing
  there instead of AppData.  The file was removed (a copy is in
  `build\gui.ini.from-installed.bak`), and the installed copy now uses
  `%LOCALAPPDATA%\PrologD\gui\gui.ini` as designed.
* **Made visible instead of silent.**  `main.py` gained `WindowParser`: in a frozen
  build a bad command line now says «Не понимаю аргументы командной строки» in a box
  instead of exiting with code 2 into nothing.  A checkout keeps `argparse`'s plain
  behaviour (its stderr has a reader).
* **Checked.**  `Start-Process` on the `.pld` (the same ShellExecute Explorer uses)
  starts `prologd-gui` and it stays up; the file lands at the head of `files/recent`
  in AppData, and the session records it as the current tab.  30 window scripts and
  `protocol_smoke.py` are green, `ctest` 424/424.
### Names and languages of the installer (2026-10-24)

* **No «2.0» in the install.**  `#define AppTitle "Пролог-Д 2.0"` was the *shell's*
  product name, and next to the version it read as two numbers in a row:
  «Пролог-Д 2.0 2.6.0» in Settings → Apps.  The installer now uses one define,
  `AppName = "Пролог-Д"`, everywhere (`AppName`, `AppVerName`, `DefaultGroupName`,
  the shortcuts, the Run line), so the entry reads «Пролог-Д 2.6.0».
  `VersionInfoDescription={#AppName} — установщик` and `VersionInfoProductName` keep
  the file properties from picking up Inno's own «… Setup» default.
  The name «Пролог-Д 2.0» stays where it is the *name of the shell* — the About box,
  the manuals, `doc/*.typ` (task_75 renamed the engine to «Пролог-У» and kept 2.0 for
  the window), so nothing under `src/gui` was touched.
* **Every own string exists in both languages.**  `[Tasks]` `Description`/
  `GroupDescription` were Russian literals, so an English wizard showed «Связь с
  файлами: Открывать файлы…».  They come from `[CustomMessages]` now, together with
  the shortcut name, the uninstall question and two shell strings.  The uninstall
  question is `ExpandConstant('{cm:DeleteSettings}')` + the settings folder on its own
  line; the language is stored in the uninstall data, so the question stays in the
  language the install used.
* **`{cm:}` in `[Registry]`, not `Languages:`.**  The first attempt gave the progid
  description and the «Запустить в консоли» verb two entries with `Languages: ru`/
  `Languages: en`; the parameter is accepted, but both entries were written anyway and
  the English one (last) won — a Russian install showed `PrologD program`.  One entry
  each with `ValueData: "{cm:FileTypeName}"` / `"{cm:ConsoleVerb}"` does it.
* **Checked by round trips.**  `Setup /VERYSILENT /LANG=en` → `PrologD program`,
  `Run in console`; `/LANG=ru` → «Программа Пролог-Д», «Запустить в консоли»; both
  times the uninstall entry is «Пролог-Д 2.6.0» and the version resource says
  «Пролог-Д — установщик», `Пролог-Д`, 2.6.0; a double-click on the `.pld` still
  opens the window.  The wizard text itself is the part only a person can look at.
## Documents in a package: PDFs only (2026-10-24)

The owner's question: the `.typ` files are closer to sources, so should they ship at
all?  No — they were removed from both packages and from the install.

* `Copy-OurDocuments` copies the six PDFs and `builtins.json` and nothing else.  The
  `.typ` sources, the shared `style.typ` and the two logos (`prologd2.png`, `csu.png`)
  were there for one reason — so the shipped sources could be compiled from the
  package — and that reason went with them.  The logos also left `$oursNeeded`, since
  the checks on the package insisted on them.
* `Copy-EngineDocuments` keeps the `help.pdf` it *compiles* from the pinned engine's
  own `help.typ`, plus `gui.pdf` and `builtins.json`; `gui.typ` and `style.typ` are no
  longer copied.  The compile still happens at packaging time, from the engine's doc
  folder, so the `d` package is unchanged in what a reader sees.
* **`builtins.json` stays**: it is not a source but the runtime data the window reads
  for `F1` and the completion summaries (`paths.builtins()`).
* The installer excludes `*.typ` as well, next to its own read-me: a package built
  before this change must not slip the sources into an install.
* `ЧИТАЙ_МЕНЯ.txt` no longer says «Исходники .typ лежат рядом — для чтения они не
  нужны»; it names the PDFs, `builtins.json`, and says the manual sources stayed in
  the repository.

Checked: `dist\prologd-2.6.0-win64\doc` and `dist\prologd-1.27-win64\doc` hold PDFs
and `builtins.json` only; a fresh silent install has **no** `.typ` anywhere and
`doc\builtins.json` in place (F1 has its data).  `ctest` 424/424, docs target green.
## The read-me is gone, and the manual says what it used to say (2026-10-24)

The owner's call: a portable folder does not need `ЧИТАЙ_МЕНЯ.txt`.  Removed, together
with its two sources (`tools\portable-readme.txt` and
`tools\portable-readme-prologd.txt`), the `$memoName` computation in code points, the
`Memo` field of every `$kinds` entry, the copy step and the check that insisted on the
file.  The installer's `Excludes` no longer names it — there is nothing to exclude.

What the memo explained had to survive somewhere, and the right place is the manual a
reader actually has:

* `doc/gui.typ` §1 — a built copy (portable folder or installed) starts with a
  double-click and needs Windows 10 (1903), 64 bit, with the reason;
* `doc/gui.typ` §2 — a `.pld` double-clicked in Explorer opens in the window (when the
  association was taken at install), the window opens *on* it and runs nothing;
* `doc/gui.typ` §8 — where `gui.ini` lives: beside the exe in a portable copy, in
  AppData in an installed one, or wherever `--settings` says.

The pages were looked at after the docs target: page 2 (§1), page 4 (§2), page 30 (§8).

Checked: `dist\prologd-2.6.0-win64` has no memo in its root; a fresh silent install has
9 files in the root, no memo, no `.typ` anywhere, the shipped `gui.pdf` and `builtins.json`
in place; a double-click on a `.pld` still opens the window.  `ctest` 424/424.

**Left before publishing**: bump the version (the code has moved past the `v2.6.0` tag),
rebuild both packages and the setup, and decide whether `main`/tags are pushed.