"""
config.py — AutoCatcher global configuration.
All paths and settings live here. Import this everywhere — never hardcode.
"""

import os
from pathlib import Path

# ── App info ──────────────────────────────────────────────────────────────────

APP_NAME = "AutoCatcher"
APP_VERSION = "0.3.0"
APP_PHASE = "Phase 3 — GUI"

# ── Paths ─────────────────────────────────────────────────────────────────────

# Root of the project (wherever this file lives)
PROJECT_ROOT = Path(__file__).parent.resolve()

# Where all cases are stored. Override with env var AUTOCACHER_CASES_DIR if needed.
CASES_DIR = Path(os.environ.get("AUTOCATCHER_CASES_DIR", PROJECT_ROOT / "cases"))

# Where packaged zips are written. Override with AUTOCACHER_PACKAGES_DIR if needed.
PACKAGES_DIR = Path(os.environ.get("AUTOCATCHER_PACKAGES_DIR", PROJECT_ROOT / "packages"))

# ── Case folder structure ─────────────────────────────────────────────────────SUBDIRS

# Subdirectories created inside every new case folder
CASE_SUBDIRS = ["screenshots", "logs", "files", "archived"]

# Fixed filenames inside each case folder
HASH_MANIFEST_FILE = "hashes.sha256"
ARCHIVED_LINKS_FILE = "archived_links.txt"
SUMMARY_FILE = "summary.txt"
METADATA_FILE = "case_meta.json"
EVIDENCE_LOG_FILE = "evidence_log.json"
REPORT_FILE = "report.pdf"  # Generated PDF — lives inside the case folder

# ── Hashing ───────────────────────────────────────────────────────────────────

HASH_ALGO = "sha256"

# ── Wayback Machine ───────────────────────────────────────────────────────────

WAYBACK_SAVE_URL = "https://web.archive.org/save/"
WAYBACK_CHECK_URL = "https://archive.org/wayback/available?url="

# ── Reporting targets ─────────────────────────────────────────────────────────

REPORT_TARGETS = {
    "discord": {
        "name": "Discord Report illegal content",
        "url": "https://discord.com/report",
        "notes": "Include the subject's username#tag, the server name, "
        "and attach your evidence zip.",
    },
    "ncmec": {
        "name": "NCMEC CyberTipline",
        "url": "https://report.cybertip.org/reporting",
        "notes": "Use this when a minor is involved. "
        "Legally mandated response from NCMEC.",
    },
    "twitter": {
        "name": "Twitter/X Trust & Safety",
        "url": "https://help.x.com/en/rules-and-policies/x-report-violation",
        "notes": "Archive their profile URL BEFORE reporting — "
        "accounts get suspended and deleted fast.",
    },
    "generic": {
        "name": "Generic Platform Report",
        "url": "",
        "notes": "Use the platform's built-in report tool, "
        "then follow up with your packaged evidence zip.",
    },
}
