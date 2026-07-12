import datetime
import json
import math
import random
import time

from flask import Blueprint, Response, jsonify

from services.wind_data_repository import wind_data_repository

windfarm_bp = Blueprint("windfarm_bp", __name__)

DEFAULT_TURBINE_COUNT = 68

STATUS_META = {
    "normal": {"label": "正常运行", "legend": "正常运行", "priority": 0},
    "limited": {"label": "限功率运行", "legend": "限功率运行", "priority": 1},
    "standby": {"label": "待风停机", "legend": "待风停机", "priority": 1},
    "alarm": {"label": "告警运行", "legend": "告警运行", "priority": 2},
    "maintenance": {"label": "维护停机", "legend": "维护停机", "priority": 3},
    "fault": {"label": "故障停机", "legend": "故障停机", "priority": 4},
}


def recheck_plan(health_score, rul_days):
    if health_score >= 90 and rul_days >= 365:
        return {"interval_days": 90, "level": "常规", "advice": "90 天内按计划复检，保持月度趋势复核。"}
    if health_score >= 80 and rul_days >= 180:
        return {"interval_days": 60, "level": "关注", "advice": "60 天内复检，重点跟踪油温、振动和油液 NAS 趋势。"}
    if health_score >= 70 and rul_days >= 90:
        return {"interval_days": 30, "level": "预警", "advice": "30 天内复检，检查润滑、轴承和齿轮箱温升。"}
    if health_score >= 60 and rul_days >= 30:
        return {"interval_days": 14, "level": "加密", "advice": "14 天内复检，必要时申请停机点检窗口。"}
    return {"interval_days": 7, "level": "高风险", "advice": "7 天内复检，并安排专项诊断或停机检查。"}


def turbine_status(index, tick):
    phase = math.sin(tick / 18 + index * 0.43)
    gust = math.sin(tick / 11 + index * 0.17)
    wind_speed = round(max(2.8, min(14.2, 8.6 + phase * 3.4 + random.uniform(-0.35, 0.35))), 1)
    if index in {5, 6, 8, 16, 18}:
        status = "limited"
    elif index in {14, 27, 51}:
        status = "maintenance"
    elif index in {23, 42} and int(tick) % 40 < 18:
        status = "alarm"
    elif index == 31 and int(tick) % 55 < 16:
        status = "fault"
    elif wind_speed < 5.0 or index % 7 == 0:
        status = "standby"
    else:
        status = "normal"

    if status == "normal":
        power = max(0, min(1500, (wind_speed - 3.2) ** 3 * 4.2 + random.uniform(-25, 25)))
    elif status == "limited":
        power = max(80, min(420, (wind_speed - 3.0) * 34 + random.uniform(-18, 18)))
    elif status == "alarm":
        power = max(60, min(680, (wind_speed - 3.5) * 48 + random.uniform(-35, 20)))
    else:
        power = random.uniform(-18, 6)

    oil_temp = round(61 + max(0, power) / 1500 * 18 + gust * 2.5, 1)
    vibration = round(2.4 + wind_speed * 0.18 + STATUS_META[status]["priority"] * 0.65 + random.uniform(-0.2, 0.2), 2)
    health_score = int(max(35, min(99, 99 - STATUS_META[status]["priority"] * 12 - max(0, oil_temp - 75) * 1.2)))
    return {
        "id": f"WTG-{index:03d}",
        "number": index,
        "status": status,
        "status_label": STATUS_META[status]["label"],
        "power_kw": round(power, 1),
        "wind_speed": wind_speed,
        "oil_temp": oil_temp,
        "vibration_rms": vibration,
        "health_score": health_score,
        "rul_days": int(max(7, health_score * 4.4 - STATUS_META[status]["priority"] * 35)),
    }


def turbine_indices():
    default_indices = set(range(1, DEFAULT_TURBINE_COUNT + 1))
    if wind_data_repository.available():
        data_indices = {wind_data_repository.unit_number(unit_id) for unit_id in wind_data_repository.all_unit_ids()}
        return sorted(default_indices | data_indices)
    return sorted(default_indices)


