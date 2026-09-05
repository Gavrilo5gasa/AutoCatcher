"""
core/packager.py — Case packaging and PDF report generation.

Two things happen here:
  1. generate_pdf_report(case_dir)  — builds a report.pdf inside the case folder
  2. package_case(case_dir)         — verifies integrity, generates PDF, zips everything

The output zip is what you attach to Discord Trust & Safety, NCMEC, etc.
The PDF is a human-readable summary of all evidence with hash verification results.

Note: report.pdf is a DERIVED document, not original evidence.
      It is included in the zip but intentionally excluded from hashes.sha256.
"""

import sys
import zipfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    APP_NAME,
    APP_VERSION,
    ARCHIVED_LINKS_FILE,
    EVIDENCE_LOG_FILE,
    HASH_MANIFEST_FILE,
    METADATA_FILE,
    PACKAGES_DIR,
    REPORT_FILE,
    SUMMARY_FILE,
)
from core.archive import list_archived
from core.case import CaseMeta, load_case
from core.evidence import count_evidence, list_evidence
from core.hasher import verify_manifest
from utils.logger import get_logger
from utils.timestamp import now_slug, now_str

log = get_logger("packager")

# Evidence subdirectories to include
_EVIDENCE_DIRS = ["screenshots", "logs", "files", "archived"]


# ── Public API ────────────────────────────────────────────────────────────────


def package_case(case_dir: Path, out_dir: Path | None = None) -> Path:
    """
    Package a case into a distributable zip file.

    Steps:
      1. Verify manifest integrity (result goes into the PDF)
      2. Generate report.pdf inside the case folder
      3. Zip everything into packages/{case_id}_{timestamp}.zip

    out_dir  — where to write the zip (defaults to PACKAGES_DIR)
    Returns the path to the created zip file.
    """
    _, meta = load_case(case_dir.name)

    log.info(f"Packaging case: {meta.case_id}")

    # Step 1 — integrity check
    log.info("Verifying manifest...")
    verification = verify_manifest(case_dir)
    _log_verification(verification)

    # Step 2 — generate PDF (includes verification result)
    log.info("Generating PDF report...")
    pdf_path = generate_pdf_report(case_dir, verification=verification)
    log.info(f"PDF written: {pdf_path.name}")

    # Step 3 — zip it up
    out_dir = out_dir or PACKAGES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"{meta.case_id}_{now_slug()}.zip"
    zip_path = out_dir / zip_name

    _build_zip(case_dir, zip_path)
    log.info(f"Package ready: {zip_path}")

    return zip_path


def generate_pdf_report(
    case_dir: Path,
    verification: dict | None = None,
) -> Path:
    """
    Generate a PDF evidence report and write it to report.pdf inside case_dir.

    verification — optional pre-run result from verify_manifest().
                   If None, verification is run here automatically.
    Returns the path to the PDF.
    """
    _, meta = load_case(case_dir.name)
    evidence = list_evidence(case_dir)
    counts = count_evidence(case_dir)
    archived = list_archived(case_dir)
    verification = verification or verify_manifest(case_dir)

    pdf_path = case_dir / REPORT_FILE
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"AutoCatcher Report — {meta.case_id}",
        author=APP_NAME,
    )

    styles = _build_styles()
    story = []

    _section_header(story, styles, meta)
    _section_case_info(story, styles, meta, counts)
    _section_evidence_table(story, styles, evidence)
    _section_archived_links(story, styles, archived)
    _section_verification(story, styles, verification)
    _section_notes(story, styles, meta)
    _section_footer(story, styles)

    doc.build(story)
    return pdf_path


# ── PDF sections ──────────────────────────────────────────────────────────────


