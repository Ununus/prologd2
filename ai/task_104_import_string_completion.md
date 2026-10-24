# task_104 — the directive's string completes to a file name

**Status:** done (2026-10-24) — ADR-042, part 171
**Depends on:** task_102 (the import lookup and the search order), task_24 (the popup)
**Milestone:** 2.6.0

## Goal

The owner asked whether the names inside `:- ИМПОРТ("is|").` could complete to
`iso.pld`.  The popup is deliberately quiet inside a string — a string is not code
— so the question was really «can the exception be made narrow enough».

## Decision

Yes, and the exception is exactly one string: the argument of an `ИМПОРТ`
directive (either spelling, `"…"` or `'…'`).  Inside it the popup offers **files
and folders** instead of predicates; everywhere else nothing changed.

- `imports.import_argument_at(text, position)` answers what is typed: the folder
  part (`lib/`, or empty) and the name part (`is`).  It reads the line with the
  editor's tokenizer, so a directive in a comment or a string of another predicate
  is not one, and a caret past the closing quote is not inside.
- `imports.search_folders(...)` — the same order the run uses (the file's own
  folder, the `-I` rows, `stdlib`), only folders that exist.
- `imports.complete_names(folders, typed)` — the entries of the typed folder,
  filtered by the typed prefix without case, folders first with a trailing `/`,
  then `*.pld`; a folder that is not there lists nothing, silently.
- The editor: one letter is enough (a name is not a word), `/` shows the folder, and
  accepting replaces **only the name part**, so `lib/` typed by hand stays.  The
  entry inserts no brackets and no arity.
- The folders come from the window through the same seam as the imported texts
  (`Buffer.set_import_folders` → `Editor.set_import_folders`), so the popup lists
  what the run would find and not a different set.

## Checks

- `src/gui/tests/test_import_file_names.py` (new, 5 cases): the caret inside the
  directive's string (both spellings, quoted atom, right after `/`, unterminated);
  an ordinary string, a comment and the code around get nothing; folders first and
  `.pld` only, matched without case; a typed folder narrows the listing and a
  missing one is silent; the search folders are the file's own, the `-I` rows and
  `stdlib`, in that order and without duplicates.
- `test_window.py`: the end-to-end case — `iso.pld` offered after `is`, `иное.pld`
  not, accept writes `iso.pld` into the quotes and leaves the caret inside them;
  and `ВЫВОД("is` offers nothing at all.
- `doc/gui.typ` §5 — the bullet, and the intro now says the threshold is one letter
  in this string.

29 GUI suites and `protocol_smoke.py` are green; `ctest` untouched (422/422).

## What was deliberately not done

- no disks scan beyond the typed folder: no index, no "all `.pld` on the machine";
- folders are offered, but only one level at a time (type `/` to go deeper);
- the `.pld` pattern is fixed — a program is not a `.txt`, and the engine would not
  load one.
