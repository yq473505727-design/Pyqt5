from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import chardet
except Exception:  # pragma: no cover - optional dependency
    chardet = None

from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtWidgets import QDateTimeEdit, QTableWidget, QTableWidgetItem


RUNMODE_TO_CODE = {
    "轨道预报": "0",
    "仿真观测值": "2",
    "定位归算": "4",
    "着陆器定位": "5",
    "精密定轨": "6",
    "星历解算": "8",
}
CODE_TO_RUNMODE = {v: k for k, v in RUNMODE_TO_CODE.items()}

INTEGCENT_TO_CODE = {
    "阿波菲斯": "999",
    "地球": "399",
    "太阳": "10",
    "月球": "301",
}
CODE_TO_INTEGCENT = {v: k for k, v in INTEGCENT_TO_CODE.items()}

FILETYPE_TO_CODE = {"PDS": "1", "GEODYN": "2", "GFZ": "3"}
CODE_TO_FILETYPE = {v: k for k, v in FILETYPE_TO_CODE.items()}

DE_TO_CODE = {"DE405": "405", "DE421": "421", "DE430": "430"}
CODE_TO_DE = {v: k for k, v in DE_TO_CODE.items()}

SR_MODEL_TO_CODE = {"锥心地月影模型": "1", "柱形光压模型": "2"}
CODE_TO_SR_MODEL = {v: k for k, v in SR_MODEL_TO_CODE.items()}

TROPO_TO_CODE = {"hopfiled": "1", "GMF": "2", "VMF1": "3"}
CODE_TO_TROPO = {v: k for k, v in TROPO_TO_CODE.items()}


PLANETS = [
    ("Mercury", 1, "ForceCent_2", "lineEdit"),
    ("Venus", 2, "ForceCent_3", "lineEdit_3"),
    ("Earth", 399, "ForceCent_4", "lineEdit_5"),
    ("Mars", 4, "ForceCent_5", "lineEdit_7"),
    ("Jupiter", 5, "ForceCent_6", "lineEdit_9"),
    ("Saturn", 6, "ForceCent_7", "lineEdit_11"),
    ("Uranus", 7, "ForceCent_8", "lineEdit_13"),
    ("Neptune", 8, "ForceCent_9", "lineEdit_15"),
    ("Pluto", 9, "ForceCent_10", "lineEdit_17"),
    ("Lunar", 301, "ForceCent_11", "lineEdit_19"),
    ("Sun", 10, "ForceCent_12", "lineEdit_21"),
]

#_read_text 支持自动识别编码，并兼容 utf-8、gbk、gb18030，降低中文卡片读取乱码风险
def _read_text(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    encodings = []
    if chardet:
        detected = chardet.detect(raw).get("encoding")
        if detected:
            encodings.append(detected)
    encodings.extend(["utf-8", "gbk", "gb18030"])
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

#_clean_lines 会忽略空行和以 # 开头的说明行，使控制卡片可以保留可读注释
def _clean_lines(path: str | Path) -> List[str]:
    lines = []
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "!" in line:
            line = line.split("!", 1)[0].strip()
        if line:
            lines.append(line[:240])
    return lines


def _numeric_values(text: str) -> List[str]:
    return re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[dDeE][+-]?\d+)?", text)


