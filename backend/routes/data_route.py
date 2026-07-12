import csv
import datetime
import io
import json
import math
import random
import time

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import func

from models.database import FaultClosure, FaultRecord, db
from services.data_acquisition import daq_system
from services.data_simulator import generate_vibration_data
from services.ml_models import get_envelope, run_diagnosis
from services.wind_data_repository import FAULT_CODE_LABELS, wind_data_repository

data_bp = Blueprint("data_bp", __name__)

GEARBOX_FAULT_CODE_CATALOG = [
    {"code": "GBX-001", "name": "齿轮箱油温过高", "category": "温度异常", "signal": "oil_temp", "unit": "°C", "warning": 75, "critical": 85, "source": "SCADA", "advice": "检查油冷器、油泵、冷却风扇、油位和滤芯压差。"},
    {"code": "GBX-002", "name": "齿轮箱油温趋势异常", "category": "温度异常", "signal": "oil_temp", "unit": "°C", "warning": 70, "critical": 80, "source": "M-IALO-SVR", "advice": "对比预测残差和同型号机组油温，复核负荷、环境温度和散热状态。"},
    {"code": "GBX-003", "name": "高速轴承温度异常", "category": "轴承故障", "signal": "bearing_temp", "unit": "°C", "warning": 80, "critical": 90, "source": "SCADA/CMS", "advice": "结合包络谱检查高速轴承润滑不足、剥落和保持架异常。"},
    {"code": "GBX-004", "name": "低速轴承温度异常", "category": "轴承故障", "signal": "low_speed_bearing_temp", "unit": "°C", "warning": 75, "critical": 85, "source": "SCADA/CMS", "advice": "检查主传动链对中、轴承润滑状态和载荷波动。"},
    {"code": "GBX-005", "name": "振动 RMS 超限", "category": "振动异常", "signal": "vibration_rms", "unit": "mm/s", "warning": 4.5, "critical": 7.1, "source": "CMS", "advice": "开展频谱、包络谱和阶次分析，排查齿轮啮合、轴承和基础松动。"},
    {"code": "GBX-006", "name": "齿轮啮合异常", "category": "齿轮故障", "signal": "vibration_rms", "unit": "mm/s", "warning": 5.0, "critical": 7.5, "source": "CMS", "advice": "关注啮合频率及边频带，检查齿面磨损、偏载和齿侧间隙。"},
    {"code": "GBX-007", "name": "齿面点蚀/剥落", "category": "齿轮故障", "signal": "oil_quality", "unit": "NAS", "warning": 8, "critical": 10, "source": "油液+CMS", "advice": "取油样复检铁谱磨粒，结合振动冲击成分判断齿面损伤。"},
    {"code": "GBX-008", "name": "齿轮断齿风险", "category": "齿轮故障", "signal": "vibration_rms", "unit": "mm/s", "warning": 6.5, "critical": 8.5, "source": "CMS", "advice": "若出现周期性冲击和啮合边频带增强，应安排停机内窥镜检查。"},
    {"code": "GBX-009", "name": "润滑油污染/劣化", "category": "润滑系统", "signal": "oil_quality", "unit": "NAS", "warning": 8, "critical": 9, "source": "油液检测", "advice": "检查滤芯、呼吸器和油液水分，必要时过滤或换油。"},
    {"code": "GBX-010", "name": "润滑系统供油异常", "category": "润滑系统", "signal": "oil_quality", "unit": "NAS", "warning": 8.5, "critical": 11, "source": "SCADA/油液", "advice": "检查油泵压力、油路堵塞、喷油嘴和回油状态。"},
    {"code": "GBX-011", "name": "冷却系统故障", "category": "冷却系统", "signal": "oil_temp", "unit": "°C", "warning": 78, "critical": 88, "source": "SCADA", "advice": "检查冷却风扇、换热器脏堵、温控阀和冷却回路。"},
    {"code": "GBX-012", "name": "轴系不对中", "category": "传动链异常", "signal": "vibration_rms", "unit": "mm/s", "warning": 4.8, "critical": 7.2, "source": "CMS", "advice": "检查联轴器、主轴承座、齿轮箱地脚和安装对中状态。"},
    {"code": "GBX-013", "name": "箱体/基础松动", "category": "结构异常", "signal": "vibration_rms", "unit": "mm/s", "warning": 5.2, "critical": 7.8, "source": "CMS", "advice": "检查地脚螺栓、弹性支撑、箱体连接和基础刚度。"},
    {"code": "GBX-014", "name": "传感器信号异常", "category": "数据质量", "signal": "data_quality", "unit": "%", "warning": 98, "critical": 95, "source": "SCADA/CMS", "advice": "核查温度、振动和转速通道接线、量程、采样频率与通讯质量。"},
    {"code": "GBX-015", "name": "RUL 低于预警阈值", "category": "寿命风险", "signal": "rul_days", "unit": "天", "warning": 180, "critical": 90, "source": "健康评估", "advice": "缩短复检周期，结合历史故障、油液和振动趋势安排检修窗口。"},
]

