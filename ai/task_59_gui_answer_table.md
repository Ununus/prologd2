# task_59 — the window: an answer table for a single query

**Status:** done (2026-10-04) — option (C): the switch "Выполнение → Формировать
таблицу" (`execution/answer_table`, **on by default now** — the default was flipped on
2026-10-03, see `ai/status.md` part 73; in this task it was off), the "Таблица" tab after
"Ввод", the Qt-free module `answers.py` with `tests/test_answers.py`, and nine cases in
`test_window.py`.  A word answer `ДА`/`НЕТ` occupies one cell; the protocol is untouched
(version 11).
**Depends on:** task_50 (the panel tabs and the counts in their titles), task_36 (question
markers in the margin — a second way into one goal), task_46/58 (the run switches in
"Выполнение" — the third one was modelled on them), task_29 (the settings table and the
dialog), task_48 (the action table: `actions.py` is the only place a menu item lives),
task_54 (an answer is a piece of the input stream).
**Milestone:** post-M10

## Goal, and why the answer is enough for it

A single query — a goal in the query line or a question marker in the margin — can show
its answer not only as text but also as a **table**: variables become columns, solutions
become rows.  The text output stays exactly as it is; the table is an extra mode, switched
by "Выполнение → Формировать таблицу" (and by the same setting in the dialog).

The user's example, which is what this is for:

```prolog
студент(вова, корчагин).
студент(данил, ахмеров).
цена(молоток, 40).
?студент(X, Y).
?цена(X, Y).
```

With `F5` the answers of the two questions lie in "Вывод" as one ribbon:

```
X=вова
Y=корчагин
X=данил
Y=ахмеров
X=молоток
Y=40
```

and one cannot separate one question from the other by the text: there is no separator and
no question name in the answer.  That is why `F5` is **not** tabulated (§5), while a single
query is: "Вывод" answers "what did the interpreter say", the table answers "which
solutions, with which values".

The answer of one goal is shaped so that the table comes out *exactly*, with no guessing
(`src/prlib/src/engine.cpp::runQuery`):

* all query variables are printed **in the order they appear in the query** —
  `for (const auto& [name, var] : query.variables)` writes `name=value` and `ПС`;
* every solution gets such a block of its own, and the solver keeps enumerating
  (`return true`), so the solutions follow one another, block by block;
* a goal **without variables** prints `ДА` once, and when nothing is found it prints
  `НЕТ`;
* so inside one query `ДА`/`НЕТ` and `Имя=значение` blocks **never mix**: either a word or
  lines.

A variable name cannot repeat within a block, and that gives the rule for a solution
boundary: **a new block starts where a name appears a second time**.  No other information
is needed from the interpreter, and the protocol is **not** touched in this round: option
B (a `bindings` field in the `result` event) is needed only by a table for a whole run,
which is separate work (§5).

## §1. The switch and the setting

**Where.**  `settings.py` (the settings table and the property), `actions.py` (an entry in
`ACTIONS` and `MENUS`), `window.py` (the handler and `_sync_actions`).

**What to do.**  `settings.py`: the key `ANSWER_TABLE = "execution/answer_table"`, the row
`Setting(ANSWER_TABLE, "Формировать таблицу", "Выполнение", "bool", False, hint=…)` and
the `answer_table` property beside `run_questions`/`print_questions`
(`_flag(ANSWER_TABLE, False)`).  The row stands **before** "Выполнять вопросы при
запуске", so that the dialog and the menu read the same.  The hint: "The answer of a
single query is also shown as a table: variables are columns, solutions are rows.  The
text in «Вывод» does not change".  `actions.py`:
`Action("answer_table", "Формировать таблицу", None, checkable=True)` — **without an
icon**, like the two neighbouring switches — placed in `MENUS` under Run **above**
`run_questions`, after the separator that follows `stop`.  `window.py`:
`_toggle_answer_table(checked)` (writes the setting, modelled on `_toggle_run_questions`),
the `_slot_for` entry, and the `setChecked` line in `_sync_actions`.

**Decision.**  The setting was **off by default** in this task: the table changes both the
content of the tab and where the window looks after an answer, while the text ribbon is the
main way to read an answer (the default was flipped on 2026-10-03, part 73).  The tick
follows the setting, not the other way round: the setting lives in a file and is visible in
the dialog, and the menu item is a second way in.