def _write_lines(path: str | Path, lines: Iterable[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _combo_code(combo, mapping, default="0") -> str:
    return mapping.get(combo.currentText(), default)


def _set_combo(combo, text: str) -> None:
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _item_text(table: QTableWidget, row: int, col: int, default: str = "") -> str:
    item = table.item(row, col)
    return item.text().strip() if item and item.text().strip() else default


def _set_item(table: QTableWidget, row: int, col: int, value: str) -> None:
    while table.rowCount() <= row:
        table.insertRow(table.rowCount())
    while table.columnCount() <= col:
        table.insertColumn(table.columnCount())
    item = QTableWidgetItem(str(value))
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.setItem(row, col, item)


def parse_datetime(value: str) -> QDateTime:
    value = value.strip()
    if not value:
        return QDateTime.currentDateTime()
    formats = [
        "yyyy-MM-ddTHH:mm:ss.zzz",
        "yyyy-MM-dd HH:mm:ss.zzz",
        "yyyy-MM-ddTHH:mm:ss",
        "yyyy-MM-dd HH:mm:ss",
        "yyyyMMddHHmmss.zzz",
        "yyyyMMddHHmmss",
    ]
    normalized = re.sub(r"(\.\d{3})\d+", r"\1", value)
    for fmt in formats:
        dt = QDateTime.fromString(normalized, fmt)
        if dt.isValid():
            return dt
    return QDateTime.currentDateTime()


def set_datetime_cell(table: QTableWidget, row: int, col: int, value: Optional[str] = None) -> None:
    editor = QDateTimeEdit()
    editor.setCalendarPopup(True)
    editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zzz")
    editor.setDateTime(parse_datetime(value or ""))
    table.setCellWidget(row, col, editor)


def datetime_cell(table: QTableWidget, row: int, col: int, fmt: str) -> str:
    widget = table.cellWidget(row, col)
    if isinstance(widget, QDateTimeEdit):
        return widget.dateTime().toString(fmt)
    text = _item_text(table, row, col)
    return parse_datetime(text).toString(fmt) if text else ""


def _comment_header(kind: str) -> List[str]:
    return [
        f"# 说明：本文件由小天体测地学参数探测平台生成，类型：{kind}",
        "# 以 # 开头的行为注释行，程序读取时会忽略。",
        "# 属性名后为对应参数值。",
        "#   0         1         2         3         4         5         6         7",
        "#23456789+123456789+123456789+123456789+123456789+123456789+123456789+123456789+",
    ]


def save_gcp(ui, save_path: str | Path) -> None:
    lines = _comment_header("GCP 全局参数卡片")
    lines.append(f"RunMode   {_combo_code(ui.Runmode, RUNMODE_TO_CODE, '6')}    0")
    lines.append(f"Integcent {_combo_code(ui.Runmode_2, INTEGCENT_TO_CODE, '999')}   SUN.GRAV")
    lines.append(f"ForceCent {int(ui.ForceCent.isChecked())}         {_combo_code(ui.comboBox, FILETYPE_TO_CODE, '1')}")
    lines.append(f"ForceNS   {ui.spinBox.value()}")
    lines.append(f"SolveNS   {ui.spinBox_2.value()}")
    lines.append(f"ForceNB   1         {_combo_code(ui.comboBox_2, DE_TO_CODE, '405')}")
    lines.append("SForceNB")
    for name, body_id, checkbox_name, gm_edit_name in PLANETS:
        gm = getattr(ui, gm_edit_name).text().strip()
        selected = int(getattr(ui, checkbox_name).isChecked())
        lines.append(f"{name:<12}{body_id:<12}{gm:<30}{selected}")
    lines.append("EForceNB")
    lines.append("#")
    lines.append(f"ForceRL   {int(ui.ForceCent_12.isChecked())}")
    lines.append(f"ForceSR   {int(ui.ForceCent_13.isChecked())}         {_combo_code(ui.comboBox_3, SR_MODEL_TO_CODE, '2')}")
    lines.append(f"ForceST   {int(ui.ForceCent_14.isChecked())}")
    lines.append(f"K2LOVE              {ui.lineEdit_23.text().strip():<20}        {ui.lineEdit_24.text().strip()}")
    lines.append(f"TropoCorr {int(ui.ForceCent_15.isChecked())}         {_combo_code(ui.comboBox_4, TROPO_TO_CODE, '1')}")
    _write_lines(save_path, lines)


def read_gcp(path: str | Path, ui) -> None:
    lines = _clean_lines(path)
    i = 0
    while i < len(lines):
        line = lines[i]
        parts = line.split()
        if not parts:
            i += 1
            continue
        key = parts[0]
        if key == "RunMode" and len(parts) > 1:
            _set_combo(ui.Runmode, CODE_TO_RUNMODE.get(parts[1], ui.Runmode.currentText()))
        elif key == "Integcent" and len(parts) > 1:
            _set_combo(ui.Runmode_2, CODE_TO_INTEGCENT.get(parts[1], ui.Runmode_2.currentText()))
        elif key == "ForceCent":
            if len(parts) > 1:
                ui.ForceCent.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.comboBox, CODE_TO_FILETYPE.get(parts[2], ui.comboBox.currentText()))
        elif key == "ForceNS" and len(parts) > 1:
            ui.spinBox.setValue(int(float(parts[1])))
        elif key == "SolveNS" and len(parts) > 1:
            ui.spinBox_2.setValue(int(float(parts[1])))
        elif key == "ForceNB" and len(parts) > 2:
            _set_combo(ui.comboBox_2, CODE_TO_DE.get(parts[2], ui.comboBox_2.currentText()))
        elif key == "SForceNB":
            i += 1
            by_name = {name: (checkbox, gm_edit) for name, _, checkbox, gm_edit in PLANETS}
            while i < len(lines) and not lines[i].startswith("EForceNB"):
                p = lines[i].split()
                if p and p[0] in by_name:
                    checkbox_name, gm_edit_name = by_name[p[0]]
                    if len(p) > 2:
                        getattr(ui, gm_edit_name).setText(p[2])
                    if len(p) > 3:
                        getattr(ui, checkbox_name).setChecked(p[3] == "1")
                i += 1
        elif key == "ForceRL" and len(parts) > 1:
            ui.ForceCent_12.setChecked(parts[1] == "1")
        elif key == "ForceSR":
            if len(parts) > 1:
                ui.ForceCent_13.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.comboBox_3, CODE_TO_SR_MODEL.get(parts[2], ui.comboBox_3.currentText()))
        elif key == "ForceST" and len(parts) > 1:
            ui.ForceCent_14.setChecked(parts[1] == "1")
        elif key == "K2LOVE":
            if len(parts) > 1:
                ui.lineEdit_23.setText(parts[1])
            if len(parts) > 2:
                ui.lineEdit_24.setText(parts[2])
        elif key == "TropoCorr":
            if len(parts) > 1:
                ui.ForceCent_15.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.comboBox_4, CODE_TO_TROPO.get(parts[2], ui.comboBox_4.currentText()))
        i += 1


