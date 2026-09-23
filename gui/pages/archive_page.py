"""
gui/pages/archive_page.py — QoL: dedicated URL Archive tab.

Previously "Archive URL" was a single button crammed into the case
header, with no way to see what had already been archived without
switching to the Overview count or reading archived_links.txt by hand.
This gives it a real home: a list of every archive attempt for the case,
plus the action to add a new one.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from core.archive import archive_url, list_archived


class ArchivePage(Gtk.Box):
    """List of archived URLs for a case, plus the action to archive a new one."""

    def __init__(self, case_dir: Path, on_notify) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_notify = on_notify
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Archived URLs", xalign=0, hexpand=True)
        title.add_css_class("case-title")
        archive_btn = Gtk.Button(label="Archive New URL")
        archive_btn.add_css_class("suggested-action")
        archive_btn.connect("clicked", lambda _b: self._open_archive_dialog())
        toolbar.append(title)
        toolbar.append(archive_btn)
        self.append(toolbar)

        hint = Gtk.Label(
            label=(
                "Archive a profile, chat, or post URL before it can be deleted. "
                "Every attempt — successful or not — is kept below."
            ),
            xalign=0,
            wrap=True,
        )
        hint.add_css_class("dim-label")
        self.append(hint)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.list_box)
        self.append(scroll)

        self.empty_label = Gtk.Label(label="Nothing archived yet.")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_visible(False)
        self.append(self.empty_label)

        self.set_case(case_dir)

    def set_case(self, case_dir: Path) -> None:
        self.case_dir = case_dir
        self.refresh()

    def refresh(self) -> None:
        while (row := self.list_box.get_row_at_index(0)) is not None:
            self.list_box.remove(row)

        lines = list_archived(self.case_dir)
        self.empty_label.set_visible(len(lines) == 0)

        for line in reversed(lines):  # newest first
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=line, xalign=0, wrap=True, selectable=True)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_margin_start(8)
            label.set_margin_end(8)
            row.set_child(label)
            self.list_box.append(row)

    def _open_archive_dialog(self) -> None:
        # Imported lazily to avoid a circular import with gui.dialogs, which
        # doesn't need to know about this page.
        from gui.dialogs import ArchiveUrlDialog

        window = self.get_root()

        def on_submit(url: str) -> None:
            self.on_notify(f"Submitting to Wayback Machine: {url}", error=False)

            def do_archive():
                result = archive_url(self.case_dir, url)
                GLib.idle_add(self._after_archive, result)
                return False

            GLib.idle_add(do_archive)

        ArchiveUrlDialog(window, on_submit=on_submit).present()

    def _after_archive(self, result) -> bool:
        self.refresh()
        if result.status == "failed":
            self.on_notify(f"Archive failed for {result.url}", error=True)
        else:
            self.on_notify(f"Archived ({result.status}): {result.archived_url}", error=False)
        return False
