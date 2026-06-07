from __future__ import annotations

from pathlib import Path

import card_io


def save_gcp_from_ui(ui, save_path):
    card_io.save_gcp(ui, Path(save_path))


def save_lcp_from_ui(ui, save_path):
    card_io.save_lcp(ui, Path(save_path))


def save_simcp_from_ui(ui, save_path):
    card_io.save_simcp(ui, Path(save_path))


def save_stacp_from_ui(ui, save_path):
    card_io.save_stacp(ui, Path(save_path))


def get_item_text(item):
    return item.text().strip() if item else ""
