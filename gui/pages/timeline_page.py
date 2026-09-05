"""
gui/pages/timeline_page.py — Phase 3.2: timeline view.

Merges everything that happened in a case — creation, evidence added,
URLs archived, notes appended — into one chronological feed.
Timestamps are the "2026-05-20 14:32:01 UTC" format from utils/timestamp.py,
which sorts correctly as plain strings, so no parsing is needed.
"""

import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.archive import list_archived
from core.evidence import list_evidence

_NOTE_LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s*(?P<text>.*)$")


class TimelinePage(Gtk.Box):
    """Read-only chronological feed of everything recorded in a case."""

    def __init__(self, case_dir: Path, meta) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list_box)
        self.append(scroll)

        self.set_data(case_dir, meta)

    def set_data(self, case_dir: Path, meta) -> None:
        self.case_dir = case_dir
        self.meta = meta
        self.refresh()

    def refresh(self) -> None:
        while (row := self.list_box.get_row_at_index(0)) is not None:
            self.list_box.remove(row)

        events = self._collect_events()
        events.sort(key=lambda e: e[0])

        if not events:
            placeholder = Gtk.Label(label="Nothing recorded yet.")
            placeholder.add_css_class("dim-label")
            self.list_box.append(placeholder)
            return

        for ts, kind, text in events:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.add_css_class("timeline-row")

            ts_label = Gtk.Label(label=ts.replace(" UTC", ""), xalign=0)
            ts_label.add_css_class("dim-label")
            row.append(ts_label)

            kind_label = Gtk.Label(label=kind, xalign=0)
            kind_label.add_css_class("timeline-kind")
            row.append(kind_label)

            text_label = Gtk.Label(label=text, xalign=0, hexpand=True, wrap=True)
            row.append(text_label)

            self.list_box.append(row)

    def _collect_events(self) -> list[tuple[str, str, str]]:
        events: list[tuple[str, str, str]] = []

        events.append((self.meta.created_at, "Case", f"Case created for {self.meta.subject} on {self.meta.platform}"))

        for rec in list_evidence(self.case_dir):
            desc = f" — {rec.description}" if rec.description else ""
            events.append((rec.added_at, "Evidence", f"[{rec.type}] {rec.filename}{desc}"))

        for line in list_archived(self.case_dir):
            m = re.match(r"^\[(?P<ts>[^\]]+)\]\s*\[(?P<status>[^\]]+)\]\s*(?P<rest>.*)$", line)
            if m:
                events.append((m.group("ts"), "Archive", f"{m.group('status').strip()}  {m.group('rest')}"))

        if self.meta.notes:
            for note_line in self.meta.notes.splitlines():
                m = _NOTE_LINE_RE.match(note_line.strip())
                if m:
                    events.append((m.group("ts"), "Note", m.group("text")))
                elif note_line.strip():
                    events.append((self.meta.created_at, "Note", note_line.strip()))

        return events