## §2. Parsing the answer — the new module `answers.py`

**Where.**  `src/gui/prologd_gui/answers.py` — a new Qt-free module (like `tokens.py`,
`queries.py`, `panels.LineBuffer`): parsing rules deserve to be tested without a screen.
The test is `src/gui/tests/test_answers.py`.

**What to do.**  `parse(text: str) -> Answer`, where

```python
@dataclass(frozen=True)
class Answer:
    columns: tuple[str, ...] = ()      # variable names, in order of appearance
    rows: tuple[tuple[str, ...], ...] = ()
    verdict: str = ""                  # "ДА"/"НЕТ", only when there are no rows
    ignored: tuple[str, ...] = ()      # lines that do not look like an answer
    def is_empty(self) -> bool: ...
```

The rules, all of them from the shape of the answer above:

1. The text is split into lines; a trailing `\r` is dropped (a piece of the protocol may
   arrive with CRLF), and nothing else inside a value is touched.
2. An empty line (spaces/tabs) is not an answer line: it goes neither into the rows nor
   into `ignored`.
3. **A binding line** is `Имя=значение`, the name being everything before the **first**
   `=`: its first character is an upper-case letter (`tokens.is_upper_letter`, that is
   `X`, `С`, `Ё`, `_`) and the rest are `tokens.is_name_character`; the value is
   everything after the first `=` verbatim.  An empty value is allowed (`X=` is how an
   empty string is printed).  Reusing `tokens` is the point: the rules for a variable are
   already written there and are the same as for the highlighter and the completion.
4. **A word** is a line that equals `ДА` or `НЕТ` after whitespace is stripped.  It is
   remembered in `verdict` **only if there were no bindings in the whole text**: a `ДА`
   printed by the program inside a block of solutions cannot hijack the table.
5. **A solution boundary** is a binding whose name has already occurred in the current
   row — it starts a new one.  The columns are the names in order of first appearance
   across all rows.
6. A row shorter than the table (possible only when the program printed exactly `Имя=…`)
   gets empty cells for the missing columns — the table does not fall over.
7. Everything else goes into `ignored` verbatim (it is what the program printed itself;
   the window shows only the table, `ignored` lives for the tests).

**Doctests** in the module header, short, modelled on `queries.py`:

```
>>> parse("X=вова\nY=корчагин\nX=данил\nY=ахмеров\n").rows
(('вова', 'корчагин'), ('данил', 'ахмеров'))
>>> parse("X=1\nX=2\nX=3\n").columns
('X',)
>>> parse("ДА\n").verdict
'ДА'
```

**The word answer — decided.**  `ДА`/`НЕТ` is shown as **one cell** (a single column
"Ответ", a single row holding the word): that is exactly the shape of the answer — for a
query without variables the answer *is* the word, not a set of values — and the tab then
never stays empty where the interpreter answered.  The fork is closed by the shape of the
answer: a word and bindings never occur in one query, so the table is either "word" or
"grid" and there can be no contradiction.  If the user prefers another look (say, the word
printed as a line in "Вывод" with the table untouched), one branch of `TablePane.set_answer`
changes.

## §3. The "Таблица" tab

**Where.**  `panels.py` (the constant and the pane), `window.py` (`_build_*`, `_tab_index`,
`_refresh_panel_tabs`, `_apply_output_font`, `_reset_panels`, `clear_output`).

**What to do.**  `panels.py`: `TAB_TABLE = "table"`, and a `TablePane` class — a
`QTableWidget` subclass with the three things the other panes have: `font_size`/
`set_font_size` (with the same bounds as `ZoomablePlainTextEdit`), the `zoomChanged`
signal and `wheelEvent` with `Ctrl` (the wheel changes the size as it does over "Вывод"),
plus `set_answer(answer)` and `copy_selection()`.  `window.py`:
`self._table = panels.TablePane()` and `addTab(self._table, "Таблица")` — **after** "Ввод"
(the tab order is Проблемы, Вывод, Система, Ввод, Таблица); `panels.TAB_TABLE:
self._table` in `_tab_index`; the title `Таблица:N` where `N` is the number of solutions
(`Таблица:0` for an empty table); `self._table` in the `panes` tuple of
`_apply_output_font` and `zoomChanged.connect(self._on_output_zoom)` beside the other four.

