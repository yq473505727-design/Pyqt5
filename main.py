from __future__ import annotations

import os
import shutil
import subprocess
import sys
import codecs
from contextlib import contextmanager
from pathlib import Path

from PyQt5.QtCore import QObject, QProcess, QThread, QDateTime, QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
)

from win import Ui_MainWindow
import card_io
import iconsource_rc
import orbit_backend


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
LEGACY_DIR = PROJECT_ROOT / "WJK__Orbit Determination__toYQ" / "pyqt5demo"
DEFAULT_SCHEME_DIR = APP_DIR / "scheme"
ORBIT_PROGRAM = APP_DIR / "external" / "TestOrbitProgram.exe"
ORBIT_OUTPUT_ENCODING = "utf-8"
CARD_NAMES = ("GCP", "LCP", "SimCP", "StaCP")
APP_ICON_NAME = "app_icon.ico"
WINDOWS_APP_ID = "wjk.orbit-determination.platform"
APP_DISPLAY_NAME = "轨道确定与预报分系统软件V1.0"
OBSERVATION_WEIGHT_HELP = {
    "51": ("双程测距", "meter"),
    "52": ("双程测速", "mm/s"),
    "59": ("VLBI 时延", "ns"),
    "60": ("VLBI 时延率", "ps/s"),
}
SELECT_OBSERVATION_TYPE_HELP = {
    "1": "双程测距",
    "2": "双程测速",
    "9": "VLBI 时延",
    "10": "VLBI 时延率",
}
SELECT_OBSERVATION_TYPE_LEGACY_CODES = {
    "51": "1",
    "52": "2",
    "59": "9",
    "60": "10",
}
PER_ACC_DIRECTION_HELP = {
    "1": "沿飞行方向（T）",
    "2": "沿轨道法向方向（N）",
    "3": "沿轨道半径方向（R）",
}
PER_ACC_MODEL_HELP = {
    "1": "使用 cos 函数拟合",
    "2": "使用 sin 函数拟合",
    "3": "使用常数拟合",
}
STATION_STATUS_OPTIONS = ("激活", "未激活")
STATION_COORD_TYPE_OPTIONS = ("直角坐标系XYZ", "大地坐标BLH")
STATION_BODY_OPTIONS = ("地球测站", "月球测站")

try:
    import UseFortran
except Exception:
    UseFortran = None


@contextmanager
def working_directory(path: Path):
    """临时切换当前工作目录，执行完毕后自动恢复原目录。"""
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class Worker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, func, *args):
        """保存后台线程需要执行的函数和参数。"""
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        """在线程中执行任务函数，并通过信号返回结果或错误信息。"""
        try:
            self.finished.emit(str(self.func(*self.args)))
        except Exception as exc:
            self.error.emit(str(exc))


class TableTools:
    TABLE_FONT_FAMILY = "Microsoft YaHei"
    TABLE_FONT_SIZE = 8

    @staticmethod
    def table_font() -> QFont:
        """返回全应用表格统一使用的字体设置。"""
        return QFont(TableTools.TABLE_FONT_FAMILY, TableTools.TABLE_FONT_SIZE)

    @staticmethod
    def apply_font(table: QTableWidget):
        """把统一字体应用到表格、表头、单元格和单元格控件。"""
        font = TableTools.table_font()
        table.setFont(font)
        table.viewport().setFont(font)
        table.horizontalHeader().setFont(font)
        table.verticalHeader().setFont(font)
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setFont(font)
        for row in range(table.rowCount()):
            header_item = table.verticalHeaderItem(row)
            if header_item is not None:
                header_item.setFont(font)
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is not None:
                    item.setFont(font)
                widget = table.cellWidget(row, col)
                if widget is not None:
                    widget.setFont(font)

    @staticmethod
    def setup(table: QTableWidget, datetime_columns=None):
        """初始化表格的选择模式、滚动策略、列宽和时间控件列。"""
        datetime_columns = datetime_columns or []
        TableTools.apply_font(table)
        table.horizontalHeader().setVisible(True)
        table.setAlternatingRowColors(True)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setDefaultSectionSize(22)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table.setShowGrid(True)
        for col in range(table.columnCount()):
            if col in datetime_columns:
                table.setColumnWidth(col, 185)
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
            else:
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        for row in range(table.rowCount()):
            for col in datetime_columns:
                if table.cellWidget(row, col) is None:
                    item = table.item(row, col)
                    value = item.text().strip() if item and item.text().strip() else None
                    card_io.set_datetime_cell(table, row, col, value)
        TableTools.apply_font(table)

    @staticmethod
    def add_row(table: QTableWidget, datetime_columns=None, defaults=None):
        """按默认值向表格追加一行，并为时间列创建时间编辑控件。"""
        datetime_columns = datetime_columns or []
        if callable(defaults):
            defaults = defaults()
        defaults = defaults or []
        row = table.rowCount()
        table.insertRow(row)
        for col in range(table.columnCount()):
            if col in datetime_columns:
                value = defaults[col] if col < len(defaults) else None
                card_io.set_datetime_cell(table, row, col, value)
            else:
                value = defaults[col] if col < len(defaults) else ""
                item = QTableWidgetItem(value)
                item.setFont(TableTools.table_font())
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col, item)
        TableTools.apply_font(table)
        table.selectRow(row)

    @staticmethod
    def delete_row(table: QTableWidget, parent):
        """删除当前选中的表格行，并在删除前弹出确认提示。"""
        row = table.currentRow()
        if row < 0:
            QMessageBox.warning(parent, "提示", "请先选择要删除的行。")
            return
        if QMessageBox.question(parent, "确认删除", f"确定删除第 {row + 1} 行吗？") == QMessageBox.Yes:
            table.removeRow(row)

    @staticmethod
    def edit_row(table: QTableWidget, parent, datetime_columns=None):
        """用弹窗编辑当前表格行，支持普通文本、下拉框和时间列。"""
        row = table.currentRow()
        if row < 0:
            QMessageBox.warning(parent, "提示", "请先选择要修改的行。")
            return
        datetime_columns = set(datetime_columns or [])
        dialog = QDialog(parent)
        dialog.setWindowTitle("修改表格行")
        layout = QFormLayout(dialog)
        editors = []
        for col in range(table.columnCount()):
            header = table.horizontalHeaderItem(col)
            label = header.text() if header else f"第 {col + 1} 列"
            if col in datetime_columns:
                editor = QDateTimeEdit()
                editor.setCalendarPopup(True)
                editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zzz")
                widget = table.cellWidget(row, col)
                if isinstance(widget, QDateTimeEdit):
                    editor.setDateTime(widget.dateTime())
                else:
                    editor.setDateTime(QDateTime.currentDateTime())
            else:
                widget = table.cellWidget(row, col)
                if isinstance(widget, QComboBox):
                    editor = QComboBox()
                    for index in range(widget.count()):
                        editor.addItem(widget.itemText(index), widget.itemData(index))
                    editor.setCurrentText(widget.currentText())
                else:
                    editor = QLineEdit(table.item(row, col).text() if table.item(row, col) else "")
            layout.addRow(label, editor)
            editors.append(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec_() != QDialog.Accepted:
            return
        for col, editor in enumerate(editors):
            if col in datetime_columns:
                card_io.set_datetime_cell(table, row, col, editor.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz"))
            elif isinstance(editor, QComboBox):
                widget = table.cellWidget(row, col)
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(editor.currentText())
                else:
                    table.setCellWidget(row, col, editor)
                item = table.item(row, col) or QTableWidgetItem()
                item.setText(editor.currentText())
                item.setFont(TableTools.table_font())
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col, item)
            else:
                item = table.item(row, col) or QTableWidgetItem()
                item.setFont(TableTools.table_font())
                item.setText(editor.text())
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col, item)
        TableTools.apply_font(table)


