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

`--theme light|dark|system` chooses the appearance; «Вид → Оформление» is the same
three in a submenu.  **`light` is the default** and is forced through the Fusion
style with an explicit palette, because Qt 6 follows the Windows dark theme and
the syntax colours are chosen for a *white* background — on a dark one they are
unreadable.

`dark` is a **palette of its own**, not an inversion: a second syntax palette for a
`#1e1e1e` page, a second set of bands (the error line, the step line, the search
matches, the current line), the margin and the colours of the output's kinds — all
of it one `theme.Palette` record, and every pair that has to be readable is
measured against the page it is really drawn on (WCAG AA, 4.5, in
`test_appearance.py`).  Switching the theme re-colours the text already in the
output pane too, so a dark window never holds light-theme red on a dark page.

`system` — «как в системе», the last of the three — follows the desktop
*completely*: the platform's widget palette and style are put back, and the syntax
colours resolve to the palette that goes with the desktop's colour scheme
(`appearance.theme_palette`).  A dark desktop therefore gets a dark window **and**
dark-page colours without anybody choosing `dark`; before that this option was half
a theme — the widgets dark and the light syntax colours on top of them.

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
| `F1` | **Справка по предикату** — the record of the word under the caret, in a dock |
| `Shift+F1` | **Руководство пользователя** — the built PDF (`doc/help.pdf`) |
| `Ctrl+Space` | completion popup — it also opens by itself after two letters |
| `Enter` / `Tab` / `Esc` | take the highlighted completion / close the popup |
| `Ctrl`+wheel, `Ctrl`+keypad `+`/`-`, `Ctrl+0` | font size (6…72 pt) and its reset |
| `Tab` / `Shift+Tab` | indent / outdent the selected lines |
| `Enter` | starts the new line at the indentation of the one above, one step deeper after `,`, `:-` or `<-` (with «Автоотступ» unticked, it starts at the margin) |

Long lines are wrapped only when **Вид → Переносить длинные строки** is on (no
key, stored as `editor/wrap`): a program line is read as a whole, and a wrapped one
hides where the line really ends.  The output pane never wraps, whatever the
switch says.

Zoom uses the *keypad* keys — `Ctrl+Num+` and `Ctrl+Num-`, which Qt spells `Num++`
and `Num+-` (the keypad modifier is part of the sequence) — because the main row
belongs to the insert table below.

## Ctrl plus a physical key

The punctuation a Prolog program needs is not where the Russian layout puts it:
`:-` is `Ctrl+;`, `?` is `Ctrl+/`, `[` is a letter.  Instead of switching the
layout, `Ctrl` plus the **physical** key inserts the symbol that key carries in
*either* layout.  The list is in **Справка → Шпаргалка по вставкам**.

| `Ctrl` + key | Inserts | Where the caret lands |
| --- | --- | --- |
| `;` or `6` | `:-.` | between `-` and `.` |
| `9` | `()` | inside |
| `[` | `[]` | inside |
| `3` | `#` | after |
| `Shift+/` or `7` | `?` | after |
| `=` | `РАВНО(,)` | after the `(` |
| `Shift+.` | `БОЛЬШЕ(,)` | after the `(` |
| `Shift+,` | `МЕНЬШЕ(,)` | after the `(` |
| `Shift+=` | `СЛОЖЕНИЕ(,,)` | after the `(` |
| `8` | `УМНОЖЕНИЕ(,,)` | after the `(` |
| `/` | `/` | after |
| `-` / `Shift+-` | `-` / `_` | after |
| `1` | `!` | after |
| `'` / `Shift+'` | `''` / `""` | inside the quotes |

The second column is the *same physical key* in a Russian and in an English
layout, and that is the whole point: the pair `Задача :- Цель.` is two chords with
the Russian layout on, and they produce exactly the same text with the English one
on.  Two symbols have a second chord because the layouts disagree about where they
live: the Russian `:` is `Shift+6` and the Russian `?` is `Shift+7`.

* **Matching is by scan code** (`QKeyEvent.nativeScanCode()`), never by
  `event.text()` — the character is the one thing the layouts differ in.
* **Only `Ctrl`** (plus the `Shift` a chord asks for) is accepted: `Alt` alone
  hands the focus to the menu bar, and `Ctrl+Alt` is `AltGr` on many layouts, so
  neither may be swallowed.  Both fall through to the window untouched.
* **One undo step** per insert, and with a selection the bracket-like entries
  *wrap* it: `(выделение)`, `[выделение]`, `#выделение#`, `?выделение`; the rest
  replace it, as typing the character would.
* **The table is data.**  It lives in the settings file under `shortcuts/table` as
  JSON, and the window writes the built-in table there the first time it runs, so
  a symbol that sits elsewhere — or a keyboard without that key — is remapped in
  the file.  An entry is `{"insert": "…", "chords": [{"scan": …, "shift": …}]}`,
  `|` marks the caret and `{}` marks the selection a `wrap` surrounds; a file that
  cannot be read falls back to the built-in table instead of taking the window
  down.  Each entry can carry **several chords**, which is what the `6` and `7` rows
  above are.
