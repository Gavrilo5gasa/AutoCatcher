"""
gui/pages/overview_page.py — case overview: key facts + append-only notes.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.archive import list_archived
from core.evidence import count_evidence


class OverviewPage(Gtk.Box):
    """Read-only summary of a case plus its notes."""

    def __init__(self, case_dir: Path, meta, on_add_note) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.grid = Gtk.Grid(row_spacing=4, column_spacing=12)
        self.append(self.grid)

        notes_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notes_title = Gtk.Label(label="Notes", xalign=0, hexpand=True)
        notes_title.add_css_class("case-title")
        add_note_btn = Gtk.Button(label="Add Note")
        add_note_btn.connect("clicked", lambda _b: on_add_note())
        notes_header.append(notes_title)
        notes_header.append(add_note_btn)
        self.append(notes_header)

        self.notes_label = Gtk.Label(xalign=0)
        self.notes_label.set_wrap(True)
        self.notes_label.set_selectable(True)
        notes_scroll = Gtk.ScrolledWindow(vexpand=True)
        notes_scroll.set_child(self.notes_label)
        self.append(notes_scroll)

        self.set_data(case_dir, meta)

    def set_data(self, case_dir: Path, meta) -> None:
        self.case_dir = case_dir
        self.meta = meta

        while (child := self.grid.get_first_child()) is not None:
            self.grid.remove(child)

        counts = count_evidence(case_dir)
        archived = list_archived(case_dir)

        rows = [
            ("Minor involved", "YES — file with NCMEC" if meta.minor_involved else "No"),
            ("Tags", ", ".join(meta.tags) if meta.tags else "—"),
            ("Screenshots", str(counts.get("screenshot", 0))),
            ("Logs", str(counts.get("log", 0))),
            ("Files", str(counts.get("file", 0))),
            ("Archived URLs", str(len(archived))),
            ("Folder", str(case_dir)),
        ]
        for i, (field, value) in enumerate(rows):
            field_label = Gtk.Label(label=field, xalign=0)
            field_label.add_css_class("dim-label")
            value_label = Gtk.Label(label=value, xalign=0, wrap=True)
            value_label.set_selectable(True)
            self.grid.attach(field_label, 0, i, 1, 1)
            self.grid.attach(value_label, 1, i, 1, 1)

        self.notes_label.set_text(meta.notes if meta.notes else "(none yet — click Add Note)")
