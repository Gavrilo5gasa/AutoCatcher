"""
gui/image_viewer.py — QoL: full-size image viewer for evidence screenshots.

Opened by clicking an image thumbnail in the evidence gallery. Shows the
image at a larger size with Previous/Next to step through every image
evidence item in the case, without closing and reopening the dialog.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

from core.evidence import evidence_path


class ImageViewerDialog(Gtk.Window):
    """Simple lightbox: one big image + Previous/Next + filename/caption."""

    def __init__(self, parent: Gtk.Window, case_dir: Path, records: list, start_index: int) -> None:
        super().__init__(transient_for=parent, modal=True)
        self.case_dir = case_dir
        self.records = records
        self.index = start_index

        self.set_default_size(900, 700)
        self.add_css_class("image-viewer")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        self.prev_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self.prev_btn.connect("clicked", lambda _b: self._step(-1))
        header.pack_start(self.prev_btn)

        self.next_btn = Gtk.Button(icon_name="go-next-symbolic")
        self.next_btn.connect("clicked", lambda _b: self._step(1))
        header.pack_start(self.next_btn)

        self.counter_label = Gtk.Label()
        self.counter_label.add_css_class("dim-label")
        header.pack_end(self.counter_label)

        # Keyboard navigation — Left/Right to step, Escape to close.
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key)
        self.add_controller(key_controller)

        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)
        root.append(self.picture)

        self.caption_label = Gtk.Label(xalign=0, wrap=True)
        self.caption_label.set_margin_top(6)
        self.caption_label.set_margin_bottom(10)
        self.caption_label.set_margin_start(12)
        self.caption_label.set_margin_end(12)
        self.caption_label.set_selectable(True)
        root.append(self.caption_label)

        self.set_child(root)
        self._load_current()

    def _on_key(self, _controller, keyval, _keycode, _state) -> bool:
        name = Gdk.keyval_name(keyval)
        if name == "Left":
            self._step(-1)
            return True
        if name == "Right":
            self._step(1)
            return True
        if name == "Escape":
            self.close()
            return True
        return False

    def _step(self, delta: int) -> None:
        new_index = self.index + delta
        if 0 <= new_index < len(self.records):
            self.index = new_index
            self._load_current()

    def _load_current(self) -> None:
        record = self.records[self.index]
        path = evidence_path(self.case_dir, record)

        self.set_title(record.filename)
        self.counter_label.set_text(f"{self.index + 1} / {len(self.records)}")
        self.prev_btn.set_sensitive(self.index > 0)
        self.next_btn.set_sensitive(self.index < len(self.records) - 1)

        if path.exists():
            self.picture.set_filename(str(path))
        else:
            self.picture.set_filename(None)

        caption_parts = [record.filename]
        if record.description:
            caption_parts.append(record.description)
        if record.source:
            caption_parts.append(f"Source: {record.source}")
        caption_parts.append(f"Added: {record.added_at}")
        caption_parts.append(f"sha256 {record.sha256[:24]}…")
        self.caption_label.set_text("   ·   ".join(caption_parts))
