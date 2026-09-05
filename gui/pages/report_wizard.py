"""
gui/pages/report_wizard.py — Phase 3.3: reporting flow, packing UI.

A two-step wizard: pick a reporting target, then view the generated
guide. Packaging (verify + PDF + zip) sits below both steps since it's
useful regardless of which guide you're looking at.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.case import load_case
from core.packager import package_case
from reporters import discord as rep_discord
from reporters import generic as rep_generic
from reporters import ncmec as rep_ncmec

from gui.dialogs import ConfirmDialog

_TARGETS = [
    ("discord", "Discord Trust & Safety"),
    ("ncmec", "NCMEC CyberTipline (minor involved)"),
    ("generic", "Generic platform report"),
]


class ReportWizardPage(Gtk.Box):
    """Step 1: choose a target. Step 2: view the guide. Package anytime."""

    def __init__(self, case_dir: Path, meta, get_window, on_notify) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.get_window = get_window
        self.on_notify = on_notify
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.minor_banner = Gtk.Label(xalign=0, wrap=True)
        self.minor_banner.add_css_class("minor-banner")
        self.minor_banner.set_visible(False)
        self.append(self.minor_banner)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.append(self.stack)

        self.stack.add_named(self._build_select_step(), "select")
        self.stack.add_named(self._build_guide_step(), "guide")
        self.stack.set_visible_child_name("select")

        # Packaging — always available, independent of wizard step
        pkg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pkg_btn = Gtk.Button(label="Package Case (verify + PDF + zip)")
        pkg_btn.add_css_class("suggested-action")
        pkg_btn.connect("clicked", lambda _b: self._package())
        pkg_box.append(pkg_btn)
        self.append(pkg_box)

        self.package_status = Gtk.Label(xalign=0, wrap=True)
        self.package_status.add_css_class("package-status")
        self.package_status.set_visible(False)
        self.append(self.package_status)

        self.set_case(case_dir, meta)

    def set_case(self, case_dir: Path, meta) -> None:
        self.case_dir = case_dir
        self.meta = meta
        if meta.minor_involved:
            self.minor_banner.set_text(
                "⚠  MINOR INVOLVED — submit to NCMEC FIRST, then the platform, "
                "then local police / FBI IC3 (ic3.gov)."
            )
            self.minor_banner.set_visible(True)
        else:
            self.minor_banner.set_visible(False)
        self.package_status.set_visible(False)
        self.stack.set_visible_child_name("select")

    # ── step 1: choose target ───────────────────────────────────────────

    def _build_select_step(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        title = Gtk.Label(label="Step 1 — Choose a reporting target", xalign=0)
        title.add_css_class("case-title")
        box.append(title)

        self.radio_buttons = {}
        leader = None
        for key, label in _TARGETS:
            btn = Gtk.CheckButton(label=label)
            if leader is None:
                leader = btn
                btn.set_active(True)
            else:
                btn.set_group(leader)
            self.radio_buttons[key] = btn
            box.append(btn)

        next_btn = Gtk.Button(label="Generate Guide →")
        next_btn.add_css_class("suggested-action")
        next_btn.connect("clicked", lambda _b: self._generate_selected())
        box.append(next_btn)
        return box

    def _generate_selected(self) -> None:
        target = next(key for key, btn in self.radio_buttons.items() if btn.get_active())
        if target == "ncmec" and not self.meta.minor_involved:
            ConfirmDialog(
                self.get_window(),
                "minor_involved is not set for this case. NCMEC is intended for "
                "cases involving minors. Generate the guide anyway?",
                on_result=lambda ok: self._generate(target) if ok else None,
                confirm_label="Generate anyway",
            ).present()
            return
        self._generate(target)

    # ── step 2: view guide ───────────────────────────────────────────────

    def _build_guide_step(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        back_btn = Gtk.Button(label="← Back")
        back_btn.connect("clicked", lambda _b: self.stack.set_visible_child_name("select"))
        box.append(back_btn)

        self.guide_title = Gtk.Label(xalign=0)
        self.guide_title.add_css_class("case-title")
        box.append(self.guide_title)

        self.guide_view = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD, cursor_visible=False)
        self.guide_view.add_css_class("guide-view")
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.guide_view)
        box.append(scroll)
        return box

    def _generate(self, target: str) -> None:
        _, meta = load_case(self.case_dir.name)
        self.meta = meta

        if target == "discord":
            guide = rep_discord.generate_guide(self.case_dir)
        elif target == "ncmec":
            guide = rep_ncmec.generate_guide(self.case_dir)
        else:
            guide = rep_generic.generate_guide(self.case_dir)

        self.guide_title.set_text(guide.title)

        lines = [f"Submit at: {guide.submit_url}", "", "Checklist"]
        for i, step in enumerate(guide.checklist, 1):
            lines.append(f"  {i}. {step}")
        lines += ["", "Template", guide.template]
        if guide.notes:
            lines += ["", "Notes", guide.notes]
        if guide.guide_path:
            lines += ["", f"(Guide written to: {guide.guide_path})"]

        self.guide_view.get_buffer().set_text("\n".join(lines))
        self.stack.set_visible_child_name("guide")

        if meta.minor_involved and target != "ncmec":
            self.on_notify("MINOR INVOLVED — also generate the NCMEC guide.", error=False)
        elif target == "ncmec":
            self.on_notify(
                "After NCMEC: report to the platform, then file with local police "
                "or FBI IC3 (ic3.gov). Keep your NCMEC tip number.",
                error=False,
            )

    # ── packaging ────────────────────────────────────────────────────────

    def _package(self) -> None:
        self.package_status.set_text("Packaging… verifying manifest, generating PDF, building zip.")
        self.package_status.set_visible(True)

        try:
            zip_path = package_case(self.case_dir)
        except Exception as e:  # noqa: BLE001 — surface any packaging failure to the user
            self.package_status.set_text(f"Packaging failed: {e}")
            self.on_notify("Packaging failed.", error=True)
            return

        lines = [f"Package ready: {zip_path.name}", f"Location: {zip_path}"]
        if self.meta.minor_involved:
            lines.append("MINOR INVOLVED — submit to NCMEC FIRST (cybertipline.org), then the platform, then local police.")
        else:
            lines.append("Next: generate a Discord or generic guide above and submit this zip.")
        self.package_status.set_text("\n".join(lines))
        self.on_notify("Package ready.", error=False)