def _build_styles() -> dict:
    """Build all paragraph styles used in the PDF."""
    base = getSampleStyleSheet()
    return {
        "base": base,
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=18,
            spaceAfter=4,
            textColor=colors.HexColor("#1a1a2e"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=10,
            spaceAfter=2,
            textColor=colors.HexColor("#555555"),
        ),
        "section": ParagraphStyle(
            "section",
            fontName="Helvetica-Bold",
            fontSize=12,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e"),
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9, spaceAfter=3, leading=13
        ),
        "mono": ParagraphStyle(
            "mono", fontName="Courier", fontSize=7.5, spaceAfter=2, leading=11
        ),
        "warning": ParagraphStyle(
            "warning",
            fontName="Helvetica-Bold",
            fontSize=10,
            spaceAfter=4,
            textColor=colors.red,
        ),
        "ok": ParagraphStyle(
            "ok",
            fontName="Helvetica-Bold",
            fontSize=9,
            spaceAfter=4,
            textColor=colors.HexColor("#2e7d32"),
        ),
        "label": ParagraphStyle(
            "label", fontName="Helvetica-Bold", fontSize=9, spaceAfter=1
        ),
    }


def _divider(story: list) -> None:
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"))
    )
    story.append(Spacer(1, 0.3 * cm))


def _section_header(story: list, styles: dict, meta: CaseMeta) -> None:
    story.append(Paragraph(f"{APP_NAME} — Evidence Report", styles["title"]))
    story.append(
        Paragraph(
            f"Case ID: {meta.case_id}  ·  Generated: {now_str()}  ·  {APP_VERSION}",
            styles["subtitle"],
        )
    )
    _divider(story)

    # Minor warning — front and centre if applicable
    if meta.minor_involved:
        story.append(
            Paragraph(
                "⚠  MINOR INVOLVED — FILE WITH NCMEC CYBERTIPLINE",
                styles["warning"],
            )
        )
        story.append(
            Paragraph(
                "Visit cybertipline.org to submit a report. "
                "You may be legally required to do so.",
                styles["body"],
            )
        )
        story.append(Spacer(1, 0.3 * cm))


def _section_case_info(
    story: list,
    styles: dict,
    meta: CaseMeta,
    counts: dict,
) -> None:
    story.append(Paragraph("Case Information", styles["section"]))

    rows = [
        ["Case ID", meta.case_id],
        ["Subject", meta.subject],
        ["Platform", meta.platform],
        ["Created (UTC)", meta.created_at],
        ["Minor Involved", "YES — SEE WARNING ABOVE" if meta.minor_involved else "No"],
        ["Tags", ", ".join(meta.tags) if meta.tags else "—"],
        ["Screenshots", str(counts.get("screenshot", 0))],
        ["Log files", str(counts.get("log", 0))],
        ["Other files", str(counts.get("file", 0))],
    ]

    table = Table(rows, colWidths=[4 * cm, 13 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#444444")),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [colors.HexColor("#f5f5f5"), colors.white],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                # Highlight the minor row red if applicable
                *(
                    [
                        ("TEXTCOLOR", (1, 4), (1, 4), colors.red),
                        ("FONTNAME", (1, 4), (1, 4), "Helvetica-Bold"),
                    ]
                    if meta.minor_involved
                    else []
                ),
            ]
        )
    )
    story.append(table)


def _section_evidence_table(
    story: list,
    styles: dict,
    evidence: list,
) -> None:
    story.append(Paragraph("Evidence", styles["section"]))

    if not evidence:
        story.append(
            Paragraph("No evidence has been added to this case.", styles["body"])
        )
        return

    header = ["Type", "Filename", "Description / Source", "SHA256 (first 16)"]
    rows = [header]
    for e in evidence:
        desc_source = e.description
        if e.source:
            desc_source += f"\n[{e.source}]"
        rows.append(
            [
                e.type,
                Paragraph(e.filename, styles["mono"]),
                Paragraph(desc_source or "—", styles["body"]),
                Paragraph(e.sha256[:16] + "…", styles["mono"]),
            ]
        )

    col_widths = [2.2 * cm, 5.5 * cm, 6.5 * cm, 3.0 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                # Data rows
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#f9f9f9"), colors.white],
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ]
        )
    )
    story.append(table)
    story.append(
        Paragraph(
            "Full SHA256 hashes are in hashes.sha256 — verifiable with: "
            "<font name='Courier'>sha256sum --check hashes.sha256</font>",
            styles["body"],
        )
    )


