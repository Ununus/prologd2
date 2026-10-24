# task_103 — the popup reads the comment above a clause, and F12 goes to it

**Status:** done (2026-10-23) — ADR-041, part 170
**Depends on:** task_24 (the popup), task_37 (the label under it), task_69 (`F12` on
an `ИМПОРТ` line), task_102 (the imported texts are already read)
**Milestone:** 2.6.0

## Goal

Two requests from the owner.  First: a library such as `stdlib/iso.pld` documents
every predicate with a `%` comment right above it, and today that text is invisible
unless the file is opened — the popup says nothing about a user's own predicate.
Second: `F12` opens the file an `ИМПОРТ` line names, and it could as well go to the
clause a name is defined by.

## 1. The comment travels with the name

`completion.collect_names` now returns a fourth half — `{name: comment}` — filled
from the `%` block written **directly above** the first clause head of that name.
The rules:

- only lines that touch the clause count, so a file's header (separated from the
  first predicate by a blank line, as `iso.pld` has it) is not glued to it;
- a wrapped comment becomes one paragraph (`%` and the space after it dropped,
  lines joined with a space), and a very long one is cut at 400 characters;
- a head is the line's *first* token with `(`, `.` or `:-` after it, so a goal, a
  query and a mention in prose are not taken; a predicate of no arguments is an
  atom in this scan and its head is recognised the same way;
- a comment *after* the clause (at the end of the line or on a line below) is not
  read: the label is about the name.

`Candidate.summary` carries it, and `editor._update_detail` shows, in this order:
`импорт: файл` (for a name an import brings in), the comment, then the built-in
record from `doc/builtins.json`.  Nothing at all means no label, as before.

`queries.py` reads the same scan (it uses the names to tell a question from prose)
and was updated with it.

## 2. F12 goes to the first clause

`definitions.py` (new, Qt-free) answers two questions about a text and a caret:
`name_at(text, position)` — the name the caret sits in or touches on either side
(F12 with the caret at the start, the middle and the end of a word are one
command) — and `first_definition(text, name)` — the line and column of the first
clause head of that name, recognised by the same shape as above; directives
(`:-`), questions (`?`) and comments are skipped, a quoted head matches its
unquoted spelling, and a space before the bracket does not hurt.

The window: `F12` is one command with two duties.  On an `ИМПОРТ` line the
directive wins (the import *is* what the name means there, task_69); everywhere
else the name under the caret is searched in the buffer, then in the files its
imports bring in — the same list the popup reads, so a name can only be found
where the program could see it.  Found in the buffer: the caret moves there.
Found in an import: the file opens in a tab and the caret lands on the clause.
Nothing found: the status says so, and for a built-in it says «встроенный
предикат — справка по F1».

The entry is enabled where the command can act — on the directive, or on any
name — which is the cheap half of the question (is there a name here at all); the
search itself is the key press.  The title became «Перейти к определению»: one
key, one question, «где это».

## Checks

- `test_definitions.py` (new, 3 cases): the name on either side of the caret, a
  quoted atom without its quotes; the head told from a goal, a query and a comment
  (`член` in the first line of the document is inside a comment and is not a
  definition); a quoted head and a space before the bracket.
- `test_completion.py`: the comment above the first clause (a wrapped block is one
  paragraph, a blank line ends it, a comment of another predicate is not attached,
  a zero-arity predicate's head counts) and the candidate carrying it.
- `test_window.py`: the popup of an imported file shows the file *and* the
  library's comment; a new case drives `F12` — a name of the buffer, a name of an
  import (the tab opens, the caret lands on the first clause), a built-in and a
  name that is nowhere.
- `doc/gui.typ` §4 (the shortcut table and the paragraph), §5 and §5.1.

28 GUI suites and `protocol_smoke.py` are green; `ctest` is untouched (422/422).

## What was deliberately not done

- only the **first** clause is a target; a list of all clauses is a different
  command («find usages»), and nothing here pretends to be one;
- a file the program does not import is not searched — the window has no index,
  and building one would be a different task;
- an operator-style head (`X = Y :- …`) is not a definition of a name;
- block comments (`/* … */`) above a clause are not read, only `%` lines.
