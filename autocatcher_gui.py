"""autocatcher_gui.py — entry point for the GUI-only Windows build (AutoCatcher.exe).

Kept free of project imports until inside main() so that a startup failure
(missing module in the frozen build, etc.) can be logged and shown instead
of silently vanishing.
"""

import os
import sys
import traceback
from pathlib import Path

SELFTEST = bool(os.environ.get("AUTOCATCHER_SELFTEST"))


def _log_path() -> Path:
    if os.environ.get("AUTOCATCHER_LOG"):
        return Path(os.environ["AUTOCATCHER_LOG"])
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "autocatcher_gui.log"


def note(msg: str) -> None:
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:  # noqa: BLE001
        pass


def _fatal(title: str, detail: str) -> None:
    if SELFTEST:  # CI: never block on a dialog
        return
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, detail[-1500:])
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    if SELFTEST:
        import faulthandler

        # If we hang, dump every thread's stack into the log and exit.
        faulthandler.dump_traceback_later(60, file=open(_log_path(), "a"), exit=True)
        note("[selftest] started")
    try:
        from gui_win.app import run
    except BaseException:  # noqa: BLE001
        err = traceback.format_exc()
        note("STARTUP IMPORT FAILED\n" + err)
        _fatal("AutoCatcher failed to start", err)
        return 1
    note("[selftest] imports ok") if SELFTEST else None
    return run(note=note if SELFTEST else None)


if __name__ == "__main__":
    sys.exit(main())