def save_lcp(ui, save_path: str | Path) -> None:
    lines = _comment_header("LCP 弧段参数卡片")
    lines.append("RefSys    1")
    lines.append(f"SatID      {ui.lineEdit_25.text().strip()}")
    lines.append(f"SatMsAr    {ui.lineEdit_27.text().strip() or '0'}         {ui.lineEdit_29.text().strip() or '0'}")
    lines.append(f"SatPanel   {ui.lineEdit_28.text().strip() or '0'}")
    lines.append(f"SatSoCr    {ui.lineEdit_30.text().strip() or '0'}         {ui.lineEdit_31.text().strip() or '0'}        1    0.0   2")
    lines.append("SatThef    1.00D0              0.00D0        0  0.0 1")
    lines.append(f"StartTime     {ui.dateTimeEdit.dateTime().toString('yyyy-MM-ddTHH:mm:ss.zzz')}")
    lines.append(f"EndTime       {ui.dateTimeEdit_2.dateTime().toString('yyyy-MM-ddTHH:mm:ss.zzz')}")
    if ui.comboBox_5.currentText() == "开普勒轨道根数":
        lines.append(f"OrbRootP1    {ui.lineEdit_32.text().strip() or '0 0 0'}")
        lines.append(f"OrbRootV1    {ui.lineEdit_33.text().strip() or '0 0 0'}")
    else:
        lines.append(f"OrbRootP0    {ui.lineEdit_32.text().strip() or '0 0 0'}")
        lines.append(f"OrbRootV0    {ui.lineEdit_33.text().strip() or '0 0 0'}")
    lines.append(f"OrbVARCOV1  {ui.lineEdit_34.text().strip() or '0 0 0'}")
    lines.append(f"OrbVARCOV2  {ui.lineEdit_35.text().strip() or '0 0 0'}")
    lines.extend(["OrbP0Bias  0.0 0.0 0.0", "OrbV0Bias  0.0 0.0 0.0", "OrbitFile  0", "DopModel   1"])
    lines.append(f"DopWindow    {ui.lineEdit_36.text().strip() or '0'}")
    lines.append(f"DopInvTime   {ui.lineEdit_37.text().strip() or '1d0'}")
    lines.append("MoyerLT    Sun Saturn Jupiter")
    lines.append(f"IntegStep  {ui.lineEdit_38.text().strip() or '60.000'}")
    lines.append(f"PrintStep  {ui.lineEdit_39.text().strip() or '60.000'}")
    lines.append("ChebOrder     11")
    lines.append("ChooseInt     2   1d-14   1d-18" if ui.comboBox_6.currentText() == "Adams12" else "ChooseInt     1   1d-14   1d-18")
    lines.extend(["DopBias    0.00d0      0.00d0          0  0.0", "AstEphSnd  0.0", "AstEphErr  0  0.0"])
    lines.append("Lutetia    5.0196D-11    0.0d0      2  0.0  2469219")
    lines.append("Reject    1")
    lines.extend(["DataEdit   51 3000 300", "DataEdit   52 3000 300", "DataEdit   53 3000 300"])
    lines.append(f"ParDeriv  {ui.lineEdit_40.text().strip() or '0.05'}")
    lines.append(f"orbDeriv   {ui.lineEdit_41.text().strip() or '1D-3'}   {ui.lineEdit_42.text().strip() or '1D-6'}")
    lines.extend(["OD_TyNum   51 2", "OD_TyNum   52 2", "OD_TyNum   53 1", "OD_TyNum   54 0", "OD_TyNum   59 0"])
    lines.append(f"InputFilt  {ui.comboBox_7.currentIndex()}")

    for row in _nonempty_rows(ui.tableWidget_2):
        lines.append(f"SIGMA     {_item_text(ui.tableWidget_2, row, 0)} {_item_text(ui.tableWidget_2, row, 1)} {_item_text(ui.tableWidget_2, row, 2)}")
    for row in _nonempty_rows(ui.tableWidget_4):
        lines.append(f"PBIAS     {_item_text(ui.tableWidget_4, row, 0)} {_item_text(ui.tableWidget_4, row, 1)} {_item_text(ui.tableWidget_4, row, 2)}")
    for row in _nonempty_rows(ui.tableWidget_5):
        lines.append(
            "ObsBias   "
            f"{_item_text(ui.tableWidget_5, row, 0)} {_item_text(ui.tableWidget_5, row, 1)} "
            f"{_item_text(ui.tableWidget_5, row, 2)} {_item_text(ui.tableWidget_5, row, 3)} "
            f"{datetime_cell(ui.tableWidget_5, row, 4, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.tableWidget_5, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{_item_text(ui.tableWidget_5, row, 6)}"
        )
    for row in _nonempty_rows(ui.tableWidget_6):
        lines.append(
            "SelectObs "
            f"{_item_text(ui.tableWidget_6, row, 0)} {_item_text(ui.tableWidget_6, row, 1)} "
            f"{_item_text(ui.tableWidget_6, row, 2)} {_item_text(ui.tableWidget_6, row, 3, '0000000')} "
            f"{_item_text(ui.tableWidget_6, row, 4, '0000000')} "
            f"{datetime_cell(ui.tableWidget_6, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.tableWidget_6, row, 6, 'yyyyMMddHHmmss.zzz')}"
        )
    for row in _nonempty_rows(ui.tableWidget_7):
        lines.append(
            "Discard   "
            f"{_item_text(ui.tableWidget_7, row, 0)} {_item_text(ui.tableWidget_7, row, 1)} "
            f"{_item_text(ui.tableWidget_7, row, 2)} {_item_text(ui.tableWidget_7, row, 3, '0000000')} "
            f"{_item_text(ui.tableWidget_7, row, 4, '0000000')} "
            f"{datetime_cell(ui.tableWidget_7, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.tableWidget_7, row, 6, 'yyyyMMddHHmmss.zzz')}"
        )
    lines.append(f"PerAccNum   {ui.spinBox_3.value()} {ui.comboBox_8.currentIndex()}")
    for row in _nonempty_rows(ui.tableWidget_8):
        lines.append(
            "PerAccinf   "
            f"{_item_text(ui.tableWidget_8, row, 0)} "
            f"{datetime_cell(ui.tableWidget_8, row, 1, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.tableWidget_8, row, 2, 'yyyyMMddHHmmss.zzz')} "
            f"{_item_text(ui.tableWidget_8, row, 3, 'TDB')}"
        )
    for row in _nonempty_rows(ui.tableWidget_16):
        lines.append(
            "PerAcc    "
            f"{_item_text(ui.tableWidget_16, row, 0)} {_item_text(ui.tableWidget_16, row, 1)} "
            f"{_item_text(ui.tableWidget_16, row, 2)} {_item_text(ui.tableWidget_16, row, 3)}"
        )

    kernel_root = ui.lineEdit_44.text().strip()
    lines.append(f"StaBaKer   {kernel_root}")
    lines.extend([
        "lsk:NAIF0012.TLS.pc",
        "spk:de430.bsp",
        "spk:jup329.bsp",
        "spk:ceres_1900_2100.bsp",
        "spk:pallas_1900_2100.bsp",
        "spk:vesta_1900_2100.bsp",
        "pck:gm_de431_xg.tpc",
        "pck:pck00010_xg.tpc",
        "fk:KS_BDAO_JMS.tf",
        "fk:EARTHFIXEDITRF93.TF",
        "pck:earth_070425_370426_predict.bpc",
        "spk:KS_BDAO_JMS.bsp",
        "EndBaKer",
        f"StaSpeKer  {kernel_root}",
        "spk:2469219_20220101_20330101.bsp",
        "fk:2016HO3.tf",
        "pck:2016HO3.TPC",
        "EndSpeKer",
    ])
    _write_lines(save_path, lines)


