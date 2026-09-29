# PrologD GUI (PySide6)

The graphical front-end is a **Python/PySide6** application that drives the
`prologd` executable through a line-delimited JSON protocol.  It never links
against `prlib`:

```
  ┌──────────────────┐   requests (JSON lines, stdin)   ┌───────────────┐
  │  PySide6 GUI     │ ───────────────────────────────▶ │  prologd      │
  │  prologd_gui/    │ ◀─────────────────────────────── │  --protocol   │
  └──────────────────┘   events (JSON lines, stdout)    │  json         │
                                                        └───────────────┘
```

Keeping the interpreter in a separate process means a buggy user program, a
Ctrl+C, or a restart of the session cannot take the GUI down with it.

## Running

```powershell
# build the interpreter first
cmake --preset windows-msvc
cmake --build build/windows-msvc --config Release

python -m venv .venv
.venv\Scripts\python -m pip install -r src/gui/requirements.txt
.venv\Scripts\python.exe src/gui/main.py --include examples/lib
```

`--exe` overrides the interpreter path (by default the newest build under
`build/` is used), `--include` adds an `ИМПОРТ` search directory and may be
repeated, and `--icons DIR` points the icon loader at another directory (the
default is `src/gui/assets`).

Activating the environment is optional: calling `.venv\Scripts\python.exe`
directly needs no `Set-ExecutionPolicy` and makes it obvious which interpreter is
meant.

`--theme light|system` chooses the appearance.  **`light` is the default and is
forced** through the Fusion style with an explicit palette, because Qt 6 follows
the Windows dark theme and the syntax colours are chosen for a *white*
background — on a dark one they are unreadable.  `system` keeps the platform
choice: what a light desktop wants, and the hook for a real dark theme, which
needs its own syntax palette rather than just this switch (task_29).

`--settings FILE` chooses the settings file; by default it is
`%LOCALAPPDATA%\PrologD\gui\gui.ini`, holding the font family and size, line
numbers, the indent character and width, completion and its threshold, and the
theme.  A value that cannot be
read falls back to the default instead of refusing to start, and keys this
version does not know are left alone (task_29 adds the dialog).

## Editor keys

| Key | Command |
| --- | --- |
| `F5`, `Ctrl+R` | **Запустить** — a run in a fresh interpreter; while a step is paused it means «продолжить» |
| `Shift+F5` | **Остановить** |
| `F10` | **Шаг** — one step point further in (starts a stepped run) |
| `Shift+F10` | **Шаг с обходом** — to the end of the current goal |
| `Ctrl+N` | **Новый** — an empty untitled buffer |
| `Ctrl+O` | **Открыть…** — a new tab; it does not run |
| `Ctrl+S`, `Ctrl+Shift+S` | **Сохранить**, **Сохранить как…** |
| `Ctrl+W` | close the tab (asks about unsaved changes) |
| `Ctrl+Tab`, `Ctrl+Shift+Tab` | next, previous tab |
| `Ctrl+Shift+R` | **Перечитать с диска** |
| `Ctrl+Q` | exit (asks about every modified buffer) |
| `Ctrl+L` | clear the output pane |
| `Ctrl+K` / `Ctrl+U` | comment / uncomment the selection or the current line |
| `Ctrl+F` | the find bar over the editor, with the selection or the word at the caret |
| `F3` / `Shift+F3` | next, previous match — also with the find bar closed |
| `Ctrl+F3` / `Ctrl+Shift+F3` | find the word under the caret, forwards and backwards |
| `Esc` | close the find bar, the focus goes back to the editor |
| `Enter` / `Shift+Enter` in the find field | the same as `F3` / `Shift+F3` |
| `F4` | show or hide the output panel (the input queue goes with it) |
| `Ctrl+F4` | move that panel between the right side and the bottom |
| `Ctrl+Space` | completion popup — it also opens by itself after two letters |
| `Enter` / `Tab` / `Esc` | take the highlighted completion / close the popup |
| `Ctrl`+wheel, `Ctrl`+keypad `+`/`-`, `Ctrl+0` | font size (6…72 pt) and its reset |
| `Tab` / `Shift+Tab` | indent / outdent the selected lines |
| `Enter` | continues the indent after `,`, `:-` or `<-` |

Long lines are wrapped only when **Вид → Переносить длинные строки** is on (no
key, stored as `editor/wrap`): a program line is read as a whole, and a wrapped one
hides where the line really ends.  The output pane never wraps, whatever the
switch says.

