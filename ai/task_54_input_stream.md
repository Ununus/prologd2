# task_54 — ответ оболочки — кусок входного потока (и BOM — не данные)

**Status:** not started — the plan is written down (2026-10-02).  The user chose
points 1–3 of the discussion: the window's answer is a *chunk of the input
stream*, the multi-line console field stays, and a leading BOM is stripped the way
the lexer strips it from sources.  Point 4 (merging `ВВОДСИМВ`/`ВВОДСТР` into
`ВВОД(Пер, Терминатор)`) is **not** part of this task — see «Отложено» below
**Depends on:** task_50 (the console moved under the goal line, the queue became
the «Ввод» tab), task_29 (the «Спрашивать ввод» switch), task_11 (the reading
built-ins)
**Milestone:** post-M10

## Goal

Make every source of input obey **one rule**, so a program written against a file
behaves the same in the window:

* a file (`-i`, `ЧТЕНИЕ_ИЗ`), stdin, a `$`-line and a front-end answer are all
  *pieces of one input stream*;
* a *line* is what lies between two `\n`, and the end of a piece ends its last line
  — exactly like the end of a file;
* therefore `\n` inside an answer is a line separator, not a character in the
  string.

Today only the front-end breaks the rule: its answer is put into `current_line_`
whole (`io.cpp:105` + `fetchLine`, `io.cpp:58-72`), so the answer is one line
however many `\n` it contains.

Verified 2026-10-02 with the built interpreter (the experiments this task turns
into tests):

| source | what happens today |
|---|---|
| `-i` file, LF, with an empty line and a leading space | one line per read, `\r`/`\n` dropped, empty line = empty string, last line without a terminator read, EOF = failure |
| `-i` file, CRLF | `len=4 codes=[99,114,108,102]` — no `13` |
| `ВВОДСИМВ` + `ВВОДСТР` on `name rest of it` (file) | `name` and ` rest of it` — the remainder of the same line, leading space kept |
| `$`-lines, `ЧТЕНИЕ_ИЗ`, stdin | the same rule |
| **file with a BOM** (Notepad's default) | `codes=[65279,98,111,109,…]` — the BOM is *not* stripped and becomes the first character of the first line |
| **window** (console answers, a multi-line field) | `ВВОДСТР` returns the whole answer *with* the `\n`s; `ВВОДСИМВ` then `ВВОДСТР` gives a remainder that starts with `\n`; `ВВКОД` sees code `10` between the lines |

The window's *queue* needs no change: the window splits it into answers so it can
show the counter and echo each answer with `>` — that split is bookkeeping, not
reading, and each answer is a one-line chunk anyway.

## The rule of a chunk (the whole implementation, in three lines)

```
fetchLine:  preloaded line → file (if ЧТЕНИЕ_ИЗ redirected) → pending chunk → base stream
pending_:   take up to '\n' (dropping a '\r' before it); no '\n' → the whole rest,
            because the end of the chunk ends its last line; then ask the front-end
            for another chunk only when pending_ is empty
```

Consequences, all of them wanted:

| answer | lines |
|---|---|
| `first` | `first` |
| `first` then a second `ВВОДСТР` | asks the front-end again (the chunk is used up) |
| `a\nb` | `a`, `b` |
| `a\n` | `a`, then the front-end is asked again — **no phantom empty line** |
| `\n` | one empty line |
| `""` (an empty answer, as today) | one empty line |
| `a\n\n` | `a`, an empty line, then the front-end is asked again (a file gives the same) |
| `ab\ncd` read by `ВВКОД` | `a`, `b`, then `c`, `d` — code `10` never leaks out |

## Deliverables

- [ ] `src/prlib/include/prlib/io.hpp`, `src/prlib/src/io.cpp`: the pending buffer
      and the drain rule above, in `fetchLine`; a comment that states the rule, so
      the next reader does not have to derive it.  The rest of `IoContext`
      (`readToken`, `readWholeLine`, `readCodePoint` over `current_line_` /
      `current_pos_`) does not change — that is what keeps «остаток строки»
      working inside a chunk's line.
- [ ] **BOM**: strip one leading UTF-8 BOM with `stripByteOrderMark`
      (`utf8.cpp:165` — the same helper the lexer, the formatter and the module
      loader use) at the *start* of a stream: the first line of the base stream,
      the first line of each file opened by `ЧТЕНИЕ_ИЗ`, and the start of every
      chunk (an answer is a stream of its own).  A `U+FEFF` anywhere else stays
      data.  `$`-lines need nothing: they come from the lexer, which already
      strips the mark.
- [ ] `src/cli/protocol.cpp`: comment only — `answerInputRequest` hands over the
      reply's `text` as a chunk (the JSON string already carries `\n`, nothing to
      parse or split).
- [ ] `src/gui/prologd_gui/panels.py`: the hint of the multi-line console says what
      the field now means — «Строки — Ctrl+Enter» (`INPUT_PROMPTS`/`ask`, `panels.py:375,468`).
- [ ] `src/gui/prologd_gui/window.py`: no behaviour change (`_input_lines` and the
      `>` echo stay), but the doc-comment of `_on_input_request` must say that an
      answer is a chunk: a multi-line answer is several input lines.
