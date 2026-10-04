# task_58 — the window: `Shift+Del`, word occurrences, the loading line, menus, "About"

**Status:** done (2026-10-04) — all five items are in the window, the icons were closed
first (`test_icons.py` went from red to green), and the eight corrections the user asked
for after reviewing the round are folded in (§6).  User answers to the two questions:
the alignment in "About" is done with **spaces** (no rich text), and "Delete line" is an
item of the **Edit** menu.
**Depends on:** task_48 (the action table and the toolbar), task_50 (the console under
the goal line, the "knowledge base loaded" line), task_36 (query markers in the margin),
task_46 (`questions`/`printQuestions`), task_29 (the settings dialog and the two
Execution switches), task_33 (the search bar — it suppresses occurrence highlighting)
**Milestone:** post-M10

## Goal

Five things, all about the window reading better:

1. **`Shift+Del` deletes the line** — under the cursor, or every line the selection
   touches (§1).
2. **Other occurrences of the selected word are visible**: the colour is pale in the
   light theme and almost the page colour in the dark one, and the dark theme is what a
   user with a dark desktop gets ("system" appearance) (§2).
3. **A click on a question marker in the margin writes
   `--- база знаний загружена (N мс) ---` into "System"**, as `F5` does (§3).
4. **The menu and the toolbar get the order the user asked for** (§4).
5. **"About" names the program and the people** (§5).

## §1. `Shift+Del` — delete the line

**Where.** The commands live in `actions.py`, the keys in the editor
(`editor.py::CodeEditor.keyPressEvent`, ~line 965, where the `_insert_shortcut` and the
completion keys are already decoded).  The key is free: `delete` ("Удалить") has `Del`,
`select_all` has `Ctrl+A`.

**What to do.** A new entry beside `delete` —
`Action("delete_line", "Удалить строку", None, ("Shift+Del",))` — and the same entry in
`MENUS` under Edit, right after `delete` (the menu is the only place where the key can
be discovered).  `editor.py` gets a method that removes the lines the cursor or the
selection touches in **one** `beginEditBlock`/`endEditBlock`, so one `Ctrl+Z` brings it
all back; `window.py` gets `_delete_line` in the handler table (`_handler_for`, next to
`"delete": self._delete`), or calls the editor method directly.

**Checks.** `src/gui/tests/test_editor.py` (editor keys are tested there already): the
cursor in the middle — the line is gone and the cursor sits at the start of the line
that moved up; a two-line selection — both are gone; the last line — one empty line
remains; one `Ctrl+Z` restores the text whole; `Shift+Del` leaves the other lines alone.
Plus a row in the "Editor keys" table of `src/gui/README.md` and in `doc/gui.typ` §4.

## §2. Occurrences of the selected word — make them visible

**Where.** The mechanism exists: `editor.py::_refresh_extra_selections` (~545) paints
the occurrences found by `search.matches(text, token, match_case=True)` in
`self._palette.occurrence`; the colours are in `theme.py`:

| palette | page | current line | occurrence | search: match / current |
|---|---|---|---|---|
| `light` | `#ffffff` | `#f4f6f9` | **`#e8ecf5`** | `#ffe9a8` / `#ffc14d` |
| `dark` | `#1e1e1e` | `#26262b` | **`#2d3038`** | `#5c4a00` / `#8a6d1f` |

The dark theme comes both from choosing "dark" and from "system" on a dark desktop
(`appearance.theme_palette` → `theme.DARK` when `system_is_dark()`), and `#2d3038` on
`#1e1e1e` is 15 lightness units — so "dim" is worst exactly there.

**What to do.** Raise the saturation of both colours while keeping occurrences
**quieter** than the search bar: an occurrence is a hint ("this name is here too"), a
search match is the answer to a question, and one colour must not mean two things.
The starting point was `#cfe0f7` (light) and `#3a4a63` (dark) — both clearly above the
page and below `search_current`; the numbers were then chosen by **looking at the
window** in both themes (`python src/gui/main.py`) and kept (§6.2).

**Checks.** `src/gui/tests/test_appearance.py` — a new case that measures not the text
contrast (as `Palette.readable_pairs` does) but the difference between the band colour
and its own page: in each palette `occurrence` must differ from `background` and from
`current_line` by at least a threshold (say 25 lightness units, `QColor.lightness()`),
otherwise "dim" comes back silently.  `test_highlighter.py` additionally pins that
occurrences are painted with `palette.occurrence`.  Documentation: one sentence about
occurrence highlighting in `doc/gui.typ` §4 ("Editor") — nothing says it today — and in
the README's editor section.

## §3. A click on a question marker — the loading line in "System"

