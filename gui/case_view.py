"""
gui/case_view.py — assembles one case's content: header + tabbed pages.

Ties together Overview, Evidence gallery, Archive, Timeline (3.2), and the
Report wizard (3.3) into a single Gtk.Notebook, and owns the dialogs
that mutate case state (add evidence, add note, link case, archive URL).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.case import delete_case, load_case

from gui.dialogs import (
    AddEvidenceDialog,
    DeleteCaseDialog,
    EditNoteDialog,
    LinkCaseDialog,
    NewCaseDialog,
    NoteDialog,
)
from gui.pages.archive_page import ArchivePage
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
        # "Archive URL" used to live here as a header button — it now has
        # its own tab (see the Archive page below), so the header is just
        # the case title and minor-involved banner.
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

        self.overview_page = OverviewPage(
            self.case_dir,
            self.meta,
            on_add_note=self._open_add_note,
            on_edit_note=self._open_edit_note,
            on_add_link=self._open_link_case,
            on_add_subcase=self._open_add_subcase,
            on_switch_case=self._switch_case,
            on_delete_case=self._open_delete_case,
        )
        self.notebook.append_page(self.overview_page, Gtk.Label(label="Overview"))

        self.evidence_page = EvidenceGalleryPage(
            self.case_dir,
            get_window=get_window,
            on_add_evidence=self._open_add_evidence,
            on_notify=on_notify,
        )
        self.notebook.append_page(self.evidence_page, Gtk.Label(label="Evidence"))

        self.archive_page = ArchivePage(self.case_dir, on_notify=on_notify)
        self.notebook.append_page(self.archive_page, Gtk.Label(label="Archive"))

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
        self.archive_page.set_case(self.case_dir)
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

    def _open_edit_note(self, note_id: str, current_text: str) -> None:
        EditNoteDialog(
            self.get_window(), self.case_dir, note_id, current_text, on_edited=self._after_change
        ).present()

    def _open_link_case(self) -> None:
        LinkCaseDialog(
            self.get_window(), self.case_dir, self.case_id, on_linked=self._after_change
        ).present()

    def _open_add_subcase(self) -> None:
        NewCaseDialog(
            self.get_window(), on_created=self._after_subcase_created, parent_case=self.case_id
        ).present()

    def _open_delete_case(self) -> None:
        DeleteCaseDialog(self.get_window(), self.case_id, on_result=self._on_delete_confirmed).present()

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        case_id = self.case_id
        delete_case(case_id)
        self.get_window().sidebar.refresh()
        self.get_window().close_case(case_id)
        self.on_notify(f"Case moved to trash: {case_id}", error=False)

    def _after_subcase_created(self, new_case_id: str) -> None:
        self._after_change()
        self.get_window().sidebar.refresh()
        self.on_notify(f"Sub-case created: {new_case_id}", error=False)

    def _switch_case(self, other_case_id: str) -> None:
        self.get_window().show_case(other_case_id)

    def _after_change(self) -> None:
        self.refresh()
