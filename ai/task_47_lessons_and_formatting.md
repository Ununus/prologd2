# task_47 — Lessons, the formatter's hard mode, and the mode control

**Status:** done (2026-10-01)
**Depends on:** task_30 (the formatter and its three modes), task_31 (the insert
table on the toolbar), task_35 (the lessons themselves)
**Milestone:** M17

## Goal

Three things around how a program *looks*, found while rewriting lesson 12: the
lesson files are laid out in three different styles, the hard mode hides the first
goal of a body on the head's line, and switching the format mode means walking
into a menu or into the settings dialog.

## What was found (2026-10-01)

* The lessons disagree about indentation.  `lesson_01`, `lesson_02`, `lesson_03`,
  `lesson_10`, `lesson_11` and `appendix_debug` have no continuation indent at
  all, `lesson_04`…`lesson_09` use a mix (spaces, 1 to 36 of them, and one line of
  `lesson_06` is 6 spaces short of its neighbours), `lesson_12` uses tabs *and*
  five space-indented lines.  `prologd --format` is the standard (soft mode, one
  tab per step): `lesson_01` comes out byte-identical, `lesson_06` and `lesson_12`
  differ on ~130 lines each.
* **The hard mode leaves the first goal on the head's line**:
  `правило(а,б):-первая_цель,` / `&#9;вторая_цель.` — the goal that a reader is
  most likely to look for is the one glued to the head, which is why lesson 12's
  long clauses are hard to scan even after formatting.
* The **format mode** is a submenu of «Правка» (`#format-mode`), added in task_30
  when it moved off the toolbar.  A mode is something the user toggles *while
  looking at the code*, and two menu levels for it is one too many.
* `lesson_12` now runs its animation on a click (`%?ТИХО, рисовать_рамку(_, _),
  кадры(250, 320, 240, 10, 10).`): 250 frames of 40 ms is ten seconds, far too
  long for `ctest` to run on every build.

## Deliverables

- [x] **Every lesson file formatted with `--format`** (soft, width 80, one tab),
  so the corpus has one style.  The `%!` expectation lines must stay in the same
  *order* — `test_lessons.cpp` compares the program's output with them in order,
  and the formatter never touches comment text.  21 of the 25 shipped programs
  changed; `examples/lessons/_old` is left alone on purpose (it is the port's
  reference, not its style).  Formatting is now *checked*, not remembered: the
  new case «every shipped program is already in the standard shape» in
  `test_formatter.cpp` fails and names the file that drifted.
- [x] **The hard mode breaks after `:-` as well**: the head stands alone on its
  line and every goal of the body gets its own, so
  `правило(а,б):-` / `&#9;первая_цель,` / `&#9;вторая_цель.`.  A **directive**
  (`:- ИМПОРТ(…)`) and a **query** (`?цель(Х).`) keep their single space: there is
  no head to stand alone, and `:-` on a line of its own is noise.  The rule is one
  sentence in the manual and in `doc/gui.typ` («жёсткое» = голова, потом цель на
  строку), and `test_formatter.cpp` pins both shapes.
- [x] **The mode control returns to the toolbar**, right after «Форматировать»,
  as it was before task_30, with the icon `edit-format-set` (already drawn,
  `edit-format-set.png`, and currently asked for by nobody).  It leaves the
  «Правка» submenu: a control that belongs to one action is looked for next to
  that action.  It carries the mode *and* the «только выделенное» switch it
  already carries.
- [x] `lesson_12`: the animation stays a click away (the `%?` line), and the
  lesson says in prose why (`ctest` may not wait ten seconds).  A two-frame
  animation (`?кадры(2, 320, 240, 10, 10).`, 80 ms) runs in its place, so the
  «анимация окончена» promise is still taken from a working interpreter.

## What the reformat found

Three things, all of them now pinned by tests:

* **A promise may not end in a space.**  The formatter drops trailing whitespace
  from every line, `%!` lines included, and `lesson_07` promised
  `%! Загадано число. ` — a space the program really printed
  (`ВЫВОД("Загадано число. ")`).  The fix belongs in the program, not in the
  promise: the message lost its trailing space.  `test_lessons.cpp` compares the
  lines byte for byte, so it caught it at once; `doc/lessons.typ` states the rule.
* **A query is a question and stays on one line.**  `lesson_07` and `lesson_12`
  turned out to hold queries longer than the width, and the soft mode broke them —
  which quietly disarmed the margin marker: the rule that offers a question is
  line-local (task_36), so a query split in two is a question nobody can click.
  The count pinned in `src/gui/tests/test_queries.py` is what noticed (19 → 18 for
  `lesson_07`).  `emitFirstBodyGap`/`emitGoalGap` now leave a query and a
  directive unbroken in **every** mode; a comment or a blank line the author left
  still breaks them.  `test_formatter.cpp` pins it in both modes, at width 20 and
  at width 80.
* **Two promises of `lesson_12` had gone stale** when the lesson was rewritten by
  hand: the frame list of `рамка/1` (which now starts at `20,20`) and the garden's
  fixture list (`сад(3, 5, 60, 100, 20, 20, …)`), and the animation line was
  commented out so nothing printed at all.  All three are refreshed from a real
  run — that is what `test_lessons.cpp` is for.

## Design notes

* The hard mode's rule is about the **head**, not about the goal count: a clause
  with one goal is laid out the same way, because a mode that switches shape
  depending on the body length is a mode nobody can predict.  `:-` and `?` are
  not clauses and keep their line.
* Formatting the lessons is a **one-off** act, but it is worth a check: the
  lessons are the widest corpus of real programs in the repository, and
  `test_lessons.cpp` already runs every one of them.  If a formatting change ever
  moved a `%!` line past the code that produces it, that test would fail — which
  is the reason to do this with the suite green rather than by hand.
* The toolbar control is the *same* widget the submenu had
  (`window.py`'s `_build_format_control`): it is moved, not rebuilt, so the mode
  and the switch cannot exist twice.

## Tests

- [x] `test_formatter.cpp`: the hard shape of a rule (head alone, one goal per
      line), of a fact (unchanged), of a directive and of a query (glued), and the
      soft mode still converting a hard layout back; plus «a query and a directive
      keep their one line» (width 20 and 80, soft and hard) and «every shipped
      program is already in the standard shape».
- [x] `test_formatter.py` (the window's half): the hard layout that the window
      sends and gets back.
- [x] `test_lessons.cpp` stays green after the reformat — that is the check that
      the corpus still prints exactly what it promises.
- [x] `test_window.py`: the control is on the toolbar (not in «Правка»), it
      carries the mode and the switch, and switching it reformats the buffer
      (`test_the_mode_control_stands_beside_the_command_it_changes`).
- [x] `test_queries.py`: the pinned question counts, refreshed for `lesson_12`
      (10 → 11: the two-frame animation is a new question) and back to 19 for
      `lesson_07`, whose long query the formatter now leaves alone.

## Acceptance

The lessons all look the same, the hard mode puts every goal on its own line, and
the format mode is one click away on the toolbar.
