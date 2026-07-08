from __future__ import annotations

from pathlib import Path

import card_io


def parse_datetime(value):
    """把卡片中的时间文本转换为 Qt 日期时间对象。"""
    return card_io.parse_datetime(value)


def read_simcp_to_table(simcp_path, table):
    """把 SimCP 模拟观测卡片读取到指定表格控件中。"""
    class TableOnlyUi:
        """为只读 SimCP 表格提供最小 UI 适配对象。"""
        pass

    ui = TableOnlyUi()
    ui.tableWidget_17 = table
    card_io.read_simcp(Path(simcp_path), ui)


def read_gcp_to_ui(gcp_path, ui):
    """把 GCP 全局参数卡片读取并填充到界面对象。"""
    card_io.read_gcp(Path(gcp_path), ui)


def read_lcp_to_ui(lcp_path, ui):
    """把 LCP 弧段参数卡片读取并填充到界面对象。"""
    card_io.read_lcp(Path(lcp_path), ui)


def read_stacp_to_ui(stacp_path, ui):
    """把 StaCP 测站参数卡片读取并填充到界面对象。"""
    card_io.read_stacp(Path(stacp_path), ui)
