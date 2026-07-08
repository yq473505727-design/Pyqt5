from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares


SECONDS_PER_DAY = 86400.0


@dataclass
class OrbitResult:
    summary: str
    orbit_csv: Path
    summary_txt: Path
    residual_csv: Optional[Path] = None


def run_direct_orbit_determination(ui, scheme_dir: Path, output_dir: Path) -> OrbitResult:
    """根据界面参数执行内置二体动力学轨道预报或带观测的初轨修正。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    start_dt = ui.date_arc_start_time.dateTime()
    end_dt = ui.date_arc_end_time.dateTime()
    duration = start_dt.secsTo(end_dt)
    if duration <= 0:
        raise ValueError("弧段结束时刻必须晚于初始时刻。")

    state0 = np.concatenate([
        _parse_vector(ui.edit_arc_initial_position.text(), 3, "卫星初轨位置 X,Y,Z"),
        _parse_vector(ui.edit_arc_initial_velocity.text(), 3, "卫星初轨速度 Vx,Vy,Vz"),
    ])
    mu = _central_mu(ui)
    step = max(_parse_float(ui.edit_arc_output_step_legacy.text(), 60.0), 1.0)

    observation_file = _find_observation_file(scheme_dir)
    observations = _read_position_observations(observation_file, start_dt) if observation_file else []
    adjusted_state = state0.copy()
    fit_report = "未发现 observations.csv，已按当前初始状态进行轨道积分预报。"
    residual_rows = []

    if observations:
        adjusted_state, residual_rows, fit_report = _fit_initial_state(state0, mu, observations)

    sample_times = np.arange(0.0, duration + step, step)
    if sample_times[-1] < duration:
        sample_times = np.append(sample_times, duration)
    states = propagate_state(adjusted_state, mu, sample_times)

    orbit_csv = output_dir / "orbit_result.csv"
    _write_orbit_csv(orbit_csv, start_dt, sample_times, states)

    residual_csv = None
    if residual_rows:
        residual_csv = output_dir / "residuals.csv"
        _write_residual_csv(residual_csv, residual_rows)

    summary = "\n".join([
        "Python 内置二体动力学定轨计算完成。",
        f"中心体引力常数 GM = {mu:.12e} m^3/s^2",
        f"积分弧长 = {duration:.3f} s，输出步长 = {step:.3f} s",
        f"初始状态修正前: {_format_state(state0)}",
        f"初始状态修正后: {_format_state(adjusted_state)}",
        fit_report,
        f"轨道结果: {orbit_csv}",
        f"残差结果: {residual_csv}" if residual_csv else "残差结果: 无",
    ])
    summary_txt = output_dir / "summary.txt"
    summary_txt.write_text(summary, encoding="utf-8")
    return OrbitResult(summary, orbit_csv, summary_txt, residual_csv)


def propagate_state(state0: np.ndarray, mu: float, times: Iterable[float]) -> np.ndarray:
    """使用 DOP853 数值积分器把六维初始状态传播到指定时间序列。"""
    times = np.asarray(list(times), dtype=float)
    if len(times) == 0:
        return np.empty((0, 6))
    if len(times) == 1 or math.isclose(times[-1], 0.0):
        return np.repeat(state0.reshape(1, 6), len(times), axis=0)
    sol = solve_ivp(
        lambda _t, y: _two_body_rhs(y, mu),
        (float(times[0]), float(times[-1])),
        state0,
        t_eval=times,
        rtol=1e-10,
        atol=1e-6,
        method="DOP853",
    )
    if not sol.success:
        raise RuntimeError(f"轨道积分失败：{sol.message}")
    return sol.y.T


def _fit_initial_state(state0: np.ndarray, mu: float, observations):
    """利用位置观测值对初始状态做最小二乘修正并生成残差数据。"""
    obs_times = np.array([row[0] for row in observations], dtype=float)
    obs_pos = np.array([row[1] for row in observations], dtype=float)
    scale = np.array([1.0e3, 1.0e3, 1.0e3, 1.0e-3, 1.0e-3, 1.0e-3])

    def residual(correction_scaled):
        """计算给定缩放状态修正量对应的位置残差向量。"""
        trial = state0 + correction_scaled * scale
        states = propagate_state(trial, mu, obs_times)
        return ((states[:, :3] - obs_pos) / 1.0e3).ravel()

    result = least_squares(residual, np.zeros(6), max_nfev=40, xtol=1e-10, ftol=1e-10, gtol=1e-10)
    adjusted = state0 + result.x * scale
    fit_states = propagate_state(adjusted, mu, obs_times)
    residual_vectors = fit_states[:, :3] - obs_pos
    rms = float(np.sqrt(np.mean(np.sum(residual_vectors * residual_vectors, axis=1))))
    rows = []
    for sec, observed, computed, res in zip(obs_times, obs_pos, fit_states[:, :3], residual_vectors):
        rows.append((sec, observed, computed, res, float(np.linalg.norm(res))))
    report = (
        f"使用 observations.csv 完成最小二乘初轨修正：观测点 {len(observations)} 个，"
        f"RMS = {rms:.6f} m，迭代状态 = {result.message}"
    )
    return adjusted, rows, report


def _two_body_rhs(y: np.ndarray, mu: float) -> np.ndarray:
    """计算二体问题状态方程右端，即速度和中心引力加速度。"""
    r = y[:3]
    v = y[3:]
    norm = np.linalg.norm(r)
    if norm <= 0.0:
        raise ValueError("位置向量模长为 0，无法计算引力加速度。")
    acc = -mu * r / norm**3
    return np.concatenate([v, acc])


def _parse_vector(text: str, size: int, label: str) -> np.ndarray:
    """从文本框内容解析固定长度的数值向量并校验维度。"""
    values = [_parse_float(part, None) for part in re.split(r"[\s,;]+", text.strip()) if part]
    if len(values) != size or any(v is None for v in values):
        raise ValueError(f"{label} 需要 {size} 个数值。")
    return np.array(values, dtype=float)


def _parse_float(text: str, default: Optional[float] = None) -> Optional[float]:
    """解析普通科学计数法或 Fortran D 计数法浮点数，失败时返回默认值。"""
    try:
        return float(str(text).strip().replace("D", "E").replace("d", "e"))
    except Exception:
        return default


def _central_mu(ui) -> float:
    """根据当前积分中心选择界面中的中心体引力常数 GM。"""
    text = ui.combo_integration_center.currentText()
    if text == "地球":
        return _parse_float(ui.edit_earth_gm.text(), 3.986004415e14)
    if text == "太阳":
        return _parse_float(ui.edit_sun_gm.text(), 1.32712440018e20)
    if text == "月球":
        return _parse_float(ui.edit_moon_gm.text(), 4.902801076e12)
    # 新界面暂未给阿波菲斯 GM 独立输入框；用全局参数中的太阳 GM 兜底，保证可直接计算。
    return _parse_float(ui.edit_sun_gm.text(), 1.32712440018e20)


def _find_observation_file(scheme_dir: Path) -> Optional[Path]:
    """在方案目录中查找可用于定轨拟合的位置观测文件。"""
    for name in ("observations.csv", "Observation.csv", "obs.csv"):
        path = scheme_dir / name
        if path.exists():
            return path
    return None


def _read_position_observations(path: Path, start_dt) -> list:
    """读取 observations.csv 中的秒计时或 UTC 位置观测并按时间排序。"""
    observations = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"x", "y", "z"}
        if not reader.fieldnames or not required.issubset({name.strip().lower() for name in reader.fieldnames}):
            raise ValueError("observations.csv 需要表头：seconds,x,y,z 或 utc,x,y,z。")
        for row in reader:
            normalized = {k.strip().lower(): v for k, v in row.items() if k}
            if "seconds" in normalized and normalized["seconds"].strip():
                seconds = _parse_float(normalized["seconds"], None)
            elif "utc" in normalized and normalized["utc"].strip():
                seconds = start_dt.secsTo(_qt_datetime_from_text(normalized["utc"]))
            else:
                raise ValueError("observations.csv 每行需要 seconds 或 utc。")
            if seconds is None:
                raise ValueError("observations.csv 中存在无法解析的时间。")
            pos = np.array([
                _parse_float(normalized.get("x"), None),
                _parse_float(normalized.get("y"), None),
                _parse_float(normalized.get("z"), None),
            ], dtype=float)
            if np.any(np.isnan(pos)):
                raise ValueError("observations.csv 中存在无法解析的位置。")
            observations.append((float(seconds), pos))
    if len(observations) < 2:
        raise ValueError("最小二乘定轨至少需要 2 个位置观测点。")
    return sorted(observations, key=lambda item: item[0])


def _qt_datetime_from_text(text: str):
    """把常见 UTC 字符串格式转换为 QDateTime 对象。"""
    from PyQt5.QtCore import QDateTime

    for fmt in ("yyyy-MM-ddTHH:mm:ss.zzz", "yyyy-MM-dd HH:mm:ss.zzz", "yyyy-MM-ddTHH:mm:ss", "yyyy-MM-dd HH:mm:ss"):
        dt = QDateTime.fromString(text.strip(), fmt)
        if dt.isValid():
            return dt
    raise ValueError(f"无法解析 UTC 时间：{text}")


def _write_orbit_csv(path: Path, start_dt, times: np.ndarray, states: np.ndarray) -> None:
    """把轨道传播结果写成包含 UTC、秒计时和六维状态的 CSV 文件。"""
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["utc", "seconds", "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps"])
        for sec, state in zip(times, states):
            writer.writerow([start_dt.addSecs(int(sec)).toString("yyyy-MM-ddTHH:mm:ss"), f"{sec:.6f}", *[f"{v:.12e}" for v in state]])


def _write_residual_csv(path: Path, rows) -> None:
    """把观测值、计算值和残差向量写入残差 CSV 文件。"""
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seconds", "obs_x_m", "obs_y_m", "obs_z_m", "calc_x_m", "calc_y_m", "calc_z_m", "res_x_m", "res_y_m", "res_z_m", "norm_m"])
        for sec, obs, calc, res, norm in rows:
            writer.writerow([f"{sec:.6f}", *[f"{v:.12e}" for v in obs], *[f"{v:.12e}" for v in calc], *[f"{v:.12e}" for v in res], f"{norm:.12e}"])


def _format_state(state: np.ndarray) -> str:
    """把六维状态向量格式化为摘要报告中的科学计数法字符串。"""
    return " ".join(f"{v:.12e}" for v in state)
