# task_25 — GUI: tabs, files, untitled buffers, save prompts

**Status:** in progress — tabs, files, prompts and text I/O are in; the split
editor (the second half) is next.
**Depends on:** task_22
**Milestone:** M11

## Goal

More than one program open at a time, the ability to start from nothing, and no
lost work: the front-end must ask before discarding a modified buffer and must
keep track of which file each tab shows.

## Deliverables

- [x] `prologd_gui/documents.py` — Qt-free document model:
  * `name` (`"Без имени"`, `"Без имени 2"`, … for new buffers), `path` or
    `None`, `text`, `modified`, `eol` (`\n`/`\r\n`), `encoding`;
  * `tab_title()` — `имя` plus `*` when modified;
  * `window_title()` — `имя — PrologD`, `*имя — PrologD` when modified;
  * file I/O: `from_file` reads (dropping a byte-order mark, reporting text that
    is not UTF-8), `save` writes the encoding and the line ending it came with.
- [x] Tab bar (`QTabWidget`) over the editors: close button per tab, `Ctrl+W`
      closes the current tab, `Ctrl+Tab`/`Ctrl+Shift+Tab` cycle, the tab shows
      the modified marker, and a double click on the tab bar starts a new file.
      Dragging a tab is allowed and the buffer list follows it (`tabMoved`).
- [x] File actions: **Новый** (`Ctrl+N`), **Открыть…** (`Ctrl+O`), **Сохранить**
      (`Ctrl+S`), **Сохранить как…** (`Ctrl+Shift+S`), **Сохранить все**,
      **Закрыть** (`Ctrl+W`), **Закрыть все**, **Выход** (`Ctrl+Q`, and `Alt+F4`
      through `closeEvent`).  Only the first three have toolbar buttons until
      task_26 builds the menus.
- [x] Modified-buffer prompts: closing a tab, closing the window and `Выход` ask
      **Сохранить / Не сохранять / Отмена** per modified buffer.
      **Changed by the user after hand-testing:** `close_all()` walks through the
      tabs instead of asking about all of them first — the tab is made current,
      the question is asked about *that* file, and it is closed as soon as the
      answer is given.  Asking everything first kept the buffers open but left the
      user guessing which file each box was about, which is the worse failure.
      Cancelling therefore stops where it happened.  `Enter` lands on **Отмена**
      either way, and a save that fails keeps the buffer.
- [x] New/recent: the last opened directory is remembered and used by both
      dialogs, the ten most recent files are stored (the menu is task_26), a
      program dropped **anywhere on the window** (tab bar, editor, output pane)
      opens in a new tab, and **Перечитать с диска** (`Ctrl+Shift+R`) reloads the
      current tab after asking about its changes.  The drop had to be taken away
      from the text panes: a `QPlainTextEdit` accepts a file drop and inserts the
      file's *text*, so the window never saw it.
- [x] `doc/gui.typ` — the user-facing paper for the interface: keys, tabs and
      files, prompts and encodings, the editor, completion, running, the mouse,
      settings, and a section listing what is *not* implemented yet.  Not in the
      original deliverable list; the user asked for it, and a feature nobody can
      look up is half a feature.
- [x] Running uses the file's own path: a saved tab is loaded with
      `{"cmd":"load","path":…}` so `ИМПОРТ` resolves relative to *that* file; an
      untitled tab is loaded as text and `ИМПОРТ` resolves against the working
      directory and the `-I` directories.  The status bar says which case is
      running, so a failing import is not a mystery.
- [x] Text I/O: UTF-8, the `eol` and the `encoding` of the loaded file preserved
      on save, a file that is not valid UTF-8 asks which encoding to use (and a
      character the file's own encoding cannot hold offers UTF-8 instead of
      writing replacement characters).
