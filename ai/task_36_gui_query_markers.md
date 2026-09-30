# task_36 — GUI: run a single query from the margin

**Status:** not started
**Depends on:** task_22 (the editor and its line-number margin), task_27 (the
output pane), task_28 (the run/stop state and the stepping seam), task_23 (the
keyword source is not needed here, but the protocol is)
**Milestone:** M13

## Goal

Make the questions in a program **clickable**.  A lesson carries 204 queries
(`?сумма(5, С).` and friends) and each of them prints its answer into one long
output pane, so a reader has to guess which answer belongs to which query — the
user's own words: «сейчас в листингах с большим количеством `?` сложно
отследить какой вывод относится к какому примеру».  Clicking a marker next to a
question should run *that question alone* and print *its* answer alone.

The other half of the same problem already exists in the lessons: thirteen
questions are deliberately **commented out** (a query that does not terminate,
a query that asks for input), written as `% ?длина(Х, 2) не завершится.` or
`%   ?ВЕРСИЯ.` in eight lesson files.  Those are exactly the lines a GUI should
still be able to run.  The marker therefore appears next to both spellings, and
**no lesson file has to change** — which is what keeps
`src/tests/test_lessons.cpp` green without a rewrite: it compares only the `%!`
lines, and a `%`-comment is ignored by the interpreter.

## What counts as a runnable statement

The rule has to survive the real files, where a commented query carries prose
after the goal: `% ?длина(Х, 2) не завершится.  Проверка длины стоит…`.  A marker
that offered `?длина(Х, 2) не завершится.` would be worse than no marker at all,
so a candidate is not cut at the first `.` blind — it is accepted only if it
*looks like a sentence*.  The check reuses machinery that is already Qt-free and
already wired into the editor:

* the line's first non-blank character is `?`, **or** `%` followed by blanks and
  then `?`;
* the candidate runs from that `?` up to a `.` — the shortest prefix that passes
  the checks below;
* round, square and curly brackets are balanced inside the candidate, and no `#`
  (an arithmetic expression) is left unclosed;
* every bare word of the candidate is a reserved name (the same `Keywords` table
  the highlighter colours with — which is why `?ВЕРСИЯ.` is accepted without
  parentheses), a variable, a quoted atom, or a name the document itself uses
  (the same scan `completion.collect_names` already performs);
* a line starting with `%!` is never a candidate — those are the expected answers
  the lesson test reads, and `!` is not `?`;
* the statement is passed on **verbatim** (the leading `?` and the trailing `.`
  included), because `prologd`'s protocol takes a whole statement
  (`protocol.query`, «выполняет одно предложение, обычно `?Goal.`»).

Consequences, all of them taken from the repository and all of them to be pinned
by tests:

| Line in a lesson | Statement offered |
|---|---|
| `?сумма(5, С).` | `?сумма(5, С).` |
| `%   ?ВЕРСИЯ.` | `?ВЕРСИЯ.` — a reserved name needs no parentheses |
| `% ?цена(хлеб, Ц1), БОЛЬШЕ(#Ц1 + 1#, 40). - см. раздел 7.` | `?цена(хлеб, Ц1), БОЛЬШЕ(#Ц1 + 1#, 40).` |
| `% ?длина(Х, 2) не завершится.  Проверка длины стоит…` | none — `не` and `завершится` are bare words that are neither reserved nor used in the document, so the line is prose |
| `% ?int("4").` | `?int("4").` |
| `%! С=15` | none |
| `% Деление: 5 / 2 — это 2.` | none — there is no leading `?` |

When a line is ambiguous, no marker is the right answer: a click that runs prose
would be worse than a click that is not there.  The absence is silent, and the
rule itself is written down in a comment so nobody "improves" it into a parser.

## Deliverables

- [ ] **Quiet load (prlib/protocol).**  A run loads the program *and runs its own
      `?` statements* — that is what `Запустить` must keep doing.  A single query
      must not: otherwise the output pane holds the whole lesson before the one
      answer asked for, and the feature defeats itself.  The seam exists:
      `ModuleLoader::setQueryRunner` is what decides whether a `Query` statement
      is executed (`src/prlib/src/module_loader.cpp:218-220`).  The protocol's
      `load` request gains an optional `"questions": false`, and the loader
      either keeps or drops the runner for that load.  Default stays `true`.
      Covered by the existing `cli_json_protocol` ctest.