* **No chord steals a window command.**  `Ctrl+\` and `Ctrl+Shift+\` are split and
  merge, so `|` has no chord, and the zoom moved to the keypad.  Two symbols are
  therefore reachable only on their US positions, and the test says so out loud:
  the Russian `/` is `Shift+\` (= merge) and the Russian `"` is `Shift+2`, which is
  why `Ctrl+/` and `Ctrl+Shift+'` are the chords for them.

The mapping, the wrapping and the settings round trip are checked without Qt in
`src/gui/tests/test_shortcuts.py`; the same file asks Windows where each symbol
actually sits in the US and the Russian layouts (`VkKeyScanExW`, `MapVirtualKeyW`),
which is the part that cannot be reasoned about.  With a Russian layout on, walk
the table once by hand — that is the one check no test replaces.

## Questions in the margin

Every question of a lesson — a `?Цель.` line, and also a query parked in a
comment (`%   ?ВЕРСИЯ.`) — is marked with a blue triangle in the margin, left of
the line numbers; a click runs exactly that statement.  The statement goes into
the query line and stays visible there, the program is loaded *quietly*
(`"questions":false`), and the pane holds the one answer that was clicked.

That same flag is what «Выводить вопросы при запуске» in the settings dialog
(`execution/run_questions`, on by default) puts on an ordinary run: unticked, a
lesson is loaded for its clauses only — including through the step and trace
commands, because a program's own `?`-statements and directives run during the
load — and its questions wait for a click on their marker.

Which lines are questions is decided by `queries.py` and checked without Qt in
`test_queries.py`: the first non-blank characters of the line are `?` or `%`
followed by blanks and `?`, the sentence ends at the first `.` outside `"..."`,
`'...'`, `#...#` and every bracket, and each bare word inside must be a variable,
a reserved name, or a name the document itself uses.  The last clause is what
refuses prose like `% ?длина(Х, 2) не завершится.` — the rule is deliberately not
a parser, and a line it cannot read gets no marker: no marker is a small loss, a
marker that runs the wrong text is a wrong program.  The sweep over `examples/`
pins the number of statements per file, and that no live `?`-line anywhere is
left without a marker.  A comment-shaped line that starts with `%` and `?` is
coloured as a question (orange) rather than as a comment: that is the shape of a
parked question — whether the word rule then gives it a marker is the rule's own
decision.

A click during a run stops it first (`Остановить`) and then runs the clicked
question in a fresh interpreter: the marker is the way out of a runaway query as
much as a way to ask one.  The click leaves the caret, the selection and the
document untouched — a run is not an edit.

## The built-in reference

The window answers «what does `КОПИЯ` do?» where the question is asked.  The data
is `doc/builtins.json` — one record per predicate (name, English aliases, kind,
arities, group, the `help.typ` section, a one-line summary, the argument modes);
`doc/help.typ` builds its appendix table of English names from the same file, so
there is one place where a predicate is *described*, not two.  The records are
kept in step with the interpreter and the manual by `test_reference.py` (name
sets, arities, kinds, section headings, the shape of a summary and of a variant);
`reference.py` is the Qt-free loader the window reads — a missing or broken file
is an empty reference, never a failed start-up.

Two places show it: a frameless `QLabel` under the completion popup showing the
summary of the highlighted row (a row without a record shows no label — silence is
better than «no description» for every second name), and the dock that `F1` opens:
summary, English alias, the help section and *every* argument mode, filled for the
word under the caret.  The dock is not modal — the manual is read *next to* the
code, and a modal window cannot be driven from a headless test.  `F1` belongs to
the in-window answer; the PDF manual keeps `Shift+F1`.

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
Далее, Назад), **Вид** (Панель
инструментов, Панель вывода, Поле очереди ввода, Разделить редактор, Объединить
редакторы, Сменить ориентацию сплита, Номера строк, Переносить длинные строки,
Увеличить/Уменьшить/Обычный размер шрифта, Оформление (подменю: светлое, тёмное,
как в системе), Полный экран), **Выполнение** (Запустить, Запустить с
трассировкой, Шаг, Шаг с обходом, Остановить, Сохранять перед запуском, Выводить
вопросы при запуске, Графическое окно) and
**Справка** (Справка по предикату, Шпаргалка по вставкам, Руководство
пользователя, Справка по окну, О программе).

An entry that does not exist yet stays in its menu but is **disabled**, and its
tooltip names what it waits for.  **That list is empty now**: «Графическое окно»
left it in task_45, and before that «Поиск» in task_33, the «Выполнение» group in
task_28, «Форматировать» in task_30 and «Настройки…» in task_29.  A menu that
silently lacks half of the feature list is worse than one that says so, and a menu
where nothing has to be said is better than both.

