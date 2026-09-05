"""
gui/main_window.py — Phase 3.1: GTK4 window shell.

HeaderBar + Paned(sidebar | content). The sidebar lists cases; the
content area is a Stack that swaps in a CaseView per selected case
(built lazily, cached so switching back and forth is instant).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from config import APP_NAME, APP_VERSION

from gui.case_view import CaseView
from gui.dialogs import NewCaseDialog
from gui.sidebar import CaseSidebar

_STATUS_CLEAR_SECONDS = 5


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application)
        self.set_title(APP_NAME)
        self.set_default_size(1100, 700)

        self._case_views: dict[str, CaseView] = {}
        self._status_timeout_id: int | None = None

        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label=f"{APP_NAME} — v{APP_VERSION} (Phase 3)"))
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_vexpand(True)

        self.sidebar = CaseSidebar(on_select=self.show_case, on_new=self.open_new_case_dialog)
        self.paned.set_start_child(self.sidebar)
        self.paned.set_resize_start_child(False)
        self.paned.set_shrink_start_child(False)

        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        welcome = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        welcome.set_valign(Gtk.Align.CENTER)
        welcome.set_halign(Gtk.Align.CENTER)
        welcome_label = Gtk.Label(label="Select a case on the left, or create a new one.")
        welcome_label.add_css_class("welcome-label")
        welcome.append(welcome_label)
        self.content_stack.add_named(welcome, "welcome")
        self.content_stack.set_visible_child_name("welcome")

        self.paned.set_end_child(self.content_stack)
        self.paned.set_resize_end_child(True)

        root.append(self.paned)

        self.status_bar = Gtk.Label(xalign=0)
        self.status_bar.set_margin_start(10)
        self.status_bar.set_margin_end(10)
        self.status_bar.set_margin_top(4)
        self.status_bar.set_margin_bottom(4)
        self.status_bar.set_visible(False)
        root.append(self.status_bar)

        self.set_child(root)

    # ── case navigation ──────────────────────────────────────────────────

    def show_case(self, case_id: str) -> None:
        if case_id not in self._case_views:
            view = CaseView(case_id, get_window=lambda: self, on_notify=self.notify)
            self._case_views[case_id] = view
            self.content_stack.add_named(view, case_id)
        else:
            self._case_views[case_id].refresh()
        self.content_stack.set_visible_child_name(case_id)
        self.sidebar.refresh(select_case_id=case_id)

    def open_new_case_dialog(self) -> None:
        NewCaseDialog(self, on_created=self._on_case_created).present()

    def _on_case_created(self, case_id: str) -> None:
        self.sidebar.refresh(select_case_id=case_id)
        self.show_case(case_id)
        self.notify(f"Case created: {case_id}", error=False)

    # ── status / notifications ──────────────────────────────────────────

    def notify(self, message: str, error: bool = False) -> None:
        self.status_bar.set_text(message)
        self.status_bar.remove_css_class("error-label")
        if error:
            self.status_bar.add_css_class("error-label")
        self.status_bar.set_visible(True)

        if self._status_timeout_id is not None:
            GLib.source_remove(self._status_timeout_id)
        self._status_timeout_id = GLib.timeout_add_seconds(
            _STATUS_CLEAR_SECONDS, self._clear_status
        )

    def _clear_status(self) -> bool:
        self.status_bar.set_visible(False)
        self._status_timeout_id = None
        return False
