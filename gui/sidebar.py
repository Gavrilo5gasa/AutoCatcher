"""
gui/sidebar.py — Phase 3.1: case list sidebar.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.case import list_cases


class CaseSidebar(Gtk.Box):
    """Lists every case, newest first, with a button to create a new one."""

    def __init__(self, on_select, on_new) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_select = on_select
        self.on_new = on_new
        self.add_css_class("sidebar")
        self.set_size_request(260, -1)

        new_btn = Gtk.Button(label="+ New Case")
        new_btn.add_css_class("suggested-action")
        new_btn.set_margin_top(8)
        new_btn.set_margin_bottom(8)
        new_btn.set_margin_start(8)
        new_btn.set_margin_end(8)
        new_btn.connect("clicked", lambda _b: self.on_new())
        self.append(new_btn)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list_box)
        self.append(scroll)

        self.empty_label = Gtk.Label(label="No cases yet.\nClick + New Case to start.")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_margin_top(20)
        self.empty_label.set_visible(False)
        self.append(self.empty_label)

        self.refresh()

    def refresh(self, select_case_id: str | None = None) -> None:
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        cases = list_cases()
        self.empty_label.set_visible(len(cases) == 0)

        select_row = None
        for meta in cases:
            row = Gtk.ListBoxRow()
            row.case_id = meta.case_id  # stash for lookup on activation

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class("case-row")

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            subject_label = Gtk.Label(label=meta.subject, xalign=0, hexpand=True)
            subject_label.add_css_class("case-row-subject")
            subject_label.set_ellipsize(True)
            top.append(subject_label)
            if meta.minor_involved:
                badge = Gtk.Label(label="MINOR")
                badge.add_css_class("minor-badge")
                top.append(badge)
            box.append(top)

            meta_label = Gtk.Label(
                label=f"{meta.platform} · {meta.created_at}", xalign=0
            )
            meta_label.add_css_class("case-row-meta")
            box.append(meta_label)

            row.set_child(box)
            self.list_box.append(row)

            if select_case_id and meta.case_id == select_case_id:
                select_row = row

        if select_row is not None:
            self.list_box.select_row(select_row)

    def _on_row_activated(self, _list_box, row) -> None:
        self.on_select(row.case_id)
