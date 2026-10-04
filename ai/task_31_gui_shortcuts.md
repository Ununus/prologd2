# task_31 — GUI: keyboard-layout-independent insertions

**Status:** done (`prologd_gui/shortcuts.py`, settings `shortcuts/table`,
«Справка → Шпаргалка по вставкам»)
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
| `3` (`Shift+3` → `#`) | — | `#` | after |
| `/` (`Shift+/` → `?`) | `7` (RU: `?` is `Shift+7`) | `?` | after |
| `=` | — | `РАВНО(,)` | between `(` and `,` — `РАВНО(\|,)` |
| `.` (`Shift+.` → `>`) | — | `БОЛЬШЕ(,)` | `БОЛЬШЕ(\|,)` |
| `,` (`Shift+,` → `<`) | — | `МЕНЬШЕ(,)` | `МЕНЬШЕ(\|,)` |
| `=` (`Shift+=` → `+`) | — | `СЛОЖЕНИЕ(,,)` | `СЛОЖЕНИЕ(\|,,)` |
| `8` (`Shift+8` → `*`) | — | `УМНОЖЕНИЕ(,,)` | `УМНОЖЕНИЕ(\|,,)` |

The `\|` row of the draft is **gone**: `\` is not free.  `Ctrl+\` splits the editor
and `Ctrl+Shift+\` merges it (task_25), and the user's decision was to keep
«Объединить редакторы», so `|` has no chord at all — it is typed as it always was,
`Shift+\` in the English layout.

Every row is addressed by the **physical key**, so the same chord works in both
layouts.  `?` and `:` sit on different physical keys in US and ЙЦУКЕН, which is
why they have a second chord; the other symbols are *believed* to coincide on
the same keys, and that belief is checked rather than trusted:

- [x] Verify every row against the real Russian layout — done with
      `VkKeyScanExW` + `MapVirtualKeyW` in `src/gui/tests/test_shortcuts.py`
      (US `00000409` and RU `00000419`), which is stronger than the on-screen
      keyboard and does not depend on anyone remembering to look.  It found two
      things the plan had wrong: ЙЦУКЕН has **no** `[`, `#`, `>`, `<` or `'` at
      all (those keys carry letters, so the chord is the only way to type them),
      and the Russian `/` and `"` sit elsewhere — see the exceptions below.
- [x] Where `Shift` distinguishes two different inserts on one physical key
      (`=`, `.`, `,`), the `Shift` state must match exactly.  Where it does not
      (the `6` and `7` chords above), either state is accepted, so a user who
      types the Russian `:` as `Ctrl+Shift+6` and a user who types `Ctrl+6` both
      get the same insert.

Two symbols are therefore reachable on their English positions only, and the test
writes both out with the reason instead of hiding them
(`UNREACHABLE_IN_LAYOUT`): the Russian `/` sits on `Shift+\` — that is
`Ctrl+Shift+\`, «Объединить редакторы» — and the Russian `"` sits on `Shift+2`.

## Deliverables

- [x] `prologd_gui/shortcuts.py` — Qt-free table of entries
      `{scan_code, shift, insert, caret_offset}` plus the pure function that
      computes the replacement `(text, caret)` for a given `(scan_code, shift)`
      and the current selection.
- [x] Match on the **physical key**, i.e. `QKeyEvent.nativeScanCode()` (or the
      Qt `Qt.Key_*` value read from the *unshifted* level of the US layout),
      **never** on `event.text()`: the whole point is that the produced character
      differs between layouts.
- [x] Accept a chord only with exactly `Ctrl` (plus `Shift` where the symbol
      needs it) and **no** `Meta`/`Alt` — `Ctrl+Alt` is `AltGr` on many layouts
      and must not be swallowed, and `Alt` alone reaches the menu bar.
- [x] `event.accept()` for a matched key so no stray character is inserted by
      the editor; unmatched keys fall through unchanged.
- [x] Insert as a single undo step; with a selection, the bracket-like entries
      **wrap** it (`(` → `(выделение)`, `[` → `[…]`, `#` → `#…#`, `?` → `?…`),
      the rest replace it.  The wrapped text stays *selected*, so a second
      wrapping goes around it and nothing is lost.
- [x] The table is data (readable from the settings file) and holds a *list* of
      chords per entry, so a symbol that sits on two physical keys (see `:` and
      `?` above) or on a keyboard without that key can be remapped without a
      code change.
- [x] A short "шпаргалка" in the Справка menu listing the active combinations.
- [x] **Collision check with the rest of the UI**: the table takes `Ctrl+=`,
      `Ctrl+Shift+=`, `Ctrl+-`… so the font zoom must *not* use them — zoom is
      `Ctrl`+wheel plus the menu entries and `Ctrl+0` for reset (task_22,
      task_29).  `Ctrl+K` (comment), `Ctrl+U` (uncomment), `Ctrl+I` (format),
      `Ctrl+W`/`Ctrl+N`/`Ctrl+O`/`Ctrl+S` and `F3`/`F5`/`F10` stay as planned.
      Checked in both directions: `test_shortcuts.py` intersects the table with
      `actions.ACTIONS` and finds nothing in common (41 window shortcuts today).
- [x] Tests: `src/gui/tests/test_shortcuts.py` (Qt-free) — the mapping for every
      entry and chord, the caret offset, wrapping a selection, and a collision
      check that no two entries share `(scan_code, shift)`; an offscreen
      keyboard test that posts the events to the editor and checks the text and
      caret, skipped without PySide6.  Two window checks came with it: the cheat
      sheet shows the stored table, and a table written into the settings file
      decides what `Ctrl`+key inserts.
- [ ] Manual checklist on the real keyboard **with the Russian layout active** —
      this is the only test that proves the feature.  The *positions* are checked
      automatically now, so what is left for a human is the feel of it: that the
      chord lands where the hand expects, with the Russian layout on.

## Extra combinations worth having

Confirmed with the user before implementing, and the answer was "the basic and simple
symbols": the symbols only, **no** clause skeletons — `ФАКТ.`, `Правило(…) :- …`,
`?цель(…).`, `% комментарий` and `<- …` were dropped as writing the program for
the user rather than helping them type it.

* done: `Ctrl+/` → `/`, `Ctrl+-` → `-`, `Ctrl+1` → `!`, `Ctrl+'` → `''` (caret
  inside), `Ctrl+Shift+'` → `""` (caret inside), `Ctrl+Shift+-` → `_`;
* not done: `Ctrl+0` (taken by the zoom reset) and the five skeletons.

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

## What was built (notes for the next session)

* `prologd_gui/shortcuts.py` is the whole feature as data: `Chord(scan, shift,
  key, layout)`, `Entry(insert, chords, wrap, char)`, `Insert(text, start, end)`,
  and a `Shortcuts` table indexable by `(scan, shift)`.  `|` in `insert` marks the
  caret, `{}` in `wrap` marks the selection.  Nothing in it imports Qt, so the
  mapping, the wrapping, the JSON and the cheat sheet are checked without a
  window.
* The editor takes it in `set_shortcuts` (`buffers.py` passes it to every view)
  and `_insert_shortcut` runs **first** in `keyPressEvent`, before the completion
  popup and before `super()`: an insert must not be seen by anything else.
* `QKeyEvent` has two constructors and **only the second** carries a native scan
  code — `QKeyEvent(type, key, modifiers, nativeScanCode, nativeVirtualKey,
  nativeModifiers, …)`.  The seven-argument form silently drops it, which is how
  the first version of the offscreen test inserted nothing at all.
* Qt resolves a `QAction` shortcut *before* the widget sees the key, so this
  table and `actions.ACTIONS` must stay disjoint; `test_shortcuts.py` intersects
  them instead of trusting anyone to remember.
* The window writes the built-in table into its settings file (`shortcuts/table`,
  key `Settings.shortcuts_table`) on the first run — without that the table would
  not be "readable from the settings file" at all.  `Shortcuts.from_json`
  answers junk with the built-in table: a hand-edited file must not take the
  window down.
* `Ctrl+0` is the zoom reset rather than a sixth skeleton, and `Ctrl+1` inserts
  `!`:
  the five clause shapes the task proposed were dropped, so no digit above `1`
  had to be reserved.
* The dock for the cheat sheet is built like the task_37 reference pane (read-only
  `ZoomablePlainTextEdit`, hidden until asked for, in `_on_zoom_changed`), so a
  font size set once reaches it too — that was a defect in the reference pane and
  was not repeated here.