GEARBOX_SCADA_CODE_MAP = {
    "GBX-001": "5",
    "GBX-002": "5",
    "GBX-003": "96",
    "GBX-004": "274",
    "GBX-005": "248",
    "GBX-006": "186",
    "GBX-007": "186/285",
    "GBX-008": "186",
    "GBX-009": "180/285",
    "GBX-010": "180",
    "GBX-011": "97",
    "GBX-012": "248",
    "GBX-013": "248",
    "GBX-014": "299/885",
    "GBX-015": "RUL",
}

SEVERITY_LEVELS = [5, 10, 20, 50, 80, 90, 100]

FIELD_CODE_SEVERITY = {
    "5": 50,
    "9": 20,
    "10": 20,
    "12": 50,
    "26": 50,
    "30": 80,
    "35": 20,
    "80": 90,
    "96": 80,
    "97": 50,
    "117": 10,
    "149": 50,
    "156": 10,
    "180": 80,
    "186": 90,
    "209": 50,
    "248": 80,
    "274": 80,
    "277": 10,
    "279": 20,
    "280": 50,
    "281": 20,
    "285": 80,
    "299": 20,
    "875": 5,
    "881": 20,
    "885": 20,
    "911": 20,
    "946": 10,
    "30006": 10,
    "41000": 100,
    "60004": 90,
    "RUL": 80,
}


def severity_level_from_fault(label, category="", source_code=""):
    code_levels = [
        FIELD_CODE_SEVERITY[part.strip()]
        for part in str(source_code).split("/")
        if part.strip() in FIELD_CODE_SEVERITY
    ]
    if code_levels:
        return max(code_levels)
    text = f"{label} {category} {source_code}"
    if any(key in text for key in ["断齿", "安全链"]):
        return 100
    if any(key in text for key in ["停机", "电网故障", "控制链路"]):
        return 90
    if any(key in text for key in ["点蚀", "剥落", "轴承", "啮合", "油液", "污染", "劣化"]):
        return 80
    if any(key in text for key in ["油温", "冷却", "润滑", "振动", "不对中", "松动", "制动", "液压", "变桨"]):
        return 50
    if any(key in text for key in ["传感器", "数据", "CMS", "SCADA", "通讯", "并网"]):
        return 20
    if any(key in text for key in ["限功率", "待风", "偏航"]):
        return 10
    return 5


def fault_category_from_label(label):
    if any(key in label for key in ["油", "润滑", "冷却"]):
        return "润滑冷却"
    if any(key in label for key in ["轴承", "齿轮", "啮合", "振动"]):
        return "齿轮轴承"
    if any(key in label for key in ["传感器", "SCADA", "CMS", "通讯", "数据"]):
        return "数据采集"
    if any(key in label for key in ["停机", "安全链", "限功率"]):
        return "运行事件"
    return "现场故障码"


