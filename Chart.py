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
    import spiceypy as spice

    with open(kernel_list_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            kernel = line.strip()
            if kernel and not kernel.startswith("#") and Path(kernel).exists():
                spice.furnsh(kernel)


def utc2et_array(start_utc, end_utc, num_points):
    import spiceypy as spice

    return np.linspace(spice.utc2et(start_utc), spice.utc2et(end_utc), num_points)


def get_positions(observer, target, frame, et_array):
    import spiceypy as spice

    positions = [spice.spkpos(target, et, frame, "NONE", observer)[0] for et in et_array]
    return np.array(positions).T


class OrbitPlotCanvas(FigureCanvas):
    def __init__(self, orbit_file_path, parent=None, width=10, height=8, dpi=100):
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
        suffix = self.orbit_file_path.suffix.lower()
        if suffix == ".csv":
            self._load_csv_orbit()
        else:
            self._load_spice_orbit()

    def _load_csv_orbit(self):
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
        self._plot_points(self.points)

    def _load_spice_orbit(self):
        import spiceypy as spice

        spice.kclear()
        kernel_list = Path(__file__).resolve().parent / "PlanetSetup.dat"
        if kernel_list.exists():
            load_kernels(kernel_list)
        spice.furnsh(str(self.orbit_file_path))
        et_array = utc2et_array("2029-04-01T00:00:00", "2030-04-15T12:00:00.00", 1000)
        points = get_positions("SSB", "2099942", "ECLIPJ2000", et_array).T
        self.points = points
        self._plot_points(points)

    def _plot_points(self, points):
        self.ax.cla()
        self.ax.set_xlabel("X / m")
        self.ax.set_ylabel("Y / m")
        self.ax.set_zlabel("Z / m")
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
        if self.points is None or self.trajectory_line is None:
            return []
        idx = min(frame, len(self.points) - 1)
        data = self.points[: idx + 1]
        self.trajectory_line.set_data(data[:, 0], data[:, 1])
        self.trajectory_line.set_3d_properties(data[:, 2])
        return [self.trajectory_line]

    def start_animation(self):
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
