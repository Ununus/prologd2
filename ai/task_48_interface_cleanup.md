# task_48 — Interface cleanups: icons, the toolbar, the search menu, Escape

**Status:** partly done (the icons, the toolbar and the search menu are in;
Escape's order and the self-opening graphics window are still to come)
**Depends on:** task_26 (the action table), task_29 (the settings dialog),
task_33 (the find bar), task_37 (the reference dock), task_45 (the graphics window)
**Milestone:** M17

## Goal

A round of small things the user asked for after living with the window: fewer
icons to draw, fewer commands nobody uses, one Escape key that closes what is in
the way, and a graphics window that opens itself when a program first draws.

## What was asked for (2026-10-01)

* **Two fewer required icons**: `view-toolbar` and `view-line-numbers`.  Both are
  *switches* of the «Вид» menu whose pictures were never drawn, and a checkable
  menu entry that says what it does in words does not need a picture.  They leave
  `MISSING` too — a drawing list that keeps a picture nobody needs is a to-do that
  lies.
* **`help-about.png` and `prologd2.png` are the same picture.**  One stays: the
  application icon `prologd2` (window icon *and* «О программе»), and `help-about`
  leaves the file tree and the action.
* **`file-save-all` leaves the toolbar.**  «Сохранить все» stays in «Файл», where
  a command that acts on every tab belongs; the toolbar keeps the three file
  buttons that act on the one in front of the user.
* **«Найти выделенное» and «Найти выделенное назад» leave the «Поиск» menu**
  (`Ctrl+F3`/`Ctrl+Shift+F3`), together with their two icons
  (`search-find-selected-next.png`, `search-find-selected-prev.png`).  The find
  bar already takes its question from the selection, so the two commands are a
  second way to do what happens anyway.
* **Escape closes things in one order**: the graphics window, then the find bar,
  then the «Справка по предикату» dock, then the «Шпаргалка по вставкам».  Today
  Escape closes only whatever owns the focus.
* **The graphics window opens itself** the first time a program draws — once per
  run, so a user who closed it during a long animation is not fought by the next
  hundred `ТОЧКА`.

## Deliverables

- [x] `actions.py`: the `toolbar` and `line_numbers` entries lose their icons (and
  `assets.MISSING` loses the two names); `about` loses `help-about`, and the file
  goes; `TOOLBAR` loses `save_all`; the `find_selected`/`find_selected_prev`
  actions, their `MENUS` entry, their two pictures and their two shortcuts go.
      `window._slot_for` loses the two entries, `MainWindow.find_selected` goes,
      and `search.py` keeps whatever the bar still uses.  Done in the same round
      as task_47; `find_selected` took its `start` argument with it, and
      `find_step(backwards=False)` now walks from the caret for both keys that
      are left.
- [ ] `window.py`: one Escape handler, on the main window, in the order above.
  The graphics window closes on its own Escape as well (its own focus), and the
  find bar keeps its own — the field is where a user expects Escape to close the
  bar, and the window's handler never sees that key.
- [ ] The graphics window opens itself on the **first drawing primitive of a run**:
  the window's own canvas decides («первый `graphics`-event после начала прогона»),
  the switch `view/graphics_visible` is set, and the state is reset by
  `run_program` — so closing the window during the run keeps it closed.
- [ ] `test_icons.py` counts drop with the files (doc `gui.typ` §9.3's audit has
  the numbers), and the missing-picture list stays honest.

## Design notes

* **Who opens the graphics window?**  The *window* does, in `_on_drawn`, and only
  when the run has not opened it before: the interpreter knows nothing about
  windows (ADR-020), and the canvas exists only if something asked for it.  So the
  first primitive of a run *creates* it — which is also the cheapest moment: the
  program has just started drawing, the picture is empty, and no snapshot is
  needed.
* Closing the window during the run sets the same flag the user's click does, so
  the next primitive does not reopen it.  That is the whole point of «once per
  run»: an animation with 250 frames would otherwise reopen the window 250 times.
* Escape is handled by **propagation** (`MainWindow.keyPressEvent`), not by a
  `QShortcut`: a shortcut is processed before the focused widget, and it would
  take Escape away from the completion popup (which closes on Escape) and from
  the find fields.  With propagation each widget gets the first chance, and the
  window's order applies to what is left — which is exactly the list above, minus
  the two places the focus is already the right answer for.
* The two removed search commands are the only ones that *need* a selection, and
  the find bar starts from the selection by itself; the icons are the reason the
  audit was noisy about them.

## Tests

- [x] `test_icons.py`: the count and the two lists; `MISSING` no longer names
  `view-toolbar`/`view-line-numbers`, and `help-about` is gone from the tree.
  The audit now reads 45 names, 41 drawn and 4 documented missing (`view-theme`
  among them), and `edit-format-set` — the formatter's mode, which task_47 put on
  the toolbar — is drawn and used at last.
- [~] `test_window.py`: the toolbar has no «Сохранить все» and no «Найти
  выделенное» ✓ (`test_the_toolbar_reuses_the_actions`); the «Поиск» menu holds
  the three commands that are left ✓ (`test_search.py`); Escape closes the
  graphics window first, then the find bar, then the reference dock, then the
  shortcut sheet, and does nothing when none of them is open — **to do**.
- [ ] `test_window.py`: a run that draws opens the graphics window once — the
  first `ТОЧКА` opens it, a closed window stays closed for the rest of the run,
  and the next run opens it again.
- [~] `test_search.py`: the «Поиск» entries that remain (the two removed ones are
  gone from the table the test walks) ✓ — the walk is now
  `("find", "find_next", "find_prev")`.
- [ ] By hand: the menu and the toolbar after the removals, and the two redrawn
  icons in the dark theme.

## Done in this round (2026-10-01, with task_47)

The first half is in: five pictures left the tree (`help-about`,
`search-find-selected-next`, `search-find-selected-prev`, `view-toolbar`,
`view-line-numbers`), the toolbar lost «Сохранить все», the «Поиск» menu lost its
two «Найти выделенное» commands, and `assets.MISSING` is down to the four names
of the «Вид» switches plus `execution-restart` (drawn, unused).  The graphics
window does **not** open itself yet, and Escape still closes only what owns the
focus: both are the next round.

## Acceptance

No entry of the window asks for a picture that does not exist; the toolbar and the
«Поиск» menu hold only what is used; Escape closes the four things in the order
the user asked for; and a program that draws shows its picture without being asked.
