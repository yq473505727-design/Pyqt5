from __future__ import annotations

from pathlib import Path

import card_io


def parse_datetime(value):
    return card_io.parse_datetime(value)


def read_simcp_to_table(simcp_path, table):
    class TableOnlyUi:
        pass

    ui = TableOnlyUi()
    ui.tableWidget_17 = table
    card_io.read_simcp(Path(simcp_path), ui)


def read_gcp_to_ui(gcp_path, ui):
    card_io.read_gcp(Path(gcp_path), ui)


def read_lcp_to_ui(lcp_path, ui):
    card_io.read_lcp(Path(lcp_path), ui)


def read_stacp_to_ui(stacp_path, ui):
    card_io.read_stacp(Path(stacp_path), ui)