**Where.** The margin click is `editor.py::margin_pressed` → `queryRequested(statement)`
→ `window.py::_on_query_requested` (~1734).  The loading line is printed by
`window.py::_on_loaded` (~3175):

```python
if self._awaiting_query or self._stopping:
    # A question still has to answer (the margin's click), or a stop of
    # our own is in flight; both conclude with their own event.
    return
...
if not self._failed_in_load:
    self._append_note(f"--- база знаний загружена ({self._run_clock.elapsed()} мс) ---\n")
```

`_on_query_requested` sets `self._awaiting_query = True` **before** `loaded` arrives, so
a quiet load (`run_program(questions=False)`) is exactly what suppresses the line: `F5`
has it, the marker click does not.

**What to do.** Print the line in this case too — before the early `return`, under the
same `not self._failed_in_load` condition; `_stopping` keeps returning early (a run is
being stopped, not a base loaded).  It is printed on `loaded`, not with the answer: the
line says "the base is loaded", which is true already then, and the panel order comes
out as with `F5` (line, then answer).  A failed load prints no line, as with `F5`.

**Checks.** `src/gui/tests/test_window.py`: in the marker test (click →
`_on_query_requested`) require that "System" contains `--- база знаний загружена (`
and that it stands *before* the answer; separately, that a failed load prints no line.

## §4. The menu and the toolbar

**Where.** `actions.py::MENUS` and `actions.py::TOOLBAR`; the handlers are
`window.py::_handler_for` (~590).

**What to do.**

* **Help:** `help_doc` ("Руководство пользователя") moves one row up, under
  `reference`, before the separator:
  `("reference", "help_doc", SEPARATOR, "shortcuts", SEPARATOR, "help_gui", "about")`.
* **Run:** `save_before_run` **leaves the menu**, and two checkable items take its
  place — `run_questions` ("Выполнять вопросы при запуске") and `print_questions`
  ("Печатать вопросы при запуске") — next to `stop`, before the separator, with
  `graphics` after them.  They are bound to the existing settings
  (`execution/run_questions`, `execution/print_questions` in `settings.py`, where the
  labels and the "Execution" section already exist), with handlers modelled on
  `_toggle_save_before_run`.  The tick follows the setting, not the other way round:
  the setting lives in a file and is visible in the dialog, so the menu item is a
  second way in, not a copy of it.
* **Toolbar:** `help_doc` goes away, and after the corrections of §6 the font-size box
  goes with it too and "Clear output" moves to the Run menu — so the right end of the
  toolbar is `graphics | settings`.
* No key is claimed twice: `print_questions` has none, `run_questions` has none
  (`Ctrl+R` is already `run`, which is `F5`).

**Checks.** `test_window.py::test_the_menus_come_from_the_action_table` compares the
menu with the table automatically, so the meaning needs a case of its own: "a menu
switch changes the setting and shows it" (click `run_questions`, read
`settings.run_questions` and the tick, then the other way round — otherwise the item
could show one thing while the file keeps another).
`test_the_toolbar_reuses_the_actions` — add that `help_doc` is not on the toolbar.
Documentation: `doc/gui.typ` §9.1 (the menu rows) and §9.2 (the toolbar paragraph),
`src/gui/README.md` (the same section in prose).

## §5. "About" and the icons

**Where.** `window.py::about_text()` (~1044) and `window.py::_about()`; the icons are
`src/gui/assets/` + `assets.py::MISSING` + `actions.py`.

**The text.** `about_text()` returned three lines: the title "PrologD 2.0 — графическая
оболочка (PySide6).", "Интерпретатор: …" and two lines the user asked to drop
("Панелей редактора: N", "Настройки: путь").  The new text is

```
Графическая оболочка Пролог-Д 2.0
Интерпретатор: PrologD 2.x.y (дата сборки)

Эту реализацию Пролога-Д разработали АБВГД:
Алексеев Михаил Николаевич   – прораб,
Балдин Виктор Михайлович     – топкодер до 2008,
Воронин Алексей Вячеславович – топкодер с 2017,
Григорьев Сергей Георгиевич  – идеолог,
Данил Адисонович Ахмеров     – топкодер с 2023.
```

The "Интерпретатор: …" line stays: it says which interpreter the window talks to, and
it is the only live value in this dialog.  "АБВГД" are the first letters of the five
surnames, so the order of the lines must not change.  The column is aligned with
**spaces** against the longest name ("Воронин Алексей Вячеславович"): `QMessageBox`
uses a proportional font, so an exact column cannot be had with spaces — this is an
honest attempt to align "by eye", as in the previous window.  An exact column would
mean `box.setTextFormat(Qt.TextFormat.RichText)` with `<pre>…</pre>` around the list
(a monospaced block), but then `about_text()` is no longer plain text and the test must
know that.  The separator is the short dash `–` (one character, §6.5).

