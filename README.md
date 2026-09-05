# AutoCatcher — Plan Tree
> Evidence collection & reporting tool for online predator documentation.
> Living document — update as the project evolves.

# Overview

## Phase 1 — CLI ✅ Done (Ai)

| Subphase              | Contents                                 | Status       |
|-----------------------|------------------------------------------|--------------|
| 1.1 — Foundation      | Project structure, config, utils         | ✅ Done      |
| 1.2 — Case Core       | case.py, hasher.py                       | ✅ Done (Ai) |
| 1.3 — Evidence Intake | evidence.py, archive.py                  | ✅ Done (Ai) |
| 1.4 — Packaging       | packager.py                              | ✅ Done (Ai) |
| 1.5 — Reporters       | discord.py, ncmec.py, generic.py         | ✅ Done (Ai) |
| 1.6 — CLI Interface   | main.py (Typer)                          | ✅ Done (Ai) |

The (Ai) mark is there to point that the file was FULLY made with Ai and needs a good overview and re-do by a human :)
And also that they are there as "Temporarly" just so the project works :)... I meant atleast works somehow

## Phase 2 — TUI ✅ Done (Ai)

| Subphase              | Contents                                 | Status       |
|-----------------------|------------------------------------------|--------------|
| 2.1                   | Textual app shell, case browser          | ✅ Done (Ai)|
| 2.2                   | Evidence viewer, add-evidence panel      | ✅ Done (Ai)|
| 2.3                   | Reporting flow, packing UI               | ✅ Done (Ai)|

## Phase 3 — GUI ✅ Done (Ai)

| Subphase              | Contents                                 | Status       |
|-----------------------|------------------------------------------|--------------|
| 3.1                   | GTK4 window shell, case list sidebar     | ✅ Done (Ai)|
| 3.2                   | Evidence gallery, timeline view          | ✅ Done (Ai)|
| 3.3                   | Report wizard                            | ✅ Done (Ai)|

## Phase 4 — Cross-Platform

| Subphase              | Contents                                 | Status       |
|-----------------------|------------------------------------------|--------------|
| 4.1                   | OS abstraction layer (screenshot, paths) | 🔲 Todo      |
| 4.2                   | Windows packaging (PyInstaller)          | 🔲 Todo      |
| 4.3                   | macOS port                               | 🔲 Todo      |

## Phase 5 — Optional

| Subphase              | Contents                                 | Status       |
|-----------------------|------------------------------------------|--------------|
| 5.1                   | Discord Bot connected to the App         | 🔲 Todo      |
| 5.2                   | Roblox Integration                       | 🔲 Todo      |
| 5.3                   | Connects to a Toster...                  | 🔲 Todo      |

It's a template.. ok... not really making it connect to a Toster...

---

# Structure

## Project Structure

```
autocatcher/
├── main.py                  # Entry point — Typer CLI
├── config.py                # All paths, settings, constants
├── PLAN_TREE.md             # This file
│
├── core/
│   ├── case.py              # Case creation, loading, folder structure
│   ├── evidence.py          # Add screenshots, logs, files to a case
│   ├── archive.py           # Wayback Machine URL archiving
│   ├── hasher.py            # SHA256 hash all files + manifest
│   └── packager.py          # Zip case + generate summary report
│
├── reporters/
│   ├── discord.py           # Discord Trust & Safety links + checklist
│   ├── ncmec.py             # NCMEC CyberTipline (minors involved)
│   └── generic.py           # Generic platform report guide
│
├── utils/
│   ├── timestamp.py         # UTC timestamps, consistent formatting
│   └── logger.py            # Internal app logging
│
└── cases/                   # Output — one folder per case
    └── 2026-05-20_username/
        ├── screenshots/
        ├── logs/
        ├── files/
        ├── archived/
        ├── hashes.sha256
        ├── archived_links.txt
        ├── case_meta.json
        └── summary.txt
```

---

## Tech Stack

| Layer       | Choice              | Why                         |
|-------------|---------------------|-----------------------------|
| Language    | Python              | Smooth CLI → TUI → GUI path |
| CLI         | Typer               | Typed, clean, auto help     |
| TUI         | Textual             | Modern, great on Hyprland   |
| GUI         | GTK4 (PyGObject)    | Native Wayland, no XWayland |
| Storage     | SQLite              | Simple case DB, portable    |
| Hashing     | hashlib (built-in)  | No deps, SHA256             |
| Archiving   | Wayback Machine API | Free, reliable              |
| Screenshots | grim (Wayland)      | Native Hyprland/Wayland     |
| Packaging   | zipfile + reportlab | Clean report output         |

---

## Core Design Rules

1. **OS-specific calls always wrapped** — never call `grim` directly in logic. Swap per-platform without touching core.
2. **Cases are self-contained folders** — if the app breaks, evidence is still human-readable on disk.
3. **Nothing is ever deleted or mutated** — append only. Evidence integrity is everything.
4. **Timestamps are always UTC** — legal validity across timezones.
5. **Hash everything on intake** — SHA256 manifest generated the moment a file is added.

---

# Report

## Reporting Targets

| Platform     | Method                              | Notes                        |
|--------------|-------------------------------------|------------------------------|
| Discord      | dis.gd/report + Trust & Safety form | Include case ID + zip        |
| NCMEC        | CyberTipline (cybertipline.org)     | Required if minor involved   |
| Twitter/X    | In-app report + Trust & Safety      | Archive profile first        |
| Local police | Cybercrime unit                     | Use packaged zip as evidence |
| Generic      | Platform report + evidence package  | Fallback for any platform    |
# AutoCatcher
