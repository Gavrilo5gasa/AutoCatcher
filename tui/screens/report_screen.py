"""
tui/screens/report_screen.py — Phase 2.3: Reporting flow, packing UI.

Generates reporting guides (Discord / NCMEC / generic) and packages the
case into a submission-ready zip, mirroring `main.py report *` and
`main.py package`.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from core.case import load_case
from core.packager import package_case
from reporters import discord as rep_discord
from reporters import generic as rep_generic
from reporters import ncmec as rep_ncmec

from tui.widgets.confirm_modal import ConfirmModal


class ReportScreen(Screen):
    """Generate reporting guides and package a case for submission."""

    BINDINGS = [
        ("escape", "back", "Back to case"),
    ]

    def __init__(self, case_id: str) -> None:
        super().__init__()
        self.case_id = case_id
        self.case_dir, self.meta = load_case(case_id)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="minor-banner")
        with Vertical():
            yield Static(
                f"[bold]Report & Package[/bold] — {self.case_id}", classes="panel-title"
            )
            with Horizontal(id="report-buttons"):
                yield Button("Discord guide", id="discord-btn")
                yield Button("NCMEC guide", id="ncmec-btn", variant="warning")
                yield Button("Generic guide", id="generic-btn")
                yield Button("Package case (verify + PDF + zip)", id="package-btn", variant="primary")
            yield Static(
                "Select a reporting target above to generate a step-by-step "
                "guide, or package the whole case for submission.",
                id="report-output",
            )
            yield Static(id="package-status")
        yield Footer()

    def on_mount(self) -> None:
        banner = self.query_one("#minor-banner", Static)
        if self.meta.minor_involved:
            banner.update(
                "⚠  MINOR INVOLVED — submit to NCMEC FIRST, then the platform, "
                "then local police / FBI IC3 (ic3.gov)."
            )
            banner.add_class("-visible")

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "discord-btn":
            self._generate_discord()
        elif bid == "ncmec-btn":
            self._maybe_generate_ncmec()
        elif bid == "generic-btn":
            self._generate_generic()
        elif bid == "package-btn":
            self._package()

    # ── guide generation ─────────────────────────────────────────────────

    def _render_guide(self, guide) -> None:
        lines = [f"[bold]{guide.title}[/bold]", f"Submit at: {guide.submit_url}", ""]
        lines.append("[bold]Checklist[/bold]")
        for i, step in enumerate(guide.checklist, 1):
            lines.append(f"  {i}. {step}")
        lines.append("")
        lines.append("[bold]Template[/bold]")
        lines.append(guide.template)
        if guide.notes:
            lines.append("")
            lines.append("[bold]Notes[/bold]")
            lines.append(guide.notes)
        if guide.guide_path:
            lines.append("")
            lines.append(f"[dim]Guide written to: {guide.guide_path}[/dim]")
        self.query_one("#report-output", Static).update("\n".join(lines))

    def _generate_discord(self) -> None:
        guide = rep_discord.generate_guide(self.case_dir)
        self._render_guide(guide)
        if self.meta.minor_involved:
            self.notify("MINOR INVOLVED — also generate the NCMEC guide.", severity="warning")

    @work
    async def _maybe_generate_ncmec(self) -> None:
        if not self.meta.minor_involved:
            confirmed = await self.app.push_screen_wait(
                ConfirmModal(
                    "minor_involved is not set for this case. NCMEC is intended "
                    "for cases involving minors. Generate the guide anyway?",
                    confirm_label="Generate anyway",
                    danger=True,
                )
            )
            if not confirmed:
                return
        guide = rep_ncmec.generate_guide(self.case_dir)
        self._render_guide(guide)
        self.notify(
            "After NCMEC: report to the platform, then file with local police "
            "or FBI IC3 (ic3.gov). Keep your NCMEC tip number.",
            timeout=8,
        )

    def _generate_generic(self) -> None:
        guide = rep_generic.generate_guide(self.case_dir)
        self._render_guide(guide)
        if self.meta.minor_involved:
            self.notify("MINOR INVOLVED — also generate the NCMEC guide.", severity="warning")

    # ── packaging ────────────────────────────────────────────────────────

    @work
    async def _package(self) -> None:
        status = self.query_one("#package-status", Static)
        status.update("Packaging… verifying manifest, generating PDF, building zip.")
        status.add_class("-visible")
        try:
            zip_path = package_case(self.case_dir)
        except Exception as e:  # noqa: BLE001 — surface any packaging failure to the user
            status.update(f"[bold red]Packaging failed:[/bold red] {e}")
            self.notify("Packaging failed.", severity="error")
            return

        lines = [f"[bold green]Package ready:[/bold green] {zip_path.name}", f"Location: {zip_path}"]
        if self.meta.minor_involved:
            lines.append("")
            lines.append(
                "[bold red]MINOR INVOLVED — submit to NCMEC FIRST[/bold red] "
                "(cybertipline.org), then the platform, then local police."
            )
        else:
            lines.append("")
            lines.append("Next: generate a Discord or generic guide above and submit this zip.")
        status.update("\n".join(lines))
        self.notify("Package ready.", severity="information")
