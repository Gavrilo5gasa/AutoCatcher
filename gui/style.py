"""
gui/style.py — Shared CSS for the whole GTK4 app.

Kept in one place so Phase 3's screens stay visually consistent, same
approach as tui/app.tcss for Phase 2.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

CSS = """
.sidebar {
    background-color: alpha(@window_fg_color, 0.03);
}

.case-row {
    padding: 8px;
}

.case-row-subject {
    font-weight: bold;
}

.case-row-meta {
    opacity: 0.65;
    font-size: 90%;
}

.minor-badge {
    color: white;
    background-color: #e01b24;
    border-radius: 6px;
    padding: 1px 6px;
    font-weight: bold;
    font-size: 85%;
}

.minor-banner {
    background-color: alpha(#e01b24, 0.15);
    border: 1px solid #e01b24;
    border-radius: 6px;
    padding: 10px;
    color: #e01b24;
    font-weight: bold;
}

.case-header {
    padding: 10px 4px;
}

.case-title {
    font-size: 130%;
    font-weight: bold;
}

.evidence-card {
    border: 1px solid alpha(@window_fg_color, 0.15);
    border-radius: 8px;
    padding: 10px;
    min-width: 200px;
}

.evidence-card-type {
    font-weight: bold;
    font-size: 90%;
}

.evidence-card-desc {
    opacity: 0.8;
}

.timeline-row {
    padding: 6px 4px;
    border-bottom: 1px solid alpha(@window_fg_color, 0.08);
}

.timeline-kind {
    font-weight: bold;
    min-width: 90px;
}

.error-label {
    color: #e01b24;
}

.guide-view {
    font-family: monospace;
}

.package-status {
    padding: 10px;
    border: 1px solid alpha(#2ec27e, 0.5);
    background-color: alpha(#2ec27e, 0.1);
    border-radius: 6px;
}

.welcome-label {
    opacity: 0.6;
    font-size: 120%;
}
"""


def apply_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
