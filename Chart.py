from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QSizePolicy


def load_kernels(kernel_list_file):
    """读取 SPICE 内核清单并逐个加载其中存在的内核文件。"""
    import spiceypy as spice

    kernel_list_path = Path(kernel_list_file).resolve()
    missing = []
    with kernel_list_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            kernel = line.strip()
            if not kernel or kernel.startswith("#"):
                continue
            kernel_path = Path(kernel)
            if not kernel_path.is_absolute():
                kernel_path = kernel_list_path.parent / kernel_path
            kernel_path = kernel_path.resolve()
            if kernel_path.exists():
                spice.furnsh(str(kernel_path))
            else:
                missing.append(str(kernel_path))
    if missing:
        raise FileNotFoundError("内核清单中存在缺失文件：\n" + "\n".join(missing))


def utc2et_array(start_utc, end_utc, num_points):
    """把 UTC 起止时间转换为等间隔的 SPICE ET 时间序列。"""
    import spiceypy as spice

    return np.linspace(spice.utc2et(start_utc), spice.utc2et(end_utc), num_points)


def get_positions(observer, target, frame, et_array):
    """按给定观测者、目标和参考系批量计算目标位置坐标。"""
    import spiceypy as spice

    positions = [spice.spkpos(target, et, frame, "NONE", observer)[0] for et in et_array]
    return np.array(positions).T


class OrbitPlotCanvas(FigureCanvas):
    def __init__(self, orbit_file_path, parent=None, width=10, height=8, dpi=100):
        """创建轨道绘图画布，并根据输入文件自动加载轨道数据。"""
        self.orbit_file_path = Path(orbit_file_path)
        fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi, subplot_kw={"projection": "3d"})
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()
        self.animation = None
        self.points = None
        self.trajectory_line = None
        self.load_and_setup()

    def load_and_setup(self):
        """根据轨道文件类型选择 CSV 或 SPK 解析流程并完成绘图初始化。"""
        suffix = self.orbit_file_path.suffix.lower()
        if suffix == ".csv":
            self._load_csv_orbit()
        else:
            self._load_spice_orbit()

    def _load_csv_orbit(self):
        """从内置后端生成的轨道 CSV 中读取位置序列并绘制轨迹。"""
        xyz = []
        with self.orbit_file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    xyz.append([float(row["x_m"]), float(row["y_m"]), float(row["z_m"])])
                except Exception:
                    continue
        if not xyz:
            raise ValueError("轨道 CSV 中没有可绘制的 x_m/y_m/z_m 数据。")
        self.points = np.array(xyz, dtype=float)
        self.coordinate_unit = "m"
        self._plot_points(self.points)

    def _load_spice_orbit(self):
        """加载 SPICE 内核和 SPK 文件，提取最长覆盖弧段用于轨道绘图。"""
        import spiceypy as spice

        spice.kclear()
        kernel_list = Path(__file__).resolve().parent / "PlanetSetup.dat"
        if not kernel_list.exists():
            raise FileNotFoundError(f"未找到 SPICE 内核清单：{kernel_list}")
        load_kernels(kernel_list)
        spice.furnsh(str(self.orbit_file_path))

        object_ids = [int(object_id) for object_id in spice.spkobj(str(self.orbit_file_path))]
        if not object_ids:
            raise ValueError(f"SPK 文件中没有可用的轨道对象：{self.orbit_file_path}")

        target_id, start_et, end_et = self._select_spk_segment(spice, object_ids)
        et_array = np.linspace(start_et, end_et, 1000)
        points = get_positions("SSB", str(target_id), "ECLIPJ2000", et_array).T
        self.points = points
        self.coordinate_unit = "km"
        self.target_id = target_id
        self.start_utc = spice.et2utc(start_et, "ISOC", 3)
        self.end_utc = spice.et2utc(end_et, "ISOC", 3)
        self._plot_points(points)

    def _select_spk_segment(self, spice, object_ids):
        """在 SPK 文件的所有对象覆盖区间中选择时间跨度最长的弧段。"""
        segments = []
        for object_id in object_ids:
            coverage = spice.spkcov(str(self.orbit_file_path), object_id)
            for index in range(0, len(coverage), 2):
                start_et = float(coverage[index])
                end_et = float(coverage[index + 1])
                segments.append((end_et - start_et, object_id, start_et, end_et))
        if not segments:
            raise ValueError(f"SPK 文件中没有有效的时间覆盖区间：{self.orbit_file_path}")
        _, object_id, start_et, end_et = max(segments, key=lambda segment: segment[0])
        return object_id, start_et, end_et

    def _plot_points(self, points):
        """把三维位置点绘制为完整轨道、起终点和动画当前弧段。"""
        self.ax.cla()
        unit = getattr(self, "coordinate_unit", "")
        self.ax.set_xlabel(f"X / {unit}" if unit else "X")
        self.ax.set_ylabel(f"Y / {unit}" if unit else "Y")
        self.ax.set_zlabel(f"Z / {unit}" if unit else "Z")
        if hasattr(self, "target_id"):
            self.ax.set_title(f"SPK object {self.target_id}\n{self.start_utc} — {self.end_utc}")
        self.ax.plot(points[:, 0], points[:, 1], points[:, 2], alpha=0.35, label="Orbit")
        self.trajectory_line, = self.ax.plot([], [], [], linewidth=2.0, label="Current arc")
        self.ax.scatter(points[0, 0], points[0, 1], points[0, 2], s=30, label="Start")
        self.ax.scatter(points[-1, 0], points[-1, 1], points[-1, 2], s=30, label="End")
        max_range = np.ptp(points, axis=0).max() or 1.0
        center = points.mean(axis=0)
        for setter, c in zip((self.ax.set_xlim, self.ax.set_ylim, self.ax.set_zlim), center):
            setter(c - max_range / 2, c + max_range / 2)
        self.ax.legend(loc="upper left")
        self.draw()

    def update_frame(self, frame):
        """按动画帧编号更新当前已走过的轨道弧段。"""
        if self.points is None or self.trajectory_line is None:
            return []
        idx = min(frame, len(self.points) - 1)
        data = self.points[: idx + 1]
        self.trajectory_line.set_data(data[:, 0], data[:, 1])
        self.trajectory_line.set_3d_properties(data[:, 2])
        return [self.trajectory_line]

    def start_animation(self):
        """启动轨道轨迹随时间推进的 Matplotlib 动画。"""
        if self.points is None or len(self.points) == 0:
            return
        self.animation = animation.FuncAnimation(
            self.figure,
            self.update_frame,
            frames=len(self.points),
            interval=20,
            blit=False,
        )
        self.animation._start()