def read_lcp(path: str | Path, ui) -> None:
    for line in _clean_lines(path):
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        values = parts[1:]
        value_text = " ".join(values)
        if key == "SatID" and values:
            ui.lineEdit_25.setText(values[0])
        elif key == "SatMsAr":
            if len(values) > 0:
                ui.lineEdit_27.setText(values[0])
            if len(values) > 1:
                ui.lineEdit_29.setText(values[1])
        elif key == "SatPanel" and values:
            ui.lineEdit_28.setText(values[0])
        elif key == "SatSoCr":
            if len(values) > 0:
                ui.lineEdit_30.setText(values[0])
            if len(values) > 1:
                ui.lineEdit_31.setText(values[1])
        elif key == "StartTime":
            ui.dateTimeEdit.setDateTime(parse_datetime(value_text))
        elif key == "EndTime":
            ui.dateTimeEdit_2.setDateTime(parse_datetime(value_text))
        elif key in ("OrbRootP0", "OrbRootP1"):
            _set_combo(ui.comboBox_5, "开普勒轨道根数" if key.endswith("1") else "直角坐标系")
            ui.lineEdit_32.setText(value_text)
        elif key in ("OrbRootV0", "OrbRootV1"):
            ui.lineEdit_33.setText(value_text)
        elif key == "OrbVARCOV1":
            ui.lineEdit_34.setText(value_text)
        elif key == "OrbVARCOV2":
            ui.lineEdit_35.setText(value_text)
        elif key == "DopWindow" and values:
            ui.lineEdit_36.setText(values[0])
        elif key == "DopInvTime" and values:
            ui.lineEdit_37.setText(values[0])
        elif key == "IntegStep" and values:
            ui.lineEdit_38.setText(values[0])
        elif key == "PrintStep" and values:
            ui.lineEdit_39.setText(values[0])
        elif key == "ChooseInt" and values:
            _set_combo(ui.comboBox_6, "Adams12" if values[0] == "2" else "ode")
        elif key == "ParDeriv" and values:
            ui.lineEdit_40.setText(values[0])
        elif key.lower() == "orbderiv":
            if len(values) > 0:
                ui.lineEdit_41.setText(values[0])
            if len(values) > 1:
                ui.lineEdit_42.setText(values[1])
        elif key == "InputFilt" and values:
            idx = int(float(values[0]))
            if 0 <= idx < ui.comboBox_7.count():
                ui.comboBox_7.setCurrentIndex(idx)
        elif key == "SIGMA":
            _append_plain_row(ui.tableWidget_2, values[:3])
        elif key == "PBIAS":
            _append_plain_row(ui.tableWidget_4, values[:3])
        elif key == "ObsBias":
            row = _append_plain_row(ui.tableWidget_5, values[:4] + ["", "", values[6] if len(values) > 6 else ""])
            if len(values) > 4:
                set_datetime_cell(ui.tableWidget_5, row, 4, values[4])
            if len(values) > 5:
                set_datetime_cell(ui.tableWidget_5, row, 5, values[5])
        elif key == "SelectObs":
            row = _append_plain_row(ui.tableWidget_6, values[:5])
            if len(values) > 5:
                set_datetime_cell(ui.tableWidget_6, row, 5, values[5])
            if len(values) > 6:
                set_datetime_cell(ui.tableWidget_6, row, 6, values[6])
        elif key == "Discard":
            row = _append_plain_row(ui.tableWidget_7, values[:5])
            if len(values) > 5:
                set_datetime_cell(ui.tableWidget_7, row, 5, values[5])
            if len(values) > 6:
                set_datetime_cell(ui.tableWidget_7, row, 6, values[6])
        elif key == "PerAccNum":
            if values:
                ui.spinBox_3.setValue(int(float(values[0])))
            if len(values) > 1 and int(float(values[1])) < ui.comboBox_8.count():
                ui.comboBox_8.setCurrentIndex(int(float(values[1])))
        elif key == "PerAccinf":
            row = _append_plain_row(ui.tableWidget_8, [values[0] if values else "", "", "", values[3] if len(values) > 3 else "TDB"])
            if len(values) > 1:
                set_datetime_cell(ui.tableWidget_8, row, 1, values[1])
            if len(values) > 2:
                set_datetime_cell(ui.tableWidget_8, row, 2, values[2])
        elif key == "PerAcc":
            _append_plain_row(ui.tableWidget_16, values[:4])
        elif key == "StaBaKer":
            ui.lineEdit_44.setText(value_text)


