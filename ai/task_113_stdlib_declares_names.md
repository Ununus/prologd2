# task_113 — the standard library declares how its names are read

**Status:** done (2026-10-24) — part 179
**Depends on:** task_67 (the marker), task_112 (the welcome imports `iso.pld`)
**Milestone:** 2.6.0

## What was wrong

`stdlib/*.pld` is written in ISO names — `Список`, `Длина`, `Отсортирован` are
variables there.  A file that imported the library in the **old** reading
(«Имена переменных» = PLD, or a program that declares `:- ИМЕНА(1).`) read those as
string constants, and `length([_|Хвост], Длина)` stopped meaning what it says.  The
library had no first line of its own, so it was read in whatever mode the run had.

## The change (the owner's edit, committed as it stood)

Every one of the six files now starts with `:- ИМЕНА(0).` — the same thing
`examples/names.pld` does: the mode belongs to the file, and a library knows its own
better than any run does.  `iso.pld`'s comment above `msort` was shortened at the
same time: the sentence about the cuts («Отсечения в первых двух предложениях
обязательны…») is gone, the two remaining lines say what the predicate is for.

## Checks

`ctest` 423/423; `test_imports.py`, `test_window.py` and `test_reference.py` green.
The welcome of task_112 imports `iso.pld`, so the first tab now shows a program whose
library states its own dialect — the one thing that makes the demo independent of
the «Имена переменных» row.

## Why the marker is right here and not a workaround

The engine reads the marker from the first line of **each** file, imported ones
included (`readVariableMarker` runs per file).  That is exactly the tool for «this
file was written by these rules», and a library is the clearest case of it: its text
does not change with the settings of the program that imports it.
