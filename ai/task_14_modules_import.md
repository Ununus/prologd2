# task_14 — Modular import system (`ИМПОРТ`)

**Status:** done
**Depends on:** task_05, task_07
**Milestone:** M6

## Goal

Replace the student `preprocessor.{h,cpp}` with a proper, modular loader.

## Background

The original `preprocessor.cpp`:

* matches import lines with a regex `\?ИМПОРТ\("..."\)\.`;
* splices files textually into one global `std::stringstream`;
* uses global mutable state (`preprocessorDestination`, `destinationFile`);
* writes a temporary file for in-memory sources;
* only blocks `../` and `..\\` by substring;
* has no cycle detection, no include-once caching, and reports no line numbers.

## Deliverables

- [ ] `include/prlib/module_loader.hpp`, `src/module_loader.cpp`
  * `ModuleLoader` with `IncludePath` list and an optional root directory.
  * `loadFile(path)` → parses a file (and its imports) into the `Database`.
  * `loadSource(name, text, origin)` for REPL / stdin.
  * Import directive forms recognised by the parser (task_05):
      - `?- ИМПОРТ("file").`
      - `:- ИМПОРТ("file").`
      - `?ИМПОРТ("file").`
      - a bare `ИМПОРТ("file").` clause is **not** accepted (must be a directive).
  * Import-once semantics keyed by `std::filesystem::weakly_canonical`.
  * Cycle detection with a readable chain in the error message.
  * Path containment: reject resolution outside root/include dirs; reject
    absolute paths unless explicitly allowed; clear error otherwise.
  * Search order: directory of the importing file, then `IncludePath` entries.
  * Module identity exposed for diagnostics (`file:line:column`), and clause
    locations preserved for `ПРЕДЛ`/trace.
  * `ИМПОРТ` used as a runtime goal: the CLI can accept an interactive
    `?ИМПОРТ("f.pld").` and load it at that point.
- [ ] `include/prlib/source_manager.hpp`, `src/source_manager.cpp` — owns loaded
  source texts and maps locations back to file/line for diagnostics.
- [ ] Remove the old preprocessor from the new build; keep a note in
  `technical.typ` explaining the replacement and in `prologd-diff.typ`
  explaining the directive syntax.

## Design notes

* No temporary files.
* Errors: `cannot open 'x'` (code 21), `import cycle: a -> b -> a`, `path
  escapes root`.
* Importing the same file twice must not duplicate clauses.
* The loader is usable from the library, not only the CLI, and is unit-testable
  with an in-memory file system abstraction or real temp directories.

## Tests

- [ ] `test_module_loader.cpp`
  * single import, nested imports, diamond import loaded once;
  * cycle detection message;
  * path traversal rejected (`../secret.pld`);
  * missing file error with location;
  * relative resolution from the importing file's directory and from include
    dirs;
  * UTF-8 file contents and BOM handling (strip a leading BOM).
- [ ] `test_import_integration.cpp`: a two-module program where predicates from
      both modules are queried.

## Acceptance

The old `?ИМПОРТ("...")` programs can be migrated by changing `?` handling only
if needed; the new loader passes all tests and no global mutable state remains.
