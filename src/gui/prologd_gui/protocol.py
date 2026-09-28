"""Wire format of the `prologd --protocol json` session.

Requests are JSON objects, one per line, and events come back the same way.  The
C++ side of the contract lives in `src/cli/protocol.cpp`; keep the two in step.

This module is deliberately free of Qt so it can be tested headlessly (see
`tests/protocol_smoke.py`).
"""

from __future__ import annotations

import json
from typing import Any, Iterator

#: Bumped by the interpreter whenever a request or an event changes shape.
#: 2: the `ready` event carries `keywords` (the reserved names and their arities).
PROTOCOL_VERSION = 2

#: Event names the interpreter emits.
EVENTS = ("ready", "output", "result", "input_request", "error", "bye")


def encode_request(**fields: Any) -> bytes:
    """Encodes one request, ready to be written to the session's stdin."""
    return (json.dumps(fields, ensure_ascii=False) + "\n").encode("utf-8")


def load_text(text: str, name: str = "<buffer>") -> bytes:
    """Loads program text (the editor buffer)."""
    return encode_request(cmd="load", text=text, name=name)


def load_file(path: str) -> bytes:
    """Loads a program from disk; imports resolve against `-I` directories."""
    return encode_request(cmd="load", path=path)


def query(text: str) -> bytes:
    """Runs one statement, usually `?Goal.`."""
    return encode_request(cmd="query", text=text)


def input_answer(text: str) -> bytes:
    """Answers the pending `input_request`."""
    return encode_request(cmd="input", text=text)


def interrupt() -> bytes:
    """Asks for a stop; effective while the interpreter waits for input."""
    return encode_request(cmd="interrupt")


def quit_session() -> bytes:
    """Ends the session; the interpreter answers with `bye`."""
    return encode_request(cmd="quit")


class Decoder:
    """Turns the byte stream of events into whole JSON objects."""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: bytes) -> Iterator[dict]:
        self._buffer += chunk.decode("utf-8", errors="replace")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                yield {
                    "event": "error",
                    "kind": "protocol",
                    "message": f"нераспознанный ответ: {line}",
                }
                continue
            if isinstance(event, dict):
                yield event