Neither list is final: the rest of the combinations is task_31.  Zoom uses the
*keypad* keys — `Ctrl+Num+` and `Ctrl+Num-`, which Qt spells `Num++` and `Num+-`
(the keypad modifier is part of the sequence) — so that `Ctrl+=`, `Ctrl++` and
`Ctrl+-` on the main row stay free for the `РАВНО(…)`, `СЛОЖЕНИЕ(…)` and
`ВЫЧИТАНИЕ(…)` skeletons.

## Menus, toolbar and icons

One table describes every command (`prologd_gui/actions.py`), and the menu bar,
the toolbar and the editor's context menu are all built from it — so a shortcut,
a tooltip or an enabled/disabled state cannot exist in two versions and drift
apart.  The window makes one `QAction` per entry and finds it by key.  A method with an
optional last argument is wired through a lambda (`"find": lambda: self.show_find()
`), because `QAction.triggered` hands the slot a `checked` boolean: that is how
`Ctrl+F` once arrived as `show_find(False)` and opened an empty field.

The menus are **Файл** (Новый, Открыть…, Последние, Сохранить, Сохранить как…,
Сохранить все, Перечитать с диска, Закрыть вкладку, Закрыть все, Выход),
**Правка** (Отменить … Удалить, Выделить всё, Закомментировать,
Раскомментировать, Форматировать, Настройки…), **Поиск** (Поиск и замена…,
Далее, Назад, Найти выделенное, Найти выделенное назад), **Вид** (Панель
инструментов, Панель вывода, Разделить редактор, Объединить редакторы, Сменить
ориентацию сплита, Номера строк, Увеличить/Уменьшить/Обычный размер шрифта,
Системная тема, Полный экран), **Выполнение** (Запустить, Запустить с
трассировкой, Шаг, Остановить, Сохранять перед запуском, Графическое окно) and
**Справка** (Руководство пользователя, Справка по окну, О программе).

An entry that does not exist yet stays in its menu but is **disabled**, and its
tooltip names what it waits for: «Форматировать» — task_30 and «Настройки…» —
task_29; «Графическое окно» has **no task file yet** (the roadmap below has the
plan).  A menu that silently lacks half of the feature list is worse than one that
says so.  «Поиск» left that list in task_33 and the «Выполнение» group in task_28 —
«Запустить с трассировкой», «Шаг» and «Шаг с обходом» are live.  The toolbar is
grouped as
the reference front-end had it: file | run/stop/step | editing (comment,
uncomment, format) | font size | tools (graphics, settings, help), and at the far
right **Очистить вывод**, which acts on the output rather than on the program;
`QToolBar.setIconSize(QSize(24, 24))` is set explicitly so the layout does not
depend on the style.

