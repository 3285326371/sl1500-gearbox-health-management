import datetime

from flask import Blueprint, jsonify, request

from models.database import FaultRecord
from services.data_acquisition import daq_system
from services.wind_data_repository import wind_data_repository

report_bp = Blueprint("report_bp", __name__)


def build_summary(status, latest_fault):
    alerts = status.get("alert_items", [])
    if latest_fault and latest_fault.severity in ["警告", "严重"]:
        return f"最近诊断记录提示“{latest_fault.fault_type}”，建议结合实时油温、振动、油液颗粒度和负荷工况复核。"
    if alerts:
        return "机组存在实时告警，建议重点关注冷却系统、振动趋势或油液状态。"
    return "机组运行平稳，关键健康指标处于可控范围。"


def build_maintenance_plan(status):
    health_score = status.get("health_score", 95)
    rul = status.get("predicted_rul_days", 180)
    if rul <= 7 or health_score < 60:
        return "24 小时内现场复核，必要时安排停机检查。"
    if rul <= 30 or health_score < 80:
        return "7 天内完成复检，重点复测油温、振动包络和油液颗粒度。"
    return "按 30-90 天常规周期复检，若油温或振动连续升高则提前复检。"


def build_workorder_action(status, latest_fault):
    health_score = status.get("health_score", 95)
    if latest_fault and latest_fault.severity == "严重":
        return "生成 P1 检修工单，24 小时内现场检查并复测验收。"
    if latest_fault and latest_fault.severity == "警告":
        return "生成 P2 检修工单，72 小时内完成振动复测和取油样。"
    if health_score < 80:
        return "建议生成 P2 复核工单，纳入班组检修计划。"
    return "暂不生成检修工单，纳入月度趋势复核。"


def build_report_payload():
    unit_id = request.args.get("unit_id") or request.args.get("unit") or "WTG-001"
    days = int(request.args.get("days", 30))
    if wind_data_repository.available():
        detail = wind_data_repository.detail(unit_id)
        trend = wind_data_repository.trend(unit_id, days)
        unit = detail["unit"]
        latest_alarm = detail["alarms"][0] if detail.get("alarms") else None
        return {
            "report_id": f"REP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "unit_id": unit["id"],
            "range_days": days,
            "gen_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "health_score": unit["health_score"],
            "summary": f"{unit['id']} 已接入风机数据文件夹。当前油温 {unit['oil_temp']} °C，振动 {unit['vibration_rms']} mm/s，健康评分 {unit['health_score']} 分，建议 {detail['life']['recheck_interval_days']} 天内复检。",
            "detailed_metrics": {
                "average_oil_temp": f"{unit['oil_temp']} °C",
                "vibration_rms_peak": f"{unit['vibration_rms']} mm/s",
                "oil_quality_nas": wind_data_repository.status_payload(unit["id"]).get("oil_quality"),
                "active_power": f"{unit['power_kw']} kW",
                "data_quality": "99%" if unit["has_realtime"] else "96%",
                "predicted_rul": f"{unit['rul_days']} 天",
                "recheck_interval": f"{detail['life']['recheck_interval_days']} 天",
                "alarm_level": "警告" if trend["summary"]["total_faults"] else "正常",
                "fault_records": trend["summary"]["total_faults"],
                "data_range": f"{unit.get('data_start') or '--'} 至 {unit.get('data_end') or '--'}",
            },
            "diagnosis_result": {
                "type": latest_alarm["status"] if latest_alarm else "正常运行",
                "severity": "警告" if trend["summary"]["total_faults"] else "正常",
                "advice": detail["life"]["recheck_advice"],
            },
            "maintenance_plan": detail["life"]["recheck_advice"],
            "workorder_action": "如同类故障码持续出现，生成 P2 检修工单并安排油温、振动与油液复核；严重停机类故障生成 P1 工单。",
        }
    status = daq_system.fuse_data()
    latest_fault = FaultRecord.query.filter_by(unit_id=unit_id).order_by(FaultRecord.timestamp.desc()).first()
    rul_days = status.get("predicted_rul_days", "--")
    health_score = status.get("health_score", 95)
    recheck_days = 90 if health_score >= 85 else (30 if health_score >= 70 else 7)

    return {
        "report_id": f"REP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "unit_id": unit_id,
        "range_days": days,
        "gen_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "health_score": health_score,
        "summary": build_summary(status, latest_fault),
        "detailed_metrics": {
            "average_oil_temp": f"{status['oil_temp']} °C",
            "vibration_rms_peak": f"{status['vibration_rms']} mm/s",
            "oil_quality_nas": status["oil_quality"],
            "active_power": f"{status['power']} kW",
            "data_quality": f"{status.get('data_quality', '--')}%",
            "predicted_rul": f"{rul_days} 天",
            "recheck_interval": f"{recheck_days} 天",
            "alarm_level": "正常" if health_score >= 85 else ("警告" if health_score >= 70 else "严重"),
        },
        "diagnosis_result": {
            "type": latest_fault.fault_type if latest_fault else "正常运行",
            "severity": latest_fault.severity if latest_fault else "正常",
            "advice": latest_fault.advice if latest_fault else "继续保持常规巡检，关注油温、振动和油液趋势。",
        },
        "maintenance_plan": build_maintenance_plan(status),
        "workorder_action": build_workorder_action(status, latest_fault),
    }


@report_bp.route("/generate", methods=["GET"])
def generate_report():
    return jsonify(build_report_payload())


@report_bp.route("/health-summary", methods=["GET"])
def health_summary():
    return jsonify(build_report_payload())


@report_bp.route("/history", methods=["GET"])
def get_report_history():
    today = datetime.date.today()
    history = []
    for index in range(3):
        day = today - datetime.timedelta(days=index * 7)
        history.append({
            "id": f"REP-{day.strftime('%Y%m%d')}001",
            "date": day.strftime("%Y-%m-%d"),
            "type": "周报",
            "status": "已归档",
        })
    return jsonify(history)