def _section_archived_links(
    story: list,
    styles: dict,
    archived: list,
) -> None:
    story.append(Paragraph("Archived URLs", styles["section"]))

    if not archived:
        story.append(Paragraph("No URLs were archived for this case.", styles["body"]))
        return

    for line in archived:
        story.append(Paragraph(line, styles["mono"]))


def _section_verification(
    story: list,
    styles: dict,
    verification: dict,
) -> None:
    story.append(Paragraph("Integrity Verification", styles["section"]))

    ok = len(verification.get("ok", []))
    failed = len(verification.get("failed", []))
    missing = len(verification.get("missing", []))
    total = ok + failed + missing

    if total == 0:
        story.append(
            Paragraph(
                "No files in manifest — no evidence has been hashed yet.",
                styles["body"],
            )
        )
        return

    if failed == 0 and missing == 0:
        story.append(
            Paragraph(
                f"✓  All {ok} file(s) verified — hashes match. Evidence is intact.",
                styles["ok"],
            )
        )
    else:
        story.append(
            Paragraph(
                f"✗  Verification issues detected — {ok} OK, "
                f"{failed} FAILED, {missing} MISSING (of {total} total)",
                styles["warning"],
            )
        )
        if verification["failed"]:
            story.append(
                Paragraph(
                    "Files with hash mismatch (possible tampering):", styles["label"]
                )
            )
            for f in verification["failed"]:
                story.append(Paragraph(f"  • {f}", styles["mono"]))
        if verification["missing"]:
            story.append(
                Paragraph("Files listed in manifest but not on disk:", styles["label"])
            )
            for f in verification["missing"]:
                story.append(Paragraph(f"  • {f}", styles["mono"]))


def _section_notes(story: list, styles: dict, meta: CaseMeta) -> None:
    if not meta.notes:
        return
    story.append(Paragraph("Notes", styles["section"]))
    for line in meta.notes.splitlines():
        story.append(Paragraph(line or " ", styles["body"]))


def _section_footer(story: list, styles: dict) -> None:
    _divider(story)
    story.append(
        Paragraph(
            f"This report was generated by {APP_NAME} {APP_VERSION}. "
            "It is a summary document derived from the evidence files in this package. "
            "Original files and their SHA256 hashes are authoritative.",
            styles["subtitle"],
        )
    )


# ── Zip builder ───────────────────────────────────────────────────────────────


def _build_zip(case_dir: Path, zip_path: Path) -> None:
    """
    Zip the entire case into a distributable archive.

    Includes ALL root-level files (case_meta.json, hashes.sha256, report.pdf,
    reporter guides, etc.) plus all evidence subdirectories. Future-proof —
    any new file written to the case root is automatically included.

    The zip preserves the case folder as a top-level directory so the
    recipient gets a clean named folder on extract.
    """
    case_name = case_dir.name
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # All root-level files (guides, manifests, metadata, report, etc.)
        for path in sorted(case_dir.iterdir()):
            if path.is_file():
                zf.write(path, arcname=f"{case_name}/{path.name}")
                file_count += 1

        # Evidence subdirectories
        for subdir_name in _EVIDENCE_DIRS:
            subdir = case_dir / subdir_name
            if subdir.exists():
                for file in sorted(subdir.iterdir()):
                    if file.is_file():
                        zf.write(file, arcname=f"{case_name}/{subdir_name}/{file.name}")
                        file_count += 1

    log.info(f"Zip contains {file_count} file(s): {zip_path.name}")


# ── Internal helpers ──────────────────────────────────────────────────────────


def _log_verification(verification: dict) -> None:
    ok = len(verification.get("ok", []))
    failed = len(verification.get("failed", []))
    missing = len(verification.get("missing", []))
    if failed or missing:
        log.warning(
            f"Manifest verification: {ok} OK, {failed} FAILED, {missing} MISSING"
        )
    else:
        log.info(f"Manifest verification: all {ok} file(s) OK")
