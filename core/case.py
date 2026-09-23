"""
core/case.py — Case creation, loading, and metadata management.

A "case" is a self-contained folder that holds all evidence for one
subject. Cases can nest — a case can contain sub-cases underneath it
(cases/<parent>/subcases/<child>/) — useful when one case represents a
whole community (e.g. a Discord server) and each sub-case is one member
under investigation.

Evidence files themselves are still never deleted or modified once added
(see core/evidence.py, core/hasher.py). Notes and case deletion below are
edit-friendly, but neither one destroys history: editing a note keeps the
prior text in that note's edit history, and deleting a case moves it to a
trash folder rather than removing it from disk.
"""

import json
import secrets
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ARCHIVED_LINKS_FILE,
    CASE_SUBDIRS,
    CASES_DIR,
    HASH_MANIFEST_FILE,
    LINKED_CASES_FILE,
    METADATA_FILE,
    SUBCASES_DIRNAME,
    SUMMARY_FILE,
    TRASH_DIRNAME,
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
    notes: str = ""  # Legacy plain-text view, auto-regenerated from note_entries
    note_entries: list = field(default_factory=list)  # structured, editable notes — see NoteEntry
    minor_involved: bool = False
    tags: list = field(default_factory=list)
    linked_cases: list = field(default_factory=list)  # [{case_id, comment, created_at}, ...]
    parent_case: str = ""  # non-empty if this is a sub-case of another case


@dataclass
class NoteEntry:
    """
    One note, structured and editable. Editing never discards the previous
    text — it's pushed onto edit_history first — so a note's full revision
    trail survives even though the displayed text can change.
    """

    id: str
    created_at: str
    text: str
    edited_at: str = ""
    edit_history: list = field(default_factory=list)  # [{"text":.., "changed_at":..}, ...]


# ── Creation ──────────────────────────────────────────────────────────────────


def create_case(
    subject: str,
    platform: str,
    notes: str = "",
    minor_involved: bool = False,
    parent_case: str = "",
) -> Path:
    """
    Create a new case folder with all subdirectories and metadata.
    Returns the Path to the case folder.

    Folder name format:  <date>_<name>
    Collisions (same subject same day) get a full timestamp suffix.

    If parent_case is given, this is created as a sub-case nested inside
    an existing case's subcases/ folder — see list_subcases().
    """
    if parent_case:
        parent_dir = _find_case_dir(parent_case)
        if parent_dir is None:
            raise FileNotFoundError(f"Parent case not found: {parent_case}")
        base_dir = parent_dir / SUBCASES_DIRNAME
    else:
        base_dir = CASES_DIR

    base_dir.mkdir(parents=True, exist_ok=True)

    safe_subject = _slugify(subject)
    case_id = f"{date_slug()}_{safe_subject}"
    case_dir = base_dir / case_id

    # Handle name collision — append full timestamp
    if case_dir.exists():
        case_id = f"{now_slug()}_{safe_subject}"
        case_dir = base_dir / case_id

    # Build folder tree
    case_dir.mkdir(parents=True)
    for sub in CASE_SUBDIRS:
        (case_dir / sub).mkdir()

    # Touch persistent files so they exist even when empty
    (case_dir / HASH_MANIFEST_FILE).touch()
    (case_dir / ARCHIVED_LINKS_FILE).touch()
    (case_dir / LINKED_CASES_FILE).touch()

    # Write metadata and initial summary
    meta = CaseMeta(
        case_id=case_id,
        subject=subject,
        platform=platform,
        created_at=now_str(),
        minor_involved=minor_involved,
        parent_case=parent_case,
    )
    if notes:
        _add_note_entry(meta, notes)
    _write_meta(case_dir, meta)
    _write_summary(case_dir, meta)

    log.info(f"Case created: {case_id}" + (f" (sub-case of {parent_case})" if parent_case else ""))
    return case_dir


# ── Loading ───────────────────────────────────────────────────────────────────


def load_case(case_id: str) -> tuple[Path, CaseMeta]:
    """
    Load an existing case by its ID string. Searches top-level cases and
    any depth of nested sub-cases (excludes the trash folder).
    Returns (case_dir, CaseMeta).
    Raises FileNotFoundError if the case doesn't exist.
    """
    case_dir = _find_case_dir(case_id)
    if case_dir is None:
        raise FileNotFoundError(f"No case found: {case_id}")
    meta = _read_meta(case_dir)
    return case_dir, meta


