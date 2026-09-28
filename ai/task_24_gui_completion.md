# task_24 — GUI: completion of keywords and predicate names

**Status:** done
**Depends on:** task_22 (editor), task_23 (keyword source)
**Milestone:** M11

## Goal

Complete what the user is typing: reserved names (with arity) and the predicate
and atom names that already occur in the open documents, so a Cyrillic program
can be written without switching the keyboard layout for every name.

## Deliverables

- [x] `prologd_gui/completion.py` — Qt-free model:
  * candidates = reserved names (task_23) + predicate names collected from the
    current document (calls, whenever the parentheses close on their own line)
    + the bare atoms + the quoted atoms, which are kept *with* their quotes
    (`'Иван Петров'` matches the prefix `'Ив` and is inserted quoted).  An
    `ИМПОРТ`ed file is not followed: that needs the loader, and the task is to
    help while typing;
  * prefix matching that is code-point based and case-sensitive by default
    (`член` matches, `Член` does not, unless the option is off);
  * ranking: exact case > matching at all > the same alphabet as the prefix >
    reserved names > predicates, then alphabetical;
  * the popup shows `НАЙТИВСЁ/3` and inserts only `НАЙТИВСЁ`;
  * `is_code_position()` says whether the caret is inside a comment, a string, a
    quoted atom or a `#…#` block (an odd number of `#` before the caret), and
    `word_before()` reads the word being typed.
- [x] Editor integration (`editor.py`): `QCompleter` with
      `QCompleter.PopupCompletion`, driven from `keyPressEvent` the way the
      reference `Editor.cpp` did it — but:
  * no completion inside a comment, a string or a `#expr#` block (decided by the
    task_22 tokenizer, not by a second set of rules);
  * manual trigger `Ctrl+Space`, automatic after N letters
    (`editor/auto_complete_after`, default 2);
  * `Enter`/`Tab` accept, `Esc` closes, `Shift+Enter` keeps the newline;
  * the arrow keys still move the caret: `Left`/`Right`/`Home`/`End` close the
    popup and do their job, `Up`/`Down` walk the list.
- [x] The popup takes the application palette, which is the forced light Fusion
      one from task_22, so its labels stay readable next to the Cyrillic font;
      its width comes from `sizeHintForColumn`, i.e. from the font actually in
      use rather than from a constant.
- [x] Tests: `src/gui/tests/test_completion.py` — Qt-free checks of the
      collection, the arity of a call with a list argument, the ranking (case,
      alphabet, predicates before atoms) and the suppression; then offscreen
      widget checks driving real key events: two letters open the popup, `Enter`
      takes the name and inserts no newline, `Esc` closes without touching the
      text, `Ctrl+Space` opens on demand, arrows move the caret, and typing in a
      comment or a string offers nothing.

## Design notes

* The reference implementation single-shot `QCompleter` on the whole word under
  the cursor and inserted the completion by replacing the *left* part; it also
  completed inside comments.  Collecting the document's own predicate names was
  not done at all, which is the part that actually saves typing in Prolog.
* Do not ask the interpreter for the document's predicates: the file may be
  mid-edit and unparsable.  A cheap line scan in Python is enough and cannot
  fail.
* Keep the candidate list cached per document and invalidated on
  `textChanged` with a small delay, or the popup will stutter on large files.
  Done without `textChanged`: the list is rebuilt inside `update()` only when the
  text it is handed differs from the last one, which puts the cost on the
  keystroke that actually triggers the popup and needs no timer.  A test counts
  the scans to keep it that way.
* **A list that arrives pre-filtered is not highlighted by Qt.**  `complete()`
  highlights a row only when the completer filtered the model itself; with the
  ranking done here, `Enter` on the fresh popup did nothing at all — the key fell
  through and inserted a newline, which looked like "completion is broken".  The
  first row is now selected explicitly.
* **Commas inside a list are not argument separators.**  `член(2, [1, 2, 3])` is
  arity 2, and counting parentheses alone offered it as `член/4` — a wrong arity
  in the popup is worse than none, so `[`/`]` depth is tracked as well.
* **An upper-case first letter makes a variable here.**  `Член(1)` is a variable
  token, not a call: there is no way to write the *same* name in two cases as a
  predicate, so the case rule mostly shows up through quoted atoms.

## Acceptance

Typing `НАЙ` offers `НАЙТИВСЁ/3`; typing `чле` after defining `член/2` offers
`член`; completion does not appear inside `% комментарий`, `"строка"` or
`#выражение#`; `Ctrl+Space` opens the popup on demand.
