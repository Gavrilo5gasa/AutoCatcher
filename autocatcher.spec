# autocatcher.spec — Phase 4.2: Windows packaging via PyInstaller.
#
# Build with:   pyinstaller autocatcher.spec
#
# Produces TWO single-file executables in dist/:
#
#   AutoCatcher.exe      — GUI ONLY (Tkinter, gui_win/). Windowed: double-click
#                          opens the app, no console window, no CLI.
#   autocatcher-cli.exe  — CLI + TUI (console). Run from a terminal; bare
#                          double-click opens the TUI. `autocatcher-cli gui`
#                          also launches the Tk GUI.
#
# The names MUST differ by more than letter case: Windows filenames are
# case-insensitive, so "AutoCatcher.exe" and "autocatcher.exe" are the same
# file and the second build silently overwrites the first.
#
# The GTK4 GUI (gui/) is Linux-only and is never bundled on Windows.

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

REPORTLAB = [
    "reportlab.graphics.barcode",
    "reportlab.lib.colors",
    "reportlab.lib.pagesizes",
    "reportlab.pdfgen.canvas",
]

# ── GUI-only build ────────────────────────────────────────────────────────────

gui_a = Analysis(
    ["autocatcher_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=REPORTLAB + ["PIL.ImageGrab", "tkinter", "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox"],
    hookspath=[],
    excludes=["gi", "gui", "tui", "textual", "typer"],  # note: "gui" != "gui_win"
    cipher=block_cipher,
    noarchive=False,
)
gui_pyz = PYZ(gui_a.pure, gui_a.zipped_data, cipher=block_cipher)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    gui_a.binaries,
    gui_a.zipfiles,
    gui_a.datas,
    [],
    name="AutoCatcher",
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # windowed: no terminal flashes up
    disable_windowed_traceback=False,
)

# ── CLI + TUI build ───────────────────────────────────────────────────────────

cli_a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Textual resolves CSS_PATH relative to the module file at runtime.
        ("tui/app.tcss", "tui"),
    ],
    hiddenimports=REPORTLAB + [
        "textual.widgets",
        "textual.screen",
        "textual.containers",
        "PIL.ImageGrab",
        "gui_win.app",  # lazy-imported by `autocatcher gui`
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    excludes=["gi", "gui"],
    cipher=block_cipher,
    noarchive=False,
)
cli_pyz = PYZ(cli_a.pure, cli_a.zipped_data, cipher=block_cipher)
cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    cli_a.binaries,
    cli_a.zipfiles,
    cli_a.datas,
    [],
    name="autocatcher-cli",
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,  # CLI + TUI need a console
    disable_windowed_traceback=False,
)