The two commands of the split editor follow the number of panes: `split` is
enabled while there is one, `merge` while there are two.  That is not cosmetic —
both carry a key, and a *disabled* `QAction` fires no shortcut — so the state is
recomputed right after a split or a merge (`_sync_pane_actions`).  It was
computed on start-up only, which left «Объединить редакторы» greyed out for the
rest of the session: the menu did nothing, `Ctrl+Shift+\` did nothing, and a
split could not be undone without a restart.

### Icon audit

`test_icons.py` is the guard: it fails as soon as a name is misspelled, and it
also checks that an icon which *does* have a file is not still listed as missing.
The code references **49** names, **42** of which have a file in
`src/gui/assets` (64×64 PNG, transparent background).  A missing file is not an
error: the action is built without a picture, and the name is reported once on
stderr (`icons: no view-theme.png — the action will have no picture`).

Present (42): `edit-clear`, `edit-comment`, `edit-copy`, `edit-cut`, `edit-del`,
`edit-find-replace`, `edit-format`, `edit-paste`, `edit-redo`, `edit-uncomment`,
`edit-undo`, `execution-abort`, `execution-execute`, `execution-step-into`,
`execution-tracing`, `file`, `file-close`, `file-close-all`, `file-exit`,
`file-modified`, `file-new`, `file-open`, `file-recent`, `file-reload`,
`file-save`, `file-save-all`, `file-save-as`, `file-saved`, `help`, `help-about`,
`prologd2`, `search-find`, `search-find-next`, `search-find-prev`,
`search-find-selected-next`, `search-find-selected-prev`, `tools-settings`,
`view-full-screen`, `view-graphics`, `view-zoom-in`, `view-zoom-out`,
`view-zoom-reset`.

Still to draw (7 names, listed in `assets.MISSING`) — the «Вид» switches
`view-toolbar`, `view-split-editor`, `view-output-right`, `view-output-bottom`,
`view-line-numbers` and `view-theme`, plus `execution-step-over`, the picture of
«Шаг с обходом» (the action is live since task_28 and shows its caption until the
file appears) and `execution-restart`, which nothing refers to yet.

Six of the names are not buttons at all:
`file`, `file-saved` and `file-modified` are the states of a tab, `prologd2` is
the window icon, `search-find` is the lens at the left of the find bar
(`actions.FIND_ICON`), and `edit-del` is the picture of «Удалить» in the «Правка»
menu.

## Stepping through a program

`F10` walks the program one step point at a time.  Four points exist, and they are
the four the textual trace already had: a **вызов** (a user predicate is entered),
an **успех** (its body is satisfied), a **переделка** (the solver is back in it,
looking for another solution) and a **неудача** (nothing matches, so it fails).  The
interpreter reports them as `step` events — structured, not the text of `ТРАССА`:
the text format is for humans and changes with the version, while a front-end needs
the action, the goal, the depth and the position.

The strip under the editor shows the point that was reached: the action, the goal
and how deep it is, where it stands in the source, and the call stack.  The stack
is rebuilt *here*, from the events: a `call` pushes the goal it names and the
`exit`/`fail` that answers it pops — an `exit` carries no goal of its own, because
the goal that succeeded is the one the `call` already reported.  The line of the
clause is highlighted in the editor in a neutral colour (the error line's
machinery, a different paint) and the caret follows it while that tab is showing.
`Shift+F10` steps out of the current goal: the interpreter stops sending the points
*inside* it, so a long recursion is walked over in one key rather than hundreds.
`F5` (**Продолжить**) runs on to the end, and `Shift+F5` ends the query, as it does
for a runaway run.

A paused step is a *usable* state, not a busy one: «Шаг», «Шаг с обходом» and
«Запустить» (= продолжить) are enabled while the panel is up, because a disabled
`QAction` fires no shortcut and those keys are exactly the ones the user needs
there.  The panel goes when the run is over; the mark stays until the next run or
the first edit.

«Запустить с трассировкой» is the same run with `ТРАССА` on.  The trace text is the
interpreter's own and arrives as `trace` events, so the pane colours it apart from
the program's output: a trace shown like the answer is a trace mistaken for one.
(The console front-end reads the same text in the output stream, where it always
was; the sink is what the protocol installs.)

### Where an error happened

`error` events carry `file`, `line` and `column` next to the human message
(protocol 3), so nothing is parsed out of the text.  A parse error has a position
from the parser and a **runtime error has one too**: the solver keeps the clause it
is solving in step with its environment, and `raise` fills in that clause's
location, so `деление на ноль` in the third clause of `модуль.pld` marks line 3
there.  `raiseAt` still overrides it where a caller knows better.

The window marks that line red, puts the caret on it, and names the file in the
status bar and in the pane (`path:line:column: message`).  A diagnostic from an
`ИМПОРТ`ed file names *that* file: the window looks for the tab, then next to the
file that imported it, then on disk — where it is opened in a tab of its own,
because marking a line in whatever tab happens to be showing would be worse than
marking none.  A name in angle brackets (`<buffer>`, `<library>`) is the text the
window itself sent, so that one is marked where it came from.  A line past the end
of the file (where `непарные скобки` is reported) is clamped to the last line that
exists, and the first edit clears the mark.

## The output panel

The output — with the input queue under it — is *one* panel inside a single
`QSplitter` whose orientation is the only thing that changes: side by side with
the editor when the panel is on the right, stacked under it when the panel is at
the bottom.  `Ctrl+F4` turns it, `F4` shows and hides it, and the side together
with the sizes of both splitters is remembered (`view/output_position`,
`view/output_visible`, `view/panel_sizes`, `view/output_sizes`) and comes back on
the next start.  A pane cannot be dragged away to nothing — `childrenCollapsible`
is off and each half has a minimum size — because a panel squeezed to zero pixels
looks like a lost window rather than a hidden one.

The text inside is `panels.OutputPane`: read-only, the editor's font and zoom,
and never wrapped (a log line cut in the middle cannot be read as data).  It
**colours by kind** — program output plain, our echo of an answer in the query
blue, our own markers grey, diagnostics crimson — and the kind comes from the
window, which knows whether it is feeding the program's text, a note or an
error; nothing is guessed from the text itself.  Chunks arrive mid-line, so a
line is held until its newline (or until the run ends, which flushes it): that is
the defect this code exists to avoid, and `LineBuffer` keeps it Qt-free so
`test_output.py` hammers it.  The history is bounded — 50 000 lines by default —
and the oldest lines are dropped in one edit with `*** вывод усечён … ***` kept
as the first line.  The view follows the end of the output until the user scrolls
up to read something, and follows again as soon as they come back to the bottom.

Undo, redo, «Запустить» and «Остановить» follow the *state*, and the state of the
interpreter is **two** things, not one: the process can be up and idle, and a
computation can be in flight in it.  «Запустить» needs the second — a run in
flight is not started twice, and the answer frees the button so that the next
press restarts the whole file — while «Остановить» needs the first, because a live
interpreter holds a knowledge base and unloading it is a stop of its own (the note
says `--- база знаний выгружена ---`; a computation that was interrupted gets
`--- остановлено ---`).  A window the user has only opened starts **no**
interpreter: the session comes up with the first run or with a goal typed into the
query line, which is also what makes «Остановить» dead until then.  The right-hand
side of the status bar says which of the three it is (`выполняется`, `база знаний
загружена`, `интерпретатор остановлен`), together with the caret's line and column
and the file's line ending and encoding.

### The input console

Under the output sits the **console**: the field the program's question goes into.
It is hidden while nothing is asked — an idle strip would take room from the output
for nothing — and appears with the question, framed in yellow (`#e0b400`) and with
the answer's own key in its placeholder (`Слово — Enter`, `Строка — Ctrl+Enter`,
`Символ — Enter`; the one-line field sends on `Enter`, the text area for a `line`
keeps `Enter` as a newline, because an answer to `ВВОДСТР` may be a sentence).
`Отправить` is there for the mouse.  The answer is echoed into the output with `>`,
like the prepared lines, and the strip disappears again.

