# task_118 — a `.deb` package of the window and both engines

**Status:** in progress (2026-10-25) — steps 1–6 done and the package is built;
step 7's install/remove round trip is left for a person
**Depends on:** task_61 (the portable layout), task_116 (installer, the settings rule),
task_117 (the window as it is today)
**Milestone:** 2.7.0 or later

## Why, and what "done" means

The owner runs Ubuntu 26.04 on the same computer as a second system and wants a real
Debian package there.  A `.deb` is the opposite of the portable folder: it installs
into the system, is recorded by `dpkg`, and is removed by `apt`.  What it buys is the
integration the Windows installer gets from the registry — a menu entry, an «Открыть с
помощью» for `.pld` — plus honest dependencies and a removal that leaves nothing
behind.

**Done means:** a clean checkout on Ubuntu 26.04 produces
`dist/prologd_<version>_amd64.deb` with one command; `sudo apt install ./…deb` pulls
what it needs, `prologd-gui` starts from the menu, a `.pld` can be chosen in «Открыть с
помощью» (the *default* stays the user's choice, as with the association checkbox on
Windows), the settings land in `~/.config/PrologD/gui/gui.ini`, and `apt remove`
leaves `/opt` and `/usr` clean.

## Facts to measure first (fill them in here, like task_61 does)

Nothing below should be guessed; the Ubuntu machine is the only authority.

```sh
lsb_release -a; uname -m; ldd --version | head -1      # release, arch, glibc
python3 --version; cmake --version; ninja --version
apt-cache policy python3-pyside6.qtcore                # is PySide6 in the archive?
.venv/bin/python -c "import PySide6, sys; print(PySide6.__version__, sys.version)"
typst --version                                        # only for the docs target
python3 -c "from PySide6.QtWidgets import QApplication; print('widgets ok')"
```

Record: the glibc version (it is the floor for everyone who installs this `.deb`), the
Python version and whether PySide6 has a wheel for it, and whether the distro's own
`python3-pyside6` exists.  `requirements.txt` asks for `PySide6>=6.6`.

Measured on 2026-10-24 (Ubuntu 26.04.1 LTS "resolute", x86_64): glibc 2.43,
Python 3.14.4, PySide6 6.12.0 in `.venv` (the distro's `python3-pyside6.qtcore`
is 6.10.2), CMake 4.2.3, Ninja 1.13.2, Typst 0.15.1, PyInstaller 6.22.3,
`dpkg-deb`, `lintian`, `desktop-file-validate` and `xmllint` present.  The wheel
supports Python 3.14, so the freeze works; the distro's older PySide6 is not used.

## Steps

### 1. Engine and CLI on Linux

```sh
cmake --preset linux-release -DBUILD_WITH_PROLOGD=ON
cmake --build build/linux-release
ctest --test-dir build/linux-release
```

`BUILD_WITH_PROLOGD` is off by default.  It has to be on here: the package ships
both engines, and without it there is no `src/cli/prologd` for the window's
dual-engine checks (`both_engines` copies the pair).  The pinned commit builds on
Linux; the warnings it prints are upstream's and are not ours to fix here.

The CI job `Linux (GCC)` already builds this and runs the same tests on `ubuntu-latest`,
so failures here are about *this* release, not about the code.  Record the test count
(424 on Windows) and any test that turns out to be Windows-only.

### 2. The window on Linux

```sh
python3 -m venv .venv
.venv/bin/pip install -r src/gui/requirements.txt
export QT_QPA_PLATFORM=offscreen
export PROLOGD_TEST_EXE=$PWD/build/linux-release/src/cli/prologu
.venv/bin/python src/gui/tests/test_window.py     # and the other 29 scripts
.venv/bin/python src/gui/tests/protocol_smoke.py
```

Then the real thing, with a display: `.venv/bin/python src/gui/main.py
--include examples/lib`, open a lesson, F5, a margin marker, `Shift+F1`, `F1`, the
graphics window, the settings dialog.  Everything Windows-specific was kept behind
`sys.platform` (`paths.reveal_command` uses `xdg-open`), but nothing has ever been
*looked at* on Linux — this is the first honest check.  Small fixes belong to this
task; a big one is a note, not a rewrite.

### 3. The installed tree

Mirror the portable package, with the system's own places:

```
/opt/prologd/                                   root-owned, read-only for the user
    prologd-gui            frozen window (PyInstaller --onedir) + _internal/
    prologu, prologd       build/linux-release/src/cli/
    doc/*.pdf, builtins.json      PDFs only — no .typ, no read-me (task_116)
    examples/, stdlib/
/usr/bin/prologd-gui       symlink to /opt/prologd/prologd-gui, or a two-line wrapper
/usr/share/applications/prologd.desktop
/usr/share/mime/packages/prologd.xml
/usr/share/icons/hicolor/<size>/apps/prologd.png
/usr/share/icons/hicolor/<size>/mimetypes/application-x-prologd.png
/usr/share/doc/prologd/copyright, changelog.gz
```

The engine searches `stdlib` **beside its own executable**, and the window looks for
the engines beside itself — so they must all sit in one folder, exactly as in the
portable build.  A wrapper script is the safer choice for `/usr/bin` (PyInstaller's
launcher resolves its own path, but a wrapper also leaves room for `--settings`).

`prologd.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Пролог-Д
Comment=Учебная система логического программирования
Exec=prologd-gui %f
Icon=prologd
Terminal=false
Categories=Education;Development;
MimeType=application/x-prologd;
StartupWMClass=PrologD
```

`prologd.xml` (the MIME type — what the registry is on Windows):

```xml
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-prologd">
    <comment>Программа Пролог-Д</comment>
    <comment xml:lang="en">PrologD program</comment>
    <sub-class-of type="text/plain"/>
    <glob pattern="*.pld" weight="60"/>
  </mime-type>
</mime-info>
```

`postinst` runs `update-mime-database /usr/share/mime` and
`update-desktop-database -q /usr/share/applications` (guarded by `command -v`);
`postrm` runs them again after removal.  The **default** handler is not touched:
`xdg-mime default …` would silently take `.pld` from another editor — the same rule the
Windows installer follows with its unchecked box for a foreign handler.

### 4. Settings: installed means XDG, and say so on purpose

`paths.settings_path()` decides by three rules (task_116): a `gui.ini` that is already
beside the window, an install location, and whether the folder can be written.  On
Ubuntu `/opt/prologd` is root-owned, so the file lands in
`~/.config/PrologD/gui/gui.ini` — the right answer, but by accident of the writability
test.  Add `/opt` (and `/usr`, `/usr/local`) to `paths.install_roots()` so an installed
copy is recognised explicitly, with a check in `test_paths.py`; the Windows rules must
not change.  Confirm that `Settings.default_path()` gives
`~/.config/PrologD/gui/gui.ini` (Qt's `AppConfigLocation`, organisation `PrologD`,
application `gui`).

### 5. Icons for Linux

`pld.ico` is a Windows container and is not used here.  Linux wants PNGs in the
hicolor theme.  `src/gui/assets/pld.png` is 64 × 64 — the same source the ICO is made
from — so 16/24/32/48 are clean downscales and 128/256 are upscales (accepted on
Windows already).  Generate them with Pillow, the way `tools/make_pld_icon.py` does for
the ICO: either a `--png` mode there or a small `tools/make_png_icons.py`.  The
application icon (`prologd2.png`) is the same story.

### 6. The build script

`tools/build_deb.sh` — bash, LF, ASCII output, the twin of `tools/build_installer.ps1`:

1. check the tools (`cmake`, `ninja`, `python3`, `pyinstaller`, `dpkg-deb`);
2. build the engines (`cmake --preset linux-release -DBUILD_WITH_PROLOGD=ON`, `ctest`);
3. freeze the window (`PyInstaller --noconfirm --clean --onedir --windowed
   --name prologd-gui --paths src/gui src/gui/main.py`, the same flags as
   `build_portable.ps1`);
4. assemble `build/deb-tree/` (the `/opt` + `/usr` layout above) and `DEBIAN/control`
   with the version read from `prologu --version` (one source of the number, as on
   Windows), `Architecture: amd64`, `Depends: libc6 (>= <measured>), libgl1,
   libxkbcommon-x11-0, libxcb-cursor0, libfontconfig1, libdbus-1-3`,
   `Recommends: xdg-utils`, `Section: education`, `Priority: optional`;
5. `md5sums` over the tree, `find … -type f -exec md5sum`, then
   `dpkg-deb --build --root-owner-group build/deb-tree dist/prologd_<version>_amd64.deb`;
6. print where the `.deb` is and what is still for a person (the same tail the Windows
   script has).