def observed_fault_catalog(unit_id):
    if not wind_data_repository.available():
        return []
    all_counts = {}
    unit_counts = {}
    for info in wind_data_repository.fault_info_map().values():
        is_current = info.get("turbine") == unit_id
        for code, count in info.get("top_codes", []):
            code = str(code)
            count = int(count)
            all_counts[code] = all_counts.get(code, 0) + count
            if is_current:
                unit_counts[code] = unit_counts.get(code, 0) + count

    mapped_codes = set()
    for value in GEARBOX_SCADA_CODE_MAP.values():
        mapped_codes.update(part.strip() for part in str(value).split("/") if part.strip().isdigit())

    observed = []
    for code, total in sorted(all_counts.items(), key=lambda item: (-item[1], item[0])):
        label = FAULT_CODE_LABELS.get(code, f"现场故障码 {code}")
        current = unit_counts.get(code, 0)
        if code in mapped_codes:
            # Keep curated gearbox rows, but let the front end know this code exists in the imported data.
            continue
        observed.append({
            "code": f"SCADA-{code}",
            "source_code": code,
            "name": label,
            "category": fault_category_from_label(label),
            "signal": f"fault_code_{code}",
            "unit": "次",
            "warning": 10,
            "critical": 50,
            "source": "风机数据文件夹",
            "advice": "该故障码来自风机故障信息统计文件，建议结合发生时间、停机记录、SCADA 趋势和检修记录复核。",
            "observed_total": total,
            "observed_current": current,
        })
    return observed


SCENARIO_FAULTS = {
    "gear_wear": "齿轮齿面磨损",
    "pitting": "齿面点蚀/剥落",
    "broken_tooth": "齿轮断齿",
    "bearing_wear": "轴承磨损",
    "bearing": "轴承点蚀/剥落",
    "bearing_pitting": "轴承点蚀/剥落",
    "bearing_overheat": "高速轴承过温",
    "overheat": "齿轮箱油温过高",
    "gearbox_overheat": "齿轮箱油温过高",
    "oil_contamination": "润滑油污染/油液劣化",
    "misalignment": "轴系不对中",
    "shaft_misalignment": "轴系不对中",
    "mesh_abnormal": "齿轮啮合异常",
    "foundation_loose": "箱体或基础松动",
    "cooling_fault": "冷却系统故障",
}

FAULT_TYPE_DISTRIBUTION_BASE = [
    ("齿轮齿面磨损", 9),
    ("齿面点蚀/剥落", 7),
    ("齿轮断齿", 2),
    ("轴承磨损", 8),
    ("轴承点蚀/剥落", 6),
    ("高速轴承过温", 4),
    ("齿轮箱油温过高", 5),
    ("润滑油污染/油液劣化", 7),
    ("轴系不对中", 5),
    ("齿轮啮合异常", 6),
    ("箱体或基础松动", 4),
    ("冷却系统故障", 5),
    ("正常运行", 36),
]


def add_impulse_train(signal, step=75, amplitude=2.0, width=8):
    signal = list(signal)
    for center in range(40, len(signal), step):
        for offset in range(width):
            pos = center + offset
            if pos < len(signal):
                signal[pos] += math.sin(math.pi * offset / max(1, width)) * amplitude
    return signal


def add_low_frequency(signal, amplitude=1.1, freq=12):
    length = max(1, len(signal))
    return [value * 0.55 + amplitude * math.sin(2 * math.pi * freq * idx / length) for idx, value in enumerate(signal)]


