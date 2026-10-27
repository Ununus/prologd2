"""PySide6 front-end for the PrologD interpreter.

The GUI never links against `prlib`: it drives the `prologd` executable through
the line-delimited JSON session (`prologd --protocol json`).  See `README.md` in
this directory for the protocol contract and `src/cli/protocol.cpp` for the C++
side of it.
"""

__all__ = [
    "actions",
    "appearance",
    "assets",
    "buffers",
    "completion",
    "documents",
    "editor",
    "highlighter",
    "keywords",
    "panes",
    "protocol",
    "session",
    "settings",
    "theme",
    "tokens",
    "window",
]
