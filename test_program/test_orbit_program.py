"""用于验证定轨界面实时捕获外部程序输出的测试程序。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


CARD_NAMES = ("GCP", "LCP", "SimCP", "StaCP")


def emit(message: str, *, stream=sys.stdout, delay: float = 0.25) -> None:
    print(message, file=stream, flush=True)
    time.sleep(delay)


def show_card(path: Path) -> None:
    emit(f"\n===== {path.name} 卡片 =====", delay=0.1)
    if not path.exists():
        emit(f"未找到卡片：{path}", stream=sys.stderr, delay=0.1)
        return

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    emit(f"路径：{path}", delay=0.1)
    emit(f"行数：{len(lines)}", delay=0.1)
    for number, line in enumerate(lines[:8], start=1):
        emit(f"{number:>3}: {line}", delay=0.08)
    if len(lines) > 8:
        emit(f"... 其余 {len(lines) - 8} 行已省略", delay=0.1)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="定轨命令行输出捕获测试程序")
    parser.add_argument("--scheme-dir", default=".", help="包含控制卡片的定轨方案目录")
    args = parser.parse_args()
    scheme_dir = Path(args.scheme_dir).resolve()

    emit("[测试程序] 定轨任务已启动")
    emit(f"[测试程序] 工作目录：{Path.cwd()}")
    emit(f"[测试程序] 方案目录：{scheme_dir}")
    emit("[测试程序] 正在读取控制卡片...")

    for card_name in CARD_NAMES:
        show_card(scheme_dir / card_name)

    emit("\n[测试程序] 正在初始化动力学模型...")
    for step in range(1, 6):
        emit(f"[定轨迭代] {step}/5  残差 RMS = {12.5 / (step * step):.6f}")

    emit("[测试程序] 定轨计算完成，退出代码 0。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