def build_scenario_input(scenario, status, raw_signal):
    forced_fault_type = SCENARIO_FAULTS.get(scenario)
    if forced_fault_type:
        status["forced_fault_type"] = forced_fault_type
    if scenario == "normal":
        status.update({"oil_temp": 64.0, "vibration_rms": 2.6, "oil_quality": 5.2})
        return [value * 0.35 for value in raw_signal], status
    if scenario in ("overheat", "gearbox_overheat"):
        status.update({"oil_temp": 86.5, "vibration_rms": 3.4, "oil_quality": 8.5})
        return [value * 0.42 for value in raw_signal], status
    if scenario in ("misalignment", "shaft_misalignment"):
        status.update({"oil_temp": 71.2, "vibration_rms": 6.2, "oil_quality": 6.8})
        return add_low_frequency(raw_signal, amplitude=1.1, freq=12), status
    if scenario in ("bearing", "bearing_pitting"):
        status.update({"oil_temp": 76.8, "vibration_rms": 6.8, "oil_quality": 9.6})
        return add_impulse_train([value * 0.65 for value in raw_signal], step=75, amplitude=2.0), status
    if scenario == "gear_wear":
        status.update({"oil_temp": 70.5, "vibration_rms": 4.8, "oil_quality": 9.2})
        return add_low_frequency(raw_signal, amplitude=0.55, freq=38), status
    if scenario == "pitting":
        status.update({"oil_temp": 73.5, "vibration_rms": 5.4, "oil_quality": 10.4})
        return add_impulse_train([value * 0.7 for value in raw_signal], step=96, amplitude=1.65), status
    if scenario == "broken_tooth":
        status.update({"oil_temp": 78.5, "vibration_rms": 8.2, "oil_quality": 11.2})
        return add_impulse_train([value * 0.8 for value in raw_signal], step=128, amplitude=3.2, width=12), status
    if scenario == "bearing_wear":
        status.update({"oil_temp": 70.8, "vibration_rms": 4.9, "oil_quality": 8.4})
        return [value * 0.9 for value in raw_signal], status
    if scenario == "bearing_overheat":
        status.update({"oil_temp": 82.6, "vibration_rms": 5.5, "oil_quality": 8.8})
        return add_impulse_train([value * 0.6 for value in raw_signal], step=80, amplitude=1.45), status
    if scenario == "oil_contamination":
        status.update({"oil_temp": 72.2, "vibration_rms": 3.8, "oil_quality": 12.8})
        return [value * 0.52 for value in raw_signal], status
    if scenario == "mesh_abnormal":
        status.update({"oil_temp": 72.8, "vibration_rms": 5.9, "oil_quality": 8.7})
        return add_low_frequency(raw_signal, amplitude=0.75, freq=45), status
    if scenario == "foundation_loose":
        status.update({"oil_temp": 66.5, "vibration_rms": 6.3, "oil_quality": 6.2})
        return add_low_frequency(raw_signal, amplitude=1.25, freq=8), status
    if scenario == "cooling_fault":
        status.update({"oil_temp": 84.2, "vibration_rms": 3.6, "oil_quality": 7.8})
        return [value * 0.45 for value in raw_signal], status
    return raw_signal, status


def normalize_record_text(value):
    mapping = {
        "严重": "严重",
        "警告": "警告",
        "正常": "正常",
        "processed": "processed",
        "pending": "pending",
    }
    return mapping.get(value, value)


def serialize_record(record):
    data = {
        "id": record.id,
        "unit_id": record.unit_id,
        "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M"),
        "fault_type": normalize_record_text(record.fault_type),
        "severity": normalize_record_text(record.severity),
        "probability": record.probability,
        "advice": record.advice,
        "status": record.status,
        "work_order_action": "已处理" if record.status == "processed" else "待现场复核",
    }
    closure = FaultClosure.query.filter_by(record_ref=str(record.id)).first()
    if closure:
        data["status"] = "processed"
        data["work_order_action"] = closure.action or "已处理"
        data["closure"] = serialize_closure(closure)
    return data


def serialize_closure(closure):
    return {
        "owner": closure.owner,
        "action": closure.action,
        "result": closure.result,
        "note": closure.note,
        "closed_at": closure.closed_at.strftime("%Y-%m-%d %H:%M:%S") if closure.closed_at else "",
    }


def apply_closures(records):
    refs = [str(item.get("id")) for item in records if item.get("id") is not None]
    if not refs:
        return records
    closures = {
        item.record_ref: item
        for item in FaultClosure.query.filter(FaultClosure.record_ref.in_(refs)).all()
    }
    for record in records:
        closure = closures.get(str(record.get("id")))
        if closure:
            record["status"] = "processed"
            record["work_order_action"] = closure.action or "已处理"
            record["closure"] = serialize_closure(closure)
    return records


def enrich_vibration_data():
    data = generate_vibration_data()
    data["signal"] = daq_system.process_vibration_signal(data["signal"])
    data["envelope"] = get_envelope(data["signal"])
    return data


@data_bp.route("/vibration", methods=["GET"])
def get_vibration():
    return jsonify(enrich_vibration_data())


@data_bp.route("/status", methods=["GET"])
def get_status():
    unit_id = request.args.get("unit_id") or request.args.get("unit") or "WTG-001"
    if wind_data_repository.available():
        daq_system.sample_counter += 1
        status = wind_data_repository.status_payload(unit_id, daq_system.sample_counter)
        status["history_summary"] = daq_system.get_history_summary()
        return jsonify(status)
    status = daq_system.fuse_data()
    status["history_summary"] = daq_system.get_history_summary()
    status["sensors"] = daq_system.get_sensor_snapshot()
    return jsonify(status)


def fault_code_state(current, warning, critical, inverse=False):
    try:
        value = float(current)
    except (TypeError, ValueError):
        return "unknown"
    if inverse:
        if value <= critical:
            return "critical"
        if value <= warning:
            return "warning"
        return "normal"
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return "normal"


