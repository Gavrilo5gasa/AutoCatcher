# autocatcher.spec — Phase 4.2: Windows packaging via PyInstaller.
#
# Build with:
#   pyinstaller autocatcher.spec
#
# Output: dist/autocatcher.exe — a single-file executable. No Python
# install, no venv, no requirements.txt needed on the target machine.
#
# NOTE: This targets the CLI + TUI only. The GTK4 GUI (gui/) is not bundled
# — PyGObject on Windows requires a separate MSYS2/GTK runtime that isn't
# practical to bundle into a onefile exe. `autocatcher gui` on this build
# will fail with the same "GTK4/PyGObject not available" message it already
# shows on Linux machines missing GTK — that's intentional, not a bug.
# macOS is out of scope for this phase (see PLAN_TREE.md Phase 4.3).

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Textual resolves App.CSS_PATH relative to the module file at
        # runtime. Under a onefile build that file lives inside the temp
        # extraction dir, so app.tcss must be bundled alongside it or the
        # TUI will crash on startup looking for a stylesheet that isn't
        # there.
        ("tui/app.tcss", "tui"),
    ],
    hiddenimports=[
        # reportlab and textual both do some dynamic/lazy importing that
        # PyInstaller's static analysis doesn't always catch on its own.
        "reportlab.graphics.barcode",
        "reportlab.lib.colors",
        "reportlab.lib.pagesizes",
        "reportlab.pdfgen.canvas",
        "textual.widgets",
        "textual.screen",
        "textual.containers",
        "PIL.ImageGrab",  # Windows screenshot capture — see utils/platform.py
    ],
    hookspath=[],
    excludes=[
        # gi/GTK is optional and Windows-incompatible in this build; don't
        # let PyInstaller try (and fail) to pull it in.
        "gi",
        "gui",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="autocatcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI + TUI both need a console; this is not a windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
