# task_30 — GUI: the program formatter

**Status:** not started
**Depends on:** task_21 (protocol), task_25 (documents), task_29 (settings)
**Milestone:** M11

## Goal

A **Форматировать** action with two modes, chosen in the settings, plus
formatting of the selection only:

* **мягкое** — keep the author's line breaks, but move the goals that overflow
  the width to a continuation line, indented;
* **жёсткое** — one goal of a clause body per line, continuation lines indented.

Indent is configurable (default: 1 tab stop, tabs or spaces) and trailing
whitespace is always removed.

```
Правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),
функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).
```
soft (`ширина 80`, `отступ 1 таб`) →
```
Правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),
	функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).
```
hard →
```
Правило(а,б,с):-функция1(а,б,с),
	функция2(а,б,с),
	функция3(а,б,с),
	функция4(а,б,с),
	функция5(а,б,с),
	функция6(а,б,с).
```

## Where it lives

The formatter goes into `prlib` and is reached through the CLI and the protocol;
the GUI is a client.  Laying out a clause requires knowing where the body starts
and which comma separates two *goals* rather than two arguments — that is the
grammar, and the grammar already exists once, in the parser.  A second
implementation in Python would drift.

- [ ] `prlib`: `formatSource(text, FormatOptions) -> FormatResult {text,
      changed, diagnostics}`, `FormatOptions {mode: none|soft|hard, width
      (default 80 columns), indent_steps (default 1), indent_unit: tab|spaces,
      selection_only}`.
- [ ] Algorithm: lex → parse into statements with their `SourceLocation` →
      rebuild the text by inserting and removing **whitespace only**.  The bytes
      of every token are copied verbatim, so quoting, `#expr#` bodies, comments
      and Cyrillic text cannot be damaged, and nothing is re-printed from the
      AST.
- [ ] **Trailing whitespace never survives**: the reference examples above were
      written with a space after the final comma and the formatted text has
      none.
- [ ] **Idempotence**: `format(format(x)) == format(x)`, enforced by a property
      test over `examples/*.pld`.
- [ ] **Semantics preserved**: the formatted program must produce the same
      output as the original for every example (golden test).
- [ ] Comments: a trailing `% …` stays on its goal's line, a comment on its own
      line stays on its own line, and a comment is never moved across a goal
      boundary.
- [ ] Empty lines: at most one blank line *between* clauses; blank lines inside
      a clause are kept (the reference implementation deleted them — see below).
- [ ] Input that does not parse: return the text unchanged with the diagnostics,
      so the GUI can report "не удалось разобрать" and mark the line instead of
      mangling the buffer.
- [ ] Selection mode: the selected fragment is parsed as a statement sequence;
      a partial clause (the caret is in the middle of a body) is formatted up to
      its last complete goal and the remainder is left alone.
- [ ] CLI: `prologd --format[=soft|hard] [--format-width N] [--format-indent N]
      [--format-unit tab|spaces] [-s FILE]` → formatted text on stdout, exit 0;
      exit 2 with the usual diagnostic when the source does not parse.  No `-o`
      needed, so it composes with the shell.
- [ ] Protocol v2: `{"cmd":"format","text":…,"mode":"hard","indent":2,"width":80}`
      → `{"event":"formatted","text":…}` or an `error` event; the request must
      be answerable between queries (it does not need the engine).
- [ ] GUI: `prologd_gui/formatter.py` (Qt-free client), the action **Форматировать**
      `Ctrl+I` with a mode dropdown on the toolbar, "форматировать только
      выделенное" in the settings and a context-menu entry; the replacement is
      one undo step, the caret and the selection survive it, and the cursor does
      not jump to the top of the document.

## Why the reference implementation is a reference, not a source

`ai/_ref/prolog/src/gui/Editor.cpp:508 formatDocument()` (see also
`canBeFunction` at the top of the same file) is a hand-rolled character state
machine over the plain text:

* `canBeFunction` decides "a call starts here" by scanning for the first
  `:`, `.`, `,` or `;` at parenthesis depth 0 — a guess, not a parse;
* it mutates the string it is scanning (`str.insert`) and compensates with
  hand-written index arithmetic (`st += 2`), which is where the corner cases
  live;
* it deletes blank lines inside a clause (`str_list.erase(...)`), so formatting
  destroys the author's grouping and is **not idempotent**;
* it always breaks after a comma, so there is no мягкое mode at all;
* it reformats the whole document — no selection mode;
* it recognises `:-`/`<-` but nothing else about the statement structure.

Keep it as a reference for the *intent* (the two target shapes above) and for
the colour conventions elsewhere; do not port it.

## Tests

- [ ] Catch2 golden tests for both examples above, byte-exact (this is the
      acceptance criterion the user actually wrote down).
- [ ] Catch2: trailing comment kept, comment-only line kept, `#1+2#` untouched,
      quoted atoms untouched, a one-goal clause unchanged, `;` terminator,
      `<-` rule, unparsable input returned unchanged, idempotence.
- [ ] CTest: `prologd --format=hard -s examples/*.pld` output re-parses, and
      running the formatted file yields the same output as the original.
- [ ] Python: `src/gui/tests/test_formatter.py` (Qt-free) against the built
      interpreter — request/response shape and an error case.

## Decisions (from the user, 2026-09-29)

* Trailing whitespace is removed — no space after the last comma on a line.
* Continuation indent defaults to **one tab** (was two in the examples above);
  the unit and the count stay configurable.
* The soft width is **80 columns**.  With 80 the built-in example splits exactly
  as drawn: goals 1–3 end at column 66 and goal 4 would reach 83, so the break
  falls before goal 4.
* Tab size for the *display* of a tab is the editor's tab-width setting
  (task_29) — the formatter emits one tab, the editor decides how wide it looks.

## Acceptance

**Форматировать** turns either example into the shape above, the same action on
an already formatted document changes nothing, formatting a selection behaves
like formatting that fragment alone, a broken program is reported instead of
rewritten, and the formatted `examples/` still pass their golden tests.
