"""
tui/widgets/confirm_modal.py — Generic yes/no confirmation dialog.

Used e.g. when generating an NCMEC guide for a case that isn't flagged
minor_involved (same confirmation the CLI asks for in main.py).
Dismisses with True / False.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmModal(ModalScreen[bool]):
    """A simple modal with a message and Yes/No buttons."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, message: str, confirm_label: str = "Yes", danger: bool = False) -> None:
        super().__init__()
        self.message = message
        self.confirm_label = confirm_label
        self.danger = danger

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(self.message)
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="no-btn")
                yield Button(
                    self.confirm_label,
                    id="yes-btn",
                    variant="error" if self.danger else "primary",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)
