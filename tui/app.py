"""
tui/app.py — Phase 2.1: Textual app shell.

Entry points:
    python main.py tui        (preferred)
    python -m tui.app         (direct)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App

from config import APP_NAME, APP_VERSION
from tui.screens.case_browser import CaseBrowserScreen


class AutoCatcherApp(App):
    """AutoCatcher — evidence collection & reporting TUI."""

    TITLE = APP_NAME
    SUB_TITLE = f"v{APP_VERSION} — Phase 2 (TUI)"
    CSS_PATH = "app.tcss"

    def on_mount(self) -> None:
        self.push_screen(CaseBrowserScreen())


def run() -> None:
    AutoCatcherApp().run()


if __name__ == "__main__":
    run()
