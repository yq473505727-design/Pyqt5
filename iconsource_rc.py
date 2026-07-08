from __future__ import annotations

from pathlib import Path


ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def icon_path(name: str) -> str:
    """返回指定图标文件在 assets/icons 目录下的绝对路径字符串。"""
    return str(ICONS_DIR / name)


def qInitResources():
    """兼容 Qt 资源初始化接口；当前图标通过文件路径加载。"""
    return None


def qCleanupResources():
    """兼容 Qt 资源清理接口；当前没有需要释放的 Qt 资源。"""
    return None
