# task_24 — GUI: completion of keywords and predicate names

**Status:** not started
**Depends on:** task_22 (editor), task_23 (keyword source)
**Milestone:** M11

## Goal

Complete what the user is typing: reserved names (with arity) and the predicate
and atom names that already occur in the open documents, so a Cyrillic program
can be written without switching the keyboard layout for every name.

## Deliverables

- [ ] `prologd_gui/completion.py` — Qt-free model:
  * candidates = reserved names (task_23) + predicate names collected from the
    current document (heads of clauses, `ДОБ`-style goals, `ИМПОРТ`ed files
    are *not* followed) + the quotes: a quoted Cyrillic atom is offered with
    its quotes;
  * prefix matching that is code-point based (`член` matches `член`, `Член`
    does not, unless the case-insensitive option is on);
  * ranking: exact case > prefix in the same alphabet > everything else, with
    built-ins before user names at equal rank;
  * the popup shows `НАЙТИВСЁ/3`, inserting only the name (never the arity).
- [ ] Editor integration (`editor.py`): `QCompleter` with
      `QCompleter.PopupCompletion`, installed per editor, driven from
      `keyPressEvent` the way the reference `Editor.cpp` did it — but:
  * no completion inside a comment, a string or a `#expr#` block (the tokenizer
    from task_22 knows where the caret is);
  * manual trigger `Ctrl+Space`, automatic after N letters (setting, default 2);
  * `Enter`/`Tab` accept, `Esc` closes, `Shift+Enter` keeps the newline;
  * the popup never steals the arrow keys from the editor inside the line.
- [ ] A completion popup colour/spacing that survives the Cyrillic font.
- [ ] Tests: `src/gui/tests/test_completion.py` (Qt-free) — candidate
      collection from a sample document, prefix matching, ranking, and
      suppression inside comments/strings; an offscreen widget test for the
      accept/close keys, skipped without PySide6.

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

## Acceptance

Typing `НАЙ` offers `НАЙТИВСЁ/3`; typing `чле` after defining `член/2` offers
`член`; completion does not appear inside `% комментарий`, `"строка"` or
`#выражение#`; `Ctrl+Space` opens the popup on demand.