@data_bp.route("/fault-codes", methods=["GET"])
def get_fault_codes():
    unit_id = request.args.get("unit_id", "WTG-001")
    if wind_data_repository.available():
        detail = wind_data_repository.detail(unit_id)
        unit = detail.get("unit", {})
        temp = detail.get("temperature", {})
        life = detail.get("life", {})
        values = {
            "oil_temp": temp.get("gearbox", unit.get("oil_temp")),
            "bearing_temp": temp.get("bearing"),
            "low_speed_bearing_temp": round(float(temp.get("gearbox", 0) or 0) + 2.8, 1),
            "vibration_rms": unit.get("vibration_rms"),
            "oil_quality": round(5.5 + float(unit.get("fault_count", 0) or 0) / 180, 1),
            "data_quality": 99.1 if unit.get("has_realtime") else 96.5,
            "rul_days": life.get("rul_days", unit.get("rul_days")),
        }
        timestamp = detail.get("scada_time")
    else:
        status = daq_system.fuse_data()
        values = {
            "oil_temp": status.get("oil_temp"),
            "bearing_temp": status.get("bearing_temp", status.get("oil_temp", 0) + 8),
            "low_speed_bearing_temp": status.get("oil_temp", 0) + 3,
            "vibration_rms": status.get("vibration_rms"),
            "oil_quality": status.get("oil_quality"),
            "data_quality": status.get("data_quality", 99.0),
            "rul_days": status.get("predicted_rul_days", 365),
        }
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    catalog = [dict(item) for item in GEARBOX_FAULT_CODE_CATALOG] + observed_fault_catalog(unit_id)
    items = []
    for item in catalog:
        signal = item["signal"]
        if signal.startswith("fault_code_"):
            current = item.get("observed_current", 0)
        else:
            current = values.get(signal)
        inverse = signal in {"data_quality", "rul_days"}
        state = fault_code_state(current, item["warning"], item["critical"], inverse=inverse)
        raw_code = item.get("code")
        source_code = item.get("source_code") or GEARBOX_SCADA_CODE_MAP.get(raw_code, raw_code)
        severity_level = item.get("severity_level") or severity_level_from_fault(item.get("name", ""), item.get("category", ""), source_code)
        items.append({
            **item,
            "raw_code": raw_code,
            "source_code": source_code,
            "severity_level": severity_level,
            "current": current,
            "state": state,
            "inverse": inverse,
            "threshold_text": (
                f"关注≤{item['warning']} / 临界≤{item['critical']} {item['unit']}"
                if inverse
                else f"关注≥{item['warning']} / 临界≥{item['critical']} {item['unit']}"
            ),
        })

    items = sorted(items, key=lambda item: (
        item["severity_level"],
        item.get("category", ""),
        str(item.get("source_code", "")),
        item.get("name", ""),
    ))
    for index, item in enumerate(items, start=1):
        item["code"] = f"ERR-{index:03d}"

    summary = {
        "total": len(items),
        "critical": sum(1 for item in items if item["state"] == "critical"),
        "warning": sum(1 for item in items if item["state"] == "warning"),
        "normal": sum(1 for item in items if item["state"] == "normal"),
    }
    return jsonify({
        "unit_id": unit_id,
        "timestamp": timestamp,
        "values": values,
        "summary": summary,
        "items": items,
    })


@data_bp.route("/diagnosis", methods=["GET"])
def get_diagnosis():
    unit_id = request.args.get("unit_id") or request.args.get("unit") or "WTG-001"
    scenario = request.args.get("scenario", "auto")
    status = wind_data_repository.status_payload(unit_id, daq_system.sample_counter + 1) if wind_data_repository.available() else daq_system.fuse_data()
    vib_data = enrich_vibration_data()
    raw_signal, status = build_scenario_input(scenario, status, vib_data["signal"])
    result = run_diagnosis(unit_id=unit_id, raw_signal=raw_signal, status=status)
    result["scenario"] = scenario
    if result["severity"] in ["严重", "警告"]:
        priority = "P1" if result["severity"] == "严重" else "P2"
        result["eam_work_order"] = {
            "status": "已生成",
            "order_number": f"WO-{datetime.datetime.now().year}-{random.randint(1000, 9999)}",
            "priority": priority,
            "assigned_to": "运维班组-A",
            "suggested_window": "24 小时内" if priority == "P1" else "72 小时内",
            "closed_loop": ["诊断触发", "派发工单", "现场复核", "检修处理", "复测验收"],
        }
    return jsonify(result)


