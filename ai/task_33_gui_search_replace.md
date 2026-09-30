# task_33 — GUI: find and replace

**Status:** done — the bar, the keys, the highlight, «Заменить всё» as one undo
step and `search.py` are in; `test_search.py` has seventeen checks, half of which
open a window but start no interpreter
**Depends on:** task_22 (the editor), task_26 (the action table, where the five
menu entries already sit disabled)
**Milestone:** M11

## Goal

Give the five entries of the **Поиск** menu something to do.  Searching is the
one feature a program editor is unusable without: a lesson program is a few
hundred lines, and `Ctrl+F` is how a reader finds the clause they are looking at.
The reference front-end had it (five `search-find*` icons came from it), the
menus and shortcuts are already declared, and the tooltips say «ещё не
реализовано» — this task removes that sentence.

## Deliverables

- [x] A find bar that appears above the editor (not a modal dialog: a modal box
      cannot be driven from a headless test — see the note in `buffers.py` about
      the same trap with `_ask_save`), with:
  * a **Найти** field, prefilled with the selection when there is one, and the
    word under the cursor when there is not;
  * a **Заменить на** field and the buttons **Заменить**, **Заменить всё** (the
    replace half may be hidden behind a disclosure triangle, as most editors do);
  * the switches **С учётом регистра**, **Слово целиком**, **Только в
    выделении**;
  * a count of what was found, in the form «3 из 17», and the search's own
    wrapping reported rather than silent.
- [x] Keys: `Ctrl+F` opens the bar and focuses the field, `Esc` closes it and
      returns focus to the editor, `F3` and `Shift+F3` find forwards and
      backwards even with the bar closed, `Ctrl+F3` and `Ctrl+Shift+F3` search
      for the word under the cursor, `Enter`/`Shift+Enter` in the field are the
      same as `F3`/`Shift+F3`.  The five actions stop being `implemented=False`.
- [x] Every match is highlighted in the editor while the bar is open (an extra
      selection in a palette colour, the way the error line already is), and the
      *current* match is told apart from the rest.  The highlight goes when the
      bar closes; the document itself is never modified by searching.
- [x] **Заменить всё** is *one* undo step, the way comment/uncomment is: a single
      `beginEditBlock`/`endEditBlock` around the whole replacement.  Nothing is
      replaced inside the *found* text by accident: replacements never re-scan
      their own output.
- [x] The search is plain text, not a regular expression: the programs are in
      Russian and often contain `#…#`, `?` and parentheses, where regex syntax
      would surprise more than help.  A `QRegularExpression` would be a later
      task with its own switch.
- [x] Case-insensitive search compares with `str.casefold()` (Cyrillic included),
      and a search for a word *does* cross the ends of the document — wrapping is
      reported in the bar.  Folded on a *slice*, not on a copy of the whole text:
      a fold that changes a string's length must not shift the offsets after it.
- [x] The bar follows the **active pane**: the split editor has two panes over one
      document set, so «Найти» acts on the pane that was used last, and the
      matches are highlighted in every view of that document (they share one
      text).
- [x] Tests: `src/gui/tests/test_search.py` — finding the first, the next and the
      previous match, wrapping in both directions, a search that matches nothing,
      case sensitivity, whole word, «заменить всё» as one `Ctrl+Z`, the bar
      closing on `Esc` with focus back in the editor, and the five menu entries
      becoming enabled.
- [x] The `edit-find-replace` icon is drawn (or the existing `search-find.png`,
      which is already in `assets/` and unused, is given the name the action
      asks for) and the name leaves `assets.MISSING`; `test_icons.py` keeps the
      two lists in step.

## Design notes

* The `search-find*` icons of the reference project are already in
  `src/gui/assets` (`search-find`, `search-find-next`, `search-find-prev`,
  `search-find-selected-next`, `search-find-selected-prev`) and
  `actions.py` already names them, so only `edit-find-replace` was missing — and
  it arrived with the rest of the pictures.
