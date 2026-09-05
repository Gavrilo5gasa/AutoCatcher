"""
tui/screens/case_detail.py — Phase 2.2: Evidence viewer, add-evidence panel.

Also folds in the small amount of remaining case-management surface
(notes, URL archiving) so a case never needs to drop back to the CLI.
Reporting/packing lives in its own screen (Phase 2.3) — see report_screen.py.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
    Button,
)

from core.archive import archive_url, list_archived
from core.case import load_case
from core.evidence import count_evidence, list_evidence
from core.hasher import verify_manifest

from tui.widgets.add_evidence_modal import AddEvidenceModal
from tui.widgets.archive_url_modal import ArchiveUrlModal
from tui.widgets.note_modal import NoteModal

_EVIDENCE_COLUMNS = ("Type", "Filename", "Description", "SHA256", "Added (UTC)")


class CaseDetailScreen(Screen):
    """Everything about one case: overview, evidence, archived links, notes."""

    BINDINGS = [
        ("escape", "back", "Back to cases"),
        ("a", "add_evidence", "Add evidence"),
        ("u", "archive_url", "Archive URL"),
        ("shift+n", "add_note", "Add note"),
        ("v", "verify", "Verify integrity"),
        ("p", "go_report", "Report / Package"),
    ]

    def __init__(self, case_id: str) -> None:
        super().__init__()
        self.case_id = case_id
        self.case_dir, self.meta = load_case(case_id)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="minor-banner")
        with Vertical():
            yield Static(self._header_text(), id="case-detail-header")
            with TabbedContent(initial="overview-tab"):
                with TabPane("Overview", id="overview-tab"):
                    yield Static(id="overview-body")
                    with Horizontal(classes="toolbar"):
                        yield Button("Add note (N)", id="add-note-btn")
                        yield Button("Verify integrity (V)", id="verify-btn")
                with TabPane("Evidence", id="evidence-tab"):
                    yield DataTable(id="evidence-table", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("Add evidence (A)", id="add-evidence-btn", variant="primary")
                with TabPane("Archived URLs", id="archive-tab"):
                    yield DataTable(id="archive-table", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("Archive a URL (U)", id="archive-url-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#evidence-table", DataTable).add_columns("Type", "Filename", "Description", "SHA256", "Added (UTC)")
        self.query_one("#archive-table", DataTable).add_columns("Status", "URL", "Archived URL", "Timestamp")
        self._refresh_all()

    # ── rendering ────────────────────────────────────────────────────────

    def _header_text(self) -> str:
        m = self.meta
        return (
            f"[bold]{m.case_id}[/bold]\n"
            f"Subject: [bold]{m.subject}[/bold]   Platform: {m.platform}   "
            f"Created: {m.created_at}"
        )

    def _refresh_all(self) -> None:
        self.case_dir, self.meta = load_case(self.case_id)

        banner = self.query_one("#minor-banner", Static)
        if self.meta.minor_involved:
            banner.update(
                "⚠  MINOR INVOLVED — file a report with the NCMEC CyberTipline. "
                "Press 'p' to go to Report / Package."
            )
            banner.add_class("-visible")
        else:
            banner.remove_class("-visible")

        self.query_one("#case-detail-header", Static).update(self._header_text())
        self._refresh_overview()
        self._refresh_evidence()
        self._refresh_archive()

    def _refresh_overview(self) -> None:
        counts = count_evidence(self.case_dir)
        archived = list_archived(self.case_dir)
        m = self.meta
        lines = [
            f"Minor involved:  {'[bold red]YES[/bold red]' if m.minor_involved else 'No'}",
            f"Tags:            {', '.join(m.tags) if m.tags else '—'}",
            f"Screenshots:     {counts.get('screenshot', 0)}",
            f"Logs:            {counts.get('log', 0)}",
            f"Files:           {counts.get('file', 0)}",
            f"Archived URLs:   {len(archived)}",
            f"Folder:          {self.case_dir}",
            "",
            "[bold]Notes[/bold]",
        ]
        if m.notes:
            lines.extend(m.notes.splitlines())
        else:
            lines.append("[dim](none yet — press N to add one)[/dim]")
        self.query_one("#overview-body", Static).update("\n".join(lines))

    def _refresh_evidence(self) -> None:
        table = self.query_one("#evidence-table", DataTable)
        table.clear()
        for rec in list_evidence(self.case_dir):
            table.add_row(
                rec.type,
                rec.filename,
                rec.description or "—",
                rec.sha256[:16] + "…",
                rec.added_at,
            )

    def _refresh_archive(self) -> None:
        table = self.query_one("#archive-table", DataTable)
        table.clear()
        for line in list_archived(self.case_dir):
            # Format: [timestamp] [STATUS] url → archived_url (arrow optional)
            status, rest = "?", line
            if "] [" in line:
                try:
                    ts_part, remainder = line.split("] [", 1)
                    status, remainder = remainder.split("]", 1)
                    rest = remainder.strip()
                except ValueError:
                    pass
            if " → " in rest:
                url, archived_url = rest.split(" → ", 1)
            else:
                url, archived_url = rest, ""
            table.add_row(status, url.strip(), archived_url.strip(), line.split("]")[0].lstrip("["))

    # ── actions ──────────────────────────────────────────────────────────

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_go_report(self) -> None:
        from tui.screens.report_screen import ReportScreen

        self.app.push_screen(ReportScreen(self.case_id))

    def action_add_evidence(self) -> None:
        self._open_add_evidence()

    def action_archive_url(self) -> None:
        self._open_archive_url()

    def action_add_note(self) -> None:
        self._open_add_note()

    @work
    async def action_verify(self) -> None:
        self.notify("Re-hashing all evidence…", timeout=2)
        results = verify_manifest(self.case_dir)
        ok, failed, missing = results["ok"], results["failed"], results["missing"]
        total = len(ok) + len(failed) + len(missing)
        if total == 0:
            self.notify("Manifest is empty — no files hashed yet.", severity="warning")
        elif not failed and not missing:
            self.notify(f"All {len(ok)} file(s) verified — hashes match.", severity="information")
        else:
            self.notify(
                f"Integrity issues: {len(failed)} failed, {len(missing)} missing "
                f"(of {total}).",
                severity="error",
                timeout=8,
            )

    @work
    async def _open_add_evidence(self) -> None:
        result = await self.app.push_screen_wait(AddEvidenceModal(self.case_dir))
        if result:
            self._refresh_all()
            self.notify("Evidence added.", severity="information")

    @work
    async def _open_archive_url(self) -> None:
        url = await self.app.push_screen_wait(ArchiveUrlModal())
        if not url:
            return
        self.notify(f"Submitting to Wayback Machine: {url}", timeout=3)
        result = archive_url(self.case_dir, url)
        self._refresh_all()
        if result.status == "failed":
            self.notify(f"Archive failed for {url}", severity="error")
        else:
            self.notify(f"Archived ({result.status}): {result.archived_url}", severity="information")

    @work
    async def _open_add_note(self) -> None:
        result = await self.app.push_screen_wait(NoteModal(self.case_dir))
        if result:
            self._refresh_all()
            self.notify("Note added.", severity="information")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "add-evidence-btn": self._open_add_evidence,
            "archive-url-btn": self._open_archive_url,
            "add-note-btn": self._open_add_note,
            "verify-btn": self.action_verify,
        }
        handler = mapping.get(event.button.id or "")
        if handler:
            handler()
