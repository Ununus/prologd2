# task_54 — the shell's answer is a piece of the input stream (and a BOM is not data)

**Status:** done (2026-10-03) — all three points are in the language and in the window: the
shell's answer is a piece of the input stream, a BOM is a marker at the start of a stream,
and the multi-line console stayed and got a precise meaning.  The fourth point (merging
`ВВОДСИМВ`/`ВВОДСТР` into `ВВОД(Пер, Терминатор)`) was out of scope and stays deferred —
see "Deferred".
**Depends on:** task_50 (the console moved under the goal line, the queue became the «Ввод»
tab), task_29 (the «Спрашивать ввод» switch), task_11 (the reading built-ins)
**Milestone:** post-M10

## Goal

Make every source of input obey **one rule**, so that a program written against a file
behaves the same in the window:

* a file (`-i`, `ЧТЕНИЕ_ИЗ`), stdin and a front-end answer are all *pieces of
  one input stream*;
* a *line* is what lies between two `\n`, and the end of a piece ends its last line —
  exactly like the end of a file;
* therefore a `\n` inside an answer is a line separator, not a character in the string.

Today only the front-end breaks the rule: its answer is put into `current_line_` whole
(`io.cpp:105` + `fetchLine`, `io.cpp:58-72`), so the answer is one line however many `\n` it
contains.

Verified 2026-10-02 with the built interpreter — the experiments this task turns into
tests:

