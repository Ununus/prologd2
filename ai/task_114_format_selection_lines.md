# task_114 — a formatted selection keeps its lines

**Status:** done (2026-10-24) — part 180
**Depends on:** task_30/`Ctrl+I` (the formatter in the window), task_114's «только
выделенное»
**Milestone:** 2.6.0

## The two reports

With «только выделенное» on:

1. `?length([1, 2, 3], Д). % выделена эта строка` selected **without** its line
   break came back with an empty line under it.
2. Two full comment lines selected lost the **second** one.

## Cause 1: the answer is a program, the selection is not

`formatSource` answers with a whole program, and a program ends with a line
terminator.  The window replaced the selected range with that answer verbatim, so a
selection that did not include its own `\n` left two: the formatted line and an empty
one.  Fixed in `_on_formatted`: when a region is replaced and the region's own text
does not end with a newline, one trailing newline of the answer is dropped.  The
restored selection is then the length of the text actually put in, so it covers the
line and not the empty one.

## Cause 2: the end-of-file marker counted as a statement

`Formatter::buildStatements` walked the token list to its end, and the list ends with
`TokenKind::EndOfFile`.  A marker is not a statement, but it made one — empty,
unterminated, starting at the end of the text.  Everything after the last real dot
then lay in a gap **between** statements, and `emitLeadGap` reads the last line of
such a gap as *the indentation in front of the next statement* and drops it.  A text
whose last line has no newline therefore lost that line: the second comment of the
report, a lone `% почему` after the last fact, the last line of a file saved without
a final newline.

Fixed twice, because there were two assumptions in one place:

- `buildStatements` stops at `EndOfFile` — the marker is not a statement;
- `emitLeadGap` treats its last line as content when `at_eof` is set: at the end of
  the text there is no next statement whose indentation it could be.  With no
  statements at all the whole text is that gap, so `run` now passes
  `at_start = statements.empty()` as well — otherwise the first line was read as the
  continuation of a line no statement had ended.

## Checks

- `test_formatter.cpp`: «a last line without a final newline survives the
  formatter» — comment-only text, a fact followed by a comment, a blank line kept,
  the terminated case unchanged, and a `selection_only` fragment.
- `test_window.py`: «a formatted selection keeps its lines» — the reported query with
  its trailing comment (selected with and without the line break), and the two
  comments (the last one without a newline) with the trailing spaces of the first
  trimmed.

`ctest` 424 tests, 29 GUI suites and `protocol_smoke.py` green.

## What is deliberately not done

The formatter's answer keeps its final newline: it is a program, and the protocol
says so.  Which line terminator is *replaced* is the caller's question, and that is
where the answer is now trimmed.
