# task_120 — the 2.7.0 release round

**Status:** done (2026-11-02) — published as <https://github.com/Ununus/prologd2/releases/tag/v2.7.0>
**Depends on:** everything from `v2.6.1` to `main` (40 commits: the name `prologd`,
the dialect at 27.1, exact numbers, the predicates of text and of the base, the editor
rounds, the installer, the Linux `.deb`)
**Milestone:** 2.7.0

## What the owner asked for

«Давай повысим версию 2.7.0.  Не осталось чего важного перед этим?»

## The number

`CMakeLists.txt` stays the single source: `VERSION 2.7.0` and
`PROLOGD_RELEASE_DATE "2026-11-02"` — `prologd --version` answers
`prologd 2.7.0 (2026-11-02)`.  The copies that are written by hand and have to follow:

| where | what |
| --- | --- |
| `src/prlib/include/prlib/version.hpp` | two lines of the doc comment (the banner, «`2.7.0` is what the program is») |
| `doc/help.typ` §13 | the example banner beside `ВЕРСИЯ` |
| `installer/prologd.iss` | the `ISCC` example line, the `#define AppVersion` default and the comment about «Пролог-Д 2.7.0 Setup»; the file keeps its **BOM** |
| `tools/build_installer.ps1` | the `-Package` example in the header |
| `tools/check_dependencies.py` | the usage line and the default package path |
| `tools/macos_plist.py` | the usage line |

`?ВЕРСИЯ` keeps printing `27.1` — that is the dialect, and `kDialectVersion` must not
follow the release number (ADR-055).

## How it went

1. `main` was pushed before the tag: `ci` and `macos` on `Версия 2.7.0` (`41448623731`,
   `41448623709`) — green.
2. `v2.7.0` is an **annotated** tag on `b6eb4c7` with a Russian message summarising the
   round (the pattern of `v2.6.1` is a bare «2.6.1»; this one says what changed, which
   is what a reader of the repository sees first).
3. The tag ran `release.yml` (`41468717545`): Linux `.deb`, Windows portable + installer,
   macOS `.dmg`, then the draft release.  All four jobs green, no step retried.
4. The draft was checked before publishing: four assets with the right names
   (`prologd_2.7.0_amd64.deb`, `prologd-2.7.0-win64.zip`, `prologd-2.7.0-setup.exe`,
   `PrologD-2.7.0-arm64.dmg`); the generated notes were replaced with a hand-written
   body — the build table, «Что нового», «Замечания» with the Wayland defect and the
   unsigned-binary warning of each platform.  Then published, marked **Latest**.

## Checks on the published assets

* `.deb`: `Version: 2.7.0`; `/opt/prologd/doc` holds four PDFs and the two JSON files,
  no `technical.pdf`; the unpacked `prologd --version` answers
  `prologd 2.7.0 (2026-11-02)`; `examples/database.pld` runs, `iso.pld` through `-I`
  answers `atom_length(пролог, N)` = 6, `atom_concat` = `пролог`, `sub_atom` = `про`.
* `.zip`: `prologd.exe` and `prologd-gui.exe` at the root, the same four PDFs, the new
  `examples/types.pld` and `examples/database.pld`, `stdlib/iso.pld`; the version string
  inside `prologd.exe` reads `2.7.0`.  The window itself is exercised by CI offscreen
  only.

## What is still left for a person

1. **The frozen window on a real desktop** — a click-through of the installed package;
   no script makes that check (task_61 §7.1).  macOS especially: the release is built in
   the cloud and has never been started on a Mac.
2. **Known defect, not fixed.**  Under Wayland the window takes a dropped file as text:
   Qt 6.12 asks the portal for the URIs, the portal times out, and Qt hands the
   *portal key* to the drop handler as `text/uri-list`
   (`qwaylanddataoffer.cpp`, `content = readData(mime)` instead of `uriList()`).  Not
   ours to fix; the workaround for a user is `QT_QPA_PLATFORM=xcb`.  It is named in the
   release notes.

## Checks made here (2026-11-02)

* `linux-release` — 445/445; `linux-werror` — 445/445; `prologd --version` in both
  trees prints `prologd 2.7.0 (2026-11-02)`.
* 29 scripts of `src/gui/tests` and `protocol_smoke.py` — green.
* `--target docs` — five PDFs, no warnings; help page 36 looked at: `ВЕРСИЯ` — `27.1`,
  the example banner — `prologd 2.7.0 (2026-11-02)`.
* `git ls-files --eol` on every touched file — `w/lf`; the `.iss` still starts with a
  BOM.