@data_bp.route("/records", methods=["GET"])
def get_records():
    records = FaultRecord.query.order_by(FaultRecord.timestamp.desc()).limit(50).all()
    if wind_data_repository.available():
        file_records = wind_data_repository.fault_records(limit=50)
        if file_records:
            return jsonify(apply_closures(file_records))
    return jsonify([serialize_record(record) for record in records])


@data_bp.route("/records/<int:record_id>/complete", methods=["POST"])
def complete_record(record_id):
    record = FaultRecord.query.get_or_404(record_id)
    record.status = "processed"
    db.session.commit()
    return jsonify(serialize_record(record))


@data_bp.route("/records/complete", methods=["POST"])
def complete_record_by_ref():
    data = request.json or {}
    record_ref = str(data.get("record_ref") or data.get("id") or "").strip()
    if not record_ref:
        return jsonify({"status": "error", "message": "缺少记录标识。"}), 400

    closure = FaultClosure.query.filter_by(record_ref=record_ref).first()
    if not closure:
        closure = FaultClosure(record_ref=record_ref)
        db.session.add(closure)

    closure.record_id = int(record_ref) if record_ref.isdigit() else None
    closure.unit_id = data.get("unit_id") or ""
    closure.fault_type = data.get("fault_type") or ""
    closure.owner = data.get("owner") or ""
    closure.action = data.get("action") or "已处理"
    closure.result = data.get("result") or ""
    closure.note = data.get("note") or ""
    closure.closed_at = datetime.datetime.now()

    if closure.record_id:
        record = FaultRecord.query.get(closure.record_id)
        if record:
            record.status = "processed"

    db.session.commit()
    return jsonify({"status": "success", "closure": serialize_closure(closure)})


@data_bp.route("/records/export", methods=["GET"])
def export_records():
    records = FaultRecord.query.order_by(FaultRecord.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["机组编号", "发生时间", "故障类型", "严重程度", "置信度", "处理状态", "工单动作", "建议措施"])
    for record in records:
        status_text = "已处理" if record.status == "processed" else "待处理"
        writer.writerow([
            record.unit_id,
            record.timestamp.strftime("%Y-%m-%d %H:%M"),
            normalize_record_text(record.fault_type),
            normalize_record_text(record.severity),
            f"{(record.probability or 0) * 100:.2f}%",
            status_text,
            "复测验收" if record.status == "processed" else "现场复核",
            record.advice or "",
        ])
    if wind_data_repository.available():
        for record in wind_data_repository.fault_records(limit=500):
            writer.writerow([
                record["unit_id"],
                record["timestamp"],
                record["fault_type"],
                record["severity"],
                f"{record['probability'] * 100:.2f}%",
                "待处理" if record["status"] == "pending" else "已处理",
                record["work_order_action"],
                record["advice"],
            ])
    data = "\ufeff" + output.getvalue()
    filename = f"SL1500_fault_records_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return Response(data, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@data_bp.route("/trend", methods=["GET"])
