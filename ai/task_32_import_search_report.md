# task_32 — say where an import was searched

**Status:** done
**Depends on:** task_14 (module loader), task_28 (running), task_29 (working folder)
**Milestone:** M11

## Goal

When `ИМПОРТ("x.pld")` fails, the message must name the directories that were
searched, in order.  Today it is only

```
Не найден импортируемый файл 'lib/x.pld' (<buffer>:3:1)
```

which tells a user nothing when the file is one directory away, when the working
folder is misconfigured, or when the buffer has never been saved.  The GUI can
only repeat what the interpreter says, so the fix belongs in the loader.

## Deliverables

- [x] `ModuleLoader::resolve` keeps the ordered candidate list
      (`importer / name`, then every `-I` directory) and hands it back with the
      failure instead of dropping it.
- [x] The message stays one line so the `file:line:column: error: message`
      shape and the existing tests survive:

      ```
      Не найден импортируемый файл 'lib/x.pld' (<buffer>:3:1). Искался в: D:\учёба; D:\учёба\библиотека
      ```

- [x] A candidate that exists but is rejected says why: outside the configured
      root (`вне корневого каталога`) or a directory instead of a file
      (`это каталог`).  Neither is skipped silently any more.
- [x] The list is capped (first five entries, then `…`) so a long `-I` chain does
      not flood the output pane.
- [x] Precedence is documented in `doc/help.typ` next to `ИМПОРТ`: the importing
      file's own directory first, then the `-I` directories in the order the user
      gave them.  The help text now also says that a failed import lists the
      directories it searched.
- [ ] Optional, cheap and worth having: `prologd --explain-imports`, which
      resolves every `ИМПОРТ` of a file and prints `ИМПОРТ("lib/x.pld") ->
      D:\учёба\lib\x.pld`, so a user can debug a search path without running the
      program.  **Not done** — the failure message covers the common case; keep
      this open until someone asks for it.
- [x] Tests:
  * Catch2 with no include directory, one and two directories — the message
    lists exactly what was tried, in order;
  * Catch2 for a rejected candidate (outside the root) and for a directory that
    matches the name;
  * CTest: `prologd -s src/tests/missing_import.pld` prints the directories and
    exits with the load code (2) — `cli_import_search_report`;
  * the Python GUI keeps showing the text verbatim, so the two sides cannot
    drift.

## Design notes

* Do not turn this into a multi-line diagnostic.  Everything downstream (the
  parser's sink, the protocol's `error` event, the GUI's red line) assumes a
  single line, and a long message is still one message.
* The empty importer path of an untitled buffer is worth spelling out: when the
  importing "file" has no directory, the first candidate is relative to the
  process working directory — say so instead of printing an empty string:
  `Искался в: <рабочий каталог процесса: D:\учёба>; D:\учёба\библиотека`.
* Keep the phrase `Не найден импортируемый файл` first: users and the existing
  tests match on it.

## Acceptance

A program that imports a file existing only in the working folder works, one that
imports a genuinely missing file reports every directory that was tried in the
order tried, and the GUI output pane shows that text without modification.

**Result.** `resolve()` fills a `std::vector<SearchStep>` (`{path, outcome}` with
`Found`/`Missing`/`NotAFile`/`OutsideRoot`); `describeImportSearch()` renders it
to absolute paths, capped at five.  Three new Catch2 cases plus
`cli_import_search_report`; 119 CTest tests pass.  A directory candidate, which
used to be returned as a resolvable path and only failed later in
`readFileText`, is now skipped with a reason.
