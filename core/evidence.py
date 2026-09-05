"""
core/evidence.py — Adding evidence files to a case.

Evidence comes in three types:
  screenshot  → screenshots/
  log         → logs/
  file        → files/  (anything that doesn't fit above)

Every file is copied in, hashed immediately, and recorded in
evidence_log.json. The original file is never touched or deleted.
"""

import json
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EVIDENCE_LOG_FILE
from core.hasher import hash_and_record
from utils.timestamp import now_str, now_slug
from utils.logger import get_logger

log = get_logger("evidence")

EvidenceType = Literal["screenshot", "log", "file"]

_TYPE_TO_SUBDIR: dict[str, str] = {
    "screenshot": "screenshots",
    "log":        "logs",
    "file":       "files",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class EvidenceRecord:
    """Metadata for a single piece of evidence, stored in evidence_log.json."""
    filename:      str          # Name as stored inside the case folder
    original_name: str          # Original filename before copy
    type:          str          # screenshot | log | file
    sha256:        str          # Hex digest — proof of integrity
    added_at:      str          # UTC string
    description:   str = ""     # What this evidence shows
    source:        str = ""     # e.g. "Discord #general", "https://...", "DM"


# ── Public API ────────────────────────────────────────────────────────────────

def add_screenshot(
    case_dir:    Path,
    src:         Path,
    description: str = "",
    source:      str = "",
) -> EvidenceRecord:
    """Add a screenshot to the case. Convenience wrapper around add_evidence."""
    return add_evidence(case_dir, src, "screenshot", description, source)


def add_log(
    case_dir:    Path,
    src:         Path,
    description: str = "",
    source:      str = "",
) -> EvidenceRecord:
    """Add a log/text file to the case. Convenience wrapper around add_evidence."""
    return add_evidence(case_dir, src, "log", description, source)


def add_file(
    case_dir:    Path,
    src:         Path,
    description: str = "",
    source:      str = "",
) -> EvidenceRecord:
    """Add a generic file to the case. Convenience wrapper around add_evidence."""
    return add_evidence(case_dir, src, "file", description, source)


def add_evidence(
    case_dir:      Path,
    src:           Path,
    evidence_type: EvidenceType,
    description:   str = "",
    source:        str = "",
) -> EvidenceRecord:
    """
    Copy a file into the case, hash it immediately, and record it.

    src            — path to the original file (not modified)
    evidence_type  — "screenshot" | "log" | "file"
    description    — what this evidence shows (optional but recommended)
    source         — where it came from: channel, URL, username, etc.

    Returns the EvidenceRecord for the newly added file.
    Raises ValueError for an unrecognised evidence_type.
    Raises FileNotFoundError if src doesn't exist.
    """
    if evidence_type not in _TYPE_TO_SUBDIR:
        raise ValueError(
            f"Invalid evidence type '{evidence_type}'. "
            f"Must be one of: {list(_TYPE_TO_SUBDIR)}"
        )

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    subdir = case_dir / _TYPE_TO_SUBDIR[evidence_type]
    dest   = _unique_dest(subdir, src.name)

    shutil.copy2(src, dest)                         # copy, preserve metadata
    digest = hash_and_record(case_dir, dest)        # hash + append to manifest

    record = EvidenceRecord(
        filename      = dest.name,
        original_name = src.name,
        type          = evidence_type,
        sha256        = digest,
        added_at      = now_str(),
        description   = description,
        source        = source,
    )
    _append_record(case_dir, record)
    log.info(f"Evidence added: [{evidence_type}] {dest.name}")
    return record


def list_evidence(case_dir: Path) -> list[EvidenceRecord]:
    """
    Return all evidence records for a case, in the order they were added.
    Returns an empty list if no evidence has been added yet.
    """
    log_path = case_dir / EVIDENCE_LOG_FILE
    if not log_path.exists() or log_path.stat().st_size == 0:
        return []
    with open(log_path) as f:
        data = json.load(f)
    return [EvidenceRecord(**entry) for entry in data]


def count_evidence(case_dir: Path) -> dict[str, int]:
    """
    Return a count of evidence by type: {"screenshot": 3, "log": 1, "file": 0}
    Useful for summaries and reports.
    """
    counts: dict[str, int] = {t: 0 for t in _TYPE_TO_SUBDIR}
    for record in list_evidence(case_dir):
        if record.type in counts:
            counts[record.type] += 1
    return counts


# ── Internal helpers ──────────────────────────────────────────────────────────

def _unique_dest(subdir: Path, filename: str) -> Path:
    """
    Build a destination path that won't collide with existing files.
    Prepends a UTC timestamp slug so files sort chronologically.

    screenshot.png        →  2026-05-31_143201_screenshot.png
    (if that exists)      →  2026-05-31_143201_screenshot_2.png
    """
    stem    = Path(filename).stem
    suffix  = Path(filename).suffix
    slug    = now_slug()
    base    = f"{slug}_{stem}"
    dest    = subdir / f"{base}{suffix}"
    counter = 2
    while dest.exists():
        dest = subdir / f"{base}_{counter}{suffix}"
        counter += 1
    return dest


def _append_record(case_dir: Path, record: EvidenceRecord) -> None:
    """Append an EvidenceRecord to evidence_log.json (creates it on first call)."""
    log_path = case_dir / EVIDENCE_LOG_FILE
    if log_path.exists() and log_path.stat().st_size > 0:
        with open(log_path) as f:
            entries = json.load(f)
    else:
        entries = []
    entries.append(asdict(record))
    with open(log_path, "w") as f:
        json.dump(entries, f, indent=2)