**Decisions.**

* **A grid, not a text table made of pipes.**  The user asked for a table; `QTableWidget`
  gives columns named after the variables and even rows of solutions, and it cannot be
  mistaken for the program's output.
* **The columns follow the interpreter's answer**, not the alphabet: that way the table
  reads together with its own text in "Вывод", which has the same order.
* **The number of columns and rows comes from the answer**; the cells are read-only
  (`ItemIsEnabled | ItemIsSelectable`, no editing) and the row header is hidden: the number
  of a solution is already visible by its position, and its count stands in the tab title.
* **The colours come from the window palette** (`appearance.apply_theme` sets the palette
  for the whole application), so the dark theme reaches the table as it reaches the other
  panes: nothing new is painted for it in `theme.py` or `panels.py`.
* **`Ctrl+C` over the table copies the selected cells** (`TablePane.copy_selection`:
  columns separated by a tab, rows by `ПС` — so the table pastes into a spreadsheet).  This
  is not decoration but a necessary detail: `_copy` copies "from wherever the user is
  looking" and knows only text panes (`ZoomablePlainTextEdit`, `QLineEdit`); without a case
  for the table the command would go to the editor and copy a selection nobody is looking
  at.

## §4. Filling the table and switching tabs

**Where.**  `window.py`: `_run_query`, `_on_query_requested`, `_append_output`,
`_on_result`, `_on_failed`, `run_program`, `_reset_panels`, `clear_output`.

**What to do.**  `self._answer_text: list[str] | None = None` means "an answer to a single
query is being collected".  It is set to `[]` wherever a query goes to the interpreter: in
`_run_query` (the query line) and in `_on_query_requested` (the margin marker), **before**
`session.run_query`.  `_append_output` puts a piece into the list **verbatim** at the top,
if an answer is being collected and `kind == panels.OUTPUT`; a piece may end in the middle
of a line, so pieces are collected and `answers.parse` cuts them (it is the one that has to
cut).  Neither `NOTE` (the "knowledge base loaded" line), nor `ERROR`/`WARNING`, nor the
`>` echo get into the answer.  `_on_result`: if an answer was being collected — `parse` the
collected text, `set_answer` into the pane, `_refresh_panel_tabs()`,
`self._answer_text = None`, and the "Таблица" tab becomes current **if** the table is not
empty and **if this run has no diagnostics** (`_error_count or _warning_count` — then
"Проблемы" already took the tab and the table does not push it aside; the table itself is
filled either way).  Collection also stops in `_on_failed`, `_stop_now`, `_on_ended` and in
`run_program` (a new run): otherwise the output of the next run would land in somebody
else's table.  `_reset_panels` and `clear_output` clear the table together with the panes:
the table is derived from the output of the last run, and "Clear output" clears what the
run produced — the text and the table.

**Decisions.**

* **A single query only.**  Neither `F5`, nor a step, nor the trace build the table: in a
  whole run the answers of different questions are indistinguishable in the text (§5).
* **One table at a time** — the table of the last single query; the previous one is not
  accumulated.  The history of solutions is "Вывод", which goes nowhere.
* **The tab title counts solutions**, as the neighbours count lines: `Таблица:3` is "three
  solutions", which is what one looks for by eye (and for a word answer it is `Таблица:1`,
  not `Таблица:0` — the tab never looks empty where the interpreter answered).
* **Diagnostics beat the table**: a line about an error is what the user looks for after a
  failed run, so it takes the tab (the rule of task_50) and the table waits for a click.
  That is a deliberate choice, and it is reversible with one line.

## §5. What the table does not do (the boundaries)

* **A whole run (`F5`) is not tabulated.**  The answers of several questions go into the
  text as one ribbon without separators, and one question's block cannot be told from
  another: that needs the protocol change — `bindings` in the `result` event (option **B**:
  four places in `protocol.cpp`/`protocol.py`, `protocol_session.cmake`, the README, the
  tests).  That is separate work, and `doc/gui.typ` §10 records it as "not done yet",
  together with the reason.
* **Only `Имя=значение` lines are parsed.**  A program that prints inside the answer (a
  `ВЫВОД` in a rule) does not reach the table — that is the agreed rule.  The other side of
  it: a program line that looks exactly like a binding (`ВЫВОД("Y=2")` — only through a
  variable) will be taken for a solution.  The price is small, and the text in "Вывод"
  stays exact anyway.
