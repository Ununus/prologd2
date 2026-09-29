# task_33 — GUI: find and replace

**Status:** not started
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

- [ ] A find bar that appears above the editor (not a modal dialog: a modal box
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
- [ ] Keys: `Ctrl+F` opens the bar and focuses the field, `Esc` closes it and
      returns focus to the editor, `F3` and `Shift+F3` find forwards and
      backwards even with the bar closed, `Ctrl+F3` and `Ctrl+Shift+F3` search
      for the word under the cursor, `Enter`/`Shift+Enter` in the field are the
      same as `F3`/`Shift+F3`.  The five actions stop being `implemented=False`.
- [ ] Every match is highlighted in the editor while the bar is open (an extra
      selection in a palette colour, the way the error line already is), and the
      *current* match is told apart from the rest.  The highlight goes when the
      bar closes; the document itself is never modified by searching.
- [ ] **Заменить всё** is *one* undo step, the way comment/uncomment is: a single
      `beginEditBlock`/`endEditBlock` around the whole replacement.  Nothing is
      replaced inside the *found* text by accident: replacements never re-scan
      their own output.
- [ ] The search is plain text, not a regular expression: the programs are in
      Russian and often contain `#…#`, `?` and parentheses, where regex syntax
      would surprise more than help.  A `QRegularExpression` would be a later
      task with its own switch.
- [ ] Case-insensitive search compares with `str.casefold()` (Cyrillic included),
      and a search for a word *does* cross the ends of the document — wrapping is
      reported in the bar.
- [ ] The bar follows the **active pane**: the split editor has two panes over one
      document set, so «Найти» acts on the pane that was used last, and the
      matches are highlighted in every view of that document (they share one
      text).
- [ ] Tests: `src/gui/tests/test_search.py` — finding the first, the next and the
      previous match, wrapping in both directions, a search that matches nothing,
      case sensitivity, whole word, «заменить всё» as one `Ctrl+Z`, the bar
      closing on `Esc` with focus back in the editor, and the five menu entries
      becoming enabled.
- [ ] The `edit-find-replace` icon is drawn (or the existing `search-find.png`,
      which is already in `assets/` and unused, is given the name the action
      asks for) and the name leaves `assets.MISSING`; `test_icons.py` keeps the
      two lists in step.

## Design notes

* The `search-find*` icons of the reference project are already in
  `src/gui/assets` (`search-find`, `search-find-next`, `search-find-prev`,
  `search-find-selected-next`, `search-find-selected-prev`) and
  `actions.py` already names them, so only `edit-find-replace` is missing.
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