**The icons.** The user redrew and added files, so the table became:

| was in the code | became | where |
|---|---|---|
| `view-output-right` | `view-output` | `Action("output", …)` |
| `view-output-bottom` | `view-output-change-orient` | `Action("split_orientation", …)` |
| — | `view-unite-editor` | `Action("merge", "Объединить редакторы")` — the icon was `None` |
| — | `select-all` | `Action("select_all", "Выделить всё")` — the icon was `None` |
| `view-split-editor` | the file is drawn | `MISSING` must let it go |
| `edit-clear` | removed with the file | "Clear output" is text only (§6.8) |

After that `assets.MISSING` is `{execution-restart, view-theme}` — two names: the
restart picture nothing refers to, and the icon of the "Appearance" submenu, which is
still words.  The counts in `doc/gui.typ` §9.3 and the README are recounted after
§6.8: **48 names, 47 drawn, one waiting** (`view-theme`).

**Checks.** `test_icons.py` — green (it was red with
`The file exists, so it must leave MISSING: ['view-split-editor']`), and its output
prints the new numbers.  `test_window.py` for "About": `about_text()` contains
"Графическая оболочка Пролог-Д 2.0", five surnames with aligned dashes, and neither
"Панелей редактора" nor a settings path (both lines were dropped on purpose).

## §6. Corrections after the first look (2026-10-03)

The user reviewed the round and corrected eight things.  The first one was a real
defect.

1. **`Shift+Del` worked from the menu but not in the editor.**  The cause is not our
   code: `QTextControl` claims `Shift+Del` as the *platform* Cut sequence
   (`QKeySequence::Cut` on Windows is `Ctrl+X` **and** `Shift+Del`), so the `QAction`
   with its own `Shift+Del` never reached the editor, while the key itself arrived in
   `keyPressEvent` — and without a selection did nothing.  Fixed where the key ends up:
   `CodeEditor.keyPressEvent` recognises `Key_Delete + ShiftModifier` and calls
   `delete_lines()`, the same command as the menu item.  The lesson went into the test:
   it now **presses the key** (`QTest.keyClick`) instead of calling the method, otherwise
   it is green with a broken key — which is what happened in the first pass.
2. **Occurrences are visible** — confirmed by the user, the colours stay
   (`#cfe0f7` / `#3a4a63`).
3. **The font-size box left the toolbar** — together with the field itself:
   `_build_font_size_box`/`_show_font_size`/`_on_font_size_chosen`/
   `_on_font_size_typed` and the `FONT_SIZE` marker in `actions.py` are gone.  The scale
   is changed by `Ctrl`+wheel and the three View commands, and the exact value is the
   "Размер шрифта" row of the settings ("Editor"); `test_two_font_sizes_and_one_wheel`
   now goes through the commands.  Under that a second, unrelated defect showed up:
   `_on_zoom_changed` **wrote** the `output/font_size` key while the output pane still
   followed the editor, so the output "detached" from the editor on the first zoom —
   although it promised to follow until the size was set for the *output*.  The old test
   could not see it: it changed the size once.  Now following applies the size without
   writing the key, and the check runs nine steps (the output follows the editor) before
   detaching it with the wheel over the pane.
4. **"Clear output" moved from the toolbar into the Run menu**, above "Graphics window":
   both commands are about what is visible on the screen, not about the run itself.
   After that the right end of the toolbar is "Настройки…".
5. **In "About" the `--` became `–`** (an en dash, one character): the column is still
   aligned with spaces, and the test compares the position of `–`.
6. The docstring of `actions.py` gained the ellipsis rule the user asked about: **"…"
   means "the command asks something first"** (a file name, a folder, a set of settings,
   a search string) and is not put on a command that acts at once, even if it opens a
   window of its own ("Руководство пользователя", "О программе", "Графическое окно").
7. **`Shift+Del` copies what it deletes.**  The key took the platform meaning ("cut"),
   and cut text has to paste back: `delete_lines` puts the removed lines on the clipboard
   (`QApplication.clipboard().setText`), and the test compares that with `"второй\n"`.
   Until it did, the behaviour was "half a cut" — the text vanished for good unless
   `Ctrl+Z` was pressed.
8. **The `edit-clear` icon was removed together with its file.**  The picture did not
   read as "clear" and the user asked for it to go entirely; the menu item stays
   text-only.  That is where the counts of §5 come from.

## Decisions (recorded after the work)

1. **Icons first.**  They were the only broken place, and the fix was exactly two files:
   four names in `actions.py` and a `MISSING` without three lines.  It also turned out
   that `view-output-right`/`view-output-bottom` had not simply vanished — nobody would
   have complained: the names stayed in `MISSING`, so the audit was silent while "Панель
   вывода" and "Сменить ориентацию сплита" sat without pictures.  The same lesson as
   with `MISSING` in general: the list documents an *expectation*, and a name in it is
   never checked against "but the file exists now".
