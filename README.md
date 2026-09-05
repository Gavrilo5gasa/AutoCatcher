# ⚠️ THIS PROJECT WAS PARTLY MADE WITH AI ⚠️
> The reason behind this is because I realised that it's
> better to put Safety over my lazyness to code,
> and that't why it's partly AI-Made but no worries
> I will rewrite the entire project to be fully human made (when I have time).
> For now look at this project as "Alpha" version

# AutoCatcher

Evidence collection and reporting toolkit for documenting online predator
activity — built for people (parents, moderators, victims, or anyone doing
digilante-style investigative work) who need to capture, hash, archive, and
package evidence in a way that holds up when it's handed to a platform's
Trust & Safety team, NCMEC, or local police.

Available as a CLI, a TUI, and (on Linux) a GTK4 desktop GUI, sharing the
same case data on disk. A standalone Windows `.exe` (CLI + TUI) is also
available — see [Windows build](#windows-build) below.

> **Not legal advice.** AutoCatcher helps you collect and preserve evidence
> in a consistent, tamper-evident way. It does not replace contacting law
> enforcement or NCMEC directly, and it does not guarantee any particular
> legal outcome.

## Why

Evidence gathered ad hoc — random screenshots, no timestamps, no hashes, no
chain of custody — is easy for a platform or investigator to dismiss.
AutoCatcher enforces a few simple rules on every case:

- **Append-only.** Nothing is ever deleted or mutated once added to a case.
- **Hash on intake.** Every file gets a SHA256 the moment it's added, so
  tampering (accidental or otherwise) is detectable later with `verify`.
- **UTC everywhere.** Timestamps are consistent regardless of where you or
  the reader are.
- **Self-contained cases.** Each case is a plain folder on disk — readable
  and usable even without the app.
- **Guided reporting.** Built-in guides for Discord, NCMEC, and generic
  platform reports, so you know exactly where evidence needs to go and in
  what order.

## Features

- Case management — create, list, inspect, and annotate cases
- Evidence intake — add screenshots, logs, or arbitrary files, each tagged
  with a description and source
- One-command screen capture — grabs a screenshot and adds it as evidence
  in a single step, using the right native tool for your OS
- SHA256 manifest + integrity verification (`verify`) to detect tampering
- Wayback Machine archiving for URLs tied to a case, before they can be
  deleted
- One-command packaging — verifies integrity, generates a PDF report, and
  zips everything into a submission-ready package
- Reporting guides for Discord Trust & Safety, NCMEC CyberTipline, and
  generic platforms, with automatic warnings when a case involves a minor
- CLI, TUI (Textual), and (Linux) GTK4 GUI — same case data, multiple
  interfaces

## Installation (from source)

Requires Python 3.10+.

```bash
git clone git@github.com:Gavrilo5gasa/AutoCatcher.git
cd AutoCatcher
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The GUI needs GTK4 + PyGObject, which are **system packages**, not pip
installable, and are **Linux-only** in this project (see
[Windows build](#windows-build)):

```bash
# Debian/Ubuntu
sudo apt install python3-gi gir1.2-gtk-4.0

# Arch
sudo pacman -S python-gobject gtk4
```

The CLI and TUI work without GTK, on any OS.

### Screenshot capture dependencies

`evidence screenshot` uses whatever's native to your OS:

| OS      | Tool(s) used                                | Extra install                       |
|---------|------------------------------------------------|-----------------------------------------|
| Linux   | `grim` (Wayland) → `scrot` → `import` (X11)   | `sudo apt install grim` or `scrot`     |
| macOS   | `screencapture` (built in)                    | None                                     |
| Windows | `PIL.ImageGrab` (Pillow)                      | Included automatically via `requirements.txt` |

If none of these are available, the command fails with a clear message
instead of crashing — screenshot capture is a convenience, not a
requirement (`evidence add` always works with any file you already have).

### Global command (Linux/macOS)

To run `autocatcher` from anywhere:

```bash
sudo cp autocatcher /usr/local/bin/autocatcher
sudo chmod +x /usr/local/bin/autocatcher
```

The wrapper script always calls the project's own `.venv/bin/python`, so
dependencies resolve correctly regardless of your shell's active
environment. **Don't run `autocatcher` with `sudo`** — it doesn't need root,
and `sudo` will bypass the venv and break imports.

## Windows build

Phase 4.2 ships AutoCatcher as a **standalone `.exe`** via PyInstaller — no
Python install required on the machine running it.

**What's included:** CLI + TUI, full feature set (cases, evidence, screenshot
capture via Pillow, archiving, hashing, PDF packaging, reporting guides).

**What's not included:** the GTK4 GUI. PyGObject on Windows needs a separate
MSYS2/GTK runtime that isn't practical to bundle into a single `.exe`.
Running `autocatcher gui` on the Windows build shows the same "GTK4 not
available" message you'd get on a Linux machine without GTK installed —
that's intentional, not a bug. macOS support is a separate, not-yet-started
phase (see [PLAN_TREE.md](PLAN_TREE.md)).

### Building it yourself

On a Windows machine, inside the project's venv:

```powershell
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller autocatcher.spec
```

The result is `dist\autocatcher.exe`. Copy it anywhere and run it directly:

```powershell
.\autocatcher.exe case new --subject "someuser#1234" --platform discord
.\autocatcher.exe tui
```

Cases and packaged zips are written next to the `.exe` itself (`cases\` and
`packages\` folders created alongside it) — not to a temp folder, and not
wherever you happened to launch it from.

## Usage

```bash
# Create a case
autocatcher case new --subject "someuser#1234" --platform discord

# Add evidence
autocatcher evidence add <case-id> screenshot.png --type screenshot --desc "Initial DM"
autocatcher evidence add <case-id> chatlog.txt --type log

# Or capture a screenshot directly instead of adding an existing file
autocatcher evidence screenshot <case-id> --desc "Profile before it got deleted"

# Archive a URL (e.g. their profile) before it disappears
autocatcher archive <case-id> https://example.com/user/someuser

# Check case details
autocatcher case show <case-id>
autocatcher case note <case-id> --text "Subject changed username to X"

# Verify nothing has been tampered with
autocatcher verify <case-id>

# Package everything (hash-verify + PDF report + zip)
autocatcher package <case-id>

# Get reporting guidance
autocatcher report discord <case-id>
autocatcher report ncmec <case-id>
autocatcher report generic <case-id>

# Or launch an interface instead of using individual commands
autocatcher tui
autocatcher gui   # Linux only
```

(On Windows, replace `autocatcher` with `.\autocatcher.exe`.)

Cases live in `cases/` next to the app (or wherever `AUTOCATCHER_CASES_DIR`
points), one folder per case:

```
cases/2026-05-20_someuser/
├── screenshots/
├── logs/
├── files/
├── archived/
├── hashes.sha256
├── archived_links.txt
├── case_meta.json
└── summary.txt
```

If a case involves a minor, flag it at creation with `--minor` — AutoCatcher
will surface NCMEC reminders throughout the case lifecycle, since a
CyberTipline report is legally mandated in that situation.

## Project structure

```
autocatcher/
├── main.py                # Typer CLI entry point
├── config.py                # Paths, settings, constants (frozen-exe aware)
├── autocatcher.spec          # PyInstaller build spec (Windows)
├── requirements-build.txt     # Build-only deps (pyinstaller)
├── core/
│   ├── case.py                  # Case creation, loading, folder structure
│   ├── evidence.py                # Evidence intake
│   ├── archive.py                   # Wayback Machine archiving
│   ├── hasher.py                      # SHA256 manifest + verification
│   └── packager.py                     # PDF report + zip packaging
├── reporters/
│   ├── discord.py                        # Discord Trust & Safety guide
│   ├── ncmec.py                            # NCMEC CyberTipline guide
│   └── generic.py                            # Generic platform guide
├── utils/
│   ├── platform.py                            # OS abstraction: screenshots, paths
│   ├── timestamp.py                             # UTC timestamps
│   └── logger.py                                  # Internal app logging
├── tui/                  # Textual terminal UI
└── gui/                   # GTK4 desktop UI (Linux only)
```

All OS-specific behavior (screenshot tools, default folder paths) lives in
`utils/platform.py`. Nothing else in the codebase branches on `sys.platform`
or shells out to an OS-specific binary directly — that's what makes adding
a platform a matter of extending one file, not hunting through the whole
codebase.

## Tech stack

| Layer       | Choice                                        | Why                                    |
|-------------|--------------------------------------------------|-------------------------------------------|
| Language    | Python                                            | Smooth CLI → TUI → GUI path                |
| CLI         | Typer                                             | Typed, clean, auto help                    |
| TUI         | Textual                                           | Modern, cross-terminal                     |
| GUI         | GTK4 (PyGObject)                                  | Native Wayland, no XWayland (Linux only)  |
| Packaging   | PyInstaller (Windows)                            | Single .exe, no Python required            |
| Hashing     | hashlib (built-in)                                | No deps, SHA256                            |
| Archiving   | Wayback Machine API                               | Free, reliable                             |
| Screenshots | grim/scrot/import (Linux), screencapture (macOS), Pillow (Windows) | One native path per OS |
| Reports     | zipfile + reportlab                               | Clean PDF + zip output                     |

## Design rules

1. **OS-specific calls always go through `utils/platform.py`** — never call
   `grim`, `screencapture`, etc. directly from core/gui/tui logic.
2. **Cases are self-contained folders** — if the app breaks, evidence is
   still human-readable on disk.
3. **Nothing is ever deleted or mutated** — append only. Evidence integrity
   is everything.
4. **Timestamps are always UTC** — legal validity across timezones.
5. **Hash everything on intake** — SHA256 manifest generated the moment a
   file is added.
6. **Frozen-build paths never depend on a temp directory.** Anything the
   app writes (cases, packages) must resolve relative to a stable location
   (`sys.executable`'s directory when frozen), never `__file__` or
   `sys._MEIPASS`, both of which point inside a directory that gets deleted
   when a packaged executable exits.

## Reporting targets

| Platform     | Method                                | Notes                            |
|--------------|-------------------------------------------|---------------------------------------|
| Discord      | dis.gd/report + Trust & Safety form      | Include case ID + zip                 |
| NCMEC        | CyberTipline (cybertip.org)               | Required if a minor is involved      |
| Twitter/X    | In-app report + Trust & Safety           | Archive profile first                 |
| Local police | Cybercrime unit                           | Use packaged zip as evidence          |
| Generic      | Platform report + evidence package        | Fallback for any platform             |

## Status

| Phase                      | Status         |
|-----------------------------|-----------------|
| 1 — CLI                     | ✅ Done         |
| 2 — TUI                     | ✅ Done         |
| 3 — GUI (GTK4, Linux)       | ✅ Done         |
| 4.1 — OS abstraction layer  | ✅ Done         |
| 4.2 — Windows packaging     | ✅ Done         |
| 4.3 — macOS port            | 🔲 Not planned yet |
| 5 — Optional integrations   | 🔲 Todo        |

## License

MIT — see [LICENSE](LICENSE).
