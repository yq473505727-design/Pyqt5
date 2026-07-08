from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

import orbit_backend


APP_DIR = Path(__file__).resolve().parent
current_process = None


def genobs(ui):
    """根据当前界面轨道参数生成简化的模拟位置观测文件 observations.csv。"""
    scheme_dir = APP_DIR / "scheme"
    output_dir = APP_DIR / "output"
    result = orbit_backend.run_direct_orbit_determination(ui, scheme_dir, output_dir)
    obs_file = scheme_dir / "observations.csv"
    with result.orbit_csv.open("r", encoding="utf-8", newline="") as src, obs_file.open("w", encoding="utf-8", newline="") as dst:
        reader = csv.DictReader(src)
        writer = csv.writer(dst)
        writer.writerow(["seconds", "x", "y", "z"])
        for idx, row in enumerate(reader):
            if idx % 10 == 0:
                writer.writerow([row["seconds"], row["x_m"], row["y_m"], row["z_m"]])
    return f"已生成模拟位置观测文件：{obs_file}\n{result.summary}"


def terminate_genobs_process():
    """终止仍在运行的旧版模拟观测生成进程并清理进程句柄。"""
    global current_process
    if current_process is not None:
        try:
            current_process.terminate()
        except Exception:
            pass
        current_process = None


def copy_simcp_to_target():
    """兼容旧接口；说明 new 版本已不需要复制 SimCP 到旧 case 目录。"""
    return "当前 new 版本使用内置 Python 计算后端，不需要复制 SimCP 到旧 case 目录。"


def process_obs_files(inputdata_dir):
    """清理空观测文件并按类型重新编号观测文件名。"""
    path = Path(inputdata_dir)
    if not path.exists():
        return f"目录不存在：{path}"
    log_msgs = []
    for fname in list(path.iterdir()):
        if fname.is_file() and fname.name.startswith(("51type_", "52type_")):
            lines = fname.read_text(encoding="utf-8", errors="ignore").splitlines()
            if fname.stat().st_size < 100 or len(lines) <= 3:
                fname.unlink()
                log_msgs.append(f"已删除空观测文件：{fname.name}")
    for prefix in ("51", "52"):
        files = []
        for fname in path.iterdir():
            match = re.match(rf"{prefix}type_(\d+)", fname.name)
            if match:
                files.append((int(match.group(1)), fname))
        for idx, (_, old_path) in enumerate(sorted(files), 1):
            new_path = old_path.with_name(f"{prefix}type_{idx:02d}")
            if old_path != new_path:
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)
                log_msgs.append(f"已重命名 {old_path.name} -> {new_path.name}")
    return "\n".join(log_msgs) if log_msgs else "未发现需要处理的观测值文件。"


def execute_fortran_program(exe_path, work_dir):
    """执行外部 Fortran/EXE 程序并返回标准输出和错误输出。"""
    exe = Path(exe_path)
    if not exe.exists():
        return f"未找到执行文件：{exe}"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(exe)],
        cwd=str(work_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=flags,
    )
    out, err = process.communicate()
    return (out or "") + (f"\n[stderr]\n{err}" if err else "")


def copy_obs_files_to_arc(ui):
    """把当前方案生成的 observations.csv 复制到指定弧段输入目录。"""
    src = APP_DIR / "scheme" / "observations.csv"
    arc_id = ui.lineEdit_87.text().strip() if hasattr(ui, "lineEdit_87") else "001"
    dst_dir = APP_DIR / "output" / "Arc" / arc_id / "InputDATA"
    dst_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return f"未找到观测文件：{src}"
    shutil.copy2(src, dst_dir / src.name)
    return f"已配置观测文件到：{dst_dir / src.name}"


def merge_our_own_ephe():
    """兼容旧接口；说明 new 版本不再调用旧星历融合程序。"""
    return "当前 new 版本未使用旧星历融合 exe；轨道结果由内置 Python 后端生成。"


def run_gen_obs_for_solve_asteph():
    """兼容旧接口；提示用户改用 new 版本的生成模拟观测值流程。"""
    return "当前 new 版本未使用旧 Gen_Obs_For_SolveAstEph.exe；请使用“生成模拟观测值”。"