| source | what happens today |
|---|---|
| `-i` file, LF, with an empty line and a leading space | one line per read, `\r`/`\n` dropped, an empty line is an empty string, the last line without a terminator is read, EOF is a failure |
| `-i` file, CRLF | `len=4 codes=[99,114,108,102]` — no `13` |
| `ВВОДСИМВ` + `ВВОДСТР` on `name rest of it` (file) | `name` and ` rest of it` — the remainder of the same line, the leading space kept |
| `ЧТЕНИЕ_ИЗ`, stdin | the same rule |
| **file with a BOM** (Notepad's default) | `codes=[65279,98,111,109,…]` — the BOM is *not* stripped and becomes the first character of the first line |
| **window** (console answers, a multi-line field) | `ВВОДСТР` returns the whole answer *with* the `\n`s; `ВВОДСИМВ` then `ВВОДСТР` gives a remainder that starts with `\n`; `ВВКОД` sees code `10` between the lines |

The window's *queue* needs no change: the window splits it into answers so that it can show
the counter and echo each answer with `>` — that split is bookkeeping, not reading, and each
answer is a one-line chunk anyway.

## The rule of a chunk (the whole implementation, in three lines)

```
fetchLine:  file (if ЧТЕНИЕ_ИЗ redirected) → pending chunk → base stream
pending_:   take up to '\n' (dropping a '\r' before it); no '\n' → the whole rest,
            because the end of the chunk ends its last line; then ask the front-end for
            another chunk only when pending_ is empty
```

The consequences, all of them wanted:

| answer | lines |
|---|---|
| `first` | `first` |
| `first`, then a second `ВВОДСТР` | the front-end is asked again (the chunk is used up) |
| `a\nb` | `a`, `b` |
| `a\n` | `a`, then the front-end is asked again — **no phantom empty line** |
| `\n` | one empty line |
| `""` (an empty answer, as today) | one empty line |
| `a\n\n` | `a`, an empty line, then the front-end is asked again (a file gives the same) |
| `ab\ncd` read by `ВВКОД` | `a`, `b`, then `c`, `d` — code `10` never leaks out |

## Deliverables

* `src/prlib/include/prlib/io.hpp`, `src/prlib/src/io.cpp`: the pending buffer and the drain
  rule above, in `fetchLine`, with a comment that states the rule so the next reader does
  not have to derive it.  The rest of `IoContext` (`readToken`, `readWholeLine`,
  `readCodePoint` over `current_line_`/`current_pos_`) does not change — that is what keeps
  «остаток строки» working inside a chunk's line.
* **BOM**: strip one leading UTF-8 BOM with `stripByteOrderMark` (`utf8.cpp:165` — the same
  helper the lexer, the formatter and the module loader use) at the *start* of a stream: the
  first line of the base stream, the first line of each file opened by `ЧТЕНИЕ_ИЗ`, and the
  start of every chunk (an answer is a stream of its own).  A `U+FEFF` anywhere else stays
  data.
* `src/cli/protocol.cpp`: a comment only — `answerInputRequest` hands over the reply's
  `text` as a chunk (the JSON string already carries `\n`, nothing to parse or split).
* `src/gui/prologd_gui/panels.py`: the hint of the multi-line console says what the field
  now means — «Строки — Ctrl+Enter» (`INPUT_PROMPTS`/`ask`, `panels.py:375,468`).
* `src/gui/prologd_gui/window.py`: no behaviour change (`_input_lines` and the `>` echo
  stay), but the doc-comment of `_on_input_request` must say that an answer is a chunk: a
  multi-line answer is several input lines.
* `src/gui/README.md`: the input section — what an answer is, and that the window never
  splits it for the interpreter (it splits the *queue* for its own counter and echo).
* `doc/help.typ`: §6.8 gains one sentence — the window hands the answer over as a piece of
  the input, so several lines in the field are read one by one, as from a file (this is what
  makes §6.7's «остаток строки» true in the window too); §6.5/§6.8 gain one sentence about
  the BOM: a byte-order mark at the start of a data file is not data (it is stripped, like
  the one in a source).
* `doc/gui.typ`: the input paragraph (lines ~548–585) is rewritten — it still described the
  window **before** task_50 («поле ввода под панелью вывода», «Пункт «Вид → Поле очереди
  ввода» прячет поле очереди», the console «под панелью» instead of under the goal line),
  and its «ответ на `ВВОДСТР` может быть фразой» becomes the new, precise meaning: one
  answer is a piece of the input, several lines = several answers.
* `ai/decisions.md`: **ADR-023** — "the front-end's answer is a piece of the input stream;
  a BOM is a file marker, not data" (ADR-022 is the last one).
* `ai/status.md`: the row and the board sentence after the work.

## Tests

* `src/tests/test_io_context.cpp` — the table above, through a handler: one line per read,
  the trailing `\n` with no phantom line, `""` = one empty line, an empty line in the middle,
  the token-then-remainder rule inside one chunk, `readCodePoint` never returning `10`
  between two lines of a chunk, and a BOM at the start of a buffer/file chunk against a
  `U+FEFF` in the middle.
* `src/tests/test_builtins_io.cpp` — the same through `ВВОДСТР`, `ВВОДСИМВ`, `ВВКОД`,
  `ВВОДЦЕЛ` (a two-line answer read by two `ВВОДСТР`; a `ВВОДЦЕЛ` after a `ВВОДСТР` in one
  chunk), and a temp data file saved with a BOM.
* `src/tests/protocol_session.cmake` — one `input` reply carrying two lines: two `ВВОДСТР`
  reads and no second `input_request` in between.
* GUI: `src/gui/tests/test_window.py` (a two-line console answer → the program gets two
  lines and the window is asked once; the queue still answers one line per request) and
  `src/gui/tests/protocol_smoke.py`.
* Nothing to change in `test_keywords`/`test_reference`: no name, arity or record is touched
  by this task.

## Decisions

1. **The line is produced by `IoContext`, not by the shell.**  A chunk is the *stream's*
   state (`pending_` + `pending_pos_`), so the rule lives in `fetchChunkLine` and the shell
   simply hands the answer over whole.  One edit covers every reading predicate at once:
   `ВВОДСТР`, `ВВОДСИМВ`, `ВВКОД` and `ВВОДЦЕЛ` read through `current_line_`/`current_pos_`
   and know nothing about chunks.
2. **The end of a chunk ends a line.**  Everything else follows: `a\n` is one line (the next
   read asks again instead of inventing an empty one), `""` is one empty line (as before),
   `a\n\n` is two (as in a file).  Counting the newline as part of the text — that was the
   old mistake.
3. **"The chunk is used up" is decided by the position, not by a flag.**
   `pending_pos_ < pending_.size()`; an empty answer is therefore handled separately (one
   empty line) and the next request goes to the shell again.
4. **The BOM is stripped at the start of a stream.**  The same `stripByteOrderMark` in three
   places: the first line of the base stream, the first line of each `ЧТЕНИЕ_ИЗ` file, and
   the start of every chunk; the flags are `base_stream_started_`/`file_stream_started_`,
   the second reset in `openInput`.
5. **The shell still splits its own chunk.**  The queue is the «Ввод» tab, and it is split
   for the sake of `>` and «осталось строк — N»: that is bookkeeping, not reading.
6. **The multi-line console field stays multi-line** (decided 2026-10-02): under this rule
   it is "a block of input lines", not a trap.  A `QLineEdit` would only fit the opposite
   model, "one answer = one line", which cannot show the remainder rule in the window at
   all.

## What the round found

* **The edit turned out to be in exactly one place.**  Neither the solver, nor the call
  checks, nor the protocol changed: `input.text` could always contain `\n`, and `IoContext`
  was already the single door for all sources.
* **The old test did not catch it.**  `interactive reads go through the input request
  handler` is written about chunks, but every one of its answers is a single line, so the
  bug lived past it.  What was needed is an answer with a newline inside — and there were no
  such checks.
* **An empty line in the middle is compared against a file.**  The test reads `а\n\nб` from
  a chunk and the same bytes from a temporary file: the behaviour must agree, otherwise the
  edit is pointless.
* **A BOM in the middle of a chunk is data**, and that is pinned too: only the start is
  cleaned.
* **The window asks once per chunk.**  The GUI check installs a "traitor" dialog: if the
  second line went to the dialog, the test would fail instead of staying silent.
* **One small thing along the way:** the hint of the «Спрашивать ввод» setting described the
  window before task_50 («строки в поле под выводом»); it now names the console under the
  goal line.

## What must not change

* Files and stdin: exactly as verified above (the same code path,
  `std::getline`).
* "`ЧТЕНИЕ_ИЗ` wins over the front-end" — the order in
  `fetchLine` stays as it is; a pending chunk simply waits while a file is redirected and is
  read again when the input returns to the base stream.  (The `$` lines that used to be read
  before the file were removed in part 81, so `fetchLine` now starts with the file.)
* The window's queue: split by `\n`, blank lines dropped, `>` echo per answer, «осталось
  строк — N».  The split stays because the counter and the echo need it.
* The protocol: no new field, no new event — the answer's `text` is simply read as a chunk.

## Verification

1. `cmake --build build/windows-msvc --config Release` and `ctest --test-dir
   build/windows-msvc -C Release`.
2. By hand with `build\windows-msvc\src\cli\Release\prologd.exe`: the six experiments of the
   table above, which must now agree with each other.
3. The window: two lines in the console answer to `?ВВОДСТР(A), ВВОДСТР(B).` → `A` and `B`
   are the two lines and the console asks once; a data file with a BOM reads as if the mark
   were not there.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`), then
   `cmake --build build/windows-msvc --config Release --target docs` and a look at §6.8 and
   at the input pages of the window manual.

## Deferred (point 4, not this task)

`ВВОДСИМВ`/`ВВОДСТР` → one `ВВОД(Пер, Терминатор [, Приглашение])` stays on the board.  The
reasons, recorded so that the question is not re-opened from scratch:

* only two of the four readers can be expressed by a terminator (`ВВОДЦЕЛ`/`ВВОДВЕЩ` also
  convert the type) — five names would become four;
* `examples/lessons/lesson_07.pld:49,58,67,70,75` uses both readers, both with prompts, and
  the pair `ВВОДСИМВ(Команда), ВВОДСТР(Аргумент)` — the lesson *and* its `%!` expectations
  would have to be rewritten;
* a terminator moves a name into runtime data: a typo like `ВВОД(С, строчка)` stops being a
  load-time error with a suggestion and becomes a runtime error;
* the prompt is not a wart — `ВВОДЦЕЛ/2` and `ВВОДВЕЩ/2` have it too, so a third argument
  would be decoration in a family that stays mixed anyway.

If it is ever wanted, the cheap shape is sugar: add `ВВОД(С, строка)` ≡ `ВВОДСТР(С)` and
retire the old spellings with advice — the `ИЛИ` → `ПЕРВОЕ` path (task_44).
