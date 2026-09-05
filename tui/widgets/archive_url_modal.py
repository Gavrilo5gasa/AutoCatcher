"""
tui/widgets/archive_url_modal.py — Modal dialog for archiving a URL via
the Wayback Machine. Mirrors `main.py archive <case-id> <url>`.

Dismisses with the ArchiveResult on success, or None if cancelled.
Network call happens on the caller's side (screen) so this modal can
show a "working…" state without blocking input widgets weirdly.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class ArchiveUrlModal(ModalScreen[str | None]):
    """Collects a URL to submit to the Wayback Machine. Returns the raw URL string."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("[bold]Archive URL[/bold]")
            yield Label("URL to snapshot on the Wayback Machine")
            yield Input(placeholder="https://x.com/someprofile", id="url-input")
            yield Static(
                "This can take a few seconds — the app will stay responsive.",
                classes="hint",
            )
            yield Static("", id="url-error", classes="error-text")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Archive", id="archive-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#url-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "archive-btn":
            self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            self.query_one("#url-error", Static).update("URL is required.")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            self.query_one("#url-error", Static).update(
                "URL must start with http:// or https://"
            )
            return
        self.dismiss(url)