The toolbar is grouped as
the reference front-end had it: file | run/stop/step | editing (comment,
uncomment, format and, right beside it, the formatter's **mode control** — a
`QToolButton` with the three modes and «только выделенное», where a mode is
switched while looking at the code) | font size | tools (graphics, settings,
help), and at the far
right **Очистить вывод**, which acts on the output rather than on the program;
`QToolBar.setIconSize(QSize(24, 24))` is set explicitly so the layout does not
depend on the style.

Two commands left the toolbar in this round.  «Сохранить все» acts on *every*
tab, so it lives in «Файл» where the rest of them are: the toolbar keeps the
three file buttons that act on the tab in front of the user.  And «Найти
выделенное» / «Найти выделенное назад» are gone altogether — with the word under
the caret already in the «Найти» field, one `Ctrl+F` did the same thing, and the
two commands cost two entries and two icons.  The «Вид» switches («Номера
строк», «Панель инструментов») are deliberately **text-only**: a switch reads
faster as a word than it is recognised as a picture.

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
The code references **45** names, **41** of which have a file in
`src/gui/assets` (64×64 PNG, transparent background).  A missing file is not an
error: the action is built without a picture, and the name is reported once on
stderr (`icons: no view-theme.png — the action will have no picture`).

Present (41): `edit-clear`, `edit-comment`, `edit-copy`, `edit-cut`, `edit-del`,
`edit-find-replace`, `edit-format`, `edit-format-set`, `edit-paste`, `edit-redo`,
`edit-uncomment`, `edit-undo`, `execution-abort`, `execution-execute`,
`execution-step-into`, `execution-step-over`, `execution-tracing`, `file`,
`file-close`, `file-close-all`, `file-exit`, `file-modified`, `file-new`,
`file-open`, `file-recent`, `file-reload`, `file-save`, `file-save-all`,
`file-save-as`, `file-saved`, `help`, `prologd2`, `search-find`,
`search-find-next`, `search-find-prev`, `tools-settings`, `view-full-screen`,
`view-graphics`, `view-zoom-in`, `view-zoom-out`, `view-zoom-reset`.

Still to draw (4 names, listed in `assets.MISSING`) — the «Вид» switches
`view-split-editor`, `view-output-right`, `view-output-bottom` and `view-theme` —
plus `execution-restart`, whose file is drawn but which nothing refers to yet.
`view-theme` belongs to the «Оформление» submenu, which is words
rather than pictures, and it stays in the audit because it is the picture the
reference front-end used for exactly this.

Three pictures left the audit.  `help-about` was the same drawing as
`prologd2`, and two files for one picture drift apart, so «О программе» now wears
the application icon; `search-find-selected-next` and
`search-find-selected-prev` went with the commands they belonged to; and
`view-toolbar` and `view-line-numbers` were dropped because those two switches
are words now.  `edit-format-set` — the formatter's mode — is the one that
*joined* the set, and it is what the mode control on the toolbar wears.

Five of the names are not buttons at all: `file`, `file-saved` and
`file-modified` are the states of a tab, `prologd2` is the window icon and
the picture of «О программе» (one drawing, one file), and
`edit-del` is the picture of «Удалить» in the «Правка» menu.  `search-find`
(`actions.FIND_ICON`) is the lens at the left of the find bar *and* the picture of
«Поиск и замена…» — the plain lens, because the command is the search; the
«замена» picture (`edit-find-replace`, `actions.REPLACE_ICON`) is the triangle
that opens the replacement half of the bar.

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
for a runaway run.  The strip carries three of the toolbar's pictures — продолжить,
шаг, стоп — with the words and their keys in the tooltips, and its whole row is set
in the editor's monospace font: a monospace goal between proportional labels reads
as a defect, and zooming used to move only half of the strip.

The «где» label carries a *place*, not the whole path: the last two components
(`…\examples\monk.pld:2:1`), with the whole path in its tooltip — a full path in
that one row ran up against the buttons beside it.  A window too narrow even for
that drops the head of the label and keeps its tail, in front of «…»: the file's
own name, the line and the column are what is being read.  (Qt's own middle
elision was measured first: it turns that place into `…\e…2:1` at a third of the
width.)

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
(protocol 3) and its `severity` (protocol 4), so nothing is parsed out of the
text.  A parse error has a position
from the parser and a **runtime error has one too**: the solver keeps the clause it
is solving in step with its environment, and `raise` fills in that clause's
location, so `деление на ноль` in the third clause of `модуль.pld` marks line 3
there.  `raiseAt` still overrides it where a caller knows better.

