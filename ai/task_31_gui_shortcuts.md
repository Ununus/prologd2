# task_31 — GUI: keyboard-layout-independent insertions

**Status:** not started
**Depends on:** task_22 (editor)
**Milestone:** M11

## Goal

Type Prolog punctuation and skeletons without switching away from the Russian
layout: `Ctrl` plus a key inserts the symbol that key carries in either layout.
`Alt` is **not** usable for this — on Windows a bare `Alt` moves the focus to the
menu bar (see the decisions below).

## The table

| `Ctrl` + physical key | Second chord | Inserts | Caret ends up |
|---|---|---|---|
| `;` | `6` (RU: `:` is `Shift+6`) | `:-.` | between `-` and `.` — `:-\|.` |
| `9` (`Shift+9` → `(`) | — | `()` | inside — `(\|)` |
| `[` | — | `[]` | inside — `[\|]` |
| `\` (`Shift+\` → `\|`) | — | `\|` | after |
| `3` (`Shift+3` → `#`) | — | `#` | after |
| `/` | `7` (RU: `?` is `Shift+7`) | `?` | after |
| `=` | — | `РАВНО(,)` | between `(` and `,` — `РАВНО(\|,)` |
| `.` (`Shift+.` → `>`) | — | `БОЛЬШЕ(,)` | `БОЛЬШЕ(\|,)` |
| `,` (`Shift+,` → `<`) | — | `МЕНЬШЕ(,)` | `МЕНЬШЕ(\|,)` |
| `=` (`Shift+=` → `+`) | — | `СЛОЖЕНИЕ(,,)` | `СЛОЖЕНИЕ(\|,,)` |
| `8` (`Shift+8` → `*`) | — | `УМНОЖЕНИЕ(,,)` | `УМНОЖЕНИЕ(\|,,)` |

Every row is addressed by the **physical key**, so the same chord works in both
layouts.  `?` and `:` sit on different physical keys in US and ЙЦУКЕН, which is
why they have a second chord; the other symbols are *believed* to coincide on
the same keys, but that must be checked while implementing rather than assumed:

- [ ] Verify every row against the real Russian layout — `VkKeyScanEx(ch, RU)`
      or the on-screen keyboard — and add a second chord to any symbol that
      turns out to live elsewhere.  A test cannot cover this; the manual
      checklist has to.
- [ ] Where `Shift` distinguishes two different inserts on one physical key
      (`=`, `.`, `,`), the `Shift` state must match exactly.  Where it does not
      (the `6` and `7` chords above), either state is accepted, so a user who
      types the Russian `:` as `Ctrl+Shift+6` and a user who types `Ctrl+6` both
      get the same insert.

## Deliverables

- [ ] `prologd_gui/shortcuts.py` — Qt-free table of entries
      `{scan_code, shift, insert, caret_offset}` plus the pure function that
      computes the replacement `(text, caret)` for a given `(scan_code, shift)`
      and the current selection.
- [ ] Match on the **physical key**, i.e. `QKeyEvent.nativeScanCode()` (or the
      Qt `Qt.Key_*` value read from the *unshifted* level of the US layout),
      **never** on `event.text()`: the whole point is that the produced character
      differs between layouts.
- [ ] Accept a chord only with exactly `Ctrl` (plus `Shift` where the symbol
      needs it) and **no** `Meta`/`Alt` — `Ctrl+Alt` is `AltGr` on many layouts
      and must not be swallowed, and `Alt` alone reaches the menu bar.
- [ ] `event.accept()` for a matched key so no stray character is inserted by
      the editor; unmatched keys fall through unchanged.
- [ ] Insert as a single undo step; with a selection, the bracket-like entries
      **wrap** it (`(` → `(выделение)`, `[` → `[…]`, `#` → `#…#`, `?` → `?…`),
      the rest replace it.
- [ ] The table is data (readable from the settings file) and holds a *list* of
      chords per entry, so a symbol that sits on two physical keys (see `:` and
      `?` above) or on a keyboard without that key can be remapped without a
      code change.
- [ ] A short "шпаргалка" in the Справка menu listing the active combinations.
- [ ] **Collision check with the rest of the UI**: the table takes `Ctrl+=`,
      `Ctrl+Shift+=`, `Ctrl+-`… so the font zoom must *not* use them — zoom is
      `Ctrl`+wheel plus the menu entries and `Ctrl+0` for reset (task_22,
      task_29).  `Ctrl+K` (comment), `Ctrl+U` (uncomment), `Ctrl+I` (format),
      `Ctrl+W`/`Ctrl+N`/`Ctrl+O`/`Ctrl+S` and `F3`/`F5`/`F10` stay as planned.
- [ ] Tests: `src/gui/tests/test_shortcuts.py` (Qt-free) — the mapping for every
      entry and chord, the caret offset, wrapping a selection, and a collision
      check that no two entries share `(scan_code, shift)`; an offscreen
      keyboard test that posts the events to the editor and checks the text and
      caret, skipped without PySide6.
- [ ] Manual checklist on the real keyboard **with the Russian layout active** —
      this is the only test that proves the feature.

## Extra combinations worth having

Free physical keys not used above, same rule (proposals, confirm before
implementing): `Ctrl+/` → `/`, `Ctrl+-` → `-`, `Ctrl+1` → `!`,
`Ctrl+'` → `''` (caret inside), `Ctrl+Shift+'` → `""` (caret inside),
`Ctrl+Shift+-` → `_`, `Ctrl+0` — taken by the zoom reset, and `Ctrl+1`…`Ctrl+5`
for five skeletons: `ФАКТ.`, `Правило(…) :- …`, `?цель(…).`, `% комментарий`,
`<- …`.

## Decisions (from the user, 2026-09-29)

* The modifier is **`Ctrl`, not `Alt`**: `Alt` moves the focus to the menu bar,
  and the previous front-end already used `Ctrl` for its insert helpers.
* `?` gets **two chords**, `Ctrl+/` (US position) and `Ctrl+7` (Russian
  position); the same is done for `:` (`Ctrl+;` and `Ctrl+6`).
* Both layouts must produce identical results — that is the point of matching
  the physical key rather than the character.

## Acceptance

With the Russian layout active, every row of the table inserts the listed text
with the caret in the listed position, the behaviour is identical with the
English layout, `Ctrl+Alt+…` and `Alt+…` are untouched, and the insert can be
undone with a single `Ctrl+Z`.