def save_simcp(ui, save_path: str | Path) -> None:
    table = ui.tableWidget_17
    rows = list(_nonempty_rows(table))
    counts = {"51": 0, "52": 0, "53": 0}
    for row in rows:
        obs_type = _item_text(table, row, 7)
        if obs_type in counts:
            counts[obs_type] += 1

    lines = _comment_header("SimCP 模拟观测卡片")
    lines.append("Simu      1")
    for obs_type in ["51", "52", "53"]:
        lines.append(f"SimuTyNum  {obs_type}    {counts[obs_type]}")
    lines.extend(["####################################################", "StartSimu"])

    previous_type = None
    for idx, row in enumerate(rows):
        obs_type = _item_text(table, row, 7, "51")
        if obs_type != previous_type:
            if previous_type is not None:
                lines.append("EndCnfg")
            lines.append(f"SimuTyp   {obs_type}")
            previous_type = obs_type
        lines.append("####")
        lines.append(f"SimuSat   {_item_text(table, row, 0, '-999')}")
        if obs_type != "53":
            lines.append(f"SimuSta   {_item_text(table, row, 2, '0')}   {_item_text(table, row, 3, '0')}   7168883696.000000")
            lines.extend([
                "ELCUTOFF  20.0  20.0",
                "CigBodyID  10",
                "SiTStaTPH  305.690000000000 931.013333333333 11.9082978629104",
                "SiRStaTPH  305.690000000000 931.013333333333 11.9082978629104",
            ])
        lines.append(f"SimuLim   {_item_text(table, row, 9, '30.000')}")
        noise = _item_text(table, row, 8, "0.00d0")
        suffix = "     1     1" if obs_type == "52" else "     1"
        lines.append(f"SimuNoi   {noise}         0.00d0{suffix}")
        lines.append(
            "SimSelect   "
            f"{datetime_cell(table, row, 5, 'yyyy-MM-ddTHH:mm:ss.zzz')}      "
            f"{datetime_cell(table, row, 6, 'yyyy-MM-ddTHH:mm:ss.zzz')}"
        )
    lines.extend(["#####", "EndCnfg", "###############################", "EndSimu"])
    _write_lines(save_path, lines)


