# task_97 — the maze example: BFS and DFS with a picture

**Status:** done (2026-10-23)
**Depends on:** task_15 (graphics), task_21 (the window that shows the picture)
**Milestone:** post-2.5.0

## Goal

A worked problem for the dialect that is more than arithmetic: a mouse searches a
maze for cheese, breadth-first and depth-first, and the search is *shown* — the
mouse walks along the found path, the previous frame is erased by hand, walls and
cheese come from pictures.

## Deliverables

Built-ins and tools:

- [x] `ЗАКРАСКА(X1, Y1, X2, Y2, Цвет)` (`fill/5`) — rectangle fill, borders
      included, any corner order, rows outside the screen dropped.  One
      `horizontal` per scan line, so the protocol carries nothing new (ADR-033).
- [x] `ТОЧКА(X, Y, Цвет)` fixed for a free `X`: it drew its line at row `width`,
      which is off screen; the test now checks coordinates, not only the operation.
- [x] `ИСТИНА/0` (`true`) — an empty branch of `(A -> B ; ИСТИНА)` needs a goal
      (ADR-032).
- [x] `tools/render_graphics.py` — runs a program over `--protocol json`, takes the
      `graphics{snapshot}` and writes a PNG with no dependencies; decodes the
      snapshot's colour number (four little-endian bytes), not raw RGBA.
- [x] `tools/image_to_pld.py` — PNG → `картинка/6` facts via `ЗАКРАСКА/5`; ink-only
      averaging, median-cut palette, greedy rectangle merge, preview PNG, `--size`,
      `--colors`, `--coverage`, `--tolerance`, `--background`.

The example (`examples/problems/maze/`):

- [x] `maze.input.txt` — the format is size, mouse, cheese, then the rows (`#` wall,
      `.` passage).
- [x] `maze.images.pld` — generated: the wall (76 rectangles, 4 colours) and the
      cheese (45, 4); the header names the tool.
- [x] `maze.graphics.pld` — cell of 16 pixels, `слева/2`, `сверху/3`,
      `очистить_поле/2`, `стереть_клетку/3`, `нарисовать_картинку/4` (draw every
      fact, then fail into a catch-all), `нарисовать_стенку/3`, `нарисовать_сыр/3`,
      `нарисовать_мышь/3` (primitives: body, head, ears, eye, tail).
- [x] `maze.pld` — `прочитать/7`, `ряд/3` (row number `N - X`), `стена/4`,
      `свободно/5`, four `сосед/7` clauses, `путь_в_ширину/8` with a queue of paths,
      `путь_в_глубину/8`, `идти/4` (draw, `ЖДИ(200)`, erase, restore the cheese),
      questions `?в_ширину.` and a commented `?в_глубину.`.

## Measurements

* The first sample maze, 7×7, used while the example was written: BFS finds 9
  cells, DFS 11 — both paths printed and checked against a hand trace; the wall
  set is 30 cells, exactly the `#` of the input.
* The shipped maze (the owner's, 14×14, mouse `(9, 2)`, cheese `(13, 13)`): BFS
  finds a path of 52 cells and DFS of 64.  The question of the file reads the
  input with `ЧТЕНИЕ_ИЗ`, whose path is relative to the working directory — the
  window runs from the example's folder, the CLI takes `-i`.
* Timings of the two searches on that maze: BFS 2.49 s and DFS 1.82 s at first —
  neither kept a shared set of visited cells.  Now both do (a cell is expanded
  once): `поиск/8` puts new paths at the **back** of the queue and `спуск/8` puts
  them at the **front** of the stack, the rest of the shape is the same.  BFS
  takes **0.12 s** on the 14×14 maze and still returns the shortest path, 52;
  DFS takes **0.06 s** and returns 64.  On the 7×7 sample: BFS 30 ms / 9 cells,
  DFS 19 ms / 15 cells — the depth-first path is longer there than the 11 of the
  old backtracking version, which is the point: it is not the shortest one.
* The picture was checked apart from the logic: the same maze drawn on a black
  field without the cheese, the snapshot cut into cells by a script — the grid
  matches the input line for line.  The first "mismatch" was the script printing
  rows bottom-up.
* The converter on 16×16 cells: wall and cheese recognisable, the mouse not (its
  outline is thinner than a cell) — hence the mouse is drawn with primitives.

## Checks that moved

* `ctest` 400 → 401 (the `ИСТИНА` case; the maze joins the parse-only list of
  `test_lessons.cpp`; the formatter's "standard shape" test sees the three new
  `.pld` files).
* `src/gui/tests/test_queries.py` — 511 questions in 55 example programs
  (`PINNED` gained the three maze files).
* `help.typ` §4.2 and §14, `doc/builtins.json` (`ИСТИНА`, `ЗАКРАСКА` arities
  `[3, 5]`) — `test_reference.py` stays green.

## Not done (on purpose)

* The maze is not part of the acceptance corpus of `test_lessons.cpp`'s output
  checks: it draws and pauses, exactly like `hanoi.pld`.
* No separate folder `README.md`: the `problems/` folders have none, the run line
  lives in `examples/README.md` and in the header of `maze.pld`.
