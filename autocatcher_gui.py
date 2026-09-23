"""autocatcher_gui.py — entry point for the GUI-only Windows build (AutoCatcher.exe)."""
import sys

from gui_win.app import run

if __name__ == "__main__":
    sys.exit(run())
