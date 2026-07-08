from __future__ import annotations

from pathlib import Path

import card_io


def save_gcp_from_ui(ui, save_path):
    """从当前界面导出 GCP 全局参数卡片。"""
    card_io.save_gcp(ui, Path(save_path))


def save_lcp_from_ui(ui, save_path):
    """从当前界面导出 LCP 弧段参数卡片。"""
    card_io.save_lcp(ui, Path(save_path))


def save_simcp_from_ui(ui, save_path):
    """从当前界面导出 SimCP 模拟观测卡片。"""
    card_io.save_simcp(ui, Path(save_path))


def save_stacp_from_ui(ui, save_path):
    """从当前界面导出 StaCP 测站参数卡片。"""
    card_io.save_stacp(ui, Path(save_path))


def get_item_text(item):
    """安全获取表格项文本，空项返回空字符串。"""
    return item.text().strip() if item else ""
