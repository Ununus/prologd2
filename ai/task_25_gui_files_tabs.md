# task_25 — GUI: tabs, files, untitled buffers, save prompts

**Status:** not started
**Depends on:** task_22
**Milestone:** M11

## Goal

More than one program open at a time, the ability to start from nothing, and no
lost work: the front-end must ask before discarding a modified buffer and must
keep track of which file each tab shows.

## Deliverables

- [ ] `prologd_gui/documents.py` — Qt-free document model:
  * `name` (`"Без имени"`, `"Без имени 2"`, … for new buffers), `path` or
    `None`, `text`, `modified`, `eol` (`\n`/`\r\n`), `undo_available`;
  * `tab_title()` — `имя` plus `*` when modified;
  * `window_title()` — `имя — PrologD`, `*имя — PrologD` when modified.
- [ ] Tab bar (`QTabWidget`) over the editors: close button per tab, `Ctrl+W`
      closes the current tab, `Ctrl+Tab`/`Ctrl+Shift+Tab` cycle, the tab shows
      the modified marker, and a double click on the tab bar starts a new file.
- [ ] File actions: **Новый** (`Ctrl+N`), **Открыть…** (`Ctrl+O`), **Сохранить**
      (`Ctrl+S`), **Сохранить как…** (`Ctrl+Shift+S`), **Сохранить все**,
      **Закрыть** (`Ctrl+W`), **Закрыть все**, **Выход** (`Alt+F4`) — the same
      set the reference GUI had.
- [ ] Modified-buffer prompts: closing a tab, closing the window and `Выход` ask
      **Сохранить / Не сохранять / Отмена** per modified buffer; cancelling
      aborts the whole close, it must not close the tabs processed earlier.
- [ ] New/recent: last opened directory remembered, recent files list (10
      entries, missing files pruned when the menu opens), drag & drop of `.pld`
      files onto the window, **Перечитать с диска** for the current tab.
- [ ] Running uses the file's own path: a saved tab is loaded with
      `{"cmd":"load","path":…}` so `ИМПОРТ` resolves relative to *that* file; an
      untitled tab is loaded as text and `ИМПОРТ` resolves against the working
      directory and the `-I` directories.  The window says which case is active
      (so a failing import is not a mystery).
- [ ] Text I/O: UTF-8, the `eol` of the loaded file preserved on save, a file
      that is not valid UTF-8 asks the user to pick an encoding instead of
      silently replacing bytes.
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
- [ ] Tests: `src/gui/tests/test_documents.py` (Qt-free) for titles, the
      untitled counter, `modified` bookkeeping, eol detection and recent-file
      pruning; the tab/prompt behaviour goes into the manual checklist below.

## Design notes

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
