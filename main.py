from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, QDateTime, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
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
CARD_NAMES = ("GCP", "LCP", "SimCP", "StaCP")
APP_ICON_NAME = "app_icon.ico"
WINDOWS_APP_ID = "wjk.orbit-determination.platform"

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
                    card_io.set_datetime_cell(table, row, col)
        TableTools.apply_font(table)

    @staticmethod
    def add_row(table: QTableWidget, datetime_columns=None, defaults=None):
        datetime_columns = datetime_columns or []
        defaults = defaults or []
        row = table.rowCount()
        table.insertRow(row)
        for col in range(table.columnCount()):
            if col in datetime_columns:
                card_io.set_datetime_cell(table, row, col)
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
        self._configure_ui()
        self._connect_signals()

    def _configure_ui(self):
        self.setWindowTitle("小天体测地学参数探测平台")
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
        self._apply_global_page_layout()
        self._apply_secondary_pages_layout()
        self._init_default_tables()
        self._setup_tables()

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
            QCheckBox {
                spacing: 5px;
                color: #334155;
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
        self._set_spacer_width(layout, 0, left)
        self._set_widget_width(self.ui.label_4, label_w)
        self._set_widget_width(self.ui.comboBox, short_w)
        self._set_spacer_width(layout, 3, 24)
        self._set_widget_width(self.ui.label_5, label_w)
        self._set_widget_width(self.ui.spinBox, 72)
        self._set_spacer_width(layout, 6, 24)
        self._set_widget_width(self.ui.label_6, label_w)
        self._set_widget_width(self.ui.spinBox_2, 72)
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
            self._set_spacer_width(layout, spacer, left)
            self._set_widget_width(label, label_w)
            self._set_widget_width(checkbox, check_w)
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
        self._stretch_layout_rows([f"horizontalLayoutWidget_{index}" for index in range(17, 31)], page_width)
        for line_name in (f"line_{index}" for index in range(10, 20)):
            line = getattr(self.ui, line_name, None)
            if line:
                self._stretch_width(line, page_width)

        tab_geometry = self.ui.tabWidget_2.geometry()
        self.ui.tabWidget_2.setGeometry(
            tab_geometry.x(),
            tab_geometry.y(),
            max(page_width - tab_geometry.x(), 640),
            max(page_height - tab_geometry.y(), 180),
        )

        sub_width = max(self.ui.tabWidget_2.width() - 8, 940)
        sub_height = max(self.ui.tabWidget_2.height() - 32, 170)
        half_width = sub_width // 2

        for left_group, right_group in ((self.ui.groupBox, self.ui.groupBox_3), (self.ui.groupBox_2, self.ui.groupBox_4)):
            top = left_group.geometry().y()
            left_group.setGeometry(0, top, half_width, max(sub_height - top - 8, 120))
            right_group.setGeometry(half_width, top, sub_width - half_width - 8, left_group.height())

        self._fill_group_table_with_side_buttons(self.ui.groupBox, self.ui.tableWidget_2, [self.ui.pushButton_7, self.ui.pushButton_8, self.ui.pushButton_9])
        self._fill_group_table_with_side_buttons(self.ui.groupBox_3, self.ui.tableWidget_4, [self.ui.pushButton_13, self.ui.pushButton_14, self.ui.pushButton_15])
        self._fill_group_table_below_buttons(self.ui.groupBox_2, self.ui.tableWidget_8)
        self._fill_group_table_below_buttons(self.ui.groupBox_4, self.ui.tableWidget_16)

        for table, buttons in (
            (self.ui.tableWidget_5, [self.ui.pushButton_16, self.ui.pushButton_18, self.ui.pushButton_17]),
            (self.ui.tableWidget_6, [self.ui.pushButton_19, self.ui.pushButton_21, self.ui.pushButton_20]),
            (self.ui.tableWidget_7, [self.ui.pushButton_22, self.ui.pushButton_24, self.ui.pushButton_23]),
        ):
            self._fill_table_with_side_buttons(table, buttons, sub_width, sub_height)

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

        page_width, page_height = self._page_size(self.ui.tab_5)
        self._stretch_layout_rows(["horizontalLayoutWidget_66", "horizontalLayoutWidget_67"], page_width)
        group_geometry = self.ui.groupBox_9.geometry()
        self.ui.groupBox_9.setGeometry(
            group_geometry.x(),
            group_geometry.y(),
            max(page_width - group_geometry.x(), 320),
            max(page_height - group_geometry.y(), 160),
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "ui"):
            self.ui.verticalLayoutWidget.setGeometry(16, 48, max(self.width() - 32, 968), max(self.height() - 100, 580))
            self._apply_global_page_layout()
            self._apply_secondary_pages_layout()

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
        self.ui.toolButton_5.clicked.connect(self.start_orbit_determination)
        self.ui.toolButton_6.clicked.connect(self.select_ast_ephe_exe)
        self.ui.pushButton_79.clicked.connect(self.copy_observations_to_arc)
        self.ui.pushButton_80.clicked.connect(self.process_observation_files)
        self.ui.pushButton_81.clicked.connect(self.configure_ast_ephe_observations)
        self.ui.pushButton_82.clicked.connect(self.merge_ephemeris)
        self.ui.pushButton_83.clicked.connect(self.show_orbit_plot)
        self.ui.pushButton_86.clicked.connect(self.show_residual_plot)
        self.ui.pushButton_85.clicked.connect(self.clear_visual_widget)
        self.ui.pushButton_84.clicked.connect(self.stop_tasks)

    def _init_default_tables(self):
        defaults = {
            self.ui.tableWidget_2: [["51", "2.0D-0", "10"], ["52", "1.0D-0", "20"]],
            self.ui.tableWidget_4: [["51", "4.0D-0", "1.0D+15"]],
            self.ui.tableWidget_5: [["51", "6", "6", "10.0D0", "", "", "1.0D-15"]],
            self.ui.tableWidget_6: [["51", "6", "6", "0000000", "0000000", "", ""]],
            self.ui.tableWidget_7: [["2", "6", "6", "0000000", "0000000", "", ""]],
            self.ui.tableWidget_8: [["1", "", "", "TDB"]],
            self.ui.tableWidget_16: [["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]],
            self.ui.tableWidget_17: [["0000", "", "", "", "", "", "", "51", "2.000d-0", "30.000"]],
            self.ui.tableWidget_26: [["001", "SHAO", "1", "15.0", "-2831686.9130", "4675733.6660", "3275327.6900", "", "", "", "0"]],
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

    def _setup_tables(self):
        configs = [
            (self.ui.tableWidget_2, self.ui.pushButton_7, self.ui.pushButton_8, self.ui.pushButton_9, [], ["51", "2.0D-0", "10"]),
            (self.ui.tableWidget_4, self.ui.pushButton_13, self.ui.pushButton_14, self.ui.pushButton_15, [], ["51", "4.0D-0", "1.0D+15"]),
            (self.ui.tableWidget_5, self.ui.pushButton_16, self.ui.pushButton_18, self.ui.pushButton_17, [4, 5], ["51", "6", "6", "10.0D0", "", "", "1.0D-15"]),
            (self.ui.tableWidget_6, self.ui.pushButton_19, self.ui.pushButton_21, self.ui.pushButton_20, [5, 6], ["51", "6", "6", "0000000", "0000000", "", ""]),
            (self.ui.tableWidget_7, self.ui.pushButton_22, self.ui.pushButton_24, self.ui.pushButton_23, [5, 6], ["2", "6", "6", "0000000", "0000000", "", ""]),
            (self.ui.tableWidget_8, self.ui.pushButton_25, self.ui.pushButton_26, self.ui.pushButton_27, [1, 2], ["1", "", "", "TDB"]),
            (self.ui.tableWidget_16, self.ui.pushButton_51, self.ui.pushButton_50, self.ui.pushButton_49, [], ["1", "3", "0.295304904947824E-05", "0.577322948775672E-06"]),
            (self.ui.tableWidget_17, self.ui.pushButton_73, self.ui.pushButton_75, self.ui.pushButton_74, [5, 6], ["0000", "", "", "", "", "", "", "51", "2.000d-0", "30.000"]),
            (self.ui.tableWidget_26, self.ui.pushButton_76, self.ui.pushButton_77, self.ui.pushButton_78, [], ["001", "SHAO", "1", "15.0", "-2831686.9130", "4675733.6660", "3275327.6900", "", "", "", "0"]),
        ]
        for table, add_btn, edit_btn, del_btn, datetime_columns, default_row in configs:
            TableTools.setup(table, datetime_columns)
            add_btn.clicked.connect(lambda _, t=table, cols=datetime_columns, row=default_row: TableTools.add_row(t, cols, row))
            edit_btn.clicked.connect(lambda _, t=table, cols=datetime_columns: TableTools.edit_row(t, self, cols))
            del_btn.clicked.connect(lambda _, t=table: TableTools.delete_row(t, self))

    def new_scheme(self):
        self._init_default_tables()
        self._setup_datetime_cells()
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
        self._write_cards(self.current_scheme_dir)
        output_dir = APP_DIR / "output"
        self._run_task(
            "正在使用 new 内置 Python 后端进行定轨计算...",
            lambda: orbit_backend.run_direct_orbit_determination(self.ui, self.current_scheme_dir, output_dir).summary,
        )

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
        if UseFortran is not None:
            try:
                UseFortran.terminate_genobs_process()
            except Exception:
                pass
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
        self.threads.clear()
        self._log("已请求停止后台任务。")

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
            (self.ui.tableWidget_6, [5, 6]),
            (self.ui.tableWidget_7, [5, 6]),
            (self.ui.tableWidget_8, [1, 2]),
            (self.ui.tableWidget_17, [5, 6]),
        ]:
            for row in range(table.rowCount()):
                for col in columns:
                    if table.cellWidget(row, col) is None:
                        card_io.set_datetime_cell(table, row, col)
            TableTools.apply_font(table)

    def _log(self, message: str):
        self.ui.textEdit.setPlainText(message)
        self.ui.statusbar.showMessage(message.splitlines()[0] if message else "")

    def show_about(self):
        QMessageBox.information(
            self,
            "关于",
            "小天体测地学参数探测平台\n"
            "新界面适配版：支持 GCP/LCP/SimCP/StaCP 卡片读写、观测值配置、定轨程序调用和可视化分析。\n\n"
            "BUG 修复记录：\n"
            "1. 优化 SimCP 导入，兼容 SimuSat/SimuSta/SimuTyp 旧格式模拟观测值卡片。\n"
            "2. 优化 StaCP 导入，支持 STAPOS 中相邻负号坐标值的自动拆分读取。",
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
