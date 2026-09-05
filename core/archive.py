"""
core/archive.py — Wayback Machine URL archiving.

Submits URLs to https://web.archive.org/save/ and records the result
in archived_links.txt inside the case folder.

Always check if a URL is already archived before submitting a new save —
the Wayback Machine rate-limits saves, and a cached snapshot is just as
valid as a new one for evidence purposes.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ARCHIVED_LINKS_FILE, WAYBACK_CHECK_URL, WAYBACK_SAVE_URL
from utils.logger import get_logger
from utils.timestamp import now_str

log = get_logger("archive")

_TIMEOUT = 30  # seconds — Wayback can be slow
_USER_AGENT = "AutoCatcher/0.3 (evidence-archiver)"


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class ArchiveResult:
    """Result of a single archive attempt."""

    url: str  # Original URL that was submitted
    archived_url: str  # Wayback snapshot URL (empty string if failed)
    status: str  # "saved" | "exists" | "failed"
    timestamp: str  # UTC string — when we submitted


# ── Public API ────────────────────────────────────────────────────────────────


def archive_url(case_dir: Path, url: str) -> ArchiveResult:
    """
    Archive a URL via the Wayback Machine and record the result.

    First checks if a snapshot already exists (avoids wasting a save slot).
    If not, submits a new save request.

    The result is always written to archived_links.txt, even on failure —
    so you have a record that you tried to archive this URL.

    Returns an ArchiveResult.
    """
    log.info(f"Archiving: {url}")

    # Check for an existing snapshot first
    existing = check_archived(url)
    if existing:
        result = ArchiveResult(
            url=url,
            archived_url=existing,
            status="exists",
            timestamp=now_str(),
        )
        _record_link(case_dir, result)
        log.info(f"Already archived: {existing}")
        return result

    # Submit new save request
    try:
        resp = requests.post(
            WAYBACK_SAVE_URL + url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
            allow_redirects=True,
        )

        if resp.status_code in (200, 201):
            archived_url = _extract_snapshot_url(resp, url)
            result = ArchiveResult(
                url=url,
                archived_url=archived_url,
                status="saved",
                timestamp=now_str(),
            )
            log.info(f"Saved: {archived_url}")

        else:
            result = ArchiveResult(
                url=url,
                archived_url="",
                status="failed",
                timestamp=now_str(),
            )
            log.warning(f"Archive failed — HTTP {resp.status_code} for: {url}")

    except requests.Timeout:
        result = ArchiveResult(
            url=url, archived_url="", status="failed", timestamp=now_str()
        )
        log.error(f"Archive timed out after {_TIMEOUT}s: {url}")

    except requests.RequestException as e:
        result = ArchiveResult(
            url=url, archived_url="", status="failed", timestamp=now_str()
        )
        log.error(f"Archive request error: {e}")

    _record_link(case_dir, result)
    return result


def check_archived(url: str) -> str:
    """
    Check if a URL already has a snapshot in the Wayback Machine.

    Uses the Wayback Availability API — fast, read-only, not rate-limited.
    Returns the snapshot URL if one exists, or an empty string if not.
    """
    try:
        resp = requests.get(
            WAYBACK_CHECK_URL + url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            snapshots = data.get("archived_snapshots", {})
            closest = snapshots.get("closest", {})
            if closest.get("available"):
                return closest.get("url", "")
    except Exception as e:
        log.warning(f"Could not check archive status: {e}")
    return ""


def list_archived(case_dir: Path) -> list[str]:
    """
    Return all lines from archived_links.txt for this case.
    Each line is a formatted record of an archive attempt.
    Returns an empty list if nothing has been archived yet.
    """
    links_file = case_dir / ARCHIVED_LINKS_FILE
    if not links_file.exists() or links_file.stat().st_size == 0:
        return []
    with open(links_file) as f:
        return [line.rstrip() for line in f if line.strip()]


# ── Internal helpers ──────────────────────────────────────────────────────────


def _extract_snapshot_url(resp: requests.Response, original_url: str) -> str:
    """
    Extract the snapshot URL from a Wayback Machine save response.
    The saved URL comes back in the Content-Location header.
    Falls back to constructing it from the final response URL.
    """
    location = resp.headers.get("Content-Location", "")
    if location:
        # Content-Location is a path like /web/20260531143201/https://...
        return f"https://web.archive.org{location}"

    # Fallback: the final URL after redirects is usually the snapshot
    if "web.archive.org" in resp.url:
        return resp.url

    return ""


def _record_link(case_dir: Path, result: ArchiveResult) -> None:
    """
    Append an ArchiveResult to archived_links.txt.

    Format:
        [2026-05-31 14:32:01 UTC] [SAVED]  https://orig.url → https://web.archive.org/...
        [2026-05-31 14:32:05 UTC] [EXISTS] https://orig.url → https://web.archive.org/...
        [2026-05-31 14:32:10 UTC] [FAILED] https://orig.url
    """
    links_file = case_dir / ARCHIVED_LINKS_FILE
    arrow = f" → {result.archived_url}" if result.archived_url else ""
    line = f"[{result.timestamp}] [{result.status.upper():<6}] {result.url}{arrow}\n"
    with open(links_file, "a") as f:
        f.write(line)
