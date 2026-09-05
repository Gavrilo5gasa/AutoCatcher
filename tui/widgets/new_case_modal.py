"""
tui/widgets/new_case_modal.py — Modal dialog for creating a new case.

Mirrors `main.py case new`: subject, platform, minor-involved flag, notes.
Dismisses with the new case_id (str) on success, or None if cancelled.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Static, TextArea

from core.case import create_case, load_case


class NewCaseModal(ModalScreen[str | None]):
    """Collects the fields needed to create a new case."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("[bold]New Case[/bold]")
            yield Label("Subject username / handle")
            yield Input(placeholder="e.g. bad_user#1234", id="subject-input")
            yield Label("Platform")
            yield Input(placeholder="e.g. discord, twitter, roblox", id="platform-input")
            yield Checkbox("Minor involved (enables NCMEC warnings)", id="minor-checkbox")
            yield Label("Opening notes (optional)")
            yield TextArea(id="notes-input")
            yield Static("", id="new-case-error", classes="error-text")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Create", id="create-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#subject-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            self._create()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _create(self) -> None:
        subject = self.query_one("#subject-input", Input).value.strip()
        platform = self.query_one("#platform-input", Input).value.strip()
        minor = self.query_one("#minor-checkbox", Checkbox).value
        notes = self.query_one("#notes-input", TextArea).text.strip()
        error = self.query_one("#new-case-error", Static)

        if not subject:
            error.update("Subject is required.")
            return
        if not platform:
            error.update("Platform is required.")
            return

        case_dir = create_case(
            subject=subject, platform=platform, notes=notes, minor_involved=minor
        )
        _, meta = load_case(case_dir.name)
        self.dismiss(meta.case_id)
