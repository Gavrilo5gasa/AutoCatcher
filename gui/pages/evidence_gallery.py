"""
gui/pages/evidence_gallery.py — Phase 3.2: evidence gallery.

Shows every piece of evidence as a card (type, filename, description,
short hash, timestamp) in a wrapping FlowBox, plus add/verify actions.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.evidence import list_evidence
from core.hasher import verify_manifest

_TYPE_ICONS = {"screenshot": "🖼", "log": "📝", "file": "📄"}


class EvidenceGalleryPage(Gtk.Box):
    """Wrapping card gallery of all evidence added to a case."""

    def __init__(self, case_dir: Path, on_add_evidence, on_notify) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_notify = on_notify
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn = Gtk.Button(label="Add Evidence")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", lambda _b: on_add_evidence())
        verify_btn = Gtk.Button(label="Verify Integrity")
        verify_btn.connect("clicked", lambda _b: self._verify())
        toolbar.append(add_btn)
        toolbar.append(verify_btn)
        self.append(toolbar)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(6)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_row_spacing(10)
        self.flow_box.set_column_spacing(10)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.flow_box)
        self.append(scroll)

        self.empty_label = Gtk.Label(label="No evidence added yet.")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_visible(False)
        self.append(self.empty_label)

        self.set_case(case_dir)

    def set_case(self, case_dir: Path) -> None:
        self.case_dir = case_dir
        self.refresh()

    def refresh(self) -> None:
        while (child := self.flow_box.get_first_child()) is not None:
            self.flow_box.remove(child)

        records = list_evidence(self.case_dir)
        self.empty_label.set_visible(len(records) == 0)

        for rec in records:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class("evidence-card")

            type_label = Gtk.Label(
                label=f"{_TYPE_ICONS.get(rec.type, '📄')}  {rec.type.upper()}", xalign=0
            )
            type_label.add_css_class("evidence-card-type")
            card.append(type_label)

            filename_label = Gtk.Label(label=rec.filename, xalign=0, wrap=True)
            filename_label.set_selectable(True)
            card.append(filename_label)

            if rec.description:
                desc_label = Gtk.Label(label=rec.description, xalign=0, wrap=True)
                desc_label.add_css_class("evidence-card-desc")
                card.append(desc_label)

            if rec.source:
                source_label = Gtk.Label(label=f"Source: {rec.source}", xalign=0, wrap=True)
                source_label.add_css_class("dim-label")
                card.append(source_label)

            hash_label = Gtk.Label(label=f"sha256 {rec.sha256[:16]}…", xalign=0)
            hash_label.add_css_class("dim-label")
            card.append(hash_label)

            added_label = Gtk.Label(label=rec.added_at, xalign=0)
            added_label.add_css_class("dim-label")
            card.append(added_label)

            self.flow_box.append(card)

    def _verify(self) -> None:
        results = verify_manifest(self.case_dir)
        ok, failed, missing = results["ok"], results["failed"], results["missing"]
        total = len(ok) + len(failed) + len(missing)
        if total == 0:
            self.on_notify("Manifest is empty — no files hashed yet.", error=False)
        elif not failed and not missing:
            self.on_notify(f"All {len(ok)} file(s) verified — hashes match.", error=False)
        else:
            self.on_notify(
                f"Integrity issues: {len(failed)} failed, {len(missing)} missing "
                f"(of {total}).",
                error=True,
            )
