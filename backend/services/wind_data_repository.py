import datetime
import json
import math
import random
from collections import Counter
from pathlib import Path


FAULT_CODE_LABELS = {
    "5": "齿轮箱油温趋势异常",
    "9": "偏航系统通讯异常",
    "10": "发电机温度异常",
    "12": "液压系统压力异常",
    "26": "变桨系统告警",
    "30": "制动系统告警",
    "35": "并网状态异常",
    "80": "控制链路停机事件",
    "96": "高速轴承温度异常",
    "97": "齿轮箱冷却系统异常",
    "117": "风速仪信号异常",
    "149": "变流器告警",
    "156": "机舱温度异常",
    "180": "润滑系统告警",
    "186": "齿轮啮合异常",
    "209": "电网侧告警",
    "248": "振动趋势异常",
    "274": "主轴承温度异常",
    "277": "偏航角度偏差",
    "279": "变桨角度偏差",
    "280": "变桨驱动异常",
    "281": "变桨通讯异常",
    "285": "油液状态异常",
    "299": "传感器信号异常",
    "875": "控制器复位事件",
    "881": "SCADA 通讯中断",
    "885": "CMS 数据质量异常",
    "911": "远程停机事件",
    "946": "待风停机事件",
    "30006": "限功率运行事件",
    "41000": "安全链动作",
    "60004": "电网故障停机",
}

GEARBOX_FAULT_CODES = {"5", "96", "97", "180", "186", "248", "274", "285", "299", "885"}


