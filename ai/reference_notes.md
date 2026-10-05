# PrologD semantics — distilled reference

This file condenses what the original interpreter does. It is the working
specification for the rewrite. Source of truth: the previous implementation,
<https://github.com/Ununus/prologd> — `prologd-help.txt`, `prlib/*.cpp`,
`prologd_test/test.txt`.

## 1. Lexical elements (original)

* Comment: `%` to end of line.
* Clause terminator: `;` or `.`.
* Rule arrow: `<-` (also `:-` was later accepted).
* Query prefix: `?`.
* Arithmetic expression: `#` … `#` with infix `+ - * / mod div` and `( )`.
* List: `[a,b|T]`, `[]`, `[a,b,c]`.
* String: `"…"` (UTF-8 / CP1251 bytes; length limit 128 in the original docs).
* Symbolic constant ("словосочетание"): letter followed by letters/digits/`_`.
* Variable (original!): **a single letter** (Latin or Cyrillic, any case),
  optionally followed by `'`; also `Name'` (name followed by apostrophe); `_`
  is anonymous.
* Names are case-sensitive.

## 2. Data types

| Type | Representation | Notes |
|------|----------------|-------|
| Integer | arbitrary precision | decimal only; overflow not reported |
| Float | IEEE double | decimal only |
| Arithmetic expression | compiled to an `expression` record | evaluated lazily during unification |
| Symbolic constant (atom) | interned string | |
| String | `"…"` | distinct from atom |
| Compound / function | `Name(arg, …)` | at least one argument; arbitrary arity |
| List | `[H|T]` with `[]` | a genuine list type, not `'.'/2` |

Lists are a first-class type. `[a|b]` where `b` is not a list is a
"list-like pair"; unification `пример(УКНЦ,YAMAHA,x)` with `пример(a,b,[a|b])`
produces `[УКНЦ|YAMAHA]`.

### Number/term unification details

* Integer literal unifies only with integer.
* Float unifies with integer when numerically equal (with the original's
  tolerance expression), and with float when exactly equal.
* Arithmetic expressions are evaluated during unification: unifying an
  expression with an integer/float computes it; unifying expression with
  expression compares computed integers (floats are **not** compared
  structurally — see `unexpr`).
* No occurs-check (cyclic terms are possible but not created by the documented
  predicates).

## 3. Output format

* Solution reporting: for each solution print `Name=Value` on its own line, one
  variable per line, variable order = order of first occurrence in the query.
  Anonymous variables and `_Name` are not printed.
* After all solutions: `ДА` if at least one solution, else `НЕТ`.
* `ВЫВОД/ПС` write to the current output stream without a trailing newline;
  the interpreter inserts a newline before `ДА`/`НЕТ` if the last write did not
  end with one.
* `ТИХО` suppresses `ДА`/`НЕТ` and the variable bindings.
* Floats are printed with trailing zeros stripped (`3.0` stays `3.`-trimmed to
  the shortest form; the original `toString` removes trailing `0` while the
  second-to-last char is not `.`), e.g. `6.6`, `3.0`.
* Strings print without quotes; atoms print as-is; lists as `[a,b]`;
  unbound variables as `_N` where `N` is the variable write number.
* `ВЕРСИЯ` prints the build date string.

## 4. Diagnostics

The original implementation numbered every error from 1 to 44 and printed the
offending source line followed by `<code> <text> (<code>)`:

```
1 Ошибка при разборе: foo(bar,"er).
1 Неверный формат строки (3)
```

**The numeric codes were deliberately dropped.** The new interpreter uses
semantic categories (`ErrorCode` in `prlib/diagnostics.hpp`: lexical, syntax and
runtime groups) and prints the usual compiler form:

```
<file>:<line>:<column>: error: <message>
```

The category is still available programmatically, but it is not part of the
user-facing interface, so codes are free to change. The original names are kept
in the old `err.h` header for reference only.

Category mapping used when porting code from the old interpreter:

