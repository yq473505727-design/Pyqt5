from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    import chardet
except Exception:  # pragma: no cover - optional dependency
    chardet = None

from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtWidgets import QComboBox, QDateTimeEdit, QTableWidget, QTableWidgetItem


RUNMODE_TO_CODE = {
    "轨道预报": "1",
    "仿真观测值": "2",
    # "定位归算": "4",
    # "着陆器定位": "5",
    "精密定轨": "4",
    # "星历解算": "8",
}
CODE_TO_RUNMODE = {v: k for k, v in RUNMODE_TO_CODE.items()}
CODE_TO_RUNMODE.update({
    "0": "轨道预报",
    "6": "精密定轨",
})

INTEGCENT_TO_CODE = {
    "阿波菲斯": "999",
    "地球": "0",
    "月球": "10",
    "火星": "2",
    # Legacy labels/codes kept so older cards can still be imported.
    "太阳": "10",
}
CODE_TO_INTEGCENT = {v: k for k, v in INTEGCENT_TO_CODE.items()}
CODE_TO_INTEGCENT.update({"0": "地球", "10": "月球", "2": "火星", "399": "地球", "301": "月球"})

FILETYPE_TO_CODE = {"PDS": "1", "GEODYN": "2", "GFZ": "3"}
CODE_TO_FILETYPE = {v: k for k, v in FILETYPE_TO_CODE.items()}

DE_TO_CODE = {"DE405": "405", "DE421": "421", "DE430": "430", "DE440": "440"}
CODE_TO_DE = {v: k for k, v in DE_TO_CODE.items()}

SR_MODEL_TO_CODE = {"锥心地月影模型": "1", "柱形光压模型": "2"}
CODE_TO_SR_MODEL = {v: k for k, v in SR_MODEL_TO_CODE.items()}

TROPO_TO_CODE = {"hopfiled": "1", "GMF": "2", "VMF1": "3"}
CODE_TO_TROPO = {v: k for k, v in TROPO_TO_CODE.items()}

INTEGRATOR_TO_CODE = {"ode": "1", "Adams12": "2"}
CODE_TO_INTEGRATOR = {v: k for k, v in INTEGRATOR_TO_CODE.items()}

OBSERVATION_TYPE_INFO = {
    "51": ("双程测距", "meter"),
    "52": ("双程测速", "mm/s"),
    "59": ("VLBI 时延", "ns"),
    "60": ("VLBI 时延率", "ps/s"),
}
SELECT_OBSERVATION_TYPE_INFO = {
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
PER_ACC_DIRECTION_INFO = {
    "1": "沿飞行方向（T）",
    "2": "沿轨道法向方向（N）",
    "3": "沿轨道半径方向（R）",
}
PER_ACC_MODEL_INFO = {
    "1": "使用 cos 函数拟合",
    "2": "使用 sin 函数拟合",
    "3": "使用常数拟合",
}
STATION_STATUS_INFO = {
    "1": "激活",
    "0": "未激活",
}
STATION_COORD_TYPE_INFO = {
    "0": "直角坐标系XYZ",
    "1": "大地坐标BLH",
}
STATION_BODY_INFO = {
    "0": "地球测站",
    "1": "月球测站",
}


PLANETS = [
    ("Mercury", 1, "check_third_body_mercury", "edit_mercury_gm"),
    ("Venus", 2, "check_third_body_venus", "edit_venus_gm"),
    ("Earth", 399, "check_third_body_earth", "edit_earth_gm"),
    ("Mars", 4, "check_third_body_mars", "edit_mars_gm"),
    ("Jupiter", 5, "check_third_body_jupiter", "edit_jupiter_gm"),
    ("Uranus", 7, "check_third_body_uranus", "edit_uranus_gm"),
    ("Neptune", 8, "check_third_body_neptune", "edit_neptune_gm"),
    ("Pluto", 9, "check_third_body_pluto", "edit_pluto_gm"),
    ("Lunar", 301, "check_third_body_moon", "edit_moon_gm"),
    ("Sun", 10, "check_third_body_sun", "edit_sun_gm"),
]

PLANET_CARD_ROWS = [
    ("Mercury", "check_third_body_mercury", "edit_mercury_gm", "edit_mercury_radius"),
    ("Venus", "check_third_body_venus", "edit_venus_gm", "edit_venus_radius"),
    ("Earth", "check_third_body_earth", "edit_earth_gm", "edit_earth_radius"),
    ("Mars", "check_third_body_mars", "edit_mars_gm", "edit_mars_radius"),
    ("Jupiter", "check_third_body_jupiter", "edit_jupiter_gm", "edit_jupiter_radius"),
    ("Saturn", None, "edit_saturn_gm", "edit_saturn_radius"),
    ("Uranus", "check_third_body_uranus", "edit_uranus_gm", "edit_uranus_radius"),
    ("Neptune", "check_third_body_neptune", "edit_neptune_gm", "edit_neptune_radius"),
    ("Pluto", "check_third_body_pluto", "edit_pluto_gm", "edit_pluto_radius"),
    ("Lunar", "check_third_body_moon", "edit_moon_gm", "edit_moon_radius"),
    ("Sun", "check_third_body_sun", "edit_sun_gm", "edit_sun_radius"),
]

#_read_text 支持自动识别编码，并兼容 utf-8、gbk、gb18030，降低中文卡片读取乱码风险
def _read_text(path: str | Path) -> str:
    """自动识别文本编码读取卡片文件，尽量兼容中文和旧格式文件。"""
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
    """读取卡片文件并过滤空行、整行注释和行尾说明内容。"""
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
    """从任意文本中提取普通或 Fortran 科学计数法形式的数值字符串。"""
    return re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[dDeE][+-]?\d+)?", text)


