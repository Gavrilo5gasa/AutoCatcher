"""
tui/screens/case_browser.py — Phase 2.1: Textual app shell, case browser.

The landing screen. Lists every case (newest first), lets you create a
new one, and opens CaseDetailScreen for whichever row is selected.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from config import CASES_DIR
from core.case import list_cases

from tui.widgets.new_case_modal import NewCaseModal

_COLUMNS = ("Case ID", "Subject", "Platform", "Minor", "Created (UTC)")


class CaseBrowserScreen(Screen):
    """Landing screen — browse and create cases."""

    BINDINGS = [
        ("n", "new_case", "New case"),
        ("r", "refresh", "Refresh"),
        ("enter", "open_case", "Open"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(
                "[bold]AutoCatcher[/bold] — [dim]cases stored in "
                f"{CASES_DIR}[/dim]",
                classes="panel-title",
            )
            yield DataTable(id="case-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#case-table", DataTable)
        table.add_columns(*_COLUMNS)
        self.refresh_cases()

    def refresh_cases(self) -> None:
        table = self.query_one("#case-table", DataTable)
        table.clear()
        cases = list_cases()
        if not cases:
            self.notify("No cases yet — press 'n' to create one.", timeout=4)
            return
        for meta in cases:
            minor = "⚠ YES" if meta.minor_involved else "no"
            table.add_row(
                meta.case_id, meta.subject, meta.platform, minor, meta.created_at,
                key=meta.case_id,
            )

    def action_refresh(self) -> None:
        self.refresh_cases()

    def action_new_case(self) -> None:
        self._open_new_case_modal()

    @work
    async def _open_new_case_modal(self) -> None:
        case_id = await self.app.push_screen_wait(NewCaseModal())
        if case_id:
            self.refresh_cases()
            self.notify(f"Case created: {case_id}", severity="information")

    def action_open_case(self) -> None:
        table = self.query_one("#case-table", DataTable)
        if table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        self._open_case(str(row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_case(str(event.row_key.value))

    def _open_case(self, case_id: str) -> None:
        # Imported here to avoid a circular import (case_detail imports back
        # into this module's sibling package on push).
        from tui.screens.case_detail import CaseDetailScreen

        self.app.push_screen(CaseDetailScreen(case_id))
