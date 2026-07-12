import random
import time
from collections import deque

import numpy as np


class DataAcquisitionSystem:
    """SCADA/CMS/油液在线监测数据采集层。"""

    def __init__(self):
        self.sensors = {
            "TEMP_GBX_OIL": {"name": "齿轮箱油温", "unit": "°C", "type": "SCADA", "sample_rate": 1},
            "VIB_HS_BRG": {"name": "高速轴承振动", "unit": "mm/s", "type": "CMS", "sample_rate": 25600},
            "OIL_NAS": {"name": "油液颗粒度", "unit": "NAS", "type": "OIL", "sample_rate": 0.02},
            "P_ACTIVE": {"name": "有功功率", "unit": "kW", "type": "SCADA", "sample_rate": 1},
        }
        self.rt_cache = deque(maxlen=120)
        self.sample_counter = 0
        self.start_time = time.time()
        self.last_status = None

    def get_raw_data(self, sensor_id):
        base_values = {
            "TEMP_GBX_OIL": 64.0,
            "VIB_HS_BRG": 2.8,
            "OIL_NAS": 5.8,
            "P_ACTIVE": 1180.0,
        }
        noise_ranges = {
            "TEMP_GBX_OIL": 0.35,
            "VIB_HS_BRG": 0.18,
            "OIL_NAS": 0.25,
            "P_ACTIVE": 12.0,
        }
        base = base_values.get(sensor_id, 0.0)
        operating_wave = np.sin(time.time() / 120) * 0.8
        noise = random.gauss(0, noise_ranges.get(sensor_id, 0.3))
        return base + operating_wave + noise

    def advanced_filter(self, data_list):
        if not data_list:
            return 0
        arr = np.array(data_list, dtype=float)
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            return mean
        filtered = arr[np.abs(arr - mean) < 2 * std]
        return np.mean(filtered) if len(filtered) else mean

    def _build_alerts(self, oil_temp, vibration_rms, oil_quality):
        alerts = []
        if oil_temp >= 85:
            alerts.append({"level": "严重", "message": "齿轮箱油温超过 85°C，建议核查油冷风扇、散热器、三通阀和油位。"})
        elif oil_temp >= 75:
            alerts.append({"level": "警告", "message": "齿轮箱油温进入关注区间，建议结合负荷和环境温度观察升温趋势。"})

        if vibration_rms >= 6:
            alerts.append({"level": "严重", "message": "高速轴承振动 RMS 偏高，建议导出波形并复核包络谱。"})
        elif vibration_rms >= 4.5:
            alerts.append({"level": "警告", "message": "振动接近预警阈值，建议 72 小时内复测并比对趋势。"})

        if oil_quality >= 10:
            alerts.append({"level": "警告", "message": "油液 NAS 等级偏高，建议取样复检并检查滤芯、呼吸器和磁性堵塞物。"})
        return alerts

    def _quality_score(self, latency_ms, packet_loss, alerts):
        score = 100 - latency_ms * 0.35 - packet_loss * 8 - len(alerts) * 5
        return int(max(60, min(100, round(score))))

    def _health_score(self, oil_temp, vibration_rms, oil_quality):
        temp_risk = max(0, min(1, (oil_temp - 70) / 18))
        vib_risk = max(0, min(1, (vibration_rms - 3.5) / 3.5))
        oil_risk = max(0, min(1, (oil_quality - 7) / 5))
        risk = temp_risk * 0.35 + vib_risk * 0.45 + oil_risk * 0.2
        return int(max(35, min(99, round(99 - risk * 58))))

    def fuse_data(self):
        temp_samples = [self.get_raw_data("TEMP_GBX_OIL") for _ in range(20)]
        vib_samples = [self.get_raw_data("VIB_HS_BRG") for _ in range(50)]

        oil_temp = round(self.advanced_filter(temp_samples), 2)
        vibration_rms = round(self.advanced_filter(vib_samples), 2)
        oil_quality = round(self.get_raw_data("OIL_NAS"), 1)
        power = round(self.get_raw_data("P_ACTIVE"), 2)
        latency_ms = random.randint(8, 28)
        packet_loss = round(random.uniform(0.0, 0.5), 2)
        alerts = self._build_alerts(oil_temp, vibration_rms, oil_quality)
        health_score = self._health_score(oil_temp, vibration_rms, oil_quality)
        predicted_rul = int(max(30, min(520, health_score * 4.8 - len(alerts) * 35)))

        self.sample_counter += 1
        result = {
            "timestamp": time.time(),
            "oil_temp": oil_temp,
            "vibration_rms": vibration_rms,
            "oil_quality": oil_quality,
            "power": power,
            "latency_ms": latency_ms,
            "packet_loss": packet_loss,
            "sampling_rate_hz": 25600,
            "acquisition_status": "在线",
            "data_quality": self._quality_score(latency_ms, packet_loss, alerts),
            "online_sensors": len(self.sensors),
            "total_sensors": len(self.sensors),
            "sample_count": self.sample_counter,
            "uptime_seconds": int(time.time() - self.start_time),
            "health_score": health_score,
            "predicted_rul_days": predicted_rul,
            "alerts": len(alerts),
            "alert_items": alerts,
        }
        self.rt_cache.append(result)
        self.last_status = result
        return result

    def get_sensor_snapshot(self):
        status = self.last_status or self.fuse_data()
        values = {
            "TEMP_GBX_OIL": status["oil_temp"],
            "VIB_HS_BRG": status["vibration_rms"],
            "OIL_NAS": status["oil_quality"],
            "P_ACTIVE": status["power"],
        }
        return [
            {
                "id": sensor_id,
                "name": meta["name"],
                "type": meta["type"],
                "unit": meta["unit"],
                "sample_rate": meta["sample_rate"],
                "value": values.get(sensor_id),
                "status": "在线",
            }
            for sensor_id, meta in self.sensors.items()
        ]

    def get_history_summary(self):
        if not self.rt_cache:
            return None
        temps = [item["oil_temp"] for item in self.rt_cache]
        vibs = [item["vibration_rms"] for item in self.rt_cache]
        quality = [item["data_quality"] for item in self.rt_cache]
        return {
            "avg_temp": round(float(np.mean(temps)), 2),
            "max_temp": round(float(np.max(temps)), 2),
            "min_temp": round(float(np.min(temps)), 2),
            "avg_vibration": round(float(np.mean(vibs)), 2),
            "max_vibration": round(float(np.max(vibs)), 2),
            "avg_quality": round(float(np.mean(quality)), 1),
        }

    def process_vibration_signal(self, raw_signal):
        if not isinstance(raw_signal, list):
            return raw_signal
        window_size = 5
        filtered_signal = np.convolve(raw_signal, np.ones(window_size) / window_size, mode="same")
        return filtered_signal.tolist()


daq_system = DataAcquisitionSystem()
