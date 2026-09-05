"""
gui/case_view.py — assembles one case's content: header + tabbed pages.

Ties together Overview, Evidence gallery, Timeline (3.2), and the
Report wizard (3.3) into a single Gtk.Notebook, and owns the dialogs
that mutate case state (add evidence, add note, archive URL).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from core.archive import archive_url
from core.case import load_case

from gui.dialogs import AddEvidenceDialog, ArchiveUrlDialog, NoteDialog
from gui.pages.evidence_gallery import EvidenceGalleryPage
from gui.pages.overview_page import OverviewPage
from gui.pages.report_wizard import ReportWizardPage
from gui.pages.timeline_page import TimelinePage


class CaseView(Gtk.Box):
    """Everything about one case: header, minor banner, tabs."""

    def __init__(self, case_id: str, get_window, on_notify) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.case_id = case_id
        self.get_window = get_window
        self.on_notify = on_notify
        self.case_dir, self.meta = load_case(case_id)

        # ── header ───────────────────────────────────────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("case-header")

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.title_label = Gtk.Label(xalign=0, hexpand=True)
        self.title_label.add_css_class("case-title")
        title_row.append(self.title_label)

        archive_btn = Gtk.Button(label="Archive URL")
        archive_btn.connect("clicked", lambda _b: self._open_archive_url())
        title_row.append(archive_btn)
        header.append(title_row)

        self.subtitle_label = Gtk.Label(xalign=0)
        self.subtitle_label.add_css_class("dim-label")
        header.append(self.subtitle_label)

        self.minor_banner = Gtk.Label(xalign=0, wrap=True)
        self.minor_banner.add_css_class("minor-banner")
        self.minor_banner.set_visible(False)
        self.minor_banner.set_margin_top(6)
        header.append(self.minor_banner)

        self.append(header)

        # ── tabs ─────────────────────────────────────────────────────────
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)

        self.overview_page = OverviewPage(self.case_dir, self.meta, on_add_note=self._open_add_note)
        self.notebook.append_page(self.overview_page, Gtk.Label(label="Overview"))

        self.evidence_page = EvidenceGalleryPage(
            self.case_dir, on_add_evidence=self._open_add_evidence, on_notify=on_notify
        )
        self.notebook.append_page(self.evidence_page, Gtk.Label(label="Evidence"))

        self.timeline_page = TimelinePage(self.case_dir, self.meta)
        self.notebook.append_page(self.timeline_page, Gtk.Label(label="Timeline"))

        self.report_page = ReportWizardPage(
            self.case_dir, self.meta, get_window=get_window, on_notify=on_notify
        )
        self.notebook.append_page(self.report_page, Gtk.Label(label="Report & Package"))

        self.append(self.notebook)

        self._refresh_header()

    # ── refresh ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self.case_dir, self.meta = load_case(self.case_id)
        self._refresh_header()
        self.overview_page.set_data(self.case_dir, self.meta)
        self.evidence_page.set_case(self.case_dir)
        self.timeline_page.set_data(self.case_dir, self.meta)
        self.report_page.set_case(self.case_dir, self.meta)

    def _refresh_header(self) -> None:
        self.title_label.set_text(self.case_id)
        self.subtitle_label.set_text(
            f"Subject: {self.meta.subject}    Platform: {self.meta.platform}    "
            f"Created: {self.meta.created_at}"
        )
        if self.meta.minor_involved:
            self.minor_banner.set_text(
                "⚠  MINOR INVOLVED — file a report with the NCMEC CyberTipline. "
                "See the Report & Package tab."
            )
            self.minor_banner.set_visible(True)
        else:
            self.minor_banner.set_visible(False)

    # ── dialogs ──────────────────────────────────────────────────────────

    def _open_add_evidence(self) -> None:
        AddEvidenceDialog(self.get_window(), self.case_dir, on_added=self._after_change).present()

    def _open_add_note(self) -> None:
        NoteDialog(self.get_window(), self.case_dir, on_added=self._after_change).present()

    def _open_archive_url(self) -> None:
        def on_submit(url: str) -> None:
            self.on_notify(f"Submitting to Wayback Machine: {url}", error=False)

            def do_archive():
                result = archive_url(self.case_dir, url)
                GLib.idle_add(self._after_archive, result)
                return False

            GLib.idle_add(do_archive)

        ArchiveUrlDialog(self.get_window(), on_submit=on_submit).present()

    def _after_archive(self, result) -> bool:
        self.refresh()
        if result.status == "failed":
            self.on_notify(f"Archive failed for {result.url}", error=True)
        else:
            self.on_notify(f"Archived ({result.status}): {result.archived_url}", error=False)
        return False

    def _after_change(self) -> None:
        self.refresh()
