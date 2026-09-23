"""
gui_win/app.py — Tkinter GUI for AutoCatcher (Windows-friendly, also runs on Linux/macOS).

Shares the exact same core/ and reporters/ as the CLI, TUI and GTK4 GUI, so
cases created in any interface show up in all of them.

Entry points:
    AutoCatcher.exe              (windowed build, GUI only)
    python autocatcher_gui.py
    python main.py gui           (falls back here when GTK4 is unavailable)
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import APP_NAME, APP_VERSION, CASES_DIR
from core.archive import archive_url, list_archived
from core.case import (
    CaseMeta,
    append_note,
    create_case,
    get_note_entries,
    list_cases,
    load_case,
)
from core.evidence import add_evidence, count_evidence, list_evidence
from core.hasher import verify_manifest
from core.packager import package_case
from reporters import discord as rep_discord
from reporters import generic as rep_generic
from reporters import ncmec as rep_ncmec
from utils.platform import capture_screenshot, default_evidence_dir
from utils.timestamp import now_slug

RED = "#c0392b"


def open_path(path: Path | str) -> None:
    """Open a file/folder with the OS default handler."""
    p = str(path)
    try:
        if sys.platform == "win32":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as e:  # noqa: BLE001
        messagebox.showerror(APP_NAME, f"Could not open:\n{p}\n\n{e}")


# ── Dialogs ───────────────────────────────────────────────────────────────────


class NewCaseDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("New case")
        self.transient(parent)
        self.resizable(False, False)
        self.result: str | None = None  # new case_id

        self.subject = tk.StringVar()
        self.platform = tk.StringVar(value="discord")
        self.minor = tk.BooleanVar(value=False)

        f = ttk.Frame(self, padding=14)
        f.grid()
        ttk.Label(f, text="Subject username / handle").grid(row=0, column=0, sticky="w")
        e = ttk.Entry(f, textvariable=self.subject, width=38)
        e.grid(row=1, column=0, pady=(0, 8))
        ttk.Label(f, text="Platform").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            f,
            textvariable=self.platform,
            width=35,
            values=["discord", "twitter", "roblox", "instagram", "snapchat", "other"],
        ).grid(row=3, column=0, pady=(0, 8))
        ttk.Checkbutton(
            f, text="A minor is involved (enables NCMEC warnings)", variable=self.minor
        ).grid(row=4, column=0, sticky="w", pady=(0, 8))
        ttk.Label(f, text="Opening notes (optional)").grid(row=5, column=0, sticky="w")
        self.notes = tk.Text(f, width=38, height=4)
        self.notes.grid(row=6, column=0, pady=(0, 10))

        btns = ttk.Frame(f)
        btns.grid(row=7, column=0, sticky="e")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Create case", command=self._create).pack(side="right")

        e.focus_set()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()

    def _create(self) -> None:
        subject = self.subject.get().strip()
        platform = self.platform.get().strip()
        if not subject or not platform:
            messagebox.showwarning(APP_NAME, "Subject and platform are required.", parent=self)
            return
        try:
            case_dir = create_case(
                subject=subject,
                platform=platform,
                notes=self.notes.get("1.0", "end").strip(),
                minor_involved=self.minor.get(),
            )
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Could not create case:\n{e}", parent=self)
            return
        self.result = case_dir.name
        self.destroy()


class AddEvidenceDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, case_dir: Path) -> None:
        super().__init__(parent)
        self.title("Add evidence")
        self.transient(parent)
        self.resizable(False, False)
        self.case_dir = case_dir
        self.added = False

        self.path = tk.StringVar()
        self.kind = tk.StringVar(value="screenshot")
        self.desc = tk.StringVar()
        self.source = tk.StringVar()

        f = ttk.Frame(self, padding=14)
        f.grid()
        ttk.Label(f, text="File").grid(row=0, column=0, sticky="w")
        row = ttk.Frame(f)
        row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Entry(row, textvariable=self.path, width=42).pack(side="left")
        ttk.Button(row, text="Browse…", command=self._browse).pack(side="left", padx=(6, 0))
        ttk.Label(f, text="Type").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            f, textvariable=self.kind, values=["screenshot", "log", "file"],
            state="readonly", width=20,
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Label(f, text="What does this show?").grid(row=4, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.desc, width=52).grid(row=5, column=0, pady=(0, 8))
        ttk.Label(f, text='Source (e.g. "Discord #general", URL)').grid(row=6, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.source, width=52).grid(row=7, column=0, pady=(0, 10))

        btns = ttk.Frame(f)
        btns.grid(row=8, column=0, sticky="e")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Add", command=self._add).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()

    def _browse(self) -> None:
        p = filedialog.askopenfilename(
            parent=self, initialdir=str(default_evidence_dir()), title="Choose evidence file"
        )
        if p:
            self.path.set(p)
            suffix = Path(p).suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
                self.kind.set("screenshot")
            elif suffix in (".txt", ".log", ".json", ".html", ".csv"):
                self.kind.set("log")
            else:
                self.kind.set("file")

    def _add(self) -> None:
        src = Path(self.path.get().strip().strip('"'))
        if not src.is_file():
            messagebox.showwarning(APP_NAME, "Choose an existing file.", parent=self)
            return
        try:
            add_evidence(self.case_dir, src, self.kind.get(), self.desc.get(), self.source.get())  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NAME, str(e), parent=self)
            return
        self.added = True
        self.destroy()


# ── Case detail pages ─────────────────────────────────────────────────────────


class CaseView(ttk.Frame):
    """Right-hand side: tabs for one case."""

    def __init__(self, parent: tk.Misc, app: "AutoCatcherTk") -> None:
        super().__init__(parent)
        self.app = app
        self.case_dir: Path | None = None
        self.meta: CaseMeta | None = None

        self.banner = tk.Label(
            self, text="", bg=RED, fg="white", anchor="w", padx=10, pady=4,
            font=("TkDefaultFont", 10, "bold"),
        )
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        # Background jobs report back through a queue that the Tk main thread
        # polls — Tk isn't thread-safe, so workers must never touch widgets.
        self._jobs: queue.Queue = queue.Queue()
        self.after(100, self._poll_jobs)

        self.t_overview = ttk.Frame(self.tabs, padding=10)
        self.t_evidence = ttk.Frame(self.tabs, padding=10)
        self.t_archive = ttk.Frame(self.tabs, padding=10)
        self.t_report = ttk.Frame(self.tabs, padding=10)
        for frame, name in (
            (self.t_overview, "Overview"),
            (self.t_evidence, "Evidence"),
            (self.t_archive, "Archive"),
            (self.t_report, "Report && Package"),
        ):
            self.tabs.add(frame, text=name.replace("&&", "&"))

        self._build_overview()
        self._build_evidence()
        self._build_archive()
        self._build_report()

    # -- builders ----------------------------------------------------------

    def _build_overview(self) -> None:
        f = self.t_overview
        self.info = tk.Text(f, height=9, wrap="word", relief="flat", state="disabled",
                            background=self.app.cget("background"))
        self.info.pack(fill="x")
        ttk.Label(f, text="Notes", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.notes_box = tk.Text(f, height=10, wrap="word", state="disabled")
        self.notes_box.pack(fill="both", expand=True)
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(8, 0))
        self.note_var = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.note_var)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Return>", lambda _e: self._add_note())
        ttk.Button(row, text="Add note", command=self._add_note).pack(side="left", padx=(6, 0))

    def _build_evidence(self) -> None:
        f = self.t_evidence
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Add file…", command=self._add_evidence).pack(side="left")
        ttk.Button(bar, text="Capture screenshot", command=self._capture).pack(side="left", padx=6)
        ttk.Button(bar, text="Verify integrity", command=self._verify).pack(side="left")
        ttk.Button(bar, text="Open selected", command=self._open_selected).pack(side="right")

        cols = ("type", "filename", "description", "sha256", "added")
        self.ev_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse")
        for c, w in zip(cols, (80, 210, 240, 120, 140)):
            self.ev_tree.heading(c, text=c.capitalize() if c != "sha256" else "SHA256")
            self.ev_tree.column(c, width=w, minwidth=60, anchor="w", stretch=(c == "description"))
        self.ev_tree.pack(fill="both", expand=True)
        self.ev_tree.bind("<Double-1>", lambda _e: self._open_selected())
        self._ev_paths: dict[str, Path] = {}

    def _build_archive(self) -> None:
        f = self.t_archive
        ttk.Label(
            f, text="Submit a URL to the Wayback Machine before it can be deleted."
        ).pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=8)
        self.url_var = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.url_var)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Return>", lambda _e: self._archive())
        self.arch_btn = ttk.Button(row, text="Archive URL", command=self._archive)
        self.arch_btn.pack(side="left", padx=(6, 0))
        self.arch_list = tk.Text(f, wrap="none", state="disabled")
        self.arch_list.pack(fill="both", expand=True)

    def _build_report(self) -> None:
        f = self.t_report
        ttk.Label(f, text="Reporting guides", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(4, 10))
        ttk.Button(row, text="Discord T&S guide", command=lambda: self._guide("discord")).pack(side="left")
        ttk.Button(row, text="NCMEC guide", command=lambda: self._guide("ncmec")).pack(side="left", padx=6)
        ttk.Button(row, text="Generic guide", command=lambda: self._guide("generic")).pack(side="left")

        ttk.Label(f, text="Submission package", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        row2 = ttk.Frame(f)
        row2.pack(fill="x", pady=(4, 10))
        self.pkg_btn = ttk.Button(row2, text="Verify + build PDF + zip", command=self._package)
        self.pkg_btn.pack(side="left")
        ttk.Button(row2, text="Open case folder", command=lambda: self.case_dir and open_path(self.case_dir)).pack(side="left", padx=6)
        ttk.Button(row2, text="Open packages folder", command=self._open_packages).pack(side="left")

        self.log = tk.Text(f, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)

    def _run_bg(self, fn, done) -> None:  # noqa: ANN001
        """Run fn() in a thread; call done(result, error) on the Tk thread."""

        def work() -> None:
            try:
                self._jobs.put((done, fn(), None))
            except Exception as exc:  # noqa: BLE001
                self._jobs.put((done, None, exc))

        threading.Thread(target=work, daemon=True).start()

    def _poll_jobs(self) -> None:
        try:
            while True:
                done, result, err = self._jobs.get_nowait()
                done(result, err)
        except queue.Empty:
            pass
        self.after(100, self._poll_jobs)

    # -- data --------------------------------------------------------------

    def show_case(self, case_id: str) -> None:
        self.case_dir, self.meta = load_case(case_id)
        self.refresh()

    def refresh(self) -> None:
        if not self.case_dir:
            return
        _, self.meta = load_case(self.case_dir.name)
        m = self.meta

        if m.minor_involved:
            self.banner.config(text="⚠  MINOR INVOLVED — report to NCMEC (cybertipline.org) FIRST")
            self.banner.pack(fill="x", before=self.tabs)
        else:
            self.banner.pack_forget()

        counts = count_evidence(self.case_dir)
        info = (
            f"Case ID:      {m.case_id}\n"
            f"Subject:      {m.subject}\n"
            f"Platform:     {m.platform}\n"
            f"Created UTC:  {m.created_at}\n"
            f"Minor:        {'YES' if m.minor_involved else 'no'}\n"
            f"Evidence:     {counts.get('screenshot', 0)} screenshots, "
            f"{counts.get('log', 0)} logs, {counts.get('file', 0)} files\n"
            f"Folder:       {self.case_dir}"
        )
        self._set_text(self.info, info)

        notes = "\n\n".join(f"[{n.created_at}]\n{n.text}" for n in get_note_entries(m)) or "(no notes yet)"
        self._set_text(self.notes_box, notes)

        self.ev_tree.delete(*self.ev_tree.get_children())
        self._ev_paths.clear()
        for rec in list_evidence(self.case_dir):
            sub = {"screenshot": "screenshots", "log": "logs", "file": "files"}[rec.type]
            iid = self.ev_tree.insert(
                "", "end",
                values=(rec.type, rec.filename, rec.description or "—", rec.sha256[:16] + "…", rec.added_at),
            )
            self._ev_paths[iid] = self.case_dir / sub / rec.filename

        arch = list_archived(self.case_dir)
        self._set_text(self.arch_list, "\n".join(arch) if arch else "(nothing archived yet)")

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _log(self, line: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # -- actions -----------------------------------------------------------

    def _add_note(self) -> None:
        text = self.note_var.get().strip()
        if not text or not self.case_dir:
            return
        append_note(self.case_dir, text)
        self.note_var.set("")
        self.refresh()

    def _add_evidence(self) -> None:
        if not self.case_dir:
            return
        dlg = AddEvidenceDialog(self, self.case_dir)
        self.wait_window(dlg)
        if dlg.added:
            self.refresh()
            self.tabs.select(self.t_evidence)

    def _capture(self) -> None:
        if not self.case_dir:
            return
        root = self.winfo_toplevel()
        root.withdraw()  # don't screenshot ourselves
        root.after(400, self._capture_now)

    def _capture_now(self) -> None:
        root = self.winfo_toplevel()
        tmp = self.case_dir / f"_capture_{now_slug()}.png"  # type: ignore[operator]
        try:
            result = capture_screenshot(tmp)
        finally:
            root.deiconify()
        if not result.ok:
            messagebox.showerror(APP_NAME, f"Screenshot failed:\n{result.error}")
            return
        try:
            add_evidence(self.case_dir, result.path, "screenshot", "Screen capture", "AutoCatcher")  # type: ignore[arg-type]
        finally:
            result.path.unlink(missing_ok=True)
        self.refresh()

    def _verify(self) -> None:
        if not self.case_dir:
            return
        r = verify_manifest(self.case_dir)
        ok, bad, miss = len(r["ok"]), len(r["failed"]), len(r["missing"])
        if ok + bad + miss == 0:
            messagebox.showinfo(APP_NAME, "Manifest is empty — nothing hashed yet.")
        elif not bad and not miss:
            messagebox.showinfo(APP_NAME, f"All {ok} file(s) verified — hashes match.\nEvidence is intact.")
        else:
            detail = "\n".join([f"MISMATCH: {p}" for p in r["failed"]] + [f"MISSING: {p}" for p in r["missing"]])
            messagebox.showerror(APP_NAME, f"Integrity issues: {ok} OK, {bad} failed, {miss} missing.\n\n{detail}")

    def _open_selected(self) -> None:
        sel = self.ev_tree.selection()
        if sel and sel[0] in self._ev_paths:
            open_path(self._ev_paths[sel[0]])

    def _archive(self) -> None:
        url = self.url_var.get().strip()
        if not url or not self.case_dir:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.arch_btn.config(state="disabled", text="Archiving…")
        case_dir = self.case_dir
        self._run_bg(lambda: archive_url(case_dir, url), self._archive_done)

    def _archive_done(self, res, err) -> None:  # noqa: ANN001
        self.arch_btn.config(state="normal", text="Archive URL")
        if err is None and res is not None and res.status in ("saved", "exists"):
            self.url_var.set("")
        else:
            why = err if err is not None else (res.status if res else "unknown")
            messagebox.showwarning(APP_NAME, f"Archiving failed ({why}). The attempt was recorded.")
        self.refresh()

    def _guide(self, which: str) -> None:
        if not self.case_dir:
            return
        mod = {"discord": rep_discord, "ncmec": rep_ncmec, "generic": rep_generic}[which]
        if which == "ncmec" and self.meta and not self.meta.minor_involved:
            if not messagebox.askyesno(APP_NAME, "This case isn't flagged as involving a minor.\nGenerate the NCMEC guide anyway?"):
                return
        try:
            g = mod.generate_guide(self.case_dir)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NAME, str(e))
            return
        self._log(f"✓ {which} guide written: {g.guide_path.name}")
        if g.submit_url and not str(g.submit_url).startswith("["):
            self._log(f"  Submit at: {g.submit_url}")
        open_path(g.guide_path)

    def _package(self) -> None:
        if not self.case_dir:
            return
        self.pkg_btn.config(state="disabled")
        self._log("Verifying integrity, generating PDF, building zip…")
        case_dir = self.case_dir
        self._run_bg(lambda: package_case(case_dir), self._package_done)

    def _package_done(self, zp: Path | None, err: Exception | None) -> None:
        self.pkg_btn.config(state="normal")
        if err is not None:
            self._log(f"✗ Packaging failed: {err}")
            return
        self._log(f"✓ Package ready: {zp}")
        open_path(zp.parent)  # type: ignore[union-attr]
        self.refresh()

    def _open_packages(self) -> None:
        from config import PACKAGES_DIR

        PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
        open_path(PACKAGES_DIR)


# ── Main window ───────────────────────────────────────────────────────────────


class AutoCatcherTk(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1100x680")
        self.minsize(900, 560)
        try:
            ttk.Style(self).theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            pass

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        side = ttk.Frame(paned, padding=8)
        paned.add(side, weight=0)
        ttk.Label(side, text="Cases", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        ttk.Button(side, text="+  New case", command=self._new_case).pack(fill="x", pady=(6, 6))
        self.case_list = tk.Listbox(side, width=34, activestyle="none", exportselection=False)
        self.case_list.pack(fill="both", expand=True)
        self.case_list.bind("<<ListboxSelect>>", self._on_select)
        ttk.Button(side, text="Open cases folder", command=lambda: (CASES_DIR.mkdir(parents=True, exist_ok=True), open_path(CASES_DIR))).pack(fill="x", pady=(6, 0))

        self.view = CaseView(paned, self)
        self.placeholder = ttk.Label(
            paned, text="Select a case on the left,\nor create a new one.", anchor="center", justify="center"
        )
        paned.add(self.placeholder, weight=1)
        self._paned = paned
        self._showing_view = False
        self._case_ids: list[str] = []

        self.reload_cases()

    def reload_cases(self, select: str | None = None) -> None:
        cases = list_cases()
        self._case_ids = [c.case_id for c in cases]
        self.case_list.delete(0, "end")
        for c in cases:
            self.case_list.insert("end", ("⚠ " if c.minor_involved else "") + c.case_id)
        if select and select in self._case_ids:
            i = self._case_ids.index(select)
            self.case_list.selection_set(i)
            self._open_case(select)

    def _new_case(self) -> None:
        dlg = NewCaseDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.reload_cases(select=dlg.result)

    def _on_select(self, _e=None) -> None:  # noqa: ANN001
        sel = self.case_list.curselection()
        if sel:
            self._open_case(self._case_ids[sel[0]])

    def _open_case(self, case_id: str) -> None:
        if not self._showing_view:
            self._paned.forget(self.placeholder)
            self._paned.add(self.view, weight=1)
            self._showing_view = True
        self.view.show_case(case_id)


def run(note=None) -> int:  # noqa: ANN001
    """Start the GUI. `note` (optional) receives selftest breadcrumbs / crash traces."""
    say = note or (lambda _m: None)
    selftest = bool(os.environ.get("AUTOCATCHER_SELFTEST"))
    # A windowed (console=False) exe has no stdout/stderr; anything that
    # writes to them (logging, rich) must not explode.
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        win = AutoCatcherTk()
        say("[selftest] window created")
        if selftest:  # CI: build the window, then exit
            win.update()
            win.destroy()
            say("[selftest] OK")
            return 0
        win.mainloop()
    except Exception:  # noqa: BLE001
        import traceback

        tb = traceback.format_exc()
        say("CRASH\n" + tb)
        if not selftest:  # never pop a dialog in CI
            try:
                messagebox.showerror(APP_NAME, f"AutoCatcher crashed:\n\n{tb[-1500:]}")
            except Exception:  # noqa: BLE001
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