def _write_lines(path: str | Path, lines: Iterable[str]) -> None:
    """创建目标目录并把卡片行按 UTF-8 文本写入文件。"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _combo_code(combo, mapping, default="0") -> str:
    """从下拉框的 itemData 或显示文本映射得到卡片需要的数字代码。"""
    data = combo.currentData()
    if data is not None:
        return str(data)
    return mapping.get(combo.currentText(), default)


def _step_text(ui, combo_name: str, edit_name: str, default: str = "60") -> str:
    """从步长下拉框或备用输入框读取积分/输出步长文本。"""
    combo = getattr(ui, combo_name, None)
    if combo is not None:
        text = combo.currentText().strip()
        if text:
            return text
    edit = getattr(ui, edit_name)
    return edit.text().strip() or default


def _normalize_step_text(value: str) -> str:
    """规范化步长文本，支持 Fortran D 计数法并去掉无意义小数。"""
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


def _set_step_text(ui, combo_name: str, edit_name: str, value: str) -> None:
    """把卡片中的步长写回输入框和下拉框，并补齐自定义选项。"""
    normalized = _normalize_step_text(value)
    edit = getattr(ui, edit_name)
    edit.setText(normalized)
    combo = getattr(ui, combo_name, None)
    if combo is None:
        return
    if combo.findText(normalized) < 0:
        combo.addItem(normalized)
    combo.setCurrentText(normalized)


def _set_combo(combo, text: str) -> None:
    """按显示文本选择下拉框项，找不到时保持原状态。"""
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _set_combo_by_code(combo, code: str, mapping, default_text: str | None = None) -> None:
    """按数字代码优先选择下拉框项，必要时退回到代码映射文本。"""
    code = str(code)
    for index in range(combo.count()):
        if str(combo.itemData(index)) == code:
            combo.setCurrentIndex(index)
            return
    _set_combo(combo, mapping.get(code, default_text or combo.currentText()))


def _item_text(table: QTableWidget, row: int, col: int, default: str = "") -> str:
    """统一读取表格普通单元格或下拉单元格的文本内容。"""
    widget = table.cellWidget(row, col)
    if isinstance(widget, QComboBox):
        text = widget.currentText().strip()
        return text if text else default
    item = table.item(row, col)
    return item.text().strip() if item and item.text().strip() else default


def _observation_type_code(value: str) -> str:
    """把观测值类型的中文标签或数字文本转换为 SimCP/LCP 使用的代码。"""
    text = str(value or "").strip()
    for code in OBSERVATION_TYPE_INFO:
        if text == code or text.startswith(f"{code}-"):
            return code
    if text.isdigit():
        normalized = str(int(text))
        if normalized in OBSERVATION_TYPE_INFO:
            return normalized
    return text


def _observation_type_label(code: str) -> str:
    """把观测值类型代码转换为“代码-中文解释”的显示文本。"""
    code = str(code or "").strip()
    info = OBSERVATION_TYPE_INFO.get(code)
    return f"{code}-{info[0]}" if info else code


def _observation_type_unit(code: str, default: str = "") -> str:
    """根据观测值类型代码返回对应单位，未知代码使用默认值。"""
    info = OBSERVATION_TYPE_INFO.get(str(code or "").strip())
    return info[1] if info else default


def _select_observation_type_code(value: str) -> str:
    """把选择观测值表中的显示文本转换为 SelectObs 使用的类型代码。"""
    text = str(value or "").strip()
    for code in SELECT_OBSERVATION_TYPE_INFO:
        if text == code or text.startswith(f"{code}-"):
            return code
    if text.isdigit():
        normalized = str(int(text))
        normalized = SELECT_OBSERVATION_TYPE_LEGACY_CODES.get(normalized, normalized)
        if normalized in SELECT_OBSERVATION_TYPE_INFO:
            return normalized
    return text


def _select_observation_type_label(code: str) -> str:
    """把 SelectObs 类型代码转换为“代码-中文解释”的显示文本。"""
    code = str(code or "").strip()
    label = SELECT_OBSERVATION_TYPE_INFO.get(code)
    return f"{code}-{label}" if label else code


def _coded_value(value: str, mapping) -> str:
    """从通用代码映射中把标签、代码或“代码-标签”文本归一为代码。"""
    text = str(value or "").strip()
    for code, label in mapping.items():
        if text == code or text.startswith(f"{code}-"):
            return code
        if text == label:
            return code
    if text.isdigit():
        normalized = str(int(text))
        if normalized in mapping:
            return normalized
    return text


def _coded_label(value: str, mapping) -> str:
    """把通用代码映射值转换为“代码-中文解释”的显示文本。"""
    code = _coded_value(value, mapping)
    label = mapping.get(code)
    return f"{code}-{label}" if label else code


def _plain_coded_label(value: str, mapping, default: str = "") -> str:
    """把通用代码映射值转换为纯中文标签，不带数字前缀。"""
    code = _coded_value(value, mapping)
    return mapping.get(code, default or str(value or "").strip())


def _split_select_satellite_1(value: str) -> Tuple[str, str]:
    """把 SelectObs 中拼接的 Passnumber 和卫星 1 编号拆回两列。"""
    text = str(value or "").strip()
    if not text:
        return "", ""
    if len(text) > 7 and text.isdigit():
        return text[:-7], text[-7:]
    return "", text


def _combine_select_satellite_1(pass_number: str, satellite_1: str) -> str:
    """把 Passnumber 和卫星 1 编号合并为旧卡片要求的字段。"""
    pass_text = re.sub(r"\D", "", str(pass_number or "").strip())
    sat_text = str(satellite_1 or "").strip()
    return f"{pass_text}{sat_text}" if pass_text else sat_text


def _fixed_width_digits(value: str, width: int, default: str) -> str:
    """提取数字并按固定宽度补零，用于生成旧式复合编号。"""
    text = str(value or "").strip()
    digits = re.sub(r"\D", "", text)
    if not digits:
        digits = default
    return digits.zfill(width)[-width:]


def _obs_bias_identifier(obs_type: str, downlink: str, uplink: str) -> str:
    """根据观测类型和上下行位生成 ObsBias 复合标识符。"""
    code = _fixed_width_digits(_observation_type_code(obs_type), 3, "051")
    down = _fixed_width_digits(downlink, 3, "001")
    up = _fixed_width_digits(uplink, 3, "001")
    return f"{code}{down}{up}00000"


def _parse_obs_bias_row(values: List[str]) -> Tuple[List[str], List[str]]:
    """解析新旧两种 ObsBias 行格式，拆出表格列值和起止时间。"""
    if not values:
        return ["", "", "", "", "", "", ""], []

    compact = re.sub(r"\D", "", values[0])
    if len(compact) >= 9:
        obs_code = _observation_type_code(compact[:3])
        downlink = compact[3:6]
        uplink = compact[6:9]
        rest = values[1:]
        row_values = [
            obs_code,
            downlink,
            uplink,
            rest[0] if len(rest) > 0 else "",
            "",
            "",
            rest[3] if len(rest) > 3 else "",
        ]
        return row_values, _row_datetimes(rest, 1)

    obs_code = _observation_type_code(values[0])
    downlink = values[1] if len(values) > 1 else "001"
    uplink = values[2] if len(values) > 2 else downlink
    row_values = [
        obs_code,
        downlink,
        uplink,
        values[3] if len(values) > 3 else "",
        "",
        "",
        values[6] if len(values) > 6 else "",
    ]
    return row_values, _row_datetimes(values, 4)


def _set_item(table: QTableWidget, row: int, col: int, value: str) -> None:
    """确保表格行列存在并写入左对齐的普通文本单元格。"""
    while table.rowCount() <= row:
        table.insertRow(table.rowCount())
    while table.columnCount() <= col:
        table.insertColumn(table.columnCount())
    item = QTableWidgetItem(str(value))
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.setItem(row, col, item)


def _clear_table_rows(*tables: QTableWidget) -> None:
    """清空一个或多个表格的所有数据行。"""
    for table in tables:
        table.setRowCount(0)


def parse_datetime(value: str) -> QDateTime:
    """解析卡片时间字符串，支持紧凑格式、ISO 格式和 Fortran D 后缀。"""
    value = value.strip()
    if not value:
        return QDateTime.currentDateTime()
    normalized = re.sub(r"[dD][+-]?\d+$", "", value)
    normalized = re.sub(r"(\.\d{3})\d+", r"\1", normalized)
    formats = [
        "yyyy-MM-ddTHH:mm:ss.zzz",
        "yyyy-MM-dd HH:mm:ss.zzz",
        "yyyy-MM-ddTHH:mm:ss",
        "yyyy-MM-dd HH:mm:ss",
        "yyyyMMddHHmmss.zzz",
        "yyyyMMddHHmmss",
    ]
    for fmt in formats:
        dt = QDateTime.fromString(normalized, fmt)
        if dt.isValid():
            return dt
    return QDateTime.currentDateTime()


def _is_valid_datetime_text(value: str) -> bool:
    """判断文本是否能按本软件支持的任一卡片时间格式解析。"""
    if not value:
        return False
    normalized = re.sub(r"[dD][+-]?\d+$", "", value.strip())
    normalized = re.sub(r"(\.\d{3})\d+", r"\1", normalized)
    formats = [
        "yyyy-MM-ddTHH:mm:ss.zzz",
        "yyyy-MM-dd HH:mm:ss.zzz",
        "yyyy-MM-ddTHH:mm:ss",
        "yyyy-MM-dd HH:mm:ss",
        "yyyyMMddHHmmss.zzz",
        "yyyyMMddHHmmss",
    ]
    return any(QDateTime.fromString(normalized, fmt).isValid() for fmt in formats)


def _compact_legacy_time(date_part: str, time_part: str = "") -> str:
    """把旧式日期和时间片段压缩为 yyyyMMddHHmmss.zzz 格式。"""
    date_digits = re.sub(r"\D", "", date_part)
    if len(date_digits) != 8:
        return ""
    time_part = time_part.strip()
    if not time_part:
        return ""
    match = re.match(r"^(\d+)(?:\.(\d+))?$", time_part)
    if not match:
        return ""
    whole = match.group(1)[-6:].zfill(6)
    millis = (match.group(2) or "000")[:3].ljust(3, "0")
    return f"{date_digits}{whole}.{millis}"


def _legacy_time_from_chunk(date_part: str, chunk: str) -> str:
    """从旧卡片日期后的松散时间片段中重建紧凑时间字符串。"""
    date_digits = re.sub(r"\D", "", date_part)
    if len(date_digits) != 8:
        return ""
    numbers = re.findall(r"\d+(?:\.\d+)?", chunk)
    if not numbers:
        return ""

    fraction = "000"
    parts = []
    for number in numbers:
        if "." in number:
            whole, decimal = number.split(".", 1)
            parts.append(whole)
            fraction = decimal[:3].ljust(3, "0")
        else:
            parts.append(number)

    if len(parts) >= 3:
        time_digits = f"{parts[0][-2:].zfill(2)}{parts[1][-2:].zfill(2)}{parts[2][-2:].zfill(2)}"
    elif len(parts) == 2:
        if len(parts[0]) <= 2 and len(parts[1]) <= 4:
            time_digits = f"{parts[0][-2:].zfill(2)}{parts[1][-4:].zfill(4)}"
        else:
            time_digits = f"{parts[0][-4:].zfill(4)}{parts[1][-2:].zfill(2)}"
    else:
        time_digits = parts[0][-6:].zfill(6)

    return f"{date_digits}{time_digits}.{fraction}"


def _extract_legacy_datetimes(values: List[str], start_index: int) -> List[str]:
    """从旧格式字段尾部扫描并提取最多两个起止时间。"""
    datetimes: List[str] = []
    tail = " ".join(values[start_index:])
    date_pattern = re.compile(r"(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])")
    matches = list(date_pattern.finditer(tail))
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(tail)
        normalized = _legacy_time_from_chunk(match.group(0), tail[match.end():next_start])
        if normalized and _is_valid_datetime_text(normalized):
            datetimes.append(normalized)
            if len(datetimes) == 2:
                break
    return datetimes


def _row_datetimes(values: List[str], start_index: int) -> List[str]:
    """优先读取标准时间字段，失败时退回旧格式时间扫描。"""
    datetimes: List[str] = []
    for value in values[start_index:]:
        if _is_valid_datetime_text(value):
            datetimes.append(value)
            if len(datetimes) == 2:
                return datetimes
    return _extract_legacy_datetimes(values, start_index)


def set_datetime_cell(table: QTableWidget, row: int, col: int, value: Optional[str] = None) -> None:
    """在表格指定位置放入带日历弹窗的 QDateTimeEdit 时间控件。"""
    editor = QDateTimeEdit()
    editor.setCalendarPopup(True)
    editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss.zzz")
    editor.setDateTime(parse_datetime(value or ""))
    table.setCellWidget(row, col, editor)


def datetime_cell(table: QTableWidget, row: int, col: int, fmt: str) -> str:
    """按指定格式读取表格时间控件或文本单元格中的时间。"""
    widget = table.cellWidget(row, col)
    if isinstance(widget, QDateTimeEdit):
        return widget.dateTime().toString(fmt)
    text = _item_text(table, row, col)
    return parse_datetime(text).toString(fmt) if text else ""


def orbit_prior_values(values: List[str]) -> str:
    """从 OrbVARCOV 行中提取轨道先验误差的三个主要数值。"""
    if len(values) >= 4:
        return " ".join(values[1:4])
    return " ".join(values)


def _comment_header(kind: str) -> List[str]:
    """生成所有控制卡片通用的中文说明头。"""
    return [
        f"# 说明：本文件由轨道确定与预报分系统软件V1.0生成，类型：{kind}",
        "# 以 # 开头的行为注释行，程序读取时会忽略。",
        "# 属性名后为对应参数值。",
        "#   0         1         2         3         4         5         6         7",
        "#23456789+123456789+123456789+123456789+123456789+123456789+123456789+123456789+",
    ]


def _checked_flag(ui, checkbox_name: str | None, default: str = "0") -> str:
    """把复选框状态转换为卡片中的 0/1 标志位。"""
    if not checkbox_name:
        return default
    checkbox = getattr(ui, checkbox_name, None)
    return "1" if checkbox and checkbox.isChecked() else "0"


def _force_nb_mask(ui) -> str:
    """按行星顺序拼接多体引力复选框状态掩码。"""
    return "".join(_checked_flag(ui, checkbox_name) for _, checkbox_name, _, _ in PLANET_CARD_ROWS)


def _compact_card_datetime(table: QTableWidget, row: int, col: int) -> str:
    """读取表格时间并转换为卡片使用的紧凑时间格式。"""
    return datetime_cell(table, row, col, "yyyyMMddHHmmss.zzz")


def _datetime_edit_card_text(editor: QDateTimeEdit) -> str:
    """把独立时间编辑框转换为卡片使用的紧凑时间加 D0 后缀。"""
    return editor.dateTime().toString("yyyyMMddHHmmss.zzz") + "D0"


def _simcp_station_fields(table: QTableWidget, row: int) -> str:
    """组合 SimCP 单行中的下行位、上行位和备用测站字段。"""
    values = [_item_text(table, row, col) for col in (2, 3, 4)]
    values = [value for value in values if value]
    return "   ".join(values) if values else "0"


def save_gcp(ui, save_path: str | Path) -> None:
    """从界面控件收集全局参数并保存为 GCP 控制卡片。"""
    lines = _comment_header("GCP 全局参数卡片")
    lines.append(f"RunMode   {_combo_code(ui.combo_run_mode, RUNMODE_TO_CODE, '4')}      1")
    lines.append(f"Integcent {_combo_code(ui.combo_integration_center, INTEGCENT_TO_CODE, '0')}")
    lines.append(f"ForceCent {int(ui.check_central_gravity_field.isChecked())}         {_combo_code(ui.combo_gravity_file_format, FILETYPE_TO_CODE, '1')}")
    lines.append(f"ForceNS   {ui.spin_gravity_degree.value()}")
    lines.append(f"ForceNB   {_force_nb_mask(ui)}     {_combo_code(ui.combo_ephemeris_model, DE_TO_CODE, '440')}")
    lines.append("#")
    for name, _, gm_edit_name, radius_edit_name in PLANET_CARD_ROWS:
        gm = getattr(ui, gm_edit_name).text().strip()
        radius = getattr(ui, radius_edit_name).text().strip()
        lines.append(f"{name:<12}{gm:<30}{radius}")
    lines.append(f"ForceRL   {int(ui.check_relativity_perturbation.isChecked())}")
    lines.append(f"ForceST   {int(ui.check_solid_tide_perturbation.isChecked())}")
    lines.append("H2LOVE                  0.6090")
    lines.append("L2LOVE                  0.0852")
    lines.append(f"K2LOVE              {ui.edit_solid_tide_k2_love_number.text().strip():<20}        {ui.edit_solid_tide_prior_error.text().strip()}")
    lines.append(f"ForceSR   {int(ui.check_solar_radiation_pressure.isChecked())}         {_combo_code(ui.combo_solar_pressure_model, SR_MODEL_TO_CODE, '2')}")
    lines.append("ForceEJ2  0")
    lines.append("PrintOut  1000000000")
    lines.append(f"TropoCorr {int(ui.check_troposphere_delay.isChecked())}         {_combo_code(ui.combo_troposphere_model, TROPO_TO_CODE, '1')}")
    lines.append("MeaParFil 1         1")
    lines.append("CompG2E   1")
    lines.append(f"IntegType {_combo_code(ui.combo_integrator_type, INTEGRATOR_TO_CODE, '2')}")
    lines.append("PreNut    0")
    _write_lines(save_path, lines)


def read_gcp(path: str | Path, ui) -> None:
    """读取 GCP 全局参数卡片并把运行模式、中心体和力模型写回界面。"""
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
            _set_combo(ui.combo_run_mode, CODE_TO_RUNMODE.get(parts[1], ui.combo_run_mode.currentText()))
        elif key == "Integcent" and len(parts) > 1:
            _set_combo_by_code(ui.combo_integration_center, parts[1], CODE_TO_INTEGCENT)
        elif key in ("ChooseInt", "IntegType") and len(parts) > 1:
            if parts[1] in CODE_TO_INTEGRATOR:
                _set_combo(ui.combo_integrator_type, CODE_TO_INTEGRATOR[parts[1]])
        elif key == "ForceCent":
            if len(parts) > 1:
                ui.check_central_gravity_field.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.combo_gravity_file_format, CODE_TO_FILETYPE.get(parts[2], ui.combo_gravity_file_format.currentText()))
        elif key == "ForceNS" and len(parts) > 1:
            ui.spin_gravity_degree.setValue(int(float(parts[1])))
        elif key == "SolveNS" and len(parts) > 1:
            ui.spin_gravity_inversion_degree.setValue(int(float(parts[1])))
        elif key == "ForceNB":
            if len(parts) > 2:
                _set_combo_by_code(ui.combo_ephemeris_model, parts[2], CODE_TO_DE)
            if len(parts) > 1 and re.fullmatch(r"[01]+", parts[1]):
                mask = parts[1]
                for index, (_, checkbox_name, _, _) in enumerate(PLANET_CARD_ROWS):
                    if checkbox_name and index < len(mask):
                        getattr(ui, checkbox_name).setChecked(mask[index] == "1")
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
            ui.check_relativity_perturbation.setChecked(parts[1] == "1")
        elif key == "ForceSR":
            if len(parts) > 1:
                ui.check_solar_radiation_pressure.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.combo_solar_pressure_model, CODE_TO_SR_MODEL.get(parts[2], ui.combo_solar_pressure_model.currentText()))
        elif key == "ForceST" and len(parts) > 1:
            ui.check_solid_tide_perturbation.setChecked(parts[1] == "1")
        elif key == "K2LOVE":
            if len(parts) > 1:
                ui.edit_solid_tide_k2_love_number.setText(parts[1])
            if len(parts) > 2:
                ui.edit_solid_tide_prior_error.setText(parts[2])
        elif key == "TropoCorr":
            if len(parts) > 1:
                ui.check_troposphere_delay.setChecked(parts[1] == "1")
            if len(parts) > 2:
                _set_combo(ui.combo_troposphere_model, CODE_TO_TROPO.get(parts[2], ui.combo_troposphere_model.currentText()))
        elif key in {name for name, _, _, _ in PLANET_CARD_ROWS}:
            by_name = {name: (gm_edit, radius_edit) for name, _, gm_edit, radius_edit in PLANET_CARD_ROWS}
            gm_edit_name, radius_edit_name = by_name[key]
            if len(parts) > 1:
                getattr(ui, gm_edit_name).setText(parts[1])
            if len(parts) > 2:
                getattr(ui, radius_edit_name).setText(parts[2])
        i += 1


def save_lcp(ui, save_path: str | Path) -> None:
    """从界面控件收集弧段参数、观测权重和解算设置并保存为 LCP。"""
    lines = _comment_header("LCP 弧段参数卡片")
    lines.append("RefSys    1")
    lines.append(f"SatID      {ui.edit_arc_satellite_id.text().strip()}")
    lines.append(f"SatMsAr    {ui.edit_arc_satellite_mass.text().strip() or '0'}         {ui.edit_arc_body_area.text().strip() or '0'}")
    lines.append(f"SatSoCr    {ui.edit_arc_solar_pressure_coefficient.text().strip() or '0'}         {ui.edit_arc_solar_pressure_prior_error.text().strip() or '0'}        1    0.0   2")
    lines.append(f"StartTime {_datetime_edit_card_text(ui.date_arc_start_time)}")
    lines.append(f"EndTime   {_datetime_edit_card_text(ui.date_arc_end_time)}")
    if ui.combo_arc_initial_orbit_type.currentText() == "开普勒轨道根数":
        lines.append(f"OrbRootP1    {ui.edit_arc_initial_position.text().strip() or '0 0 0'}")
        lines.append(f"OrbRootV1    {ui.edit_arc_initial_velocity.text().strip() or '0 0 0'}")
    else:
        lines.append(f"OrbRootP0    {ui.edit_arc_initial_position.text().strip() or '0 0 0'}")
        lines.append(f"OrbRootV0    {ui.edit_arc_initial_velocity.text().strip() or '0 0 0'}")
    lines.append(f"OrbVARCOV1  {ui.edit_arc_position_prior.text().strip() or '0 0 0'}")
    lines.append(f"OrbVARCOV2  {ui.edit_arc_velocity_prior.text().strip() or '0 0 0'}")
    lines.append(f"IntegStep  {_step_text(ui, 'combo_arc_integration_step', 'edit_arc_integration_step_legacy', '60')}")
    lines.append(f"PrintStep  {_step_text(ui, 'combo_arc_output_step', 'edit_arc_output_step_legacy', '60')}")
    lines.append("EPS_DX        100.0")

    for row in _nonempty_rows(ui.table_arc_observation_weight):
        obs_code = _observation_type_code(_item_text(ui.table_arc_observation_weight, row, 0))
        lines.append(f"SIGMA         {obs_code}           {_item_text(ui.table_arc_observation_weight, row, 1)}")
    for row in _nonempty_rows(ui.table_arc_measurement_bias):
        lines.append(f"PBIAS     {_item_text(ui.table_arc_measurement_bias, row, 0)} {_item_text(ui.table_arc_measurement_bias, row, 1)} {_item_text(ui.table_arc_measurement_bias, row, 2)}")
    for row in _nonempty_rows(ui.table_arc_fixed_measurement_bias):
        obs_bias_id = _obs_bias_identifier(
            _item_text(ui.table_arc_fixed_measurement_bias, row, 0),
            _item_text(ui.table_arc_fixed_measurement_bias, row, 1, "001"),
            _item_text(ui.table_arc_fixed_measurement_bias, row, 2, "001"),
        )
        lines.append(
            "ObsBias   "
            f"{obs_bias_id} {_item_text(ui.table_arc_fixed_measurement_bias, row, 3)} "
            f"{datetime_cell(ui.table_arc_fixed_measurement_bias, row, 4, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.table_arc_fixed_measurement_bias, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{_item_text(ui.table_arc_fixed_measurement_bias, row, 6)}"
        )
    for row in _nonempty_rows(ui.table_arc_select_observation):
        satellite_1 = _combine_select_satellite_1(
            _item_text(ui.table_arc_select_observation, row, 3),
            _item_text(ui.table_arc_select_observation, row, 4, "0000000"),
        )
        lines.append(
            "SelectObs "
            f"{_select_observation_type_code(_item_text(ui.table_arc_select_observation, row, 0))} "
            f"{_item_text(ui.table_arc_select_observation, row, 1)} "
            f"{_item_text(ui.table_arc_select_observation, row, 2)} {satellite_1} "
            f"{_item_text(ui.table_arc_select_observation, row, 5, '0000000')} "
            f"{_compact_card_datetime(ui.table_arc_select_observation, row, 6)} "
            f"{_compact_card_datetime(ui.table_arc_select_observation, row, 7)}"
        )
    for row in _nonempty_rows(ui.table_arc_delete_observation):
        lines.append(
            "Discard   "
            f"{_item_text(ui.table_arc_delete_observation, row, 0)} {_item_text(ui.table_arc_delete_observation, row, 1)} "
            f"{_item_text(ui.table_arc_delete_observation, row, 2)} {_item_text(ui.table_arc_delete_observation, row, 3, '0000000')} "
            f"{_item_text(ui.table_arc_delete_observation, row, 4, '0000000')} "
            f"{datetime_cell(ui.table_arc_delete_observation, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.table_arc_delete_observation, row, 6, 'yyyyMMddHHmmss.zzz')}"
        )
    lines.append(f"PerAccNum   {ui.spin_arc_per_acc_count.value()} {ui.combo_arc_per_acc_model_type.currentIndex()}")
    for row in _nonempty_rows(ui.table_arc_per_acc_period):
        lines.append(
            "PerAccinf   "
            f"{_item_text(ui.table_arc_per_acc_period, row, 0)} "
            f"{datetime_cell(ui.table_arc_per_acc_period, row, 1, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(ui.table_arc_per_acc_period, row, 2, 'yyyyMMddHHmmss.zzz')} "
            f"{_item_text(ui.table_arc_per_acc_period, row, 3, 'TDB')}"
        )
    for row in _nonempty_rows(ui.table_arc_per_acc_model):
        lines.append(
            "PerAcc    "
            f"{_coded_value(_item_text(ui.table_arc_per_acc_model, row, 0), PER_ACC_DIRECTION_INFO)} "
            f"{_coded_value(_item_text(ui.table_arc_per_acc_model, row, 1), PER_ACC_MODEL_INFO)} "
            f"{_item_text(ui.table_arc_per_acc_model, row, 2)} {_item_text(ui.table_arc_per_acc_model, row, 3)}"
        )
    lines.append("PrintStat 0000000000")
    lines.append("Residu    1")
    _write_lines(save_path, lines)


def read_lcp(path: str | Path, ui) -> None:
    """读取 LCP 弧段参数卡片并恢复轨道、观测和经验加速度表格。"""
    _clear_table_rows(
        ui.table_arc_observation_weight,
        ui.table_arc_measurement_bias,
        ui.table_arc_fixed_measurement_bias,
        ui.table_arc_select_observation,
        ui.table_arc_delete_observation,
        ui.table_arc_per_acc_period,
        ui.table_arc_per_acc_model,
    )
    for line in _clean_lines(path):
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        values = parts[1:]
        value_text = " ".join(values)
        if key == "SatID" and values:
            ui.edit_arc_satellite_id.setText(values[0])
        elif key == "SatMsAr":
            if len(values) > 0:
                ui.edit_arc_satellite_mass.setText(values[0])
            if len(values) > 1:
                ui.edit_arc_body_area.setText(values[1])
        elif key == "SatPanel" and values:
            ui.edit_arc_solar_panel_area.setText(values[0])
        elif key == "SatSoCr":
            if len(values) > 0:
                ui.edit_arc_solar_pressure_coefficient.setText(values[0])
            if len(values) > 1:
                ui.edit_arc_solar_pressure_prior_error.setText(values[1])
        elif key == "StartTime":
            ui.date_arc_start_time.setDateTime(parse_datetime(value_text))
        elif key == "EndTime":
            ui.date_arc_end_time.setDateTime(parse_datetime(value_text))
        elif key in ("OrbRootP0", "OrbRootP1"):
            _set_combo(ui.combo_arc_initial_orbit_type, "开普勒轨道根数" if key.endswith("1") else "直角坐标系")
            ui.edit_arc_initial_position.setText(value_text)
        elif key in ("OrbRootV0", "OrbRootV1"):
            ui.edit_arc_initial_velocity.setText(value_text)
        elif key == "OrbVARCOV1":
            ui.edit_arc_position_prior.setText(orbit_prior_values(values))
        elif key == "OrbVARCOV2":
            ui.edit_arc_velocity_prior.setText(orbit_prior_values(values))
        elif key == "DopWindow" and values:
            ui.edit_arc_doppler_integration_time.setText(values[0])
        elif key == "DopInvTime" and values:
            ui.edit_arc_doppler_inverse_time.setText(values[0])
        elif key == "IntegStep" and values:
            _set_step_text(ui, "combo_arc_integration_step", "edit_arc_integration_step_legacy", values[0])
        elif key == "PrintStep" and values:
            _set_step_text(ui, "combo_arc_output_step", "edit_arc_output_step_legacy", values[0])
        elif key == "ChooseInt" and values:
            if values[0] in CODE_TO_INTEGRATOR:
                _set_combo(ui.combo_integrator_type, CODE_TO_INTEGRATOR[values[0]])
        elif key == "ParDeriv" and values:
            ui.edit_arc_partial_derivative_step.setText(values[0])
        elif key.lower() == "orbderiv":
            if len(values) > 0:
                ui.edit_arc_position_derivative_step.setText(values[0])
            if len(values) > 1:
                ui.edit_arc_velocity_derivative_step.setText(values[1])
        elif key == "InputFilt" and values:
            idx = int(float(values[0]))
            if 0 <= idx < ui.combo_arc_input_filter.count():
                ui.combo_arc_input_filter.setCurrentIndex(idx)
        elif key == "SIGMA":
            obs_code = values[0] if values else ""
            row_values = [
                _observation_type_label(obs_code),
                values[1] if len(values) > 1 else "",
                _observation_type_unit(obs_code, values[2] if len(values) > 2 else ""),
            ]
            _append_plain_row(ui.table_arc_observation_weight, row_values)
        elif key == "PBIAS":
            _append_plain_row(ui.table_arc_measurement_bias, values[:3])
        elif key == "ObsBias":
            row_values, datetimes = _parse_obs_bias_row(values)
            row = _append_plain_row(ui.table_arc_fixed_measurement_bias, row_values)
            if len(datetimes) > 0:
                set_datetime_cell(ui.table_arc_fixed_measurement_bias, row, 4, datetimes[0])
            if len(datetimes) > 1:
                set_datetime_cell(ui.table_arc_fixed_measurement_bias, row, 5, datetimes[1])
        elif key == "SelectObs":
            pass_number, satellite_1 = _split_select_satellite_1(values[3] if len(values) > 3 else "")
            row_values = [
                _select_observation_type_label(values[0] if len(values) > 0 else ""),
                values[1] if len(values) > 1 else "",
                values[2] if len(values) > 2 else "",
                pass_number,
                satellite_1,
                values[4] if len(values) > 4 else "",
                "",
                "",
            ]
            row = _append_plain_row(ui.table_arc_select_observation, row_values)
            datetimes = _row_datetimes(values, 5)
            if len(datetimes) > 0:
                set_datetime_cell(ui.table_arc_select_observation, row, 6, datetimes[0])
            if len(datetimes) > 1:
                set_datetime_cell(ui.table_arc_select_observation, row, 7, datetimes[1])
        elif key == "Discard":
            row = _append_plain_row(ui.table_arc_delete_observation, values[:5])
            datetimes = _row_datetimes(values, 5)
            if len(datetimes) > 0:
                set_datetime_cell(ui.table_arc_delete_observation, row, 5, datetimes[0])
            if len(datetimes) > 1:
                set_datetime_cell(ui.table_arc_delete_observation, row, 6, datetimes[1])
        elif key == "PerAccNum":
            if values:
                ui.spin_arc_per_acc_count.setValue(int(float(values[0])))
            ui.combo_arc_per_acc_model_type.setCurrentIndex(0)
        elif key == "PerAccinf":
            row = _append_plain_row(ui.table_arc_per_acc_period, [values[0] if values else "", "", "", values[3] if len(values) > 3 else "TDB"])
            datetimes = _row_datetimes(values, 1)
            if len(datetimes) > 0:
                set_datetime_cell(ui.table_arc_per_acc_period, row, 1, datetimes[0])
            if len(datetimes) > 1:
                set_datetime_cell(ui.table_arc_per_acc_period, row, 2, datetimes[1])
        elif key == "PerAcc":
            row_values = [
                _coded_label(values[0] if len(values) > 0 else "", PER_ACC_DIRECTION_INFO),
                _coded_label(values[1] if len(values) > 1 else "", PER_ACC_MODEL_INFO),
                values[2] if len(values) > 2 else "",
                values[3] if len(values) > 3 else "",
            ]
            _append_plain_row(ui.table_arc_per_acc_model, row_values)
        elif key == "StaBaKer":
            ui.edit_arc_spice_kernel_path.setText(value_text)


def save_simcp(ui, save_path: str | Path) -> None:
    """从模拟观测表格生成 SimCP 控制卡片，保存时把中文类型转回数字码。"""
    table = ui.table_simulated_observations
    rows = list(_nonempty_rows(table))

    lines = _comment_header("SimCP 模拟观测卡片")
    lines.append("Simu      1")
    first_interval = _item_text(table, rows[0], 9, "30.000") if rows else "30.000"
    lines.append(f"SimuLim   {first_interval}")
    lines.append("#")

    for row in rows:
        obs_type = _observation_type_code(_item_text(table, row, 7, "51"))
        noise = _item_text(table, row, 8, "0.00d0")
        lines.append(f"SimuSat   {_item_text(table, row, 0, '-999')}")
        if obs_type != "53":
            lines.append(f"SimuSta   {_simcp_station_fields(table, row)}")
        lines.append(
            "SimuTim   "
            f"{datetime_cell(table, row, 5, 'yyyyMMddHHmmss.zzz')} "
            f"{datetime_cell(table, row, 6, 'yyyyMMddHHmmss.zzz')}"
        )
        lines.append(f"SimuTyp   {obs_type}           {noise}             0.000d0")
        lines.append("EndCnfg")
        lines.append("#")
    lines.append("EndSimu")
    _write_lines(save_path, lines)


def read_simcp(path: str | Path, ui) -> None:
    """读取 SimCP 模拟观测卡片并填充模拟观测表格。"""
    table = ui.table_simulated_observations
    table.setRowCount(0)
    current_type = ""
    global_interval = ""
    current = {}

    def append_current():
        """把当前累计的一组 SimCP 配置写入表格并重置临时状态。"""
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
            _observation_type_label(current.get("obs_type", current_type)),
            current.get("noise", ""),
            current.get("interval", global_interval),
        ]
        for col, value in enumerate(values):
            if col not in (5, 6):
                _set_item(table, row, col, value)
        start = current.get("start") or ui.date_arc_start_time.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        end = current.get("end") or ui.date_arc_end_time.dateTime().toString("yyyy-MM-dd HH:mm:ss.zzz")
        set_datetime_cell(table, row, 5, start)
        set_datetime_cell(table, row, 6, end)
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
    """从测站参数表格和全局测站设置生成 StaCP 控制卡片。"""
    table = ui.table_station_parameters
    rows = list(_nonempty_rows(table))
    lines = _comment_header("StaCP 测站参数卡片")
    lines.append(f"STATION {len(rows)}")
    lines.append(f"ELCUTOFF {ui.edit_station_elevation_cutoff.text().strip() or '15.0'}")
    lines.append(f"GEODETIC {ui.edit_station_earth_semimajor_axis.text().strip() or '6378137.000'} {ui.edit_station_earth_flattening.text().strip() or '298.257223563'}")
    lines.extend(["FIXED", ""])
    for row in rows:
        station_id = _item_text(table, row, 0)
        name = _item_text(table, row, 1)
        active = _coded_value(_item_text(table, row, 2, "激活"), STATION_STATUS_INFO)
        cutoff = _item_text(table, row, 3, ui.edit_station_elevation_cutoff.text().strip() or "15.0")
        coord_type = _coded_value(_item_text(table, row, 4, "直角坐标系XYZ"), STATION_COORD_TYPE_INFO)
        planet = _coded_value(_item_text(table, row, 12, "地球测站"), STATION_BODY_INFO)
        lines.append(f"STAIDNAME {station_id} {name} {cutoff} {active} {planet}")
        lines.append(f"STAPOS {_item_text(table, row, 5)} {_item_text(table, row, 6)} {_item_text(table, row, 7)} {coord_type}")
        vel = [_item_text(table, row, 8), _item_text(table, row, 9), _item_text(table, row, 10)]
        if any(vel):
            lines.append(f"STAVEL {vel[0]} {vel[1]} {vel[2]}")
        lines.extend(["ENDSTA", ""])
    lines.append("ENDALLSTA")
    _write_lines(save_path, lines)


def read_stacp(path: str | Path, ui) -> None:
    """读取 StaCP 测站参数卡片并恢复测站表格及测站全局参数。"""
    table = ui.table_station_parameters
    table.setRowCount(0)
    row = -1
    for line in _clean_lines(path):
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        values = parts[1:]
        if key == "STATION" and values:
            ui.spin_station_count.setValue(int(float(values[0])))
        elif key == "ELCUTOFF" and values:
            ui.edit_station_elevation_cutoff.setText(values[0])
        elif key == "GEODETIC":
            if len(values) > 0:
                ui.edit_station_earth_semimajor_axis.setText(values[0])
            if len(values) > 1:
                ui.edit_station_earth_flattening.setText(values[1])
        elif key == "STAIDNAME":
            row += 1
            table.insertRow(row)
            mapped = [
                values[0] if len(values) > 0 else "",
                values[1] if len(values) > 1 else "",
                _plain_coded_label(values[3] if len(values) > 3 else "1", STATION_STATUS_INFO, "激活"),
                values[2] if len(values) > 2 else "",
                _plain_coded_label("0", STATION_COORD_TYPE_INFO, "直角坐标系XYZ"),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                _plain_coded_label(values[4] if len(values) > 4 else "0", STATION_BODY_INFO, "地球测站"),
            ]
            for col, value in enumerate(mapped):
                _set_item(table, row, col, value)
        elif key == "STAPOS" and row >= 0:
            position_values = _numeric_values(line[len(key):])
            for col, value in enumerate(position_values[:3], start=5):
                _set_item(table, row, col, value)
            coord_type = position_values[3] if len(position_values) > 3 else "0"
            _set_item(table, row, 4, _plain_coded_label(coord_type, STATION_COORD_TYPE_INFO, "直角坐标系XYZ"))
        elif key == "STAVEL" and row >= 0:
            velocity_values = _numeric_values(line[len(key):])
            for col, value in enumerate(velocity_values[:3], start=8):
                _set_item(table, row, col, value)


def _nonempty_rows(table: QTableWidget):
    """遍历表格中至少有一个非空单元格的数据行。"""
    for row in range(table.rowCount()):
        if any(_item_text(table, row, col) for col in range(table.columnCount())):
            yield row


def _append_plain_row(table: QTableWidget, values: List[str]) -> int:
    """向表格追加普通文本行，若首行为空则复用首行。"""
    if table.rowCount() == 1 and not any(_item_text(table, 0, col) for col in range(table.columnCount())):
        row = 0
    else:
        row = table.rowCount()
        table.insertRow(row)
    for col, value in enumerate(values[: table.columnCount()]):
        _set_item(table, row, col, value)
    return row