* **Values are not parsed**: a value is the string as the interpreter printed it (`абвг`,
  `-а`, `Ёё[1,2]_1`, `_1`).  No numbers, no sorting, no sums.
* **The output of the load itself is not part of the answer**, but it is not cut off
  either: at a marker the program is loaded (`questions=False`), and what a directive
  printed (`:- ВЫВОД(…)`) may arrive after the query has gone.  It passes through the same
  shape rule as any foreign line: only `Имя=значение` counts as a binding, everything else
  is `ignored`.  The "база знаний загружена" line has another kind (`NOTE`) and does not
  enter the answer at all.
* **The table is not saved**, neither by "Сохранить вывод…" nor by a session: it is a view
  of an answer, not data (it has nothing to do in the settings file).

## §6. Documents and records

* `doc/gui.typ`: a new subsection **§6.5 "Таблица ответа"** — what it is, the switch, that
  the table appears only for a single query, that `Имя=значение` lines are what is parsed,
  that `ДА`/`НЕТ` is one cell, that "Вывод" stays the full text, and the user's example
  (two questions, of which only a separate run grows a table).  §8 — the "Выполнение" row
  of the settings table gains "формировать таблицу" plus a paragraph saying it is the third
  way in beside the two question switches.  §9.1 — a new menu row above the two switches.
  §10 — the item about a table for a whole run and `bindings` (what is left).
* `src/gui/README.md`: the list of panel tabs (there are five), the switch in the settings
  list and in the "Выполнение" section, a paragraph about the table and its boundaries, and
  a line about `Ctrl+C` over the table in the keys section.
* `ai/status.md`: the task row in the table and the round's journal entry; that is where
  yesterday's open question ("an answer table" — option C chosen) is closed, and the user's
  second question is answered: "the problem with files that have many questions" is not a
  defect but exactly the impossibility of separating the answers from one another.
* `commitmsg*.txt` — by the habit of the round, in a temporary file, deleted after the
  commit.

## Checks

`src/gui/tests/test_answers.py` (new, Qt-free, like `test_queries.py`: a table of cases and
a `main()`):

* the bindings of one solution are one row, columns in the order of the answer;
* a repeated name starts a new solution (`X=1\nX=2\nX=3` → three rows, one column);
* two questions in one text (`X=вова\nY=корчагин\nX=данил\nY=ахмеров`) give **two** rows,
  not four — which is the point of the table;
* `ДА` and `НЕТ` become `verdict` with empty rows; a `ДА` printed by the program beside
  bindings does not hijack a solution;
* program lines (`ВЫВОД`) go to `ignored` without breaking the table;
* an empty value (`X=`), a trailing `\r`, empty lines, a one-letter name, a Cyrillic name
  (`С=15`), and a value containing `=` (the first one wins).

`src/gui/tests/test_window.py`:

* `test_the_panel_has_five_tabs_with_counts` — the earlier case about four tabs gains
  "Таблица:0" (and it is the first thing to fail if the tab was forgotten);
* `test_a_marker_builds_the_answer_table` — lesson_04, `?сумма(5, С).`: one column "С", one
  row "15", the "Таблица" tab in front, `Таблица:1`, and "Вывод" still says `С=15`;
* `test_the_table_separates_two_solutions` — the user's example: two facts and
  `?студент(X, Y).` → columns "X", "Y" and two rows;
* `test_the_table_shows_a_word_for_a_ground_query` — `ДА` and `НЕТ` in one cell;
* `test_the_table_stays_off_until_it_is_asked_for` — with the switch off the table is
  empty, the tab does not leave "Вывод", and the tick and the setting agree;
* `test_the_answer_table_switch_is_in_the_menu_and_in_the_settings` — modelled on the two
  neighbours: a click in the menu writes the setting, editing the setting comes back into
  the tick, and in `MENUS` the entry stands above `run_questions`;
* `test_a_diagnostic_keeps_the_panel_on_the_problems` — a run with an error: the table is
  filled, the tab stayed on "Проблемы";
* `test_a_new_run_empties_the_table` — after a table, `F5` (and `Ctrl+L`) clear it;
* `test_the_table_follows_the_output_font` — the table's size equals the output's after
  zooming, and the wheel with `Ctrl` over the table writes `output/font_size` (a sequel to
  `test_two_font_sizes_and_one_wheel`);
