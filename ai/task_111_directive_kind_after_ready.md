# task_111 — the kinds arrive with the first run, and `-I` has one meaning

**Status:** done (2026-10-24) — ADR-047, part 177
**Depends on:** task_102 (imported names in the popup), task_104 (the file name
inside the directive), task_61 (the `-I` list), task_50 (the keyword table)
**Milestone:** 2.6.0

## The owner's report

After the first `F5` in a program with `:- ИМПОРТ("iso.pld").`:
`ИМПОРТ` stopped being bold, `F12`/`length` stopped working, and the library
predicate was no longer found.  They also showed that the same program works in the
portable package (`Д=3`) and fails in a checkout («Не найден импортируемый файл
'iso.pld'»).

## Cause 1: two tables, one of them with kinds

The window reads the reserved names twice.  Before the first run they come from
`prologu --list-keywords`, which prints `name/arity` lines and **no kinds** — so
`ИМПОРТ` is a plain `KEYWORD`.  From the first run on they come from the `ready`
event, where the interpreter says `"kind": "directive"`.

Two places compared against the wrong list of kinds:

- `imports.directive_names` and `imports.import_argument_at` accepted
  `KEYWORD`/`ATOM`/`VARIABLE` but not `DIRECTIVE`.  So once the kinds arrived, the
  `ИМПОРТ` line named no file: the popup lost every imported name (`length`
  included), `F12` on such a name said «не найдено», and the file-name completion
  inside the quotes (`task_104`) went quiet.
- `theme._BOLD_KINDS` held only `KEYWORD`, so a `directive` was coloured like a
  keyword but not bold.  That is the visible half of the same fact.

Both now know the kind: one `imports.is_directive_name(token)` for the two import
functions (with the three legacy kinds and a comment saying why), and
`_BOLD_KINDS = {KEYWORD, DIRECTIVE}`.

## Cause 2: `-I` meant two folders

The window's own lookup resolves a search directory against **its** working
directory; the interpreter resolves `-I` against the **running program's** folder.
A row of `stdlib` was therefore two folders: the popup found `iso.pld` while the
run answered «не найден».  `_import_directories` now hands out absolute paths
(`os.path.abspath`, which only rewrites the spelling and does not ask the disk —
it is asked on every keystroke), so both readers see one folder.

A README-worthy note for a checkout: the engine looks for `stdlib` **beside its
executable**, and in a build tree the executable is deep in `build/…`, so
`ИМПОРТ("iso.pld")` needs `-I <repo>/stdlib` there.  In the portable package
`stdlib` is beside `prologu.exe`, which is why the owner's `dist` run worked with
no `-I` at all.  Checked both ways on the engine: `Д=3` with the absolute `-I`,
the «Не найден» message without it.

## Checks

- `test_imports.py`: the same line read by a table without kinds and by one from
  `ready` — both name the file, and the file-name lookup inside the brackets works
  with the kinds too.
- `test_highlighter.py`: `ИМПОРТ` is bold (weight and colour) with and without the
  kinds.
- `test_window.py`: the import popup is checked before **and after** a run, in the
  same tab — the regression the owner hit; and the settings dialog's import row is
  compared as a path, since the session now hears the absolute spelling.

29 GUI suites and `protocol_smoke.py` green; `ctest` 423/423.