| Old code | New category |
|----------|--------------|
| `InvalidCharacter` | `InvalidCharacter` |
| `InvalidStringFormat` | `InvalidStringLiteral` |
| `InvalidNumberFormat` | `InvalidNumberLiteral` |
| `AbsentSeparator`, `ErrorWhileParsingSentence` | `InvalidSentence` |
| `IncorrectUseListAsPredicate`, `IncorrectUseQuestion`, `IncorrectUseUnderscore`, `IncorrectUseExclamation` | `InvalidGoal` / `MisplacedQuestion` / `MisplacedUnderscore` / `MisplacedCut` |
| `AbsentMinus`, `AbsentClosingBraceOrDef`, `IncorrectUseDef` | `InvalidDefinition` |
| `AbsentFunctorBeforeOpenBracket` | `MissingFunctor` |
| `UnpairedBracketsIn*` | `UnpairedBracket` |
| `ErrorWhileParsingFunction` | `InvalidFunction` |
| `SignNotInArithmeticExpression` | `MisplacedSign` |
| `ErrorIn*ArithmeticExpression` | `InvalidArithmeticExpression` |
| `UnknownError` (bad arguments) | `TypeMismatch` |
| `DivisionByZero*` | `DivisionByZero` |
| `Mod/DivOperationAppliedToRealOperand` | `ArithmeticType` |
| `ErrorInBuiltinPredicateInt/Float` | `TypeConversion` |
| `ExecutionInterrupted` | `Interrupted` |
| `TooLongList` | `TooManySolutions` |
| `CannotOpenFileOut`, `IOError` | `IoError` |

## 5. Built-in predicates

Native built-ins are recognised before user clauses with the same name.

### Control / logic

| Predicate | Semantics |
|-----------|-----------|
| `!` | Cut. |
| `ЛОЖЬ` | Always fails. |
| `ВЫП(G)` | Meta-call `G`. Cut inside is transparent (cuts in caller). |
| `НЕ(G)` | Negation as failure, defined in Prolog as `НЕ(x)<-ВЫП(x),!,ЛОЖЬ; НЕ(_);` |
| `ИЛИ(A,B)` | Disjunction, defined as `ИЛИ(x,_)<-ВЫП(x),!; ИЛИ(_,x)<-ВЫП(x);` |
| `РАВНО(A,B)` | Unification, defined as unit clause `РАВНО(x,x).` |
| `ТРАССА`, `НЕТ_ТРАССЫ` | Toggle trace output. |
| `ТИХО` | Suppress solution printing for the rest of the run. |
| `ВЕРСИЯ` | Print build date. |

### Arithmetic

| Predicate | Semantics |
|-----------|-----------|
| `БОЛЬШЕ(A,B)` | `A > B`; int/float/string (lexicographic) comparison. |
| `МЕНЬШЕ(A,B)` | `БОЛЬШЕ(B,A)` (Prolog library). |
| `СЛОЖЕНИЕ(A,B,C)` | `C = A + B`; reversible in any two-of-three sense. |
| `УМНОЖЕНИЕ(A,B,C)` | `C = A * B`; if two are known, the third is derived (`/`). |
| `УМНОЖЕНИЕ(A,B,C,D)` | `A*B + C = D` with documented reversible cases (see help). |
| `СЛУЧ(N)` | Seed the RNG with `N`, or bind an unbound `N` to a random int. |
| `СЛУЧ(N,Lo,Hi)` | Bind `N` to a random int in `[Lo,Hi]`. |
| `ABS`, `SQRT`, `SIN`, `COS`, `TAN`, `EXP` | Two-argument: compute or compare; integer variants for `ABS`/`SQRT`. |
| `int(X)`, `float(X)` | Type conversion. |

`div`/`mod` are expression operators; `УМНОЖЕНИЕ/4` uses `div`/`mod` semantics
for the reversible cases.

### I/O

| Predicate | Semantics |
|-----------|-----------|
| `ВЫВОД(A1,…,An)` | Write terms (no newline), variable arity. |
| `ПС` | Newline; defined as `ПС<-ВВКОД(13),ВВКОД(10);` |
| `ВВКОД(X)` | With integer: write character code. With variable: read one char code. |
| `ВВОДЦЕЛ(X[,Caption])` | Read integer, unify; on file input uses stream extraction. |
| `ВВОДВЕЩ(X[,Caption])` | Read float. |
| `ВВОДСИМВ(X[,Caption])` | Read one whitespace-delimited token as atom/string. |
| `ВВОДСТР(X[,Caption])` | Read a whole line. |
| `ЧТЕНИЕ_ИЗ(X)` | Close current input; open named file, `""`/`con:` = keyboard; with variable, expose the current input file name. |
| `ЗАПИСЬ_В(X)` | Same for output; `""`/`con:` = screen. Missing extension gets `.pld`. |
| `ЖДИ(N)` | Sleep `N` ms; always true. |

Input semantics: if an input file is open, whitespace-separated tokens are
consumed; otherwise the interactive reader is used. In the original CLI a line
starting with `$` in the source preloads one input line (test harness feature) —
the port had it too and dropped it in part 81, at the user's request.

### Strings

