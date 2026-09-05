"""
reporters/discord.py — Discord Trust & Safety reporting guide.

Generates a step-by-step guide and submission template for reporting
a subject to Discord's Trust & Safety team.

Submission URL: https://dis.gd/report
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.case import load_case
from utils.logger import get_logger
from utils.timestamp import now_str

from reporters import ReportGuide

log = get_logger("reporter.discord")

_PLATFORM = "discord"
_TITLE = "Discord Trust & Safety"
_SUBMIT_URL = "https://dis.gd/report"
_GUIDE_FILE = "discord_guide.txt"


# ── Public API ────────────────────────────────────────────────────────────────


def generate_guide(case_dir: Path) -> ReportGuide:
    """
    Generate a Discord reporting guide for this case.
    Writes discord_guide.txt into the case folder.
    Returns a ReportGuide with all structured content.
    """
    _, meta = load_case(case_dir.name)

    checklist = _build_checklist(meta)
    template = _build_template(meta)
    notes = _build_notes(meta)

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

    log.info(f"Discord guide written: {guide_path.name}")
    return guide


# ── Guide content ─────────────────────────────────────────────────────────────


def _build_checklist(meta) -> list[str]:
    steps = [
        f"Archive the subject's Discord profile page BEFORE submitting — "
        f"accounts are deleted after a report is processed.",
        f"Confirm the subject's full username: {meta.subject!r}. "
        f"Note their User ID too if you can find it "
        f"(right-click username → Copy User ID with Developer Mode enabled).",
        "Note every server name where the contact occurred. "
        "Discord T&S can only act on servers they can identify.",
        "Package your evidence using AutoCatcher's package command. "
        "The zip contains your screenshots, logs, and the SHA256 manifest.",
        f"Submit the report at {_SUBMIT_URL}. "
        f"Select the violation type that best fits (see notes below).",
        "Attach your evidence zip to the report form.",
        "Save the ticket/confirmation number Discord gives you.",
    ]
    if meta.minor_involved:
        steps.insert(
            0,
            "⚠  MINOR INVOLVED — also submit a CyberTipline report to NCMEC "
            "at cybertipline.org. Run: autocatcher report ncmec",
        )
    return steps


def _build_template(meta) -> str:
    minor_line = (
        "\n⚠ A minor is involved in this case. I have also filed a report "
        "with the NCMEC CyberTipline.\n"
        if meta.minor_involved
        else ""
    )
    return f"""\
I am reporting the Discord user {meta.subject!r} for [DESCRIBE VIOLATION — e.g. \
grooming / solicitation / sharing explicit content / harassment].
{minor_line}
Reported User:      {meta.subject}
User ID (if known): [PASTE ID OR REMOVE THIS LINE]
Server(s):          [LIST SERVERS WHERE CONTACT OCCURRED, OR "Direct Messages"]
Date(s):            [EARLIEST DATE] to [LATEST DATE]

Summary:
[Describe what happened in plain factual language. One to three sentences. \
Stick to what occurred and when — avoid emotional language. Example: \
"The subject contacted me via DMs on [date] and repeatedly requested \
explicit images over the course of [duration]."]

I have collected evidence using AutoCatcher (Case ID: {meta.case_id}). \
The package includes timestamped screenshots, exported chat logs, \
and archived profile URLs. All files have been SHA256-hashed for \
integrity verification. I am attaching the evidence zip to this report.

Please let me know if you need additional information.\
"""


def _build_notes(meta) -> str:
    notes = """\
VIOLATION TYPE — select the best match on the Discord form:
  - "Harassment or Bullying"           → targeted harassment, hate speech
  - "Sharing someone's personal info"  → doxxing
  - "Sexual content involving minors"  → CSAM, grooming, solicitation of minors
  - "Threatening to share private images" → non-consensual intimate images
  - "Spam or misleading content"       → scam accounts, impersonation

TIPS:
  - Include the User ID if possible — usernames can be changed, IDs cannot.
  - If the abuse happened in a server, include the Server ID too
    (right-click server icon → Copy Server ID).
  - Discord T&S response times vary. If no response within 5 business days,
    follow up by replying to your ticket confirmation email.
  - For immediate physical danger, contact local law enforcement first.\
"""
    if meta.minor_involved:
        notes = (
            "⚠  MINOR INVOLVED — you MUST also report to NCMEC CyberTipline.\n"
            "   cybertipline.org\n\n"
        ) + notes
    return notes


# ── File writer ───────────────────────────────────────────────────────────────


def _write_guide(case_dir: Path, guide: ReportGuide, meta) -> Path:
    """Write the formatted guide to discord_guide.txt inside the case folder."""
    divider = "=" * 72

    sections = [
        divider,
        f"  AutoCatcher — {guide.title} Reporting Guide",
        divider,
        f"  Case ID:   {meta.case_id}",
        f"  Subject:   {meta.subject}",
        f"  Platform:  {meta.platform}",
        f"  Generated: {now_str()}",
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
        # Wrap long steps at 68 chars
        prefix = f"  [{i}] "
        indent = "      "
        words = step.split()
        lines = []
        cur_line = prefix
        for word in words:
            if len(cur_line) + len(word) + 1 > 72 and cur_line.strip():
                lines.append(cur_line)
                cur_line = indent + word + " "
            else:
                cur_line += word + " "
        if cur_line.strip():
            lines.append(cur_line)
        sections.extend(lines)

    sections += [
        "",
        "REPORT TEMPLATE — copy and paste into the submission form",
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