class MainWindow(QMainWindow):
    def __init__(self):
        """创建主窗口、初始化 UI 状态并连接所有交互信号。"""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.current_scheme_dir = DEFAULT_SCHEME_DIR
        self.threads = []
        self.orbit_process = None
        self._orbit_stdout_decoder = None
        self._orbit_stderr_decoder = None
        self._syncing_observation_weight = False
        self._syncing_select_observation = False
        self._syncing_simulation_observation = False
        self._syncing_per_acc = False
        self._configure_ui()
        self._connect_signals()

    def _configure_ui(self):
        """完成窗口标题、图标、样式、默认表格和主要页面布局初始化。"""
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setWindowIcon(load_app_icon())
        self.setFont(QFont("Microsoft YaHei", 8))
        self._apply_layout_polish()
        self._apply_style()
        self._align_text_widgets()
        self.ui.statusbar.showMessage(f"工作目录：{self.current_scheme_dir}")
        self.ui.button_new_scheme.setToolTip("新建定轨方案")
        self.ui.button_open_scheme.setToolTip("打开定轨方案")
        self.ui.button_save_scheme.setToolTip("保存定轨方案")
        self.ui.button_save_scheme_as.setToolTip("另存为定轨方案")
        self.ui.button_start_orbit.setToolTip("开始定轨")
        self.ui.button_show_chart.setToolTip("查看图表")
        self._apply_toolbar_icons()
        if self.ui.date_arc_start_time.dateTime().secsTo(self.ui.date_arc_end_time.dateTime()) <= 0:
            self.ui.date_arc_end_time.setDateTime(self.ui.date_arc_start_time.dateTime().addDays(1))
        self._configure_global_parameters()
        self._configure_arc_parameters()
        self._apply_global_page_layout()
        self._apply_secondary_pages_layout()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_simulation_observation_table()
        self._configure_per_acc_table()
        self._configure_station_table()
        self._init_default_tables()
        self._setup_tables()

    def _configure_global_parameters(self):
        """初始化全局参数页面的运行模式、积分中心和隐藏项。"""
        self._move_integrator_to_global_parameters()
        self._normalize_global_parameter_labels()
        self._configure_run_modes()

        integration_centers = [
            ("地球", "0"),
            # ("月球", "10"),
            # ("火星", "2"),
        ]
        self.ui.combo_integration_center.clear()
        for label, code in integration_centers:
            self.ui.combo_integration_center.addItem(label, code)
        self.ui.combo_integration_center.setCurrentIndex(0)
        self._hide_gravity_inversion_order()
        self._sync_integration_center_controls()

        if self.ui.combo_ephemeris_model.findText("DE440") < 0:
            self.ui.combo_ephemeris_model.addItem("DE440", "440")
        for index in range(self.ui.combo_ephemeris_model.count()):
            text = self.ui.combo_ephemeris_model.itemText(index)
            if self.ui.combo_ephemeris_model.itemData(index) is None and text.startswith("DE"):
                self.ui.combo_ephemeris_model.setItemData(index, text.removeprefix("DE"))
        self.ui.combo_ephemeris_model.setCurrentText("DE440")

        integrators = [("ode", "1"), ("Adams12", "2")]
        for index, (label, code) in enumerate(integrators):
            if index >= self.ui.combo_integrator_type.count():
                self.ui.combo_integrator_type.addItem(label, code)
            else:
                self.ui.combo_integrator_type.setItemText(index, label)
                self.ui.combo_integrator_type.setItemData(index, code)
        self.ui.combo_integrator_type.setCurrentText("Adams12")
        self.ui.combo_integrator_type.setToolTip("1=ode；2=Adams12（12阶 Adams-Bashforth-Moulton 预估校正固定步长积分器）")
        integrator_font = QFont("Microsoft YaHei", 8)
        self.ui.label_integrator_selection.setFont(integrator_font)
        self.ui.combo_integrator_type.setFont(integrator_font)

        self.ui.check_third_body_moon.setChecked(True)
        self.ui.check_third_body_sun.setChecked(True)

        self._lock_unreleased_global_parameters()

    def _configure_run_modes(self):
        """重建运行模式下拉框，仅保留当前版本支持的模式。"""
        run_modes = [
            ("轨道预报", "1"),
            ("仿真观测值", "2"),
            ("精密定轨", "4"),
        ]
        self.ui.combo_run_mode.clear()
        for label, code in run_modes:
            self.ui.combo_run_mode.addItem(label, code)
        self.ui.combo_run_mode.setCurrentText("精密定轨")
        self.ui.combo_run_mode.setToolTip("1=轨道预报；2=仿真观测值；4=精密定轨")

    def _normalize_global_parameter_labels(self):
        """修正全局参数页面中的显示文字，使中文标签更清晰一致。"""
        for label, text in (
            (self.ui.label_gravity_file_format, "引力场文件格式："),
            (self.ui.label_solid_tide_perturbation, "固体潮摄动："),
        ):
            label.setText(text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _hide_gravity_inversion_order(self):
        """隐藏当前版本暂未开放的重力场解算阶次输入区域。"""
        self.ui.label_gravity_inversion_degree.hide()
        self.ui.spin_gravity_inversion_degree.hide()

    def _sync_integration_center_controls(self):
        """根据积分中心选择同步中心体相关复选框的可用状态。"""
        center_code = str(self.ui.combo_integration_center.currentData() or "0")
        is_earth_center = center_code in {"0", "399"}
        if is_earth_center:
            self.ui.check_third_body_earth.setChecked(False)
        self.ui.check_third_body_earth.setEnabled(not is_earth_center)

    def _move_integrator_to_global_parameters(self):
        """把积分器选择控件从弧段参数页移到全局参数页显示。"""
        if self.ui.combo_integrator_type.parent() is self.ui.row_global_troposphere:
            return

        self.ui.horizontalLayout_28.removeWidget(self.ui.label_integrator_selection)
        self.ui.horizontalLayout_28.removeWidget(self.ui.combo_integrator_type)
        self.ui.label_integrator_selection.setParent(self.ui.row_global_troposphere)
        self.ui.combo_integrator_type.setParent(self.ui.row_global_troposphere)

        insert_at = max(self.ui.horizontalLayout_16.count() - 1, 0)
        self.ui.horizontalLayout_16.insertSpacing(insert_at, 24)
        self.ui.horizontalLayout_16.insertWidget(insert_at + 1, self.ui.label_integrator_selection)
        self.ui.horizontalLayout_16.insertWidget(insert_at + 2, self.ui.combo_integrator_type)
        self.ui.label_integrator_selection.show()
        self.ui.combo_integrator_type.show()

        self.ui.row_arc_integrator_type.hide()
        if hasattr(self.ui, "separator_arc_integrator_type"):
            self.ui.separator_arc_integrator_type.hide()

    def _move_widget_y(self, widget, y):
        """只调整控件的纵坐标，保留原有横坐标和尺寸。"""
        geometry = widget.geometry()
        widget.setGeometry(geometry.x(), y, geometry.width(), geometry.height())

    def _compact_arc_integrator_gap(self):
        """压缩弧段参数页中移走积分器后留下的垂直空隙。"""
        positions = {
            "separator_arc_internal_tabs": 250,
            "tabs_arc_parameter_details": 260,
        }
        for name, y in positions.items():
            widget = getattr(self.ui, name, None)
            if widget:
                self._move_widget_y(widget, y)

    def _compact_arc_parameter_rows(self):
        """重新排列弧段参数页基础输入行，使页面更紧凑。"""
        positions = {
            "separator_arc_time_span": 80,
            "row_arc_time_span": 90,
            "row_arc_initial_position": 110,
            "row_arc_initial_velocity": 130,
            "row_arc_position_prior": 150,
            "row_arc_velocity_prior": 170,
            "separator_arc_prior_errors": 190,
            "row_arc_doppler_settings": 200,
            "separator_arc_step_settings": 220,
            "row_arc_step_settings": 230,
        }
        for name, y in positions.items():
            widget = getattr(self.ui, name, None)
            if widget:
                self._move_widget_y(widget, y)

    def _lock_unreleased_global_parameters(self):
        """禁用当前版本尚未开放的全局参数控件。"""
        self.ui.check_solid_tide_perturbation.setChecked(False)
        self._lock_widgets(
            self.ui.spin_gravity_inversion_degree,
            self.ui.label_solid_tide_perturbation,
            self.ui.check_solid_tide_perturbation,
            self.ui.label_solid_tide_k2_love_number,
            self.ui.edit_solid_tide_k2_love_number,
            self.ui.label_solid_tide_prior_error,
            self.ui.edit_solid_tide_prior_error,
        )

    def _configure_per_acceleration_model(self):
        """初始化经验加速度模型选择，并隐藏未开放的有限推力选项。"""
        self.ui.combo_arc_per_acc_model_type.clear()
        self.ui.combo_arc_per_acc_model_type.addItem("经验加速度模型", 0)
        # self.ui.combo_arc_per_acc_model_type.addItem("有限推力", 1)
        self.ui.combo_arc_per_acc_model_type.setCurrentIndex(0)
        self.ui.combo_arc_per_acc_model_type.setToolTip("当前仅启用经验加速度模型")
        tab_index = self.ui.tabs_arc_parameter_details.indexOf(self.ui.tab_arc_per_acceleration)
        if tab_index >= 0:
            self.ui.tabs_arc_parameter_details.setTabText(tab_index, "经验加速度模型")

    def _configure_arc_parameters(self):
        """配置弧段参数页的可见项、时间控件、快捷按钮和经验加速度入口。"""
        self._comment_out_solar_panel_area()
        self._remove_albedo_radiation_row()
        self._comment_out_doppler_inverse_time()
        self._replace_orbit_step_edits()
        self._configure_per_acceleration_model()
        self._remove_arc_derivative_filter_rows()
        self._remove_spice_kernel_path_row()
        self._align_arc_parameter_labels()

        self.ui.check_arc_albedo_radiation.setChecked(False)
        self._lock_widgets(self.ui.label_arc_albedo_radiation, self.ui.check_arc_albedo_radiation)
        self._lock_widgets(
            self.ui.label_arc_partial_derivative_step,
            self.ui.edit_arc_partial_derivative_step,
            self.ui.label_arc_position_derivative_step,
            self.ui.edit_arc_position_derivative_step,
            self.ui.label_arc_velocity_derivative_step,
            self.ui.edit_arc_velocity_derivative_step,
            self.ui.label_arc_input_filter,
            self.ui.combo_arc_input_filter,
        )
        self._ensure_observation_weight_help_button()

        for editor in (self.ui.date_arc_start_time, self.ui.date_arc_end_time):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zzz")

        if not hasattr(self.ui, "button_arc_start_now"):
            self.ui.button_arc_start_now = QPushButton("当前", self.ui.row_arc_time_span)
            self.ui.button_arc_start_now.setObjectName("button_arc_start_now")
            self.ui.horizontalLayout_21.insertWidget(3, self.ui.button_arc_start_now)

        if not hasattr(self.ui, "button_arc_end_plus7"):
            self.ui.button_arc_end_plus7 = QPushButton("+7天", self.ui.row_arc_time_span)
            self.ui.button_arc_end_plus7.setObjectName("button_arc_end_plus7")
            self.ui.horizontalLayout_21.insertWidget(7, self.ui.button_arc_end_plus7)

        if not hasattr(self.ui, "button_arc_end_plus5"):
            self.ui.button_arc_end_plus5 = QPushButton("+5天", self.ui.row_arc_time_span)
            self.ui.button_arc_end_plus5.setObjectName("button_arc_end_plus5")
            self.ui.horizontalLayout_21.insertWidget(8, self.ui.button_arc_end_plus5)

        time_layout = self.ui.horizontalLayout_21
        time_layout.removeWidget(self.ui.button_arc_end_plus5)
        time_layout.removeWidget(self.ui.button_arc_end_plus7)
        time_layout.insertWidget(7, self.ui.button_arc_end_plus5)
        time_layout.insertWidget(8, self.ui.button_arc_end_plus7)

        self.ui.button_arc_start_now.setText("当前")
        self.ui.button_arc_start_now.setToolTip("同步为电脑当前时间，并同步弧段结束时刻")
        self.ui.button_arc_end_plus7.setText("+7天")
        self.ui.button_arc_end_plus7.setToolTip("弧段结束时刻 = 弧段初始时刻 + 7 天")
        self.ui.button_arc_end_plus5.setText("+5天")
        self.ui.button_arc_end_plus5.setToolTip("弧段结束时刻 = 弧段初始时刻 + 5 天")

        time_font = QFont("Microsoft YaHei", 8)
        for widget in (
            self.ui.label_arc_start_time,
            self.ui.date_arc_start_time,
            self.ui.button_arc_start_now,
            self.ui.label_arc_end_time,
            self.ui.date_arc_end_time,
            self.ui.button_arc_end_plus5,
            self.ui.button_arc_end_plus7,
        ):
            widget.setFont(time_font)

        for button in (self.ui.button_arc_start_now, self.ui.button_arc_end_plus7, self.ui.button_arc_end_plus5):
            button.setMinimumHeight(18)
            button.setMaximumHeight(22)

        self.ui.button_arc_start_now.clicked.connect(self._set_arc_start_to_now)
        self.ui.button_arc_end_plus7.clicked.connect(lambda: self._set_arc_end_days_after_start(7))
        self.ui.button_arc_end_plus5.clicked.connect(lambda: self._set_arc_end_days_after_start(5))

    def _comment_out_solar_panel_area(self):
        """隐藏当前界面暂不使用的太阳帆板面积输入项。"""
        self.ui.label_arc_solar_panel_area.hide()
        self.ui.edit_arc_solar_panel_area.hide()

    def _remove_albedo_radiation_row(self):
        """隐藏反照辐射相关行并禁用对应开关。"""
        for widget_name in ("row_arc_albedo_radiation", "separator_arc_albedo_radiation"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        self.ui.label_arc_albedo_radiation.hide()
        self.ui.check_arc_albedo_radiation.hide()

    def _comment_out_doppler_inverse_time(self):
        """隐藏多普勒积分时间输入项，保留内部默认处理。"""
        self.ui.label_arc_doppler_inverse_time.hide()
        self.ui.edit_arc_doppler_inverse_time.hide()

    def _replace_orbit_step_edits(self):
        """用下拉框替换积分步长和输出步长的自由文本输入。"""
        self.ui.combo_arc_integration_step = self._ensure_step_combo(
            "combo_arc_integration_step",
            self.ui.edit_arc_integration_step_legacy,
            self.ui.horizontalLayout_27,
        )
        self.ui.combo_arc_output_step = self._ensure_step_combo(
            "combo_arc_output_step",
            self.ui.edit_arc_output_step_legacy,
            self.ui.horizontalLayout_27,
        )

        step_font = QFont("Microsoft YaHei", 8)
        for widget in (
            self.ui.label_arc_integration_step,
            self.ui.combo_arc_integration_step,
            self.ui.label_arc_output_step,
            self.ui.combo_arc_output_step,
        ):
            widget.setFont(step_font)

    def _ensure_step_combo(self, name, old_edit, layout):
        """创建或复用步长下拉框，并接管旧输入框在布局中的位置。"""
        combo = getattr(self.ui, name, None)
        if combo is None:
            combo = QComboBox(old_edit.parent())
            combo.setObjectName(name)
            combo.addItems(["10", "60"])
            setattr(self.ui, name, combo)

        value = self._normalize_step_value(old_edit.text())
        if value and combo.findText(value) < 0:
            combo.addItem(value)
        if value:
            combo.setCurrentText(value)

        old_index = layout.indexOf(old_edit)
        combo_index = layout.indexOf(combo)
        if combo_index < 0:
            layout.insertWidget(old_index if old_index >= 0 else layout.count(), combo)
        old_edit.hide()
        old_edit.setEnabled(False)
        combo.show()
        combo.setMinimumHeight(18)
        combo.setMaximumHeight(22)
        return combo

    @staticmethod
    def _normalize_step_value(value):
        """规范化步长数值文本，支持 D/E 科学计数法。"""
        text = str(value or "").strip()
        if not text:
            return "60"
        try:
            numeric = float(text.replace("D", "E").replace("d", "e"))
        except ValueError:
            return text
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:g}"

    def _remove_arc_derivative_filter_rows(self):
        """隐藏轨道偏导和观测滤波相关行，避免未开放功能被误用。"""
        for widget_name in ("row_arc_derivative_filter", "separator_arc_derivative_filter"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        for widget in (
            self.ui.label_arc_partial_derivative_step,
            self.ui.edit_arc_partial_derivative_step,
            self.ui.label_arc_position_derivative_step,
            self.ui.edit_arc_position_derivative_step,
            self.ui.label_arc_velocity_derivative_step,
            self.ui.edit_arc_velocity_derivative_step,
            self.ui.label_arc_input_filter,
            self.ui.combo_arc_input_filter,
        ):
            widget.hide()
            widget.setEnabled(False)

    def _remove_spice_kernel_path_row(self):
        """隐藏 SPICE 内核路径输入行，new 版本改用固定资源目录。"""
        for widget_name in ("row_arc_spice_kernel_path", "separator_arc_spice_kernel"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        self.ui.label_arc_spice_kernel_path.hide()
        self.ui.edit_arc_spice_kernel_path.hide()
        self.ui.edit_arc_spice_kernel_path.setEnabled(False)

    def _align_arc_parameter_labels(self):
        """统一弧段参数页标签的右对齐方式。"""
        labels = (
            self.ui.label_arc_satellite_id,
            self.ui.label_arc_initial_frame,
            self.ui.label_arc_initial_orbit_type,
            self.ui.label_arc_satellite_mass,
            self.ui.label_arc_body_area,
            self.ui.label_arc_solar_pressure_coefficient,
            self.ui.label_arc_solar_pressure_prior_error,
            self.ui.label_arc_start_time,
            self.ui.label_arc_end_time,
            self.ui.label_arc_initial_position,
            self.ui.label_arc_initial_velocity,
            self.ui.label_arc_position_prior,
            self.ui.label_arc_velocity_prior,
            self.ui.label_arc_doppler_integration_time,
            self.ui.label_arc_integration_step,
            self.ui.label_arc_output_step,
        )
        for label in labels:
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _align_arc_first_column(self):
        """统一弧段参数页第一列标签宽度和左侧边距。"""
        first_column_width = 168
        left_margin = 24
        for layout, label in (
            (self.ui.horizontalLayout_17, self.ui.label_arc_satellite_id),
            (self.ui.horizontalLayout_18, self.ui.label_arc_satellite_mass),
            (self.ui.horizontalLayout_19, self.ui.label_arc_solar_pressure_coefficient),
            (self.ui.horizontalLayout_21, self.ui.label_arc_start_time),
            (self.ui.horizontalLayout_22, self.ui.label_arc_initial_position),
            (self.ui.horizontalLayout_23, self.ui.label_arc_initial_velocity),
            (self.ui.horizontalLayout_24, self.ui.label_arc_position_prior),
            (self.ui.horizontalLayout_25, self.ui.label_arc_velocity_prior),
            (self.ui.horizontalLayout_26, self.ui.label_arc_doppler_integration_time),
            (self.ui.horizontalLayout_27, self.ui.label_arc_integration_step),
        ):
            layout.setSpacing(4)
            self._set_spacer_width(layout, 0, left_margin)
            self._set_widget_width(label, first_column_width)

    def _set_arc_start_to_now(self):
        """把弧段起止时刻同步设置为当前系统时间。"""
        current = QDateTime.currentDateTime()
        self.ui.date_arc_start_time.setDateTime(current)
        self.ui.date_arc_end_time.setDateTime(current)

    def _set_arc_end_days_after_start(self, days):
        """按起始时刻向后推指定天数设置弧段结束时刻。"""
        self.ui.date_arc_end_time.setDateTime(self.ui.date_arc_start_time.dateTime().addDays(days))

    @staticmethod
    def _lock_widgets(*widgets):
        """禁用一组控件并保留其显示状态。"""
        for widget in widgets:
            widget.setEnabled(False)

    def _ensure_observation_weight_help_button(self):
        """确保观测值权重表旁存在“说明”按钮并连接帮助弹窗。"""
        button = getattr(self.ui, "pushButton_obs_weight_help", None)
        if button is None:
            button = QPushButton("说明", self.ui.group_arc_observation_weight)
            button.setObjectName("pushButton_obs_weight_help")
            self.ui.pushButton_obs_weight_help = button
        button.setText("说明")
        button.setToolTip("查看观测值类型和权重说明")
        button.setGeometry(self.ui.button_arc_observation_weight_delete.x(), self.ui.button_arc_observation_weight_delete.y() + 30, self.ui.button_arc_observation_weight_delete.width(), self.ui.button_arc_observation_weight_delete.height())
        if not button.property("help_connected"):
            button.clicked.connect(self.show_observation_weight_help)
            button.setProperty("help_connected", True)

    def _apply_layout_polish(self):
        """设置主窗口初始尺寸、工具栏按钮位置和基础布局边距。"""
        self.resize(1040, 720)
        self.setMinimumSize(1000, 680)
        self.ui.centralwidget.setMinimumSize(1000, 0)
        self.ui.verticalLayoutWidget.setGeometry(16, 48, 1008, 620)
        self.ui.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.verticalLayout.setSpacing(0)
        self.ui.tabWidget.setDocumentMode(True)

        toolbar_buttons = [
            self.ui.button_new_scheme,
            self.ui.button_open_scheme,
            self.ui.button_save_scheme,
            self.ui.button_save_scheme_as,
            self.ui.button_start_orbit,
            self.ui.button_show_chart,
        ]
        x = 18
        for index, button in enumerate(toolbar_buttons):
            if index == 4:
                x += 18
            button.setGeometry(x, 8, 34, 34)
            button.setIconSize(QSize(22, 22))
            x += 40

    def _apply_style(self):
        """应用全局 Qt 样式表，统一窗口、表格、按钮和输入框外观。"""
        self.setStyleSheet(
            """
            QMainWindow, QWidget#centralwidget {
                background: #f3f6fa;
                color: #1f2937;
                font-family: "Microsoft YaHei", "Segoe UI", Arial;
                font-size: 8pt;
            }
            QMenuBar {
                background: #eef3f8;
                color: #1f2937;
                border-bottom: 1px solid #d7e0ea;
                padding: 1px 8px;
            }
            QMenuBar::item {
                padding: 3px 9px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #dbeafe;
            }
            QStatusBar {
                background: #eef3f8;
                color: #526173;
                border-top: 1px solid #d7e0ea;
            }
            QTabWidget::pane {
                border: 1px solid #ccd7e3;
                background: #ffffff;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e8eef5;
                color: #475569;
                padding: 5px 14px;
                border: 1px solid #ccd7e3;
                border-bottom: none;
                min-width: 78px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0f172a;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background: #f8fafc;
            }
            QLabel {
                color: #344256;
                padding: 0 3px 0 0;
            }
            QLineEdit, QComboBox, QSpinBox, QDateTimeEdit {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 3px;
                min-height: 16px;
                max-height: 20px;
                padding: 0 4px;
                selection-background-color: #bfdbfe;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateTimeEdit:focus {
                border: 1px solid #3b82f6;
            }
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDateTimeEdit:disabled {
                background: #e2e8f0;
                color: #8a97a8;
                border: 1px solid #b8c4d2;
            }
            QLabel:disabled, QCheckBox:disabled {
                color: #9aa7b8;
            }
            QCheckBox {
                spacing: 5px;
                color: #334155;
            }
            QCheckBox::indicator:disabled {
                background: #d9e1ea;
                border: 1px solid #aebacc;
            }
            QPushButton, QToolButton {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 1px 7px;
                color: #263445;
            }
            QPushButton:hover, QToolButton:hover {
                background: #eff6ff;
                border-color: #93c5fd;
            }
            QPushButton:pressed, QToolButton:pressed {
                background: #dbeafe;
            }
            QGroupBox {
                border: 1px solid #d4dde8;
                border-radius: 6px;
                margin-top: 10px;
                background: #fbfdff;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #1f3b57;
            }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f8fafc;
                gridline-color: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }
            QHeaderView::section {
                background: #eaf0f7;
                color: #243447;
                border: none;
                border-right: 1px solid #d7e0ea;
                border-bottom: 1px solid #d7e0ea;
                padding: 3px 5px;
                font-weight: 600;
            }
            QTextEdit {
                background: #0f172a;
                color: #dbeafe;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, "Microsoft YaHei";
            }
            """
        )

    def _align_text_widgets(self):
        """统一标签、输入控件、按钮和分隔线的尺寸与对齐方式。"""
        section_labels = {
            "label_planet_gravity_section", "label_output_orbit_solution", "label_output_ephemeris_solution", "label_visual_orbit_plot", "label_visual_residual_plot",
            "label_simulation_import_card", "label_simulation_generate_observations",
        }
        for label in self.findChildren(QLabel):
            if label.objectName() in section_labels:
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setMinimumHeight(16)
            label.setMaximumHeight(22)

        for editor in self.findChildren(QLineEdit):
            editor.setMinimumHeight(16)
            editor.setMaximumHeight(20)
        for combo in self.findChildren(QComboBox):
            combo.setMinimumHeight(16)
            combo.setMaximumHeight(20)
        for spin in self.findChildren(QSpinBox):
            spin.setMinimumHeight(16)
            spin.setMaximumHeight(20)
        for date_edit in self.findChildren(QDateTimeEdit):
            date_edit.setMinimumHeight(16)
            date_edit.setMaximumHeight(20)
        for checkbox in self.findChildren(QCheckBox):
            checkbox.setMinimumHeight(16)
            checkbox.setMaximumHeight(20)
        for button in self.findChildren(QPushButton):
            if button not in {
                self.ui.button_new_scheme,
                self.ui.button_open_scheme,
                self.ui.button_save_scheme,
                self.ui.button_save_scheme_as,
                self.ui.button_start_orbit,
                self.ui.button_show_chart,
            }:
                button.setMinimumHeight(18)
                button.setMaximumHeight(22)
        for tool_button in self.findChildren(QToolButton):
            tool_button.setMinimumHeight(18)
            tool_button.setMaximumHeight(22)
        for group in self.findChildren(QGroupBox):
            group.setAlignment(Qt.AlignLeft)
        for frame in self.findChildren(QFrame):
            if frame.frameShape() in (QFrame.HLine, QFrame.VLine):
                frame.setStyleSheet("")
                frame.setLineWidth(1)
                frame.setMidLineWidth(0)

    def _set_spacer_width(self, layout, index, width):
        """把指定布局项中的 spacer 调整为固定宽度。"""
        item = layout.itemAt(index)
        if item and item.spacerItem():
            item.spacerItem().changeSize(width, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

    def _set_expanding_spacer(self, layout, index, width=0):
        """把指定布局项中的 spacer 调整为可扩展宽度。"""
        item = layout.itemAt(index)
        if item and item.spacerItem():
            item.spacerItem().changeSize(width, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

    def _ensure_trailing_expander(self, layout):
        """为布局末尾补一个只添加一次的弹性伸展项。"""
        if not layout.property("trailing_expander_added"):
            layout.addStretch(1)
            layout.setProperty("trailing_expander_added", True)

    def _set_widget_width(self, widget, width):
        """把控件宽度固定到指定值，同时保留原有垂直尺寸策略。"""
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)
        widget.setSizePolicy(QSizePolicy.Fixed, widget.sizePolicy().verticalPolicy())

    def _refresh_layout(self, layout):
        """强制布局重新计算几何尺寸并立即生效。"""
        layout.invalidate()
        layout.activate()

    def _apply_global_page_layout(self):
        """根据窗口宽度重排全局参数页的各行控件和行星参数区。"""
        page_width = max(self.ui.page_global_parameters.width() - 8, 980)
        rows = [
            self.ui.row_global_run_mode,
            self.ui.row_global_integration_center,
            self.ui.row_global_central_gravity,
            self.ui.row_global_gravity_field,
            self.ui.row_global_third_body_ephemeris,
            self.ui.row_global_planet_gravity_header,
            self.ui.row_global_mercury_venus_gravity,
            self.ui.row_global_earth_mars_gravity,
            self.ui.row_global_jupiter_saturn_gravity,
            self.ui.row_global_uranus_neptune_gravity,
            self.ui.row_global_pluto_moon_gravity,
            self.ui.row_global_sun_gravity,
            self.ui.row_global_relativity,
            self.ui.row_global_solar_pressure,
            self.ui.row_global_solid_tide,
            self.ui.row_global_troposphere,
        ]
        for row in rows:
            row.setGeometry(0, row.geometry().y(), page_width, row.geometry().height())
            if row.layout():
                row.layout().setContentsMargins(0, 0, 0, 0)
                row.layout().setSpacing(6)

        for line_name in ("separator_global_run_mode", "separator_global_integration_center", "separator_global_gravity_field", "separator_global_third_body", "separator_global_planet_gravity", "separator_global_relativity", "separator_global_solar_pressure", "separator_global_solid_tide", "separator_global_troposphere"):
            separator = getattr(self.ui, line_name, None)
            if separator:
                separator.setGeometry(0, separator.geometry().y(), page_width, separator.geometry().height())

        left = 48
        label_w = 136
        short_w = 120
        check_w = 74
        mid_w = 170
        gm_w = 178
        radius_w = 140
        planet_label_w = 58
        section_w = 112
        inner_gap = 6
        pair_gap = 30
        header_pair_gap = 92

        top_specs = [
            (self.ui.horizontalLayout, 0, [("label_run_mode", label_w), ("combo_run_mode", short_w)]),
            (self.ui.horizontalLayout_2, 0, [("label_integration_center", label_w), ("combo_integration_center", short_w)]),
            (self.ui.horizontalLayout_3, 0, [("label_central_gravity_field", label_w), ("check_central_gravity_field", check_w)]),
        ]
        for layout, spacer_index, widgets in top_specs:
            self._set_spacer_width(layout, spacer_index, left)
            self._set_expanding_spacer(layout, layout.count() - 1)
            for name, width in widgets:
                self._set_widget_width(getattr(self.ui, name), width)
            self._refresh_layout(layout)

        layout = self.ui.horizontalLayout_4
        layout.setSpacing(0)
        self._set_spacer_width(layout, 0, left)
        self._set_widget_width(self.ui.label_gravity_file_format, label_w)
        self._set_widget_width(self.ui.combo_gravity_file_format, short_w)
        self._set_spacer_width(layout, 3, 24)
        self._set_widget_width(self.ui.label_gravity_degree, label_w)
        self._set_widget_width(self.ui.spin_gravity_degree, 72)
        self._set_spacer_width(layout, 6, 0)
        if self.ui.label_gravity_inversion_degree.isVisible():
            self._set_widget_width(self.ui.label_gravity_inversion_degree, label_w)
        if self.ui.spin_gravity_inversion_degree.isVisible():
            self._set_widget_width(self.ui.spin_gravity_inversion_degree, 72)
        self._ensure_trailing_expander(layout)
        self._set_expanding_spacer(layout, layout.count() - 1)
        self._refresh_layout(layout)

        layout = self.ui.horizontalLayout_5
        layout.setSpacing(4)
        self._set_spacer_width(layout, 0, left)
        self._set_widget_width(self.ui.label_third_body_ephemeris, label_w)
        for name in ("check_third_body_mercury", "check_third_body_venus", "check_third_body_earth", "check_third_body_mars", "check_third_body_jupiter", "check_third_body_uranus", "check_third_body_neptune", "check_third_body_pluto", "check_third_body_moon", "check_third_body_sun"):
            self._set_widget_width(getattr(self.ui, name), 58)
        self._set_spacer_width(layout, 12, 10)
        self._set_widget_width(self.ui.combo_ephemeris_model, 126)
        self._refresh_layout(layout)

        header = self.ui.horizontalLayout_6
        header.setSpacing(4)
        self._set_widget_width(self.ui.label_planet_gravity_section, section_w)
        self._set_spacer_width(header, 1, 0)
        self._set_widget_width(self.ui.label_planet_gm_header_left, gm_w)
        self._set_spacer_width(header, 3, 0)
        self._set_widget_width(self.ui.label_planet_radius_header_left, radius_w)
        self._set_spacer_width(header, 5, header_pair_gap)
        self._set_widget_width(self.ui.label_planet_gm_header_right, gm_w)
        self._set_spacer_width(header, 7, 0)
        self._set_widget_width(self.ui.label_planet_radius_header_right, radius_w)
        for label in (self.ui.label_planet_gm_header_left, self.ui.label_planet_radius_header_left, self.ui.label_planet_gm_header_right, self.ui.label_planet_radius_header_right):
            label.setAlignment(Qt.AlignCenter)
        self._set_expanding_spacer(header, 9)
        self._refresh_layout(header)

        planet_rows = [
            ("horizontalLayout_7", "label_mercury_gravity", "edit_mercury_gm", "edit_mercury_radius", "label_venus_gravity", "edit_venus_gm", "edit_venus_radius"),
            ("horizontalLayout_8", "label_earth_gravity", "edit_earth_gm", "edit_earth_radius", "label_mars_gravity", "edit_mars_gm", "edit_mars_radius"),
            ("horizontalLayout_9", "label_jupiter_gravity", "edit_jupiter_gm", "edit_jupiter_radius", "label_saturn_gravity", "edit_saturn_gm", "edit_saturn_radius"),
            ("horizontalLayout_10", "label_uranus_gravity", "edit_uranus_gm", "edit_uranus_radius", "label_neptune_gravity", "edit_neptune_gm", "edit_neptune_radius"),
            ("horizontalLayout_11", "label_pluto_gravity", "edit_pluto_gm", "edit_pluto_radius", "label_moon_gravity", "edit_moon_gm", "edit_moon_radius"),
        ]
        for layout_name, l1, gm1, r1, l2, gm2, r2 in planet_rows:
            layout = getattr(self.ui, layout_name)
            layout.setSpacing(4)
            self._set_spacer_width(layout, 0, left)
            self._set_widget_width(getattr(self.ui, l1), planet_label_w)
            self._set_spacer_width(layout, 2, inner_gap)
            self._set_widget_width(getattr(self.ui, gm1), gm_w)
            self._set_widget_width(getattr(self.ui, r1), radius_w)
            self._set_spacer_width(layout, 5, pair_gap)
            self._set_widget_width(getattr(self.ui, l2), planet_label_w)
            self._set_widget_width(getattr(self.ui, gm2), gm_w)
            self._set_widget_width(getattr(self.ui, r2), radius_w)
            self._ensure_trailing_expander(layout)
            self._refresh_layout(layout)

        sun = self.ui.horizontalLayout_12
        sun.setSpacing(4)
        self._set_spacer_width(sun, 0, left)
        self._set_spacer_width(sun, 1, 0)
        self._set_spacer_width(sun, 2, 0)
        self._set_widget_width(self.ui.label_sun_gravity, planet_label_w)
        self._set_spacer_width(sun, 4, inner_gap)
        self._set_widget_width(self.ui.edit_sun_gm, gm_w)
        self._set_widget_width(self.ui.edit_sun_radius, radius_w)
        self._set_expanding_spacer(sun, 7)
        self._refresh_layout(sun)

        for layout, spacer, label, checkbox in [
            (self.ui.horizontalLayout_13, 0, self.ui.label_relativity_perturbation, self.ui.check_relativity_perturbation),
            (self.ui.horizontalLayout_14, 0, self.ui.label_solar_pressure_perturbation, self.ui.check_solar_radiation_pressure),
            (self.ui.horizontalLayout_15, 0, self.ui.label_solid_tide_perturbation, self.ui.check_solid_tide_perturbation),
            (self.ui.horizontalLayout_16, 0, self.ui.label_troposphere_delay, self.ui.check_troposphere_delay),
        ]:
            layout.setSpacing(0)
            self._set_spacer_width(layout, spacer, left)
            self._set_widget_width(label, label_w)
            self._set_widget_width(checkbox, check_w)
            self._ensure_trailing_expander(layout)
            self._set_expanding_spacer(layout, layout.count() - 1)
            self._refresh_layout(layout)

        self._set_spacer_width(self.ui.horizontalLayout_14, 3, 140)
        self._set_widget_width(self.ui.label_solar_pressure_model, 166)
        self._set_widget_width(self.ui.combo_solar_pressure_model, mid_w)
        self._refresh_layout(self.ui.horizontalLayout_14)

        self._set_spacer_width(self.ui.horizontalLayout_15, 3, 80)
        self._set_widget_width(self.ui.label_solid_tide_k2_love_number, 154)
        self._set_widget_width(self.ui.edit_solid_tide_k2_love_number, 150)
        self._set_spacer_width(self.ui.horizontalLayout_15, 6, 30)
        self._set_widget_width(self.ui.label_solid_tide_prior_error, 94)
        self._set_widget_width(self.ui.edit_solid_tide_prior_error, 130)
        self._refresh_layout(self.ui.horizontalLayout_15)

        self._set_spacer_width(self.ui.horizontalLayout_16, 3, 140)
        self._set_widget_width(self.ui.label_troposphere_model, 166)
        self._set_widget_width(self.ui.combo_troposphere_model, 150)
        self._set_widget_width(self.ui.label_integrator_selection, 112)
        self._set_widget_width(self.ui.combo_integrator_type, 120)
        self._refresh_layout(self.ui.horizontalLayout_16)

    def _page_size(self, page):
        """计算页面可用宽高，并给响应式布局提供最小尺寸。"""
        return max(page.width() - 8, 980), max(page.height() - 8, 560)

    def _stretch_width(self, widget, width):
        """把控件从当前位置拉伸到指定页面宽度。"""
        geometry = widget.geometry()
        widget.setGeometry(geometry.x(), geometry.y(), max(width - geometry.x(), 1), geometry.height())

    def _stretch_layout_rows(self, names, width):
        """按对象名批量拉伸横向布局容器。"""
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget:
                self._stretch_width(widget, width)
                if widget.layout():
                    widget.layout().invalidate()

    def _move_button_column(self, buttons, x):
        """把一组表格侧边按钮移动到同一纵列。"""
        for button in buttons:
            geometry = button.geometry()
            button.setGeometry(x, geometry.y(), geometry.width(), geometry.height())

    def _fill_table_with_side_buttons(self, table, buttons, page_width, page_height, bottom_margin=12):
        """让表格填满页面剩余区域，并把操作按钮放到表格右侧。"""
        table_geometry = table.geometry()
        button_width = max(button.width() for button in buttons)
        button_x = max(page_width - button_width - 10, table_geometry.x() + 280)
        table_width = max(button_x - table_geometry.x() - 9, 320)
        table_height = max(page_height - table_geometry.y() - bottom_margin, 120)
        table.setGeometry(table_geometry.x(), table_geometry.y(), table_width, table_height)
        self._move_button_column(buttons, button_x)

    def _fill_group_table_with_side_buttons(self, group, table, buttons):
        """在分组框内调整表格和右侧按钮列的宽高。"""
        table_geometry = table.geometry()
        button_width = max(button.width() for button in buttons)
        button_x = max(group.width() - button_width - 10, table_geometry.x() + 180)
        table_width = max(button_x - table_geometry.x() - 9, 180)
        table_height = max(group.height() - table_geometry.y() - 10, 80)
        table.setGeometry(table_geometry.x(), table_geometry.y(), table_width, table_height)
        self._move_button_column(buttons, button_x)

    def _fill_group_table_below_buttons(self, group, table):
        """让分组框内无侧边按钮的表格填满下方空间。"""
        geometry = table.geometry()
        table.setGeometry(
            geometry.x(),
            geometry.y(),
            max(group.width() - geometry.x() - 10, 180),
            max(group.height() - geometry.y() - 10, 80),
        )

    def _apply_arc_page_layout(self, page_width, page_height):
        """重排弧段参数页和内部观测/经验加速度页签的响应式布局。"""
        self._compact_arc_parameter_rows()
        self._compact_arc_integrator_gap()
        self._stretch_layout_rows(
            [
                "row_arc_satellite_identity",
                "row_arc_mass_area",
                "row_arc_solar_pressure",
                "row_arc_albedo_radiation",
                "row_arc_time_span",
                "row_arc_initial_position",
                "row_arc_initial_velocity",
                "row_arc_position_prior",
                "row_arc_velocity_prior",
                "row_arc_doppler_settings",
                "row_arc_step_settings",
                "row_arc_integrator_type",
                "row_arc_derivative_filter",
                "row_arc_spice_kernel_path",
            ],
            page_width,
        )
        separator_width = max(self.ui.page_arc_parameters.width(), page_width)
        for line_name in (
            "separator_arc_mass_area",
            "separator_arc_solar_pressure",
            "separator_arc_albedo_radiation",
            "separator_arc_time_span",
            "separator_arc_prior_errors",
            "separator_arc_step_settings",
            "separator_arc_integrator_type",
            "separator_arc_internal_tabs",
            "separator_arc_derivative_filter",
            "separator_arc_spice_kernel",
        ):
            separator = getattr(self.ui, line_name, None)
            if separator:
                self._stretch_width(separator, separator_width)

        self._align_arc_first_column()

        time_layout = self.ui.horizontalLayout_21
        for label in (
            self.ui.label_arc_initial_frame,
            self.ui.label_arc_initial_orbit_type,
        ):
            self._set_widget_width(label, 150)

        self._set_widget_width(self.ui.date_arc_start_time, 185)
        self._set_widget_width(self.ui.button_arc_start_now, 48)
        self._set_spacer_width(time_layout, 4, 24)
        self._set_widget_width(self.ui.label_arc_end_time, 150)
        self._set_widget_width(self.ui.date_arc_end_time, 185)
        self._set_widget_width(self.ui.button_arc_end_plus7, 48)
        self._set_widget_width(self.ui.button_arc_end_plus5, 48)
        self._set_expanding_spacer(time_layout, 9)
        self._refresh_layout(time_layout)

        self._set_widget_width(self.ui.edit_arc_satellite_mass, 96)
        self._set_spacer_width(self.ui.horizontalLayout_18, 3, 16)
        self._set_widget_width(self.ui.label_arc_body_area, 150)
        self._set_widget_width(self.ui.edit_arc_body_area, 78)
        self._set_expanding_spacer(self.ui.horizontalLayout_18, self.ui.horizontalLayout_18.count() - 1)
        self._set_widget_width(self.ui.edit_arc_solar_pressure_coefficient, 96)
        self._set_spacer_width(self.ui.horizontalLayout_19, 3, 16)
        self._set_widget_width(self.ui.label_arc_solar_pressure_prior_error, 86)
        self._set_widget_width(self.ui.edit_arc_solar_pressure_prior_error, 96)
        self._set_expanding_spacer(self.ui.horizontalLayout_19, self.ui.horizontalLayout_19.count() - 1)
        self._set_widget_width(self.ui.edit_arc_doppler_integration_time, 76)
        self._set_widget_width(self.ui.combo_arc_integration_step, 76)
        self._set_widget_width(self.ui.label_arc_output_step, 150)
        self._set_widget_width(self.ui.combo_arc_output_step, 76)
        self._set_expanding_spacer(self.ui.horizontalLayout_26, self.ui.horizontalLayout_26.count() - 1)
        self._set_expanding_spacer(self.ui.horizontalLayout_27, self.ui.horizontalLayout_27.count() - 1)
        for layout in (
            self.ui.horizontalLayout_17,
            self.ui.horizontalLayout_18,
            self.ui.horizontalLayout_19,
            self.ui.horizontalLayout_21,
            self.ui.horizontalLayout_22,
            self.ui.horizontalLayout_23,
            self.ui.horizontalLayout_24,
            self.ui.horizontalLayout_25,
            self.ui.horizontalLayout_26,
            self.ui.horizontalLayout_27,
        ):
            layout.setSpacing(4)
            self._refresh_layout(layout)
        self._refresh_layout(self.ui.horizontalLayout_27)

        tab_geometry = self.ui.tabs_arc_parameter_details.geometry()
        self.ui.tabs_arc_parameter_details.setGeometry(
            tab_geometry.x(),
            tab_geometry.y(),
            max(page_width - tab_geometry.x(), 640),
            max(page_height - tab_geometry.y() + 8, 220),
        )

        sub_width = max(self.ui.tabs_arc_parameter_details.width() - 8, 940)
        sub_height = max(self.ui.tabs_arc_parameter_details.height() - 28, 210)
        half_width = sub_width // 2

        for left_group, right_group in ((self.ui.group_arc_observation_weight, self.ui.group_arc_measurement_bias), (self.ui.group_arc_per_acc_period, self.ui.group_arc_per_acc_model)):
            top = left_group.geometry().y()
            left_group.setGeometry(0, top, half_width, max(sub_height - top, 140))
            right_group.setGeometry(half_width, top, sub_width - half_width - 8, left_group.height())

        weight_buttons = [self.ui.button_arc_observation_weight_add, self.ui.button_arc_observation_weight_edit, self.ui.button_arc_observation_weight_delete]
        if hasattr(self.ui, "pushButton_obs_weight_help"):
            weight_buttons.append(self.ui.pushButton_obs_weight_help)
        self._fill_group_table_with_side_buttons(self.ui.group_arc_observation_weight, self.ui.table_arc_observation_weight, weight_buttons)
        self._fill_group_table_with_side_buttons(self.ui.group_arc_measurement_bias, self.ui.table_arc_measurement_bias, [self.ui.button_arc_measurement_bias_add, self.ui.button_arc_measurement_bias_edit, self.ui.button_arc_measurement_bias_delete])
        self._fill_group_table_below_buttons(self.ui.group_arc_per_acc_period, self.ui.table_arc_per_acc_period)
        self._fill_group_table_below_buttons(self.ui.group_arc_per_acc_model, self.ui.table_arc_per_acc_model)

        for table, buttons in (
            (self.ui.table_arc_fixed_measurement_bias, [self.ui.button_arc_fixed_bias_add, self.ui.button_arc_fixed_bias_edit, self.ui.button_arc_fixed_bias_delete]),
            (self.ui.table_arc_select_observation, [self.ui.button_arc_select_observation_add, self.ui.button_arc_select_observation_edit, self.ui.button_arc_select_observation_delete]),
            (self.ui.table_arc_delete_observation, [self.ui.button_arc_delete_observation_add, self.ui.button_arc_delete_observation_edit, self.ui.button_arc_delete_observation_delete]),
        ):
            self._fill_table_with_side_buttons(table, buttons, sub_width, sub_height, bottom_margin=0)
        self._fit_observation_bias_columns()
        self._fit_select_observation_columns()

        self._stretch_layout_rows(["horizontalLayoutWidget_31"], sub_width)

    def _apply_secondary_pages_layout(self):
        """重排模拟观测、测站参数、运行日志和图表页面的布局。"""
        page_width, page_height = self._page_size(self.ui.page_arc_parameters)
        self._apply_arc_page_layout(page_width, page_height)

        for page, row_names, table, buttons in (
            (self.ui.page_simulation_observations, ["row_simulation_card_actions"], self.ui.table_simulated_observations, [self.ui.button_simulation_observation_add, self.ui.button_simulation_observation_edit, self.ui.button_simulation_observation_delete]),
            (self.ui.page_station_parameters, ["row_station_global_settings"], self.ui.table_station_parameters, [self.ui.button_station_add, self.ui.button_station_edit, self.ui.button_station_delete]),
        ):
            page_width, page_height = self._page_size(page)
            self._stretch_layout_rows(row_names, page_width)
            self._fill_table_with_side_buttons(table, buttons, page_width, page_height)
            if table is self.ui.table_station_parameters:
                self._fit_station_columns()

        page_width, page_height = self._page_size(self.ui.page_orbit_output)
        self.ui.group_orbit_process.setGeometry(
            0,
            0,
            max(page_width, 320),
            max(page_height, 160),
        )
        self._stretch_layout_rows(["row_orbit_process_actions"], self.ui.group_orbit_process.width())
        text_geometry = self.ui.text_orbit_process_log.geometry()
        self.ui.text_orbit_process_log.setGeometry(
            text_geometry.x(),
            text_geometry.y(),
            max(self.ui.group_orbit_process.width() - text_geometry.x(), 320),
            max(self.ui.group_orbit_process.height() - text_geometry.y() - 10, 100),
        )

        page_width, page_height = self._page_size(self.ui.page_visual_analysis)
        self._stretch_layout_rows(["row_visual_analysis_actions"], page_width)
        visual_geometry = self.ui.panel_visual_canvas.geometry()
        self.ui.panel_visual_canvas.setGeometry(
            visual_geometry.x(),
            visual_geometry.y(),
            max(page_width - visual_geometry.x(), 320),
            max(page_height - visual_geometry.y(), 160),
        )

    def _refresh_responsive_layout(self):
        """在窗口尺寸变化后刷新主布局和各页面响应式布局。"""
        if hasattr(self, "ui"):
            self.ui.verticalLayoutWidget.setGeometry(16, 48, max(self.width() - 32, 968), max(self.height() - 100, 580))
            self._apply_global_page_layout()
            self._apply_secondary_pages_layout()

    def _schedule_layout_refresh(self, *_):
        """延迟触发布局刷新，确保页签切换后控件尺寸已更新。"""
        QTimer.singleShot(0, self._refresh_responsive_layout)
        QTimer.singleShot(50, self._refresh_responsive_layout)

    def resizeEvent(self, event):
        """响应窗口缩放事件并重新计算页面布局。"""
        super().resizeEvent(event)
        self._refresh_responsive_layout()

    def showEvent(self, event):
        """响应窗口首次显示事件，安排一次完整布局刷新。"""
        super().showEvent(event)
        self._schedule_layout_refresh()

    def _apply_toolbar_icons(self):
        """为顶部工具栏按钮加载图标并设置提示文本。"""
        buttons = [
            (self.ui.button_new_scheme, "new_scheme.png", "新建定轨方案"),
            (self.ui.button_open_scheme, "open_scheme.png", "打开定轨方案"),
            (self.ui.button_save_scheme, "save_scheme.png", "保存定轨方案"),
            (self.ui.button_save_scheme_as, "save_as_scheme.png", "另存为定轨方案"),
            (self.ui.button_start_orbit, "run_orbit.png", "开始定轨"),
            (self.ui.button_show_chart, "chart.png", "查看图表"),
        ]
        for button, icon_name, tooltip in buttons:
            path = iconsource_rc.icon_path(icon_name)
            if Path(path).exists():
                button.setIcon(QIcon(path))
                button.setIconSize(QSize(20, 20))
                button.setText("")
            button.setToolTip(tooltip)

    def _connect_signals(self):
        """连接菜单、按钮、表格和任务控制相关的 Qt 信号。"""
        self.ui.tabWidget.currentChanged.connect(self._schedule_layout_refresh)
        self.ui.tabs_arc_parameter_details.currentChanged.connect(self._schedule_layout_refresh)
        self.ui.combo_integration_center.currentIndexChanged.connect(self._sync_integration_center_controls)
        self.ui.table_arc_observation_weight.itemChanged.connect(self._on_observation_weight_item_changed)
        self.ui.table_arc_select_observation.itemChanged.connect(self._on_select_observation_item_changed)
        self.ui.table_simulated_observations.itemChanged.connect(self._on_simulation_observation_item_changed)
        self.ui.table_arc_per_acc_model.itemChanged.connect(self._on_per_acc_item_changed)

        self.ui.button_new_scheme.clicked.connect(self.new_scheme)
        self.ui.button_open_scheme.clicked.connect(self.open_scheme)
        self.ui.button_save_scheme.clicked.connect(self.save_scheme)
        self.ui.button_save_scheme_as.clicked.connect(self.save_scheme_as)
        self.ui.button_start_orbit.clicked.connect(self.start_orbit_determination)
        self.ui.button_show_chart.clicked.connect(lambda: self.ui.tabWidget.setCurrentWidget(self.ui.page_visual_analysis))

        self.ui.action_new_scheme.triggered.connect(self.new_scheme)
        self.ui.action_open_scheme.triggered.connect(self.open_scheme)
        self.ui.action_save_scheme.triggered.connect(self.save_scheme)
        self.ui.action_save_scheme_as.triggered.connect(self.save_scheme_as)
        self.ui.action_import_gcp_card.triggered.connect(lambda: self.import_card("GCP"))
        self.ui.action_import_lcp_card.triggered.connect(lambda: self.import_card("LCP"))
        self.ui.action_import_simcp_card.triggered.connect(lambda: self.import_card("SimCP"))
        self.ui.action_import_stacp_card.triggered.connect(lambda: self.import_card("StaCP"))
        self.ui.action_start_orbit.triggered.connect(self.start_orbit_determination)
        self.ui.action_show_chart.triggered.connect(lambda: self.ui.tabWidget.setCurrentWidget(self.ui.page_visual_analysis))
        self.ui.action_show_about.triggered.connect(self.show_about)

        self.ui.tool_simulation_import_card.clicked.connect(lambda: self.import_card("SimCP"))
        self.ui.tool_simulation_generate_observations.clicked.connect(self.configure_and_generate_observations)
        # 全局/弧段参数解算和小行星星历解算入口已停用，仅保留定轨过程。
        # self.ui.tool_output_start_orbit_solution.clicked.connect(self.start_orbit_determination)
        # self.ui.tool_output_select_ephemeris_exe.clicked.connect(self.select_ast_ephe_exe)
        # self.ui.button_output_configure_observation_file.clicked.connect(self.copy_observations_to_arc)
        # self.ui.button_output_process_observation_file.clicked.connect(self.process_observation_files)
        # self.ui.button_output_configure_ephemeris_observation_file.clicked.connect(self.configure_ast_ephe_observations)
        # self.ui.button_output_merge_ephemeris_observation_file.clicked.connect(self.merge_ephemeris)
        self.ui.button_visual_import_orbit_file.clicked.connect(self.show_orbit_plot)
        self.ui.button_visual_import_residual_file.clicked.connect(self.show_residual_plot)
        self.ui.button_visual_clear.clicked.connect(self.clear_visual_widget)
        self.ui.button_orbit_process_clear_stop.clicked.connect(self.stop_tasks)

    def _init_default_tables(self):
        """清空并填充各参数表格的默认行。"""
        defaults = {
            self.ui.table_arc_observation_weight: [["51-双程测距", "2.0D-0", "meter"], ["52-双程测速", "1.0D-0", "mm/s"]],
            self.ui.table_arc_measurement_bias: [["51", "4.0D-0", "1.0D+15"]],
            self.ui.table_arc_fixed_measurement_bias: [["51", "001", "001", "10.0D0", "", "", "1.0D-15"]],
            self.ui.table_arc_select_observation: [["1-双程测距", "6", "6", "", "0000000", "0000000", "", ""]],
            self.ui.table_arc_delete_observation: [["2", "6", "6", "0000000", "0000000", "", ""]],
            self.ui.table_arc_per_acc_period: [["1", "", "", "TDB"]],
            self.ui.table_arc_per_acc_model: [["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]],
            self.ui.table_simulated_observations: [self._simulation_observation_default_row()],
            self.ui.table_station_parameters: [self._station_default_row()],
        }
        for table, rows in defaults.items():
            table.setRowCount(0)
            for values in rows:
                row = table.rowCount()
                table.insertRow(row)
                for col, value in enumerate(values):
                    if col < table.columnCount():
                        item = QTableWidgetItem(value)
                        item.setFont(TableTools.table_font())
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        table.setItem(row, col, item)
            TableTools.apply_font(table)

    def _configured_tables(self):
        """返回需要统一字体和刷新处理的业务表格列表。"""
        return [
            self.ui.table_arc_observation_weight,
            self.ui.table_arc_measurement_bias,
            self.ui.table_arc_fixed_measurement_bias,
            self.ui.table_arc_select_observation,
            self.ui.table_arc_delete_observation,
            self.ui.table_arc_per_acc_period,
            self.ui.table_arc_per_acc_model,
            self.ui.table_simulated_observations,
            self.ui.table_station_parameters,
        ]

    def _apply_configured_table_fonts(self):
        """对所有业务表格重新应用统一字体。"""
        for table in self._configured_tables():
            TableTools.apply_font(table)

    def _simulation_observation_default_row(self):
        """生成一行默认 SimCP 模拟观测配置，时间跟随当前弧段。"""
        start = self.ui.date_arc_start_time.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        end = self.ui.date_arc_end_time.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        return ["0000", "", "", "", "", start, end, "51-双程测距", "2.000d-0", "30.000"]

    def _station_default_row(self):
        """生成一行默认测站参数，作为新增测站时的初始值。"""
        return ["001", "SHAO", "激活", "15.0", "直角坐标系XYZ", "-2831686.9130", "4675733.6660", "3275327.6900", "", "", "", "", "地球测站"]

    def _add_station_row(self):
        """向测站表格新增默认测站行并刷新下拉列。"""
        TableTools.add_row(self.ui.table_station_parameters, [], self._station_default_row())
        self._configure_station_table()

    def _setup_tables(self):
        """为所有业务表格绑定增删改按钮、时间列和默认行配置。"""
        configs = [
            (self.ui.table_arc_observation_weight, self.ui.button_arc_observation_weight_add, self.ui.button_arc_observation_weight_edit, self.ui.button_arc_observation_weight_delete, [], ["51-双程测距", "2.0D-0", "meter"]),
            (self.ui.table_arc_measurement_bias, self.ui.button_arc_measurement_bias_add, self.ui.button_arc_measurement_bias_edit, self.ui.button_arc_measurement_bias_delete, [], ["51", "4.0D-0", "1.0D+15"]),
            (self.ui.table_arc_fixed_measurement_bias, self.ui.button_arc_fixed_bias_add, self.ui.button_arc_fixed_bias_edit, self.ui.button_arc_fixed_bias_delete, [4, 5], ["51", "001", "001", "10.0D0", "", "", "1.0D-15"]),
            (self.ui.table_arc_select_observation, self.ui.button_arc_select_observation_add, self.ui.button_arc_select_observation_edit, self.ui.button_arc_select_observation_delete, [6, 7], ["1-双程测距", "6", "6", "", "0000000", "0000000", "", ""]),
            (self.ui.table_arc_delete_observation, self.ui.button_arc_delete_observation_add, self.ui.button_arc_delete_observation_edit, self.ui.button_arc_delete_observation_delete, [5, 6], ["2", "6", "6", "0000000", "0000000", "", ""]),
            (self.ui.table_arc_per_acc_period, self.ui.button_arc_per_acc_period_add, self.ui.button_arc_per_acc_period_edit, self.ui.button_arc_per_acc_period_delete, [1, 2], ["1", "", "", "TDB"]),
            (self.ui.table_arc_per_acc_model, self.ui.button_arc_per_acc_model_add, self.ui.button_arc_per_acc_model_edit, self.ui.button_arc_per_acc_model_delete, [], ["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]),
            (self.ui.table_simulated_observations, self.ui.button_simulation_observation_add, self.ui.button_simulation_observation_edit, self.ui.button_simulation_observation_delete, [5, 6], self._simulation_observation_default_row),
        ]
        for table, add_btn, edit_btn, del_btn, datetime_columns, default_row in configs:
            TableTools.setup(table, datetime_columns)
            add_btn.clicked.connect(lambda _, t=table, cols=datetime_columns, row=default_row: TableTools.add_row(t, cols, row))
            edit_btn.clicked.connect(lambda _, t=table, cols=datetime_columns: TableTools.edit_row(t, self, cols))
            del_btn.clicked.connect(lambda _, t=table: TableTools.delete_row(t, self))
        TableTools.setup(self.ui.table_station_parameters, [])
        self.ui.button_station_add.clicked.connect(self._add_station_row)
        self.ui.button_station_edit.clicked.connect(lambda: TableTools.edit_row(self.ui.table_station_parameters, self, []))
        self.ui.button_station_delete.clicked.connect(lambda: TableTools.delete_row(self.ui.table_station_parameters, self))
        self._configure_observation_weight_table()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_simulation_observation_table()
        self._configure_per_acc_table()
        self._configure_station_table()

    def _configure_per_acc_table(self):
        """配置经验加速度表头，并同步方向和模型的中文显示。"""
        table = self.ui.table_arc_per_acc_model
        headers = ("方向", "模型", "数值", "先验误差")
        table.setColumnCount(len(headers))
        for col, text in enumerate(headers):
            item = table.horizontalHeaderItem(col) or QTableWidgetItem()
            item.setText(text)
            item.setFont(TableTools.table_font())
            table.setHorizontalHeaderItem(col, item)
        for row in range(table.rowCount()):
            self._sync_per_acc_row(row)
        TableTools.apply_font(table)

    def _configure_station_table(self):
        """配置测站参数表头和状态、坐标类型、所在天体下拉列。"""
        table = self.ui.table_station_parameters
        headers = (
            "测站编号",
            "测站简称",
            "状态",
            "高度截止角",
            "坐标类型",
            "位置数值1",
            "位置数值2",
            "位置数值3",
            "速度数值1",
            "速度数值2",
            "速度数值3",
            "时间间隔",
            "所在天体",
        )
        table.setColumnCount(len(headers))
        for col, text in enumerate(headers):
            item = table.horizontalHeaderItem(col) or QTableWidgetItem()
            item.setText(text)
            item.setFont(TableTools.table_font())
            table.setHorizontalHeaderItem(col, item)
        for row in range(table.rowCount()):
            self._set_station_combo_cell(table, row, 2, STATION_STATUS_OPTIONS, "激活")
            self._set_station_combo_cell(table, row, 4, STATION_COORD_TYPE_OPTIONS, "直角坐标系XYZ")
            self._set_station_combo_cell(table, row, 12, STATION_BODY_OPTIONS, "地球测站")
        self._fit_station_columns()
        TableTools.apply_font(table)

    def _fit_station_columns(self):
        """按可用宽度自适应测站参数表的 13 个列宽。"""
        table = self.ui.table_station_parameters
        if table.columnCount() < 13:
            return
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setStretchLastSection(False)

        available = max(table.viewport().width(), table.width() - 4, 1)
        weights = [7, 8, 7, 8, 11, 10, 10, 10, 8, 8, 8, 8, 7]
        minimums = [52, 58, 52, 62, 88, 76, 76, 76, 62, 62, 62, 62, 52]
        weight_total = sum(weights)
        widths = [max(minimum, available * weight // weight_total) for minimum, weight in zip(minimums, weights)]
        if sum(widths) > available:
            scale = available / sum(widths)
            widths = [max(1, int(width * scale)) for width in widths]
        widths[-1] += available - sum(widths)
        for col, width in enumerate(widths):
            table.setColumnWidth(col, max(width, 1))

    def _set_station_combo_cell(self, table, row, col, options, default):
        """把测站表指定列设置为下拉框，并兼容旧卡片中的数字代码。"""
        current = self._table_cell_text(table, row, col) or default
        if current in ("1", "1.0") or current.startswith("1-"):
            if col == 2:
                current = "激活"
            elif col == 4:
                current = "大地坐标BLH"
            else:
                current = "月球测站"
        elif current in ("0", "0.0") or current.startswith("0-"):
            if col == 2:
                current = "未激活"
            elif col == 4:
                current = "直角坐标系XYZ"
            else:
                current = "地球测站"
        if current not in options:
            current = default
        combo = table.cellWidget(row, col)
        if not isinstance(combo, QComboBox):
            combo = QComboBox(table)
            table.setCellWidget(row, col, combo)
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        combo.setCurrentText(current)
        combo.setFont(TableTools.table_font())
        combo.blockSignals(False)
        item = table.item(row, col) or QTableWidgetItem()
        item.setText(current)
        item.setFont(TableTools.table_font())
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.setItem(row, col, item)

    @staticmethod
    def _table_cell_text(table, row, col):
        """读取表格单元格文本，兼容普通项和下拉框控件。"""
        widget = table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        item = table.item(row, col)
        return item.text().strip() if item and item.text() else ""

    def _configure_select_observation_table(self):
        """配置选择观测值表头，并把观测类型同步为中文标签。"""
        table = self.ui.table_arc_select_observation
        headers = ("观测值类型", "上行位", "下行位", "Passnumber", "卫星1编号", "卫星2编号", "起始时刻", "结束时刻")
        table.setColumnCount(len(headers))
        for col, text in enumerate(headers):
            item = table.horizontalHeaderItem(col) or QTableWidgetItem()
            item.setText(text)
            item.setFont(TableTools.table_font())
            table.setHorizontalHeaderItem(col, item)
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item:
                code = self._select_observation_type_code(item.text())
                item.setText(self._select_observation_type_label(code))
        self._fit_select_observation_columns()
        TableTools.apply_font(table)

    def _fit_select_observation_columns(self):
        """按可用宽度自适应选择观测值表各列宽度。"""
        table = self.ui.table_arc_select_observation
        if table.columnCount() < 8:
            return
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setStretchLastSection(False)

        available = max(table.viewport().width(), table.width() - 4, 0)
        minimums = [104, 54, 54, 82, 92, 92, 174, 174]
        weights = [14, 7, 7, 10, 12, 12, 19, 19]
        min_total = sum(minimums)
        if available <= min_total:
            widths = minimums
        else:
            extra = available - min_total
            weight_total = sum(weights)
            widths = [minimum + extra * weight // weight_total for minimum, weight in zip(minimums, weights)]
            widths[-1] += available - sum(widths)
        for col, width in enumerate(widths):
            table.setColumnWidth(col, max(width, 1))

    def _configure_simulation_observation_table(self):
        """刷新模拟观测值表的观测类型中文标签和字体。"""
        table = self.ui.table_simulated_observations
        for row in range(table.rowCount()):
            self._sync_simulation_observation_row(row)
        TableTools.apply_font(table)

    def _configure_observation_bias_table(self):
        """配置测量偏差固定表表头和列宽策略。"""
        table = self.ui.table_arc_fixed_measurement_bias
        headers = ("观测值类型", "下行位", "上行位", "偏差初值", "起始时刻", "结束时刻", "先验误差")
        table.setColumnCount(len(headers))
        for col, text in enumerate(headers):
            item = table.horizontalHeaderItem(col) or QTableWidgetItem()
            item.setText(text)
            item.setFont(TableTools.table_font())
            table.setHorizontalHeaderItem(col, item)
        for col in range(table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        self._fit_observation_bias_columns()
        TableTools.apply_font(table)

    def _fit_observation_bias_columns(self):
        """按可用宽度自适应测量偏差固定表各列宽度。"""
        table = self.ui.table_arc_fixed_measurement_bias
        if table.columnCount() < 7:
            return
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setStretchLastSection(False)

        available = max(table.viewport().width(), table.width() - 4, 0)
        minimums = [96, 62, 62, 104, 178, 178, 96]
        weights = [13, 8, 8, 13, 22, 22, 14]
        min_total = sum(minimums)
        if available <= min_total:
            widths = minimums
        else:
            extra = available - min_total
            weight_total = sum(weights)
            widths = [minimum + extra * weight // weight_total for minimum, weight in zip(minimums, weights)]
            widths[-1] += available - sum(widths)
        for col, width in enumerate(widths):
            table.setColumnWidth(col, max(width, 1))

    def _configure_observation_weight_table(self):
        """配置观测值权重表，并同步观测类型中文标签和单位。"""
        table = self.ui.table_arc_observation_weight
        for col, text in enumerate(("观测值类型", "观测值权重", "观测值单位")):
            item = table.horizontalHeaderItem(col) or QTableWidgetItem()
            item.setText(text)
            item.setFont(TableTools.table_font())
            table.setHorizontalHeaderItem(col, item)
        for row in range(table.rowCount()):
            self._sync_observation_weight_row(row)
        TableTools.apply_font(table)

    @staticmethod
    def _observation_type_code(value):
        """从观测类型单元格文本中提取 LCP/SimCP 使用的观测类型代码。"""
        text = str(value or "").strip()
        for code in OBSERVATION_WEIGHT_HELP:
            if text == code or text.startswith(f"{code}-"):
                return code
        return text

    @staticmethod
    def _observation_type_label(code):
        """把观测类型代码转换为“代码-中文解释”的显示文本。"""
        code = str(code or "").strip()
        info = OBSERVATION_WEIGHT_HELP.get(code)
        return f"{code}-{info[0]}" if info else code

    @staticmethod
    def _observation_unit(code):
        """根据观测类型代码返回权重表中应显示的单位。"""
        info = OBSERVATION_WEIGHT_HELP.get(str(code or "").strip())
        return info[1] if info else ""

    @staticmethod
    def _select_observation_type_code(value):
        """把选择观测值表中的类型文本转换为 SelectObs 代码。"""
        text = str(value or "").strip()
        for code in SELECT_OBSERVATION_TYPE_HELP:
            if text == code or text.startswith(f"{code}-"):
                return code
        if text.isdigit():
            normalized = str(int(text))
            normalized = SELECT_OBSERVATION_TYPE_LEGACY_CODES.get(normalized, normalized)
            if normalized in SELECT_OBSERVATION_TYPE_HELP:
                return normalized
        return text

    @staticmethod
    def _select_observation_type_label(code):
        """把 SelectObs 类型代码转换为“代码-中文解释”的显示文本。"""
        code = str(code or "").strip()
        label = SELECT_OBSERVATION_TYPE_HELP.get(code)
        return f"{code}-{label}" if label else code

    @staticmethod
    def _coded_label_code(value, mapping):
        """用给定映射从代码标签文本中提取标准代码。"""
        text = str(value or "").strip()
        for code in mapping:
            if text == code or text.startswith(f"{code}-"):
                return code
        if text.isdigit():
            normalized = str(int(text))
            if normalized in mapping:
                return normalized
        return text

    @staticmethod
    def _coded_label(code, mapping):
        """用给定映射把标准代码转换为“代码-中文解释”文本。"""
        code = str(code or "").strip()
        label = mapping.get(code)
        return f"{code}-{label}" if label else code

    def _sync_observation_weight_row(self, row):
        """同步观测权重表单行的观测类型标签和单位列。"""
        if row < 0 or self._syncing_observation_weight:
            return
        table = self.ui.table_arc_observation_weight
        if row >= table.rowCount():
            return
        code = self._observation_type_code(self._table_text(table, row, 0))
        if not code:
            return
        unit = self._observation_unit(code)
        if not unit:
            return
        self._syncing_observation_weight = True
        try:
            type_item = table.item(row, 0) or QTableWidgetItem()
            type_item.setText(self._observation_type_label(code))
            type_item.setFont(TableTools.table_font())
            type_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row, 0, type_item)

            unit_item = table.item(row, 2) or QTableWidgetItem()
            unit_item.setText(unit)
            unit_item.setFont(TableTools.table_font())
            unit_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row, 2, unit_item)
        finally:
            self._syncing_observation_weight = False

    def _sync_simulation_observation_row(self, row):
        """同步模拟观测值表单行的观测类型中文标签。"""
        if row < 0 or self._syncing_simulation_observation:
            return
        table = self.ui.table_simulated_observations
        if row >= table.rowCount() or table.columnCount() <= 7:
            return
        code = self._observation_type_code(self._table_text(table, row, 7))
        label = self._observation_type_label(code)
        if not label:
            return
        self._syncing_simulation_observation = True
        try:
            item = table.item(row, 7) or QTableWidgetItem()
            item.setText(label)
            item.setFont(TableTools.table_font())
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row, 7, item)
        finally:
            self._syncing_simulation_observation = False

    def _sync_per_acc_row(self, row):
        """同步经验加速度表单行的方向和模型中文标签。"""
        if row < 0 or self._syncing_per_acc:
            return
        table = self.ui.table_arc_per_acc_model
        if row >= table.rowCount():
            return
        updates = (
            (0, PER_ACC_DIRECTION_HELP),
            (1, PER_ACC_MODEL_HELP),
        )
        self._syncing_per_acc = True
        try:
            for col, mapping in updates:
                item = table.item(row, col)
                if item is None:
                    continue
                code = self._coded_label_code(item.text(), mapping)
                label = self._coded_label(code, mapping)
                item.setText(label)
                item.setFont(TableTools.table_font())
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        finally:
            self._syncing_per_acc = False

    def _on_observation_weight_item_changed(self, item):
        """处理观测权重表单元格修改，触发类型和单位同步。"""
        if item and item.tableWidget() is self.ui.table_arc_observation_weight and item.column() in (0, 2):
            self._sync_observation_weight_row(item.row())

    def _on_select_observation_item_changed(self, item):
        """处理选择观测值表类型列修改，自动补全中文说明。"""
        if (
            not item
            or item.tableWidget() is not self.ui.table_arc_select_observation
            or item.column() != 0
            or self._syncing_select_observation
        ):
            return
        code = self._select_observation_type_code(item.text())
        label = self._select_observation_type_label(code)
        if label == item.text():
            return
        self._syncing_select_observation = True
        try:
            item.setText(label)
            item.setFont(TableTools.table_font())
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        finally:
            self._syncing_select_observation = False

    def _on_simulation_observation_item_changed(self, item):
        """处理模拟观测值表类型列修改，自动补全中文说明。"""
        if item and item.tableWidget() is self.ui.table_simulated_observations and item.column() == 7:
            self._sync_simulation_observation_row(item.row())

    def _on_per_acc_item_changed(self, item):
        """处理经验加速度表方向/模型列修改，自动补全中文说明。"""
        if item and item.tableWidget() is self.ui.table_arc_per_acc_model and item.column() in (0, 1):
            self._sync_per_acc_row(item.row())

    def new_scheme(self):
        """新建默认定轨方案，重置表格、时间控件和日志输出。"""
        self._configure_global_parameters()
        self._init_default_tables()
        self._setup_datetime_cells()
        self._configure_observation_weight_table()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_simulation_observation_table()
        self._configure_per_acc_table()
        self._apply_configured_table_fonts()
        self.current_scheme_dir = DEFAULT_SCHEME_DIR
        self.ui.text_orbit_process_log.clear()
        self._log("已新建默认定轨方案。")

    def open_scheme(self):
        """选择方案目录并批量导入其中存在的 GCP/LCP/SimCP/StaCP 卡片。"""
        directory = QFileDialog.getExistingDirectory(self, "选择定轨方案目录", str(self.current_scheme_dir))
        if not directory:
            return
        self.current_scheme_dir = Path(directory)
        loaded = []
        for name in CARD_NAMES:
            path = self.current_scheme_dir / name
            if path.exists():
                self._load_card_from_path(name, path)
                loaded.append(name)
        self._setup_datetime_cells()
        self._apply_configured_table_fonts()
        self._log(f"已打开方案目录：{self.current_scheme_dir}\n已导入：{', '.join(loaded) if loaded else '未发现卡片文件'}")

    def save_scheme(self):
        """把当前界面参数保存到当前方案目录。"""
        self._save_cards(self.current_scheme_dir)

    def save_scheme_as(self):
        """选择新目录并把当前界面参数另存为一套控制卡片。"""
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录", str(self.current_scheme_dir))
        if not directory:
            return
        self.current_scheme_dir = Path(directory)
        self._save_cards(self.current_scheme_dir)

    def import_card(self, card_name: str):
        """导入指定类型的单个控制卡片并刷新相关表格显示。"""
        file_path, _ = QFileDialog.getOpenFileName(self, f"选择 {card_name} 文件", str(self.current_scheme_dir), "卡片文件 (*);;所有文件 (*)")
        if file_path:
            self._load_card_from_path(card_name, Path(file_path))
            self._setup_datetime_cells()
            self._apply_configured_table_fonts()
            self._log(f"已导入 {card_name}：{file_path}")

    def _save_cards(self, directory: Path):
        """保存全部控制卡片并向用户显示保存结果。"""
        self._write_cards(directory, notify=True)

    def _write_cards(self, directory: Path, notify: bool = False):
        """把当前界面数据写出为 GCP、LCP、SimCP 和 StaCP 四类卡片。"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            card_io.save_gcp(self.ui, directory / "GCP")
            card_io.save_lcp(self.ui, directory / "LCP")
            card_io.save_simcp(self.ui, directory / "SimCP")
            card_io.save_stacp(self.ui, directory / "StaCP")
            self.ui.statusbar.showMessage(f"方案已保存：{directory}")
            self._log(f"保存成功：{directory}")
            if notify:
                QMessageBox.information(self, "保存成功", f"已保存 GCP、LCP、SimCP、StaCP 到：\n{directory}")
        except Exception as exc:
            if notify:
                QMessageBox.critical(self, "保存失败", str(exc))
            else:
                raise

    def _load_card_from_path(self, card_name: str, path: Path):
        """按卡片类型调用对应读取函数，并执行导入后的界面同步。"""
        loaders = {
            "GCP": card_io.read_gcp,
            "LCP": card_io.read_lcp,
            "SimCP": card_io.read_simcp,
            "StaCP": card_io.read_stacp,
        }
        loaders[card_name](path, self.ui)
        if card_name == "GCP":
            self._lock_unreleased_global_parameters()
            self._hide_gravity_inversion_order()
            self._sync_integration_center_controls()
        elif card_name == "LCP":
            self._configure_observation_weight_table()
            self._configure_observation_bias_table()
            self._configure_select_observation_table()
            self._configure_per_acc_table()
        elif card_name == "SimCP":
            self._configure_simulation_observation_table()
        elif card_name == "StaCP":
            self._configure_station_table()

    def show_observation_weight_help(self):
        """根据当前观测权重表生成观测类型、单位和权重说明弹窗。"""
        lines = []
        table = self.ui.table_arc_observation_weight
        for row in range(table.rowCount()):
            obs_type = self._observation_type_code(self._table_text(table, row, 0))
            weight = self._table_text(table, row, 1)
            if not obs_type and not weight:
                continue
            description, unit = OBSERVATION_WEIGHT_HELP.get(obs_type, (f"未知类型({obs_type or '未填写'})", ""))
            weight_text = weight or "未填写"
            unit_text = f" {unit}" if unit else ""
            obs_label = self._observation_type_label(obs_type) if obs_type else "未填写"
            lines.append(f"观测值类型 {obs_label}, {description}, Observation weighting={weight_text}{unit_text}")
        if not lines:
            lines.append("当前观测值权重表没有可说明的数据。")
        QMessageBox.information(self, "观测值权重说明", "\n".join(lines))

    @staticmethod
    def _table_text(table: QTableWidget, row: int, col: int) -> str:
        """安全读取普通表格单元格文本，空单元格返回空字符串。"""
        item = table.item(row, col)
        return item.text().strip() if item and item.text() else ""

    def configure_and_generate_observations(self):
        """保存当前方案并启动模拟观测值生成任务。"""
        self._write_cards(self.current_scheme_dir)
        self._run_usefortran("正在配置并生成模拟观测值，请稍候...", self._genobs_job)

    def _genobs_job(self):
        """后台执行 SimCP 配置兼容流程和模拟观测值生成流程。"""
        self._require_usefortran()
        msg = UseFortran.copy_simcp_to_target()
        output = UseFortran.genobs(self.ui)
        return f"{msg}\n{output}"

    def copy_observations_to_arc(self):
        """保存方案后把生成的观测文件复制到界面指定的弧段目录。"""
        self._write_cards(self.current_scheme_dir)
        result = self._copy_obs_files_to_arc(self.ui.edit_output_observation_station_id.text().strip())
        self._log(result)

    @staticmethod
    def _copy_obs_files_to_arc(arc_id: str) -> str:
        """把 scheme/observations.csv 复制到指定编号弧段的 InputDATA 目录。"""
        if not arc_id:
            return "未输入目标弧段编号。"
        if arc_id not in {"001", "002", "003"}:
            return "弧段编号应为 001、002 或 003。"
        src = APP_DIR / "scheme" / "observations.csv"
        dst_dir = APP_DIR / "output" / "Arc" / arc_id / "InputDATA"
        if not src.exists():
            return f"源观测值文件不存在：{src}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst_dir / src.name)
        return f"弧段 {arc_id} 配置完成，已复制文件：\n{dst_dir / src.name}"

    def process_observation_files(self):
        """启动观测文件清理和重编号任务。"""
        self._run_usefortran("正在处理观测值文件...", self._process_obs_job)

    def _process_obs_job(self):
        """后台遍历三个弧段目录并调用观测文件处理逻辑。"""
        self._require_usefortran()
        base = APP_DIR / "output" / "Arc"
        messages = []
        for arc_id in ("001", "002", "003"):
            path = base / arc_id / "InputDATA"
            messages.append(f"弧段 {arc_id}: {UseFortran.process_obs_files(str(path))}")
        return "\n".join(messages)

    def select_solve_global_exe(self):
        """选择并运行旧版全局参数与弧段参数解算程序。"""
        default = APP_DIR / "external" / "Solve_Global_Para.exe"
        self._select_and_run_exe(default, "选择全局参数与弧段参数解算程序")

    def select_ast_ephe_exe(self):
        """选择并运行旧版小行星星历解算程序。"""
        default = APP_DIR / "external" / "Batch_developing.exe"
        self._select_and_run_exe(default, "选择小行星星历解算程序")

    def start_orbit_determination(self):
        """保存方案并启动外部定轨测试程序，实时接收命令行输出。"""
        if self.orbit_process and self.orbit_process.state() != QProcess.NotRunning:
            QMessageBox.information(self, "定轨程序运行中", "当前定轨任务尚未结束，请先停止任务。")
            return

        self._write_cards(self.current_scheme_dir)
        if not ORBIT_PROGRAM.exists():
            QMessageBox.warning(
                self,
                "未找到定轨程序",
                f"未找到测试可执行程序：\n{ORBIT_PROGRAM}\n\n"
                "请运行 test_program/build_test_exe.ps1 生成测试程序。",
            )
            return

        self.ui.tabWidget.setCurrentWidget(self.ui.page_orbit_output)
        self.ui.text_orbit_process_log.clear()
        self._log(f"准备启动外部定轨程序：{ORBIT_PROGRAM}")

        self._orbit_stdout_decoder = codecs.getincrementaldecoder(ORBIT_OUTPUT_ENCODING)(errors="replace")
        self._orbit_stderr_decoder = codecs.getincrementaldecoder(ORBIT_OUTPUT_ENCODING)(errors="replace")

        process = QProcess(self)
        process.setProgram(str(ORBIT_PROGRAM))
        process.setArguments(["--scheme-dir", str(self.current_scheme_dir.resolve())])
        process.setWorkingDirectory(str(self.current_scheme_dir.resolve()))
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.started.connect(self._on_orbit_process_started)
        process.readyReadStandardOutput.connect(self._read_orbit_stdout)
        process.readyReadStandardError.connect(self._read_orbit_stderr)
        process.errorOccurred.connect(self._on_orbit_process_error)
        process.finished.connect(self._on_orbit_process_finished)
        self.orbit_process = process
        self.ui.button_start_orbit.setEnabled(False)
        self.ui.action_start_orbit.setEnabled(False)
        process.start()

    def _on_orbit_process_started(self):
        """记录外部定轨程序已成功启动的状态。"""
        self._log("外部定轨程序已启动，正在实时接收命令行输出...")

    def _read_orbit_stdout(self):
        """读取外部定轨程序标准输出并追加到日志窗口。"""
        if not self.orbit_process or not self._orbit_stdout_decoder:
            return
        data = bytes(self.orbit_process.readAllStandardOutput())
        self._append_log_text(self._orbit_stdout_decoder.decode(data))

    def _read_orbit_stderr(self):
        """读取外部定轨程序标准错误并追加到日志窗口。"""
        if not self.orbit_process or not self._orbit_stderr_decoder:
            return
        data = bytes(self.orbit_process.readAllStandardError())
        text = self._orbit_stderr_decoder.decode(data)
        if text:
            self._append_log_text(f"[stderr] {text}")

    def _on_orbit_process_error(self, error):
        """处理外部定轨程序启动失败等 QProcess 错误并恢复按钮状态。"""
        if error == QProcess.FailedToStart:
            detail = self.orbit_process.errorString() if self.orbit_process else "未知错误"
            self._log(f"定轨程序启动失败：{detail}")
            self.ui.button_start_orbit.setEnabled(True)
            self.ui.action_start_orbit.setEnabled(True)
            if self.orbit_process:
                self.orbit_process.deleteLater()
            self.orbit_process = None
            self._orbit_stdout_decoder = None
            self._orbit_stderr_decoder = None

    def _on_orbit_process_finished(self, exit_code, exit_status):
        """处理外部定轨程序结束事件，刷新日志并释放进程状态。"""
        if self._orbit_stdout_decoder:
            self._append_log_text(self._orbit_stdout_decoder.decode(b"", final=True))
        if self._orbit_stderr_decoder:
            tail = self._orbit_stderr_decoder.decode(b"", final=True)
            if tail:
                self._append_log_text(f"[stderr] {tail}")

        if exit_status == QProcess.NormalExit:
            self._log(f"外部定轨程序已结束，退出代码：{exit_code}")
        else:
            self._log("外部定轨程序异常终止。")
        self.ui.button_start_orbit.setEnabled(True)
        self.ui.action_start_orbit.setEnabled(True)
        if self.orbit_process:
            self.orbit_process.deleteLater()
        self.orbit_process = None
        self._orbit_stdout_decoder = None
        self._orbit_stderr_decoder = None

    def _select_and_run_exe(self, default_path: Path, title: str):
        """弹出文件选择框选择可执行程序并启动运行。"""
        start_dir = str(default_path.parent if default_path.parent.exists() else LEGACY_DIR)
        file_path, _ = QFileDialog.getOpenFileName(self, title, start_dir, "可执行程序 (*.exe);;所有文件 (*)")
        if file_path:
            self._run_exe(Path(file_path))

    def _run_exe(self, exe_path: Path):
        """把外部可执行程序包装成后台任务运行。"""
        self._run_usefortran(f"正在运行：{exe_path}", lambda: self._execute_program(exe_path))

    @staticmethod
    def _execute_program(exe_path: Path):
        """同步执行指定 EXE，并返回其标准输出和错误输出。"""
        if not exe_path.exists():
            return f"未找到执行文件：{exe_path}"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=flags,
        )
        out, err = process.communicate()
        return (out or "") + (f"\n[stderr]\n{err}" if err else "")

    def configure_ast_ephe_observations(self):
        """启动旧版小行星星历观测值配置任务。"""
        self._run_usefortran("正在配置小行星星历观测值...", self._gen_obs_for_asteph_job)

    def _gen_obs_for_asteph_job(self):
        """在旧项目目录中调用小行星星历观测值配置接口。"""
        self._require_usefortran()
        with working_directory(LEGACY_DIR):
            return UseFortran.run_gen_obs_for_solve_asteph()

    def merge_ephemeris(self):
        """启动旧版多弧段探测器星历融合任务。"""
        self._run_usefortran("正在融合多弧段探测器星历...", self._merge_ephe_job)

    def _merge_ephe_job(self):
        """在旧项目目录中调用星历融合兼容接口。"""
        self._require_usefortran()
        with working_directory(LEGACY_DIR):
            return UseFortran.merge_our_own_ephe()

    def show_orbit_plot(self):
        """选择轨道结果文件并在图表页显示三维轨道动画。"""
        default = APP_DIR / "output" / "orbit_result.csv"
        start_dir = str(default.parent if default.parent.exists() else APP_DIR)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择轨道文件", start_dir, "Orbit files (*.csv *.spk *.bsp);;所有文件 (*)")
        if not file_path and default.exists():
            file_path = str(default)
        if not file_path:
            return
        try:
            from Chart import OrbitPlotCanvas

            self.clear_visual_widget()
            canvas = OrbitPlotCanvas(file_path, parent=self.ui.panel_visual_canvas)
            layout = self._visual_layout()
            layout.addWidget(canvas)
            canvas.start_animation()
            self.ui.tabWidget.setCurrentWidget(self.ui.page_visual_analysis)
        except Exception as exc:
            QMessageBox.critical(self, "绘图失败", str(exc))

    def show_residual_plot(self):
        """读取残差文件并在图表页显示残差散点图。"""
        try:
            from Residual import show_residual_in_widget2

            self.clear_visual_widget()
            show_residual_in_widget2(self, self.ui.panel_visual_canvas)
            self.ui.tabWidget.setCurrentWidget(self.ui.page_visual_analysis)
        except Exception as exc:
            QMessageBox.critical(self, "残差分析失败", str(exc))

    def clear_visual_widget(self):
        """清空图表页容器中已有的画布或其他子控件。"""
        layout = self.ui.panel_visual_canvas.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def _visual_layout(self):
        """获取或创建图表页容器的垂直布局。"""
        layout = self.ui.panel_visual_canvas.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui.panel_visual_canvas)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def stop_tasks(self):
        """停止正在运行的外部进程和后台线程，或清空当前输出日志。"""
        process_stopped = False
        process = self.orbit_process
        if process and process.state() != QProcess.NotRunning:
            process_stopped = True
            process.terminate()
            if not process.waitForFinished(1000):
                process.kill()
                process.waitForFinished(1000)
        if UseFortran is not None:
            try:
                UseFortran.terminate_genobs_process()
            except Exception:
                pass
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
        self.threads.clear()
        if process_stopped:
            self._log("已停止外部定轨程序。")
        else:
            self.ui.text_orbit_process_log.clear()
            self.ui.statusbar.showMessage("定轨输出已清空。")

    def _run_usefortran(self, start_message: str, func):
        """兼容旧命名的任务启动入口，内部转交给通用后台任务函数。"""
        self._run_task(start_message, func)

    def _run_task(self, start_message: str, func):
        """创建 QThread 和 Worker 执行耗时任务，并把结果写入日志。"""
        self.ui.tabWidget.setCurrentWidget(self.ui.page_orbit_output)
        self._log(start_message)
        thread = QThread(self)
        worker = Worker(func)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self.threads.append(thread)

    def _on_worker_finished(self, text: str):
        """处理后台任务成功结束后的日志输出。"""
        self._log(text or "任务完成。")

    def _on_worker_error(self, text: str):
        """处理后台任务异常结束后的日志输出。"""
        self._log(f"任务失败：{text}")

    def _require_usefortran(self):
        """确认 UseFortran 兼容模块可用，否则抛出明确错误。"""
        if UseFortran is None:
            raise RuntimeError("旧项目 UseFortran.py 模块导入失败。")

    def _setup_datetime_cells(self):
        """确保所有配置为时间列的表格单元格都使用 QDateTimeEdit 控件。"""
        for table, columns in [
            (self.ui.table_arc_fixed_measurement_bias, [4, 5]),
            (self.ui.table_arc_select_observation, [6, 7]),
            (self.ui.table_arc_delete_observation, [5, 6]),
            (self.ui.table_arc_per_acc_period, [1, 2]),
            (self.ui.table_simulated_observations, [5, 6]),
        ]:
            for row in range(table.rowCount()):
                for col in columns:
                    if table.cellWidget(row, col) is None:
                        item = table.item(row, col)
                        value = item.text().strip() if item and item.text().strip() else None
                        card_io.set_datetime_cell(table, row, col, value)
            TableTools.apply_font(table)

    def _log(self, message: str):
        """向日志窗口和状态栏写入一条消息。"""
        if self.ui.text_orbit_process_log.toPlainText() and not self.ui.text_orbit_process_log.toPlainText().endswith("\n"):
            self._append_log_text("\n")
        self._append_log_text(f"{message.rstrip()}\n" if message else "")
        self.ui.statusbar.showMessage(message.splitlines()[0] if message else "")

    def _append_log_text(self, text: str):
        """把文本追加到日志窗口末尾并滚动到最新位置。"""
        if not text:
            return
        cursor = self.ui.text_orbit_process_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.text_orbit_process_log.setTextCursor(cursor)
        self.ui.text_orbit_process_log.ensureCursorVisible()

    def show_about(self):
        """显示软件版本说明、功能范围和近期兼容性修复。"""
        QMessageBox.information(
            self,
            "关于",
            f"{APP_DISPLAY_NAME}\n"
            "支持 GCP/LCP/SimCP/StaCP 卡片读写、观测值配置、定轨程序调用和可视化分析。\n\n"
            "主要优化（2026-06-20）：\n"
            "1. 优化全局参数页面，保留轨道预报、仿真观测值和精密定轨三种运行模式。\n"
            "2. 精简弧段参数，优化时间联动、快捷加 5/7 天、积分步长及输出步长选择和控件布局。\n"
            "3. 完善观测值权重、测量偏差固定及观测值选择，增加中文类型、单位、上下行位和 Passnumber。\n"
            "4. 将有限推力模型调整为经验加速度模型，优化方向、拟合方式及卡片读取显示。\n"
            "5. 完善模拟观测值时间同步，使 SimCP 时间默认与弧段起止时刻一致。\n"
            "6. 优化测站参数，增加坐标类型和速度数值 3，并以文字下拉框显示状态、坐标类型及所在天体。\n"
            "7. 更新卡片写入规则，使输出格式与标准示例保持一致，并移除已停用参数。\n\n"
            "兼容性修复：\n"
            "1. 兼容 SimuSat/SimuSta/SimuTyp 旧格式模拟观测值卡片。\n"
            "2. 支持 STAPOS 中相邻负号坐标值的自动拆分读取。\n"
            "3. 优化最大化窗口后的面板切换与布局刷新。",
        )

    def closeEvent(self, event):
        """窗口关闭前停止后台任务并继续执行默认关闭流程。"""
        self.stop_tasks()
        super().closeEvent(event)


def configure_windows_app_id():
    """在 Windows 上设置任务栏应用 ID，确保图标和窗口分组正确。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def load_app_icon() -> QIcon:
    """从 assets/icons 加载应用图标，缺失时返回空图标。"""
    icon_path = iconsource_rc.icon_path(APP_ICON_NAME)
    return QIcon(icon_path) if Path(icon_path).exists() else QIcon()


def main():
    """配置高 DPI、创建 QApplication 和主窗口，并进入 Qt 事件循环。"""
    configure_windows_app_id()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setWindowIcon(load_app_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
