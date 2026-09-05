"""
gui/dialogs.py — Modal dialogs shared across the GTK4 app.

Mirrors tui/widgets/*_modal.py one-to-one, just with GTK4 widgets instead
of Textual ones. Each dialog does its own core/ call on confirm and hands
the result back via a callback (GTK4 dialogs are async/signal-driven, so
we don't return values the way the Textual modals do).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.case import append_note, create_case, load_case
from core.evidence import add_evidence
from utils.platform import example_evidence_path

_EVIDENCE_TYPES = [("Screenshot", "screenshot"), ("Log / chat export", "log"), ("Other file", "file")]


def _content_box(dialog: Gtk.Dialog) -> Gtk.Box:
    box = dialog.get_content_area()
    box.set_spacing(8)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    return box


def _error_label() -> Gtk.Label:
    label = Gtk.Label(label="")
    label.add_css_class("error-label")
    label.set_wrap(True)
    label.set_xalign(0)
    return label


# ── New case ─────────────────────────────────────────────────────────────────


class NewCaseDialog(Gtk.Dialog):
    """Create a case. Calls on_created(case_id) once the case exists."""

    def __init__(self, parent: Gtk.Window, on_created) -> None:
        super().__init__(title="New Case", transient_for=parent, modal=True)
        self.on_created = on_created
        self.set_default_size(420, -1)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        create_btn = self.add_button("Create", Gtk.ResponseType.OK)
        create_btn.add_css_class("suggested-action")

        box = _content_box(self)

        box.append(Gtk.Label(label="Subject username / handle", xalign=0))
        self.subject_entry = Gtk.Entry(placeholder_text="e.g. bad_user#1234")
        box.append(self.subject_entry)

        box.append(Gtk.Label(label="Platform", xalign=0))
        self.platform_entry = Gtk.Entry(placeholder_text="e.g. discord, twitter, roblox")
        box.append(self.platform_entry)

        self.minor_check = Gtk.CheckButton(label="Minor involved (enables NCMEC warnings)")
        box.append(self.minor_check)

        box.append(Gtk.Label(label="Opening notes (optional)", xalign=0))
        self.notes_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD)
        notes_scroll = Gtk.ScrolledWindow(min_content_height=80)
        notes_scroll.set_child(self.notes_view)
        box.append(notes_scroll)

        self.error_label = _error_label()
        box.append(self.error_label)

        self.connect("response", self._on_response)
        self.subject_entry.grab_focus()

    def _on_response(self, dialog, response) -> None:
        if response != Gtk.ResponseType.OK:
            self.destroy()
            return

        subject = self.subject_entry.get_text().strip()
        platform = self.platform_entry.get_text().strip()
        if not subject:
            self.error_label.set_text("Subject is required.")
            return
        if not platform:
            self.error_label.set_text("Platform is required.")
            return

        buf = self.notes_view.get_buffer()
        notes = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()

        case_dir = create_case(
            subject=subject,
            platform=platform,
            notes=notes,
            minor_involved=self.minor_check.get_active(),
        )
        _, meta = load_case(case_dir.name)
        self.destroy()
        self.on_created(meta.case_id)


# ── Add evidence ─────────────────────────────────────────────────────────────


class AddEvidenceDialog(Gtk.Dialog):
    """Add a piece of evidence to a case. Calls on_added() on success."""

    def __init__(self, parent: Gtk.Window, case_dir: Path, on_added) -> None:
        super().__init__(title="Add Evidence", transient_for=parent, modal=True)
        self.case_dir = case_dir
        self.on_added = on_added
        self.set_default_size(460, -1)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        add_btn = self.add_button("Add", Gtk.ResponseType.OK)
        add_btn.add_css_class("suggested-action")

        box = _content_box(self)

        box.append(Gtk.Label(label="File path (screenshot, log export, anything)", xalign=0))
        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.path_entry = Gtk.Entry(placeholder_text=example_evidence_path(), hexpand=True)
        browse_btn = Gtk.Button(label="Browse…")
        browse_btn.connect("clicked", self._on_browse)
        path_row.append(self.path_entry)
        path_row.append(browse_btn)
        box.append(path_row)

        box.append(Gtk.Label(label="Type", xalign=0))
        self.type_dropdown = Gtk.DropDown.new_from_strings([label for label, _ in _EVIDENCE_TYPES])
        box.append(self.type_dropdown)

        box.append(Gtk.Label(label="Description (what does this show?)", xalign=0))
        self.desc_entry = Gtk.Entry(placeholder_text="e.g. DM asking to move to Telegram")
        box.append(self.desc_entry)

        box.append(Gtk.Label(label="Source (channel, URL, username…)", xalign=0))
        self.source_entry = Gtk.Entry(placeholder_text="e.g. Discord DM, #general")
        box.append(self.source_entry)

        self.error_label = _error_label()
        box.append(self.error_label)

        self.connect("response", self._on_response)
        self.path_entry.grab_focus()

    def _on_browse(self, _button) -> None:
        file_dialog = Gtk.FileDialog(title="Select evidence file")
        file_dialog.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, file_dialog: Gtk.FileDialog, result) -> None:
        try:
            gfile = file_dialog.open_finish(result)
        except Exception:
            return  # cancelled
        if gfile is not None:
            path = gfile.get_path()
            if path:
                self.path_entry.set_text(path)

    def _on_response(self, dialog, response) -> None:
        if response != Gtk.ResponseType.OK:
            self.destroy()
            return

        raw_path = self.path_entry.get_text().strip()
        if not raw_path:
            self.error_label.set_text("File path is required.")
            return

        src = Path(raw_path).expanduser()
        evidence_type = _EVIDENCE_TYPES[self.type_dropdown.get_selected()][1]
        description = self.desc_entry.get_text().strip()
        source = self.source_entry.get_text().strip()

        try:
            add_evidence(self.case_dir, src, evidence_type, description, source)
        except (FileNotFoundError, ValueError) as e:
            self.error_label.set_text(str(e))
            return

        self.destroy()
        self.on_added()


# ── Archive URL ──────────────────────────────────────────────────────────────


class ArchiveUrlDialog(Gtk.Dialog):
    """Collects a URL to archive. Calls on_submit(url) — the caller does the
    actual network call so this dialog never blocks on I/O."""

    def __init__(self, parent: Gtk.Window, on_submit) -> None:
        super().__init__(title="Archive URL", transient_for=parent, modal=True)
        self.on_submit = on_submit
        self.set_default_size(420, -1)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        archive_btn = self.add_button("Archive", Gtk.ResponseType.OK)
        archive_btn.add_css_class("suggested-action")

        box = _content_box(self)
        box.append(Gtk.Label(label="URL to snapshot on the Wayback Machine", xalign=0))
        self.url_entry = Gtk.Entry(placeholder_text="https://x.com/someprofile")
        box.append(self.url_entry)

        hint = Gtk.Label(
            label="This can take a few seconds — the app will stay responsive.",
            xalign=0,
        )
        hint.add_css_class("dim-label")
        box.append(hint)

        self.error_label = _error_label()
        box.append(self.error_label)

        self.connect("response", self._on_response)
        self.url_entry.grab_focus()

    def _on_response(self, dialog, response) -> None:
        if response != Gtk.ResponseType.OK:
            self.destroy()
            return
        url = self.url_entry.get_text().strip()
        if not url:
            self.error_label.set_text("URL is required.")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            self.error_label.set_text("URL must start with http:// or https://")
            return
        self.destroy()
        self.on_submit(url)


# ── Add note ─────────────────────────────────────────────────────────────────


class NoteDialog(Gtk.Dialog):
    """Appends a timestamped note to a case. Calls on_added() on success."""

    def __init__(self, parent: Gtk.Window, case_dir: Path, on_added) -> None:
        super().__init__(title="Add Note", transient_for=parent, modal=True)
        self.case_dir = case_dir
        self.on_added = on_added
        self.set_default_size(420, -1)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        add_btn = self.add_button("Add Note", Gtk.ResponseType.OK)
        add_btn.add_css_class("suggested-action")

        box = _content_box(self)
        hint = Gtk.Label(
            label="Notes are timestamped and append-only — nothing is ever overwritten.",
            xalign=0,
        )
        hint.set_wrap(True)
        box.append(hint)

        self.note_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD)
        scroll = Gtk.ScrolledWindow(min_content_height=100)
        scroll.set_child(self.note_view)
        box.append(scroll)

        self.error_label = _error_label()
        box.append(self.error_label)

        self.connect("response", self._on_response)
        self.note_view.grab_focus()

    def _on_response(self, dialog, response) -> None:
        if response != Gtk.ResponseType.OK:
            self.destroy()
            return
        buf = self.note_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not text:
            self.error_label.set_text("Note can't be empty.")
            return
        append_note(self.case_dir, text)
        self.destroy()
        self.on_added()


# ── Generic confirm ──────────────────────────────────────────────────────────


class ConfirmDialog(Gtk.Dialog):
    """A simple Yes/No confirmation. Calls on_result(True|False)."""

    def __init__(self, parent: Gtk.Window, message: str, on_result, confirm_label: str = "Yes") -> None:
        super().__init__(title="Confirm", transient_for=parent, modal=True)
        self.on_result = on_result
        self.set_default_size(380, -1)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        confirm_btn = self.add_button(confirm_label, Gtk.ResponseType.OK)
        confirm_btn.add_css_class("destructive-action")

        box = _content_box(self)
        label = Gtk.Label(label=message, xalign=0)
        label.set_wrap(True)
        box.append(label)

        self.connect("response", lambda d, r: (self.destroy(), self.on_result(r == Gtk.ResponseType.OK)))
