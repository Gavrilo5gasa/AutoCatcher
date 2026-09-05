"""
utils/platform.py — Phase 4.1: OS abstraction layer.

Every OS-specific call in AutoCatcher (screenshot capture, default folder
locations) goes through this module. Nothing in core/, gui/, or tui/ should
ever call `grim`, `screencapture`, etc. directly, or branch on
sys.platform itself — import from here instead so Windows/macOS support
(Phase 4.2/4.3) is a matter of filling in the branches below, not hunting
through the whole codebase.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from utils.logger import get_logger

log = get_logger("platform")

OSName = Literal["linux", "macos", "windows", "unknown"]


def current_os() -> OSName:
    """Return the current OS as one of our three supported names."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform in ("win32", "cygwin"):
        return "windows"
    return "unknown"


# ── Paths ─────────────────────────────────────────────────────────────────────

def default_evidence_dir() -> Path:
    """
    Best-guess folder to suggest when a user is asked to pick a screenshot
    or file (e.g. as placeholder/starting-directory text in a file picker).
    Falls back to the home directory if the OS-typical folder doesn't exist.
    """
    home = Path.home()
    os_name = current_os()

    if os_name == "windows":
        candidate = home / "Pictures"
    elif os_name == "macos":
        candidate = home / "Pictures"
    else:  # linux and unknown
        candidate = home / "Pictures"

    return candidate if candidate.is_dir() else home


def example_evidence_path() -> str:
    """
    OS-appropriate example path for UI placeholder text
    (file pickers in gui/dialogs.py and tui/widgets/*_modal.py).
    """
    os_name = current_os()
    base = default_evidence_dir()

    if os_name == "windows":
        return str(base / "proof.png").replace("/", "\\")
    return str(base / "proof.png")


# ── Screenshot capture ──────────────────────────────────────────────────────

@dataclass
class ScreenshotResult:
    ok: bool
    path: Path | None
    error: str = ""


def screenshot_tool_available() -> bool:
    """Whether we have a way to take a screenshot at all on this OS/session."""
    os_name = current_os()

    if os_name == "linux":
        # Wayland: grim. X11: fall back to scrot or import (ImageMagick).
        return any(shutil.which(tool) for tool in ("grim", "scrot", "import"))
    if os_name == "macos":
        return shutil.which("screencapture") is not None
    if os_name == "windows":
        # No external tool needed — capture_screenshot uses PIL.ImageGrab,
        # which ships with Pillow (already a dependency via reportlab chain
        # is NOT guaranteed; Pillow is pulled in transitively but not
        # declared — see requirements.txt note in Phase 4.2).
        try:
            import PIL.ImageGrab  # noqa: F401
            return True
        except ImportError:
            return False
    return False


def capture_screenshot(out_path: Path) -> ScreenshotResult:
    """
    Capture the full screen (or let the user interactively select a region,
    where supported) and save it to out_path. out_path's parent directory
    must already exist.

    This is a best-effort capture meant for quickly grabbing evidence from
    the desktop session AutoCatcher itself is running in — it is not a
    replacement for archiving (core/archive.py), which is what preserves
    evidence that lives on someone else's server.
    """
    os_name = current_os()
    out_path = out_path.resolve()

    if os_name == "linux":
        return _capture_linux(out_path)
    if os_name == "macos":
        return _capture_macos(out_path)
    if os_name == "windows":
        return _capture_windows(out_path)

    return ScreenshotResult(
        ok=False,
        path=None,
        error=f"Screenshot capture isn't supported on this platform ({sys.platform}).",
    )


def _capture_linux(out_path: Path) -> ScreenshotResult:
    # Prefer grim (Wayland/wlroots — Hyprland, Sway, etc.)
    if shutil.which("grim"):
        try:
            subprocess.run(["grim", str(out_path)], check=True, capture_output=True)
            return ScreenshotResult(ok=True, path=out_path)
        except subprocess.CalledProcessError as e:
            log.warning("grim failed: %s", e.stderr.decode(errors="replace"))

    # X11 fallbacks
    if shutil.which("scrot"):
        try:
            subprocess.run(["scrot", str(out_path)], check=True, capture_output=True)
            return ScreenshotResult(ok=True, path=out_path)
        except subprocess.CalledProcessError as e:
            log.warning("scrot failed: %s", e.stderr.decode(errors="replace"))

    if shutil.which("import"):  # ImageMagick
        try:
            subprocess.run(
                ["import", "-window", "root", str(out_path)],
                check=True,
                capture_output=True,
            )
            return ScreenshotResult(ok=True, path=out_path)
        except subprocess.CalledProcessError as e:
            log.warning("import (ImageMagick) failed: %s", e.stderr.decode(errors="replace"))

    return ScreenshotResult(
        ok=False,
        path=None,
        error=(
            "No screenshot tool found. Install one of:\n"
            "  Wayland (Hyprland/Sway):  sudo apt install grim\n"
            "  X11:                      sudo apt install scrot"
        ),
    )


def _capture_macos(out_path: Path) -> ScreenshotResult:
    if not shutil.which("screencapture"):
        return ScreenshotResult(
            ok=False, path=None, error="`screencapture` not found (unexpected on macOS)."
        )
    try:
        # -x: no camera sound. Full screen; interactive region select is
        # -i but we default to full-screen for unattended/scripted use.
        subprocess.run(["screencapture", "-x", str(out_path)], check=True, capture_output=True)
        return ScreenshotResult(ok=True, path=out_path)
    except subprocess.CalledProcessError as e:
        return ScreenshotResult(ok=False, path=None, error=e.stderr.decode(errors="replace"))


def _capture_windows(out_path: Path) -> ScreenshotResult:
    try:
        from PIL import ImageGrab
    except ImportError:
        return ScreenshotResult(
            ok=False,
            path=None,
            error="Pillow is required for screenshots on Windows: pip install Pillow",
        )
    try:
        image = ImageGrab.grab()
        image.save(out_path)
        return ScreenshotResult(ok=True, path=out_path)
    except Exception as e:  # noqa: BLE001 — surfacing any capture failure to the caller
        return ScreenshotResult(ok=False, path=None, error=str(e))
