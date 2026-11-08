# task_121 — the 2.8.0 release round

**Status:** done (2026-11-09) — published as <https://github.com/Ununus/prologd2/releases/tag/v2.8.0>
**Depends on:** everything from `v2.7.0` to `main` (10 commits: the sorting split, the
new diagnostic wording, `atan`/`atan2`, `ВРЕМЯ/1`, the macOS bundle fix, `ФОРМАТ` and
`ВЫВОДФ`)
**Milestone:** 2.8.0

## What the owner asked for

«Сделаем v2.7.1?»

The plan was a patch release, cut only to rebuild the macOS `.dmg` — the released 2.7.0
bundle kept `stdlib` beside the window instead of beside the engine, so the window's
welcome program failed with «Не найден импортируемый файл 'iso.pld' … Искался в:
/iso.pld» (part 265).  The round then grew: `atan`/`atan2`, `ВРЕМЯ/1`, `ФОРМАТ/2+`,
`ВЫВОДФ/1+`, the split of the sorts and a new diagnostic wording.

## Why 2.8.0 and not 2.7.1

A patch number promises that nothing breaks.  Two things in this round do:

* **`СОРТИРОВКА/2` changed meaning.**  In 2.7.0 it dropped duplicates
  (`СОРТИРОВКА([3, 1, 2, 1], С)` was `С=[1,2,3]` and the manual said so); since part
  259 it keeps them (`[1,1,2,3]`).  A program written for 2.7.0 does not fail — it
  answers differently, which is worse.
* **The English spelling of `sort` moved.**  `sort/2` is `МНОЖЕСТВО/2` now, while
  `sort/3` stays `СОРТИРОВКА/3` and `msort/2` is `СОРТИРОВКА/2`.

New predicates do not force a minor on their own — but a silent behaviour change at a
released name does.  The owner agreed to `2.8.0`.

## The number

`CMakeLists.txt` is the single source: `VERSION 2.8.0` and
`PROLOGD_RELEASE_DATE "2026-11-09"` — `prologd --version` answers
`prologd 2.8.0 (2026-11-09)`.  The copies written by hand, bumped together:

| where | what |
| --- | --- |
| `src/prlib/include/prlib/version.hpp` | the banner in `versionBanner`'s doc comment and «`2.8.0` is what the program is» |
| `doc/help.typ` §13 | the example banner beside `ВЕРСИЯ` |
| `installer/prologd.iss` | the `ISCC` example line, the `#define AppVersion` default and the «Пролог-Д 2.8.0 Setup» comment; the file keeps its **BOM** |
| `tools/build_installer.ps1` | the `-Package` example in the header |
| `tools/check_dependencies.py` | the usage line and the default package path |
| `tools/macos_plist.py` | the usage line |
| `README.md` | the `apt install ./prologd_2.8.0_amd64.deb` example |

`?ВЕРСИЯ` keeps printing `27.1`: that is the dialect, not the release (ADR-055).

## What the release says changed since 2.7.0

* **Fixed:** the macOS bundle keeps the library beside the engine
  (`Contents/MacOS/bin/stdlib`); a package is now checked by an importing program run
  from `/` before signing (part 265).  A malformed command line exits with 1, whatever
  CLI11 reports (part 258).
* **New predicates:** `ВРЕМЯ/1` (`elapsed`) — monotonic seconds since the start, for
  measurements (part 264); `ФОРМАТ/2+` (`format_string`) and `ВЫВОДФ/1+` (`format`) —
  a pattern with `{}` places (part 266); `МНОЖЕСТВО/2` (`sort`) — the set, which did
  not exist as a separate predicate (part 259).
* **New functions:** `atan(X)` and `atan2(Y, X)`, the ISO arc tangents (part 263).
* **Changed, and named in the notes:** `СОРТИРОВКА/2` keeps duplicates, `sort/2` is
  `МНОЖЕСТВО/2`; the type diagnostic names the kind of the term and the spelling the
  program used (part 260).
* **Documentation:** every «Отличие от ISO» claim checked against SWI 9.2.9 and GNU
  Prolog 1.5.0 (parts 261, 262) — five claims corrected, the term order of `1` and
  `1.0` documented as ours; `stdlib/iso.pld` says what is the standard and what is a
  common library name, and what is missing; `examples/io.pld` (was `file_io.pld`)
  shows the whole of input and output and is now checked by tests like the rest.

## Checks to make here

* `linux-release` — 457/457; `linux-werror` — 457/457; `--version` in both trees prints
  `prologd 2.8.0 (2026-11-09)`; `?ВЕРСИЯ` still `27.1`.
* 29 scripts of `src/gui/tests` and `protocol_smoke.py` — green.
* `--target docs` — five PDFs, no empty page; the §13 page looked at.
* `git ls-files --eol` on every touched file — `w/lf`; the `.iss` still starts with a BOM.

## How it went

1. `main` was pushed before the tag: `ci` (`42532781363`) and `macos` (`42532781305`)
   on `Версия 2.8.0` — green.  The macOS run is the one that matters this round: the
   «Import the library from the bundle» step added in part 265 ran on the Mac runner
   and passed, so the fix was proven before the tag existed.
2. `v2.8.0` is an annotated tag on `84e12fc` with a Russian message; the pattern of
   `v2.7.0` is kept.
3. The tag ran `release.yml` (`42533348467`): Linux `.deb`, Windows portable and
   installer, macOS `.dmg`, draft release — all four jobs green, no step retried.
4. The draft was checked before publishing, then the notes were replaced with a
   hand-written body (build table, «Исправлено», «Новое», «Изменилось», «Замечания»)
   and the release was published and marked **Latest**.

## Checks on the published assets

* `.deb`: `Version: 2.8.0`; `--version` answers `prologd 2.8.0 (2026-11-09)`; four
  PDFs and the two JSON files in `doc/`, no `technical.pdf`; `examples/io.pld` is
  there; through `-I` the library answers `atom_length(пролог, N)` = 6; `?ВЕРСИЯ` is
  `27.1`; `atan2(1, -1)` = 2.356194490192345, `ВРЕМЯ` binds a real, `ФОРМАТ` gives
  `2 + 3 = 5`.
* `.zip`: `prologd.exe`, `prologd-gui.exe`, `_internal`, `doc`, `examples`, `stdlib`;
  the version string inside `prologd.exe` reads `2.8.0 (2026-11-09)`.
* `.dmg`: **`PrologD.app/Contents/MacOS/bin/stdlib`** — the library is beside the
  engine, which is what this release was cut for; `examples` and `doc` stay beside the
  window; `CFBundleShortVersionString` and `CFBundleVersion` are both `2.8.0`.

## What is still left for a person

1. **The frozen window on a real desktop** — a click-through of the installed package,
   macOS especially.  The bundle is now checked by a run, not by eye, but no script
   clicks through the window.
2. **Known defect, not fixed.**  Under Wayland the window takes a dropped file as text
   (Qt 6.12 and the desktop portal).  Workaround: `QT_QPA_PLATFORM=xcb`.  It stays in
   the notes.