2. **`Shift+Del` is a command, not a key in the editor.**  Every key in the window is a
   `QAction` from the table, so the key gets a menu item, a tooltip and a row in the
   README table for free.  No icon: `edit-del` belongs to "Удалить".
3. **The last line empties rather than disappears.**  `QTextDocument` cannot be left
   without a block, so deleting the last line is erasing its text; the other editors with
   this key behave the same.  A selection that stops at the first column of a line does
   **not** take that line.
4. **The occurrence colour stays a band of the editor, not a setting.**  The
   "Highlighting" dialog changes only the `theme.Theme` colours (syntax roles), and
   `occurrence` is a band like `current_line` and `search_match`; a new colour is a new
   `default`, and a user who dislikes it is a separate conversation.
5. **The loading line is printed on `loaded`, not on the answer**, and a failed load
   prints none — as with `F5`.  There is nowhere to print it a second time: the early
   `return` in `_on_loaded` now does it itself.
6. **The two menu switches are the same settings, not copies of them.**  The item writes
   `settings.run_questions`/`print_questions`, and `_sync_actions` puts the value back
   into the tick; the settings dialog reads the same file.  `save_before_run` left the
   menu and lives only in the dialog — a user decision, and a sensible one: "save before
   running" is usually decided once, while the two question switches are touched while
   working.
7. **What the user gave verbatim stays verbatim**: the five surnames, their order and
   their spellings (only the alignment was ours to choose).  Rewriting someone's name in
   a shorter form is not a formatting decision.

## What the round found

* **`test_icons.py` went red on one name and did not notice two lost pictures**: a name
  in `MISSING` reads as "there is no file, and that is recorded", so a renamed icon sits
  in the same string and the audit stays silent while the menu item already has no
  picture.  The test catches a *typo*, not a *rename* (Notes below).
* **In the README a menu item was named differently from the setting**: "Выводить вопросы
  при запуске" against "Печатать вопросы при запуске" in `settings.py`.  The label comes
  from the setting, so the documents now use one name.
* **The menu tick and the setting are linked one way automatically**: `_sync_actions`
  runs at start and after a state change, so a test of "menu → setting" and
  "setting → menu" covers both sides.
* **Space alignment is checkable** even without the modal window: in `about_text()` the
  dash of all five list lines sits at the same index, and the test compares that
  (`{line.index("–")}` is a single number).

## What must not change

* `Del` and `Ctrl+A` as they were; `Shift+Del` takes nothing from them.
* Occurrence highlighting is still **suppressed** while the search bar is open, and still
  does not fire on long documents (`OCCURRENCE_LIMIT`).
* The "база знаний загружена" line of `F5` is printed as it was, once per run; a quiet
  load (a marker click) does not start printing answers.
* `save_before_run` still works from the dialog, and `run_program` reads it as before.
* `doc/gui.typ` §9.3 stays a list of *what is drawn and what is not*: when an icon
  appears it leaves both `MISSING` and the prose, otherwise the list lies.

## Verification

1. `cmake --build build/windows-msvc --config Release` and
   `ctest --test-dir build/windows-msvc -C Release` — the C++ suite must not move (the
   new cases are in `test_*.py`; the GUI suites are run by hand).
2. The GUI suites: `PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`, a loop over
   `src/gui/tests/test_*.py` (except `_debug_*`) and `protocol_smoke.py` — all green;
   `test_icons.py` goes **from red to green**.
3. By eye in the window: `Shift+Del` in the middle of a program and on the last line;
   occurrences in the light and the dark theme; a marker click — the line in "System"
   before the answer; the Help and Run menus; the right end of the toolbar; the "About"
   box (it is modal and no autotest opens it, so it is a human's job).
4. `cmake --build build/windows-msvc --config Release --target docs`, then a look at §4
   and §9.1–9.3 of the window manual.
5. Records: `ai/status.md` (the task row and the round's paragraph) and this file
   ("Decisions", "What the round found").

## Notes

- `test_icons.py` catches a **typo** but not a **rename**; the second case is visible
  only by eye, so `MISSING` is cleaned by hand when icons are renamed.
- Requests 2 and 3 are about one thing: the window must say what happened, and the
  highlight must show what the reader is looking for by eye.  Both got a check that
  measures something (the lightness of the band) or demands content of the panel — so
  that "dim" and "silent" do not come back.
- Texts of names and the order of surnames are the user's data; they are quoted here
  verbatim, and it is their *formatting* (not the alignment) that is not ours to change.
