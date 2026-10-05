# task_63 — colour becomes `0xRRGGBB`, with a library of names

**Status:** done (2026-10-06)
**Depends on:** task_15 (the graphics built-ins and their backends), task_45 (the
graphics window), ADR-016 (what a built-in does when it cannot answer), ADR-026 (the
standard library beside the interpreter), task_62 (the library as a place for
predicates the language does not have to grow), the `Versioning` section of
`ai/conventions.md`
**Milestone:** the graphics surface after M16; asked for directly by the user

## Goal

The user asked whether the graphics predicates should stop taking the 0…15 palette,
gain an `rgb/4`, gain a `graphics.pld` with the colour names, and whether `lesson_12`
and `drawing.pld` should be rewritten to use them.  Two decisions were theirs and are
answered: **modern RGB values** for the names (not the EGA ones the palette showed),
and **yes to a range check** — a value that is not a colour is an error.

## What is already there

Colour is not the engine's business: `GraphicsColor` is `unsigned`, «the colour
**value** the program wrote», and the window's `graphics.color_for` turns a value into
a pixel.  That function already reads anything above 15 as `0xRRGGBB`, and
`help.typ` §14 already documents both ranges — so this task is **subtractive** on the
engine side and **additive** in the library:

* the palette (`graphics.color_for`'s first branch and `EGA_PALETTE`) goes away;
* a colour is `0xRRGGBB`, that is `0…16777215`, and nothing else;
* the names arrive in `stdlib/graphics.pld` as `rgb/4` calls, so a program writes
  `красный(Ц), ЛИНИЯ(0, 0, 10, 10, Ц)` and never a bare `16711680`.

## Design

**The value is the colour.**  `0xRRGGBB` keeps the canvas a grid of numbers: a write
and a read (`ТОЧКА(X, Y, Цвет)` with a free colour) compare the same thing, and the
window needs no palette to interpret it.  `0` stays the blank screen and is plain
black.

**`rgb/4` is a relation, and works both ways.**  Two guarded clauses:

```prolog
rgb(Красный, Зелёный, Синий, Цвет):-ЦЕЛ(Красный), ЦЕЛ(Зелёный), ЦЕЛ(Синий),
	РАВНО(#Красный * 65536 + Зелёный * 256 + Синий#, Цвет).
rgb(Красный, Зелёный, Синий, Цвет):-ЦЕЛ(Цвет),
	РАВНО(#Цвет div 65536 mod 256#, Красный),
	РАВНО(#Цвет div 256 mod 256#, Зелёный),
	РАВНО(#Цвет mod 256#, Синий).
```

Free `Цвет` — it computes (what a drawing program needs); bound `Цвет` — it *checks*
(what a read needs: `?ТОЧКА(X, Y, Ц), красный(Ц).`).  The guards are not decoration:
an arithmetic expression over a free variable is an **error**, not a failure, so
without `ЦЕЛ(...)` the second clause would never be reached with a bound colour.  A
mixed call (colour free *and* a component free) is a plain failure: there is no
generator for "all colours like that" here.

**A value outside the range is an error.**  `builtins_graphics.cpp` gains a
`colour(...)` helper beside `coordinate(...)`: an integer in `0…0xFFFFFF` or a
`TypeMismatch` whose message names the range and the value.  Without it the window
masked `0x1FF0000` into `#ff0000`, so two values that *looked* alike compared unequal
on a read.

**The names use modern values** (the user's choice): the classic 16 plus a couple a
drawing wants.  `красный` is `#ff0000`, not the palette's `#aa0000` — the demo
pictures shift a little, and in exchange every colour has one definition that both
the library and the window share.

| Name | Value | Name | Value |
|---|---|---|---|
| `чёрный` | `0x000000` | `белый` | `0xffffff` |
| `красный` | `0xff0000` | `тёмнокрасный` | `0x800000` |
| `зелёный` | `0x00ff00` | `тёмнозелёный` | `0x008000` |
| `синий` | `0x0000ff` | `тёмносиний` | `0x000080` |
| `голубой` | `0x00ffff` | `бирюзовый` | `0x008080` |
| `сиреневый` | `0xff00ff` | `пурпурный` | `0x800080` |
| `жёлтый` | `0xffff00` | `коричневый` | `0x808000` |
| `оранжевый` | `0xff8000` | `серый` | `0x808080` |
| `светлосерый` | `0xc0c0c0` | `тёмносерый` | `0x404040` |

## What moves

- [x] `builtins_graphics.cpp` — `colour(...)` with the range check, used by every
      colour argument of `ТОЧКА`/`ЛИНИЯ`/`ОКРУЖНОСТЬ`/`ЗАКРАСКА`;
- [x] `graphics.py` — `EGA_PALETTE` and the palette branch out of `color_for`;
- [x] `graphicswindow.py` — the hovered cell shows `#rrggbb`, not a bare number;
- [x] `stdlib/graphics.pld` — `rgb/4` and the names;
- [x] `stdlib/README.md`, `doc/library.typ` — the new file (the completeness check
      requires every head of `stdlib/*.pld` to be in the document);
- [x] `examples/lessons/lesson_12.pld` — the names, and the paragraph that says
      «1 — чёрный, 4 — синий…»; the `%!` lines re-recorded from the interpreter;
- [x] `examples/drawing.pld` — the names instead of `0`, `1`, `10`, `14`, `15`;
- [x] `doc/help.typ` §14 — the colour paragraph: `0xRRGGBB`, the range, the library;
- [x] `doc/gui.typ` — the graphics window's two mentions of the palette;
- [x] `doc/builtins.json` — the colour argument of the four predicates (the detail line
      has to start with `ТОЧКА`, or `test_reference.py` refuses it);
- [x] `doc/prologd-diff.typ` — the palette is gone: a difference from the original;
- [x] `doc/lessons.typ`, `examples/README.md`, `src/gui/README.md` — the words
      (`doc/lessons.typ` turned out to name no colour and needed nothing);
- [x] `src/gui/tests/test_graphics.py` — `color_for` without the palette;
- [x] the range error is verified by hand (all four predicates: exit 3, «Цвет вне
      диапазона 0…16777215», and `16777215` accepted); a *test* still does not pin it —
      the graphics suite pins colour values, not refusals;
- [x] `examples/stdlib_demo.pld` — left alone by decision: its table is per library file
      and the names are already shown by lesson 12 and `drawing.pld`, so `PINNED` did not
      move;
- [x] journal part 95, one commit.

## Verification

- `ctest --test-dir build/windows-msvc -C Release` green (the formatter sweep demands
  `stdlib/graphics.pld` be a fixed point of `--format`, `test_stdlib.cpp` that its
  every head is in `doc/library.typ`, and `test_lessons.cpp` that lesson 12 still
  prints exactly what its `%!` lines promise).
- `test_graphics.py`, `test_window.py`, `test_queries.py` green.
- The six documents build.
- By hand: a program that draws with `красный(Ц)` and reads the colour back; a value
  out of range refused with the new message.

## Risks

* A lesson that imports `stdlib/graphics.pld` depends on the library being findable —
  it is, beside the interpreter (ADR-026) and through the include path in the source
  tree, but the lesson header should say where the names come from.
* Old programs that drew with `4` now draw near-black, silently; no test pins a
  *rendered* colour except `test_graphics.py`, which is why it is on the list.
* `test_queries.py`'s `PINNED` counts `?`-statements per example file: the demo's
  table has to be refreshed with `--print` in the same change.