The window marks that line red, puts the caret on it, and names the file in the
status bar and in the pane (`path:line:column: message`).  A diagnostic from an
`ИМПОРТ`ed file names *that* file: the window looks for the tab, then next to the
file that imported it, then on disk — where it is opened in a tab of its own,
because marking a line in whatever tab happens to be showing would be worse than
marking none.  A diagnostic names the text it came from, and *which* of the window's own names it
is decides whether a line is marked at all: a text load is named after its tab — a
saved file by its path, an unnamed buffer by its title («Без имени 2», the name on
the tab) — so a diagnostic in it belongs to that buffer and is marked there;
`<buffer>` is the protocol's default for a load that named nothing, and the window
still reads it as «the showing tab».  `<library>` is the interpreter's own
preloaded text and `<query>` is the one statement of a `query` request (typed in
the query line or clicked in the margin) — neither has a line in any tab, so they
are shown in the pane and the caret is left alone.
Marking line 1 of the program for a failed query is exactly what that rule fixed:
the error is in the statement, not in the first line of the program.  A line past
the end of the file (where `непарные скобки` is reported) is clamped to the last
line that exists, and the first edit clears the mark.

## The graphics window

The graphics predicates draw into the interpreter (a `ТОЧКА(X, Y, Цвет)` read and
a `ЗАКРАСКА` read cells from *inside* a built-in, so the pixels cannot live on the
other side of the pipe) and **«Выполнение → Графическое окно»** shows them.  The
entry is checkable — its state is the window's visibility — and both the
visibility and where the window stood are remembered (`view/graphics_visible`,
`view/graphics_geometry`, a `saveGeometry()` blob: Qt knows about screens, a
maximised window and a display that is no longer there).

`graphicswindow.GraphicsWindow` is a window of its own (`Qt.Window`, *owned* by
the main window — without that flag a `QWidget` with a parent is a child widget
and the picture would be embedded in the editor).  Its toolbar has «Вписать в
окно» (the whole 1024×768 screen in the window), «1 : 1» (one cell per screen
pixel, with the scroll area doing the moving), «Очистить» (the *window's* picture
— the interpreter's screen belongs to the program, and a new run starts a fresh
interpreter and clears the canvas with it) and «Сохранить как PNG…»; to the right
stands the cell under the pointer («x=320 y=240 цвет=14»), because "why is it
yellow" is a question the palette answers.

`CanvasView` paints `graphics.Canvas.rgba` — the canvas' own buffer, wrapped in a
`QImage` without a copy, so a primitive costs a few writes and one repaint and an
animation (lesson 12) follows the program.  The scale is nearest-neighbour: the
picture is pixel art, and a smoothed line at a fractional zoom no longer stands
where the program put it.

The drawing arrives as events while the window is open; a window that was **not**
open asks for the whole screen when it opens (`{"cmd":"graphics","snapshot":true}`
→ `bitmap`).  A window that was never opened costs nothing: the canvas is created
on first use, and the events of a run nobody watched are simply not needed — the
snapshot has them.

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

The text inside is `panels.OutputPane`: read-only, its own font and zoom (task_29:
the editor and the output keep two sizes, and the output follows the editor's
while nobody has set one of its own), and never wrapped (a log line cut in the
middle cannot be read as data).  It
**colours by kind** — program output plain, our echo of an answer in the query
blue, our own markers grey, diagnostics crimson — and the kind comes from the
window, which knows whether it is feeding the program's text, a note or an
error; nothing is guessed from the text itself.  Chunks arrive mid-line, so a
line is held until its newline (or until the run ends, which flushes it): that is
the defect this code exists to avoid, and `LineBuffer` keeps it Qt-free so
`test_output.py` hammers it.  The history is bounded — 50 000 lines by default,
and the limit is a setting since task_29 (`output/line_limit`, 100…500 000:
a smaller one trims the pane at once) —
and the oldest lines are dropped in one edit with `*** вывод усечён … ***` kept
as the first line.  The view follows the end of the output until the user scrolls
up to read something, and follows again as soon as they come back to the bottom —
unless «Следить за выводом» in the settings dialog is unticked
(`view/follow_output`), which forbids the jump even at the end of the text, for a
reader who wants the pane to hold still while a program talks.
The pane is read-only, so the one operation it owes beside reading is copying text
*out* of it: the mouse selects as usual, and `Ctrl+C` copies the selection of
whichever text widget has the focus — the output, the input queue, the console
line or the editor — instead of always the editor's (the command is a window
shortcut and used to do exactly that).