Hand-written `DEBIAN/` + `dpkg-deb --build` rather than debhelper: no build-dependencies,
one script, and the same shape as the Windows packaging.  If the package ever goes into
a repository, `debsign`/`reprepro` is a separate conversation (the owner has already
decided against code signing for Windows for now).

### 7. Checks on the installed system

```sh
sudo apt install ./dist/prologd_<version>_amd64.deb
/opt/prologd/prologu --version         # the packaged engine answers (not on PATH)
prologd-gui                            # menu entry, icon, window
prologd-gui ~/проба.pld                # opens on the file, runs nothing
xdg-mime query filetype ~/проба.pld    # application/x-prologd
ls ~/.config/PrologD/gui/gui.ini       # settings where they belong
sudo apt remove prologd
ls /opt/prologd /usr/bin/prologd-gui 2>&1       # both gone
dpkg -l prologd | grep '^rc'                    # removed; dpkg keeps the rc state
sudo apt purge prologd                          # clears that state
```

`apt remove` leaves the package in `rc` even though it has no conffiles, so
`dpkg -L prologd | wc -l` answers with the line «does not contain any files (!)»
rather than 0; `apt purge` is what makes the package disappear from `dpkg -l`.
The settings file in `~/.config/PrologD/gui/gui.ini` is user data, not a package
file: it stays through both remove and purge, on purpose (put it aside by hand to
test a fresh user).

Also try a **fresh** user (or a container of the same release) — a package that only
works because the developer's venv is on `PATH` is not a package.  Record the `.deb`
size, the dependency list `apt` pulled in, and anything that needed a manual step.

## Progress

- [x] Step 1: `linux-release` with `-DBUILD_WITH_PROLOGD=ON` builds both engines;
      `ctest` — 424/424.  The pinned original engine compiles with GCC 15 (its own
      warnings remain).
- [x] Step 2: all 30 `src/gui/tests/test_*.py` scripts and `protocol_smoke.py` pass
      offscreen.  What the Linux run needed:
  * `test_the_output_limit_stops_a_flood`: a 100000-line flood can finish before the
    500 ms grace on Linux, and the `interrupt` request is dispatched only between
    requests, so the process stayed alive.  The query now ends with `ЖДИ(5000)`, so
    the grace expires while it is still solving; the test also checks
    `--- остановлено ---`.
  * `QDragEnterEvent` is built from `QPointF`: the `QPoint` overload is deprecated in
    PySide6 6.10.
  * `test_the_graphics_window_follows_the_program`: reopening shows the canvas that
    already holds the picture.  Waiting for `рисунок получен` after it raced the
    snapshot and passed only when the bitmap happened to arrive late.
  * `test_engines`: `launch` is checked with `engines.OURS.file_name`, not the
    Windows literal `prologu.exe`.
- `This plugin does not support propagateSizeHints()` is the offscreen platform
  plugin's own warning, once per window: harmless, and silenceable only by muting
  every default-category Qt warning.
- [x] Step 3: `installer/linux/` carries `control`, `postinst`, `postrm`, the
      `prologd-gui` wrapper, the desktop entry, the MIME XML, `copyright` (MIT,
      also in the root `LICENSE`), `lintian-overrides` and the hicolor PNGs.
      The desktop entry uses one main category (`Education;Development;` made
      `desktop-file-validate` hint at a duplicate menu entry).
- [x] Step 4: `paths.install_roots()` adds `/opt`, `/usr`, `/usr/local` on
      non-Windows; `test_paths.py` checks a frozen copy under each.  `Settings.
      default_path()` answers `$XDG_CONFIG_HOME/PrologD/gui/gui.ini`, checked
      with a temporary `XDG_CONFIG_HOME`.
- [x] Step 5: `tools/make_png_icons.py` regenerates 16/24/32/48/64/128/256 for the
      application and the `.pld` type from the two 64 px sources; the PNGs live in
      `installer/linux/icons/hicolor/` and are committed.
- [x] Step 6: `tools/build_deb.sh` checks the tools, configures `linux-release`
      with both engines, runs ctest, builds the docs, freezes the window with
      PyInstaller, assembles `build/deb-tree` (mode-normalised), checks the
      payload, writes `DEBIAN/` with the version from `prologu --version` and the
      measured glibc floor, and builds `dist/prologd_<version>_<arch>.deb`.
      `--skip-tests`, `--skip-docs` and `--skip-freeze` allow a quick repack.