def build_windfarm_snapshot():
    tick = time.time()
    turbines = [turbine_status(index, tick) for index in turbine_indices()]
    turbine_count = len(turbines) or DEFAULT_TURBINE_COUNT
    running = [item for item in turbines if item["status"] in {"normal", "limited", "alarm"}]
    available = [item for item in turbines if item["status"] != "fault"]
    total_power = sum(max(0, item["power_kw"]) for item in turbines)
    status_counts = {key: 0 for key in STATUS_META}
    for item in turbines:
        status_counts[item["status"]] += 1
    return {
        "windfarm": "齿轮箱健康管理总览",
        "system": "SL1500 齿轮箱多源状态监测",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "time_availability": round(len(available) / turbine_count * 100, 2),
            "energy_availability": round((len(running) / turbine_count) * 100 - status_counts["limited"] * 0.18, 2),
            "average_temp": round(sum(item["oil_temp"] for item in turbines) / turbine_count, 2),
            "average_wind": round(sum(item["wind_speed"] for item in turbines) / turbine_count, 2),
            "total_power": round(total_power, 1),
            "average_health": round(sum(item["health_score"] for item in turbines) / turbine_count, 1),
            "alarm_count": status_counts["alarm"] + status_counts["fault"],
            "running_count": len(running),
            "turbine_count": turbine_count,
        },
        "status_counts": status_counts,
        "legend": [{"key": key, **value} for key, value in STATUS_META.items()],
        "turbines": turbines,
    }


@windfarm_bp.route("/overview", methods=["GET"])
def overview():
    if wind_data_repository.available():
        snapshot = wind_data_repository.overview()
        snapshot["legend"] = [{"key": key, **value} for key, value in STATUS_META.items()]
        return jsonify(snapshot)
    return jsonify(build_windfarm_snapshot())


def parameter_groups():
    return {
        "监测采集": [
            ("SCADA 采样周期", "1.00", "s"),
            ("CMS 振动采样频率", "25600", "Hz"),
            ("油温通道刷新周期", "1.00", "s"),
            ("油液检测周期", "30", "d"),
            ("数据质量下限", "98.00", "%"),
            ("通讯超时阈值", "10.00", "s"),
        ],
        "齿轮箱阈值": [
            ("齿轮箱油温关注值", "75.00", "°C"),
            ("齿轮箱油温告警值", "85.00", "°C"),
            ("高速轴承温度告警值", "90.00", "°C"),
            ("振动 RMS 关注值", "4.50", "mm/s"),
            ("振动 RMS 告警值", "7.10", "mm/s"),
            ("油液 NAS 上限", "9", "级"),
        ],
        "寿命评估": [
            ("设计寿命", "20", "年"),
            ("RUL 预警阈值", "180", "d"),
            ("RUL 严重阈值", "90", "d"),
            ("健康评分关注值", "85", "分"),
            ("健康评分告警值", "70", "分"),
            ("复检周期上限", "90", "d"),
        ],
        "诊断模型": [
            ("模型方法", "M-IALO-SVR", "-"),
            ("训练窗口", "30", "d"),
            ("预测步长", "24", "h"),
            ("残差告警阈值", "2.50", "σ"),
            ("样本类别数", "8", "类"),
            ("模型更新周期", "7", "d"),
        ],
        "报警策略": [
            ("提示处置窗口", "7", "d"),
            ("警告处置窗口", "72", "h"),
            ("严重处置窗口", "24", "h"),
            ("停机处置窗口", "0", "h"),
            ("告警确认超时", "30", "min"),
            ("复测验收周期", "24", "h"),
        ],
    }