Answers are taken in this order: the **prepared lines** under it (one per request),
then the console, and the **modal dialog** only when the whole panel is hidden by
`F4` — there is nowhere to put a console then.  «Вид → Поле очереди ввода» hides the
prepared lines; a hidden field contributes nothing at all, so the console answers
instead.  A run that is waiting is abandoned with «Остановить».

One thing the output pane learned from a user report: a line that has no newline yet
is written **at once**.  `ВЫВОД` prints without ending the line (that is the language:
`ВЫВОД` prints, `ПС` breaks the line), so a prompt like
`ВЫВОД("Введите символ"),ВВОДСИМВ(Ч)` used to stay invisible until the answer's
echo brought the newline — the program looked as if it asked before saying anything.
The pane now writes the unfinished line and continues it in place; a change of kind
(the window's own note arriving mid-line) still closes it first, and the end of a run
closes what is left.  «Файл → Сохранить вывод…» writes the pane as UTF-8 text — the
text, not the colours: a log should be readable in any editor.

## The find bar

`Ctrl+F` puts a strip above the editor: the question, the switches, the count and —
behind the «Замена» disclosure — the replacement field with **Заменить** and
**Заменить всё**.  It is a widget of the window and not a dialog, for two reasons: a
modal box covers the text being searched, and a modal box cannot be driven from a
headless test (the same trap `Buffers._ask_save` avoids).

Three rows, and the switches have one of their own: beside the field they were the
first thing squeezed out of a narrow window, and a switch that cannot be read is a
switch the user cannot use.  The strip is also as tall as its rows ask and no more
(`QSizePolicy.Maximum`) — with the default policy the layout shared the window's
spare height with the editor, so three short lines took half of the program pane.
A hidden row takes no room at all, so closing «Замена» gives the height back.

The question starts as the **selection**, or as the word the caret is inside when
nothing is selected — `факт` for a caret anywhere in `факт(1)`, not the whole
clause.  `F3` and `Shift+F3` walk the matches and wrap at the ends, and the bar
**says** it wrapped («1 из 3 — поиск с начала»).  A match the caret is *inside*
counts as the one being looked for, so `Ctrl+F` in the middle of a word lands on
that word, while `F3` still moves on.  Every match is highlighted while the bar is
open — the current one darker than the rest — in **every view** of the document,
because the split editor shows one text twice; `Esc` clears the highlight, closes
the strip and gives the focus back to the editor.  Searching never writes to the
file, and neither do `Ctrl+F3` and `Ctrl+Shift+F3`, which search for the word under
the caret.

The engine is `prologd_gui/search.py`, and it is **Qt-free** on purpose: what goes
wrong in a search is arithmetic — an offset into a folded copy instead of into the
text, a match counted twice, a wrap that never comes, a «Заменить всё» that finds
its own output — and `test_search.py` hammers exactly that.  The search is by
*text*, not by pattern: the programs are Russian and full of `#…#`, `?` and
parentheses, where regular-expression syntax would surprise more than help.
«С учётом регистра» switches case folding on (`факт` and `ФАКТ` are two predicates
in PrologD), and «Слово целиком» refuses a match that touches a word character on
either side, so `фактик` is not `факт`.

«Только в выделении» keeps the span it was switched on over — kept, and not read
again on every step, because the search itself moves the selection it would
otherwise be read from.  Switched on with nothing selected it refuses, and the bar
says «сначала выделите фрагмент» rather than quietly meaning «everywhere», which
would make its own message a lie.  «Заменить всё» is **one undo step**
(`beginEditBlock` around the whole replacement), so `Ctrl+Z` undoes the lot; the
count is recomputed while the text is edited under the bar, and that never moves
the caret — typing in the program must not throw the cursor into the next match.

## Tabs and files

A tab is one program.  **Запустить** runs the tab that is showing; a saved,
unmodified buffer is loaded *by path* (so `ИМПОРТ` resolves against the file's own
directory and diagnostics name it), while an edited or untitled buffer is loaded
as text — the status bar says which of the two is running.  Nothing is dropped
quietly: closing a tab, closing the window and `Ctrl+Q` ask **Сохранить / Не
сохранять / Отмена** per modified buffer, `Enter` lands on **Отмена**, and a
cancel cancels the whole close rather than only the last question.

A file keeps its shape: the line ending (LF or CRLF) and the encoding it was read
in are the ones it is written back with, a byte-order mark is dropped, and text
that is not valid UTF-8 asks which encoding to use instead of being decoded by
guesswork.  Dropping a `.pld` file on the window opens it in a new tab — it is not
run.  The last directory and the ten most recent files are remembered in the
settings file and shown in the «Последние» submenu of **Файл**, which prunes the
entries whose file is gone and can be emptied in one click.

`Ctrl+\` splits the editor into two panes side by side — each with its own tab
bar, both over the *same* document set, so an edit in either pane is the same
edit and re-ordering tabs in one re-orders them in the other.  The split, its
sizes and whether to restore it at all are settings (`view/split`,
`view/split_sizes`, `view/restore_split`).

A tab carries its state as a picture: `file` for a buffer that was never saved,
`file-saved` once it has a file on disk, and `file-modified` while there are
unsaved changes — saved or not.  The title bar carries the **whole path**, so two
files with one name are told apart without opening anything; the tab keeps the
short name, because a tab bar full of paths cannot be read.  The «Последние»
submenu shows the file picture for the entries that are programs, and the window
itself carries the application icon (`prologd2.png`), which «О программе» shows
as well.

Undo and redo follow the document of the tab that is showing — they are enabled
exactly when there is something to undo in *that* buffer, because the documents do
not share an undo stack.  A greyed-out «Отменить» with something to undo is a lie
the user notices at once.

Headless check of the protocol, without PySide6 installed:

```powershell
python src/gui/tests/protocol_smoke.py
```

## Protocol contract (version 3)

One JSON object per line in both directions; the interpreter writes nothing else
to stdout.  The C++ side lives in `src/cli/protocol.cpp`, the Python side in
`prologd_gui/protocol.py`.  Version 2 added the reserved names to `ready`; version
3 added stepping (`step` events and the `step` request), the `trace` events, the
`step`/`trace` flags of `load` and `query`, and the `file`/`line`/`column` fields
of `error`.  Version 1 sessions are still understood by the Python client (the
table is then empty and completion falls back to the document's own
predicates).

### Requests

| Request | Meaning |
|---------|---------|
| `{"cmd":"load","path":"prog.pld"}` | load a file; `ИМПОРТ` resolves against the `-I` directories |
| `{"cmd":"load","text":"…","name":"buffer"}` | load program text (the editor buffer) |
| `{"cmd":"query","text":"?цель(X)."}` | run one statement |
| `{"cmd":"input","text":"…"}` | answer the pending `input_request` |
| `{"cmd":"step","action":"into"}` | answer the pending `step` event; `action` is `into`, `over`, `continue` or `stop` |
| `{"cmd":"interrupt"}` | ask for a stop (see the note below) |
| `{"cmd":"quit"}` | end the session |

`load` and `query` take two optional flags: `"trace":true` turns `ТРАССА` on for
that run, and `"step":true` arms the step hook, so the run stops at its first
step point and waits for a `step` request.  A false flag is left off the wire.

### Events

| Event | Meaning |
|-------|---------|
| `{"event":"ready","protocol":3,"version":"2.0.0","keywords":[…]}` | the session is up |
| `{"event":"output","text":"…"}` | program output (`ВЫВОД`, query results) |
| `{"event":"result","found":true}` | one query finished; `found` is false when nothing matched |
| `{"event":"input_request","kind":"line"}` | `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД` waits for an answer; `kind` is `token`, `line` or `codepoint` |
| `{"event":"step","action":"call","goal":"…","depth":2,"file":"…","line":9,"column":1}` | a step point; `action` is `call`, `exit`, `redo` or `fail`.  `goal` is absent for `exit` (the goal is the one its `call` named), and the position is absent when there is none |
| `{"event":"trace","text":"…"}` | one line of the `ТРАССА` trace |
| `{"event":"error","kind":"parse","message":"…","file":"…","line":3,"column":5}` | diagnostic; `kind` is `parse`, `runtime` or `protocol`, and the position is absent when there is none to report |
| `{"event":"bye"}` | the session is over |

Exit codes: `0` clean, `1` usage error, `2` load/parse failure, `3` runtime
failure (for example an interrupted query).

### Notes for front-ends

* **A run is a new session.**  The clause database, the `СЛУЧ` seed, the
  `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` redirection and the preloaded `$` input lines all live
  in the interpreter process, so loading a second program into a session that
  already ran one *accumulates* clauses and prints every solution twice.  Start a
  fresh process for a run — that is what **Запустить** does — and keep one session
  only for the queries that belong together.  A request written before the
  interpreter announced itself is queued by `session.py` rather than lost.
* **`result` carries no text.**  The answer is printed by the interpreter itself
  (`ДА`, `НЕТ`, or `X=1` lines) and arrives as `output`; `result` only says the
  query is over, with `found` telling whether anything matched.  A front-end that
  appends its own `НЕТ` for `found == false` prints the answer twice — which
  looks like a bug in the user's program.  The window keeps it for the status
  bar only.
* **Input is a question, not a stream.**  The interpreter asks with
  `input_request` and waits for exactly one `input` request with the answer, so a
  front-end may answer out of its own prepared list.  The window feeds the lines
  typed into the field under the output pane, one per request, and falls back to
  a single-line dialog when that list is empty; cancelling the dialog stops the
  session instead of answering an empty string.
* **A step point is a question too.**  The `step` event is written when the solver
  reaches a point with the hook armed, and the interpreter then *waits* inside the
  query for the `step` request that answers it — the same re-entrant read loop
  `input_request` uses, so no new threading model is involved.  This is the whole
  reason the hook blocks instead of returning a "paused" state: the solver has no
  continuation to suspend, and the read loop a front-end already has is exactly
  the pause.  A `step` request with nothing waiting is a protocol error, as an
  `input` with nothing waiting is.
* `ready` carries `keywords`: every reserved name the lexer knows, with its kind
  (`predicate`, `operator`, `directive`) and its arities — `[]` for operators,
  directives and the variadic `ВЫВОД`, which is marked with `"variadic":true`.
  The same table is printed by `prologd --list-keywords`, one `name/arity` per
  line (`ВЫВОД/+` for the variadic one), so a front-end never keeps its own copy
  of the built-in list.  Highlighting, completion and the shortcut cheat-sheet
  all read it.

* Read the interpreter's stdout line by line and never merge it with stderr; in
  protocol mode all diagnostics travel as `error` events.
* The answer to an `input_request` is one string; embedded newlines stay inside
  that string.
* `interrupt` is handled between commands and while the interpreter waits for
  input.  A query that neither waits for input nor finishes **cannot** be
  interrupted politely — terminate the process and start a new session, which is
  what the **Остановить** button does.
* `-i`, `-o` and `-e` are refused together with `--protocol json`: the protocol
  owns stdin and stdout.

## Roadmap

* A graphics pane fed by a `GraphicsBackend` that emits protocol events
  (`ТОЧКА`, `ЛИНИЯ`, … currently reach a null backend).
* Step-by-step execution over the `ТРАССА` stream.
* Settings persistence: the file and the editor's values exist; the dialog and
  the rest of the list (interpreter path, include directories, window layout)
  are task_29.
