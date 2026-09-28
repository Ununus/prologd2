"""What to offer while typing: the reserved names and the document's own names.

Qt-free on purpose.  The two things worth testing are the ranking and *where*
completion must stay quiet (a comment, a string, a `#…#` block), and both are
pure functions of the text.  The popup itself is `editor.py`'s business.

The document is the better half of the value: in Prolog the name of the next
predicate is almost always a name already written a few lines above, and no
keyword table can know it.  The scan is a plain line-by-line pass over the
tokenizer's output — deliberately not a parse, because the file is mid-edit and
may not parse at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tokens
from .keywords import Keywords

#: Where a candidate came from; at equal rank a reserved name wins.
BUILTIN = "builtin"
USER = "user"

#: What a candidate is.  Names of both kinds are inserted the same way.
PREDICATE = "predicate"
ATOM_NAME = "atom"

#: Kinds the caret must not be completed inside.  A comment is special-cased:
#: it runs to the end of the line, so its last column is still inside it, and a
#: `#…#` block is a run between two `#` tokens rather than one token.
_SUPPRESSED = (tokens.STRING, tokens.QUOTED_ATOM)

_QUOTES = "'\""


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

    @property
    def label(self) -> str:
        """What the popup shows: `НАЙТИВСЁ/3`, `ВЫВОД/+` or the bare name."""
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


def collect_names(text: str, keywords: Keywords | None = None):
    """The document's own names.

    Returns `{name: {arity}}` for the names called with parentheses, a set of the
    bare atoms and a set of the quoted atoms (kept with their quotes).
    """
    calls: dict[str, set[int | None]] = {}
    atoms: set[str] = set()
    quoted: set[str] = set()
    for line in text.splitlines():
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
            elif token.kind == tokens.QUOTED_ATOM:
                quoted.add(token.text)
    return calls, atoms, quoted


def collect(text: str, keywords: Keywords | None = None) -> list[Candidate]:
    """Every candidate for a document: the reserved names, then its own."""
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
            for arity in sorted(keyword.arities):
                candidates.append(Candidate(keyword.name, arity, PREDICATE, BUILTIN))
            if not keyword.arities:
                # An operator or a directive: the name alone is what is typed.
                candidates.append(Candidate(keyword.name, None, PREDICATE, BUILTIN))

    calls, atoms, quoted = collect_names(text, keywords)
    for name in sorted(calls):
        if name in reserved:
            continue
        # The named arities first, the unknown one (`None`) last.
        for arity in sorted(calls[name], key=lambda value: (value is None, value or 0)):
            candidates.append(Candidate(name, arity, PREDICATE, USER))
    for name in sorted(atoms):
        if name in reserved or name in calls:
            continue
        candidates.append(Candidate(name, None, ATOM_NAME, USER))
    for name in sorted(quoted):
        candidates.append(Candidate(name, None, ATOM_NAME, USER, quoted=True))
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

    def set_keywords(self, keywords: Keywords | None) -> None:
        self._keywords = keywords
        self._text = None  # the reserved half of the list changed

    def update(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self._candidates = collect(text, self._keywords)

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
            # Same case as typed, then a match at all (a case-insensitive model
            # can offer more than the prefix matches literally), then the same
            # alphabet as the prefix — a Cyrillic prefix should not put Latin
            # names first — then reserved names, predicates, and finally the
            # alphabet so the order stays stable between keystrokes.
            not candidate.match_text.startswith(prefix),
            not name.startswith(folded),
            tokens.alphabet_of(prefix) != tokens.alphabet_of(candidate.match_text),
            candidate.source != BUILTIN,
            candidate.kind != PREDICATE,
            name,
        )


def word_before(text: str, position: int) -> str:
    """The name being typed at `position`, quotes included.

    Offsets are code points; the caller's `position` comes from Qt, which counts
    UTF-16 units.  They agree for every character a name can contain.
    """
    start = position
    while start > 0 and tokens.is_name_character(text[start - 1]):
        start -= 1
    if start > 0 and text[start - 1] in _QUOTES:
        start -= 1
    return text[start:position]


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