- [ ] **Разделить редактор** (`Ctrl+\`): the window holds one or two
      **independent** editor panes side by side, each with its own tab bar, so
      the left pane can show `lesson_1.pld` while the right shows `lesson_4.pld`.
      The current document is *also* shown in the new pane (the usual editor
      behaviour) and **Объединить редакторы** closes it again.  The active pane
      owns the run/format/comment actions and the status bar says which one it
      is.
- [ ] Implementation of the split: the two views share one `QTextDocument` per
      document (`setDocument`), so an edit in one pane appears in the other for
      free — never keep two copies of the text.
- [ ] The split state (one or two panes, which document in which pane, splitter
      position and orientation) is restored on start when "восстанавливать
      вкладки" is on.
- [ ] **Открыть не запускает программу.**  Opening fills the editor and nothing
      else.  `load` *adds* clauses to the live interpreter (that is what
      `ИМПОРТ` needs), so an open into a session that had already run something
      duplicated the program — and with duplicated recursive clauses every
      solution multiplies: the factorial example answered 64 times instead of
      once, which reads as an endless loop.  Running stays F5, and a run starts a
      fresh session (task_28).
- [ ] Running uses the file: a saved, unmodified buffer is loaded **by path**,
      so `ИМПОРТ` resolves against the file's own directory and diagnostics name
      it; an edited or untitled buffer is loaded as text whose `name` is the file
      path when there is one (see task_28 for the table).
- [ ] Tests: `src/gui/tests/test_documents.py` (Qt-free) for titles, the
      untitled counter, `modified` bookkeeping, eol detection and recent-file
      pruning; the tab/prompt behaviour goes into the manual checklist below.
      `test_documents.py` is written: line endings, byte-order marks, cp1251
      round trips, the untitled counter and the recent list.  The tab, save and
      prompt behaviour is in `test_window.py` offscreen, where the modal box is
      replaced by a one-line `_ask_save` stub — the decision is what matters, and
      a real `QMessageBox` cannot be driven headless.

## Design notes

The layout is held together by one rule: **the buffer list and the tab bar are
the same order**.  `Buffer` (in `buffers.py`) owns a model, one
`QTextDocument` and one editor; the window keeps a list of them and uses the tab
index everywhere.  Dragging a tab reorders the widget only, so `tabMoved`
re-orders the list, and a second pane (the remaining half of this task) will add
a second *view* of the same `QTextDocument` rather than a second copy of the
text.

* **`QPlainTextEdit.setDocument` needs `QPlainTextDocumentLayout`.**  Handing
  it a plain `QTextDocument` makes Qt print one warning and *silently* leave the
  pane empty while the document does hold the text — `editor.toPlainText()` came
  back as `''` with 88 characters in the document.  The layout is set before the
  document is handed over.
* A single empty, unmodified buffer is treated as a placeholder: the first file
  that is opened takes its place instead of leaving an empty tab behind.  The
  welcome program is not empty, so it stays until the user closes it — a rule
  that is one line of code and one test, rather than "the first tab is always
  reused".

* The reference `MainWindow.cpp` kept one `QTabWidget` of `Editor` widgets and
  tracked the file name per editor — a structure worth keeping, but the
  modified flag and the prompt logic were incomplete (closing the window never
  asked).  `QTextDocument.isModified()` plus an explicit save prompt on
  `QCloseEvent` is the whole fix.
* "Не сохранять" must be the *default-safe* option being last, not first: the
  destructive button should not sit under an accidental `Enter`.
* Splitting is a *view* feature: the `Document` objects are shared, only the
  views are new.  A document shown in both panes keeps one text and one
  modified flag (that is why the two editors share a `QTextDocument`), and a
  split pane does not change how a buffer is saved.

## Acceptance

Two files and one untitled buffer can be open at once, in one or two panes; an
edit in one tab marks it `*`; closing it asks before discarding; a saved file
runs with its own directory in `ИМПОРТ`'s search path; a `.pld` file dropped on
the window opens in a new tab.
