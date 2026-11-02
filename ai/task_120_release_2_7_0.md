# task_120 — the 2.7.0 release round

**Status:** in progress (2026-11-02) — the version is raised; the packages and the tag
are left
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

## What is left for a person

1. **The commits are not pushed.**  `main` is ten commits ahead of `origin/main`; no
   workflow has seen them.  `git push` first, then read the three CI runs.
2. **Packages.**  `tools/build_deb.sh` builds and was checked here (four PDFs, no
   `technical.pdf`, the frozen window starts).  The Windows pair —
   `tools/build_portable.ps1` and then `tools/build_installer.ps1 -SkipPackage` — needs
   a Windows machine, and it carries the change of part 254 (the package ships four
   manuals now, `technical.pdf` stays at home) — it has not been run since that.
3. **The frozen window on a real desktop.**  `test_window.py` runs offscreen; a
   click-through of the packaged folder is the check no script makes (task_61 §7.1).
4. **Known defect, not fixed.**  Under Wayland the window takes a dropped file as text:
   Qt 6.12 asks the portal for the URIs, the portal times out, and Qt hands the
   *portal key* to the drop handler as `text/uri-list`
   (`qwaylanddataoffer.cpp`, `content = readData(mime)` instead of `uriList()`).  Not
   ours to fix; the workaround for a user is `QT_QPA_PLATFORM=xcb`.  The report text
   lives in the session folder, not in the repository.
5. **The tag.**  `v2.7.0`, annotated, on the commit that carries this number; the tag
   runs `release.yml`, which opens a **draft** release — read the asset names and the
   notes before publishing.

## Checks made here (2026-11-02)

* `linux-release` — 445/445; `linux-werror` — 445/445; `prologd --version` in both
  trees prints `prologd 2.7.0 (2026-11-02)`.
* 29 scripts of `src/gui/tests` and `protocol_smoke.py` — green.
* `--target docs` — five PDFs, no warnings; help page 36 looked at: `ВЕРСИЯ` — `27.1`,
  the example banner — `prologd 2.7.0 (2026-11-02)`.
* `git ls-files --eol` on every touched file — `w/lf`; the `.iss` still starts with a
  BOM.
