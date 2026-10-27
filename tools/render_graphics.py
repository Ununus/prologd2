"""Render what a program draws to a PNG, through the JSON protocol.

    python tools/render_graphics.py --source examples/problems/maze/maze.pld \
        --include stdlib --input examples/problems/maze/maze.input.txt \
        --out build/maze.png --scale 4

The picture is the session's own screen: the harness asks for a `graphics`
snapshot — the same bitmap the window shows — and writes it as PNG.  Nothing of
the picture is re-drawn here; a program that draws nothing gives a blank page,
and that is the answer too.

The console interpreter draws nothing (its graphics backend is a stub), so this
is the only way to *look* at a program from a terminal.  The PNG is written by
hand — zlib and `struct`, no Pillow and no Qt — so the tool runs in the venv the
GUI uses without adding a dependency.

A run takes as long as the program's own animation: `ЖДИ(200)` between two steps
is a real sleep in both front-ends, and the maze has eight of them.  The window
paints while it sleeps, this tool is silent until the last frame — hence the
`... operations drawn` lines on stderr and the `took` line at the end.

A `load` runs the program's own `?`-lines, exactly as `-s` does on the command
line, so a program that already asks its question (the maze does) needs no
`--query`; `--query` goals run after the program's own.  Anything the program
reads has to come from `--input`: without it the interpreter waits for a screen
nobody is typing on.

Exit code: 0 the picture was written, 1 the interpreter refused the program or a
query failed, 2 the harness itself could not start the interpreter.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: Where a Release build of the interpreter lands, and the variable the GUI tests
#: use to point at another one.
DEFAULT_EXECUTABLE = ROOT / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe"


def decode_rgba(pixels: bytes) -> bytes:
    """The snapshot's cells as PNG bytes.

    A snapshot carries the *colour number* of every cell, four bytes each and
    little-endian — the same number a program writes (`0xRRGGBB`), not RGBA.  A
    picture that is passed through unchanged comes out with a zero alpha channel,
    i.e. white, so the three colour bytes are re-ordered and an opaque alpha is
    added; `prologd_gui.graphics` does the same on the window's side.
    """
    result = bytearray(len(pixels))
    for index in range(0, len(pixels), 4):
        value = int.from_bytes(pixels[index : index + 4], "little")
        result[index] = (value >> 16) & 0xFF
        result[index + 1] = (value >> 8) & 0xFF
        result[index + 2] = value & 0xFF
        result[index + 3] = 0xFF
    return bytes(result)


def write_png(path: pathlib.Path, width: int, height: int, rgba: bytes, scale: int) -> None:
    """A PNG of the pixels, each cell repeated `scale` times.

    The rows go through the compressor one by one: a big `--scale` multiplies the
    picture by `scale` squared, and holding all of it in memory is how a 600x600
    screen at scale 8 turns into a hundred megabytes of `bytearray`.
    """
    import struct

    out_width, out_height = width * scale, height * scale
    compressor = zlib.compressobj(6)
    compressed = bytearray()
    for y in range(height):
        row = rgba[y * width * 4 : (y + 1) * width * 4]
        if scale > 1:
            stretched = bytearray()
            for x in range(width):
                stretched += row[x * 4 : x * 4 + 4] * scale
            row = bytes(stretched)
        line = b"\x00" + row  # filter type «none»
        for _ in range(scale):
            compressed += compressor.compress(line)
    compressed += compressor.flush()

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", out_width, out_height, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", bytes(compressed))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


class Session:
    """One `prologd --protocol json` process, driven line by line."""

    def __init__(self, executable: pathlib.Path, answers: list[str], includes: list[str]) -> None:
        command = [str(executable)]
        for directory in includes:
            command += ["-I", directory]
        command.append("--protocol")
        command.append("json")
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self.answers = list(answers)
        self.events: list[dict] = []
        #: How many times the program asked for input the harness had no answer for.
        self.unanswered = 0

    def send(self, request: dict) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def read(self) -> dict:
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            details = ""
            if self.process.stderr is not None:
                details = self.process.stderr.read().strip()
            raise SystemExit(f"the interpreter stopped answering ({details or 'no message'})")
        event = json.loads(line)
        self.events.append(event)
        if event.get("event") == "input_request":
            # A program that reads: the harness answers the way the window does,
            # one line per request.  A program that keeps asking after the answers
            # are gone would spin forever, so two extra requests are the end of it.
            if self.answers:
                self.send({"cmd": "input", "text": self.answers.pop(0)})
            else:
                self.unanswered += 1
                if self.unanswered > 2:
                    raise SystemExit(
                        "the program wants more input than --input gives: "
                        f"{event.get('prompt', '')!r}"
                    )
                self.send({"cmd": "input", "text": ""})
        return event

    def until(self, wanted: set[str]) -> dict:
        """Reads events until one of `wanted` arrives; an error is fatal, a warning is not."""
        drawn = 0
        while True:
            event = self.read()
            name = event.get("event")
            if name == "graphics":
                drawn += 1
                # The program's own `ЖДИ` sleeps, so a long run is not a hang:
                # say how much has been drawn instead of staying silent.
                if drawn % 500 == 0:
                    print(f"  ... {drawn} operations drawn", file=sys.stderr, flush=True)
                continue
            if name == "error":
                if event.get("severity", "error") == "warning":
                    print(f"warning: {event.get('message')}", file=sys.stderr)
                    continue
                raise SystemExit(f"error: {event.get('message')}")
            if name in wanted:
                return event

    def close(self) -> None:
        try:
            self.send({"cmd": "quit"})
        except Exception:  # noqa: BLE001 - the process may already be gone
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=pathlib.Path, help="a program file")
    source.add_argument("--text", help="the program as text")
    parser.add_argument("--query", action="append", default=[], help="a goal, `?цель.`; repeatable")
    parser.add_argument("--input", type=pathlib.Path, help="answers for a program that reads")
    parser.add_argument("--include", action="append", default=[],
                        help="a module search directory (`-I`); repeatable")
    parser.add_argument("--screen", help="the screen size, WxH (default: the engine's own)")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "screen.png")
    parser.add_argument("--scale", type=int, default=1, help="repeat every cell N times")
    parser.add_argument("--verbose", action="store_true", help="print every event")
    parser.add_argument(
        "--executable",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("PROLOGD_TEST_EXE", DEFAULT_EXECUTABLE)),
    )
    args = parser.parse_args(argv[1:])

    if not args.executable.is_file():
        print(f"no interpreter at {args.executable}", file=sys.stderr)
        return 2
    started = time.perf_counter()
    answers = []
    if args.input is not None:
        answers = args.input.read_text(encoding="utf-8").splitlines()

    text = args.source.read_text(encoding="utf-8") if args.source else args.text
    session = Session(args.executable, answers, args.include)
    try:
        session.until({"ready"})
        load = {"cmd": "load", "text": text, "name": str(args.source or "<text>")}
        if args.screen:
            width, height = (int(part) for part in args.screen.lower().split("x"))
            load["screen"] = {"width": width, "height": height}
        session.send(load)
        session.until({"loaded"})
        for goal in args.query:
            session.send({"cmd": "query", "text": goal})
            session.until({"result"})
        session.send({"cmd": "graphics", "snapshot": True})
        bitmap = session.until({"bitmap"})
    finally:
        session.close()

    width, height = bitmap["width"], bitmap["height"]
    pixels = base64.b64decode(bitmap["data"])
    write_png(args.out, width, height, decode_rgba(pixels), max(1, args.scale))

    drawn = sum(1 for event in session.events if event.get("event") == "graphics")
    background = pixels[0:4]
    painted = sum(
        1
        for index in range(0, len(pixels), 4)
        if pixels[index : index + 4] != background
    )
    if args.verbose:
        for event in session.events:
            print(json.dumps(event, ensure_ascii=False))
    print(f"picture : {args.out} ({width}x{height}, scale {args.scale})")
    print(f"events  : {drawn} graphics, {painted} cells differ from the first one")
    print(f"took    : {time.perf_counter() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