* A `QPlainTextEdit` gives the cursor and the document; a search over
  `document().toPlainText()` with `str.find` is enough — the file is small, and a
  hand-written scanner keeps the «найти выделенное» and the count honest.
  Performance is not a concern at this size; if it ever becomes one, the
  tokenizer's line index is the thing to reuse.
* Two Qt notes that already cost time here and apply again: the editor's context
  menu must not collect a second copy of an action (`_apply_context_actions`
  guards this with a dynamic property), and a bar that is hidden with
  `setVisible(False)` inside a layout is not the same as one removed from it —
  the editor must not keep a gap where the bar was.

## Acceptance

`Ctrl+F` opens the bar with the selection in the field, `F3` walks through the
matches of the active pane and wraps at the end, `Ctrl+F3` searches for the word
under the cursor, `Заменить всё` is undone by one `Ctrl+Z`, `Esc` closes the bar
and the editor has the focus again, and none of it writes to the file.

## What was built (2026-09-29)

* `prologd_gui/search.py` — Qt-free engine: `Options(match_case, whole_word,
  span)`, `matches`, `count`, `match_at`, `next_match`, `previous_match`,
  `replace_all`.  Offsets always point into the original text.
* `prologd_gui/findbar.py` — the strip: «Найти», next/previous, the count, the
  three switches, «Замена» behind a disclosure with «Заменить» and «Заменить
  всё».  It owns the question and the switches and knows nothing about editors, so
  there is one place where a search is turned into offsets, and that place is
  `search.py`.
* `window.py` — the state machine: `show_find`, `close_find`, `find_selected`,
  `find_step`, `replace_current`, `replace_all`, the highlight in every view of
  the active document and the re-follow when the pane or the tab changes.
* `editor.py` — `word_under_cursor()`, `search_ranges()`, and the extra selections
  now compose the diagnostic line, the search's matches and the selected word's
  occurrences in one list (Qt keeps one).

Three decisions worth keeping:

1. **A match the caret is *inside* is the one that is found** (`search.match_at`),
   so `Ctrl+F` in the middle of `факт` lands on that `факт`; `F3` is unaffected
   because it steps *after* the match it is on.  Without it `Ctrl+F` jumped to the
   next occurrence, which reads as a bug.
2. **The span of «Только в выделении» is taken once**, when the switch goes on: the
   search itself moves the selection it would otherwise be read from.  Switched on
   with nothing selected it refuses and says so, instead of quietly meaning
   «everywhere».
3. **Re-running the search never moves the caret.**  The first version recomputed
   on every text change and moved the caret to the match it picked, so typing in
   the program threw the cursor into the next `факт`.

Two Qt traps hit on the way, both worth a line in `src/gui/README.md`:
`QAction.triggered` hands the slot a `checked` boolean, so `"find":
self.show_find` called `show_find(False)` and opened an empty field; and the
occurrence highlight had to be suppressed while the search is showing its own
matches, or the pale occurrence colour was painted over the warm one and the
*current* match stopped standing out.

The `search-find` icon was given a name in the table (`actions.FIND_ICON`) rather
than renamed, so the audit covers it; `edit-del` (drawn at the same time) became
the picture of «Удалить» in the «Правка» menu.

**2026-10-01 — which of the two magnifiers goes where.**  The user redrew
`edit-find-replace.png` (a magnifier over a red `R`) and then asked for the menu
entry «Поиск и замена…» to carry `search-find.png` instead — the plain lens, which
is what the command actually does: it *opens the search*.  So the action names
`FIND_ICON`, and the picture with the `R` moved to the control that really is
about replacement: the «Замена» triangle of the bar, which opens the second row.
It is named `actions.REPLACE_ICON`, so it stays in `ICON_NAMES` and the audit
still holds the file to a name (`test_icons.py`: 49 names, 42 drawn, 7 missing).
Without the move the bar would have shown the same lens twice — once at the left
of the field and once on the triangle.