Undo, redo, «Запустить» and «Остановить» follow the *state*, and the state of the
interpreter is **two** things, not one: the process can be up and idle, and a
computation can be in flight in it.  «Запустить» needs the second — a run in
flight is not started twice, and the answer frees the button so that the next
press restarts the whole file — while «Остановить» needs the first, because a live
interpreter holds a knowledge base and unloading it is a stop of its own (the note
says `--- база знаний выгружена ---`; a computation that was interrupted gets
`--- остановлено ---`).  Stopping a *run* is polite first: the session is asked to
end the query (`interrupt`), and the process is taken down only if the interpreter
has not finished on its own within `STOP_GRACE_MS` (500 ms) — so an interrupted run
leaves the interpreter idle *with* its base, and the next press unloads it.  A
window the user has only opened starts **no**
interpreter: the session comes up with the first run or with a goal typed into the
query line, which is also what makes «Остановить» dead until then.  Opening the
window *does* start the executable once, briefly, for `--list-keywords`: the
reserved names are needed by completion and colouring before anything runs, and
waiting for the first `ready` is why autocompletion used to work only after the
first run.  That process exits at once — no interpreter is left alive — and the
first real session replaces the table with the `ready` event's copy of the same
data.  The right-hand
side of the status bar says which of the three it is (`выполняется`, `база знаний
загружена`, `интерпретатор остановлен`), together with the caret's line and column
and the file's line ending and encoding.  A run of a program that asks no
questions — an empty one included — ends on the `loaded` event (protocol 8) with
`выполнено`: `result` arrives per question, and without that event a program with
none left the window saying `выполняется` with `Запустить` disabled forever.

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
instead.  «Спрашивать ввод» in the settings dialog (`view/input_mode`) chooses
between the two *places* a question is put: `в панели вывода` (the console, the box
only when the panel is hidden — the default) or `в диалоге`, where every question is
a box even with the console right there.  A run that is waiting is abandoned with
«Остановить».

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

## Formatting a program

**Форматировать** (`Ctrl+I`) only ever moves whitespace: the text is laid out
again, but every name, number, `#expr#` body, quote and comment is copied byte
for byte, so formatting cannot damage a program.  The formatter itself lives in
prlib, next to the grammar it has to understand — a second parser in Python would
drift — so the window sends the buffer with a `format` request (protocol 6) and
puts the answer back.  The grammar's copy of that request is `prologd --format`;
the protocol contract has the details, and `src/gui/tests/test_formatter.py`
drives the wire headlessly.

