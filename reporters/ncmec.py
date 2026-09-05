"""
reporters/ncmec.py — NCMEC CyberTipline reporting guide.

FOR CASES INVOLVING MINORS ONLY.

The National Center for Missing & Exploited Children (NCMEC) operates the
CyberTipline — the central intake for reports of online child sexual
exploitation in the US. Reports can be submitted by anyone.

Submission URL: https://cybertipline.org
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.case import load_case
from utils.logger import get_logger
from utils.timestamp import now_str

from reporters import ReportGuide

log = get_logger("reporter.ncmec")

_PLATFORM = "ncmec"
_TITLE = "NCMEC CyberTipline"
_SUBMIT_URL = "https://cybertipline.org"
_GUIDE_FILE = "ncmec_guide.txt"


# ── Public API ────────────────────────────────────────────────────────────────


def generate_guide(case_dir: Path) -> ReportGuide:
    """
    Generate an NCMEC CyberTipline reporting guide for this case.
    Writes ncmec_guide.txt into the case folder.

    Note: This guide is valid regardless of minor_involved status —
    the CLI warns, but the user may know more than the metadata reflects.
    """
    _, meta = load_case(case_dir.name)

    if not meta.minor_involved:
        log.warning(
            "minor_involved is False for this case. "
            "NCMEC CyberTipline is intended for cases involving minors. "
            "Generating guide anyway — verify before submitting."
        )

    checklist = _build_checklist(meta)
    template = _build_template(meta)
    notes = _build_notes()

    guide = ReportGuide(
        platform=_PLATFORM,
        title=_TITLE,
        submit_url=_SUBMIT_URL,
        checklist=checklist,
        template=template,
        notes=notes,
    )

    guide_path = _write_guide(case_dir, guide, meta)
    guide.guide_path = guide_path

    log.info(f"NCMEC guide written: {guide_path.name}")
    return guide


# ── Guide content ─────────────────────────────────────────────────────────────


def _build_checklist(meta) -> list[str]:
    return [
        "DO NOT delete, alter, or screenshot over any evidence. "
        "Original files are required. AutoCatcher preserves them — don't touch them.",
        "DO NOT confront or warn the subject. This could cause them to delete "
        "accounts and destroy evidence before law enforcement can act.",
        "Archive the subject's profile page immediately if you haven't already "
        "(accounts disappear after reports are processed).",
        f"Note the subject's exact username on the platform: {meta.subject!r}. "
        "Include any user IDs, email addresses, or other identifiers you have.",
        "Note the child's approximate age if known — the CyberTipline form "
        "asks for this. You do not need to be certain.",
        "Identify the incident type: online enticement, grooming, "
        "CSAM production/distribution, or sextortion (see notes).",
        f"Submit your report at {_SUBMIT_URL}. You will receive a tip number — "
        "keep it. Law enforcement uses it to track the case.",
        "After submitting to NCMEC, file a report with your local law "
        "enforcement or the FBI's IC3 at ic3.gov. Provide your NCMEC tip number.",
        "Also report the account to the platform (Discord, etc.) separately. "
        "Platform + NCMEC + law enforcement are three separate steps.",
    ]


def _build_template(meta) -> str:
    return f"""\
[This is a reference for what to have ready when filling the CyberTipline form.
The form is structured — you fill in fields rather than pasting free text.]

INCIDENT TYPE (select the best match):
  [ ] Online Enticement           — adult soliciting a minor online
  [ ] Child Sexual Abuse Material — production, distribution, or possession
  [ ] Sextortion                  — coercing a minor with images/threats
  [ ] Misleading Domain Name      — site designed to expose minors to adult content
  [ ] Obscene Material Sent to Minor

SUSPECT INFORMATION:
  Platform:         {meta.platform.title()}
  Username/Handle:  {meta.subject}
  User ID:          [PASTE IF KNOWN, otherwise leave blank]
  Other identifiers: [email, phone, other usernames if known]

