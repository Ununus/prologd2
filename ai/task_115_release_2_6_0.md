# task_115 — the 2.6.0 release round

**Status:** done (2026-10-24) — part 181
**Depends on:** task_99…task_114 (everything the round summarises)
**Milestone:** 2.6.0

## What the owner asked for

After the feature rounds were finished («Вроде всё основное сделали»), the owner
picked the release preparation out of the offered list: items 1–3, 6 and 8, then a
full verification sweep, portable packages `both` and `d` (not `u`), and the tag.

## 1–2. The version

`CMakeLists.txt` is the single source of the number (`src/prlib/CMakeLists.txt`
configures `version.cpp.in` from it, and the `cli_version` test compares the two), so
`project(prologd VERSION 2.6.0 …)` is the whole change — `prologu --version` answers
`Пролог-У 2.6.0 (2026-10-24)`.  `doc/help.typ` §13 quotes that banner as an example
of `ВЕРСИЯ`, so its number and date were moved with it.

## 3. README: the command line and the protocol

* The usage block was missing three options the CLI has had since task_99/101:
  `--vars 0|1|2`, `--names 0|1|2`, `--dialect ru|en`.  Added with the same padding
  and wording as `--help`.
* The protocol paragraph said «Protocol version 2 adds the reserved names…», which
  reads as if 2 were the current version.  It now states the contract is at
  version **16**, that a front-end reads the number from `ready`, and that version 2
  was the change that put the reserved names and their arities into `ready`; the
  later versions are described one by one in the contract itself.

## 3 (cont.) `src/gui/README.md`

The section heading said «Protocol contract (version 13)» while the engine sends 16.
Retitled, and the sentence about 13 is followed by what 14, 15 and 16 added: `screen`
as an event (the canvas of `:- ХОЛСТ(…)`, ADR-035), `names` in `format` (task_99),
`dialect` in `format` (`en`/`ru`, task_101).

## 6. `_on_formatted` no longer maps offsets of a fragment

The caret was mapped with `formatter.map_positions(pending["old"], text, …)` before
the replacement, for every request.  For «только выделенное» `text` is the formatted
*fragment*, so offsets computed from the whole old buffer were meaningless — the
selection afterwards came from a mapping that could not be right.  The call moved
into the whole-buffer branch, which is the only one where `old` and `text` describe
the same document; a replaced region keeps the selection it was given.

## 8. `ai/plan.md`

The milestone table stopped at M17 (the portable package, task 61).  Added
`M18 | The editor: completion, statement forms, conversion, the session and closing
| 99–114`.

## Checks

* `cmake --build … --config Release`, `ctest` — **424/424**.
* 29 `src/gui/tests/test_*.py` suites and `protocol_smoke.py` — all green.
* `--target docs` — 7 PDFs, no warnings; help page 35 looked at: `ВЕРСИЯ` shows
  `Пролог-У 2.6.0 (2026-10-24)`.
* `git ls-files --eol` on every touched file — `w/lf`.

## Packages

`.\tools\build_portable.ps1 -Engine both` → `dist\prologd-2.6.0-win64` (and `.zip`,
38.5 MiB) with `prologu.exe`, `prologd.exe`, the window, 7 manual PDFs and `stdlib`;
`-Engine d` → `dist\prologd-1.27-win64` (37.1 MiB) with `prologd.exe`, the window and
the six PDFs that apply.  Smoke: `prologd.exe --source=examples\prologd\factorial.pld`
answers `ф=720` in the `both` package, `--source=examples\factorial.pld` answers the
same in the `d` package, `prologu --version` prints 2.6.0.

**Trap that cost time:** the script sets `$ErrorActionPreference = 'Stop'`, so it must
be run plainly.  With the streams merged at the call site (`2>&1 | …` or `*> file`)
the first line PyInstaller writes to stderr becomes a terminating error inside the
freeze step, and the script reports `FAILED … & $python @freeze` with a single
`INFO: PyInstaller` line as the whole explanation.  Nothing is wrong with the build.

## Tag

`v2.6.0`, annotated.