def read_simcp(path: str | Path, ui) -> None:
    table = ui.tableWidget_17
    table.setRowCount(0)
    current_type = ""
    global_interval = ""
    current = {}

    def append_current():
        nonlocal current
        if not current.get("sat1") and not current.get("obs_type"):
            current = {}
            return
        row = table.rowCount()
        table.insertRow(row)
        values = [
            current.get("sat1", ""),
            current.get("sat2", ""),
            current.get("down", ""),
            current.get("up", ""),
            current.get("backup", ""),
            "",
            "",
            current.get("obs_type", current_type),
            current.get("noise", ""),
            current.get("interval", global_interval),
        ]
        for col, value in enumerate(values):
            if col not in (5, 6):
                _set_item(table, row, col, value)
        if current.get("start"):
            set_datetime_cell(table, row, 5, current.get("start"))
        if current.get("end"):
            set_datetime_cell(table, row, 6, current.get("end"))
        current = {}

    for line in _clean_lines(path):
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        if key == "SimuLim" and len(parts) > 1:
            if current:
                current["interval"] = parts[1]
            else:
                global_interval = parts[1]
        elif key == "SimuTyp" and len(parts) > 1:
            if current:
                current["obs_type"] = parts[1]
                if len(parts) > 2:
                    current["noise"] = parts[2]
                append_current()
            else:
                current_type = parts[1]
        elif key == "SimuSat":
            current = {"obs_type": current_type, "sat1": parts[1] if len(parts) > 1 else ""}
        elif key == "SimuSta":
            current["down"] = parts[1] if len(parts) > 1 else ""
            current["up"] = parts[2] if len(parts) > 2 else ""
        elif key == "SimuTim":
            if len(parts) > 1:
                current["start"] = parts[1]
            if len(parts) > 2:
                current["end"] = parts[2]
        elif key == "SimuNoi":
            current["noise"] = parts[1] if len(parts) > 1 else ""
        elif key == "SimSelect":
            current["start"] = parts[1] if len(parts) > 1 else ""
            current["end"] = parts[2] if len(parts) > 2 else ""
            append_current()
        elif key == "EndCnfg":
            append_current()