The mode is the button on the toolbar right after **Форматировать** (it is a
preference, so task_29's dialog edits the same keys): one click opens the list —
**в одну строку** joins the goals of a body
whatever the line costs; **мягкое** builds the lines again — goals are packed up
to the width (80 columns by default) and moved to a continuation line when they
do not fit; **жёсткое** puts the head of a clause on a line of its own and each
goal of its body on a line of its own.  The same menu carries «только выделенное»:
with it, only the selected fragment is sent,
and a fragment that breaks off in the middle of a body is formatted up to its
last complete goal — the rest is copied as it stands.  Trailing whitespace never
survives, runs of blank lines between statements collapse into one (inside a
statement an author's blank line stays and forces a break), and a `%` comment
stays on the line it was written on.

A **query** and a **directive** are never broken, in any mode.  Neither has a
head or a body to lay out — one is a question, the other an instruction — and the
tools that run them read a *line*: the margin marker is line-local by design
(task_36), so a query split by the formatter would be a question nobody can
click.  This is not abstract: formatting lesson 12 broke its long «сад» query in
two and the pinned question count in `test_queries.py` caught it.

The soft mode deliberately does **not** keep the author's line breaks between
goals: a break written by the hard mode cannot be told apart from one the author
made, and keeping them is exactly what used to make «из жёсткого обратно в
мягкое» impossible.  Only three things break a soft line — the width, a comment
(which owns its line) and a blank line the author left.  The soft shape is
therefore canonical, and any format converts into any other: the way back from a
hard layout is `Ctrl+I` with the soft mode.  There is no «не менять» entry any
more: the command not being pressed is «не менять».

What the window takes care of around the text: the replacement is **one undo
step**, the **caret and the selection keep their places** (only whitespace moved,
so `formatter.map_positions` carries the old offsets onto the new text), and a
program that does not parse is **never rewritten** — the status bar says «не
удалось разобрать», the offending line is marked, and the buffer keeps its text.
An edit that arrives while the answer is in flight cancels the format instead of
discarding the edit.

## Settings

**Правка → Настройки…** is built from `settings.SETTINGS`: a table of records —
key, label, section, kind, default, bounds, hint — that is also what validation
clamps against and what «Сбросить» writes back.  A new preference is therefore a
new record, and the dialog grows by itself; `test_settingsdialog.py` checks that
every record has a widget and every widget writes its key.

| Section | What is in it |
| --- | --- |
| Редактор | font family and size, line numbers, the current-line band, word wrap, tabs or spaces and the width, auto-indent, completion (on/off, after how many letters, `Учитывать регистр`) |
| Вид | theme (light, dark or system), toolbar, the output panel (shown, right or bottom), the input queue field, where a program's input question is asked (console or dialog), the output's font size, its line limit and whether it follows the end |
| Формат | the formatter's mode, width, indent and unit, «только выделенное» |
| Выполнение | whether a run answers the program's own `?`-questions, save before run, the four limits (steps, depth, НАЙТИВСЕ solutions, seconds), the shared folder for `ИМПОРТ`, more `-I` folders |
| Файлы | autosave in minutes (0 = off), how many recent files to remember, restoring the open tabs at start-up |
| Вставки | the live `Ctrl`+key table (task_31), the settings file path, «Вернуть встроенную таблицу» |

* **ОК** and **Применить** write through `Settings` and say so
(`SettingsDialog.changesApplied`); the window's answer to that signal is
`apply_settings`, which re-reads every value — so a change shows *there and then*,
with the dialog still open (the window behind a modal dialog is blocked for
input but keeps painting).  «Применить» writes only the rows that actually
differ, so a fresh file stays fresh.  «Отмена» closes without writing what was
not applied; what *was* applied stays, the way `Применить` means everywhere.
* The button row is built by hand, not by a `QDialogButtonBox`: that one lays its
buttons out by *role* and by the current style, and here the order is a decision —
«Сбросить», «Импорт…», «Экспорт…» on the left (they act on the whole file),
«ОК», «Отмена», «Применить» on the right (they end or keep the dialog).
* The pages share **one label column**: a `QFormLayout` sizes that column to the
longest label *on its own page*, so the fields used to start at a different x on
every section.  Every label is given the width of the widest one in the dialog
(`QFormLayout` has no column width to set in PySide6) and every value fills its
column, so the two columns line up wherever the user looks.
* **Сбросить** puts the defaults into the widgets; they still have to be applied,
so a reset can be looked at before it is kept.  It touches the preferences only —
the recent list, the window geometry and the insert table are records the window
keeps, not choices the user made in this dialog.
* **Импорт…** stages a file and shows it («ОК» keeps it, «Отмена» drops it, and
a key this version does not know travels with the rest); **Экспорт…** applies
first and writes the whole configuration, unknown keys included, so one ini file
can be handed out to a class.
* Values live in `%LOCALAPPDATA%\PrologD\gui\gui.ini` (or `--settings FILE`), and
a value that cannot be read falls back to its default instead of taking the
window down.

The split of the two font sizes is the one place where an old file behaves
differently from a new one: `output/font_size` unset means «follow the editor»,
and the first wheel over the output panel (or a value typed in the dialog) gives
it a size of its own for good.  `Ctrl`+wheel over the editor moves the editor's
size, over the output pane its own; the toolbar's box and `Ctrl+Num±` / `Ctrl+0`
are the editor's.

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

The tabs that were open come back on the next start (`files/restore_tabs`, on by
default).  A *file* tab is remembered by its **path**, not by its text: the next
run reads the file, so a change the user refused to save is not resurrected.  An
*untitled* tab has no file to read, so its text travels with the record
(`documents.TabRecord`), up to `documents.SESSION_TEXT_BUDGET` (256 KiB) — a
buffer that does not fit is dropped whole and counted, because a tab that comes
back with half of its text is worse than one that does not come back at all, and
an empty untitled tab is not stored, being the placeholder a first file would
replace anyway.  A stored path whose file has gone is skipped and **named** in the
status bar («не найдено: …») while the rest of the session opens.  A restored
untitled tab counts as **unsaved work**, so the next close asks about it, and an
untitled tab that *is* answered with «Не сохранять» is **left out of the session
altogether** — the answer means the text is not to be seen again, so a session
written before the questions would make it a lie.  The same rule works the other
way: a tab the user saves to a file while closing is remembered as the *file* it
became, not as the unnamed buffer it was.  The session is written when the window
really closes, and only once the close happened: «Отмена» leaves the window open,
and a session written on the way out would describe a window that never closed.
Untick the box and the window opens on the welcome program instead.

`Ctrl+\` splits the editor into two panes side by side — each with its own tab
bar, both over the *same* document set, so an edit in either pane is the same
edit and re-ordering tabs in one re-orders them in the other.  The split, its
sizes and whether to restore it at all are settings (`view/split`,
`view/split_sizes`, `view/restore_split`).

A tab carries its state as a picture: `file` for a buffer that was never saved,
`file-saved` once it has a file on disk, and `file-modified` while there are
unsaved changes — saved or not.  The title bar carries the **whole path**, so two
files with one name are told apart without opening anything; the tab keeps the
short name, because a tab bar full of paths cannot be read, and the status bar
shortens what it says about a file to the last two components
(`…\lessons\lesson_04.pld`, see `documents.short_path`) — one line, where a full
path would push everything else out.  The «Последние»
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
python src/gui/tests/test_graphics.py
```

The second one is the picture: it checks the canvas on its own, and — when a build
is found — draws a program, asks for the finished bitmap and replays the very
events the same session reported, so the two rasterisers (C++ and Python) cannot
drift apart quietly.

## Protocol contract (version 10)

One JSON object per line in both directions; the interpreter writes nothing else
to stdout.  The C++ side lives in `src/cli/protocol.cpp`, the Python side in
`prologd_gui/protocol.py`.  Version 2 added the reserved names to `ready`; version
3 added stepping (`step` events and the `step` request), the `trace` events, the
`step`/`trace` flags of `load` and `query`, and the `file`/`line`/`column` fields
of `error`; version 4 adds `severity` to `error` (`error` or `warning` — a warning
is advice and never ends the run); version 5 adds the `questions` flag of `load`
(`false` loads a program without running its own `?`-statements — the editor's
margin uses it to answer one clicked query alone, task_36); version 6 adds
`format` — the formatter, which needs no engine and is answerable at any time
(task_30); version 7 makes its modes `line`, `soft` and `hard`; version 8 adds
`loaded` — the load and the program's own `?`-statements are over, which is how a
front-end knows a run *without* questions (an empty program included) finished;
version 9 adds the `limits` object of `load` (the step, depth and НАЙТИВСЕ caps of
the run, `0` for «без предела» — task_46) and answers a request whose field has
the wrong *type* with an `error` event instead of ending the session; version 10
adds the drawing: `graphics` events, one per primitive, and the `graphics` request
with `snapshot`, answered with the whole `bitmap` (task_45).
Version 1 sessions are still understood by the Python client (the table is then
empty and completion falls back to the document's own predicates).

### Requests

| Request | Meaning |
|---------|---------|
| `{"cmd":"load","path":"prog.pld"}` | load a file; `ИМПОРТ` resolves against the `-I` directories |
| `{"cmd":"load","text":"…","name":"buffer"}` | load program text (the editor buffer) |
| `{"cmd":"query","text":"?цель(X)."}` | run one statement |
| `{"cmd":"input","text":"…"}` | answer the pending `input_request` |
| `{"cmd":"step","action":"into"}` | answer the pending `step` event; `action` is `into`, `over`, `continue` or `stop` |
| `{"cmd":"format","text":"…","mode":"hard"}` | lay the text out and answer with `formatted`; `mode` is `soft` (default), `hard` or `line`, and `width`, `indent`, `unit` (`tab`/`spaces`) and `selection` say how |
| `{"cmd":"graphics","snapshot":true}` | the whole picture drawn so far, as a `bitmap` event |
| `{"cmd":"interrupt"}` | ask for a stop (see the note below) |
| `{"cmd":"quit"}` | end the session |

`load` and `query` take two optional flags: `"trace":true` turns `ТРАССА` on for
that run, and `"step":true` arms the step hook, so the run stops at its first
step point and waits for a `step` request.  `load` also takes `"questions":false`:
the program is then loaded for its clauses only, and its own `?`-statements are
not run (what the margin's single query needs).  A false `step`/`trace` flag is
left off the wire.

`load` takes `"limits"` as well (version 9): `{"maxSteps":100000,"maxDepth":10000,
"maxFindall":1000}`, each `0` for «без предела», applied *before* the load — the
program's own `?`-statements run during it, and a limit set afterwards would miss
the run it was meant for.  The engine has **no limits of its own**: a limit is
something a front-end asks for, here or on the command line, so this window sends
the three it was configured with and leaves the rest out.  A limit that fires ends
the run with a diagnostic that names the limit and its value («Превышен предел
шагов выполнения: 5000») and nothing else — the engine knows about neither a flag
nor a dialog row (ADR-020) — so the *window* answers «where do I raise it»: the
run prints «пределы: «Предел шагов» 5000 — строки в «Выполнении» настроек» before
it starts, in the words of the rows.  The `НАЙТИВСЕ` cap is a *diagnostic*, never a
silently shortened list.  The window's «Предел времени, с» is not in this object:
the deadline belongs to the front-end (a timer and the `interrupt` request), which
keeps a clock out of the solver's hot loop — and a program waiting *outside* the
solver (a `ВВОД` nobody answers) is not preempted by it at all.  A request with a
field of the wrong type — `"maxSteps":-1`, or a string where a number belongs —
is answered with an `error` event of kind `protocol`, and the session reads the
next line; before version 9 such a request took the process down.

The graphics predicates (version 10) draw **in the session**: the pixels live next
to the engine, because a `ТОЧКА(X, Y, Цвет)` read and a `ЗАКРАСКА` read cells
from inside a built-in, and a front-end on the other side of a pipe is asked
nothing in the middle of one.  Every primitive goes out as it is drawn:

```json
{"event":"graphics","op":"setPixel","x":1,"y":2,"color":3}
{"event":"graphics","op":"line","x1":0,"y1":0,"x2":60,"y2":40,"color":5}
{"event":"graphics","op":"rectangle",…}   {"event":"graphics","op":"vertical",…}
{"event":"graphics","op":"ellipse","x":320,"y":240,"rx":240,"ry":240,"color":14}
{"event":"graphics","op":"floodFill","x":30,"y":15,"color":9}
{"event":"graphics","op":"clearView","color":0}
```

Every primitive is a **cell** (`setPixel`, `floodFill`: `x`, `y`), a **segment**
(`line`, `vertical`, `horizontal`: `x1`, `y1`, `x2`, `y2`, both ends included) or a
**box** (`rectangle`: `x1`, `y1`, `x2`, `y2`, opposite corners in any order);
`ellipse` is the odd one and says so in its field names — a centre `x`, `y` and two
radii `rx`, `ry`, because `ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes its four numbers
straight through.  `clearView` carries the colour alone.  The coordinates are the
ones the program asked for, *not* the clipped ones: the engine and the canvas clip
the same way, and a picture drawn off the screen should be visible as what it was.

A window that was not open while the program drew asks for the picture instead of
starting blank:

```json
{"event":"bitmap","width":1024,"height":768,"data":"AwAAAA…"}
```

`data` is base64 of `width × height` **four-byte little-endian colour values** —
the program's own numbers, not ARGB, so a replayed picture and a snapshot are
comparable cell by cell (`protocol_smoke.py` compares them for a program that
draws one of everything, and `test_graphics.py` does it for a whole drawing).
The screen is 1024×768, it starts black, and a primitive outside it is clipped.

### Events

| Event | Meaning |
|-------|---------|
| `{"event":"ready","protocol":10,"version":"2.0.0","keywords":[…]} `| the session is up |
| `{"event":"output","text":"…"}` | program output (`ВЫВОД`, query results) |
| `{"event":"result","found":true}` | one query finished; `found` is false when nothing matched |
| `{"event":"loaded"}` | a `load` request is over: its program and its own `?`-statements ran (a `query` request is answered by its `result` alone) |
| `{"event":"input_request","kind":"line"}` | `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД` waits for an answer; `kind` is `token`, `line` or `codepoint` |
| `{"event":"step","action":"call","goal":"…","depth":2,"file":"…","line":9,"column":1}` | a step point; `action` is `call`, `exit`, `redo` or `fail`.  `goal` is absent for `exit` (the goal is the one its `call` named), and the position is absent when there is none |
| `{"event":"trace","text":"…"}` | one line of the `ТРАССА` trace |
| `{"event":"formatted","text":"…","changed":true}` | the laid-out text of a `format` request; `changed` says whether it differs from what was sent |
| `{"event":"graphics","op":"setPixel","x":1,"y":2,"color":3}` | one drawing primitive, as the program called it; `op` is one of the eight and the fields are the cell, the segment or the box it acts on |
| `{"event":"bitmap","width":1024,"height":768,"data":"…"}` | the whole screen, base64 of four-byte little-endian colour values — the answer to a `graphics` request |
| `{"event":"error","kind":"parse","severity":"warning","message":"…","file":"…","line":3,"column":5}` | diagnostic; `kind` is `parse`, `runtime` or `protocol`, `severity` is `error` or `warning` (a warning never ends the run), and the position is absent when there is none to report |
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
  of the built-in list — and one that needs the names *before* a session is up
  (completion at startup) can have them from that listing alone:
  `Keywords.from_list_lines` parses it.  Highlighting, completion and the
  shortcut cheat-sheet all read it.

* Read the interpreter's stdout line by line and never merge it with stderr; in
  protocol mode all diagnostics travel as `error` events.
* The answer to an `input_request` is one string; embedded newlines stay inside
  that string.
* `interrupt` reaches the solver at every step of its loop, and a paused step
  point answers it by ending the pause — a running query, a runaway and a read
  waiting for input all end on the request with the runtime error of the
  interrupted query.  **Остановить** asks first and terminates the process only
  when the request is not answered within `STOP_GRACE_MS` (500 ms); a polite stop
  leaves the session idle *with* its knowledge base, and stopping that idle
  session is what unloads it.
* `-i`, `-o` and `-e` are refused together with `--protocol json`: the protocol
  owns stdin and stdout.

## Roadmap

One piece of work is planned in a task file of its own (`ai/task_*.md`):

* **Interpreter options, profiles and limits** —
  `ai/task_46_interpreter_options_and_limits.md`.  The limits are done: the
  session carries them on `load` (protocol 9), the dialog has a row for each of
  them plus «Предел времени, с», and a run names the rows it goes with before it
  starts.  Still open: the path to the interpreter (still `--exe`), the working
  directory of the process, and named profiles.

The graphics window left this list in task_45: the engine keeps the pixels, the
session draws them and sends every primitive, and `graphicswindow.py` shows the
picture (section «The graphics window» above).

task_29's own list is closed: «использовать системные цвета» was done with the
three themes, and **RU/EN was dropped** (2026-10-01, ADR-021 — the window stays
Russian, and English belongs to the language, not to the interface); the settings
dialog, the live apply, the session restore, the recent files, the theme page and
the small switches are done.