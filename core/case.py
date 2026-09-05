"""
core/case.py — Case creation, loading, and metadata management.

A "case" is a self-contained folder under cases/ that holds all evidence
for one subject. Once created, files inside are never deleted or modified.
"""

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ARCHIVED_LINKS_FILE,
    CASE_SUBDIRS,
    CASES_DIR,
    HASH_MANIFEST_FILE,
    METADATA_FILE,
    SUMMARY_FILE,
)
from utils.logger import get_logger
from utils.timestamp import date_slug, now_slug, now_str

log = get_logger("case")


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class CaseMeta:
    """
    Everything AutoCatcher knows about a case.
    Stored as case_meta.json inside the case folder.
    Add new fields here as the app grows — old cases just won't have them.
    """

    case_id: str
    subject: str  # Username / handle of the subject
    platform: str  # e.g. "discord", "twitter"
    created_at: str  # UTC string
    notes: str = ""
    minor_involved: bool = False
    tags: list = field(default_factory=list)


# ── Creation ──────────────────────────────────────────────────────────────────


def create_case(
    subject: str,
    platform: str,
    notes: str = "",
    minor_involved: bool = False,
) -> Path:
    """
    Create a new case folder with all subdirectories and metadata.
    Returns the Path to the case folder.

    Folder name format:  <date>_<name>
    Collisions (same subject same day) get a full timestamp suffix.
    """
    CASES_DIR.mkdir(parents=True, exist_ok=True)

    safe_subject = _slugify(subject)
    case_id = f"{date_slug()}_{safe_subject}"
    case_dir = CASES_DIR / case_id

    # Handle name collision — append full timestamp
    if case_dir.exists():
        case_id = f"{now_slug()}_{safe_subject}"
        case_dir = CASES_DIR / case_id

    # Build folder tree
    case_dir.mkdir(parents=True)
    for sub in CASE_SUBDIRS:
        (case_dir / sub).mkdir()

    # Touch persistent files so they exist even when empty
    (case_dir / HASH_MANIFEST_FILE).touch()
    (case_dir / ARCHIVED_LINKS_FILE).touch()

    # Write metadata and initial summary
    meta = CaseMeta(
        case_id=case_id,
        subject=subject,
        platform=platform,
        created_at=now_str(),
        notes=notes,
        minor_involved=minor_involved,
    )
    _write_meta(case_dir, meta)
    _write_summary(case_dir, meta)

    log.info(f"Case created: {case_id}")
    return case_dir


# ── Loading ───────────────────────────────────────────────────────────────────


def load_case(case_id: str) -> tuple[Path, CaseMeta]:
    """
    Load an existing case by its ID string.
    Returns (case_dir, CaseMeta).
    Raises FileNotFoundError if the case doesn't exist.
    """
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        raise FileNotFoundError(f"No case found: {case_id}")
    meta = _read_meta(case_dir)
    return case_dir, meta


def list_cases() -> list[CaseMeta]:
    """
    Return metadata for all cases, sorted newest first.
    Skips folders that are missing a metadata file (e.g. manual folders).
    """
    if not CASES_DIR.exists():
        return []
    cases = []
    for path in sorted(CASES_DIR.iterdir(), reverse=True):
        if path.is_dir() and (path / METADATA_FILE).exists():
            try:
                cases.append(_read_meta(path))
            except Exception as e:
                log.warning(f"Could not read case {path.name}: {e}")
    return cases


# ── Notes ─────────────────────────────────────────────────────────────────────


def append_note(case_dir: Path, note: str) -> None:
    """
    Add a timestamped note to an existing case.
    Never overwrites — always appends to existing notes.
    """
    meta = _read_meta(case_dir)
    sep = "\n" if meta.notes else ""
    meta.notes = f"{meta.notes}{sep}[{now_str()}] {note}"
    _write_meta(case_dir, meta)
    _write_summary(case_dir, meta)
    log.info("Note appended to case.")


# ── Internal helpers ──────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Convert a username to a filesystem-safe slug: Bad User#1234 → bad_user_1234"""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "_", text)  # replace special chars with _
    text = re.sub(r"[\s-]+", "_", text)  # replace spaces/dashes with _
    return text[:40]  # cap length


def _write_meta(case_dir: Path, meta: CaseMeta) -> None:
    with open(case_dir / METADATA_FILE, "w") as f:
        json.dump(asdict(meta), f, indent=2)


def _read_meta(case_dir: Path) -> CaseMeta:
    with open(case_dir / METADATA_FILE) as f:
        data = json.load(f)
    return CaseMeta(**data)


def _write_summary(case_dir: Path, meta: CaseMeta) -> None:
    """Regenerate the human-readable summary.txt from current metadata."""
    minor_flag = (
        "*** YES — FILE WITH NCMEC CYBERTIPLINE ***" if meta.minor_involved else "No"
    )
    lines = [
        "=" * 60,
        "  AutoCatcher — Case Summary",
        "=" * 60,
        f"  Case ID:         {meta.case_id}",
        f"  Subject:         {meta.subject}",
        f"  Platform:        {meta.platform}",
        f"  Created:         {meta.created_at}",
        f"  Minor Involved:  {minor_flag}",
        f"  Tags:            {', '.join(meta.tags) if meta.tags else 'none'}",
        "=" * 60,
        "  Notes",
        "-" * 60,
        meta.notes if meta.notes else "  (none)",
        "=" * 60,
    ]
    with open(case_dir / SUMMARY_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
