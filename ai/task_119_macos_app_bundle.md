# task_119 — a macOS `.app` built in the cloud

**Status:** planned (2026-10-24) — no Mac in the house, so the build lives in CI
**Depends on:** task_61 (the portable layout), task_116 (installer and the settings
rule), task_118 (the Linux work; the same "what is installed" question)
**Milestone:** 2.8.0 or later

## Why, and what "done" means

The product will have macOS users, the owner has never worked on macOS, and there is
no Mac to build on.  Neither of the two obvious shortcuts works:

* **cross-compiling from Windows** — no.  The app bundle needs Apple's clang, linker and
  SDK (redistributable only with Xcode, under Apple's licence), and `PyInstaller`,
  `codesign`, `hdiutil` and `iconutil` all have to *run* on macOS;
* **a virtual machine** — a macOS guest is licensed only on Apple hardware, and the
  current releases are arm64-only, so a PC host cannot run them usefully anyway.

What does work is a **cloud Mac**: GitHub Actions runs macOS VMs, which is the cheapest
and the most reproducible option available.  The plan below keeps everything except the
final human look at the result inside CI.

**Done means:** a tag (or a manual dispatch) produces `dist/PrologD-<version>.dmg` on a
GitHub macOS runner with nothing typed by hand; the `.app` inside starts on a real Mac,
opens a `.pld` from Finder, keeps its settings in `~/Library/Application Support`, and
the same workflow runs the C++ tests on macOS so the engine stays honest.

## What the owner's old builds already tell us

`ai/_ref/macos` holds two bundles built by someone else (read, never edited — it is
`ai/_ref/`, which is ignored by git):

| | `Prolog-D_i` | `Prolog-D_M1` |
| --- | --- | --- |
| binary | **universal**: x86_64 + arm64 | arm64 only |
| `LC_BUILD_VERSION` | **macOS 14.0**, SDK 14.2 | macOS 14.0, SDK 14.2 |
| layout | `Contents/MacOS/Prolog-D` (one file, 39 MB), `settings.ini` and `prolog1.ico` beside it | same, 18.7 MB |
| `Info.plist` | `com.csu.prologd.Prolog-D`, `CFBundleShortVersionString` 1.0, **no** `LSMinimumSystemVersion`, **no** `CFBundleDocumentTypes` | same |

Three things follow:

1. **The floor is the build machine**, not the code: 14.0 is Sonoma because that is where
   it was built.  Qt 6 is what really sets the floor (macOS 11–12 depending on the
   version); pass `-DCMAKE_OSX_DEPLOYMENT_TARGET` and check the result with
   `otool -l` instead of inheriting the runner's release.
2. The build is a **single frozen executable inside the bundle** (PyInstaller `--onefile`
   or Nuitka), with the settings file *next to the binary* inside `Contents/MacOS` —
   the same "everything beside the executable" idea the portable Windows folder uses.
3. The icon is a **`.ico`**, which macOS does not read (it wants `.icns`), and the file
   association is simply **not declared** — on macOS that is `CFBundleDocumentTypes`
   plus an exported UTI in `Info.plist`, not a registry.

## Code work that has to land first

These are real gaps, not packaging choices — with them the app would start but be
half-broken.

1. **`src/prlib/src/module_loader.cpp`** — `executableDirectory()` has a `_WIN32` branch
   (`GetModuleFileNameW`) and a `__linux__` branch (`/proc/self/exe`), and `#else
   return {}`.  On macOS it therefore returns nothing, so the engine cannot find the
   `stdlib` beside itself and every `ИМПОРТ("lists.pld")` fails.  Add an `__APPLE__`
   branch with `_NSGetExecutablePath` (`<mach-o/dyld.h>`), and make the existing unit
   test for that helper run there too.
2. **`src/gui/prologd_gui/paths.py`** —
   * `data_root()` is "the folder of the executable", which inside a bundle is
     `PrologD.app/Contents/MacOS`; that is where the engines, `doc/`, `examples/` and
     `stdlib/` must be placed (the old build did the same with `settings.ini`);
   * `settings_path()` needs a macOS rule: a build running from inside a `.app` is
     **installed**, so its settings belong in `~/Library/Application Support/PrologD/gui/gui.ini`
     — not beside the binary inside the bundle, which would break the signature of every
     copy on first write;
   * `default_path()` (Qt's `AppConfigLocation`) on macOS gives `~/Library/Preferences`;
     decide between it and `AppDataLocation` (`Application Support`), and say why;
   * `reveal_command()` already answers `open -R` for `darwin` — check it, do not
     rewrite it;
   * `interpreter()` has to look in `build/macos-release/src/cli` as well.
   Each of these is checkable in `test_paths.py` without a Mac (`sys.platform` faked,
   the way `test_paths.py` already fakes `sys.frozen`).
3. **Shortcuts.**  The insert table and the actions are built from `Ctrl+…`.  On macOS
   Qt maps the `Ctrl` modifier in *menus* to ⌘, but a `QKeySequence("Ctrl+N")` built by
   hand does not become ⌘N.  Decide: map `Ctrl` → `Meta` on `darwin` in
   `shortcuts.py` (one place, and the table then reads ⌘ for the user), and check every
   action that builds its key sequence by hand.
4. **`CMakePresets.json`** — a `macos-release` preset (Ninja, Release) so the engine
   build in CI is one line, and `paths.interpreter()` can look in `build/macos-release`.
5. **Icons** — `prologd2.png` (64 × 64) and `pld.png` are the sources; macOS wants an
   `.icns`.  Build it in CI from an `.iconset` folder with `iconutil -c icns` (Pillow
   cannot write ICNS away from macOS).  The document icon is optional on macOS — the
   bundle icon is what Finder shows.

## Findings from the code (2026-10-25)

What the plan above gets right, and three corrections found by reading the code and
the current tooling:

* `executableDirectory()` indeed ends in `#else return {}`; on macOS the engine
  finds no `stdlib` until the `_NSGetExecutablePath` branch is added.  Confirmed.
* `settings_path()` has no `.app` rule: a frozen build inside
  `PrologD.app/Contents/MacOS` is writable for the user, so it would put `gui.ini`
  there — inside the bundle, which breaks the signature on the first write.  The
  rule must recognise `Contents/MacOS` under a `.app` as *installed*.  `default_path()`
  uses `AppConfigLocation`, which on macOS is `~/Library/Preferences/<APPNAME>` (Qt
  docs); the file the task wants is in `~/Library/Application Support`, so macOS
  should use `AppDataLocation` (or an explicit path), not the Preferences folder.
  `interpreter()` also lacks `build/macos-release/src/cli`.
* **Shortcuts, corrected:** Qt 6 by default remaps Command to
  `Qt::ControlModifier` (`AA_MacDontSwapCtrlAndMeta` is not set), so
  `QKeySequence("Ctrl+N")` already becomes ⌘N and the menu rows are fine.  A
  Ctrl→Meta translation is therefore not the fix and would break the default.
  The real gap is the *insert table*: it matches `QKeyEvent.nativeScanCode()`, and
  the table stores Windows scan codes.  On macOS Cocoa hands the virtual key code
  in `nativeVirtualKey` (and `nativeScanCode` is not the Windows value), so the table
  needs macOS key codes (a second mapping keyed by `nativeVirtualKey`) or another
  physical-key match.  The cheat sheet should print ⌘, not Ctrl, on macOS.

Two more facts from the current runners and wheels:

* `macos-14` is deprecated in 2026.  Available labels: `macos-15` (arm64),
  `macos-15-intel` (x86_64), `macos-26` (arm64), `macos-26-intel` (x86_64).
  Use `macos-15` for the first run and add the Intel label only if a second build
  is needed.
* The unpinned `PySide6>=6.6` currently installs 6.12, and Qt 6.12 supports macOS
  **14.4 or newer**, with Xcode 16 / macOS 15 SDK.  `LSMinimumSystemVersion 12.0`
  would therefore promise a system the bundled Qt cannot run on.  Either set the
  deployment target and plist to 14.4, or pin PySide6 6.8 (Qt 6.8) and keep a
  12.0 floor.  The C++ engine itself has no macOS-specific link requirements.
* Whether the original `prologd` builds with AppleClang is unverified.  Its own
  `src/CMakeLists.txt` sets `CMAKE_OSX_ARCHITECTURES "x86_64;arm64"`;
  `-DBUILD_WITH_PROLOGD=ON` built it on AppleClang in run `40136493860` (warnings
  `-Winvalid-source-encoding` on CP1251 strings only).

## Progress (2026-10-25)

- [x] `module_loader.cpp`: the `__APPLE__` branch reads `_NSGetExecutablePath` and
      canonicalises it; `test_module_loader.cpp` checks that the directory is real
      and holds the test binary on every platform.
- [x] `paths.py`: `inside_app_bundle()` recognises `Foo.app/Contents/MacOS`;
      `settings_path()` leaves such a bundle alone; `interpreter()` searches
      `build/macos-release/src/cli`.  `settings.py` uses `AppDataLocation` on macOS
      (`~/Library/Application Support`) and keeps `AppConfigLocation` elsewhere.
      Checks live in `test_paths.py` and `test_settings.py`.
- [x] `CMakePresets.json`: `macos-release` (Ninja, Release, deployment target 14.4)
      with build/test presets.
- [x] `.github/workflows/macos.yml`: test-only job on `macos-15` — configure, build
      and `ctest` on every push/PR and by hand.
- [ ] The insert table still matches Windows scan codes; macOS needs
      `nativeVirtualKey` and ⌘ labels (see the findings above).
- [x] Packaging job: `.icns`, PyInstaller `.app`, `Info.plist`
      (`tools/macos_plist.py`), ad-hoc signing, `.dmg`, artifact and release attach.
      Run `40136493860` built `PrologD-2.6.1-arm64.dmg` with both engines; the
      real-Mac checks are still open.

## The bundle

```
PrologD.app/Contents/
    Info.plist                    CFBundleIdentifier, version, document types
    MacOS/PrologD                 the frozen window (PyInstaller --onedir)
    MacOS/prologu, prologd        the engines, beside the window as everywhere
    MacOS/doc/*.pdf, builtins.json
    MacOS/examples/, stdlib/
    Frameworks/…                  Qt, Python — PyInstaller's own layout
    Resources/PrologD.icns
```

`onedir`, not `onefile`: the folder starts faster, `data_root()` is a real directory,
and the engines are simply copied next to the window.  The old build used onefile and
a 39 MB universal binary; a onedir bundle is a folder in a `.dmg`, which is what macOS
users expect anyway.

`Info.plist` extras (PyInstaller generates the rest; post-process it with `plutil -replace`
or `PlistBuddy`):

```xml
<key>LSMinimumSystemVersion</key><string>14.4</string>
<key>NSHighResolutionCapable</key><true/>
<key>UTExportedTypeDeclarations</key>
<array><dict>
  <key>UTTypeIdentifier</key><string>com.csu.prologd.program</string>
  <key>UTTypeDescription</key><string>Программа Пролог-Д</string>
  <key>UTTypeConformsTo</key><array><string>public.plain-text</string></array>
  <key>UTTypeTagSpecification</key>
  <dict><key>public.filename-extension</key><array><string>pld</string></array></dict>
</dict></array>
<key>CFBundleDocumentTypes</key>
<array><dict>
  <key>CFBundleTypeName</key><string>Программа Пролог-Д</string>
  <key>LSItemContentTypes</key><array><string>com.csu.prologd.program</string></array>
  <key>CFBundleTypeRole</key><string>Editor</string>
</dict></array>
```

That is what makes Finder offer the app for `.pld`.  The *default* handler stays the
user's choice (`duti` or «Открыть с помощью → Все программы»), the same rule the
Windows installer and the Linux MIME file follow.

## The workflow

Add to `.github/workflows/` (a second file, `macos.yml`, or a job in `ci.yml` — a
separate file keeps the tag-triggered packaging out of every push):

```yaml
jobs:
  test:                      # every push: does the engine still build on macOS?
    runs-on: macos-15        # arm64; macos-15-intel is the x86_64 runner
    steps: checkout → cmake --preset macos-release → build → ctest

  package:                   # tag v* or manual dispatch
    runs-on: macos-15
    steps:
      - build the engine (Release)
      - python3 -m venv .venv && pip install -r src/gui/requirements.txt pyinstaller
      - pyinstaller --noconfirm --clean --onedir --windowed --name PrologD \
          --icon build/PrologD.icns --paths src/gui src/gui/main.py
      - copy prologu, prologd, doc, examples, stdlib into PrologD.app/Contents/MacOS
      - iconutil -c icns build/PrologD.iconset -o build/PrologD.icns   (before the freeze)
      - plutil -replace … (version, document types, minimum system)
      - codesign --force --deep --sign - PrologD.app      (ad-hoc; see below)
      - hdiutil create -volname PrologD -srcfolder dist/PrologD.app \
          -ov -format UDZO dist/PrologD-<version>-arm64.dmg
      - actions/upload-artifact
```

The version comes from `prologu --version`, as on Windows and Linux — never typed twice.

## Signing and Gatekeeper

* **Without an Apple Developer account** an ad-hoc signature (`codesign -s -`) is enough
  for the app to start on the machine that built it, but a *downloaded* `.dmg` is
  quarantined: the user sees «разработчик не подтверждён» and must use right-click →
  «Открыть», or run `xattr -dr com.apple.quarantine PrologD.app` once.  Say so in the
  manual's macOS paragraph.
* **With** an account ($99/year) the way is `codesign --options runtime --sign "Developer
  ID Application: …"` + `xcrun notarytool submit --wait` + `xcrun stapler staple`.  It
  needs the certificate and an app-specific password as repository secrets; the workflow
  should take the identity from a secret and fall back to ad-hoc without it.

## What only a person can check

The first run on a real Mac — the owner's future users, or an hour of a rented cloud
Mac — has to look at: the app starting from Finder and from the `.dmg`, the menu bar
(«Правка → Настройки…»), ⌘ shortcuts, Cyrillic and the fonts, F5 on a lesson, a margin
marker, `Shift+F1`/`F1`, the graphics window, Retina sharpness of the icons, «Открыть с
помощью» for a `.pld`, and the Gatekeeper flow above.  Nothing of this can be asserted
by a test; it belongs in the task file as the acceptance list.

## Rules that carry over

* The bundle ships **PDFs and `builtins.json`**, never `.typ` sources and no read-me
  (task_116/187); the manual explains the settings and the association.
* `dist/` stays out of git; the workflow file and any `installer/macos/` inputs go in.
* Do not touch the Windows packaging or `CMakeLists.txt`'s version as part of this task.
* `ai/` is English; user-facing texts are Russian, with English where the platform asks
  (`UTTypeDescription`, the manual's paragraph).

## Open questions for the owner

1. **Deployment target**: 12 (Monterey) is the safe floor for Qt 6.8; 11 (Big Sur) is
   possible with an older Qt.  Decide from what the users actually run.
2. **Universal or two builds**: one universal2 `.app` (a bigger `.dmg`, one download) or
   separate arm64 and x86_64 builds (smaller, a picker for the user).  PySide6 ships
   universal2 wheels, so the first is likely to just work — verify with `lipo -archs`.
3. **Signing now or later**: an ad-hoc signature plus a note in the manual, or an Apple
   Developer account before the first public `.dmg`.
4. Does macOS get the association at all in the first release, or is «Открыть → выбрать
   файл» enough for a start?

## What to record when it is done

A journal part in `ai/status.md` with the measured facts (`sw_vers`, Python and PySide6
versions, the `LC_BUILD_VERSION` of the built binaries, `.dmg` size), the result of each
step above, and every non-obvious choice — `ai/decisions.md` for the architectural ones
(«installed means inside a `.app`», the settings location on macOS).
