# task_32 — say where an import was searched

**Status:** not started
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

- [ ] `ModuleLoader::resolve` keeps the ordered candidate list
      (`importer / name`, then every `-I` directory) and hands it back with the
      failure instead of dropping it.
- [ ] The message stays one line so the `file:line:column: error: message`
      shape and the existing tests survive:

      ```
      Не найден импортируемый файл 'lib/x.pld' (<buffer>:3:1). Искался в: D:\учёба; D:\учёба\библиотека
      ```

- [ ] A candidate that exists but is rejected says why: outside the configured
      root (`Импорт выходит за пределы корневого каталога`), unreadable, or a
      directory instead of a file.
- [ ] The list is capped (first five entries, then `…`) so a long `-I` chain does
      not flood the output pane.
- [ ] Precedence is documented in `doc/help.typ` next to `ИМПОРТ`: the importing
      file's own directory first, then the `-I` directories in the order the user
      gave them (the working folder first of those, task_29).
- [ ] Optional, cheap and worth having: `prologd --explain-imports`, which
      resolves every `ИМПОРТ` of a file and prints `ИМПОРТ("lib/x.pld") ->
      D:\учёба\lib\x.pld`, so a user can debug a search path without running the
      program.
- [ ] Tests:
  * Catch2 with no include directory, one and two directories — the message
    lists exactly what was tried, in order;
  * Catch2 for a rejected candidate (outside the root) and for a directory that
    matches the name;
  * CTest: `prologd -s examples/…` on a program with a missing import prints the
    directories and exits with the load code (2);
  * the Python GUI test does not re-derive the message: it shows the text as it
    arrives (keeps the two sides from drifting).

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
