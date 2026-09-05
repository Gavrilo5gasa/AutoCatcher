"""
tui/widgets/add_evidence_modal.py — Modal dialog for adding a piece of evidence.

Mirrors `main.py evidence add`: source file path, type, description, source.
Dismisses with True on success (caller should refresh its evidence table),
or None if cancelled.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from core.evidence import add_evidence
from utils.platform import example_evidence_path

_TYPE_OPTIONS = [
    ("Screenshot", "screenshot"),
    ("Log / chat export", "log"),
    ("Other file", "file"),
]


class AddEvidenceModal(ModalScreen[bool | None]):
    """Collects a file path + metadata and adds it to the case as evidence."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, case_dir: Path) -> None:
        super().__init__()
        self.case_dir = case_dir

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("[bold]Add Evidence[/bold]")
            yield Label("File path (screenshot, log export, anything)")
            yield Input(placeholder=example_evidence_path(), id="path-input")
            yield Label("Type")
            yield Select(_TYPE_OPTIONS, value="screenshot", id="type-select")
            yield Label("Description (what does this show?)")
            yield Input(placeholder="e.g. DM asking to move to Telegram", id="desc-input")
            yield Label("Source (channel, URL, username…)")
            yield Input(placeholder="e.g. Discord DM, #general", id="source-input")
            yield Static("", id="evidence-error", classes="error-text")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Add", id="add-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#path-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "add-btn":
            self._add()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _add(self) -> None:
        error = self.query_one("#evidence-error", Static)
        raw_path = self.query_one("#path-input", Input).value.strip()

        if not raw_path:
            error.update("File path is required.")
            return

        src = Path(raw_path).expanduser()
        evidence_type = self.query_one("#type-select", Select).value
        description = self.query_one("#desc-input", Input).value.strip()
        source = self.query_one("#source-input", Input).value.strip()

        try:
            add_evidence(self.case_dir, src, evidence_type, description, source)
        except (FileNotFoundError, ValueError) as e:
            error.update(str(e))
            return

        self.dismiss(True)
