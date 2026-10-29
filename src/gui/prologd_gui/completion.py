"""What to offer while typing: the reserved names and the document's own names.

Qt-free on purpose: the ranking and *where* completion stays quiet (a comment, a
string, a `#…#` block) are pure functions of the text, and the popup is
`editor.py`'s business.

The document is the better half of the value — the next predicate is almost always
a name already written a few lines above.  The scan is a line-by-line pass over the
tokenizer's output, deliberately not a parse: the file is mid-edit.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from . import tokens
from .keywords import Keywords

#: Where a candidate came from; at equal rank a reserved name wins, then the
#: document's own, then a name an imported file brings in (task_102).
BUILTIN = "builtin"
USER = "user"
IMPORTED = "imported"

#: What a candidate is.  Names of both kinds are inserted the same way.
PREDICATE = "predicate"
ATOM_NAME = "atom"

#: Kinds the caret must not be completed inside.  A comment is special-cased:
#: it runs to the end of the line, so its last column is still inside it, and a
#: `#…#` block is a run between two `#` tokens rather than one token.
_SUPPRESSED = (tokens.STRING, tokens.QUOTED_ATOM)

#: Where a candidate came from, best first: a reserved name wins a tie, then the
#: document's own, and a name an imported file brings in comes last (task_102).
_SOURCE_RANK = {BUILTIN: 0, USER: 1, IMPORTED: 2}

_QUOTES = "'\""

#: How much of a predicate's comment the popup's label shows (task_103): enough
#: for a sentence or two, not a wall of text over the code.
SUMMARY_LIMIT = 400


@dataclass(frozen=True)
class Statement:
    """How a name that is written as a statement of its own is typed (task_105)."""

    #: The whole text the typed name is replaced with.
    text: str
    #: Where the caret goes, as an offset into `text`.
    caret: int


def _statement(template: str) -> Statement:
    """Reads a template written with `|` where the caret goes.

    `':- ИМПОРТ("|").'` says both things at once — the text and the caret — and
    needs no arithmetic when the caret is not right after the `(`.  No statement
    has a `|` in it, so the mark cannot be mistaken for the language.
    """
    return Statement(template.replace("|", ""), template.index("|"))


#: The directives a program writes as a statement of its own — `ИМПОРТ` (task_105)
#: and `ХОЛСТ` (task_106).  The caret lands where the next keystroke belongs: inside
#: `ИМПОРТ`'s quotes (the string completes to a file, task_104) and before
#: `ХОЛСТ`'s comma.
STATEMENT_TEMPLATES = {
    "ИМПОРТ": _statement(':- ИМПОРТ("|").'),
    "import": _statement(':- import("|").'),
    "ХОЛСТ": _statement(":- ХОЛСТ(|, )."),
    "canvas": _statement(":- canvas(|, )."),
}


@dataclass(frozen=True)
class Candidate:
    """One thing the popup can offer.

    `arity` is `None` when the name is not a call — an atom used as an argument,
    or a call whose parentheses run past the end of its line.  `variadic` marks
    `ВЫВОД/+`, which accepts any arity.
    """

    name: str
    arity: int | None = None
    kind: str = PREDICATE
    source: str = USER
    quoted: bool = False
    variadic: bool = False
    #: The file an imported name comes from, for the popup's label (task_102).
    origin: str | None = None
    #: The comment written above the name's first clause, for the same label
    #: (task_103) — the note a library keeps for its predicates.
    summary: str | None = None
    #: What the popup shows when the name is not the answer: a directive is offered
    #: as the whole statement it has to be (task_105).
    display: str | None = None
    #: `(text, caret)` to insert instead of the call form — the same task.
    skeleton: tuple[str, int] | None = None
    #: True for a directive: a statement of its own, so it is offered only where a
    #: statement can start, never inside a body.
    directive: bool = False

    @property
    def label(self) -> str:
        """What the popup shows: `НАЙТИВСЕ/3`, `ВЫВОД/+` or the bare name."""
        if self.display is not None:
            return self.display
        if self.variadic:
            return f"{self.name}/+"
        if self.arity is None:
            return self.name
        return f"{self.name}/{self.arity}"

    @property
    def match_text(self) -> str:
        """The name as typed: a quoted atom matches without its quotes."""
        if self.quoted and len(self.name) >= 2 and self.name[0] in _QUOTES:
            if self.name[-1] == self.name[0]:
                return self.name[1:-1]
        return self.name

    @property
    def insert_text(self) -> str:
        """What replaces the typed prefix — the name, never the arity."""
        return self.name

    @property
    def call_form(self) -> tuple[str, int]:
        """`(text, caret)` for accepting this offer (2026-10-02).

        A predicate with arguments inserts its call skeleton — `СЛОЖЕНИЕ(, , )`
        for arity 3 — with the caret right after the opening parenthesis, so the
        next keystroke types the first argument.  Variadic `ВЫВОД` behaves like
        one argument (nobody knows how many it takes), and a zero-arity name or
        a bare atom inserts only the name with the caret at the end.
        """
        if self.skeleton is not None:
            return self.skeleton
        if self.variadic:
            return self.name + "()", len(self.name) + 1
        if self.arity is None or self.arity == 0:
            return self.name, len(self.name)
        skeleton = self.name + "(" + ", ".join([""] * self.arity) + ")"
        return skeleton, len(self.name) + 1

    def call_form_after(self, following: str = "") -> tuple[str, int]:
        """`(text, caret)` for accepting this offer where `following` stands next.

        A name typed right before its own `(` — `БОЛ(`, with `БОЛЬШЕ` on offer — keeps
        that bracket: only the name goes in and the caret stops inside the call, or the
        text would read `БОЛЬШЕ(, )(` (part 238).  Anything else is `call_form`.
        """
        if following.startswith("(") and self.skeleton is None and (
            self.variadic or (self.arity or 0) > 0
        ):
            return self.name, len(self.name) + 1
        return self.call_form


def _count_arguments(line_tokens: list[tokens.Token], start: int) -> int | None:
    """Arity of the call whose `(` is at `start`, or `None` if it does not close.

    Commas inside a list are not argument separators, so `[`/`]` is tracked too:
    `член(2, [1, 2, 3])` is arity 2, not 4.  A name whose arguments continue on
    the next line is offered without an arity rather than guessed at.
    """
    depth = 0
    list_depth = 0
    commas = 0
    seen_argument = False
    for token in line_tokens[start:]:
        text = token.text
        if text == "(":
            depth += 1
        elif text == ")":
            if list_depth == 0:
                depth -= 1
                if depth == 0:
                    return commas + 1 if seen_argument else 0
        elif text in ("[", "]"):
            list_depth = list_depth + 1 if text == "[" else max(0, list_depth - 1)
            if depth == 1:
                seen_argument = True
        elif text == "," and depth == 1 and list_depth == 0:
            commas += 1
        elif depth == 1:
            seen_argument = True
    return None


def comment_above(lines: list[str], index: int) -> str:
    """The `%` block written directly above line `index`, as one paragraph.

    Only the lines that touch the clause count, so the header of a file (separated
    from the first predicate by a blank line, as `stdlib/iso.pld` has it) is not
    glued to it.  A comment *after* the clause on the same line is not read: the
    label is about the name, and a trailing `%` may say anything at all.
    """
    collected: list[str] = []
    number = index - 1
    while number >= 0:
        stripped = lines[number].strip()
        if not stripped.startswith("%"):
            break
        collected.append(stripped[1:].strip())
        number -= 1
    collected.reverse()
    joined = " ".join(part for part in collected if part)
    if len(joined) > SUMMARY_LIMIT:
        return joined[: SUMMARY_LIMIT - 1].rstrip() + "…"
    return joined


def collect_names(text: str, keywords: Keywords | None = None):
    """The document's own names.

    Returns `{name: {arity}}` for the names called with parentheses, a set of the
    bare atoms, a set of the quoted atoms (kept with their quotes), and the
    comment written above the first clause of each name (task_103) — the last one
    only for a line whose *first* token is the name, because that is a clause head
    and not a goal.  A predicate of no arguments is an atom here (`дождь.`,
    `мокро :- дождь.`), and its head is recognised the same way.
    """
    calls: dict[str, set[int | None]] = {}
    atoms: set[str] = set()
    quoted: set[str] = set()
    summaries: dict[str, str] = {}
    lines = text.splitlines()
    for number, line in enumerate(lines):
        line_tokens = tokens.tokenize(line, keywords)
        for index, token in enumerate(line_tokens):
            if token.kind == tokens.ATOM:
                following = (
                    line_tokens[index + 1] if index + 1 < len(line_tokens) else None
                )
                if following is not None and following.text == "(":
                    calls.setdefault(token.text, set()).add(
                        _count_arguments(line_tokens, index + 1)
                    )
                else:
                    atoms.add(token.text)
                # A head is the first token of its line; what follows it opens its
                # arguments, ends the sentence or starts its body.
                if (
                    index == 0
                    and token.text not in summaries
                    and following is not None
                    and following.text in ("(", ".", ":-")
                ):
                    note = comment_above(lines, number)
                    if note:
                        summaries[token.text] = note
            elif token.kind == tokens.QUOTED_ATOM:
                quoted.add(token.text)
    return calls, atoms, quoted, summaries


def collect(text: str, keywords: Keywords | None = None, imported=None) -> list[Candidate]:
    """Every candidate for a document: the reserved names, then its own, then the
    ones its `ИМПОРТ` files bring in (task_102).

    `imported` is `{path: text}`, exactly what `imports.ImportedFiles.texts`
    answers; the file's name is kept so the popup can say where a name came from.
    Only *predicates* are taken from there — a library's atoms (a colour, a kind of
    friction) are not what the next goal is typed with, and they would bury the
    names of the document itself.
    """
    candidates: list[Candidate] = []
    reserved: set[str] = set()
    if keywords is not None:
        for keyword in keywords:
            reserved.add(keyword.name)
            if keyword.variadic:
                candidates.append(
                    Candidate(keyword.name, None, PREDICATE, BUILTIN, variadic=True)
                )
                continue
            template = STATEMENT_TEMPLATES.get(keyword.name)
            if template is not None:
                # A statement of its own, offered as the whole line: the bare name
                # (`ИМПОРТ`) does not parse.  Its caret lands between the quotes,
                # where the string completes to a file name (task_104).
                candidates.append(
                    Candidate(
                        keyword.name,
                        None,
                        PREDICATE,
                        BUILTIN,
                        display=template.text,
                        skeleton=(template.text, template.caret),
                        directive=True,
                    )
                )
                continue
            for arity in sorted(keyword.arities):
                candidates.append(Candidate(keyword.name, arity, PREDICATE, BUILTIN))
            if not keyword.arities:
                # An operator: the name alone is what is typed.
                candidates.append(Candidate(keyword.name, None, PREDICATE, BUILTIN))

    calls, atoms, quoted, summaries = collect_names(text, keywords)
    for name in sorted(calls):
        if name in reserved:
            continue
        # The named arities first, the unknown one (`None`) last.
        for arity in sorted(calls[name], key=lambda value: (value is None, value or 0)):
            candidates.append(
                Candidate(name, arity, PREDICATE, USER, summary=summaries.get(name))
            )
    for name in sorted(atoms):
        if name in reserved or name in calls:
            continue
        candidates.append(
            Candidate(name, None, ATOM_NAME, USER, summary=summaries.get(name))
        )
    for name in sorted(quoted):
        candidates.append(Candidate(name, None, ATOM_NAME, USER, quoted=True))
    # What the imported files define.  A name the document itself has is offered
    # once, as the document's own, and an imported file's atoms are left out: the
    # point of the import is the predicates.
    offered = set(calls) | atoms
    for path, source in (imported or {}).items():
        origin = pathlib.PurePath(path).name
        file_calls, _atoms, _quoted, file_notes = collect_names(source, keywords)
        for name in sorted(file_calls):
            if name in reserved or name in offered:
                continue
            offered.add(name)
            for arity in sorted(
                file_calls[name], key=lambda value: (value is None, value or 0)
            ):
                candidates.append(
                    Candidate(
                        name,
                        arity,
                        PREDICATE,
                        IMPORTED,
                        origin=origin,
                        summary=file_notes.get(name),
                    )
                )
    return candidates


class CompletionModel:
    """The candidates for one document, ranked for a prefix.

    The list is rebuilt only when the text or the keyword table changes: it is
    asked for a prefix on every keystroke, and re-tokenising a whole file each
    time is what makes a popup stutter.
    """

    def __init__(
        self, keywords: Keywords | None = None, case_sensitive: bool = True
    ) -> None:
        self._keywords = keywords
        self._case_sensitive = case_sensitive
        self._text: str | None = None
        self._candidates: list[Candidate] = []
        self._imported: dict[str, str] = {}

    def set_imported(self, texts) -> None:
        """The texts the document's `ИМПОРТ` lines bring in (task_102).

        Handed over by the window (it alone knows the search directories), so the
        model stays a function of texts.  Rebuilding the list is what the next
        `update` does; asking twice with the same texts does nothing.
        """
        texts = dict(texts or {})
        if texts == self._imported:
            return
        self._imported = texts
        self._text = None  # the imported half of the list changed

    def set_keywords(self, keywords: Keywords | None) -> None:
        self._keywords = keywords
        self._text = None  # the reserved half of the list changed

    def set_case_sensitive(self, flag: bool) -> None:
        """Whether the case of what is typed has to match (task_29's switch)."""
        self._case_sensitive = bool(flag)

    def update(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self._candidates = collect(text, self._keywords, self._imported)

    def candidates(self, prefix: str) -> list[Candidate]:
        folded = self._fold(prefix)
        matches = [c for c in self._candidates if self._fold(c.match_text).startswith(folded)]
        return sorted(matches, key=lambda candidate: self._sort_key(candidate, prefix, folded))

    def labels(self, prefix: str) -> list[str]:
        """The popup's lines, in the order it shows them."""
        return [candidate.label for candidate in self.candidates(prefix)]

    def _fold(self, text: str) -> str:
        return text if self._case_sensitive else text.lower()

    def _sort_key(self, candidate: Candidate, prefix: str, folded: str):
        name = self._fold(candidate.match_text)
        return (
            # Same case as typed, then a match at all, then the same alphabet as the
            # prefix (a Cyrillic prefix should not put Latin names first), then
            # reserved before the document's own before imported, predicates before
            # atoms, and the alphabet last for a stable order between keystrokes.
            not candidate.match_text.startswith(prefix),
            not name.startswith(folded),
            tokens.alphabet_of(prefix) != tokens.alphabet_of(candidate.match_text),
            _SOURCE_RANK.get(candidate.source, len(_SOURCE_RANK)),
            candidate.kind != PREDICATE,
            name,
        )


def at_statement_start(text: str, position: int, prefix: str = "") -> bool:
    """True when only whitespace stands between the line start and the typed word.

    What a directive needs (task_105): `:- ИМПОРТ("…").` is a statement of its own,
    and offering it in the middle of a body would be offering a syntax error.
    `prefix` is the word being typed — the caret stands after it, so the question is
    about what comes *before* the word.
    """
    line_start = text.rfind("\n", 0, position) + 1
    before = text[line_start:position]
    if prefix and before.endswith(prefix):
        before = before[: len(before) - len(prefix)]
    return before.strip() == ""


def prefix_span(text: str, position: int) -> tuple[int, int]:
    """Where the name being completed starts, and where its text ends.

    Usually the caret is the end: `БОЛ|` is a word ending there.  A name typed right
    before its own bracket — `БОЛ(|` or `БОЛ|(` — is being completed too, and then
    the name ends at the bracket, which the completion keeps: accepting must not
    bring a second one (part 238).  An empty span means there is nothing to replace.
    """
    position = max(0, min(int(position), len(text)))
    end = position
    if position and text[position - 1] == "(":
        end = position - 1
    start = end
    while start > 0 and tokens.is_name_character(text[start - 1]):
        start -= 1
    if start > 0 and text[start - 1] in _QUOTES:
        start -= 1
    if start == end:
        return position, position
    return start, end


def word_before(text: str, position: int) -> str:
    """The name being typed at `position`, quotes included.

    Offsets are code points; the caller's `position` comes from Qt, which counts
    UTF-16 units.  They agree for every character a name can contain.
    """
    start, end = prefix_span(text, position)
    return text[start:end]


def is_code_position(text: str, position: int, keywords: Keywords | None = None) -> bool:
    """False inside a comment, a string, a quoted atom or a `#…#` block."""
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    line = text[line_start:] if line_end < 0 else text[line_start:line_end]
    column = position - line_start
    inside_expression = False
    for token in tokens.tokenize(line, keywords):
        if token.kind == tokens.EXPRESSION:
            # `#` opens and closes an expression: an odd number of them before
            # the caret means the caret is inside one.
            if column <= token.start:
                break
            inside_expression = not inside_expression
            continue
        if token.start >= column:
            break
        if token.kind == tokens.COMMENT:
            # To the end of the line: the caret after the text is still inside.
            return False
        if token.kind in _SUPPRESSED and column < token.end:
            return False
    return not inside_expression