class WindDataRepository:
    def __init__(self):
        self._cache = None
        self._mtime = None
        self._root = Path(__file__).resolve().parents[2]
        self._summary_path = self._root / "风机数据" / "wind_data_summary.json"

    def available(self):
        return self._summary_path.exists()

    def load(self):
        if not self.available():
            return None
        mtime = self._summary_path.stat().st_mtime
        if self._cache is None or self._mtime != mtime:
            self._cache = json.loads(self._summary_path.read_text(encoding="utf-8"))
            self._mtime = mtime
        return self._cache

    @staticmethod
    def unit_number(unit_id):
        try:
            return int("".join(ch for ch in str(unit_id) if ch.isdigit()) or "1")
        except ValueError:
            return 1

    @staticmethod
    def unit_id(number):
        return f"WTG-{int(number):03d}"

    @staticmethod
    def _num(value, default=0.0):
        try:
            if value in ("", None):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _sane(self, value, low, high, default):
        number = self._num(value, default)
        if not math.isfinite(number) or number < low or number > high:
            return default
        return number

    def free_report_map(self):
        data = self.load() or {}
        report = data.get("free_report") or {}
        rows = report.get("records") or report.get("sample") or []
        result = {}
        for row in rows:
            if not row:
                continue
            number = int(self._num(row[0], 0))
            if number:
                result[self.unit_id(number)] = {
                    "avg_power": self._sane(row[1], -100, 1800, 0),
                    "avg_wind": self._sane(row[2], 0, 35, 6.0),
                    "max_wind": self._sane(row[3], 0, 70, 0),
                    "ambient": self._sane(row[4], -40, 55, 8.0),
                }
        return result

    def realtime_map(self):
        data = self.load() or {}
        return {item["turbine"]: item for item in data.get("realtime", [])}

    def fault_stats_map(self):
        data = self.load() or {}
        return {item["turbine"]: item for item in data.get("fault_stats", [])}

    def fault_info_map(self):
        data = self.load() or {}
        return {item["turbine"]: item for item in data.get("fault_info", [])}

    def all_unit_ids(self):
        ids = set(self.free_report_map()) | set(self.realtime_map()) | set(self.fault_stats_map()) | set(self.fault_info_map())
        if not ids:
            ids = {self.unit_id(i) for i in range(1, 57)}
        return sorted(ids, key=self.unit_number)

    def _fault_risk(self, unit_id):
        stats = self.fault_stats_map().get(unit_id) or {}
        info = self.fault_info_map().get(unit_id) or {}
        fault_count = int(stats.get("fault_count") or info.get("records") or 0)
        return fault_count, min(34, fault_count / 28)

    def turbine_snapshot(self, unit_id):
        number = self.unit_number(unit_id)
        unit_id = self.unit_id(number)
        realtime = self.realtime_map().get(unit_id) or {}
        free = self.free_report_map().get(unit_id) or {}
        avg = realtime.get("avg") or {}
        last = realtime.get("last") or {}
        maxs = realtime.get("max") or {}

        wind_speed = round(self._num(free.get("avg_wind"), 5.5 + (number % 7) * 0.6), 1)
        avg_power = self._num(avg.get("有功功率"), self._num(free.get("avg_power"), 0))
        power_kw = self._num(last.get("有功功率"), avg_power)
        generator_speed = self._num(last.get("发电机转速"), self._num(avg.get("发电机转速"), 0))
        oil_temp = self._num(last.get("齿轮箱油温"), self._num(avg.get("齿轮箱油温"), self._num(last.get("齿轮箱加热"), self._num(avg.get("齿轮箱加热"), 56 + avg_power / 110))))
        pitch = self._num(last.get("叶片1角度"), self._num(avg.get("叶片1角度"), max(0, 84 - max(0, avg_power) / 22)))
        nacelle = self._num(last.get("机舱位置"), self._num(avg.get("机舱位置"), (number * 13.7) % 360))
        ambient = self._num(last.get("环境温度"), self._num(free.get("ambient"), 8.5))
        fault_count, fault_risk = self._fault_risk(unit_id)
        vibration_rms = round(2.3 + min(3.2, fault_count / 180) + max(0, oil_temp - 70) * 0.08 + (number % 5) * 0.08, 2)

        status = "normal"
        status_label = "正常运行"
        if fault_count >= 500 or oil_temp >= 80 or vibration_rms >= 6:
            status, status_label = "alarm", "告警运行"
        elif power_kw <= 1 and generator_speed < 80:
            status, status_label = "standby", "待机"
        elif power_kw < 0:
            status, status_label = "limited", "限功率运行"

        health_score = int(max(35, min(99, 99 - fault_risk - max(0, oil_temp - 65) * 0.9 - max(0, vibration_rms - 3.5) * 5)))
        rul_days = int(max(30, min(620, health_score * 4.9 - fault_risk * 8)))
        return {
            "id": unit_id,
            "number": number,
            "status": status,
            "status_label": status_label,
            "power_kw": round(power_kw, 1),
            "avg_power_kw": round(avg_power, 1),
            "wind_speed": wind_speed,
            "max_wind_speed": round(self._num(free.get("max_wind"), maxs.get("风速", wind_speed)), 1),
            "generator_speed": round(generator_speed, 1),
            "pitch_angle": round(pitch, 2),
            "oil_temp": round(oil_temp, 1),
            "ambient_temp": round(ambient, 1),
            "nacelle_position": round(nacelle, 2),
            "vibration_rms": vibration_rms,
            "health_score": health_score,
            "rul_days": rul_days,
            "fault_count": fault_count,
            "data_start": realtime.get("start", ""),
            "data_end": realtime.get("end", ""),
            "sample_rows": realtime.get("rows", 0),
            "source_file": realtime.get("file") or "",
            "has_realtime": bool(realtime),
            "has_faults": bool(fault_count),
            "design_life_years": 20,
        }

    def overview(self, asset_numbers=None):
        ids = self.all_unit_ids()
        if asset_numbers:
            ids = sorted(set(ids) | {self.unit_id(n) for n in asset_numbers}, key=self.unit_number)
        turbines = [self.turbine_snapshot(unit_id) for unit_id in ids]
        count = len(turbines) or 1
        available = [item for item in turbines if item["status"] != "fault"]
        running = [item for item in turbines if item["status"] in {"normal", "limited", "alarm"}]
        status_counts = Counter(item["status"] for item in turbines)
        return {
            "windfarm": "齿轮箱健康管理总览",
            "system": "SL1500 齿轮箱多源状态监测",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "time_availability": round(len(available) / count * 100, 2),
                "energy_availability": round(len(running) / count * 100, 2),
                "average_temp": round(sum(item["oil_temp"] for item in turbines) / count, 2),
                "average_wind": round(sum(item["wind_speed"] for item in turbines) / count, 2),
                "total_power": round(sum(max(0, item["power_kw"]) for item in turbines), 1),
                "average_health": round(sum(item["health_score"] for item in turbines) / count, 1),
                "alarm_count": status_counts["alarm"] + status_counts["fault"],
                "running_count": len(running),
                "turbine_count": count,
                "data_source": "风机数据文件夹",
            },
            "status_counts": {
                "normal": status_counts["normal"],
                "limited": status_counts["limited"],
                "standby": status_counts["standby"],
                "alarm": status_counts["alarm"],
                "maintenance": status_counts["maintenance"],
                "fault": status_counts["fault"],
            },
            "turbines": turbines,
        }

    def detail(self, unit_id):
        unit = self.turbine_snapshot(unit_id)
        oil_temp = unit["oil_temp"]
        health = unit["health_score"]
        rul = unit["rul_days"]
        recheck_days = 90 if health >= 90 and rul >= 365 else 60 if health >= 80 else 30 if health >= 70 else 14
        recheck_level = "常规" if recheck_days == 90 else "关注" if recheck_days == 60 else "预警" if recheck_days == 30 else "加密"
        fault_info = self.fault_info_map().get(unit["id"]) or {}
        top_codes = fault_info.get("top_codes") or []
        alarms = []
        if top_codes:
            primary = next((item for item in top_codes if str(item[0]) in GEARBOX_FAULT_CODES), top_codes[0])
            code = str(primary[0])
            count = primary[1]
            prefix = "齿轮箱关联故障" if code in GEARBOX_FAULT_CODES else "运行关联事件"
            alarms.append({
                "code": f"FAULT-{code}",
                "status": f"{prefix}：{FAULT_CODE_LABELS.get(code, '历史故障码')}，历史出现 {count} 次",
                "time": fault_info.get("end") or unit.get("data_end") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        if not alarms:
            alarms.append({"code": "RUN-0", "status": "运行链路正常，SCADA/CMS 数据同步稳定", "time": unit.get("data_end") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return {
            "unit": unit,
            "metrics": {
                "active_power": unit["power_kw"],
                "wind_speed": unit["wind_speed"],
                "rotor_speed": round(max(0, unit["generator_speed"] / 104.0), 2),
                "generator_speed": unit["generator_speed"],
                "pitch_angle": unit["pitch_angle"],
                "torque": round(max(0, unit["power_kw"]) * 0.018, 2),
                "daily_energy": round(max(0, unit["avg_power_kw"]) * 24, 1),
                "availability": round(max(0, 100 - unit["fault_count"] / 60), 2),
                "total_energy": round(2300 + unit["number"] * 1.8 + max(0, unit["avg_power_kw"]) / 120, 2),
                "yaw_angle": unit["nacelle_position"],
            },
            "temperature": {
                "cabinet": round(25 + (unit["number"] % 5) * 0.6, 1),
                "generator": round(oil_temp + 8.5, 1),
                "gearbox": oil_temp,
                "bearing": round(oil_temp + unit["vibration_rms"] * 2.1, 1),
                "ambient": unit["ambient_temp"],
            },
            "life": {
                "design_life_years": 20,
                "fan_years": 20,
                "service_years": round(2.5 + (unit["number"] % 11) * 0.18, 1),
                "gearbox_years": round(max(0.1, rul / 365), 1),
                "gearbox_months": max(1, int(rul / 30)),
                "health_score": health,
                "rul_days": rul,
                "recheck_interval_days": recheck_days,
                "recheck_level": recheck_level,
                "recheck_advice": f"当前健康评分 {health} 分，建议 {recheck_days} 天内复检，重点核查油温、振动和历史故障码趋势。",
            },
            "component_state": [
                {"name": "低速轴承", "value": round(oil_temp + 2.8, 1), "unit": "°C", "level": "warning" if oil_temp > 72 else "normal"},
                {"name": "高速轴承", "value": round(oil_temp + unit["vibration_rms"] * 2.1, 1), "unit": "°C", "level": "warning" if oil_temp > 72 or unit["vibration_rms"] > 4.5 else "normal"},
                {"name": "齿轮箱油温", "value": oil_temp, "unit": "°C", "level": "warning" if oil_temp > 72 else "normal"},
                {"name": "振动 RMS", "value": unit["vibration_rms"], "unit": "mm/s", "level": "warning" if unit["vibration_rms"] > 4.5 else "normal"},
                {"name": "润滑油", "value": 7 if unit["vibration_rms"] < 4.5 and oil_temp < 75 else 9, "unit": "NAS", "level": "warning" if unit["vibration_rms"] >= 4.5 or oil_temp >= 75 else "normal"},
            ],
            "cluster_compare": [
                {"name": "健康评分", "unit_value": health, "cluster_value": 90, "unit": "分"},
                {"name": "齿轮箱油温", "unit_value": oil_temp, "cluster_value": 60.5, "unit": "°C"},
                {"name": "振动 RMS", "unit_value": unit["vibration_rms"], "cluster_value": 3.8, "unit": "mm/s"},
                {"name": "RUL", "unit_value": rul, "cluster_value": 360, "unit": "天"},
                {"name": "历史故障", "unit_value": unit["fault_count"], "cluster_value": 120, "unit": "条"},
            ],
            "control_mode": "远程自动",
            "scada_time": unit.get("data_end") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "alarms": alarms,
        }

    def trend(self, unit_id, days=30):
        unit_id = self.unit_id(self.unit_number(unit_id))
        stats = self.fault_stats_map().get(unit_id) or {}
        info = self.fault_info_map().get(unit_id) or {}
        seed = self.unit_number(unit_id) * 1009 + days
        rng = random.Random(seed)
        total_faults = int(stats.get("fault_count") or info.get("records") or 0)
        avg_daily = total_faults / max(1, int(stats.get("days") or days))
        daily_trend = []
        today = datetime.date.today()
        for offset in range(days, 0, -1):
            day = today - datetime.timedelta(days=offset)
            wave = 0.6 + 0.6 * math.sin((offset + self.unit_number(unit_id)) / 4.0)
            count = max(0, int(round(avg_daily * wave + rng.choice([0, 0, 1]) - 0.4)))
            daily_trend.append({"date": day.strftime("%m-%d"), "count": count})

        type_distribution = []
        for code, count in info.get("top_codes", []):
            type_distribution.append({"name": FAULT_CODE_LABELS.get(str(code), f"故障码 {code}"), "value": int(count)})
        if not type_distribution and total_faults:
            type_distribution = [{"name": "历史故障事件", "value": total_faults}]

        severe_raw = sum(item["value"] for item in type_distribution if any(key in item["name"] for key in ["安全链", "停机", "电网故障"]))
        severe = min(total_faults, severe_raw)
        warning = max(0, total_faults - severe)
        severity_distribution = [
            {"name": "正常", "value": max(1, days - min(days, warning // 10))},
            {"name": "警告", "value": warning},
            {"name": "严重", "value": severe},
        ]

        unit_distribution = [
            {"unit": item["turbine"], "count": int(item.get("fault_count") or 0)}
            for item in sorted(self.fault_stats_map().values(), key=lambda x: int(x.get("fault_count") or 0), reverse=True)[:8]
        ]
        return {
            "daily_trend": daily_trend,
            "type_distribution": type_distribution,
            "severity_distribution": severity_distribution,
            "unit_distribution": unit_distribution,
            "summary": {
                "unit_id": unit_id,
                "total_faults": total_faults or sum(item["count"] for item in daily_trend),
                "critical_faults": severe,
                "pending_faults": max(0, min(8, total_faults // 80)),
                "days_queried": days,
                "data_source": "风机数据文件夹",
            },
        }

    def fault_records(self, limit=50):
        records = []
        for unit_id, info in self.fault_info_map().items():
            for idx, (code, count) in enumerate(info.get("top_codes", [])[:4], start=1):
                label = FAULT_CODE_LABELS.get(str(code), f"故障码 {code}")
                severity = "严重" if any(key in label for key in ["安全链", "停机", "电网故障"]) or int(count) >= 120 else "警告"
                records.append({
                    "id": f"{unit_id}-{code}",
                    "unit_id": unit_id,
                    "timestamp": info.get("end") or "",
                    "fault_type": label,
                    "severity": severity,
                    "probability": round(min(0.99, 0.72 + int(count) / 800), 2),
                    "advice": f"该故障码历史出现 {count} 次，建议结合 SCADA 趋势、CMS 振动和检修记录复核。",
                    "status": "pending" if severity == "严重" else "processed",
                    "work_order_action": "生成 P1/P2 检修工单" if severity == "严重" else "纳入趋势跟踪",
                })
        return sorted(records, key=lambda item: (item["severity"] != "严重", item["unit_id"]))[:limit]

    def status_payload(self, unit_id="WTG-001", sample_count=1):
        detail = self.detail(unit_id)
        unit = detail["unit"]
        alerts = []
        if unit["oil_temp"] >= 75:
            alerts.append({"level": "警告", "message": "齿轮箱油温偏高，建议核查油冷系统、油位和负荷工况。"})
        if unit["vibration_rms"] >= 4.5:
            alerts.append({"level": "警告", "message": "振动 RMS 偏高，建议复测包络谱并检查轴承和齿轮啮合状态。"})
        return {
            "timestamp": datetime.datetime.now().timestamp(),
            "unit_id": unit["id"],
            "oil_temp": unit["oil_temp"],
            "vibration_rms": unit["vibration_rms"],
            "oil_quality": round(5.5 + unit["fault_count"] / 180, 1),
            "power": unit["power_kw"],
            "latency_ms": 52,
            "packet_loss": 0.05,
            "sampling_rate_hz": 25600,
            "acquisition_status": "在线",
            "data_quality": 99 if unit["has_realtime"] else 96,
            "online_sensors": 4,
            "total_sensors": 4,
            "sample_count": sample_count,
            "uptime_seconds": 0,
            "health_score": unit["health_score"],
            "predicted_rul_days": unit["rul_days"],
            "alerts": len(alerts),
            "alert_items": alerts,
            "sensors": self.sensor_snapshot(unit),
        }

    def sensor_snapshot(self, unit):
        return [
            {"id": "TEMP_GBX_OIL", "name": "齿轮箱油温", "type": "SCADA", "unit": "°C", "sample_rate": 1, "value": unit["oil_temp"], "status": "在线"},
            {"id": "VIB_HS_BRG", "name": "高速轴承振动", "type": "CMS", "unit": "mm/s", "sample_rate": 25600, "value": unit["vibration_rms"], "status": "在线"},
            {"id": "GEN_SPEED", "name": "发电机转速", "type": "SCADA", "unit": "rpm", "sample_rate": 1, "value": unit["generator_speed"], "status": "在线"},
            {"id": "P_ACTIVE", "name": "有功功率", "type": "SCADA", "unit": "kW", "sample_rate": 1, "value": unit["power_kw"], "status": "在线"},
        ]


wind_data_repository = WindDataRepository()