def list_cases() -> list[CaseMeta]:
    """
    Return metadata for all top-level cases, sorted newest first.
    Sub-cases are not included here — see list_subcases(parent_case_id).
    Skips folders that are missing a metadata file (e.g. manual folders)
    and the trash folder.
    """
    if not CASES_DIR.exists():
        return []
    cases = []
    for path in sorted(CASES_DIR.iterdir(), reverse=True):
        if path.name == TRASH_DIRNAME:
            continue
        if path.is_dir() and (path / METADATA_FILE).exists():
            try:
                cases.append(_read_meta(path))
            except Exception as e:
                log.warning(f"Could not read case {path.name}: {e}")
    return cases


def list_subcases(parent_case_id: str) -> list[CaseMeta]:
    """Return every direct sub-case of parent_case_id, newest first."""
    parent_dir = _find_case_dir(parent_case_id)
    if parent_dir is None:
        return []
    sub_root = parent_dir / SUBCASES_DIRNAME
    if not sub_root.exists():
        return []
    cases = []
    for path in sorted(sub_root.iterdir(), reverse=True):
        if path.is_dir() and (path / METADATA_FILE).exists():
            try:
                cases.append(_read_meta(path))
            except Exception as e:
                log.warning(f"Could not read sub-case {path.name}: {e}")
    return cases


# ── Notes ─────────────────────────────────────────────────────────────────────


def append_note(case_dir: Path, text: str) -> str:
    """
    Add a new note to a case. Kept under its historical name (`append_note`)
    since the CLI/TUI/packager all call it, but it now stores a structured,
    later-editable NoteEntry rather than only a plain-text line.

    Returns the new note's id (needed for edit_note()).
    """
    meta = _read_meta(case_dir)
    note_id = _add_note_entry(meta, text)
    _write_meta(case_dir, meta)
    _write_summary(case_dir, meta)
    log.info("Note added to case.")
    return note_id


def edit_note(case_dir: Path, note_id: str, new_text: str) -> None:
    """
    Change an existing note's text. The previous text is preserved in the
    note's edit_history rather than being discarded — the note's audit
    trail survives an edit, only the "current" text shown by default
    changes. Raises ValueError if note_id doesn't exist on this case.
    """
    meta = _read_meta(case_dir)
    for entry in meta.note_entries:
        if entry["id"] == note_id:
            entry["edit_history"].append(
                {"text": entry["text"], "changed_at": entry["edited_at"] or entry["created_at"]}
            )
            entry["text"] = new_text
            entry["edited_at"] = now_str()
            meta.notes = _render_legacy_notes(meta.note_entries)
            _write_meta(case_dir, meta)
            _write_summary(case_dir, meta)
            log.info(f"Note edited: {note_id}")
            return
    raise ValueError(f"No note with id {note_id} on this case.")


def get_note_entries(meta: CaseMeta) -> list[NoteEntry]:
    """Structured view of every note on a case, oldest first."""
    return [NoteEntry(**entry) for entry in meta.note_entries]


def _add_note_entry(meta: CaseMeta, text: str) -> str:
    """Mutates meta in place: appends a new NoteEntry, regenerates meta.notes."""
    note_id = f"{now_slug()}_{secrets.token_hex(3)}"
    meta.note_entries.append(
        {
            "id": note_id,
            "created_at": now_str(),
            "text": text,
            "edited_at": "",
            "edit_history": [],
        }
    )
    meta.notes = _render_legacy_notes(meta.note_entries)
    return note_id


def _render_legacy_notes(note_entries: list) -> str:
    """
    Rebuild the classic "[timestamp] text" plain-text blob from structured
    entries, so CLI output, the TUI, and the PDF report — none of which
    know about note_entries — keep showing the current (possibly edited)
    text without needing any changes on their end.
    """
    lines = []
    for entry in note_entries:
        suffix = " (edited)" if entry.get("edited_at") else ""
        lines.append(f"[{entry['created_at']}]{suffix} {entry['text']}")
    return "\n".join(lines)


