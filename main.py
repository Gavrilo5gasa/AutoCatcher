"""
main.py — AutoCatcher CLI entry point.

Phase 1.6 — Typer-based CLI interface.

Usage:
    python main.py --help
    python main.py case new
    python main.py case list
    python main.py evidence add <case-id> <file>
    python main.py evidence screenshot <case-id>
    python main.py archive <case-id> <url>
    python main.py package <case-id>
    python main.py report discord <case-id>
    python main.py report ncmec <case-id>
    python main.py report generic <case-id>
    python main.py verify <case-id>
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

sys.path.insert(0, str(Path(__file__).parent))

from config import APP_NAME, APP_PHASE, APP_VERSION, CASES_DIR, PACKAGES_DIR
from core.archive import archive_url, list_archived
from core.case import (
    append_note,
    create_case,
    list_cases,
    load_case,
)
from core.evidence import (
    add_evidence,
    count_evidence,
    list_evidence,
)
from core.hasher import verify_manifest
from core.packager import generate_pdf_report, package_case
from reporters import discord as rep_discord
from reporters import generic as rep_generic
from reporters import ncmec as rep_ncmec
from utils.platform import capture_screenshot
from utils.timestamp import now_slug

# ── App setup ─────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="autocatcher",
    help=(
        f"[bold]{APP_NAME}[/bold] — Evidence collection & reporting tool "
        "for online predator documentation."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)

case_app = typer.Typer(help="Manage cases.", no_args_is_help=True)
ev_app = typer.Typer(help="Add and list evidence.", no_args_is_help=True)
rep_app = typer.Typer(help="Generate reporting guides.", no_args_is_help=True)

app.add_typer(case_app, name="case")
app.add_typer(ev_app, name="evidence")
app.add_typer(rep_app, name="report")

console = Console()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ok(msg: str) -> None:
    rprint(f"[bold green]✓[/bold green]  {msg}")


def _err(msg: str) -> None:
    rprint(f"[bold red]✗[/bold red]  {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    rprint(f"[bold yellow]![/bold yellow]  {msg}")


def _info(msg: str) -> None:
    rprint(f"[dim]→[/dim]  {msg}")


def _resolve_case(case_id: str):
    """Load a case or exit with a friendly error."""
    try:
        return load_case(case_id)
    except FileNotFoundError:
        _err(f"No case found with ID: [bold]{case_id}[/bold]")
        _info(f"Run [bold]autocatcher case list[/bold] to see available cases.")
        raise typer.Exit(1)


# ── app-level callbacks ────────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"[bold]{APP_NAME}[/bold]  {APP_VERSION}  ({APP_PHASE})")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """
    [bold]AutoCatcher[/bold] — collect, hash, and report online predator evidence.

    Run any subcommand with [bold]--help[/bold] for details.
    """


# ── case commands ─────────────────────────────────────────────────────────────


@case_app.command("new")
def case_new(
    subject: str = typer.Option(
        ...,
        "--subject",
        "-s",
        prompt="Subject username / handle",
        help="Username or handle of the subject being documented.",
    ),
    platform: str = typer.Option(
        ...,
        "--platform",
        "-p",
        prompt="Platform",
        help='Platform where the contact occurred (e.g. "discord", "twitter").',
    ),
    minor: bool = typer.Option(
        False,
        "--minor",
        help="Flag if a minor is involved. Enables NCMEC warnings throughout.",
    ),
    notes: str = typer.Option(
        "", "--notes", "-n", help="Optional opening notes for the case."
    ),
) -> None:
    """Create a new evidence case."""
    case_dir = create_case(
        subject=subject,
        platform=platform,
        notes=notes,
        minor_involved=minor,
    )
    _, meta = load_case(case_dir.name)

    _ok(f"Case created:  [bold]{meta.case_id}[/bold]")
    _info(f"Folder:  {case_dir}")

    if meta.minor_involved:
        console.print()
        console.print(
            Panel(
                "[bold red]⚠  MINOR INVOLVED[/bold red]\n"
                "You must also file a report with the NCMEC CyberTipline.\n"
                "Run:  [bold]autocatcher report ncmec {case_id}[/bold]".format(
                    case_id=meta.case_id
                ),
                border_style="red",
            )
        )


@case_app.command("list")
def case_list() -> None:
    """List all cases, newest first."""
    cases = list_cases()

    if not cases:
        _warn("No cases found.")
        _info(f"Start one with:  [bold]autocatcher case new[/bold]")
        return

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Case ID", style="cyan", no_wrap=True)
    table.add_column("Subject", style="white")
    table.add_column("Platform", style="dim")
    table.add_column("Minor", justify="center")
    table.add_column("Created (UTC)", style="dim", no_wrap=True)

    for meta in cases:
        minor_flag = (
            Text("⚠ YES", style="bold red")
            if meta.minor_involved
            else Text("no", style="dim")
        )
        table.add_row(
            meta.case_id,
            meta.subject,
            meta.platform,
            minor_flag,
            meta.created_at,
        )

    console.print(table)
    console.print(f"\n[dim]{len(cases)} case(s) in {CASES_DIR}[/dim]")


@case_app.command("show")
def case_show(
    case_id: str = typer.Argument(..., help="Case ID to inspect."),
) -> None:
    """Show full details for a single case."""
    case_dir, meta = _resolve_case(case_id)
    counts = count_evidence(case_dir)
    archived = list_archived(case_dir)

    console.print()
    console.print(
        Panel(
            f"[bold]{meta.case_id}[/bold]",
            subtitle=f"{APP_NAME} Case",
            border_style="cyan",
        )
    )

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold dim", no_wrap=True)
    table.add_column("Value")

    table.add_row("Subject", meta.subject)
    table.add_row("Platform", meta.platform)
    table.add_row("Created", meta.created_at)
    table.add_row(
        "Minor",
        "[bold red]YES — file with NCMEC[/bold red]" if meta.minor_involved else "No",
    )
    table.add_row("Tags", ", ".join(meta.tags) if meta.tags else "—")
    table.add_row("Screenshots", str(counts.get("screenshot", 0)))
    table.add_row("Logs", str(counts.get("log", 0)))
    table.add_row("Files", str(counts.get("file", 0)))
    table.add_row("Archived URLs", str(len(archived)))
    table.add_row("Folder", str(case_dir))

    console.print(table)

    if meta.notes:
        console.print()
        console.print("[bold]Notes[/bold]")
        for line in meta.notes.splitlines():
            console.print(f"  [dim]{line}[/dim]")


@case_app.command("note")
def case_note(
    case_id: str = typer.Argument(..., help="Case ID to add a note to."),
    note: str = typer.Option(
        ...,
        "--text",
        "-t",
        prompt="Note text",
        help="Text to append as a timestamped note.",
    ),
) -> None:
    """Append a timestamped note to an existing case."""
    case_dir, _ = _resolve_case(case_id)
    append_note(case_dir, note)
    _ok(f"Note appended to [bold]{case_id}[/bold].")


# ── evidence commands ─────────────────────────────────────────────────────────


@ev_app.command("add")
def evidence_add(
    case_id: str = typer.Argument(..., help="Case ID to add evidence to."),
    src: Path = typer.Argument(
        ...,
        help="Path to the file to add.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    kind: str = typer.Option(
        "screenshot",
        "--type",
        "-t",
        help='Evidence type: "screenshot", "log", or "file".',
    ),
    description: str = typer.Option(
        "", "--desc", "-d", help="What this evidence shows."
    ),
    source: str = typer.Option(
        "", "--source", "-s", help='Where it came from (e.g. "Discord #general", URL).'
    ),
) -> None:
    """Add a file as evidence to a case (screenshot, log, or file)."""
    valid_types = ("screenshot", "log", "file")
    if kind not in valid_types:
        _err(
            f"Invalid type [bold]{kind!r}[/bold]. Must be one of: {', '.join(valid_types)}"
        )
        raise typer.Exit(1)

    case_dir, _ = _resolve_case(case_id)

    try:
        record = add_evidence(case_dir, src, kind, description, source)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as e:
        _err(str(e))
        raise typer.Exit(1)

    _ok(f"Evidence added:  [bold]{record.filename}[/bold]")
    _info(f"Type:    {record.type}")
    _info(f"SHA256:  {record.sha256[:32]}…")
    if description:
        _info(f"Desc:    {description}")


@ev_app.command("list")
def evidence_list(
    case_id: str = typer.Argument(..., help="Case ID to inspect."),
) -> None:
    """List all evidence recorded for a case."""
    case_dir, meta = _resolve_case(case_id)
    evidence = list_evidence(case_dir)

    if not evidence:
        _warn(f"No evidence added to [bold]{case_id}[/bold] yet.")
        _info("Add some with:  [bold]autocatcher evidence add <case-id> <file>[/bold]")
        return

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Filename", style="white")
    table.add_column("Description")
    table.add_column("SHA256", style="dim", no_wrap=True)
    table.add_column("Added (UTC)", style="dim", no_wrap=True)

    for i, rec in enumerate(evidence, 1):
        table.add_row(
            str(i),
            rec.type,
            rec.filename,
            rec.description or "—",
            rec.sha256[:16] + "…",
            rec.added_at,
        )

    console.print(table)
    counts = count_evidence(case_dir)
    console.print(
        f"\n[dim]{len(evidence)} item(s) — "
        f"screenshots: {counts['screenshot']}, "
        f"logs: {counts['log']}, "
        f"files: {counts['file']}[/dim]"
    )


@ev_app.command("screenshot")
def evidence_screenshot(
    case_id: str = typer.Argument(..., help="Case ID to add the screenshot to."),
    description: str = typer.Option(
        "", "--desc", "-d", help="What this screenshot shows."
    ),
    source: str = typer.Option(
        "", "--source", "-s", help='Where it came from (e.g. "Discord #general").'
    ),
) -> None:
    """
    Capture the screen right now (Phase 4.1 — cross-platform: grim/scrot on
    Linux, screencapture on macOS, ImageGrab on Windows) and add it as
    evidence directly, skipping the manual screenshot-then-add-evidence step.
    """
    case_dir, _ = _resolve_case(case_id)

    tmp_path = case_dir / f"_capture_{now_slug()}.png"
    _info("Capturing screen…")
    result = capture_screenshot(tmp_path)

    if not result.ok:
        _err("Screenshot capture failed.")
        _info(result.error)
        raise typer.Exit(1)

    try:
        record = add_evidence(case_dir, result.path, "screenshot", description, source)
    finally:
        # add_evidence copies the file into screenshots/; clean up the
        # temporary capture regardless of whether that copy succeeded.
        result.path.unlink(missing_ok=True)

    _ok(f"Screenshot captured and added:  [bold]{record.filename}[/bold]")
    _info(f"SHA256:  {record.sha256[:32]}…")


# ── archive commands ──────────────────────────────────────────────────────────


@app.command("archive")
def archive(
    case_id: str = typer.Argument(..., help="Case ID to archive a URL for."),
    url: str = typer.Argument(..., help="URL to submit to the Wayback Machine."),
) -> None:
    """Archive a URL via the Wayback Machine and record it in the case."""
    case_dir, _ = _resolve_case(case_id)

    _info(f"Submitting to Wayback Machine…  [dim]{url}[/dim]")
    result = archive_url(case_dir, url)

    if result.status == "saved":
        _ok(f"Saved:  [link={result.archived_url}]{result.archived_url}[/link]")
    elif result.status == "exists":
        _ok(
            f"Already archived:  [link={result.archived_url}]{result.archived_url}[/link]"
        )
    else:
        _err(f"Archive failed for:  {url}")
        _info("The failure has been recorded in archived_links.txt.")
        raise typer.Exit(1)


@app.command("verify")
def verify(
    case_id: str = typer.Argument(..., help="Case ID to verify."),
) -> None:
    """Re-hash all evidence and verify integrity against the SHA256 manifest."""
    case_dir, _ = _resolve_case(case_id)

    _info("Re-hashing all evidence files…")
    results = verify_manifest(case_dir)

    ok = results.get("ok", [])
    failed = results.get("failed", [])
    missing = results.get("missing", [])
    total = len(ok) + len(failed) + len(missing)

    if total == 0:
        _warn("Manifest is empty — no files have been hashed yet.")
        return

    if not failed and not missing:
        _ok(
            f"All [bold]{len(ok)}[/bold] file(s) verified — hashes match. Evidence is intact."
        )
        return

    _err(
        f"Integrity issues:  "
        f"{len(ok)} OK,  {len(failed)} FAILED,  {len(missing)} MISSING  "
        f"(of {total} total)"
    )
    if failed:
        console.print("\n[bold red]Hash mismatch (possible tampering):[/bold red]")
        for f in failed:
            console.print(f"  [red]✗[/red]  {f}")
    if missing:
        console.print("\n[bold yellow]In manifest but not on disk:[/bold yellow]")
        for f in missing:
            console.print(f"  [yellow]?[/yellow]  {f}")

    raise typer.Exit(1)


# ── package command ───────────────────────────────────────────────────────────


@app.command("tui")
def tui() -> None:
    """Launch the Textual TUI (Phase 2)."""
    from tui.app import run as run_tui

    run_tui()


@app.command("gui")
def gui() -> None:
    """Launch the GTK4 desktop GUI (Phase 3). Requires PyGObject + GTK4."""
    try:
        from gui.app import run as run_gui
    except ImportError as e:
        _err(f"GTK4/PyGObject not available: {e}")
        _info("Debian/Ubuntu:  sudo apt install python3-gi gir1.2-gtk-4.0")
        _info("Arch:           sudo pacman -S python-gobject gtk4")
        raise typer.Exit(1)

    raise typer.Exit(run_gui())


@app.command("package")
def package(
    case_id: str = typer.Argument(..., help="Case ID to package."),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Directory to write the zip into (default: packages/).",
    ),
) -> None:
    """
    Verify integrity, generate a PDF report, and zip everything for submission.

    The resulting zip is what you attach to Discord T&S, NCMEC, or police.
    """
    case_dir, meta = _resolve_case(case_id)

    console.print()
    _info(f"Packaging case [bold]{case_id}[/bold]…")
    _info("Step 1/3 — verifying manifest integrity…")
    _info("Step 2/3 — generating PDF report…")
    _info("Step 3/3 — building zip…")
    console.print()

    try:
        zip_path = package_case(case_dir, out_dir=out)
    except Exception as e:
        _err(f"Packaging failed: {e}")
        raise typer.Exit(1)

    _ok(f"Package ready:  [bold]{zip_path.name}[/bold]")
    _info(f"Location:  {zip_path}")
    console.print()

    if meta.minor_involved:
        console.print(
            Panel(
                "[bold red]⚠  MINOR INVOLVED — submit to NCMEC FIRST[/bold red]\n"
                "cybertipline.org  —  then Discord / platform  —  then local police.",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                "Next steps:\n"
                f"  Report to platform:  [bold]autocatcher report discord {case_id}[/bold]\n"
                f"  Generic platform:    [bold]autocatcher report generic {case_id}[/bold]",
                border_style="cyan",
            )
        )


# ── report commands ───────────────────────────────────────────────────────────


@rep_app.command("discord")
def report_discord(
    case_id: str = typer.Argument(..., help="Case ID to generate a guide for."),
) -> None:
    """Generate a Discord Trust & Safety reporting guide for this case."""
    case_dir, meta = _resolve_case(case_id)

    guide = rep_discord.generate_guide(case_dir)

    _ok(f"Discord reporting guide written:  [bold]{guide.guide_path.name}[/bold]")
    _info(f"Submit at:  [link={guide.submit_url}]{guide.submit_url}[/link]")

    if meta.minor_involved:
        _warn(
            "MINOR INVOLVED — also run:  [bold]autocatcher report ncmec {case_id}[/bold]".format(
                case_id=case_id
            )
        )


@rep_app.command("ncmec")
def report_ncmec(
    case_id: str = typer.Argument(..., help="Case ID to generate a guide for."),
) -> None:
    """Generate an NCMEC CyberTipline reporting guide (for cases involving minors)."""
    case_dir, meta = _resolve_case(case_id)

    if not meta.minor_involved:
        _warn(
            "minor_involved is [bold]not set[/bold] for this case. "
            "NCMEC is intended for cases involving minors."
        )
        confirmed = typer.confirm("Generate the NCMEC guide anyway?", default=False)
        if not confirmed:
            raise typer.Exit()

    guide = rep_ncmec.generate_guide(case_dir)

    _ok(f"NCMEC guide written:  [bold]{guide.guide_path.name}[/bold]")
    _info(f"Submit at:  [link={guide.submit_url}]{guide.submit_url}[/link]")
    console.print()
    console.print(
        Panel(
            "[bold]After NCMEC:[/bold]\n"
            "  1. Report to the platform too (Discord, etc.)\n"
            "  2. File with local police or FBI IC3:  https://ic3.gov\n"
            "  3. Keep your NCMEC tip number — law enforcement needs it.",
            border_style="yellow",
        )
    )


@rep_app.command("generic")
def report_generic(
    case_id: str = typer.Argument(..., help="Case ID to generate a guide for."),
) -> None:
    """Generate a generic platform reporting guide for this case."""
    case_dir, meta = _resolve_case(case_id)

    guide = rep_generic.generate_guide(case_dir)

    _ok(f"Generic guide written:  [bold]{guide.guide_path.name}[/bold]")
    if guide.submit_url and not guide.submit_url.startswith("["):
        _info(f"Submit at:  [link={guide.submit_url}]{guide.submit_url}[/link]")
    else:
        _info("See the guide file for platform-specific submission URLs.")

    if meta.minor_involved:
        _warn(
            "MINOR INVOLVED — also run:  [bold]autocatcher report ncmec {case_id}[/bold]".format(
                case_id=case_id
            )
        )


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
