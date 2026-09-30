"""Checks that `doc/builtins.json` agrees with the interpreter and the manual.

    python src/gui/tests/test_reference.py [path-to-prologd]

Three places know the same thing, and this file is what keeps them one fact:

* `doc/builtins.json` — one record per built-in: the name, its English spellings,
  kind, arities, group, the section of `doc/help.typ` it comes from, and the short
  lines the window shows;
* the interpreter — `--list-keywords` prints every reserved name with its
  arities (and `+` for a variadic one), and the `ready` event adds the kind
  (`test_keywords.py` pins the two listings against each other);
* `doc/help.typ` — the section numbers the records point at, and the table of
  English names it builds *from this same file*.

Checked here: every name of the interpreter has a record and no record is
unknown; arities, the variadic flag and the kind are the interpreter's; an alias
is listed once and never twice; every `section` is a heading of the manual; every
variant starts with the predicate's own name; a summary is one non-empty line
without a trailing period.

Not checked here: that an English spelling is paired with the right Russian word.
That is knowledge no fourth source holds — the pairing is written down once, in
this file, and `help.typ` renders it.  Everything else about an alias (its
existence, kind and arities) is checked.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from prologd_gui import protocol  # noqa: E402

from protocol_smoke import check_default_executable  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
BUILTINS_PATH = ROOT / "doc" / "builtins.json"
HELP_PATH = ROOT / "doc" / "help.typ"

#: `== 7.4. `КОПИЯ…`` -> `7.4`; `= 8. Модули…` -> `8`.
HEADING = re.compile(r"^=+\s*(\d+(?:\.\d+)?)\.")


def load_records() -> list[dict]:
    data = json.loads(BUILTINS_PATH.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else None
    assert isinstance(records, list), f"{BUILTINS_PATH} has no \"records\" list"
    assert records, "the record list is empty"
    return records


def listing(executable: str) -> dict[str, dict]:
    """`--list-keywords` as `{name: {"arities": [...], "variadic": bool}}`.

    The name may appear once per arity (`СЛУЧ/1`, `СЛУЧ/3`); the arities are
    merged, and `/+` is a variadic predicate whose arity list is empty.
    """
    result = subprocess.run(
        [executable, "--list-keywords"], capture_output=True, check=True
    )
    lines = result.stdout.decode("utf-8").splitlines()
    assert lines, "no keywords printed"
    found: dict[str, dict] = {}
    for line in lines:
        name, _, arity = line.rpartition("/")
        if not name:  # no slash: `mod`, `div` — an operator has no arity
            name, arity = line, ""
        entry = found.setdefault(name, {"arities": [], "variadic": False})
        if arity == "+":
            entry["variadic"] = True
        elif arity:
            entry["arities"].append(int(arity))
    for entry in found.values():
        entry["arities"].sort()
    return found


def kinds(executable: str) -> dict[str, str]:
    """The kind of every name, from a `ready` event — the listing has none."""
    session = subprocess.run(
        [executable, "--protocol", "json"],
        input=protocol.quit_session(),
        capture_output=True,
        check=True,
    )
    events = list(protocol.Decoder().feed(session.stdout))
    ready = next(event for event in events if event.get("event") == "ready")
    return {entry["name"]: entry.get("kind", "") for entry in ready["keywords"]}


def help_sections() -> set[str]:
    headings = set()
    for line in HELP_PATH.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if match:
            headings.add(match.group(1))
    assert headings, f"no numbered headings in {HELP_PATH}"
    return headings


def test_every_name_of_the_interpreter_has_a_record(executable: str) -> None:
    records = load_records()
    names = listing(executable)
    known: dict[str, str] = {}  # spelling -> the record's own name
    for record in records:
        own = record.get("name")
        assert isinstance(own, str) and own, f"a record has no name: {record!r}"
        for spelling in [own, *record.get("aliases", [])]:
            assert spelling not in known, (
                f"{spelling!r} is listed by {known.get(spelling)!r} and by {own!r}"
            )
            known[spelling] = own

    missing = sorted(set(names) - set(known))
    unknown = sorted(set(known) - set(names))
    assert not missing, f"the interpreter has names with no record: {missing}"
    assert not unknown, f"records name things the interpreter does not have: {unknown}"
    print(f"ok: {len(records)} records cover all {len(names)} reserved names")


def test_arities_kind_and_variadic_are_the_interpreters(executable: str) -> None:
    records = load_records()
    names = listing(executable)
    kinds_by_name = kinds(executable)
    for record in records:
        own = record["name"]
        for spelling in [own, *record.get("aliases", [])]:
            real = names[spelling]
            assert real["arities"] == sorted(record.get("arities", [])), (
                f"{spelling}: arities {real['arities']} != {record.get('arities')}"
            )
            assert real["variadic"] == bool(record.get("variadic", False)), (
                f"{spelling}: variadic {real['variadic']} != {record.get('variadic')}"
            )
            assert record.get("kind") == kinds_by_name[spelling], (
                f"{spelling}: kind {record.get('kind')!r} != {kinds_by_name[spelling]!r}"
            )
    print("ok: arities, the variadic flag and the kind are what the interpreter reports")


def test_sections_and_summaries() -> None:
    records = load_records()
    sections = help_sections()
    for record in records:
        own = record["name"]
        section = record.get("section")
        assert section in sections, (
            f"{own}: section {section!r} is not a heading of {HELP_PATH.name}"
        )
        summary = record.get("summary")
        assert isinstance(summary, str) and summary.strip(), f"{own}: no summary"
        assert not summary.rstrip().endswith("."), (
            f"{own}: the summary ends in a period: {summary!r}"
        )
        variants = record.get("variants")
        assert isinstance(variants, list) and variants, f"{own}: no variants"
        for line in variants:
            assert isinstance(line, str) and line.startswith(own), (
                f"{own}: the variant does not start with the name: {line!r}"
            )
    print(f"ok: {len(records)} sections exist in the manual, summaries and variants hold")


def test_the_groups_are_known() -> None:
    known = {
        "control", "debug", "arith", "types", "strings", "io", "database",
        "modules", "graphics",
    }
    for record in load_records():
        group = record.get("group")
        assert group in known, f"{record['name']}: unknown group {group!r}"
    print(f"ok: every record belongs to one of {len(known)} groups")


def test_the_loader_serves_names_aliases_and_degrades() -> None:
    """`reference.py` is what the window reads; the checks above use the file."""
    from prologd_gui.reference import Reference

    reference = Reference.load()
    assert len(reference) > 50, len(reference)
    assert reference.summary("КОПИЯ").startswith("Подстрока и поиск")
    # An alias answers the record of its own predicate, not a copy of it.
    assert reference.record("substring") is reference.record("КОПИЯ")
    assert len(reference.variants("substring")) == 5
    assert reference.section("substring") == "7.4"
    assert reference.summary("неизвестное") == ""
    # A missing or unreadable file is not an error: no descriptions, and the
    # window still works (it has to run in a checkout without `doc/`).
    assert len(Reference.load(pathlib.Path("нет-такого-файла.json"))) == 0
    assert len(Reference.load(pathlib.Path(__file__).parent)) == 0  # a directory
    print("ok: the loader serves names and aliases, and a broken file is empty")


def main(argv: list[str]) -> int:
    test_the_loader_serves_names_aliases_and_degrades()
    executable = argv[1] if len(argv) > 1 else check_default_executable()
    print(f"interpreter: {executable}")
    test_every_name_of_the_interpreter_has_a_record(executable)
    test_arities_kind_and_variadic_are_the_interpreters(executable)
    test_sections_and_summaries()
    test_the_groups_are_known()
    print("all reference checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