@dataclass
class LegacyNoteEntry:
    """One parsed legacy note line — kept for cases from before structured notes."""

    timestamp: str
    text: str


def parse_notes(notes: str) -> list[LegacyNoteEntry]:
    """
    Split a raw notes blob (one "[timestamp] text" per line) into entries.
    Used only as a fallback for reading very old case_meta.json files that
    predate note_entries — new code should use get_note_entries() instead.
    """
    if not notes:
        return []
    entries = []
    for line in notes.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            ts, _, text = line[1:].partition("]")
            entries.append(LegacyNoteEntry(timestamp=ts.strip(), text=text.strip()))
        else:
            entries.append(LegacyNoteEntry(timestamp="", text=line))
    return entries


# ── Case linking ──────────────────────────────────────────────────────────────


def link_case(case_dir: Path, other_case_id: str, comment: str = "") -> None:
    """
    Record a link between this case and another, with an optional comment
    explaining why (e.g. "subject is being promoted to this server from
    another case we're tracking") — like pinning two index cards together
    on a board with a note on the string.

    Written to both cases (so the link is visible from either side) and
    appended to each case's linked_cases.txt — an always-growing audit
    file of every link ever made, independent of whether it's later
    unlinked. Multiple links between the same two cases are allowed; each
    one is its own dated entry, since the reason for a link can change or
    accumulate evidence over time.
    """
    meta = _read_meta(case_dir)
    if other_case_id == meta.case_id:
        return
    other_dir = _find_case_dir(other_case_id)
    if other_dir is None:
        raise FileNotFoundError(f"No case found: {other_case_id}")
    other_meta = _read_meta(other_dir)

    ts = now_str()
    meta.linked_cases.append({"case_id": other_case_id, "comment": comment, "created_at": ts})
    other_meta.linked_cases.append({"case_id": meta.case_id, "comment": comment, "created_at": ts})
    _write_meta(case_dir, meta)
    _write_meta(other_dir, other_meta)

    _append_linked_file(case_dir, other_case_id, comment, ts)
    _append_linked_file(other_dir, meta.case_id, comment, ts)

    log.info(f"Linked case {meta.case_id} <-> {other_case_id}: {comment or '(no comment)'}")


def unlink_case(case_dir: Path, other_case_id: str) -> None:
    """
    Remove other_case_id from this case's *current* linked_cases list (and
    vice versa). This only affects what's shown as currently linked — the
    historical record in linked_cases.txt is never edited or truncated.
    """
    meta = _read_meta(case_dir)
    meta.linked_cases = [l for l in meta.linked_cases if l["case_id"] != other_case_id]
    _write_meta(case_dir, meta)

    other_dir = _find_case_dir(other_case_id)
    if other_dir is not None:
        other_meta = _read_meta(other_dir)
        other_meta.linked_cases = [l for l in other_meta.linked_cases if l["case_id"] != meta.case_id]
        _write_meta(other_dir, other_meta)


def list_linked_cases(meta: CaseMeta) -> list[dict]:
    """Currently-linked cases: [{case_id, comment, created_at}, ...], newest first."""
    return list(reversed(meta.linked_cases))


def _append_linked_file(case_dir: Path, other_case_id: str, comment: str, ts: str) -> None:
    """Append one line to this case's linked_cases.txt — never overwritten."""
    line = f"[{ts}] -> {other_case_id} : {comment or '(no comment)'}\n"
    with open(case_dir / LINKED_CASES_FILE, "a") as f:
        f.write(line)


# ── Deletion (soft — moves to trash, never destroys) ──────────────────────────


def delete_case(case_id: str) -> Path:
    """
    Move a case (and everything nested inside it — sub-cases travel with
    their parent) to the trash folder instead of deleting it outright.
    No forcedel needed, and nothing is actually lost — see restore_case()
    and purge_case().

    Returns the new path inside the trash folder.
    """
    case_dir = _find_case_dir(case_id)
    if case_dir is None:
        raise FileNotFoundError(f"No case found: {case_id}")

    trash_root = CASES_DIR / TRASH_DIRNAME
    trash_root.mkdir(parents=True, exist_ok=True)

    dest = trash_root / case_id
    if dest.exists():
        dest = trash_root / f"{case_id}_{now_slug()}"

    shutil.move(str(case_dir), str(dest))
    log.info(f"Case moved to trash: {case_id}")
    return dest


