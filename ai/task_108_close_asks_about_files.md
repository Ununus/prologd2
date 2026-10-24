# task_108 — the window asks about files, not about scratch pads

**Status:** done (2026-10-24) — ADR-046, part 175
**Depends on:** task_29/task_49 (the remembered session), task_67 (the names marker)
**Milestone:** 2.6.0

## Goal

The owner's question: on closing the window, should an unnamed «Без имени» tab be
offered for saving at all?  Its text already rides in the session and comes back on
the next start, so the question was mostly ceremony — and «Сохранить» there meant a
file dialog for a program that has no name yet.  The alternative (a Notepad++-style
"save everything, restore everything") was considered and rejected.

## Why the question was wrong for an unnamed tab

`documents.TabRecord` is asymmetric on purpose: a **file** tab is remembered by its
path, so the next run reads the file from disk and an edit that was not written is
gone — the question is the only thing between that edit and the rubbish bin.  An
**untitled** tab is remembered by its *text* plus the «unsaved» flag, so the text
cannot be lost by closing the window at all.  The question there only added a file
dialog, and its third answer («Не сохранять») was the sole way to keep a scratch tab
out of the session.

The Notepad++ route was rejected for three reasons: it writes the user's files
without a question at exit, it would need the text of *file* buffers in the session
(today only untitled text is stored), and it makes «Не сохранять» untrue.

## Decision

`MainWindow._closing_needs_a_question` decides, and `_confirm_close` asks only when
it says yes:

- a buffer **with a file** always earns the question;
- an **unnamed** one is passed to the session without a word — except when the
  session cannot keep it: the «Восстанавливать вкладки при старте» setting is off
  (no store at all), or the text is over `SESSION_TEXT_BUDGET`;
- the rule holds only while the *window* closes (`self._closing`).  `Ctrl+W`,
  «Закрыть вкладку» and «Закрыть все вкладки» have no session behind them and ask
  about everything, unnamed tabs included.

The budget moved from the whole session to **one buffer** (task_108): it is now the
size above which the close has to ask, so one big scratch tab cannot cost the small
one standing next to it.  `session_records` measures each untitled text on its own.

## The second half: the promise has to be sayable

Closing silently keeps an unnamed tab by *writing* it into the settings file.  A
write that failed — a full disk, a folder that went read-only — would turn that
silence into a lie.  `Settings.write_failed` reads `QSettings.status()` (every
setter syncs), and `MainWindow._warn_if_not_remembered` says, before the window
goes, that the session could not be stored and the unnamed tabs will not come back.
The close still happens: a warning, not a veto — refusing to close would be the
worse trap.

## What the owner's script question turned out to mean

«Сконвертировать картинку» and «Сконвертировать исходник» open an **unnamed** tab
with the generated program (`convert_image`, `_show_converted`).  Under this rule
such a tab is not asked about at close and comes back from the session with its
text — which is the behaviour the owner described as wanted.  Nothing in the
converter needed to change; a generated program is a scratch tab until the user
gives it a name, and `save_buffer` offers the dialog when they ask for it.

## Checks

- `test_documents.py`: the budget is per buffer — two 80-character tabs fit a budget
  of 100, a 120-character one is dropped and counted.
- `test_window.py`: «the window close asks only about files» — an unnamed tab is
  asked about nothing and lands in the session starred, a file tab is asked about,
  the session switched off brings the question back, and so does an over-budget text.
- `test_window.py`: «an unnamed tab left unsaved is forgotten» now closes the *tab*
  (`close_buffer`) with «Не сохранять» and checks the session leaves it out.

## What was deliberately not done

- no auto-save of unnamed tabs to a file at close: the user decides the name, and a
  path chosen by the program is exactly what «Без имени» avoids;
- no change to the 256 KB limit itself, only to how it is measured.
