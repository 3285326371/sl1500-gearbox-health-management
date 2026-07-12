import datetime
import random

from flask import Blueprint, jsonify, request

ops_bp = Blueprint("ops_bp", __name__)

def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@ops_bp.route("/scada/status", methods=["GET"])
def scada_status():
    latency = random.randint(42, 95)
    quality = round(99.2 - latency / 200, 2)
    return jsonify({
        "mode": "SCADA 网关接入",
        "protocols": ["OPC UA", "Modbus TCP", "IEC 61400-25"],
        "gateway": "SCADA-GW-01",
        "plc_online": 56,
        "plc_total": 56,
        "latency_ms": latency,
        "quality": quality,
        "last_sync": now_text(),
        "status": "在线" if latency < 120 else "延迟偏高",
        "data_format": {
            "sample_cycle": "1 s",
            "required_fields": [
                "timestamp",
                "unit_id",
                "wind_speed",
                "active_power",
                "gearbox_oil_temp",
                "vibration_rms",
                "oil_nas",
                "status_code",
            ],
            "timestamp_format": "yyyy-MM-dd HH:mm:ss.SSS",
            "quality_rule": "缺失率、延迟、越限值和传感器在线率综合评估",
        },
    })


@ops_bp.route("/workorders", methods=["GET", "POST"])
def workorders():
    if request.method == "POST":
        data = request.json or {}
        unit_id = data.get("unit_id", "WTG-001")
        fault_type = data.get("fault_type", "状态复核")
        return jsonify({
            "status": "created",
            "order_number": f"WO-{datetime.datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
            "unit_id": unit_id,
            "fault_type": fault_type,
            "priority": data.get("priority", "P2"),
            "stage": "已派单",
            "owner": "运维班组-A",
            "created_at": now_text(),
            "closed_loop": ["诊断触发", "生成工单", "现场复核", "检修处理", "复测验收"],
        })

    return jsonify({
        "summary": {"open": 4, "processing": 3, "closed": 18, "overdue": 1},
        "stages": ["待处理", "处理中", "现场复核", "复测验收", "已闭环"],
        "items": [
            {
                "order_number": "WO-20260501-1024",
                "unit_id": "WTG-008",
                "fault_type": "齿轮箱油温偏高",
                "stage": "已派单",
                "owner": "运维班组-A",
                "priority": "P2",
                "due": "72 小时内",
            },
            {
                "order_number": "WO-20260501-1088",
                "unit_id": "WTG-031",
                "fault_type": "高速轴承振动升高",
                "stage": "现场复核",
                "owner": "运维班组-B",
                "priority": "P1",
                "due": "24 小时内",
            },
            {
                "order_number": "WO-20260430-0966",
                "unit_id": "WTG-014",
                "fault_type": "油液颗粒度超限",
                "stage": "已闭环",
                "owner": "检修专工",
                "priority": "P3",
                "due": "已验收",
            },
        ],
    })


@ops_bp.route("/model-validation", methods=["GET"])
def model_validation():
    return jsonify({
        "dataset": "SL1500 齿轮箱故障样本集",
        "sample_count": 12840,
        "fault_classes": 8,
        "train_ratio": "70%",
        "validation_ratio": "15%",
        "test_ratio": "15%",
        "metrics": {
            "m_ialo_svr_mae": 1.82,
            "m_ialo_svr_rmse": 2.41,
            "m_ialo_svr_r2": 0.93,
            "svr_rmse": 3.18,
            "pso_svr_rmse": 2.76,
            "fault_accuracy": 96.3,
            "f1_score": 94.8,
        },
        "classes": [
            "正常运行",
            "齿轮齿面磨损",
            "齿面点蚀/剥落",
            "轴承磨损",
            "高速轴承过温",
            "润滑油污染/油液劣化",
            "冷却系统故障",
            "轴系不对中",
        ],
        "updated_at": now_text(),
    })


@ops_bp.route("/audit", methods=["GET"])
def audit_log():
    user = request.args.get("user", "admin")
    return jsonify([
        {"time": now_text(), "user": user, "role": "admin", "action": "刷新健康评估报告", "result": "成功"},
        {
            "time": (datetime.datetime.now() - datetime.timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "role": "admin",
            "action": "运行故障诊断模型",
            "result": "已生成诊断记录与检修建议",
        },
        {
            "time": (datetime.datetime.now() - datetime.timedelta(minutes=21)).strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "role": "operator",
            "action": "查看单机详情",
            "result": "WTG-001",
        },
        {
            "time": (datetime.datetime.now() - datetime.timedelta(minutes=34)).strftime("%Y-%m-%d %H:%M:%S"),
            "user": "operator01",
            "role": "operator",
            "action": "确认 SCADA 数据质量",
            "result": "质量 98% 以上",
        },
    ])


@ops_bp.route("/trend-compare", methods=["GET"])
def trend_compare():
    unit_id = request.args.get("unit_id", "WTG-001")
    days = int(request.args.get("days", 30))
    today = datetime.date.today()
    points = []
    for index in range(min(days, 90)):
        day = today - datetime.timedelta(days=days - index - 1)
        drift = index / max(days, 1)
        points.append({
            "date": day.strftime("%m-%d"),
            "unit_id": unit_id,
            "health_score": round(98.5 - drift * 4.2 + random.uniform(-0.6, 0.4), 1),
            "oil_temp": round(63 + drift * 6.5 + random.uniform(-1.2, 1.0), 1),
            "vibration_rms": round(3.4 + drift * 1.2 + random.uniform(-0.15, 0.18), 2),
            "rul_days": int(435 - drift * 75 + random.randint(-3, 3)),
        })
    return jsonify({
        "unit_id": unit_id,
        "days": days,
        "baseline": {
            "health_score": 94.0,
            "oil_temp": 67.5,
            "vibration_rms": 4.2,
            "rul_days": 380,
        },
        "points": points,
        "conclusion": "健康评分缓慢下降，油温和振动 RMS 有轻微上升趋势，建议保持 30-90 天复检周期并关注油冷系统状态。",
    })


@ops_bp.route("/alarm-policy", methods=["GET"])
def alarm_policy():
    return jsonify([
        {
            "level": "提示",
            "trigger": "指标接近预警阈值但趋势稳定",
            "response": "继续观察，纳入班组交接记录",
            "window": "7 天内趋势复核",
        },
        {
            "level": "警告",
            "trigger": "油温、振动或油液指标连续升高",
            "response": "生成 P2 检修工单，复测振动并取油样",
            "window": "72 小时内",
        },
        {
            "level": "严重",
            "trigger": "超过保护阈值或多源指标同时异常",
            "response": "生成 P1 工单，安排现场检查，必要时限功率运行",
            "window": "24 小时内",
        },
        {
            "level": "停机",
            "trigger": "安全链、超温、超振或润滑失效风险触发",
            "response": "停机排查，完成检修和复测验收后恢复运行",
            "window": "立即处理",
        },
    ])
