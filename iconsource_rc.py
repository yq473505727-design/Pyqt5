from __future__ import annotations

from pathlib import Path


ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def icon_path(name: str) -> str:
    return str(ICONS_DIR / name)


def qInitResources():
    return None


def qCleanupResources():
    return None
