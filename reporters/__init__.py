"""
reporters/__init__.py — Shared types for all reporter modules.

Every reporter (discord, ncmec, generic) returns a ReportGuide.
The CLI (Phase 1.6) uses this to print guides and open URLs consistently.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReportGuide:
    """
    Structured output from a reporter module.

    platform    — reporter key: "discord" | "ncmec" | "generic"
    title       — human-readable title for display
    submit_url  — primary URL where the report is submitted
    checklist   — ordered list of steps to follow
    template    — copy-paste text for the submission form
    notes       — extra guidance that doesn't fit the above
    guide_path  — path to the .txt file written inside the case folder
    """
    platform:   str
    title:      str
    submit_url: str
    checklist:  list[str]
    template:   str
    notes:      str
    guide_path: Path | None = None
