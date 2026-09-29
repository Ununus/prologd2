# Porting notes: original PrologD examples to the new syntax

The programs in `examples/` are ports of the original PrologD sources (the
previous implementation, <https://github.com/Ununus/prologd>, `examples/`). The
mechanical part of the conversion is performed by `ai/tools/port_lessons.py`;
this file records the rules and the manual checks.

## Conversion rules

| Original (PrologD) | New (PrologD 2.0) | Rule |
|--------------------|-------------------|------|
| single letter, any case (`x`, `X`, `н`, `Н`) | upper-case name (`X`, `Н`) | a single letter was always a variable |
| lower-case single letter whose upper-case form is also a variable in the same file (`м` and `М`) | `М_` | keep the mapping injective |
| `Имя'` / `x'` | `Имя` / `X` | trailing apostrophe marked a variable |
| multi-letter name starting with an upper-case letter, used as a predicate (`XOR(...)`, `Фиб(...)`) | lower-cased (`xor`, `фиб`) | predicate names start lower-case |
| multi-letter name starting with an upper-case letter, used as a constant (`Россия`, `Stelle`, `CPM`) | quoted (`'Россия'`, `'Stelle'`, `'CPM'`) | upper-case start means variable |
| reserved built-in names (`БОЛЬШЕ`, `НАЙТИВСЁ`, …) | unchanged | reserved atoms |
| comments, strings, quoted atoms | unchanged | copied verbatim |

## Automatic mapping

For a single lower-case letter `c` the tool uses `C` unless the upper-case letter
`C` also occurs as a variable anywhere in the file, in which case it uses `C_`.
For example, in `lesson_6.pld` the original uses both `М` and `м`; they become
`М` and `М_`, which keeps them distinct.

Apostrophe names are capitalised: `история'` → `История`, `на_правом'` →
`На_правом`, `в_лодку'` → `В_лодку`, `x'` → `X`.

## Per-file notes

The table lists the files ported from the reference.  The rewritten course
(`examples/lessons/lesson_01.pld` … `lesson_12.pld`, see
`ai/task_35_lessons_rework.md`) is written for this dialect from scratch and is
not a port; the old lesson it replaces is kept under `examples/lessons/_old/`.

| File | Notes |
|------|-------|
| `lessons/_old/lesson_1.pld` | archived when lesson 1 was rewritten for the course; `Himmel`, `Sonne`, `Stelle` are quoted atoms; `Галя`, `Боря`, … are quoted. |
| `lessons/_old/lesson_2.pld` | archived when lesson 2 was rewritten for the course (its arithmetic moved to lesson 3); trailing-dot floats (`1.`, `2.`); the `sqrt`/`sqrt1`/`abs` predicates keep their names. |
| `lessons/lesson_3.pld` | string predicates operate on quoted strings and atoms; positions are code points.  **Changed on purpose:** the original counted occurrences with `КОПИЯ(с,х,у,б)` (position and length both free) and took the prefix *before* the found occurrence, which counts correctly only when that search goes from the **end** of the string.  The reference searched from the end until commit `da51bbe` («Fix: КОПИЯ», 23.03.2023) switched it to `str0.find`, and the port follows the current reference: with position and length free it takes the **first** occurrence (`doc/help.typ` §7.4 says so now).  `сколько/3`, `замена/4` and `удаление/3` are therefore rewritten for that direction — the count walks the rest *after* the occurrence, replacement and deletion cut the first one out and recurse — and the commented queries stay commented.  `?сколько(идиотизм,"и",Н)` → `Н=3`, `?замена("а","ю",абвабва,Т)` → `Т=юбвюбвю`, `?удаление("а",абракадабра,Ю)` → `Ю=бркдбр` (`test_lessons.cpp`). |
| `lessons/_old/lesson_4.pld` | archived when lesson 5 was rewritten (lists moved there); list predicates; the active `?быстрсорт(...)` query is preserved. |
| `lessons/lesson_5.pld` | apostrophe variables in the ferry puzzle; the file defines `список/2`, `можно/2`, `нельзя/2` twice (queens and parliament sections) — this is faithful to the original and is why `ферзи` cannot be queried from the full file (the parliament `можно/2` clashes); use the queens fragment or a standalone program. |
| `lessons/lesson_6.pld` | `XOR` → `xor`; `Денис`, `Кирилл`, `Максим`, `Миша`, … quoted; `М`/`м` and `П`/`п` stay distinct. |
| `lessons/lesson_8.pld` | graphics; the animation query recurses forever and is therefore not executed by the tests. |
| `lessons/lesson_9.pld` | interactive (`ВВОДСИМВ`); the queries need input, so only parsing is tested. |
| `factorial.pld` | `н`, `ф`, `х` → `Н`, `Ф`, `Х`. |
| `file_io.pld` | `Н` stays `Н`. |
| `drawing.pld` | tabs preserved; single-letter coordinates renamed. |
| `monk.pld`, `monkd.pld` | `a`, `b`, `c` become `A_`, `B_`, `C_` because `A`, `B`, `C` are already variables. |
| `ranez.pld` | dropped: the reference copy was double-encoded; the `ranez` predicate is present in `lesson_4.pld`. |

## Regenerating the ports

Check out <https://github.com/Ununus/prologd> and point the tool at its
`examples/` directory (the local reference copy has been removed):

```sh
python3 ai/tools/port_lessons.py "<checkout>/examples/lessons" examples/lessons
python3 ai/tools/port_lessons.py "<checkout>/examples" examples
```

`examples/findall_demo.pld` is already written in the new syntax and must not be
overwritten by the tool; restore it if necessary (it is the requirements
example).