def get_trend_data():
    days = int(request.args.get("days", 30))
    unit_id = request.args.get("unit_id") or request.args.get("unit") or "WTG-001"
    if wind_data_repository.available():
        return jsonify(wind_data_repository.trend(unit_id, days))
    try:
        unit_no = int("".join(ch for ch in unit_id if ch.isdigit()) or "1")
    except ValueError:
        unit_no = 1
    rng = random.Random(unit_no * 7919 + days * 17)
    start_date = datetime.datetime.now() - datetime.timedelta(days=days)
    record_scope = FaultRecord.query.filter(FaultRecord.unit_id == unit_id)
    daily_raw = db.session.query(
        func.date(FaultRecord.timestamp).label("day"),
        func.count(FaultRecord.id).label("count"),
    ).filter(
        FaultRecord.timestamp >= start_date,
        FaultRecord.unit_id == unit_id,
    ).group_by(func.date(FaultRecord.timestamp)).all()
    daily_map = {str(row.day): row.count for row in daily_raw}
    daily_trend = []
    for i in range(days, 0, -1):
        day = datetime.datetime.now() - datetime.timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        base_risk = 0.35 + (unit_no % 9) * 0.08
        cycle = 0.5 + 0.5 * math.sin((i + unit_no) / 4.2)
        fallback_count = max(0, int(round(base_risk + cycle + rng.choice([0, 0, 1, 1, 2]) - 1)))
        daily_trend.append({"date": day.strftime("%m-%d"), "count": daily_map.get(key, fallback_count)})

    type_stats = db.session.query(
        FaultRecord.fault_type,
        func.count(FaultRecord.id).label("count"),
    ).filter(FaultRecord.unit_id == unit_id).group_by(FaultRecord.fault_type).all()
    if type_stats:
        type_distribution = [{"name": normalize_record_text(row.fault_type), "value": row.count} for row in type_stats]
    else:
        dominant_index = unit_no % max(1, len(FAULT_TYPE_DISTRIBUTION_BASE) - 1)
        type_distribution = []
        for index, (name, base) in enumerate(FAULT_TYPE_DISTRIBUTION_BASE):
            bias = 4 if index == dominant_index else (2 if (index + unit_no) % 5 == 0 else 0)
            type_distribution.append({"name": name, "value": max(1, base + bias + rng.randint(-2, 3))})

    severity_stats = db.session.query(
        FaultRecord.severity,
        func.count(FaultRecord.id).label("count"),
    ).filter(FaultRecord.unit_id == unit_id).group_by(FaultRecord.severity).all()
    if severity_stats:
        severity_distribution = [{"name": normalize_record_text(row.severity), "value": row.count} for row in severity_stats]
    else:
        risk_level = unit_no % 6
        severity_distribution = [
            {"name": "正常", "value": rng.randint(30, 50) - risk_level},
            {"name": "警告", "value": rng.randint(8, 18) + risk_level},
            {"name": "严重", "value": rng.randint(1, 5) + max(0, risk_level - 3)},
        ]

    unit_stats = db.session.query(FaultRecord.unit_id, func.count(FaultRecord.id).label("count")).group_by(FaultRecord.unit_id).order_by(func.count(FaultRecord.id).desc()).limit(8).all()
    if unit_stats:
        unit_distribution = [{"unit": row.unit_id, "count": row.count} for row in unit_stats]
    else:
        related_units = sorted({max(1, min(56, unit_no + offset)) for offset in [-9, -5, -2, 0, 3, 6, 11, 15]})
        while len(related_units) < 8:
            related_units.append(rng.randint(1, 56))
            related_units = sorted(set(related_units))
        unit_distribution = [
            {"unit": f"WTG-{str(i).zfill(3)}", "count": max(1, rng.randint(2, 14) + (4 if i == unit_no else 0))}
            for i in related_units[:8]
        ]
        unit_distribution.sort(key=lambda item: item["count"], reverse=True)

    total_faults = record_scope.count() or 0
    critical_faults = record_scope.filter(FaultRecord.severity == "严重").count() or 0
    pending_faults = record_scope.filter(FaultRecord.status == "pending").count() or 0
    if total_faults == 0:
        total_faults = sum(item["count"] for item in daily_trend)
        critical_faults = sum(item["value"] for item in severity_distribution if item["name"] == "严重")
        pending_faults = rng.randint(1, 6)

    return jsonify({
        "daily_trend": daily_trend,
        "type_distribution": type_distribution,
        "severity_distribution": severity_distribution,
        "unit_distribution": unit_distribution,
        "summary": {
            "unit_id": unit_id,
            "total_faults": total_faults,
            "critical_faults": critical_faults,
            "pending_faults": pending_faults,
            "days_queried": days,
        },
    })


@data_bp.route("/stream")
def data_stream():
    def generate():
        while True:
            if wind_data_repository.available():
                daq_system.sample_counter += 1
                status = wind_data_repository.status_payload("WTG-001", daq_system.sample_counter)
                sensors = status.get("sensors") or []
            else:
                status = daq_system.fuse_data()
                sensors = daq_system.get_sensor_snapshot()
            payload = {
                "status": status,
                "vibration": enrich_vibration_data(),
                "history_summary": daq_system.get_history_summary(),
                "sensors": sensors,
                "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(1)

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