* `test_copy_over_the_table_takes_the_cells` — focus on the table, `Ctrl+C`, and the
  clipboard holds the selected cells separated by tabs while the editor's selection is
  untouched.

Then the usual round: every `src/gui/tests/test_*.py` suite, `protocol_smoke.py`, `ctest`
and the docs build, and the table itself by eye (light and dark theme, a narrow panel, a
long value in a cell).

## Decisions taken while composing this

1. **Option C** (a table for a single query) instead of A (a heuristic over the whole
   output) and B (structural `bindings` in the protocol) — as the user chose: A confuses
   the program's output with the answers, and B is needed only by a table for a whole run.
2. **One setting, two ways in** — a menu item and a dialog row (the pattern of the two
   switches of task_58).
3. **Off by default** — the text ribbon stays the main way of reading (flipped later,
   part 73).
4. **A single parser** — the new Qt-free `answers.py`, not code in the window: the rules
   are tested without a screen, and the window only puts the text into the pane.
5. **`ДА`/`НЕТ` is a 1×1 table** (§2).
6. **The protocol is untouched**: the version stays 11, `protocol.cpp`/`protocol.py` do not
   change — the table is built from what already arrives.

## What the round found

1. **The status bar is no good for waiting for a second answer in one test.**  It holds the
   word of the *previous* answer ("решение найдено"), so `wait_for_result` returns at once
   after the second query and the check reads a still-empty table.  A new helper,
   `wait_for_the_run`, waits for `not window._busy` — a state the window keeps for the
   buttons anyway.  It cost one red run.
2. **`Ctrl+C` over the table would have been a silent mistake.**  `_copy` copies "from
   wherever the user is looking" and knows only text panes; without a case for the table
   the command would have gone to the editor and copied a selection nobody is looking at.
   Hence `TablePane.copy_selection` (columns by tabs, rows by newlines, so the table pastes
   into a spreadsheet) and `_copy` checking the table first.
3. **`QTableWidget` does not take focus without `show()`.**  The first version of the
   `Ctrl+C` check failed because `setFocus()` on an invisible window does not make a widget
   focused and `window.focusWidget()` stays the editor; now the check shows the window first
   and then requires `focusWidget() is window._table` — what the `Ctrl+C` case of the output
   pane does too.
4. **The table is not a kind of output.**  It has no `kind` and has nothing to do in
   `KIND_TAB`: it is built from an answer, not from text.  That is where the three things
   that had to be repeated in `TablePane` come from (the font size, the `zoomChanged`
   signal, the wheel with `Ctrl`), plus the fifth entry in `panes` for
   `_apply_output_font`; otherwise the wheel over the table would move somebody else's panes
   and the output would stop following it.
5. **Collecting has to start when the query is sent, not at `loaded`.**  At a marker the
   program is loaded *quietly* (`questions=False`), so the output of the load (what a
   directive printed) may arrive after the query has gone to the interpreter.  Only the
   shape rule saves it (`Имя=значение`; everything else is `ignored`).  This is recorded in
   §5 as a boundary, not as a defect.
6. **The count in the tab title counts solutions.**  `Таблица:3` reads as "three solutions"
   rather than "three rows" (the same thing, the first clearer), and a word answer gives
   `Таблица:1`, not `Таблица:0` — the tab never looks empty where the interpreter answered.

## Notes

* The key lines everything hangs on: `window.py::run_program` (which calls
  `_show_panel_tab(panels.TAB_OUTPUT)`), `window.py::_on_result` (the answer has already
  arrived as text), `window.py::_append_output` (the single funnel all output passes
  through), `engine.cpp::runQuery` (the shape of an answer), `panels.py::KIND_TAB` (the
  table is not a kind of output, which is why it is not there).
* The trap that easily gives an empty table: `_run_query` does not load the program, while
  `_on_query_requested` loads it *quietly* (`questions=False`) — so at a marker the answer
  arrives after `loaded`, whereas with a query line the program is loaded already.
  Collecting must start when the query is sent in both cases, and `loaded` meanwhile
  contributes the header line in "Система" (task_58), which does not enter the table — it
  has another kind (`NOTE`).
