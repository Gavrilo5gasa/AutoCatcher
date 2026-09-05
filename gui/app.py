"""
gui/app.py — Phase 3.1: GTK4 application entry point.

Entry points:
    python main.py gui        (preferred)
    python -m gui.app         (direct)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

from gui.main_window import MainWindow
from gui.style import apply_css


class AutoCatcherGtkApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="dev.autocatcher.app",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window: MainWindow | None = None

    def do_activate(self) -> None:
        apply_css()
        if self.window is None:
            self.window = MainWindow(self)
        self.window.present()


def run() -> int:
    app = AutoCatcherGtkApp()
    # Only pass argv[0] (program name) through — GTK's GApplication parses
    # any leftover positional args itself and treats them as filenames to
    # open unless HANDLES_OPEN is set. Since our Typer CLI already consumed
    # "gui"/"tui"/etc., forwarding the full sys.argv makes GTK think those
    # subcommand words are files, producing the "can not open files" error.
    return app.run(sys.argv[:1])


if __name__ == "__main__":
    sys.exit(run())
