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
| `F5`, `Ctrl+R` | **Запустить** — a run in a fresh interpreter |
| `Shift+F5` | **Остановить** |
| `Ctrl+N` | **Новый** — an empty untitled buffer |
| `Ctrl+O` | **Открыть…** — a new tab; it does not run |
| `Ctrl+S`, `Ctrl+Shift+S` | **Сохранить**, **Сохранить как…** |
| `Ctrl+W` | close the tab (asks about unsaved changes) |
| `Ctrl+Tab`, `Ctrl+Shift+Tab` | next, previous tab |
| `Ctrl+Shift+R` | **Перечитать с диска** |
| `Ctrl+Q` | exit (asks about every modified buffer) |
| `Ctrl+L` | clear the output pane |
| `Ctrl+K` / `Ctrl+U` | comment / uncomment the selection or the current line |
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
apart.  The window makes one `QAction` per entry and finds it by key.

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
tooltip names what it waits for: «Форматировать» — task_30, «Настройки…» —
task_29, «Поиск и замена…» and the four search commands — task_33,
«Запустить с трассировкой» and «Шаг» — task_28, «Графическое окно» — **no task
file yet** (the roadmap below has the plan).  A menu that silently lacks half of
the feature list is worse than one that says so.  The toolbar is grouped as
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
The code references **46** names, **31** of which have a file in
`src/gui/assets` (64×64 PNG, transparent background).  A missing file is not an
error: the action is built without a picture, and the name is reported once on
stderr (`icons: no view-zoom-in.png — the action will have no picture`).

Present (31): `edit-comment`, `edit-copy`, `edit-cut`, `edit-format`,
`edit-paste`, `edit-redo`, `edit-uncomment`, `edit-undo`, `execution-abort`,
`execution-execute`, `execution-step-into`, `execution-tracing`, `file`,
`file-close`, `file-close-all`, `file-exit`, `file-new`, `file-open`,
`file-save`, `file-save-all`, `file-saved`, `file-modified`, `help`,
`prologd2`, `search-find-next`, `search-find-prev`, `search-find-selected-next`,
`search-find-selected-prev`, `tools-settings`, `view-full-screen`,
`view-graphics`.

Still to draw (15 names, listed in `assets.MISSING`) — needed for:

| Name | Needed for |
|------|------------|
| `file-save-as`, `file-reload` | Сохранить как…, Перечитать с диска |
| `file-recent` | the «Последние» submenu (named in `actions.RECENT_ICON`) |
| `edit-clear`, `edit-find-replace` | Очистить вывод; Поиск и замена… |
| `view-toolbar`, `view-split-editor`, `view-output-right`, `view-line-numbers` | the view switches |
| `view-zoom-in`, `view-zoom-out`, `view-zoom-reset`, `view-theme` | zoom (combo box, `Ctrl+0` and the keypad keys) and the theme switch |
| `view-output-bottom`, `help-about` | Сменить ориентацию сплита; О программе |

`MISSING` also names two icons nothing refers to yet — `execution-restart` and
`execution-step-over` — which is allowed: they are the pictures for features that
are not wired (task_27, task_28).  The directory holds 32 files, and only one is
never asked for: `search-find.png`, which task_33 wants under its own name.  Four
of the names are not buttons at all: `file`, `file-saved` and `file-modified` are
the states of a tab, and `prologd2` is the window icon, shown in «О программе» and
in the taskbar.

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

Undo, redo, «Запустить» and «Остановить» follow the *state*: the first two read
the document of the tab that is showing, the last two the session — a live
interpreter is the only thing that can be stopped, and a fresh one the only thing
that can be started (`_sync_run_actions`, refreshed on `ready`, on a failure, when
a run ends and right after a stop).  The right-hand side of the status bar shows
that state together with the caret's line and column and the file's line ending
and encoding.

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

## Protocol contract (version 2)

One JSON object per line in both directions; the interpreter writes nothing else
to stdout.  The C++ side lives in `src/cli/protocol.cpp`, the Python side in
`prologd_gui/protocol.py`.  Version 2 added the reserved names to `ready`;
version 1 sessions are still understood by the Python client (the table is then
empty and completion falls back to the document's own predicates).

### Requests

| Request | Meaning |
|---------|---------|
| `{"cmd":"load","path":"prog.pld"}` | load a file; `ИМПОРТ` resolves against the `-I` directories |
| `{"cmd":"load","text":"…","name":"buffer"}` | load program text (the editor buffer) |
| `{"cmd":"query","text":"?цель(X)."}` | run one statement |
| `{"cmd":"input","text":"…"}` | answer the pending `input_request` |
| `{"cmd":"interrupt"}` | ask for a stop (see the note below) |
| `{"cmd":"quit"}` | end the session |

### Events

| Event | Meaning |
|-------|---------|
| `{"event":"ready","protocol":2,"version":"2.0.0","keywords":[…]}` | the session is up |
| `{"event":"output","text":"…"}` | program output (`ВЫВОД`, query results, traces) |
| `{"event":"result","found":true}` | one query finished; `found` is false when nothing matched |
| `{"event":"input_request","kind":"line"}` | `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД` waits for an answer; `kind` is `token`, `line` or `codepoint` |
| `{"event":"error","kind":"parse","message":"…"}` | diagnostic; `kind` is `parse`, `runtime` or `protocol` |
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
