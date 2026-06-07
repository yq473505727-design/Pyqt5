from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout


def j2000_datetime():
    return QDateTime(2000, 1, 1, 12, 0, 0, 0, Qt.UTC)


class ResidualCanvas(FigureCanvas):
    def __init__(self, times, res1, res2=None, filetype=None, parent=None):
        self.fig = Figure(figsize=(12, 5))
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(bottom=0.2)
        self.plot_residual(times, res1, res2, filetype)

    def plot_residual(self, times, res1, res2=None, filetype=None):
        x = [float(t) for t in times]
        self.ax.clear()
        self.ax.scatter(x, res1, s=10, label="Residual")
        if res2 is not None and len(res2) == len(x):
            self.ax.scatter(x, res2, s=10, label="Residual 2")
        self.ax.set_xlabel("Time / s")
        self.ax.set_ylabel("Residual / m")
        self.ax.legend()
        self.draw()


def show_residual_in_widget2(parent, widget2):
    default = Path(__file__).resolve().parent / "output"
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "选择残差文件",
        str(default),
        "Residual files (*.csv *.dat51 *.dat52 *.dat53);;All files (*)",
    )
    if not file_path:
        return
    try:
        times, res1, res2 = read_residual_file(Path(file_path))
        if not times:
            QMessageBox.warning(parent, "数据错误", "文件内容为空或格式不正确。")
            return
        layout = widget2.layout()
        if layout is None:
            layout = QVBoxLayout(widget2)
            widget2.setLayout(layout)
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        layout.addWidget(ResidualCanvas(times, res1, res2, Path(file_path).suffix, parent=widget2))
    except Exception as exc:
        QMessageBox.critical(parent, "绘图错误", f"绘制残差图时出错：{exc}")


def read_residual_file(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            times, res = [], []
            for row in reader:
                if "norm_m" in row:
                    times.append(float(row.get("seconds", len(times))))
                    res.append(float(row["norm_m"]))
            return times, res, None
    times, res1, res2 = [], [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 3 or line.lstrip().startswith("#"):
                continue
            try:
                times.append(float(parts[1]))
                res1.append(float(parts[2]))
                if len(parts) > 3:
                    res2.append(float(parts[3]))
            except Exception:
                continue
    return times, res1, res2 if res2 else None