@windfarm_bp.route("/turbine/<unit_id>", methods=["GET"])
def turbine_detail(unit_id):
    groups = parameter_groups()
    first_group = next(iter(groups))
    if wind_data_repository.available():
        detail = wind_data_repository.detail(unit_id)
        detail["parameter_groups"] = groups
        detail["parameters"] = groups[first_group]
        return jsonify(detail)

    try:
        number = int(unit_id.split("-")[-1])
    except (ValueError, IndexError):
        number = 1
    if number not in turbine_indices():
        number = 1

    base = turbine_status(number, time.time())
    status_priority = STATUS_META[base["status"]]["priority"]
    yaw_angle = round((number * 13.7 + time.time() / 8) % 360, 2)
    rotor_speed = round(max(0, base["wind_speed"] * 0.75 + random.uniform(-0.4, 0.4)), 2)
    alarms = []
    if base["status"] in {"fault", "alarm", "maintenance"}:
        alarms.append({"code": f"SCADA-{number % 9 + 1}", "status": base["status_label"], "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    else:
        code, text = "RUN-0", "运行链路正常，SCADA/CMS 数据同步稳定"
        if base["oil_temp"] >= 75:
            code, text = "TMP-1", "油温趋势偏高，建议关注油冷系统与润滑状态"
        elif base["vibration_rms"] >= 4.2:
            code, text = "VIB-1", "振动趋势接近关注阈值，建议跟踪频谱和包络谱"
        elif int(time.time() / 10 + number) % 3 == 0:
            code, text = "DAQ-0", "采集链路稳定，传感器在线"
        alarms.append({"code": code, "status": text, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    cluster_average = {"availability": 96.8, "health_score": 88.5, "wind_speed": 8.7, "power_kw": 720.0, "oil_temp": 67.5}
    cluster_compare = [
        {"name": "时间可利用率", "unit_value": round(100 - status_priority * 6.5 - max(0, base["vibration_rms"] - 4) * 0.5, 2), "cluster_value": cluster_average["availability"], "unit": "%"},
        {"name": "健康评分", "unit_value": base["health_score"], "cluster_value": cluster_average["health_score"], "unit": "分"},
        {"name": "实时风速", "unit_value": base["wind_speed"], "cluster_value": cluster_average["wind_speed"], "unit": "m/s"},
        {"name": "有功功率", "unit_value": base["power_kw"], "cluster_value": cluster_average["power_kw"], "unit": "kW"},
        {"name": "齿轮箱油温", "unit_value": base["oil_temp"], "cluster_value": cluster_average["oil_temp"], "unit": "°C"},
    ]
    component_state = [
        {"name": "轮毂", "value": round(base["wind_speed"] * 9.2, 1), "unit": "rpm", "level": "normal"},
        {"name": "主轴承", "value": round(base["oil_temp"] + 3.6, 1), "unit": "°C", "level": "warning" if base["oil_temp"] > 76 else "normal"},
        {"name": "齿轮箱", "value": base["oil_temp"], "unit": "°C", "level": "warning" if base["oil_temp"] > 76 else "normal"},
        {"name": "发电机", "value": round(base["oil_temp"] + 8.5, 1), "unit": "°C", "level": "warning" if base["oil_temp"] > 72 else "normal"},
        {"name": "变流器", "value": round(38 + status_priority * 3.2 + math.sin(number) * 2, 1), "unit": "°C", "level": "normal"},
    ]
    design_life_years = 20
    service_years = round(2.5 + (number % 11) * 0.18, 1)
    recheck = recheck_plan(base["health_score"], base["rul_days"])
    return jsonify({
        "unit": base,
        "metrics": {
            "active_power": base["power_kw"],
            "wind_speed": base["wind_speed"],
            "rotor_speed": rotor_speed,
            "pitch_angle": round(90 - min(88, max(0, base["power_kw"]) / 18), 2),
            "torque": round(max(0, base["power_kw"]) * 0.018, 2),
            "daily_energy": round(max(0, base["power_kw"]) * 6.8, 1),
            "availability": round(100 - status_priority * 6.5, 2),
            "total_energy": round(2300 + number * 1.8 + max(0, base["power_kw"]) / 1000, 2),
            "yaw_angle": yaw_angle,
        },
        "temperature": {
            "cabinet": round(24 + math.sin(number) * 2, 1),
            "generator": round(base["oil_temp"] + 8.5, 1),
            "gearbox": base["oil_temp"],
            "bearing": round(base["oil_temp"] + base["vibration_rms"] * 2.2, 1),
            "ambient": round(6 + math.sin(time.time() / 100) * 3, 1),
        },
        "life": {
            "design_life_years": design_life_years,
            "service_years": service_years,
            "remaining_design_years": round(max(0, design_life_years - service_years), 1),
            "fan_years": design_life_years,
            "gearbox_years": round(max(0.2, base["rul_days"] / 365), 1),
            "gearbox_months": max(1, int(base["rul_days"] / 30)),
            "health_score": base["health_score"],
            "rul_days": base["rul_days"],
            "recheck_interval_days": recheck["interval_days"],
            "recheck_level": recheck["level"],
            "recheck_advice": recheck["advice"],
        },
        "component_state": component_state,
        "cluster_compare": cluster_compare,
        "control_mode": "远程自动",
        "scada_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "parameter_groups": groups,
        "parameters": groups[first_group],
        "alarms": alarms,
    })


@windfarm_bp.route("/stream")
def stream():
    def generate():
        while True:
            yield f"data: {json.dumps(build_windfarm_snapshot(), ensure_ascii=False)}\n\n"
            time.sleep(3)

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
