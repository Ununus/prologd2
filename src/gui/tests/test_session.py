"""Offscreen checks of the interpreter session (needs PySide6 and a build).

    python src/gui/tests/test_session.py [path-to-prologd]

Two things are worth a test rather than a comment:

* a request issued right after `start()` must not be lost — the process is not
  up yet, so the session queues it until `ready`;
* loading a second program into a session that already ran one accumulates the
  clauses, which is why a front-end starts a *fresh* session per run (the bug
  that made a second **Запустить** print every solution twice).

Run with `QT_QPA_PLATFORM=offscreen` (set here) so it needs no display.
"""

from __future__ import annotations

import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

try:
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
except ImportError:  # pragma: no cover - the check below reports it
    QCoreApplication = None  # type: ignore[assignment]


PROGRAM = "факт(1).\nфакт(2).\n?факт(X).\n"
ONCE = "X=1\nX=2\n"
TWICE = "X=1\nX=2\nX=1\nX=2\n"


def find_executable(argv: list[str]) -> str | None:
    if len(argv) > 1:
        return argv[1]
    root = pathlib.Path(__file__).resolve().parents[3]
    for candidate in (
        root / "build" / "windows-msvc" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "linux-release" / "src" / "cli" / "prologd",
        root / "build" / "src" / "cli" / "Release" / "prologd.exe",
        root / "build" / "src" / "cli" / "prologd",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def pump(session, predicate, timeout: float = 15.0) -> bool:
    """Runs the event loop until `predicate()` is true or the timeout expires."""
    loop = QEventLoop()
    poll = QTimer()
    poll.setInterval(20)

    def check() -> None:
        if predicate():
            loop.quit()

    poll.timeout.connect(check)
    poll.start()
    QTimer.singleShot(int(timeout * 1000), loop.quit)
    check()
    if not predicate():
        loop.exec()
    poll.stop()
    return predicate()


class Recorder:
    def __init__(self, session) -> None:
        self.output = ""
        self.ready = ""
        self.trace = ""
        self.steps: list[str] = []
        self.failures: list[str] = []
        session.output.connect(self.on_output)
        session.ready.connect(self.on_ready)
        session.trace.connect(self.on_trace)
        session.stepped.connect(self.on_stepped)
        # A failure carries where it happened as well (protocol 3) and how bad
        # it is (protocol 4: "error" or "warning"); the position is a
        # `protocol.Position` or None, and the message is what a test looks at.
        session.failed.connect(
            lambda kind, severity, message, _position: self.failures.append(
                f"{kind}/{severity}: {message}"
            )
        )

    def on_output(self, text: str) -> None:
        self.output += text

    def on_trace(self, text: str) -> None:
        self.trace += text

    def on_stepped(self, point) -> None:
        self.steps.append(point.action)

    def on_ready(self, version: str) -> None:
        self.ready = version


def test_request_issued_before_ready(executable: str) -> None:
    """`load` right after `start()` must survive the interpreter booting."""
    from prologd_gui.session import PrologSession

    session = PrologSession(executable)
    recorder = Recorder(session)
    session.start()
    session.load_text(PROGRAM)  # immediately: the process may not be up yet

    assert pump(session, lambda: ONCE in recorder.output), (
        f"queued request lost, output was {recorder.output!r}"
    )
    session.stop()
    print("ok: a request issued before `ready` is queued, not lost")


def test_a_second_load_accumulates(executable: str) -> None:
    """The behaviour that made a second Запустить double every solution."""
    from prologd_gui.session import PrologSession

    session = PrologSession(executable)
    recorder = Recorder(session)
    session.start()
    session.load_text(PROGRAM)
    assert pump(session, lambda: ONCE in recorder.output), recorder.output

    session.load_text(PROGRAM)
    assert pump(session, lambda: TWICE in recorder.output), (
        f"the second load did not accumulate, output was {recorder.output!r}"
    )
    session.stop()
    print("ok: a second load into the same session accumulates clauses")


def test_a_fresh_session_starts_clean(executable: str) -> None:
    """`stop()` + `start()` is the clean slate a run needs."""
    from prologd_gui.session import PrologSession

    session = PrologSession(executable)
    recorder = Recorder(session)
    session.start()
    session.load_text(PROGRAM)
    assert pump(session, lambda: ONCE in recorder.output), recorder.output

    session.stop()
    recorder.output = ""
    session.start()
    session.load_text(PROGRAM)
    assert pump(session, lambda: ONCE in recorder.output), recorder.output
    assert TWICE not in recorder.output, f"state leaked across a restart: {recorder.output!r}"
    session.stop()
    print("ok: a restarted session has no clauses from the previous run")


def main(argv: list[str]) -> int:
    if QCoreApplication is None:
        print("skipped: PySide6 is not installed")
        return 0
    executable = find_executable(argv)
    if executable is None:
        print("skipped: no prologd build found, pass its path to check the session")
        return 0

    application = QCoreApplication(sys.argv[:1])
    print(f"interpreter: {executable}")
    test_request_issued_before_ready(executable)
    test_a_second_load_accumulates(executable)
    test_a_fresh_session_starts_clean(executable)
    print("all session checks passed")
    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
