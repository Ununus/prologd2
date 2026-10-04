# task_57 — a failed `ЗАПИСЬ_В` left the output on a closed stream

**Status:** done (2026-10-03) — the defect was found while working on task_54,
reproduced on the built interpreter, fixed with one line and pinned by two tests.
**Depends on:** task_11 (the I/O predicates), task_54 (the round of I/O fixes — where
`IoContext` was under the same microscope)
**Milestone:** post-M10

## What was wrong

`IoContext::openOutput` closed the current file **before** trying to open the new one:

```cpp
file_output_.close();
output_to_file_ = false;
output_name_.clear();
if (path.empty() || ...) { output_ = base_output_; return true; }
file_output_.open(path);
if (!file_output_.is_open()) {
  return false;            // output_ still points at the CLOSED file_output_
}
```

`output_` was assigned only on success, so after a failed redirect it kept pointing at
the closed `file_output_`.  Writing to a closed `std::ofstream` is silently lost (the
`badbit` flag, which nobody looks at), so everything vanished until the next successful
`ЗАПИСЬ_В`: the program's output *and* the interpreter's own answers — `ДА`/`НЕТ` and
bindings are printed through the same `IoContext`.

Reproduced on 2026-10-03 on `prologd.exe`:

```prolog
?ЗАПИСЬ_В("tmp_out.txt").
?ЗАПИСЬ_В("нет_такого_каталога/файл.txt").
?ВЫВОД("после").
?ПС.
?ЗАПИСЬ_В("").
?ВЫВОД("снова на экран").
?ПС.
```

Before the fix the screen showed `ДА`, `снова на экран`, `ДА`, an empty line, `ДА`: the
`НЕТ` of the failed redirect and the whole third goal were gone.  After the fix the
screen shows `НЕТ`, `после`, `ДА`, `ДА`, `снова на экран`, `ДА`, an empty line, `ДА`.

It was hard to notice precisely because it was **silent**: `ЗАПИСЬ_В` honestly fails, no
diagnostic is printed, and the output simply stops appearing.  The neighbouring branch —
input — behaved correctly: a failed `ЧТЕНИЕ_ИЗ` returned reading to the keyboard, because
`fetchLine` checks `input_from_file_`, not a stream pointer.

## The fix

One rule for both streams: **a failed redirect returns the stream to where it would be
without the attempt**.

```cpp
file_output_.close();
output_to_file_ = false;
output_name_.clear();
output_ = base_output_;      // <- the only new line
```

The alternative — "open first, close only on success" — was rejected: it would leave the
program writing into the *previous* file after a failed redirect, that is, silently
ignoring the request.  Nobody proposed that for input either: there reading returns to
the keyboard, not to the previous file.

## What did not change

* A successful `ЗАПИСЬ_В` and `ЗАПИСЬ_В("")` as they were; `outputName()` after a failure
  was empty before (the name was cleared before the attempt), and that is now pinned by a
  test.
* `openInput` was not touched: it was right.
* Neither the dispatcher nor the solver: `builtinTell` just reads `false` from
  `openOutput`.

## Checks

* `src/tests/test_builtins_io.cpp`, the case "a failed redirect returns the output to the
  screen": a successful redirect into a file, a failed one (output and answers stay on
  the screen), `ЗАПИСЬ_В(Имя)` after the failure gives an empty name, then a return into
  the file with an empty string.
* `src/tests/test_io_context.cpp`, the case "a redirect that fails leaves the output on
  the base stream": the same at the `IoContext` level — `write` after a failure lands in
  the base stream, `outputName()` is empty, and a successful redirect after a failed one
  works.
* `doc/help.typ` §6.9: one sentence about where the output returns to (symmetric with the
  sentence about the keyboard for `ЧТЕНИЕ_ИЗ`).

## Notes

* A failed `ЗАПИСЬ_В` inside a *directive* (`:- ЗАПИСЬ_В("...").`) is simply false too:
  loading continues and the output goes to the screen — which is what the manual now
  describes.
* The defect living next to `fetchLine` is no accident: both fixes (task_54 and this one)
  are about one thing — "the current stream" must be a stream one can really write to or
  read from.