- [x] Step 7, without root: the extracted payload passes `md5sum -c`, both engines
      run, lesson 1 loads, the frozen window stays up offscreen,
      `desktop-file-validate` and `xmllint` are clean, the type resolves to
      `application/x-prologd` in a temporary XDG tree, and `lintian` is clean with
      the documented overrides.
- [x] Step 7, installed by the owner: `sudo apt install` (the `_apt` sandbox
      notice is harmless — the file lies under a home folder `_apt` cannot
      traverse), the MIME type resolves to `application/x-prologd`, and
      `apt remove` leaves `/opt/prologd` and `/usr/bin/prologd-gui` gone.  The
      package stays in `rc` until `apt purge`; `~/.config/PrologD/gui/gui.ini` is
      user data and stays through both, on purpose.
- [ ] Step 7, still for a person: the menu entry, «Открыть с помощью», a fresh
      user, and the visual pass with a display (step 2's list).
- [x] Trimming (2026-10-25): `--exclude-module` does not take PySide6's Qt data with
      it, so the 2.6.1 package carried `Qt6Qml*`, `Qt6Quick`, `Qt6Pdf`,
      `Qt6VirtualKeyboard*` and `Qt6Network` — 23 MiB unpacked, measured on the
      published `.deb`.  `tools/build_deb.sh` now removes the same pieces by name
      (`TRIMMED`, mirroring `$trimmedFiles` of `build_portable.ps1`) plus the four
      plugins only they reach: `libqvnc` and `qtuiotouchplugin` need Qt6Network,
      `libqpdf` needs Qt6Pdf, the virtual-keyboard input context needs the rest.
      Step 7 then asks every remaining binary what it needs (`readelf -d`) and
      refuses a name that was taken away — the offscreen start alone cannot judge
      this, because a machine with system Qt would happily load a replacement.
      `--no-trim` keeps the old behaviour.

Built: `dist/prologd_2.6.0_amd64.deb`, 57,735,990 bytes (56 MiB), Installed-Size
185,908 KiB, 528 entries.  `Depends: libc6 (>= 2.43), libgl1,
libxkbcommon-x11-0, libxcb-cursor0, libfontconfig1, libdbus-1-3`;
`Recommends: xdg-utils`.

The 2.6.1 package as published was 66,242,272 bytes, Installed-Size 216,304 KiB
(the CI runner installs the newest PySide6 and its own glibc, which made
`libc6 (>= 2.39)`).  Measured on one machine, with the same sources and the same
`dpkg-deb` (zstd): 57,737,522 bytes without the trimming against 50,172,334 with
it — 7.57 MB (13%) less compressed, and Installed-Size 185,920 -> 162,128 KiB,
23.2 MiB less unpacked.  Compression gains less than unpacking: Qt libraries pack
about three to one.

## Rules that carry over from the Windows work

* The package ships **PDFs and `builtins.json`**, never `.typ` sources and no read-me
  (task_116/187); the manual is what explains the settings, the association and the
  Windows floor.
* The version comes from the engine's own `--version`, never typed twice.
* `dist/` stays out of git; `installer/linux/` (control, postinst, desktop, mime, icons)
  goes in, next to `installer/prologd.iss`.
* Don't touch the Windows packaging or the version in `CMakeLists.txt` as part of this
  task.
* Everything in `ai/` is English; user-facing texts are Russian (the product's language)
  with English where the desktop needs it (`Comment` in the `.desktop`, `comment
  xml:lang="en"` in the MIME file).

## Choices taken (the old open questions)

1. `Section:` is `education`; the desktop entry names one main category, so
   `desktop-file-validate` stays quiet.
2. `/usr/bin/prologd-gui` is a two-line wrapper (`exec /opt/prologd/prologd-gui
   "$@"`), not a symlink: it leaves room for a `--settings` argument later.
3. The window is frozen with PyInstaller on Linux too.  The distro's
   `python3-pyside6` exists (6.10.2) but is older than the 6.12 the sources use,
   and freezing keeps the Windows and Linux packages the same shape.
4. The `.deb` does not depend on `typst`: the PDFs are built at packaging time.

The install root and the wrapper are recorded in ADR-050.

## What to record when it is done

A journal part in `ai/status.md` with the measured facts above, the size of the `.deb`,
what `apt` pulled in, the result of the install/remove round trip, and every choice that
was not obvious — `ai/decisions.md` if it is architectural (for example «installed means
`/opt`»), the task file otherwise.
