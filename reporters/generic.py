"""
reporters/generic.py — Generic platform reporting guide.

For platforms not covered by a dedicated reporter (Twitter/X, Instagram,
Roblox, Steam, etc.). Produces a universal checklist and template that
works for any platform's abuse/safety reporting form.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.case import load_case
from utils.logger import get_logger
from utils.timestamp import now_str

from reporters import ReportGuide

log = get_logger("reporter.generic")

_PLATFORM = "generic"
_TITLE = "Generic Platform Report"
_GUIDE_FILE = "generic_guide.txt"

# Known platform safety pages — used to give a more specific URL when possible
_PLATFORM_URLS: dict[str, str] = {
    "twitter": "https://help.twitter.com/forms/report_abuse",
    "x": "https://help.twitter.com/forms/report_abuse",
    "instagram": "https://help.instagram.com/contact/383679321740945",
    "tiktok": "https://support.tiktok.com/en/safety-hc/report-a-problem",
    "roblox": "https://en.help.roblox.com/hc/en-us/articles/203312410",
    "steam": "https://help.steampowered.com/en/faqs/view/4DE7-E4F5-8C92-3D80",
    "twitch": "https://safety.twitch.tv/s/article/How-to-file-a-User-Report",
    "youtube": "https://support.google.com/youtube/answer/2802027",
    "snapchat": "https://support.snapchat.com/en-US/article/report-abuse",
    "telegram": "https://telegram.org/faq#how-do-i-report-a-user",
    "reddit": "https://support.reddithelp.com/hc/en-us/articles/360058309512",
}


# ── Public API ────────────────────────────────────────────────────────────────


def generate_guide(case_dir: Path) -> ReportGuide:
    """
    Generate a generic platform reporting guide for this case.
    Writes generic_guide.txt into the case folder.
    If the case platform matches a known entry, includes its specific URL.
    """
    _, meta = load_case(case_dir.name)

    submit_url = _PLATFORM_URLS.get(meta.platform.lower(), "")
    checklist = _build_checklist(meta, submit_url)
    template = _build_template(meta)
    notes = _build_notes(meta)

    guide = ReportGuide(
        platform=_PLATFORM,
        title=_TITLE,
        submit_url=submit_url or "[find your platform's reporting page — see notes]",
        checklist=checklist,
        template=template,
        notes=notes,
    )

    guide_path = _write_guide(case_dir, guide, meta, submit_url)
    guide.guide_path = guide_path

    log.info(f"Generic guide written: {guide_path.name}")
    return guide


# ── Guide content ─────────────────────────────────────────────────────────────


def _build_checklist(meta, submit_url: str) -> list[str]:
    platform_str = meta.platform.title()

    url_step = (
        f"Submit the report at: {submit_url}"
        if submit_url
        else f'Find the reporting page by searching "{platform_str} report abuse" '
        f"or checking the platform's Help / Safety centre."
    )

    steps = [
        f"Archive the subject's {platform_str} profile page BEFORE reporting. "
        "Accounts are typically suspended after a successful report, which "
        "deletes the profile. Use AutoCatcher's archive command or "
        "web.archive.org/save/ manually.",
        "Note the exact username or account identifier: "
        f"{meta.subject!r}. Also note the user ID if the platform exposes it.",
        "Identify which community guideline or terms of service the subject "
        "violated. Most platforms have a violation type dropdown — "
        "pick the most specific match.",
        "Package your evidence using AutoCatcher. The zip contains screenshots, "
        "logs, archived links, and a SHA256 integrity manifest.",
        url_step,
        "Attach your evidence zip if the platform's form allows uploads. "
        "If not, note in the report that you have an evidence package "
        "and provide your email so they can request it.",
        "Save the report confirmation or ticket number the platform gives you.",
        "If the platform does not respond within 5–7 business days, "
        "follow up by replying to your confirmation email or re-submitting.",
    ]

    if meta.minor_involved:
        steps.insert(
            0,
            "⚠  MINOR INVOLVED — also report to NCMEC CyberTipline at "
            "cybertipline.org AND to local law enforcement. "
            "Run: autocatcher report ncmec",
        )

    return steps


def _build_template(meta) -> str:
    minor_line = (
        "\n⚠ A minor is involved. I have also filed a report with the "
        "NCMEC CyberTipline (cybertipline.org).\n"
        if meta.minor_involved
        else ""
    )
    return f"""\
