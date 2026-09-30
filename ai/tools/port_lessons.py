#!/usr/bin/env python3
"""Port the original PrologD lesson/example programs to the new syntax.

Rules (see ai/reference_notes.md and doc/prologd-diff.typ):

* a single letter (Latin or Cyrillic, any case) was a variable -> rename it to
  an upper-case name; if the upper-case counterpart is also used as a variable
  anywhere in the file, append ``_`` to keep the mapping injective;
* a name ending in ``'`` was a variable -> capitalise the first letter and drop
  the apostrophe;
* a multi-letter name starting with an upper-case letter was an atom: it becomes
  a predicate (lower-cased) when it is immediately followed by ``(``, otherwise
  it is quoted;
* reserved built-in names, comments, strings and quoted atoms are copied
  verbatim.

Usage:  python3 ai/tools/port_lessons.py <src-dir> <dst-dir>
"""

from __future__ import annotations

import os
import sys

RESERVED = set(
    """ЛОЖЬ ТРАССА НЕТ_ТРАССЫ ВЫП НЕ ИЛИ РАВНО ТИХО ВЕРСИЯ ПС
    БОЛЬШЕ МЕНЬШЕ СЛОЖЕНИЕ УМНОЖЕНИЕ СЛУЧ ABS SQRT SIN COS TAN EXP
    int float mod div ЧТЕНИЕ_ИЗ ЗАПИСЬ_В ВВКОД ВВОДЦЕЛ ВВОДВЕЩ ВВОДСИМВ
    ВВОДСТР ВЫВОД ЖДИ БУКВА ЦИФРА СЦЕП КОПИЯ ДЛИНА ПЕР ЦЕЛ ВЕЩ СИМВ СПИСОК
    СТРСПИС СТРЦЕЛ СТРВЕЩ ЦЕЛВЕЩ СКОЛЬКО ПРЕДЛ ТЕРМ ДОБ УДАЛЕНИЕ ТОЧКА
    ЛИНИЯ ОКРУЖНОСТЬ ЗАКРАСКА НАЙТИВСЕ ИМПОРТ""".split()
)


def is_lower(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("а" <= ch <= "я") or ch == "ё"


def is_upper(ch: str) -> bool:
    return ("A" <= ch <= "Z") or ("А" <= ch <= "Я") or ch == "Ё"


def is_letter(ch: str) -> bool:
    return is_lower(ch) or is_upper(ch)


def is_name_char(ch: str) -> bool:
    return is_letter(ch) or ch.isdigit() or ch == "_"


def scan_variables(source: str) -> tuple[set[str], set[str]]:
    """Return (single-letter names, apostrophe names) used in the file."""
    singles: set[str] = set()
    apostrophes: set[str] = set()
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "%":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch == '"':
            i += 1
            while i < n and source[i] not in ('"', "\n"):
                i += 1
            i += 1
            continue
        if is_letter(ch) or ch == "_":
            j = i
            while j < n and is_name_char(source[j]):
                j += 1
            name = source[i:j]
            if j < n and source[j] == "'":
                if len(name) > 1:
                    apostrophes.add(name)
                j += 1
            elif len(name) == 1:
                singles.add(name)
            i = j
            continue
        i += 1
    return singles, apostrophes


def convert(source: str) -> str:
    singles, apostrophes = scan_variables(source)

    def variable_name(name: str) -> str:
        if len(name) == 1:
            if is_lower(name):
                upper = name.upper()
                return upper + "_" if upper in singles else upper
            return name
        base = name[0].upper() + name[1:]
        while base in apostrophes and base != name:
            base += "_"
        return base

    out: list[str] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "%":
            j = i
            while j < n and source[j] != "\n":
                j += 1
            out.append(source[i:j])
            i = j
            continue
        if ch == '"':
            j = i + 1
            while j < n and source[j] not in ('"', "\n"):
                j += 1
            if j < n:
                j += 1
            out.append(source[i:j])
            i = j
            continue
        if is_letter(ch) or ch == "_":
            j = i
            while j < n and is_name_char(source[j]):
                j += 1
            name = source[i:j]
            has_apostrophe = j < n and source[j] == "'"
            if has_apostrophe:
                j += 1
            if name in RESERVED:
                out.append(name)
            elif name == "_":
                out.append("_")
            elif len(name) == 1 or has_apostrophe:
                out.append(variable_name(name))
            elif is_upper(name[0]):
                k = j
                while k < n and source[k] in " \t\r\n":
                    k += 1
                if k < n and source[k] == "(":
                    out.append(name.lower())
                else:
                    out.append("'" + name.replace("'", "''") + "'")
            else:
                out.append(name)
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src_dir, dst_dir = sys.argv[1], sys.argv[2]
    os.makedirs(dst_dir, exist_ok=True)
    for entry in sorted(os.listdir(src_dir)):
        if not entry.endswith(".pld"):
            continue
        with open(os.path.join(src_dir, entry), encoding="utf-8") as handle:
            text = handle.read()
        converted = convert(text)
        target = os.path.join(dst_dir, entry.replace(" ", "_"))
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(converted)
        print(f"ported {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
