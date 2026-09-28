# task_22 — GUI: code editor (highlighting, line numbers, editing)

**Status:** in progress — the tokenizer is in (`tokens.py`, tested); the
highlighter, the line numbers, the editing commands and the font live below.
**Depends on:** task_21 (skeleton), task_23 (keyword source)
**Milestone:** M11

## Goal

Turn the placeholder `QPlainTextEdit` of the skeleton into a code editor: syntax
highlighting that distinguishes Cyrillic from Latin identifiers, line numbers,
font control, the usual editing commands and block comment/uncomment.

Everything the user types must survive a round trip: UTF-8 in, UTF-8 out, no BOM,
no mangled line endings, no lost trailing newline.

## Deliverables

- [x] `prologd_gui/tokens.py` — Qt-free tokenizer for highlighting: comment,
      string, quoted atom, integer, float, `#expr#` block, built-in name,
      variable (`X`, `_X`, `_`), atom, punctuation, plus a
      `latin`/`cyrillic` attribute on every identifier.
- [ ] `prologd_gui/highlighter.py` — `QSyntaxHighlighter` that maps token kinds
      to formats from the settings, using `tokens.py`.  Highlighting must not
      run regular expressions over the whole document per keystroke:
      `highlightBlock` works line by line and carries only the multi-line state
      (inside a `"…"` string, inside a `#…#` expression).
- [ ] `prologd_gui/editor.py` — `CodeEditor(QPlainTextEdit)`:
  * line number area with the current line emphasised;
  * an error marker in the margin and a red background on the line reported by
    the last diagnostic (filled in by task_28);
  * `Ctrl` + wheel changes the font size (`Ctrl+0` resets it), bounded 6…72;
  * monospaced font family from the settings, Cyrillic-capable (Cascadia Mono
    covers it; fall back to the closest match and say so in the status bar);
  * selection, block indent/outdent (`Tab`/`Shift+Tab` on a selection);
  * auto-indent on `Enter` inside a clause body (continuation indent), and no
    auto-indent after a clause terminator.
- [ ] `comment()` / `uncomment()` on the current selection or line (Ctrl+K /
      Ctrl+U), inserting and removing a leading `%` per line, as a single undo
      step.  Unlike the reference implementation, the `%` is inserted at the
      first non-blank column, never in the middle of a line, and uncomment
      removes only the first `%` of the leading run.
- [ ] Standard editing actions wired to the editor's undo stack: undo, redo,
      cut, copy, paste, delete, select all, duplicate line, and find/replace
      (task_26 puts them in the menu, task_25 keeps them per document).
- [ ] UTF-8 discipline: read as UTF-8 (`errors="strict"`, report a replacement
      prompt otherwise), write UTF-8 without BOM, keep the dominant line ending
      of the loaded file (LF by default), preserve a trailing newline if the
      file had one.
- [ ] Colour scheme (defaults, all overridable in task_29):
      built-in names dark blue bold; **Latin identifiers `#800000`**, **Cyrillic
      identifiers `#7B1FA2`** — the colours the user asked for to tell the two
      alphabets apart; numbers `#505000`; comments dark green; `#expr#` blocks
      and quoted atoms/strings a distinct hue; query lines (`?…`) blue `#0A22D6`
      like the reference GUI.
- [ ] Tests: `src/gui/tests/test_tokens.py` (Qt-free, table of tricky lines),
      `src/gui/tests/test_editor.py` (offscreen, needs PySide6, skipped when it
      is not installed) checking line-number width, comment/uncomment round
      trip and that highlighting assigns the expected format to a Cyrillic and
      a Latin identifier.

## Design notes

* **Two colour families for identifiers.** The reference GUI only coloured
  `[a-zA-Z]+` dark red and left Cyrillic alone.  Here both alphabets get their
  own colour, so `член` and `member` in one file are told apart at a glance.
  Cyrillic built-ins keep the built-in colour, which wins over the identifier
  colour.
* **The tokenizer is not authoritative.** The interpreter owns the lexical
  rules; `tokens.py` mirrors them for display only and must never influence
  execution.  Keep it small and table-driven so the two stay comparable, and
  cover every rule with a test line.  The keyword list itself comes from the
  interpreter (task_23), not from a copy.
* What the tests already found: whitespace is not a token (nothing to colour,
  and the sweep asserts the stronger property that every other character is
  inside exactly one token), and no state is carried between lines — neither a
  string nor `#…#` may span lines in PrologD, so a line-local pass is enough and
  an unterminated string is simply coloured to the end of its own line.
* The reference `Highlighter.cpp` builds one `QRegularExpression` per keyword —
  about 50 patterns applied to every line, plus a keyword list duplicated in
  `MainWindow.cpp`.  A single tokenizer pass is both faster and the only way to
  tell a keyword from an identical-looking atom inside a string.
* Comments start with `%` and there is no block comment, so highlighting is
  line-local except for strings and `#…#` blocks.

## Acceptance

A Cyrillic program with Latin identifiers, comments, strings, `#expr#` blocks
and queries highlights correctly, Latin and Cyrillic names are visibly
different colours, `Ctrl+K`/`Ctrl+U` round-trip a multi-line selection, `Ctrl`+
wheel changes the font size, and saving the buffer writes byte-identical UTF-8
for an unchanged document.
