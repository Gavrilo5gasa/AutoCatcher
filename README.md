# AutoCatcher

Evidence collection and reporting toolkit for documenting online predator
activity — built for people (parents, moderators, victims, or anyone doing
digilante-style investigative work) who need to capture, hash, archive, and
package evidence in a way that holds up when it's handed to a platform's
Trust & Safety team, NCMEC, or local police.

Available as a CLI, a TUI, and a GTK4 desktop GUI, sharing the same case
data on disk.

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
- CLI, TUI (Textual), and GTK4 GUI — same case data, three interfaces

## Installation

Requires Python 3.10+.

```bash
git clone git@github.com:Gavrilo5gasa/AutoCatcher.git
cd AutoCatcher
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The GUI needs GTK4 + PyGObject, which are **system packages**, not pip
installable:

```bash
# Debian/Ubuntu
sudo apt install python3-gi gir1.2-gtk-4.0

# Arch
sudo pacman -S python-gobject gtk4
```

The CLI and TUI work without GTK.

### Screenshot capture dependencies

`evidence screenshot` uses whatever's native to your OS:

| OS      | Tool(s) used                                  | Extra install                          |
|---------|------------------------------------------------|-----------------------------------------|
| Linux   | `grim` (Wayland) → `scrot` → `import` (X11)     | `sudo apt install grim` or `scrot`     |
| macOS   | `screencapture` (built in)                      | None                                    |
| Windows | `PIL.ImageGrab` (Pillow)                        | `pip install Pillow`                    |

If none of these are available, the command fails with a clear message
instead of crashing — screenshot capture is a convenience, not a
requirement (`evidence add` always works with any file you already have).

### Global command

To run `autocatcher` from anywhere:

```bash
sudo cp autocatcher /usr/local/bin/autocatcher
sudo chmod +x /usr/local/bin/autocatcher
```

The wrapper script always calls the project's own `.venv/bin/python`, so
dependencies resolve correctly regardless of your shell's active
environment. **Don't run `autocatcher` with `sudo`** — it doesn't need root,
and `sudo` will bypass the venv and break imports.

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
autocatcher gui
```

Cases live in `cases/` inside the project (or wherever `AUTOCATCHER_CASES_DIR`
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
├── main.py            # Typer CLI entry point
├── config.py           # Paths, settings, constants
├── core/
│   ├── case.py           # Case creation, loading, folder structure
│   ├── evidence.py        # Evidence intake
│   ├── archive.py          # Wayback Machine archiving
│   ├── hasher.py            # SHA256 manifest + verification
│   └── packager.py           # PDF report + zip packaging
├── reporters/
│   ├── discord.py             # Discord Trust & Safety reporting guide
│   ├── ncmec.py                 # NCMEC CyberTipline reporting guide
│   └── generic.py                # Generic platform reporting guide
├── utils/
│   ├── platform.py                # OS abstraction: screenshots, paths
│   ├── timestamp.py                # UTC timestamps
│   └── logger.py                    # Internal app logging
├── tui/                # Textual terminal UI
└── gui/                 # GTK4 desktop UI
```

All OS-specific behavior (screenshot tools, default folder paths) lives in
`utils/platform.py`. Nothing else in the codebase branches on `sys.platform`
or shells out to an OS-specific binary directly — that's what makes adding
a new platform a matter of extending one file.

## Tech stack

| Layer       | Choice                                       | Why                                  |
|-------------|-----------------------------------------------|----------------------------------------|
| Language    | Python                                        | Smooth CLI → TUI → GUI path            |
| CLI         | Typer                                         | Typed, clean, auto help                |
| TUI         | Textual                                       | Modern, cross-terminal                 |
| GUI         | GTK4 (PyGObject)                              | Native Wayland, no XWayland            |
| Hashing     | hashlib (built-in)                            | No deps, SHA256                        |
| Archiving   | Wayback Machine API                           | Free, reliable                         |
| Screenshots | grim/scrot/import (Linux), screencapture (macOS), Pillow (Windows) | One native path per OS |
| Packaging   | zipfile + reportlab                           | Clean report output                    |

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

## Reporting targets

| Platform     | Method                              | Notes                          |
|--------------|---------------------------------------|-----------------------------------|
| Discord      | dis.gd/report + Trust & Safety form  | Include case ID + zip             |
| NCMEC        | CyberTipline (cybertip.org)           | Required if a minor is involved  |
| Twitter/X    | In-app report + Trust & Safety       | Archive profile first             |
| Local police | Cybercrime unit                       | Use packaged zip as evidence      |
| Generic      | Platform report + evidence package    | Fallback for any platform         |

## Status

| Phase                      | Status         |
|-----------------------------|-----------------|
| 1 — CLI                     | ✅ Done         |
| 2 — TUI                     | ✅ Done         |
| 3 — GUI (GTK4)              | ✅ Done         |
| 4.1 — OS abstraction layer  | ✅ Done         |
| 4.2 — Windows packaging     | 🔲 In progress |
| 4.3 — macOS port            | 🔲 Todo        |
| 5 — Optional integrations   | 🔲 Todo        |

## License

MIT — see [LICENSE](LICENSE).