- [ ] `src/gui/README.md`: the input section — what an answer is, and that the
      window never splits it for the interpreter (it splits the *queue* for its
      own counter and echo).
- [ ] `doc/help.typ`:
      * §6.7 gains one sentence: the window hands the answer over as a piece of
        the input, so several lines in the field are read one by one, as from a
        file (this is what makes §6.6's «остаток строки» true in the window too);
      * §6.4/§6.7 gain one sentence about the BOM: a byte-order mark at the start
        of a data file is not data (it is stripped, like the one in a source).
- [ ] `doc/gui.typ`: the input paragraph (lines ~548–585) is rewritten — it still
      describes the window **before** task_50 («поле ввода под панелью вывода»,
      «Пункт «Вид → Поле очереди ввода» прячет поле очереди», the console
      «под панелью» instead of under the goal line), and its «ответ на `ВВОДСТР`
      может быть фразой» becomes the new, precise meaning: one answer is a piece
      of the input, several lines = several answers.
- [ ] `ai/decisions.md`: **ADR-023** — «the front-end's answer is a piece of the
      input stream; a BOM is a file marker, not data» (ADR-022 is the last one).
- [ ] `ai/status.md`: the row and the board sentence after the work.

## Tests

- `src/tests/test_io_context.cpp` — the table above, through a handler: one line
  per read, the trailing `\n` with no phantom line, `""` = one empty line, an empty
  line in the middle, the token-then-remainder rule inside one chunk, `readCodePoint`
  never returning `10` between two lines of a chunk, and a BOM at the start of a
  buffer/file chunk vs a `U+FEFF` in the middle.
- `src/tests/test_builtins_io.cpp` — the same through `ВВОДСТР`, `ВВОДСИМВ`,
  `ВВКОД`, `ВВОДЦЕЛ` (a two-line answer read by two `ВВОДСТР`; a `ВВОДЦЕЛ` after a
  `ВВОДСТР` in one chunk), and a temp data file saved with a BOM.
- `src/tests/protocol_session.cmake` — one `input` reply carrying two lines: two
  `ВВОДСТР` reads, and no second `input_request` in between.
- GUI: `src/gui/tests/test_window.py` (a two-line console answer → the program gets
  two lines and the window is asked once; the queue still answers one line per
  request) and `src/gui/tests/protocol_smoke.py`.
- Nothing to change in `test_keywords`/`test_reference`: no name, arity or record
  is touched by this task.

## What must not change

- Files, stdin and `$`-lines: exactly as verified above (the same code path,
  `std::getline`).
- «`ЧТЕНИЕ_ИЗ` wins over the front-end», and `$`-lines are consumed first — the
  order in `fetchLine` stays as it is; a pending chunk simply waits while a file is
  redirected, and is read again when the input returns to the base stream.
- The window's queue: split by `\n`, blank lines dropped, `>` echo per answer,
  «осталось строк — N».  The split stays because the counter and the echo need it.
- The protocol: no new field, no new event — the answer's `text` is simply read as
  a chunk.
- The multi-line console field stays multi-line (decided 2026-10-02): under this
  rule it is «a block of input lines», not a trap.  A `QLineEdit` would only fit
  the opposite model, «one answer = one line», which cannot show the remainder rule
  in the window at all.

## Verification

1. `cmake --build build/windows-msvc --config Release` and
   `ctest --test-dir build/windows-msvc -C Release`.
2. By hand with `build\windows-msvc\src\cli\Release\prologd.exe`: the six
   experiments of the table above, which must now agree with each other.
3. The window: two lines in the console answer to `?ВВОДСТР(A), ВВОДСТР(B).` → `A`
   and `B` are the two lines and the console asks once; a data file with a BOM
   reads as if the mark were not there.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`), then
   `cmake --build build/windows-msvc --config Release --target docs` and a look at
   §6.7 and at the input pages of the window manual.

## Отложено (point 4, not this task)

`ВВОДСИМВ`/`ВВОДСТР` → one `ВВОД(Пер, Терминатор [, Приглашение])` stays on the
board.  The reasons, recorded so the question is not re-opened from scratch:

* only two of the four readers can be expressed by a terminator (`ВВОДЦЕЛ`/
  `ВВОДВЕЩ` also convert the type) — five names become four;
* `examples/lessons/lesson_07.pld:49,58,67,70,75` uses both readers, both with
  prompts, and the pair `ВВОДСИМВ(Команда), ВВОДСТР(Аргумент)` — the lesson *and*
  its `%!` expectations would be rewritten;
* a terminator moves a name into runtime data: a typo like `ВВОД(С, строчка)` stops
  being a load-time error with a suggestion and becomes a runtime error;
* the prompt is not a wart — `ВВОДЦЕЛ/2` and `ВВОДВЕЩ/2` have it too, so a third
  argument would be decoration in a family that stays mixed anyway.

If it is ever wanted, the cheap shape is sugar: add `ВВОД(С, строка)` ≡
`ВВОДСТР(С)` and retire the old spellings with advice — the `ИЛИ` → `ПЕРВОЕ` path
(task_44).
