# task_102 — the popup knows what an `ИМПОРТ` line brings in

**Status:** done (2026-10-23) — ADR-040, part 169
**Depends on:** task_24 (the popup and its model), task_69 (`paths.resolve_import`,
the `F12` search order), task_14 (imports are includes, not modules)
**Milestone:** 2.6.0

## Goal

Completion offered the names written in the buffer and the reserved ones.  A name
the program *imports* lives in another file and was offered by nothing — and in
Prolog that is very often the name of the next goal (lesson 11 is exactly that:
`:- ИМПОРТ("библиотека.pld").` and then `член(…)`).  The owner asked how the popup
works today and whether the imported files could be picked up.

## How it works now

`completion.py` (Qt-free) builds the list from two halves: the reserved names (from
`--list-keywords`/`ready`) and the document's own — a line-by-line pass through the
tokenizer, deliberately not a parse, because the file is mid-edit.  A call gives a
name with its arity (`_count_arguments`, lists tracked), a bare or quoted atom is a
candidate of its own.  `CompletionModel.update(text)` rebuilds only when the text
changes; `candidates(prefix)` filters and ranks.

## What was added

- **`imports.py`** (new, Qt-free): `directive_names(text)` reads the `ИМПОРТ`/
  `import` lines with the editor's tokenizer — so a directive inside a comment or a
  string names nothing — and `ImportedFiles.texts(names, …)` resolves each name the
  way `F12` does (`paths.resolve_import`: the importing file's folder, then the `-I`
  directories, then `stdlib`), reads it, and walks *its* imports too, with a `seen`
  set (the engine tolerates a cycle, so this must) and with the search restarted in
  each imported file's own folder.  A file is read again only when its size or
  modification time changed.
- **`completion.py`**: `collect(text, keywords, imported)` — a third source,
  `IMPORTED`, ranked after the document's own and before nothing else; the
  candidate carries `origin` (the file's name).  Only *predicates* are taken from
  an imported file: a library's atoms are not what the next goal is typed with, and
  they would bury the document's own names.
- **`editor.py`**: `set_import_lookup(lookup)`; the popup rescans the directive list
  and asks for the texts **only when that list changed**, so a keystroke costs one
  substring test per line, and typed text elsewhere costs nothing.  The label under
  the popup says «импорт: библиотека.pld» for a name that has no record of its own.
- **`buffers.py` / `window.py`**: the lookup travels with the buffer to every view;
  the window builds it, because only the window knows the search directories, the
  interpreter and the folder of the file (a buffer without a path resolves against
  the directories alone, as the interpreter does for standard input).

## Checks

- `src/gui/tests/test_imports.py` (new, 5 cases): both spellings and both argument
  kinds; a commented or quoted directive names nothing; recursion with a cycle and a
  missing file; the search starting in each importing file's folder; the read cache
  (an unchanged file is served again, a changed one is read).
- `test_completion.py`: «an imported file adds its predicates» (source, origin,
  arity, no atoms, a reserved name stays reserved, the document's own name ranks
  first) and the cache case now also proves that a new import list invalidates the
  candidates and the same list does not.
- `test_window.py`: «an imported file reaches the popup» — the real seam: the
  «Дополнительные каталоги ИМПОРТ» row is filled, the directive is typed, and the
  popup offers `член_списка/2` with the file named under it.
- `doc/gui.typ` §5 and §5.1.

27 GUI suites and `protocol_smoke.py` are green; `ctest` is untouched (422/422).

## What was deliberately not done

- imported **atoms** are not offered (a colour is not a goal);
- a file edited in another tab is not noticed until it is saved: the cache is keyed
  by the file's version on disk, and reading the open buffer instead would mean
  wiring every buffer's text into the popup's key;
- no diagnostics: a name that cannot be found is the interpreter's business when
  the program runs.