def list_trash() -> list[CaseMeta]:
    """Return metadata for every case currently sitting in the trash."""
    trash_root = CASES_DIR / TRASH_DIRNAME
    if not trash_root.exists():
        return []
    cases = []
    for path in sorted(trash_root.iterdir(), reverse=True):
        if path.is_dir() and (path / METADATA_FILE).exists():
            try:
                cases.append(_read_meta(path))
            except Exception as e:
                log.warning(f"Could not read trashed case {path.name}: {e}")
    return cases


def restore_case(case_id: str) -> Path:
    """Move a case out of the trash and back to top-level cases/."""
    trash_root = CASES_DIR / TRASH_DIRNAME
    src = trash_root / case_id
    if not src.exists():
        raise FileNotFoundError(f"No trashed case found: {case_id}")

    dest = CASES_DIR / case_id
    if dest.exists():
        dest = CASES_DIR / f"{case_id}_restored_{now_slug()}"

    shutil.move(str(src), str(dest))
    log.info(f"Case restored from trash: {case_id}")
    return dest


def purge_case(case_id: str) -> None:
    """
    Permanently delete a case from the trash. This is the only actually
    destructive operation in the whole app — it only ever operates on
    cases already sitting in the trash, never on a live case directly.
    """
    trash_root = CASES_DIR / TRASH_DIRNAME
    target = trash_root / case_id
    if not target.exists():
        raise FileNotFoundError(f"No trashed case found: {case_id}")
    shutil.rmtree(target)
    log.info(f"Case permanently purged: {case_id}")


# ── Internal helpers ──────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Convert a username to a filesystem-safe slug: Bad User#1234 → bad_user_1234"""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "_", text)  # replace special chars with _
    text = re.sub(r"[\s-]+", "_", text)  # replace spaces/dashes with _
    return text[:40]  # cap length


def _find_case_dir(case_id: str, root: Path | None = None) -> Path | None:
    """
    Locate a case's folder anywhere in the tree: top-level, or nested any
    number of levels inside other cases' subcases/ folders. Skips the
    trash folder — a trashed case must be restored before it can be
    loaded/linked/edited again.
    """
    root = root or CASES_DIR
    if not root.exists():
        return None

    direct = root / case_id
    if direct.is_dir() and (direct / METADATA_FILE).exists():
        return direct

    for entry in root.iterdir():
        if not entry.is_dir() or entry.name == TRASH_DIRNAME:
            continue
        if not (entry / METADATA_FILE).exists():
            continue
        sub_root = entry / SUBCASES_DIRNAME
        if sub_root.is_dir():
            found = _find_case_dir(case_id, sub_root)
            if found is not None:
                return found
    return None


def _write_meta(case_dir: Path, meta: CaseMeta) -> None:
    with open(case_dir / METADATA_FILE, "w") as f:
        json.dump(asdict(meta), f, indent=2)


def _read_meta(case_dir: Path) -> CaseMeta:
    with open(case_dir / METADATA_FILE) as f:
        data = json.load(f)
    meta = CaseMeta(**data)

    # Self-healing migration: cases written before structured notes existed
    # have text in `notes` but nothing in `note_entries`. Migrate once, on
    # first read, using deterministic ids (not random) so re-reading the
    # same un-migrated file twice can't ever produce two different ids for
    # the same note.
    if not meta.note_entries and meta.notes:
        legacy = parse_notes(meta.notes)
        meta.note_entries = [
            {
                "id": f"legacy-{i:04d}",
                "created_at": entry.timestamp or meta.created_at,
                "text": entry.text,
                "edited_at": "",
                "edit_history": [],
            }
            for i, entry in enumerate(legacy)
        ]
        _write_meta(case_dir, meta)

    return meta


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
    ]
    if meta.parent_case:
        lines.append(f"  Parent case:     {meta.parent_case}")
    lines += [
        "=" * 60,
        "  Notes",
        "-" * 60,
        meta.notes if meta.notes else "  (none)",
        "=" * 60,
    ]
    with open(case_dir / SUMMARY_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
