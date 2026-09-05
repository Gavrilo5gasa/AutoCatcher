"""
gui — AutoCatcher Phase 3 GTK4 desktop interface (PyGObject, native Wayland).

Entry points:
    python main.py gui        (preferred — via the Typer CLI)
    python -m gui.app         (direct)

Requires system packages, not pip-installable:
    sudo pacman -S python-gobject gtk4          (Arch)
    sudo apt install python3-gi gir1.2-gtk-4.0  (Debian/Ubuntu)
"""