| Predicate | Semantics |
|-----------|-----------|
| `БУКВА(S,P)` | `S[P]` is a letter; if `P` is a variable, bind first letter position (1-based). |
| `ЦИФРА(S,P)` | Same for digits. |
| `СЦЕП(A,B,C)` | Concatenation, reversible in each argument. |
| `КОПИЯ(S,Pos,Len,Sub)` | Substring extraction / search (see help for the 5 modes, negative `Len` = search from the right). |
| `ДЛИНА(S,N)` | String length; defined as `ДЛИНА(x,y)<-КОПИЯ(x,1,y,x);` |
| `СТРСПИС(S,L)` | String ↔ list of char codes (mod 255 on the way back). |
| `СТРЦЕЛ(S,N)` | String ↔ integer. |
| `СТРВЕЩ(S,X)` | String ↔ float. |
| `ЦЕЛВЕЩ(N,X)` | Integer ↔ float. |

Note: `occ_line` in the original reads a `recordstring`, so string built-ins
accept string literals and symbolic constants through the same storage. In the
new implementation both `"abc"` and `abc` should be accepted where the original
accepted them.

### Type tests

`ПЕР(X)` (unbound variable), `ЦЕЛ(X)`, `ВЕЩ(X)`, `СИМВ(X)` (atom or string),
`СПИСОК(X)` (list or `[]`).

### Program database

| Predicate | Semantics |
|-----------|-----------|
| `СКОЛЬКО(Name,N)` | Number of clauses whose head functor is `Name`. |
| `ПРЕДЛ(Name,Idx,Head,Goals)` | Access clause number `Idx` (1-based); `Goals` is the list of body goals; reversible. |
| `ТЕРМ(Term,List)` | Convert between a term and `[Functor,Arg…]`. |
| `ДОБ(Head,Goals,Pos)` | Assert a clause at position `Pos`; `Pos < 2` or missing ⇒ first; `Goals=[]` ⇒ fact. |
| `УДАЛЕНИЕ(Name,Idx)` | Remove clause `Idx` of `Name`. |

### Graphics (abstract stubs)

`ТОЧКА/3`, `ЛИНИЯ/5`, `ОКРУЖНОСТЬ/4`, `ЗАКРАСКА/3` call the host's drawing
callbacks (originally Qt `QPainter`, originally `maxgrx=1024`, `maxgry=768`).
In the console build they must be no-ops behind an interface.

### New: `НАЙТИВСЕ/3`

Standard `findall/3`:

```
?НАЙТИВСЕ(И, студент(И,Ф), А).            % А = [вова,данил,ваня]
?НАЙТИВСЕ([И,Ф], студент(И,Ф), А).        % А = [[вова,корчагин],[данил,ахмеров],[ваня,петров]]
```

Changes made by the goal are undone; the collected template instances are
copied so they share no variables with the rest of the program. The result list
preserves solution order.

## 6. Original control machine (for reference)

`control.cpp` is a 6-state machine:

* state 2 `PrepereNewTarget` → state 3
* state 3 `Yes` → pick next goal or report a solution
* state 4 `ControlStep` → try the next clause of the current predicate
* state 5 `No` → backtrack one environment
* state 6 `Builtin` → dispatch a built-in
* state 1 `Error` → stop

Stacks: control stack (`vst_con`, 7 words per environment), variable stack
(`vst_vr1` term, `vst_vr2` frame), trail (`vst_trail`), unification stack
(`vbf`), output buffer (`vBPT`). It uses structure sharing: a variable is a
`(frame, num)` offset pair. The rewrite replaces this with value terms + an
explicit trail, but must preserve observable behaviour.

## 7. Historical quirks worth preserving or consciously dropping

Preserve:

* `СЛОЖЕНИЕ` is native *and* has a Prolog library clause that is shadowed;
  `СКОЛЬКО(СЛОЖЕНИЕ,N)` therefore reports 1.
* `РАВНО`, `МЕНЬШЕ`, `ПС`, `ДЛИНА`, `НЕ`, `ИЛИ` are pure Prolog library
  clauses loaded at startup.
* No occurs-check.
* `ВЫВОД` never appends a newline; the harness adds one before `ДА`/`НЕТ`.
* Strings and symbolic constants are both accepted by string predicates.

Drop (and document in `prologd-diff.typ`):

* single-letter variables;
* trailing-apostrophe variables;
* CP1251 anywhere in the pipeline;
* manual MP1251 conversions;
* global mutable interpreter state (`term`, `frame`, `arg`, `flaglist`,
  `count_var`, `target_number`) — replace with explicit engine state.