def save_stacp(ui, save_path: str | Path) -> None:
    table = ui.tableWidget_26
    rows = list(_nonempty_rows(table))
    lines = _comment_header("StaCP 测站参数卡片")
    lines.append(f"STATION {len(rows)}")
    lines.append(f"ELCUTOFF {ui.lineEdit_88.text().strip() or '15.0'}")
    lines.append(f"GEODETIC {ui.lineEdit_89.text().strip() or '6378137.000'} {ui.lineEdit_90.text().strip() or '298.257223563'}")
    lines.extend(["FIXED", ""])
    for row in rows:
        station_id = _item_text(table, row, 0)
        name = _item_text(table, row, 1)
        active = _item_text(table, row, 2, "1")
        cutoff = _item_text(table, row, 3, ui.lineEdit_88.text().strip() or "15.0")
        planet = _item_text(table, row, 10, "0")
        lines.append(f"STAIDNAME {station_id} {name} {cutoff} {active} {planet}")
        lines.append(f"STAPOS {_item_text(table, row, 4)} {_item_text(table, row, 5)} {_item_text(table, row, 6)} 1")
        vel = [_item_text(table, row, 7), _item_text(table, row, 8), _item_text(table, row, 9)]
        if any(vel):
            lines.append(f"STAVEL {vel[0]} {vel[1]} {vel[2]}")
        lines.extend(["ENDSTA", ""])
    lines.append("ENDALLSTA")
    _write_lines(save_path, lines)


def read_stacp(path: str | Path, ui) -> None:
    table = ui.tableWidget_26
    table.setRowCount(0)
    row = -1
    for line in _clean_lines(path):
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        values = parts[1:]
        if key == "STATION" and values:
            ui.spinBox_7.setValue(int(float(values[0])))
        elif key == "ELCUTOFF" and values:
            ui.lineEdit_88.setText(values[0])
        elif key == "GEODETIC":
            if len(values) > 0:
                ui.lineEdit_89.setText(values[0])
            if len(values) > 1:
                ui.lineEdit_90.setText(values[1])
        elif key == "STAIDNAME":
            row += 1
            table.insertRow(row)
            mapped = [
                values[0] if len(values) > 0 else "",
                values[1] if len(values) > 1 else "",
                values[3] if len(values) > 3 else "1",
                values[2] if len(values) > 2 else "",
                "",
                "",
                "",
                "",
                "",
                "",
                values[4] if len(values) > 4 else "0",
            ]
            for col, value in enumerate(mapped):
                _set_item(table, row, col, value)
        elif key == "STAPOS" and row >= 0:
            position_values = _numeric_values(line[len(key):])
            for col, value in enumerate(position_values[:3], start=4):
                _set_item(table, row, col, value)
        elif key == "STAVEL" and row >= 0:
            velocity_values = _numeric_values(line[len(key):])
            for col, value in enumerate(velocity_values[:3], start=7):
                _set_item(table, row, col, value)


def _nonempty_rows(table: QTableWidget):
    for row in range(table.rowCount()):
        if any(_item_text(table, row, col) for col in range(table.columnCount())):
            yield row


def _append_plain_row(table: QTableWidget, values: List[str]) -> int:
    if table.rowCount() == 1 and not any(_item_text(table, 0, col) for col in range(table.columnCount())):
        row = 0
    else:
        row = table.rowCount()
        table.insertRow(row)
    for col, value in enumerate(values[: table.columnCount()]):
        _set_item(table, row, col, value)
    return row
