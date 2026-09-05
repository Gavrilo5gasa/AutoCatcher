"""
tui/widgets/note_modal.py — Modal dialog for appending a timestamped note
to a case. Mirrors the note-append behaviour in core/case.py (append-only).

Dismisses with True on success (caller should refresh), or None if cancelled.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea

from core.case import append_note


class NoteModal(ModalScreen[bool | None]):
    """Collects a note and appends it to the case (never overwrites)."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, case_dir: Path) -> None:
        super().__init__()
        self.case_dir = case_dir

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("[bold]Add Note[/bold]")
            yield Static(
                "Notes are timestamped and append-only — nothing is ever overwritten.",
                classes="hint",
            )
            yield TextArea(id="note-input")
            yield Static("", id="note-error", classes="error-text")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Add Note", id="add-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#note-input", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "add-btn":
            self._add()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _add(self) -> None:
        text = self.query_one("#note-input", TextArea).text.strip()
        if not text:
            self.query_one("#note-error", Static).update("Note can't be empty.")
            return
        append_note(self.case_dir, text)
        self.dismiss(True)
