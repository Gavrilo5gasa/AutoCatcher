"""
gui/pages/overview_page.py — case overview: key facts, notes, links, sub-cases.

QoL rework:
  - Notes render as individual, editable rows (timestamp + text + Edit
    button), not one raw newline-joined text blob. Editing keeps the
    previous text in that note's history rather than discarding it.
  - "Linked Cases" section — cases marked as related to this one, each
    showing the comment explaining *why* they're linked (detective-board
    style), clickable to jump straight to the other case.
  - "Sub-cases" section — cases nested underneath this one (Case Folders,
    e.g. individual members of a community case), also clickable, plus a
    button to create another.
  - Delete Case button, clearly labeled as moving to trash rather than a
    permanent delete.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.archive import list_archived
from core.case import get_note_entries, list_subcases, load_case
from core.evidence import count_evidence


def _section_title(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0)
    label.add_css_class("section-title")
    return label


class OverviewPage(Gtk.Box):
    """Summary of a case: key facts, editable notes, links, and sub-cases."""

    def __init__(
        self,
        case_dir: Path,
        meta,
        on_add_note,
        on_edit_note,
        on_add_link,
        on_add_subcase,
        on_switch_case,
        on_delete_case,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.on_add_note = on_add_note
        self.on_edit_note = on_edit_note
        self.on_add_link = on_add_link
        self.on_add_subcase = on_add_subcase
        self.on_switch_case = on_switch_case
        self.on_delete_case = on_delete_case

        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        outer_scroll = Gtk.ScrolledWindow(vexpand=True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        outer_scroll.set_child(content)
        self.append(outer_scroll)

        # ── key facts ────────────────────────────────────────────────────
        self.grid = Gtk.Grid(row_spacing=4, column_spacing=12)
        content.append(self.grid)

        # ── notes ────────────────────────────────────────────────────────
        notes_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notes_header.append(_section_title("Notes"))
        notes_header.append(Gtk.Box(hexpand=True))
        add_note_btn = Gtk.Button(label="Add Note")
        add_note_btn.connect("clicked", lambda _b: self.on_add_note())
        notes_header.append(add_note_btn)
        content.append(notes_header)

        self.notes_list = Gtk.ListBox()
        self.notes_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.notes_list.add_css_class("boxed-list")
        content.append(self.notes_list)

        self.notes_empty_label = Gtk.Label(label="No notes yet — click Add Note.")
        self.notes_empty_label.add_css_class("dim-label")
        self.notes_empty_label.set_visible(False)
        content.append(self.notes_empty_label)

        # ── linked cases ─────────────────────────────────────────────────
        links_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        links_header.append(_section_title("Linked Cases"))
        links_header.append(Gtk.Box(hexpand=True))
        link_btn = Gtk.Button(label="Link Case")
        link_btn.connect("clicked", lambda _b: self.on_add_link())
        links_header.append(link_btn)
        content.append(links_header)

        self.links_list = Gtk.ListBox()
        self.links_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.links_list.add_css_class("boxed-list")
        content.append(self.links_list)

        self.links_empty_label = Gtk.Label(
            label="No linked cases yet — link cases you think are connected, "
            "with a note on why (e.g. same subject moved to a new server)."
        )
        self.links_empty_label.add_css_class("dim-label")
        self.links_empty_label.set_wrap(True)
        self.links_empty_label.set_visible(False)
        content.append(self.links_empty_label)

        # ── sub-cases (case folders) ─────────────────────────────────────
        sub_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sub_header.append(_section_title("Sub-cases"))
        sub_header.append(Gtk.Box(hexpand=True))
        add_sub_btn = Gtk.Button(label="+ New Sub-case")
        add_sub_btn.connect("clicked", lambda _b: self.on_add_subcase())
        sub_header.append(add_sub_btn)
        content.append(sub_header)

        self.subcases_list = Gtk.ListBox()
        self.subcases_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.subcases_list.add_css_class("boxed-list")
        self.subcases_list.connect(
            "row-activated", lambda _lb, row: self.on_switch_case(row.case_id)
        )
        content.append(self.subcases_list)

        self.subcases_empty_label = Gtk.Label(
            label="No sub-cases yet — useful when this case represents a whole "
            "community (e.g. a Discord server) and you want a separate case "
            "nested underneath it for each member."
        )
        self.subcases_empty_label.add_css_class("dim-label")
        self.subcases_empty_label.set_wrap(True)
        self.subcases_empty_label.set_visible(False)
        content.append(self.subcases_empty_label)

        # ── danger zone ──────────────────────────────────────────────────
        danger_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        danger_header.set_margin_top(10)
        delete_btn = Gtk.Button(label="Delete Case")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", lambda _b: self.on_delete_case())
        danger_header.append(delete_btn)
        delete_hint = Gtk.Label(label="Moves to trash — recoverable, not permanent.")
        delete_hint.add_css_class("dim-label")
        danger_header.append(delete_hint)
        content.append(danger_header)

        self.set_data(case_dir, meta)

    # ── data ─────────────────────────────────────────────────────────────

    def set_data(self, case_dir: Path, meta) -> None:
        self.case_dir = case_dir
        self.meta = meta

        self._refresh_facts()
        self._refresh_notes()
        self._refresh_links()
        self._refresh_subcases()

    def _refresh_facts(self) -> None:
        while (child := self.grid.get_first_child()) is not None:
            self.grid.remove(child)

        counts = count_evidence(self.case_dir)
        archived = list_archived(self.case_dir)

        rows = [
            ("Minor involved", "YES — file with NCMEC" if self.meta.minor_involved else "No"),
            ("Tags", ", ".join(self.meta.tags) if self.meta.tags else "—"),
            ("Screenshots", str(counts.get("screenshot", 0))),
            ("Logs", str(counts.get("log", 0))),
            ("Files", str(counts.get("file", 0))),
            ("Archived URLs", str(len(archived))),
            ("Folder", str(self.case_dir)),
        ]
        if self.meta.parent_case:
            rows.insert(0, ("Parent case", self.meta.parent_case))

        for i, (field, value) in enumerate(rows):
            field_label = Gtk.Label(label=field, xalign=0)
            field_label.add_css_class("dim-label")
            value_label = Gtk.Label(label=value, xalign=0, wrap=True)
            value_label.set_selectable(True)
            self.grid.attach(field_label, 0, i, 1, 1)
            self.grid.attach(value_label, 1, i, 1, 1)

        # Parent case, if any, is clickable — jump straight to the community
        # case this one belongs to.
        if self.meta.parent_case:
            parent_value_widget = self.grid.get_child_at(1, 0)
            parent_btn = Gtk.Button(label=self.meta.parent_case)
            parent_btn.add_css_class("link")
            parent_btn.connect(
                "clicked", lambda _b, cid=self.meta.parent_case: self.on_switch_case(cid)
            )
            self.grid.remove(parent_value_widget)
            self.grid.attach(parent_btn, 1, 0, 1, 1)

    def _refresh_notes(self) -> None:
        while (row := self.notes_list.get_row_at_index(0)) is not None:
            self.notes_list.remove(row)

        entries = get_note_entries(self.meta)
        self.notes_empty_label.set_visible(len(entries) == 0)

        for entry in reversed(entries):  # newest first
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.add_css_class("note-row")

            text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
            ts_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            ts_label = Gtk.Label(label=entry.created_at, xalign=0)
            ts_label.add_css_class("note-row-timestamp")
            ts_row.append(ts_label)
            if entry.edited_at:
                edited_label = Gtk.Label(
                    label=f"· edited {entry.edited_at} · {len(entry.edit_history)} "
                    f"previous version{'s' if len(entry.edit_history) != 1 else ''}"
                )
                edited_label.add_css_class("dim-label")
                ts_row.append(edited_label)
            text_col.append(ts_row)

            text_label = Gtk.Label(label=entry.text, xalign=0, wrap=True)
            text_label.set_selectable(True)
            text_col.append(text_label)
            row_box.append(text_col)

            edit_btn = Gtk.Button(label="Edit")
            edit_btn.connect(
                "clicked",
                lambda _b, nid=entry.id, txt=entry.text: self.on_edit_note(nid, txt),
            )
            row_box.append(edit_btn)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            self.notes_list.append(row)

    def _refresh_links(self) -> None:
        while (row := self.links_list.get_row_at_index(0)) is not None:
            self.links_list.remove(row)

        links = list(reversed(self.meta.linked_cases))  # newest first
        self.links_empty_label.set_visible(len(links) == 0)

        for link in links:
            other_id = link["case_id"]
            comment = link.get("comment", "")
            try:
                _, other_meta = load_case(other_id)
                subject_text = other_meta.subject
            except Exception:
                subject_text = other_id

            row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row_box.set_margin_top(6)
            row_box.set_margin_bottom(6)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            chip = Gtk.Button(label=subject_text)
            chip.add_css_class("case-chip")
            chip.set_tooltip_text(other_id)
            chip.connect("clicked", lambda _b, cid=other_id: self.on_switch_case(cid))
            top_row.append(chip)
            ts_label = Gtk.Label(label=link.get("created_at", ""))
            ts_label.add_css_class("dim-label")
            top_row.append(ts_label)
            row_box.append(top_row)

            if comment:
                comment_label = Gtk.Label(label=comment, xalign=0, wrap=True)
                comment_label.add_css_class("dim-label")
                row_box.append(comment_label)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            self.links_list.append(row)

    def _refresh_subcases(self) -> None:
        while (row := self.subcases_list.get_row_at_index(0)) is not None:
            self.subcases_list.remove(row)

        subcases = list_subcases(self.meta.case_id)
        self.subcases_empty_label.set_visible(len(subcases) == 0)

        for sub_meta in subcases:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_top(6)
            row_box.set_margin_bottom(6)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            subject_label = Gtk.Label(label=sub_meta.subject, xalign=0, hexpand=True)
            meta_label = Gtk.Label(
                label=f"{sub_meta.platform} · {sub_meta.created_at}", xalign=0
            )
            meta_label.add_css_class("dim-label")
            row_box.append(subject_label)
            row_box.append(meta_label)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            row.case_id = sub_meta.case_id
            self.subcases_list.append(row)
