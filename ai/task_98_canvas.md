# task_98 — the canvas directive `:- ХОЛСТ(Высота, Ширина).`

**Status:** done (2026-10-23)
**Depends on:** task_15 (graphics), task_73 (the screen the front-end names)
**Milestone:** post-2.5.0

## Goal

A program should be able to say what it draws on.  The size of the screen was the
front-end's to name (the window's setting, the protocol's `load.screen`), so a
picture of a known size — the maze is 14 cells of 16 pixels — needed a flag that
was invisible from the source.

## Deliverables

- [x] `:- ХОЛСТ(Высота, Ширина).` / `:- canvas(Height, Width).` — a directive the
      loader applies while loading, so it comes after the front-end's request and
      overrides it (the way `ИМЕНА` overrides the naming row).
- [x] Both arguments are integer literals; each side 16…2048.  `kMinScreen` and
      `kMaxScreen` moved to `graphics.hpp` and the protocol uses the same pair.
- [x] `GraphicsBackend::reset(width, height)` is virtual (a no-op in the console
      backend), so the loader resizes without knowing the backend.
- [x] `ХОЛСТ`/`canvas` are reserved: using one as a goal gives «ХОЛСТ — директива,
      а не предикат», the hint the reserved-directive table already produced.
- [x] The buffer is cleared by every `ХОЛСТ`, and the last directive of a program
      wins; a library's directive counts too.
- [x] Three cases in `test_graphics.cpp`: the directive sets the size and beats the
      size the front-end asked for; a size outside the limits is a load error naming
      the limits; a non-literal argument is a parse error.

## Measurements

* Over the protocol: `--screen 100x100` plus `:- ХОЛСТ(40, 60).` gives a 60 × 40
  snapshot and a PNG of that size — the directive wins.
* `:- ХОЛСТ(5, 5).` → `ХОЛСТ: размер холста должен быть от 16 до 2048 точек, а
  названо 5 на 5 (файл:1:1)`, exit code 2.
* `:- ХОЛСТ(A, 40).` → parse error «ХОЛСТ ожидает два целых числа:
  ХОЛСТ(Высота, Ширина)», exit code 2.

## Not done (on purpose)

* No arithmetic in the arguments: the size is needed before the first goal runs.
* The maze's own file does not set a canvas yet — it is edited by the owner, and a
  fixed 224 × 224 would not fit the 7 × 7 sample.