- [ ] `src/gui/prologd_gui/queries.py`, Qt-free: `find_statements(text, keywords)`,
      returning `(line, text)` per statement, plus `statement_at(text, line)`.
      Pure text in, pure data out, no Qt import — the same shape as
      `completion.py` and `search.py`.  The keyword table is passed in, so the
      module has no dependency on the interpreter being up.
- [ ] Editor margin: the line-number area grows an icon column (~14 px, added to
      `line_number_area_width`), a marker is painted for every line that has a
      statement, and a click on it emits `queryRequested(str)`.
      `LineNumberArea` is a plain `QWidget` today (`editor.py:71-95`) — it needs
      `mousePressEvent`, and the hit test uses the same
      `blockBoundingGeometry(block) + contentOffset()` arithmetic that
      `paint_line_numbers` already uses.  A pointing-hand cursor over a marker,
      and no marker where `line_numbers` is switched off (the margin is zero
      wide then).
- [ ] Window: `queryRequested` runs the statement the way the query line does —
      `_run_query` (`window.py:934`) already prepends `?` when it is missing,
      starts the session if there is none and reports the run state.  The path
      for a marker is: load the current buffer (or its file, exactly as
      `Запустить` chooses) with `questions: false`, then run the statement.  If a
      run is in flight the marker stops it first (or is refused — decide with the
      user; a marker click during a runaway query is the case that matters).
      The statement is put into the query line first so the user sees what is
      about to run, which is the other half of the motivation.
- [ ] `%?` is visible as a question, not as a comment: `theme.py` gains a colour
      for a comment whose first non-blank character after `%` is `?` (orange, as
      the user asked), the rule lives next to the other token rules in
      `highlighter.py`, and `test_appearance.py` measures its contrast like every
      other palette entry.
- [ ] Docs: `doc/gui.typ` gains a short section (what the marker does, that
      `%?` is for a question the program itself must not run),
      `examples/lessons/README.md` gets one paragraph saying the same in the
      course's own words, and `src/gui/README.md` records the protocol addition.
- [ ] Tests: a new `src/gui/tests/test_queries.py` (the table above, plus a sweep
      over every lesson and example file that pins the *number* of statements per
      file — so a query added to a lesson shows up as a failing expectation rather
      than as a silently missing marker, and no `%!` line ever yields one), the
      margin width and hit-box in `test_editor.py`, the click-to-run path in
      `test_window.py` (drive it through `trigger()`/the signal, not synthetic
      keys — see part 13 of the session log), and `test_highlighter.py` for the
      new rule.
- [ ] Nothing in `examples/` changes, and the catch: the feature must work for a
      buffer with unsaved changes (the same rule as `Запустить`: load the text
      under the file's own name so `ИМПОРТ` still resolves).

## Acceptance criteria

1. With `examples/lessons/lesson_04.pld` open, clicking the marker at
   `?сумма(5, С).` prints `С=15` and *only* that — no trace of the other
   nineteen answers of the first four sections.
2. The same click on `%   ?ВЕРСИЯ.` in `appendix_debug.pld` runs it, although the
   file itself never executes that line.
3. Clicking a marker does not move the caret, change the selection or modify the
   document (the buffer stays "not modified").
4. The whole suite is green: `ctest` (193 tests, plus the new protocol case) and
   the headless GUI scripts, `test_lessons.cpp` among them, with no lesson file
   edited.

## Risks and notes

* A statement with side effects (`?ЗАПИСЬ_В("файл"), ВЫВОД("строка"), ПС.`) runs
  as written.  That is the point — but it is also why the statement is shown in
  the query line before it runs.
* A question that asks for input (`ВВОДСТР`) is the one case where the run waits:
  the input field and the modal fallback already handle it (task_25), so the
  marker needs no special case — the test should confirm the window does not
  deadlock.
* Multi-line queries (none exist in the lessons today) get no marker: the rule is
  one line, one statement.  Worth stating in the code comment so nobody
  "improves" it into a parser.
* Out of scope: changing the lesson format to `%?`-only (the file must stay
  runnable end to end — that is its main property), and running a *selection*.
