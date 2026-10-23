# task_100 — the old dialect learns quoted atoms and `_` variables; a new pin

**Status:** done (2026-10-23)
**Depends on:** task_67 (two name modes), task_77 (`2` merged into `1`), task_99
(the conversion this unblocks)
**Milestone:** post-2.5.0

## Goal

The original engine now reads `'атом'` (a quoted constant) and `_имя` (a
variable) — commit `daf6b1b` on `Ununus/prologd`, «Атомы в кавычках и переменные с
подчёркиванием».  Pin it, and make our engine and the window's highlighting follow
the same rules.  This is also what removes the awkward half of task_99's reverse
direction: an ISO atom like `x` or `'a b'` finally has a spelling in the old
naming (`'x'`, `'a b'`) instead of having to become a string.

## What upstream changed (`daf6b1b`, `823a9d1..daf6b1b`)

- `quotedconst()` in `functions.cpp`: `'…'` is a constant read up to the closing
  quote, so spaces and separators (`,` `.` `(` `)` `?` `:`) are allowed inside;
  the quotes are **not** part of the name, which makes `'атом'` and `атом` the same
  constant (it prints without quotes, like any atom); an unclosed quote is the new
  error **45 `InvalidAtomFormat`** («Неверный формат атома»), the old numbers did
  not move.  A quoted name works as a predicate name too (`?'пункт'(1).`).
- `issvar()` / `issconst()`: a variable is a one-letter name, a name ending in
  `'`, or a name starting with `_`; everything else is a constant.  `_` alone is
  still the anonymous variable (`hpunkn`), and the scanner's `case '_'` now tells
  `_` from `_имя` with the new `underscorename()`.  `_Пер'` is the same variable as
  `_Пер` — the apostrophe is stripped, because a silent `_Арг` in a head against
  `_Арг'` in a body is exactly the bug the rule avoids.  Case still matters
  (`_Пер` ≠ `_пер`).
- New cases in `src/tests/test_scanner.cpp`, the rules written into `doc/help.typ`.

## What was done — and what was already there

- [x] `CMakeLists.txt`: `PROLOGD_ENGINE_COMMIT` → `daf6b1bf60a68200268adc81f8e7e4cb9ce65603`,
      with the «Bumped in part 164» sentence in the comment block and the note
      about the stale `PROLOGD_ENGINE_COMMIT=7b7f46f…` in `CMakeCache.txt`.
      Then rebuilt with `prologd.exe`.
- [x] Our lexer (`src/prlib/src/lexer.cpp`): `'атом'` and `_Имя` needed nothing —
      both already worked in both modes; **`_Пер'` did**, and now the apostrophe is
      consumed and kept out of the name in the old mode.  ISO keeps `'` a quote
      (eating it there would hide a typo).  Case still tells `_Пер` from `_пер`,
      and a lone `_` takes no suffix.
- [x] Parser: **nothing to do** — a quoted atom has been a legal functor since
      task_96, in both modes; a runtime case now pins it (`?'пункт'(атом).` → ДА).
- [x] Printing: **nothing to do** — the writer prints an atom by its text, so
      `'Тоже атом'` comes out as `Тоже атом`, which is exactly what the original
      prints («кавычки в имя не входят»).  Pinned in the same runtime case.
- [x] The window: **nothing to do in `tokens.py`** — `_identifier()` already
      returns VARIABLE for `_…`, `'…'` is QUOTED_ATOM in every mode and `имя'` a
      variable in the old one.  `test_highlighter.py` pins the old mode's colours
      and that the apostrophe belongs to the variable's token there.
- [x] Tests: two cases in `test_lexer.cpp`, one in `test_builtins_control.cpp`
      (four blocks: quoted constant ≡ bare atom; `_Пер'` ≡ `_Пер`; `_` stays
      anonymous; a quoted functor and a printed atom), one in
      `test_highlighter.py`.  `ctest` — **410/410** (was 408).
- [x] Docs: `doc/prologd-diff.typ` (the short table gains «Атом в кавычках» and
      re-states the variable rows; the sections «Переменные», «Константы,
      начинающиеся с заглавной», «Режим чтения имён» and the migration line),
      `doc/help.typ` (§2 and the comparison table), `ai/reference_notes.md`.
      `tools/build_portable.ps1` needed no change: `$kinds` is about packages,
      not syntax.

## Decisions and open questions

- The marker and `--vars` story does not change: these are rules of the old
  dialect, not a third mode.  `2` keeps meaning `1`.
- Our **ISO** mode does not strip `_Пер'`: in ISO `'` opens a quoted atom, and
  quietly eating it would hide a typo; the suffix belongs to the old dialect.
- Upstream's error *number* 45 is not adopted — our codes are our own and the
  message («Незакрытая кавычка в имени константы») already says the same thing.
- One residual loss in task_99's reverse direction, and it stays: an atom that
  contains a `'` cannot be written in the old dialect at all — upstream reads
  `'…'` up to the first closing quote, with no doubled-quote escape.

## Measurements (2026-10-23)

- `git ls-remote https://github.com/Ununus/prologd.git` → `master` =
  `daf6b1bf60a68200268adc81f8e7e4cb9ce65603`; the clone the build keeps in
  `build/windows-msvc/prologd-engine/src/prologd_engine` shows **one** commit over
  our pin `823a9d1`, touching `err.{h,cpp}`, `functions.{h,cpp}`, `scaner.cpp`,
  `doc/help.typ`, `src/tests/test_scanner.cpp`.
- The probe `build\probe-old-rules.pld` — a fact `пункт(атом)`, a question
  `?пункт('атом')`, a clause `одинаковые(_Пер, _Пер')` and two questions about it —
  prints `ДА / ДА / НЕТ` in both engines: `prologd.exe -s=…` and
  `prologu --vars 1 -s …`.  (The original's command line wants the equals sign:
  `-s=path`, not `-s path`.)
- Our lexer already had `case '\''` → `lexQuotedAtom` with no mode check, and
  `lexIdentifier` tested `text.front() == '_'` before the mode branch — so only
  `_Пер'` needed code.
