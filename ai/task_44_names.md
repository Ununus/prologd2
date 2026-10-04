# task_44 — names: `ПЕРВОЕ` instead of `ИЛИ`, `НАЙТИВСЕ` without the ё

**Status:** done.

## Why

1. **`ИЛИ/2` was not named after what it is.**  The name was honest for the original
   dialect: there was no disjunction in it at all, and "or" was the best word available.
   Why exactly that word is visible in the original (`Ununus/prologd`,
   `src/prologd-help.html`, checked 2026-10-03):

   * **the "or" sign was taken.**  The statement terminator of the original language is
     `;` (`Факт ::= Предикат;`), so there was nothing else to say "one of the two" with
     inside a rule: either two clauses with one head, or the predicate `ИЛИ/2`;
   * **the name described the condition, not the mechanism.**  The manual explains it from
     both sides: "Предикат ИЛИ истинен тогда и только тогда, когда хотя бы один из
     аргументов истинен" — "or" as a logical connective — and right after that
     procedurally: "попытаться выполнить цель1. Если цель1 выполнена успешно, то
     предикат ИЛИ истинен, а цель2 не выполняется, в противном случае происходит попытка
     выполнить цель2" — "or" as `||` in ordinary languages, short-circuit.  For a school
     audience that is the familiar "or";
   * **it was a library predicate.**  The manual has a section "Пример: реализация
     предикатов НЕ, ИЛИ" with the two clauses
     `ИЛИ(цель1',_) <- ВЫП(цель1'),!;` / `ИЛИ(_,цель2') <- ВЫП(цель2');` — exactly the
     ones the port inherited in `engine.cpp` until this task;
   * **"or" was a working word of the dialect.**  Same place:
     `БОЛЬШЕ_ИЛИ_РАВНО(x,y) <- НЕ(МЕНЬШЕ(x,y));`, and lesson 1 explains the cut as
     "исключающее ИЛИ".

   The name described an *intention* ("either this or that"), not what the predicate
   does, and it was true while "or" meant only that in the language.  But after task_41
   disjunction exists — it is `;`.  `ИЛИ` takes **the first solution of the first goal
   that succeeds**: `?ИЛИ(РАВНО(X,1), РАВНО(X,2)).` answers `X=1` and never gives `X=2`.
   The name promises enumeration over two branches, and promises it wrongly.

2. **`НАЙТИВСЁ` had drifted from the original.**  In the task (`task_13_findall.md`) and in
   the notes on the original (`reference_notes.md`) the name is written without the ё:
   `?НАЙТИВСЕ(И,студент(И,Ф),А).`  The port added the ё by itself.  Without it the name is
   both easier to type and more precise to read: "find all [solutions]", not "everything".

## The decision (chosen by the user)

* `ИЛИ` → `ПЕРВОЕ` (the English name `or` → `first`).  The old name is **removed**: calling
  it is a load error with the message "«ИЛИ» переименовано: теперь это «ПЕРВОЕ(Ц1, Ц2)», а
  дизъюнкция — «A ; B»".
* `НАЙТИВСЁ` → `НАЙТИВСЕ`.  The old spelling stays reserved (it is not a variable!) and
  gives the ordinary warning with a hint: "не найдено: НАЙТИВСЁ/3; возможно, НАЙТИВСЕ/3".
  No table of its own is needed — the edit distance to the new name is 1 and the hint comes
  out by itself.

## What was done

* `lexer.cpp`: `ПЕРВОЕ`/`first` in the main set, plus a new set `kRetiredBuiltinNames`
  (`ИЛИ`, `НАЙТИВСЁ`) — the lexer keeps those as predicate names, but
  `reservedBuiltinNames()` does not report them: the keyword table, the GUI completion and
  `--list-keywords` do not offer retired spellings.
* `checks.cpp`: the table `kRetiredNames` and a load error for calling a retired name (the
  check runs before the lookup in `known`, where the retired name no longer exists);
  `ПЕРВОЕ/2` expands as a meta-call — both its arguments are goals.
* `engine.cpp`: the two library clauses `ИЛИ(X,_) :- ВЫП(X), !.` / `ИЛИ(_,X) :- ВЫП(X).`
  are removed — otherwise `ИЛИ` would keep working through the database.  (The remaining
  shadowed library clauses are removed by task_43.)
* Tests: `test_keywords.cpp` (retired names are not offered, `ПЕРВОЕ/2` is),
  `test_lexer.cpp` (a retired spelling is still a name, not a variable),
  `test_diagnostics.cpp` (the message about `ИЛИ` word for word; the hint for `НАЙТИВСЁ`),
  and in `test_builtins_control.cpp` the cases stopped calling `ПЕРВОЕ` "disjunction".
* Documents: `help.typ` §4.5/§4.6 and appendix 17; `prologd-diff.typ` §6 (the stale "the
  behaviour is preserved" wording brought in line with task_41), §13, §14, §16 and new §17
  (`НАЙТИВСЕ` without the ё) and §18 (`ПЕРВОЕ` instead of `ИЛИ`); `technical.typ` §6.4;
  `lessons.typ`; lesson 4 and its section 5; `ai/conventions.md`, `ai/status.md`, the
  table of task_39.

## Checks

* ctest 221 → 223, Catch2 208 → 210 cases; the GUI suite (venv) and the five Typst
  documents build.
* By hand: `?НАЙТИВСЁ(_, ЛОЖЬ, _).` →
  `1:2: warning: не найдено: НАЙТИВСЁ/3; возможно, НАЙТИВСЕ/3` (exit 0);
  `?ИЛИ(ЛОЖЬ, ЛОЖЬ).` → `1:2: error: «ИЛИ» переименовано: …` (exit 2).