CHILD INFORMATION (only what you know — estimated is fine):
  Age (approximate): [AGE IF KNOWN]
  Relationship to suspect: Stranger / Online acquaintance / [other]

INCIDENT DETAILS:
  Date(s):    [EARLIEST DATE] to [LATEST DATE]
  Location:   Online — {meta.platform.title()} [server/DMs]
  Description:
    [Describe the behavior factually: what the suspect said or did,
    how contact was initiated, what was requested or shared, and over
    what time period. Keep it factual and specific.]

EVIDENCE:
  I have an evidence package collected with AutoCatcher (Case ID: {meta.case_id}).
  It contains timestamped screenshots, exported chat logs, and archived URLs.
  All files have been SHA256-hashed for integrity verification.
  [Attach the zip if the form supports uploads, or note it is available on request.]\
"""


def _build_notes() -> str:
    return """\
WHAT NCMEC DOES WITH YOUR REPORT:
  NCMEC analysts review each tip and forward qualifying reports to the
  relevant law enforcement agency (federal, state, or international).
  You will receive a tip number — this is how law enforcement references
  your report. Keep it.

INCIDENT TYPES — choose carefully:
  Online Enticement  = an adult using the internet to solicit a minor for
                       sexual activity, to produce sexual images, or to meet.
  CSAM               = images or video depicting sexual abuse of a minor.
  Sextortion         = coercing someone with threats to release intimate images.

LAW ENFORCEMENT — file separately:
  FBI Internet Crime Complaint Center: https://ic3.gov
  Local police (cybercrime unit): bring your NCMEC tip number + evidence zip.
  These are separate from your NCMEC report — do all three.

CONFIDENTIALITY:
  Your identity as a reporter is protected. NCMEC does not publish reporter
  information. Law enforcement may contact you for follow-up.

IF THE CHILD IS IN IMMEDIATE DANGER:
  Call 911 or your local emergency number immediately.
  NCMEC hotline (24/7): 1-800-THE-LOST (1-800-843-5678)\
"""


# ── File writer ───────────────────────────────────────────────────────────────


def _write_guide(case_dir: Path, guide: ReportGuide, meta) -> Path:
    """Write the formatted guide to ncmec_guide.txt inside the case folder."""
    divider = "=" * 72

    sections = [
        divider,
        f"  AutoCatcher — {guide.title} Reporting Guide",
        "  ⚠  FOR CASES INVOLVING MINORS",
        divider,
        f"  Case ID:   {meta.case_id}",
        f"  Subject:   {meta.subject}",
        f"  Platform:  {meta.platform}",
        f"  Generated: {now_str()}",
    ]

    if not meta.minor_involved:
        sections += [
            "",
            "  NOTE: minor_involved is not set for this case.",
            "  Verify this applies before submitting to NCMEC.",
        ]

    sections += [
        divider,
        "",
        "SUBMISSION URL",
        "-" * 40,
        f"  {guide.submit_url}",
        "",
        "CHECKLIST — follow these steps in order",
        "-" * 40,
    ]

    for i, step in enumerate(guide.checklist, 1):
        prefix = f"  [{i}] "
        indent = "      "
        words = step.split()
        lines = []
        cur = prefix
        for word in words:
            if len(cur) + len(word) + 1 > 72 and cur.strip():
                lines.append(cur)
                cur = indent + word + " "
            else:
                cur += word + " "
        if cur.strip():
            lines.append(cur)
        sections.extend(lines)

    sections += [
        "",
        "FORM REFERENCE — have this ready when filling in cybertipline.org",
        "-" * 40,
        guide.template,
        "",
        "NOTES",
        "-" * 40,
        guide.notes,
        "",
        divider,
    ]

    path = case_dir / _GUIDE_FILE
    with open(path, "w") as f:
        f.write("\n".join(sections) + "\n")
    return path
