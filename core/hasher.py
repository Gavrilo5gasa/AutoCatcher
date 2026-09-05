"""
core/hasher.py — SHA256 hashing and manifest management.

Every file added to a case gets hashed immediately on intake.
The manifest (hashes.sha256) is append-only — never modified, never deleted.
This lets anyone verify evidence hasn't been tampered with.
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HASH_ALGO, HASH_MANIFEST_FILE
from utils.timestamp import now_str
from utils.logger import get_logger

log = get_logger("hasher")


# ── Hashing ───────────────────────────────────────────────────────────────────

def hash_file(filepath: Path) -> str:
    """
    Compute the SHA256 hash of a file.
    Reads in chunks so large files (videos, big logs) don't blow up RAM.
    Returns the hex digest string.
    """
    h = hashlib.new(HASH_ALGO)
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):   # 64 KB chunks
            h.update(chunk)
    return h.hexdigest()


# ── Manifest ──────────────────────────────────────────────────────────────────

def append_to_manifest(case_dir: Path, filepath: Path, digest: str) -> None:
    """
    Append one line to the case's hashes.sha256 manifest.
    Format matches standard sha256sum output so it's verifiable with
    system tools too (sha256sum --check hashes.sha256).

    Line format:
        <hash>  <relative/path/to/file>  # added 2026-05-20 15:32:01 UTC
    """
    manifest = case_dir / HASH_MANIFEST_FILE
    relative = filepath.relative_to(case_dir)
    line = f"{digest}  {relative}  # added {now_str()}\n"
    with open(manifest, "a") as f:
        f.write(line)
    log.info(f"Manifest updated: {relative}")


def hash_and_record(case_dir: Path, filepath: Path) -> str:
    """
    Hash a file AND append it to the manifest in one call.
    This is what evidence.py calls every time a file is added.
    Returns the hex digest.
    """
    digest = hash_file(filepath)
    append_to_manifest(case_dir, filepath, digest)
    return digest


# ── Verification ──────────────────────────────────────────────────────────────

def verify_manifest(case_dir: Path) -> dict:
    """
    Re-hash every file listed in the manifest and compare.
    Returns a dict:
        {
          "ok":      [list of paths that passed],
          "failed":  [list of paths that failed — possible tampering],
          "missing": [list of paths in manifest but not on disk],
        }
    """
    manifest = case_dir / HASH_MANIFEST_FILE
    results = {"ok": [], "failed": [], "missing": []}

    if not manifest.exists() or manifest.stat().st_size == 0:
        log.warning("Manifest is empty or missing — nothing to verify.")
        return results

    with open(manifest) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Strip inline comment before splitting
            clean = line.split("#")[0].strip()
            parts = clean.split(None, 1)   # split on first whitespace
            if len(parts) != 2:
                continue

            expected_digest, relative_path = parts
            filepath = case_dir / relative_path.strip()

            if not filepath.exists():
                log.warning(f"MISSING: {relative_path}")
                results["missing"].append(str(relative_path))
                continue

            actual_digest = hash_file(filepath)
            if actual_digest == expected_digest:
                log.info(f"OK: {relative_path}")
                results["ok"].append(str(relative_path))
            else:
                log.error(f"FAILED (tampered?): {relative_path}")
                results["failed"].append(str(relative_path))

    return results
