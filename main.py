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
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.finished.emit(str(self.func(*self.args)))
        except Exception as exc:
            self.error.emit(str(exc))


class TableTools:
    TABLE_FONT_FAMILY = "Microsoft YaHei"
    TABLE_FONT_SIZE = 8

    @staticmethod
    def table_font() -> QFont:
        return QFont(TableTools.TABLE_FONT_FAMILY, TableTools.TABLE_FONT_SIZE)

    @staticmethod
    def apply_font(table: QTableWidget):
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
        row = table.currentRow()
        if row < 0:
            QMessageBox.warning(parent, "提示", "请先选择要删除的行。")
            return
        if QMessageBox.question(parent, "确认删除", f"确定删除第 {row + 1} 行吗？") == QMessageBox.Yes:
            table.removeRow(row)

    @staticmethod
    def edit_row(table: QTableWidget, parent, datetime_columns=None):
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
        self._syncing_per_acc = False
        self._configure_ui()
        self._connect_signals()

    def _configure_ui(self):
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setWindowIcon(load_app_icon())
        self.setFont(QFont("Microsoft YaHei", 8))
        self._apply_layout_polish()
        self._apply_style()
        self._align_text_widgets()
        self.ui.statusbar.showMessage(f"工作目录：{self.current_scheme_dir}")
        self.ui.pushButton.setToolTip("新建定轨方案")
        self.ui.pushButton_2.setToolTip("打开定轨方案")
        self.ui.pushButton_3.setToolTip("保存定轨方案")
        self.ui.pushButton_4.setToolTip("另存为定轨方案")
        self.ui.pushButton_5.setToolTip("开始定轨")
        self.ui.pushButton_6.setToolTip("查看图表")
        self._apply_toolbar_icons()
        if self.ui.dateTimeEdit.dateTime().secsTo(self.ui.dateTimeEdit_2.dateTime()) <= 0:
            self.ui.dateTimeEdit_2.setDateTime(self.ui.dateTimeEdit.dateTime().addDays(1))
        self._configure_global_parameters()
        self._configure_arc_parameters()
        self._apply_global_page_layout()
        self._apply_secondary_pages_layout()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_per_acc_table()
        self._configure_station_table()
        self._init_default_tables()
        self._setup_tables()

    def _configure_global_parameters(self):
        self._move_integrator_to_global_parameters()
        self._normalize_global_parameter_labels()
        self._configure_run_modes()

        integration_centers = [
            ("地球", "0"),
            # ("月球", "10"),
            # ("火星", "2"),
        ]
        self.ui.Runmode_2.clear()
        for label, code in integration_centers:
            self.ui.Runmode_2.addItem(label, code)
        self.ui.Runmode_2.setCurrentIndex(0)
        self._hide_gravity_inversion_order()
        self._sync_integration_center_controls()

        if self.ui.comboBox_2.findText("DE440") < 0:
            self.ui.comboBox_2.addItem("DE440", "440")
        for index in range(self.ui.comboBox_2.count()):
            text = self.ui.comboBox_2.itemText(index)
            if self.ui.comboBox_2.itemData(index) is None and text.startswith("DE"):
                self.ui.comboBox_2.setItemData(index, text.removeprefix("DE"))
        self.ui.comboBox_2.setCurrentText("DE440")

        integrators = [("ode", "1"), ("Adams12", "2")]
        for index, (label, code) in enumerate(integrators):
            if index >= self.ui.comboBox_6.count():
                self.ui.comboBox_6.addItem(label, code)
            else:
                self.ui.comboBox_6.setItemText(index, label)
                self.ui.comboBox_6.setItemData(index, code)
        self.ui.comboBox_6.setCurrentText("Adams12")
        self.ui.comboBox_6.setToolTip("1=ode；2=Adams12（12阶 Adams-Bashforth-Moulton 预估校正固定步长积分器）")
        integrator_font = QFont("Microsoft YaHei", 8)
        self.ui.label_51.setFont(integrator_font)
        self.ui.comboBox_6.setFont(integrator_font)

        self.ui.ForceCent_10.setChecked(True)
        self.ui.ForceCent_11.setChecked(True)

        self._lock_unreleased_global_parameters()

    def _configure_run_modes(self):
        run_modes = [
            ("轨道预报", "1"),
            ("仿真观测值", "2"),
            ("精密定轨", "4"),
        ]
        self.ui.Runmode.clear()
        for label, code in run_modes:
            self.ui.Runmode.addItem(label, code)
        self.ui.Runmode.setCurrentText("精密定轨")
        self.ui.Runmode.setToolTip("1=轨道预报；2=仿真观测值；4=精密定轨")

    def _normalize_global_parameter_labels(self):
        for label, text in (
            (self.ui.label_4, "引力场文件格式："),
            (self.ui.label_27, "固体潮摄动："),
        ):
            label.setText(text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _hide_gravity_inversion_order(self):
        self.ui.label_6.hide()
        self.ui.spinBox_2.hide()

    def _sync_integration_center_controls(self):
        center_code = str(self.ui.Runmode_2.currentData() or "0")
        is_earth_center = center_code in {"0", "399"}
        if is_earth_center:
            self.ui.ForceCent_4.setChecked(False)
        self.ui.ForceCent_4.setEnabled(not is_earth_center)

    def _move_integrator_to_global_parameters(self):
        if self.ui.comboBox_6.parent() is self.ui.horizontalLayoutWidget_16:
            return

        self.ui.horizontalLayout_28.removeWidget(self.ui.label_51)
        self.ui.horizontalLayout_28.removeWidget(self.ui.comboBox_6)
        self.ui.label_51.setParent(self.ui.horizontalLayoutWidget_16)
        self.ui.comboBox_6.setParent(self.ui.horizontalLayoutWidget_16)

        insert_at = max(self.ui.horizontalLayout_16.count() - 1, 0)
        self.ui.horizontalLayout_16.insertSpacing(insert_at, 24)
        self.ui.horizontalLayout_16.insertWidget(insert_at + 1, self.ui.label_51)
        self.ui.horizontalLayout_16.insertWidget(insert_at + 2, self.ui.comboBox_6)
        self.ui.label_51.show()
        self.ui.comboBox_6.show()

        self.ui.horizontalLayoutWidget_28.hide()
        if hasattr(self.ui, "line_16"):
            self.ui.line_16.hide()

    def _move_widget_y(self, widget, y):
        geometry = widget.geometry()
        widget.setGeometry(geometry.x(), y, geometry.width(), geometry.height())

    def _compact_arc_integrator_gap(self):
        positions = {
            "line_17": 250,
            "tabWidget_2": 260,
        }
        for name, y in positions.items():
            widget = getattr(self.ui, name, None)
            if widget:
                self._move_widget_y(widget, y)

    def _compact_arc_parameter_rows(self):
        positions = {
            "line_13": 80,
            "horizontalLayoutWidget_21": 90,
            "horizontalLayoutWidget_22": 110,
            "horizontalLayoutWidget_23": 130,
            "horizontalLayoutWidget_24": 150,
            "horizontalLayoutWidget_25": 170,
            "line_14": 190,
            "horizontalLayoutWidget_26": 200,
            "line_15": 220,
            "horizontalLayoutWidget_27": 230,
        }
        for name, y in positions.items():
            widget = getattr(self.ui, name, None)
            if widget:
                self._move_widget_y(widget, y)

    def _lock_unreleased_global_parameters(self):
        self.ui.ForceCent_14.setChecked(False)
        self._lock_widgets(
            self.ui.spinBox_2,
            self.ui.label_27,
            self.ui.ForceCent_14,
            self.ui.label_28,
            self.ui.lineEdit_23,
            self.ui.label_29,
            self.ui.lineEdit_24,
        )

    def _configure_per_acceleration_model(self):
        self.ui.comboBox_8.clear()
        self.ui.comboBox_8.addItem("经验加速度模型", 0)
        # self.ui.comboBox_8.addItem("有限推力", 1)
        self.ui.comboBox_8.setCurrentIndex(0)
        self.ui.comboBox_8.setToolTip("当前仅启用经验加速度模型")
        tab_index = self.ui.tabWidget_2.indexOf(self.ui.tab_11)
        if tab_index >= 0:
            self.ui.tabWidget_2.setTabText(tab_index, "经验加速度模型")

    def _configure_arc_parameters(self):
        self._comment_out_solar_panel_area()
        self._remove_albedo_radiation_row()
        self._comment_out_doppler_inverse_time()
        self._replace_orbit_step_edits()
        self._configure_per_acceleration_model()
        self._remove_arc_derivative_filter_rows()
        self._remove_spice_kernel_path_row()
        self._align_arc_parameter_labels()

        self.ui.checkBox.setChecked(False)
        self._lock_widgets(self.ui.label_40, self.ui.checkBox)
        self._lock_widgets(
            self.ui.label_52,
            self.ui.lineEdit_40,
            self.ui.label_53,
            self.ui.lineEdit_41,
            self.ui.label_54,
            self.ui.lineEdit_42,
            self.ui.label_55,
            self.ui.comboBox_7,
        )
        self._ensure_observation_weight_help_button()

        for editor in (self.ui.dateTimeEdit, self.ui.dateTimeEdit_2):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zzz")

        if not hasattr(self.ui, "pushButton_arc_start_now"):
            self.ui.pushButton_arc_start_now = QPushButton("当前", self.ui.horizontalLayoutWidget_21)
            self.ui.pushButton_arc_start_now.setObjectName("pushButton_arc_start_now")
            self.ui.horizontalLayout_21.insertWidget(3, self.ui.pushButton_arc_start_now)

        if not hasattr(self.ui, "pushButton_arc_end_now"):
            self.ui.pushButton_arc_end_now = QPushButton("+7天", self.ui.horizontalLayoutWidget_21)
            self.ui.pushButton_arc_end_now.setObjectName("pushButton_arc_end_now")
            self.ui.horizontalLayout_21.insertWidget(7, self.ui.pushButton_arc_end_now)

        if not hasattr(self.ui, "pushButton_arc_end_plus5"):
            self.ui.pushButton_arc_end_plus5 = QPushButton("+5天", self.ui.horizontalLayoutWidget_21)
            self.ui.pushButton_arc_end_plus5.setObjectName("pushButton_arc_end_plus5")
            self.ui.horizontalLayout_21.insertWidget(8, self.ui.pushButton_arc_end_plus5)

        time_layout = self.ui.horizontalLayout_21
        time_layout.removeWidget(self.ui.pushButton_arc_end_plus5)
        time_layout.removeWidget(self.ui.pushButton_arc_end_now)
        time_layout.insertWidget(7, self.ui.pushButton_arc_end_plus5)
        time_layout.insertWidget(8, self.ui.pushButton_arc_end_now)

        self.ui.pushButton_arc_start_now.setText("当前")
        self.ui.pushButton_arc_start_now.setToolTip("同步为电脑当前时间，并同步弧段结束时刻")
        self.ui.pushButton_arc_end_now.setText("+7天")
        self.ui.pushButton_arc_end_now.setToolTip("弧段结束时刻 = 弧段初始时刻 + 7 天")
        self.ui.pushButton_arc_end_plus5.setText("+5天")
        self.ui.pushButton_arc_end_plus5.setToolTip("弧段结束时刻 = 弧段初始时刻 + 5 天")

        time_font = QFont("Microsoft YaHei", 8)
        for widget in (
            self.ui.label_41,
            self.ui.dateTimeEdit,
            self.ui.pushButton_arc_start_now,
            self.ui.label_43,
            self.ui.dateTimeEdit_2,
            self.ui.pushButton_arc_end_plus5,
            self.ui.pushButton_arc_end_now,
        ):
            widget.setFont(time_font)

        for button in (self.ui.pushButton_arc_start_now, self.ui.pushButton_arc_end_now, self.ui.pushButton_arc_end_plus5):
            button.setMinimumHeight(18)
            button.setMaximumHeight(22)

        self.ui.pushButton_arc_start_now.clicked.connect(self._set_arc_start_to_now)
        self.ui.pushButton_arc_end_now.clicked.connect(lambda: self._set_arc_end_days_after_start(7))
        self.ui.pushButton_arc_end_plus5.clicked.connect(lambda: self._set_arc_end_days_after_start(5))

    def _comment_out_solar_panel_area(self):
        self.ui.label_36.hide()
        self.ui.lineEdit_28.hide()

    def _remove_albedo_radiation_row(self):
        for widget_name in ("horizontalLayoutWidget_20", "line_12"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        self.ui.label_40.hide()
        self.ui.checkBox.hide()

    def _comment_out_doppler_inverse_time(self):
        self.ui.label_48.hide()
        self.ui.lineEdit_37.hide()

    def _replace_orbit_step_edits(self):
        self.ui.comboBox_integ_step = self._ensure_step_combo(
            "comboBox_integ_step",
            self.ui.lineEdit_38,
            self.ui.horizontalLayout_27,
        )
        self.ui.comboBox_print_step = self._ensure_step_combo(
            "comboBox_print_step",
            self.ui.lineEdit_39,
            self.ui.horizontalLayout_27,
        )

        step_font = QFont("Microsoft YaHei", 8)
        for widget in (
            self.ui.label_49,
            self.ui.comboBox_integ_step,
            self.ui.label_50,
            self.ui.comboBox_print_step,
        ):
            widget.setFont(step_font)

    def _ensure_step_combo(self, name, old_edit, layout):
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
        for widget_name in ("horizontalLayoutWidget_29", "line_18"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        for widget in (
            self.ui.label_52,
            self.ui.lineEdit_40,
            self.ui.label_53,
            self.ui.lineEdit_41,
            self.ui.label_54,
            self.ui.lineEdit_42,
            self.ui.label_55,
            self.ui.comboBox_7,
        ):
            widget.hide()
            widget.setEnabled(False)

    def _remove_spice_kernel_path_row(self):
        for widget_name in ("horizontalLayoutWidget_30", "line_19"):
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.hide()
        self.ui.label_56.hide()
        self.ui.lineEdit_44.hide()
        self.ui.lineEdit_44.setEnabled(False)

    def _align_arc_parameter_labels(self):
        labels = (
            self.ui.label_32,
            self.ui.label_33,
            self.ui.label_34,
            self.ui.label_35,
            self.ui.label_37,
            self.ui.label_38,
            self.ui.label_39,
            self.ui.label_41,
            self.ui.label_43,
            self.ui.label_42,
            self.ui.label_44,
            self.ui.label_45,
            self.ui.label_46,
            self.ui.label_47,
            self.ui.label_49,
            self.ui.label_50,
        )
        for label in labels:
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def _align_arc_first_column(self):
        first_column_width = 168
        left_margin = 24
        for layout, label in (
            (self.ui.horizontalLayout_17, self.ui.label_32),
            (self.ui.horizontalLayout_18, self.ui.label_35),
            (self.ui.horizontalLayout_19, self.ui.label_38),
            (self.ui.horizontalLayout_21, self.ui.label_41),
            (self.ui.horizontalLayout_22, self.ui.label_42),
            (self.ui.horizontalLayout_23, self.ui.label_44),
            (self.ui.horizontalLayout_24, self.ui.label_45),
            (self.ui.horizontalLayout_25, self.ui.label_46),
            (self.ui.horizontalLayout_26, self.ui.label_47),
            (self.ui.horizontalLayout_27, self.ui.label_49),
        ):
            layout.setSpacing(4)
            self._set_spacer_width(layout, 0, left_margin)
            self._set_widget_width(label, first_column_width)

    def _set_arc_start_to_now(self):
        current = QDateTime.currentDateTime()
        self.ui.dateTimeEdit.setDateTime(current)
        self.ui.dateTimeEdit_2.setDateTime(current)

    def _set_arc_end_days_after_start(self, days):
        self.ui.dateTimeEdit_2.setDateTime(self.ui.dateTimeEdit.dateTime().addDays(days))

    @staticmethod
    def _lock_widgets(*widgets):
        for widget in widgets:
            widget.setEnabled(False)

    def _ensure_observation_weight_help_button(self):
        button = getattr(self.ui, "pushButton_obs_weight_help", None)
        if button is None:
            button = QPushButton("说明", self.ui.groupBox)
            button.setObjectName("pushButton_obs_weight_help")
            self.ui.pushButton_obs_weight_help = button
        button.setText("说明")
        button.setToolTip("查看观测值类型和权重说明")
        button.setGeometry(self.ui.pushButton_9.x(), self.ui.pushButton_9.y() + 30, self.ui.pushButton_9.width(), self.ui.pushButton_9.height())
        if not button.property("help_connected"):
            button.clicked.connect(self.show_observation_weight_help)
            button.setProperty("help_connected", True)

    def _apply_layout_polish(self):
        self.resize(1040, 720)
        self.setMinimumSize(1000, 680)
        self.ui.centralwidget.setMinimumSize(1000, 0)
        self.ui.verticalLayoutWidget.setGeometry(16, 48, 1008, 620)
        self.ui.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.verticalLayout.setSpacing(0)
        self.ui.tabWidget.setDocumentMode(True)

        toolbar_buttons = [
            self.ui.pushButton,
            self.ui.pushButton_2,
            self.ui.pushButton_3,
            self.ui.pushButton_4,
            self.ui.pushButton_5,
            self.ui.pushButton_6,
        ]
        x = 18
        for index, button in enumerate(toolbar_buttons):
            if index == 4:
                x += 18
            button.setGeometry(x, 8, 34, 34)
            button.setIconSize(QSize(22, 22))
            x += 40

    def _apply_style(self):
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
        section_labels = {
            "label_8", "label_125", "label_126", "label_127", "label_128",
            "label_58", "label_60",
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
                self.ui.pushButton,
                self.ui.pushButton_2,
                self.ui.pushButton_3,
                self.ui.pushButton_4,
                self.ui.pushButton_5,
                self.ui.pushButton_6,
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
        item = layout.itemAt(index)
        if item and item.spacerItem():
            item.spacerItem().changeSize(width, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

    def _set_expanding_spacer(self, layout, index, width=0):
        item = layout.itemAt(index)
        if item and item.spacerItem():
            item.spacerItem().changeSize(width, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

    def _ensure_trailing_expander(self, layout):
        if not layout.property("trailing_expander_added"):
            layout.addStretch(1)
            layout.setProperty("trailing_expander_added", True)

    def _set_widget_width(self, widget, width):
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)
        widget.setSizePolicy(QSizePolicy.Fixed, widget.sizePolicy().verticalPolicy())

    def _refresh_layout(self, layout):
        layout.invalidate()
        layout.activate()

    def _apply_global_page_layout(self):
        page_width = max(self.ui.tab.width() - 8, 980)
        rows = [
            self.ui.horizontalLayoutWidget,
            self.ui.horizontalLayoutWidget_2,
            self.ui.horizontalLayoutWidget_3,
            self.ui.horizontalLayoutWidget_4,
            self.ui.horizontalLayoutWidget_5,
            self.ui.horizontalLayoutWidget_6,
            self.ui.horizontalLayoutWidget_7,
            self.ui.horizontalLayoutWidget_8,
            self.ui.horizontalLayoutWidget_9,
            self.ui.horizontalLayoutWidget_10,
            self.ui.horizontalLayoutWidget_11,
            self.ui.horizontalLayoutWidget_12,
            self.ui.horizontalLayoutWidget_13,
            self.ui.horizontalLayoutWidget_14,
            self.ui.horizontalLayoutWidget_15,
            self.ui.horizontalLayoutWidget_16,
        ]
        for row in rows:
            row.setGeometry(0, row.geometry().y(), page_width, row.geometry().height())
            if row.layout():
                row.layout().setContentsMargins(0, 0, 0, 0)
                row.layout().setSpacing(6)

        for line_name in ("line", "line_2", "line_3", "line_4", "line_5", "line_6", "line_7", "line_8", "line_9"):
            line = getattr(self.ui, line_name, None)
            if line:
                line.setGeometry(0, line.geometry().y(), page_width, line.geometry().height())

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
            (self.ui.horizontalLayout, 0, [("label", label_w), ("Runmode", short_w)]),
            (self.ui.horizontalLayout_2, 0, [("label_2", label_w), ("Runmode_2", short_w)]),
            (self.ui.horizontalLayout_3, 0, [("label_3", label_w), ("ForceCent", check_w)]),
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
        self._set_widget_width(self.ui.label_4, label_w)
        self._set_widget_width(self.ui.comboBox, short_w)
        self._set_spacer_width(layout, 3, 24)
        self._set_widget_width(self.ui.label_5, label_w)
        self._set_widget_width(self.ui.spinBox, 72)
        self._set_spacer_width(layout, 6, 0)
        if self.ui.label_6.isVisible():
            self._set_widget_width(self.ui.label_6, label_w)
        if self.ui.spinBox_2.isVisible():
            self._set_widget_width(self.ui.spinBox_2, 72)
        self._ensure_trailing_expander(layout)
        self._set_expanding_spacer(layout, layout.count() - 1)
        self._refresh_layout(layout)

        layout = self.ui.horizontalLayout_5
        layout.setSpacing(4)
        self._set_spacer_width(layout, 0, left)
        self._set_widget_width(self.ui.label_7, label_w)
        for name in ("ForceCent_2", "ForceCent_3", "ForceCent_4", "ForceCent_5", "ForceCent_6", "ForceCent_7", "ForceCent_8", "ForceCent_9", "ForceCent_10", "ForceCent_11"):
            self._set_widget_width(getattr(self.ui, name), 58)
        self._set_spacer_width(layout, 12, 10)
        self._set_widget_width(self.ui.comboBox_2, 126)
        self._refresh_layout(layout)

        header = self.ui.horizontalLayout_6
        header.setSpacing(4)
        self._set_widget_width(self.ui.label_8, section_w)
        self._set_spacer_width(header, 1, 0)
        self._set_widget_width(self.ui.label_11, gm_w)
        self._set_spacer_width(header, 3, 0)
        self._set_widget_width(self.ui.label_12, radius_w)
        self._set_spacer_width(header, 5, header_pair_gap)
        self._set_widget_width(self.ui.label_9, gm_w)
        self._set_spacer_width(header, 7, 0)
        self._set_widget_width(self.ui.label_13, radius_w)
        for label in (self.ui.label_11, self.ui.label_12, self.ui.label_9, self.ui.label_13):
            label.setAlignment(Qt.AlignCenter)
        self._set_expanding_spacer(header, 9)
        self._refresh_layout(header)

        planet_rows = [
            ("horizontalLayout_7", "label_14", "lineEdit", "lineEdit_2", "label_15", "lineEdit_3", "lineEdit_4"),
            ("horizontalLayout_8", "label_16", "lineEdit_5", "lineEdit_6", "label_17", "lineEdit_7", "lineEdit_8"),
            ("horizontalLayout_9", "label_18", "lineEdit_9", "lineEdit_10", "label_19", "lineEdit_11", "lineEdit_12"),
            ("horizontalLayout_10", "label_20", "lineEdit_13", "lineEdit_14", "label_21", "lineEdit_15", "lineEdit_16"),
            ("horizontalLayout_11", "label_22", "lineEdit_17", "lineEdit_18", "label_23", "lineEdit_19", "lineEdit_20"),
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
        self._set_widget_width(self.ui.label_24, planet_label_w)
        self._set_spacer_width(sun, 4, inner_gap)
        self._set_widget_width(self.ui.lineEdit_21, gm_w)
        self._set_widget_width(self.ui.lineEdit_22, radius_w)
        self._set_expanding_spacer(sun, 7)
        self._refresh_layout(sun)

        for layout, spacer, label, checkbox in [
            (self.ui.horizontalLayout_13, 0, self.ui.label_10, self.ui.ForceCent_12),
            (self.ui.horizontalLayout_14, 0, self.ui.label_25, self.ui.ForceCent_13),
            (self.ui.horizontalLayout_15, 0, self.ui.label_27, self.ui.ForceCent_14),
            (self.ui.horizontalLayout_16, 0, self.ui.label_30, self.ui.ForceCent_15),
        ]:
            layout.setSpacing(0)
            self._set_spacer_width(layout, spacer, left)
            self._set_widget_width(label, label_w)
            self._set_widget_width(checkbox, check_w)
            self._ensure_trailing_expander(layout)
            self._set_expanding_spacer(layout, layout.count() - 1)
            self._refresh_layout(layout)

        self._set_spacer_width(self.ui.horizontalLayout_14, 3, 140)
        self._set_widget_width(self.ui.label_26, 166)
        self._set_widget_width(self.ui.comboBox_3, mid_w)
        self._refresh_layout(self.ui.horizontalLayout_14)

        self._set_spacer_width(self.ui.horizontalLayout_15, 3, 80)
        self._set_widget_width(self.ui.label_28, 154)
        self._set_widget_width(self.ui.lineEdit_23, 150)
        self._set_spacer_width(self.ui.horizontalLayout_15, 6, 30)
        self._set_widget_width(self.ui.label_29, 94)
        self._set_widget_width(self.ui.lineEdit_24, 130)
        self._refresh_layout(self.ui.horizontalLayout_15)

        self._set_spacer_width(self.ui.horizontalLayout_16, 3, 140)
        self._set_widget_width(self.ui.label_31, 166)
        self._set_widget_width(self.ui.comboBox_4, 150)
        self._set_widget_width(self.ui.label_51, 112)
        self._set_widget_width(self.ui.comboBox_6, 120)
        self._refresh_layout(self.ui.horizontalLayout_16)

    def _page_size(self, page):
        return max(page.width() - 8, 980), max(page.height() - 8, 560)

    def _stretch_width(self, widget, width):
        geometry = widget.geometry()
        widget.setGeometry(geometry.x(), geometry.y(), max(width - geometry.x(), 1), geometry.height())

    def _stretch_layout_rows(self, names, width):
        for name in names:
            widget = getattr(self.ui, name, None)
            if widget:
                self._stretch_width(widget, width)
                if widget.layout():
                    widget.layout().invalidate()

    def _move_button_column(self, buttons, x):
        for button in buttons:
            geometry = button.geometry()
            button.setGeometry(x, geometry.y(), geometry.width(), geometry.height())

    def _fill_table_with_side_buttons(self, table, buttons, page_width, page_height, bottom_margin=12):
        table_geometry = table.geometry()
        button_width = max(button.width() for button in buttons)
        button_x = max(page_width - button_width - 10, table_geometry.x() + 280)
        table_width = max(button_x - table_geometry.x() - 9, 320)
        table_height = max(page_height - table_geometry.y() - bottom_margin, 120)
        table.setGeometry(table_geometry.x(), table_geometry.y(), table_width, table_height)
        self._move_button_column(buttons, button_x)

    def _fill_group_table_with_side_buttons(self, group, table, buttons):
        table_geometry = table.geometry()
        button_width = max(button.width() for button in buttons)
        button_x = max(group.width() - button_width - 10, table_geometry.x() + 180)
        table_width = max(button_x - table_geometry.x() - 9, 180)
        table_height = max(group.height() - table_geometry.y() - 10, 80)
        table.setGeometry(table_geometry.x(), table_geometry.y(), table_width, table_height)
        self._move_button_column(buttons, button_x)

    def _fill_group_table_below_buttons(self, group, table):
        geometry = table.geometry()
        table.setGeometry(
            geometry.x(),
            geometry.y(),
            max(group.width() - geometry.x() - 10, 180),
            max(group.height() - geometry.y() - 10, 80),
        )

    def _apply_arc_page_layout(self, page_width, page_height):
        self._compact_arc_parameter_rows()
        self._compact_arc_integrator_gap()
        self._stretch_layout_rows([f"horizontalLayoutWidget_{index}" for index in range(17, 31)], page_width)
        for line_name in (f"line_{index}" for index in range(10, 20)):
            line = getattr(self.ui, line_name, None)
            if line:
                self._stretch_width(line, page_width)

        self._align_arc_first_column()

        time_layout = self.ui.horizontalLayout_21
        for label in (
            self.ui.label_33,
            self.ui.label_34,
        ):
            self._set_widget_width(label, 150)

        self._set_widget_width(self.ui.dateTimeEdit, 185)
        self._set_widget_width(self.ui.pushButton_arc_start_now, 48)
        self._set_spacer_width(time_layout, 4, 24)
        self._set_widget_width(self.ui.label_43, 150)
        self._set_widget_width(self.ui.dateTimeEdit_2, 185)
        self._set_widget_width(self.ui.pushButton_arc_end_now, 48)
        self._set_widget_width(self.ui.pushButton_arc_end_plus5, 48)
        self._set_expanding_spacer(time_layout, 9)
        self._refresh_layout(time_layout)

        self._set_widget_width(self.ui.lineEdit_27, 96)
        self._set_spacer_width(self.ui.horizontalLayout_18, 3, 16)
        self._set_widget_width(self.ui.label_37, 150)
        self._set_widget_width(self.ui.lineEdit_29, 78)
        self._set_expanding_spacer(self.ui.horizontalLayout_18, self.ui.horizontalLayout_18.count() - 1)
        self._set_widget_width(self.ui.lineEdit_30, 96)
        self._set_spacer_width(self.ui.horizontalLayout_19, 3, 16)
        self._set_widget_width(self.ui.label_39, 86)
        self._set_widget_width(self.ui.lineEdit_31, 96)
        self._set_expanding_spacer(self.ui.horizontalLayout_19, self.ui.horizontalLayout_19.count() - 1)
        self._set_widget_width(self.ui.lineEdit_36, 76)
        self._set_widget_width(self.ui.comboBox_integ_step, 76)
        self._set_widget_width(self.ui.label_50, 150)
        self._set_widget_width(self.ui.comboBox_print_step, 76)
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

        tab_geometry = self.ui.tabWidget_2.geometry()
        self.ui.tabWidget_2.setGeometry(
            tab_geometry.x(),
            tab_geometry.y(),
            max(page_width - tab_geometry.x(), 640),
            max(page_height - tab_geometry.y() + 8, 220),
        )

        sub_width = max(self.ui.tabWidget_2.width() - 8, 940)
        sub_height = max(self.ui.tabWidget_2.height() - 28, 210)
        half_width = sub_width // 2

        for left_group, right_group in ((self.ui.groupBox, self.ui.groupBox_3), (self.ui.groupBox_2, self.ui.groupBox_4)):
            top = left_group.geometry().y()
            left_group.setGeometry(0, top, half_width, max(sub_height - top, 140))
            right_group.setGeometry(half_width, top, sub_width - half_width - 8, left_group.height())

        weight_buttons = [self.ui.pushButton_7, self.ui.pushButton_8, self.ui.pushButton_9]
        if hasattr(self.ui, "pushButton_obs_weight_help"):
            weight_buttons.append(self.ui.pushButton_obs_weight_help)
        self._fill_group_table_with_side_buttons(self.ui.groupBox, self.ui.tableWidget_2, weight_buttons)
        self._fill_group_table_with_side_buttons(self.ui.groupBox_3, self.ui.tableWidget_4, [self.ui.pushButton_13, self.ui.pushButton_14, self.ui.pushButton_15])
        self._fill_group_table_below_buttons(self.ui.groupBox_2, self.ui.tableWidget_8)
        self._fill_group_table_below_buttons(self.ui.groupBox_4, self.ui.tableWidget_16)

        for table, buttons in (
            (self.ui.tableWidget_5, [self.ui.pushButton_16, self.ui.pushButton_18, self.ui.pushButton_17]),
            (self.ui.tableWidget_6, [self.ui.pushButton_19, self.ui.pushButton_21, self.ui.pushButton_20]),
            (self.ui.tableWidget_7, [self.ui.pushButton_22, self.ui.pushButton_24, self.ui.pushButton_23]),
        ):
            self._fill_table_with_side_buttons(table, buttons, sub_width, sub_height, bottom_margin=0)
        self._fit_observation_bias_columns()
        self._fit_select_observation_columns()

        self._stretch_layout_rows(["horizontalLayoutWidget_31"], sub_width)

    def _apply_secondary_pages_layout(self):
        page_width, page_height = self._page_size(self.ui.tab_2)
        self._apply_arc_page_layout(page_width, page_height)

        for tab, row_names, table, buttons in (
            (self.ui.tab_3, ["horizontalLayoutWidget_32"], self.ui.tableWidget_17, [self.ui.pushButton_73, self.ui.pushButton_75, self.ui.pushButton_74]),
            (self.ui.tab_4, ["horizontalLayoutWidget_65"], self.ui.tableWidget_26, [self.ui.pushButton_76, self.ui.pushButton_77, self.ui.pushButton_78]),
        ):
            page_width, page_height = self._page_size(tab)
            self._stretch_layout_rows(row_names, page_width)
            self._fill_table_with_side_buttons(table, buttons, page_width, page_height)
            if table is self.ui.tableWidget_26:
                self._fit_station_columns()

        page_width, page_height = self._page_size(self.ui.tab_5)
        self.ui.groupBox_9.setGeometry(
            0,
            0,
            max(page_width, 320),
            max(page_height, 160),
        )
        self._stretch_layout_rows(["horizontalLayoutWidget_68"], self.ui.groupBox_9.width())
        text_geometry = self.ui.textEdit.geometry()
        self.ui.textEdit.setGeometry(
            text_geometry.x(),
            text_geometry.y(),
            max(self.ui.groupBox_9.width() - text_geometry.x(), 320),
            max(self.ui.groupBox_9.height() - text_geometry.y() - 10, 100),
        )

        page_width, page_height = self._page_size(self.ui.tab_6)
        self._stretch_layout_rows(["horizontalLayoutWidget_69"], page_width)
        visual_geometry = self.ui.widget.geometry()
        self.ui.widget.setGeometry(
            visual_geometry.x(),
            visual_geometry.y(),
            max(page_width - visual_geometry.x(), 320),
            max(page_height - visual_geometry.y(), 160),
        )

    def _refresh_responsive_layout(self):
        if hasattr(self, "ui"):
            self.ui.verticalLayoutWidget.setGeometry(16, 48, max(self.width() - 32, 968), max(self.height() - 100, 580))
            self._apply_global_page_layout()
            self._apply_secondary_pages_layout()

    def _schedule_layout_refresh(self, *_):
        QTimer.singleShot(0, self._refresh_responsive_layout)
        QTimer.singleShot(50, self._refresh_responsive_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_responsive_layout()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_layout_refresh()

    def _apply_toolbar_icons(self):
        buttons = [
            (self.ui.pushButton, "new_scheme.png", "新建定轨方案"),
            (self.ui.pushButton_2, "open_scheme.png", "打开定轨方案"),
            (self.ui.pushButton_3, "save_scheme.png", "保存定轨方案"),
            (self.ui.pushButton_4, "save_as_scheme.png", "另存为定轨方案"),
            (self.ui.pushButton_5, "run_orbit.png", "开始定轨"),
            (self.ui.pushButton_6, "chart.png", "查看图表"),
        ]
        for button, icon_name, tooltip in buttons:
            path = iconsource_rc.icon_path(icon_name)
            if Path(path).exists():
                button.setIcon(QIcon(path))
                button.setIconSize(QSize(20, 20))
                button.setText("")
            button.setToolTip(tooltip)

    def _connect_signals(self):
        self.ui.tabWidget.currentChanged.connect(self._schedule_layout_refresh)
        self.ui.tabWidget_2.currentChanged.connect(self._schedule_layout_refresh)
        self.ui.Runmode_2.currentIndexChanged.connect(self._sync_integration_center_controls)
        self.ui.tableWidget_2.itemChanged.connect(self._on_observation_weight_item_changed)
        self.ui.tableWidget_6.itemChanged.connect(self._on_select_observation_item_changed)
        self.ui.tableWidget_16.itemChanged.connect(self._on_per_acc_item_changed)

        self.ui.pushButton.clicked.connect(self.new_scheme)
        self.ui.pushButton_2.clicked.connect(self.open_scheme)
        self.ui.pushButton_3.clicked.connect(self.save_scheme)
        self.ui.pushButton_4.clicked.connect(self.save_scheme_as)
        self.ui.pushButton_5.clicked.connect(self.start_orbit_determination)
        self.ui.pushButton_6.clicked.connect(lambda: self.ui.tabWidget.setCurrentWidget(self.ui.tab_6))

        self.ui.action1.triggered.connect(self.new_scheme)
        self.ui.action1_2.triggered.connect(self.open_scheme)
        self.ui.action2.triggered.connect(self.save_scheme)
        self.ui.action3.triggered.connect(self.save_scheme_as)
        self.ui.action1_3.triggered.connect(lambda: self.import_card("GCP"))
        self.ui.action2_2.triggered.connect(lambda: self.import_card("LCP"))
        self.ui.action3_2.triggered.connect(lambda: self.import_card("SimCP"))
        self.ui.action4.triggered.connect(lambda: self.import_card("StaCP"))
        self.ui.action1_4.triggered.connect(self.start_orbit_determination)
        self.ui.actiond.triggered.connect(lambda: self.ui.tabWidget.setCurrentWidget(self.ui.tab_6))
        self.ui.actiona.triggered.connect(self.show_about)

        self.ui.toolButton.clicked.connect(lambda: self.import_card("SimCP"))
        self.ui.toolButton_2.clicked.connect(self.configure_and_generate_observations)
        # 全局/弧段参数解算和小行星星历解算入口已停用，仅保留定轨过程。
        # self.ui.toolButton_5.clicked.connect(self.start_orbit_determination)
        # self.ui.toolButton_6.clicked.connect(self.select_ast_ephe_exe)
        # self.ui.pushButton_79.clicked.connect(self.copy_observations_to_arc)
        # self.ui.pushButton_80.clicked.connect(self.process_observation_files)
        # self.ui.pushButton_81.clicked.connect(self.configure_ast_ephe_observations)
        # self.ui.pushButton_82.clicked.connect(self.merge_ephemeris)
        self.ui.pushButton_83.clicked.connect(self.show_orbit_plot)
        self.ui.pushButton_86.clicked.connect(self.show_residual_plot)
        self.ui.pushButton_85.clicked.connect(self.clear_visual_widget)
        self.ui.pushButton_84.clicked.connect(self.stop_tasks)

    def _init_default_tables(self):
        defaults = {
            self.ui.tableWidget_2: [["51-双程测距", "2.0D-0", "meter"], ["52-双程测速", "1.0D-0", "mm/s"]],
            self.ui.tableWidget_4: [["51", "4.0D-0", "1.0D+15"]],
            self.ui.tableWidget_5: [["51", "001", "001", "10.0D0", "", "", "1.0D-15"]],
            self.ui.tableWidget_6: [["1-双程测距", "6", "6", "", "0000000", "0000000", "", ""]],
            self.ui.tableWidget_7: [["2", "6", "6", "0000000", "0000000", "", ""]],
            self.ui.tableWidget_8: [["1", "", "", "TDB"]],
            self.ui.tableWidget_16: [["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]],
            self.ui.tableWidget_17: [self._simulation_observation_default_row()],
            self.ui.tableWidget_26: [self._station_default_row()],
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
        return [
            self.ui.tableWidget_2,
            self.ui.tableWidget_4,
            self.ui.tableWidget_5,
            self.ui.tableWidget_6,
            self.ui.tableWidget_7,
            self.ui.tableWidget_8,
            self.ui.tableWidget_16,
            self.ui.tableWidget_17,
            self.ui.tableWidget_26,
        ]

    def _apply_configured_table_fonts(self):
        for table in self._configured_tables():
            TableTools.apply_font(table)

    def _simulation_observation_default_row(self):
        start = self.ui.dateTimeEdit.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        end = self.ui.dateTimeEdit_2.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        return ["0000", "", "", "", "", start, end, "51", "2.000d-0", "30.000"]

    def _station_default_row(self):
        return ["001", "SHAO", "激活", "15.0", "直角坐标系XYZ", "-2831686.9130", "4675733.6660", "3275327.6900", "", "", "", "", "地球测站"]

    def _add_station_row(self):
        TableTools.add_row(self.ui.tableWidget_26, [], self._station_default_row())
        self._configure_station_table()

    def _setup_tables(self):
        configs = [
            (self.ui.tableWidget_2, self.ui.pushButton_7, self.ui.pushButton_8, self.ui.pushButton_9, [], ["51-双程测距", "2.0D-0", "meter"]),
            (self.ui.tableWidget_4, self.ui.pushButton_13, self.ui.pushButton_14, self.ui.pushButton_15, [], ["51", "4.0D-0", "1.0D+15"]),
            (self.ui.tableWidget_5, self.ui.pushButton_16, self.ui.pushButton_18, self.ui.pushButton_17, [4, 5], ["51", "001", "001", "10.0D0", "", "", "1.0D-15"]),
            (self.ui.tableWidget_6, self.ui.pushButton_19, self.ui.pushButton_21, self.ui.pushButton_20, [6, 7], ["1-双程测距", "6", "6", "", "0000000", "0000000", "", ""]),
            (self.ui.tableWidget_7, self.ui.pushButton_22, self.ui.pushButton_24, self.ui.pushButton_23, [5, 6], ["2", "6", "6", "0000000", "0000000", "", ""]),
            (self.ui.tableWidget_8, self.ui.pushButton_25, self.ui.pushButton_26, self.ui.pushButton_27, [1, 2], ["1", "", "", "TDB"]),
            (self.ui.tableWidget_16, self.ui.pushButton_51, self.ui.pushButton_50, self.ui.pushButton_49, [], ["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]),
            (self.ui.tableWidget_17, self.ui.pushButton_73, self.ui.pushButton_75, self.ui.pushButton_74, [5, 6], self._simulation_observation_default_row),
        ]
        for table, add_btn, edit_btn, del_btn, datetime_columns, default_row in configs:
            TableTools.setup(table, datetime_columns)
            add_btn.clicked.connect(lambda _, t=table, cols=datetime_columns, row=default_row: TableTools.add_row(t, cols, row))
            edit_btn.clicked.connect(lambda _, t=table, cols=datetime_columns: TableTools.edit_row(t, self, cols))
            del_btn.clicked.connect(lambda _, t=table: TableTools.delete_row(t, self))
        TableTools.setup(self.ui.tableWidget_26, [])
        self.ui.pushButton_76.clicked.connect(self._add_station_row)
        self.ui.pushButton_77.clicked.connect(lambda: TableTools.edit_row(self.ui.tableWidget_26, self, []))
        self.ui.pushButton_78.clicked.connect(lambda: TableTools.delete_row(self.ui.tableWidget_26, self))
        self._configure_observation_weight_table()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_per_acc_table()
        self._configure_station_table()

    def _configure_per_acc_table(self):
        table = self.ui.tableWidget_16
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
        table = self.ui.tableWidget_26
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
        table = self.ui.tableWidget_26
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
        widget = table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        item = table.item(row, col)
        return item.text().strip() if item and item.text() else ""

    def _configure_select_observation_table(self):
        table = self.ui.tableWidget_6
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
        table = self.ui.tableWidget_6
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

    def _configure_observation_bias_table(self):
        table = self.ui.tableWidget_5
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
        table = self.ui.tableWidget_5
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
        table = self.ui.tableWidget_2
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
        text = str(value or "").strip()
        for code in OBSERVATION_WEIGHT_HELP:
            if text == code or text.startswith(f"{code}-"):
                return code
        return text

    @staticmethod
    def _observation_type_label(code):
        code = str(code or "").strip()
        info = OBSERVATION_WEIGHT_HELP.get(code)
        return f"{code}-{info[0]}" if info else code

    @staticmethod
    def _observation_unit(code):
        info = OBSERVATION_WEIGHT_HELP.get(str(code or "").strip())
        return info[1] if info else ""

    @staticmethod
    def _select_observation_type_code(value):
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
        code = str(code or "").strip()
        label = SELECT_OBSERVATION_TYPE_HELP.get(code)
        return f"{code}-{label}" if label else code

    @staticmethod
    def _coded_label_code(value, mapping):
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
        code = str(code or "").strip()
        label = mapping.get(code)
        return f"{code}-{label}" if label else code

    def _sync_observation_weight_row(self, row):
        if row < 0 or self._syncing_observation_weight:
            return
        table = self.ui.tableWidget_2
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

    def _sync_per_acc_row(self, row):
        if row < 0 or self._syncing_per_acc:
            return
        table = self.ui.tableWidget_16
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
        if item and item.tableWidget() is self.ui.tableWidget_2 and item.column() in (0, 2):
            self._sync_observation_weight_row(item.row())

    def _on_select_observation_item_changed(self, item):
        if (
            not item
            or item.tableWidget() is not self.ui.tableWidget_6
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

    def _on_per_acc_item_changed(self, item):
        if item and item.tableWidget() is self.ui.tableWidget_16 and item.column() in (0, 1):
            self._sync_per_acc_row(item.row())

    def new_scheme(self):
        self._configure_global_parameters()
        self._init_default_tables()
        self._setup_datetime_cells()
        self._configure_observation_weight_table()
        self._configure_observation_bias_table()
        self._configure_select_observation_table()
        self._configure_per_acc_table()
        self._apply_configured_table_fonts()
        self.current_scheme_dir = DEFAULT_SCHEME_DIR
        self.ui.textEdit.clear()
        self._log("已新建默认定轨方案。")

    def open_scheme(self):
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
        self._save_cards(self.current_scheme_dir)

    def save_scheme_as(self):
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录", str(self.current_scheme_dir))
        if not directory:
            return
        self.current_scheme_dir = Path(directory)
        self._save_cards(self.current_scheme_dir)

    def import_card(self, card_name: str):
        file_path, _ = QFileDialog.getOpenFileName(self, f"选择 {card_name} 文件", str(self.current_scheme_dir), "卡片文件 (*);;所有文件 (*)")
        if file_path:
            self._load_card_from_path(card_name, Path(file_path))
            self._setup_datetime_cells()
            self._apply_configured_table_fonts()
            self._log(f"已导入 {card_name}：{file_path}")

    def _save_cards(self, directory: Path):
        self._write_cards(directory, notify=True)

    def _write_cards(self, directory: Path, notify: bool = False):
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
        elif card_name == "StaCP":
            self._configure_station_table()

    def show_observation_weight_help(self):
        lines = []
        table = self.ui.tableWidget_2
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
        item = table.item(row, col)
        return item.text().strip() if item and item.text() else ""

    def configure_and_generate_observations(self):
        self._write_cards(self.current_scheme_dir)
        self._run_usefortran("正在配置并生成模拟观测值，请稍候...", self._genobs_job)

    def _genobs_job(self):
        self._require_usefortran()
        msg = UseFortran.copy_simcp_to_target()
        output = UseFortran.genobs(self.ui)
        return f"{msg}\n{output}"

    def copy_observations_to_arc(self):
        self._write_cards(self.current_scheme_dir)
        result = self._copy_obs_files_to_arc(self.ui.lineEdit_87.text().strip())
        self._log(result)

    @staticmethod
    def _copy_obs_files_to_arc(arc_id: str) -> str:
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
        self._run_usefortran("正在处理观测值文件...", self._process_obs_job)

    def _process_obs_job(self):
        self._require_usefortran()
        base = APP_DIR / "output" / "Arc"
        messages = []
        for arc_id in ("001", "002", "003"):
            path = base / arc_id / "InputDATA"
            messages.append(f"弧段 {arc_id}: {UseFortran.process_obs_files(str(path))}")
        return "\n".join(messages)

    def select_solve_global_exe(self):
        default = APP_DIR / "external" / "Solve_Global_Para.exe"
        self._select_and_run_exe(default, "选择全局参数与弧段参数解算程序")

    def select_ast_ephe_exe(self):
        default = APP_DIR / "external" / "Batch_developing.exe"
        self._select_and_run_exe(default, "选择小行星星历解算程序")

    def start_orbit_determination(self):
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

        self.ui.tabWidget.setCurrentWidget(self.ui.tab_5)
        self.ui.textEdit.clear()
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
        self.ui.pushButton_5.setEnabled(False)
        self.ui.action1_4.setEnabled(False)
        process.start()

    def _on_orbit_process_started(self):
        self._log("外部定轨程序已启动，正在实时接收命令行输出...")

    def _read_orbit_stdout(self):
        if not self.orbit_process or not self._orbit_stdout_decoder:
            return
        data = bytes(self.orbit_process.readAllStandardOutput())
        self._append_log_text(self._orbit_stdout_decoder.decode(data))

    def _read_orbit_stderr(self):
        if not self.orbit_process or not self._orbit_stderr_decoder:
            return
        data = bytes(self.orbit_process.readAllStandardError())
        text = self._orbit_stderr_decoder.decode(data)
        if text:
            self._append_log_text(f"[stderr] {text}")

    def _on_orbit_process_error(self, error):
        if error == QProcess.FailedToStart:
            detail = self.orbit_process.errorString() if self.orbit_process else "未知错误"
            self._log(f"定轨程序启动失败：{detail}")
            self.ui.pushButton_5.setEnabled(True)
            self.ui.action1_4.setEnabled(True)
            if self.orbit_process:
                self.orbit_process.deleteLater()
            self.orbit_process = None
            self._orbit_stdout_decoder = None
            self._orbit_stderr_decoder = None

    def _on_orbit_process_finished(self, exit_code, exit_status):
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
        self.ui.pushButton_5.setEnabled(True)
        self.ui.action1_4.setEnabled(True)
        if self.orbit_process:
            self.orbit_process.deleteLater()
        self.orbit_process = None
        self._orbit_stdout_decoder = None
        self._orbit_stderr_decoder = None

    def _select_and_run_exe(self, default_path: Path, title: str):
        start_dir = str(default_path.parent if default_path.parent.exists() else LEGACY_DIR)
        file_path, _ = QFileDialog.getOpenFileName(self, title, start_dir, "可执行程序 (*.exe);;所有文件 (*)")
        if file_path:
            self._run_exe(Path(file_path))

    def _run_exe(self, exe_path: Path):
        self._run_usefortran(f"正在运行：{exe_path}", lambda: self._execute_program(exe_path))

    @staticmethod
    def _execute_program(exe_path: Path):
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
        self._run_usefortran("正在配置小行星星历观测值...", self._gen_obs_for_asteph_job)

    def _gen_obs_for_asteph_job(self):
        self._require_usefortran()
        with working_directory(LEGACY_DIR):
            return UseFortran.run_gen_obs_for_solve_asteph()

    def merge_ephemeris(self):
        self._run_usefortran("正在融合多弧段探测器星历...", self._merge_ephe_job)

    def _merge_ephe_job(self):
        self._require_usefortran()
        with working_directory(LEGACY_DIR):
            return UseFortran.merge_our_own_ephe()

    def show_orbit_plot(self):
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
            canvas = OrbitPlotCanvas(file_path, parent=self.ui.widget)
            layout = self._visual_layout()
            layout.addWidget(canvas)
            canvas.start_animation()
            self.ui.tabWidget.setCurrentWidget(self.ui.tab_6)
        except Exception as exc:
            QMessageBox.critical(self, "绘图失败", str(exc))

    def show_residual_plot(self):
        try:
            from Residual import show_residual_in_widget2

            self.clear_visual_widget()
            show_residual_in_widget2(self, self.ui.widget)
            self.ui.tabWidget.setCurrentWidget(self.ui.tab_6)
        except Exception as exc:
            QMessageBox.critical(self, "残差分析失败", str(exc))

    def clear_visual_widget(self):
        layout = self.ui.widget.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def _visual_layout(self):
        layout = self.ui.widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui.widget)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def stop_tasks(self):
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
            self.ui.textEdit.clear()
            self.ui.statusbar.showMessage("定轨输出已清空。")

    def _run_usefortran(self, start_message: str, func):
        self._run_task(start_message, func)

    def _run_task(self, start_message: str, func):
        self.ui.tabWidget.setCurrentWidget(self.ui.tab_5)
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
        self._log(text or "任务完成。")

    def _on_worker_error(self, text: str):
        self._log(f"任务失败：{text}")

    def _require_usefortran(self):
        if UseFortran is None:
            raise RuntimeError("旧项目 UseFortran.py 模块导入失败。")

    def _setup_datetime_cells(self):
        for table, columns in [
            (self.ui.tableWidget_5, [4, 5]),
            (self.ui.tableWidget_6, [6, 7]),
            (self.ui.tableWidget_7, [5, 6]),
            (self.ui.tableWidget_8, [1, 2]),
            (self.ui.tableWidget_17, [5, 6]),
        ]:
            for row in range(table.rowCount()):
                for col in columns:
                    if table.cellWidget(row, col) is None:
                        item = table.item(row, col)
                        value = item.text().strip() if item and item.text().strip() else None
                        card_io.set_datetime_cell(table, row, col, value)
            TableTools.apply_font(table)

    def _log(self, message: str):
        if self.ui.textEdit.toPlainText() and not self.ui.textEdit.toPlainText().endswith("\n"):
            self._append_log_text("\n")
        self._append_log_text(f"{message.rstrip()}\n" if message else "")
        self.ui.statusbar.showMessage(message.splitlines()[0] if message else "")

    def _append_log_text(self, text: str):
        if not text:
            return
        cursor = self.ui.textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.textEdit.setTextCursor(cursor)
        self.ui.textEdit.ensureCursorVisible()

    def show_about(self):
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
        self.stop_tasks()
        super().closeEvent(event)


def configure_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def load_app_icon() -> QIcon:
    icon_path = iconsource_rc.icon_path(APP_ICON_NAME)
    return QIcon(icon_path) if Path(icon_path).exists() else QIcon()


def main():
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