I am reporting the account {meta.subject!r} on {meta.platform.title()} \
for [DESCRIBE VIOLATION — be specific about which policy was broken].
{minor_line}
Account / Username: {meta.subject}
User ID (if known): [PASTE OR REMOVE]
Date(s) of incident: [EARLIEST DATE] to [LATEST DATE]
Where it occurred: [channel, chat room, DMs, public profile, etc.]

Description:
[Describe what happened factually. Stick to observable actions and \
direct quotes where relevant. Avoid emotional language — platforms \
respond better to factual reports. Example: "This user contacted me \
on [date] via [feature], sent [describe content], and [describe \
escalation]. This continued for [duration]."]

Evidence:
I have collected evidence using AutoCatcher (Case ID: {meta.case_id}), \
including timestamped screenshots, chat logs, and archived URLs. \
All files have been SHA256-hashed for integrity verification. \
[Attach the zip if supported, or note it is available on request.]\
"""


def _build_notes(meta) -> str:
    platform = meta.platform.lower()

    known_url = _PLATFORM_URLS.get(platform)
    url_note = (
        f"  {meta.platform.title()} reporting page: {known_url}"
        if known_url
        else f'  Search: "{meta.platform.title()} report abuse" or '
        f'"[platform] trust and safety contact"'
    )

    return f"""\
FINDING THE REPORTING PAGE:
{url_note}
  Tip: on most platforms you can also report directly from the user's
  profile by clicking ⋯ (more options) → Report.

WRITING AN EFFECTIVE REPORT:
  - Be specific: "sent explicit image on [date] via DMs" beats "was inappropriate"
  - Cite the rule: "This violates your policy on [X]" improves response rates
  - Stay factual: platforms are more responsive to factual reports than
    emotional ones — keep it to what happened, when, and where
  - Include your Case ID: {meta.case_id}

IF THE PLATFORM DOESN'T RESPOND:
  - Follow up after 5–7 business days
  - Escalate to law enforcement if there are threats of physical harm
  - In the US, the FBI's IC3 (ic3.gov) handles online crime reports
  - For minors: NCMEC CyberTipline (cybertipline.org) regardless of platform

KNOWN PLATFORM SAFETY PAGES:
  Twitter/X:  https://help.twitter.com/forms/report_abuse
  Instagram:  https://help.instagram.com/contact/383679321740945
  TikTok:     https://support.tiktok.com/en/safety-hc/report-a-problem
  Roblox:     https://en.help.roblox.com/hc/en-us/articles/203312410
  Twitch:     https://safety.twitch.tv/s/article/How-to-file-a-User-Report
  Snapchat:   https://support.snapchat.com/en-US/article/report-abuse\
"""


# ── File writer ───────────────────────────────────────────────────────────────


def _write_guide(case_dir: Path, guide: ReportGuide, meta, submit_url: str) -> Path:
    """Write the formatted guide to generic_guide.txt inside the case folder."""
    divider = "=" * 72

    platform_str = meta.platform.title()
    url_display = submit_url or "[see notes below for your platform's URL]"

    sections = [
        divider,
        f"  AutoCatcher — {guide.title}",
        f"  Platform: {platform_str}",
        divider,
        f"  Case ID:   {meta.case_id}",
        f"  Subject:   {meta.subject}",
        f"  Generated: {now_str()}",
        divider,
        "",
        "SUBMISSION URL",
        "-" * 40,
        f"  {url_display}",
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
