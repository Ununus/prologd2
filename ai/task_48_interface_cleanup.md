# task_48 — Interface cleanups: icons, the toolbar, the search menu, Escape

**Status:** done (2026-10-01; the by-hand look at the redrawn icons was confirmed by
the user on 2026-10-02 — «иконки в тёмной теме нормальные»)
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
- [x] `window.py`: one Escape handler, on the main window, in the order above.
  The graphics window closes on its own Escape as well (its own focus), and the
  find bar keeps its own — the field is where a user expects Escape to close the
  bar, and the window's handler never sees that key.
- [x] The graphics window opens itself on the **first drawing primitive of a run**:
  `MainWindow._on_drawn` shows it when `_graphics_shown` is clear, the switch
  `view/graphics_visible` is set by `show_graphics_window`, and the flag is reset
  by `run_program` — so closing the window during the run keeps it closed.
- [x] `test_icons.py` counts drop with the files (doc `gui.typ` §9.3's audit has
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
- [x] `test_window.py`: the toolbar has no «Сохранить все» and no «Найти
  выделенное» ✓ (`test_the_toolbar_reuses_the_actions`); the «Поиск» menu holds
  the three commands that are left ✓ (`test_search.py`); Escape closes the
  graphics window first, then the find bar, then the reference dock, then the
  shortcut sheet, and does nothing when none of them is open ✓
  (`test_escape_closes_the_picture_then_the_bar_then_the_docks`: the key is sent
  to the *editor* so that the real propagation runs, and the last press has to
  come back unaccepted).
- [x] `test_window.py`: a run that draws opens the graphics window once — the
  first `ТОЧКА` opens it, a closed window stays closed for the rest of the run
  (`?ТОЧКА(1, 1, 1), ЖДИ(200), ТОЧКА(6, 6, 6).` puts the close *between* two
  primitives, or the check would pass without the flag), a program that draws
  nothing opens no window, and the next run opens it again ✓
  (`test_a_run_that_draws_opens_the_picture_by_itself`).
- [~] `test_search.py`: the «Поиск» entries that remain (the two removed ones are
  gone from the table the test walks) ✓ — the walk is now
  `("find", "find_next", "find_prev")`.
- [x] By hand: the menu and the toolbar after the removals, and the redrawn
  icons in the dark theme — the user's own look on 2026-10-02: «иконки в тёмной
  теме нормальные», дорисовывать нечего.

## The second half (2026-10-01, the round after task_47)

* **Escape** is `MainWindow.keyPressEvent` plus `_escape_closes_something`, and the
  order is one `if` chain: graphics window → find bar → reference dock → cheat
  sheet, then the event is left alone.  The window that has the focus answers for
  itself: the find bar's field (where the key was pressed) and the graphics window
  (a top-level window with a keyboard focus of its own, handled by
  `GraphicsWindow.keyPressEvent` → `close()`, the same path as its ✕).  The
  completion popup keeps the key as well.  Written down in `doc/gui.typ` §4.1 (and
  pointed at from §5.1 and §6.4) and in `src/gui/README.md`.
* **The window opens itself** in `_on_drawn`, on the first primitive of a run.  The
  flag is `_graphics_shown`, cleared by `run_program` and set by
  `show_graphics_window(True)` — so it is «this run already brought the window up»,
  whoever did it, and hiding the window does not clear it.  That is what makes the
  two halves of the same request work: the picture appears without being asked, and
  a window closed during a 250-frame animation stays closed.  A run whose program
  draws nothing opens nothing.
* One thing to live with: a window closed by the user opens again on the *next*
  run.  That is what «once per run» says, and the settings still remember the
  window as open; if that turns out to annoy, the switch belongs in the settings
  dialog (`execution/…`) rather than in the flag.
* `show_graphics_window(True)` requests the snapshot, so the auto-opened window
  catches up with what the program drew before it existed — no new protocol work
  was needed for this half.

## Done in the first round (2026-10-01, with task_47)

The first half is in: five pictures left the tree (`help-about`,
`search-find-selected-next`, `search-find-selected-prev`, `view-toolbar`,
`view-line-numbers`), the toolbar lost «Сохранить все», the «Поиск» menu lost its
two «Найти выделенное» commands, and `assets.MISSING` is down to the four names
of the «Вид» switches plus `execution-restart` (drawn, unused).  Escape's order and
the self-opening graphics window came in the round after (see above).

## Acceptance

No entry of the window asks for a picture that does not exist; the toolbar and the
«Поиск» menu hold only what is used; Escape closes the four things in the order
the user asked for; and a program that draws shows its picture without being asked.
