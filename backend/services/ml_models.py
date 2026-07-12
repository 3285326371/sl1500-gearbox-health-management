import math
import random

import numpy as np

from models.database import FaultRecord, db


FAULT_LIBRARY = [
    {
        "type": "正常运行",
        "severity": "正常",
        "advice": "关键指标未见超限，保持日常巡检和趋势跟踪。",
        "component": "齿轮箱总成",
        "basis": "振动、油温、油液颗粒度均处于可控范围。",
    },
    {
        "type": "齿轮齿面磨损",
        "severity": "警告",
        "advice": "72 小时内复测振动趋势，取油样做铁谱/颗粒度复核，关注齿面接触斑和金属磨粒。",
        "component": "齿轮副",
        "basis": "振动能量和油液污染风险轻度升高，符合齿面早期磨损特征。",
    },
    {
        "type": "齿面点蚀/剥落",
        "severity": "严重",
        "advice": "建议降载运行并安排内窥镜检查，确认齿面点蚀、剥落范围和磁性堵塞物情况。",
        "component": "齿轮副",
        "basis": "冲击峭度、包络峰值和油液颗粒风险同步升高，疑似齿面局部损伤。",
    },
    {
        "type": "齿轮断齿",
        "severity": "严重",
        "advice": "建议立即降载或停机复核，检查啮合冲击、内窥镜图像和油液金属磨粒。",
        "component": "齿轮副",
        "basis": "周期性强冲击和振动能量显著升高，存在突发啮合损伤风险。",
    },
    {
        "type": "轴承磨损",
        "severity": "警告",
        "advice": "复测轴承测点 RMS、温升和包络谱，检查润滑油清洁度、游隙和滚道状态。",
        "component": "高速轴承",
        "basis": "振动有效值缓慢升高，但冲击特征尚未达到严重阈值。",
    },
    {
        "type": "轴承点蚀/剥落",
        "severity": "严重",
        "advice": "结合包络谱复核 120-240Hz 特征频段，必要时安排停机检查滚道和保持架。",
        "component": "高速轴承",
        "basis": "峭度、峰值因子和包络峰值升高，说明局部冲击特征明显。",
    },
    {
        "type": "高速轴承过温",
        "severity": "严重",
        "advice": "检查高速轴承润滑、游隙、冷却风路和温度测点，必要时停机复核。",
        "component": "高速轴承",
        "basis": "油温和轴承冲击风险同时偏高，可能存在高速端摩擦发热。",
    },
    {
        "type": "齿轮箱油温过高",
        "severity": "严重",
        "advice": "检查散热器、油冷风扇、三通阀、温控开关、油位和滤芯压差。",
        "component": "油冷系统",
        "basis": "油温风险超过严重阈值，冷却效率或润滑状态疑似异常。",
    },
    {
        "type": "润滑油污染/油液劣化",
        "severity": "警告",
        "advice": "取样复测 NAS 等级、水分、黏度和金属颗粒，检查滤芯、呼吸器、密封和磁性堵塞物。",
        "component": "润滑系统",
        "basis": "油液颗粒度偏高，可能降低齿轮与轴承润滑可靠性。",
    },
    {
        "type": "轴系不对中",
        "severity": "严重",
        "advice": "复核发电机与齿轮箱热态对中，检查联轴器弹性体、地脚螺栓和支撑状态。",
        "component": "联轴器/轴系",
        "basis": "低频振动能量偏高，并伴随峰值因子异常。",
    },
    {
        "type": "齿轮啮合异常",
        "severity": "警告",
        "advice": "检查啮合频率及边频带、齿侧间隙、载荷波动和齿面接触斑。",
        "component": "齿轮副",
        "basis": "振动能量、峰值因子和油液风险同步抬升，疑似啮合状态异常。",
    },
    {
        "type": "箱体或基础松动",
        "severity": "严重",
        "advice": "检查齿轮箱支座、地脚螺栓、弹性支撑和基础连接，复核水平/垂直振动差异。",
        "component": "箱体/基础",
        "basis": "宽频振动能量偏高且冲击不典型，符合安装或基础松动特征。",
    },
    {
        "type": "冷却系统故障",
        "severity": "警告",
        "advice": "检查油冷风扇电机、接触器、散热器堵塞和控制回路，确认是否切换至高速冷却。",
        "component": "油冷系统",
        "basis": "油温存在上升趋势，但冲击类振动特征尚未达到严重阈值。",
    },
]


def fault_by_type(fault_type):
    for item in FAULT_LIBRARY:
        if item["type"] == fault_type:
            return item
    return FAULT_LIBRARY[0]


def process_signals(signal_data):
    arr = np.array(signal_data, dtype=float)
    rms = float(np.sqrt(np.mean(arr ** 2)))
    peak = float(np.max(np.abs(arr)))
    mean = float(np.mean(arr))
    std = float(np.std(arr)) or 1e-6
    centered = arr - mean
    kurtosis = float(np.mean(centered ** 4) / (std ** 4))
    crest_factor = float(peak / rms) if rms > 0 else 1.0
    impulse_factor = float(peak / (np.mean(np.abs(arr)) or 1e-6))
    envelope = get_envelope(arr.tolist())
    envelope_peak = float(max(envelope)) if envelope else 0.0
    return {
        "rms": round(rms, 4),
        "kurtosis": round(kurtosis, 4),
        "peak": round(peak, 4),
        "crest_factor": round(crest_factor, 4),
        "impulse_factor": round(impulse_factor, 4),
        "envelope_peak": round(envelope_peak, 4),
    }


def get_envelope(signal_data):
    arr = np.array(signal_data, dtype=float)
    analytic_signal = arr + 1j * np.gradient(arr)
    envelope = np.abs(analytic_signal)
    return np.convolve(envelope, np.ones(5) / 5, mode="same").tolist()


def generate_demo_signal():
    t = np.linspace(0, 1, 1024)
    signal = 0.45 * np.sin(2 * math.pi * 35 * t)
    signal += 0.18 * np.sin(2 * math.pi * 120 * t)
    signal += np.random.normal(0, 0.08, size=t.shape)
    if random.random() < 0.35:
        for center in random.sample(range(80, 940), 5):
            signal[center:center + 8] += np.hanning(8) * random.uniform(0.6, 1.2)
    return signal.tolist()


def normalize(value, low, high):
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def score_risk(features, status=None):
    status = status or {}
    oil_temp = float(status.get("oil_temp", random.uniform(62, 82)))
    vibration_rms = float(status.get("vibration_rms", features["rms"] * 3.2))
    oil_quality = float(status.get("oil_quality", random.uniform(5, 11)))
    factors = {
        "振动 RMS": normalize(vibration_rms, 3.0, 7.0),
        "冲击峭度": normalize(features["kurtosis"], 3.2, 7.5),
        "峰值因子": normalize(features["crest_factor"], 2.0, 5.0),
        "包络峰值": normalize(features["envelope_peak"], 0.7, 1.8),
        "齿轮箱油温": normalize(oil_temp, 72.0, 88.0),
        "油液 NAS": normalize(oil_quality, 7.0, 12.0),
    }
    total = (
        factors["振动 RMS"] * 0.22
        + factors["冲击峭度"] * 0.24
        + factors["峰值因子"] * 0.18
        + factors["包络峰值"] * 0.14
        + factors["齿轮箱油温"] * 0.14
        + factors["油液 NAS"] * 0.08
    )
    return round(total, 4), factors, {
        "oil_temp": round(oil_temp, 2),
        "vibration_rms": round(vibration_rms, 2),
        "oil_quality": round(oil_quality, 1),
    }


def classify_fault(features, risk_score, factors, status=None):
    forced_fault_type = (status or {}).get("forced_fault_type")
    if forced_fault_type:
        return fault_by_type(forced_fault_type)
    oil_quality = float((status or {}).get("oil_quality") or 0)
    vibration = float((status or {}).get("vibration_rms") or 0)
    if factors["齿轮箱油温"] > 0.75 and factors["冲击峭度"] < 0.55:
        return fault_by_type("齿轮箱油温过高")
    if factors["齿轮箱油温"] > 0.45 and risk_score > 0.45:
        return fault_by_type("冷却系统故障")
    if oil_quality >= 10 and factors["冲击峭度"] < 0.55:
        return fault_by_type("润滑油污染/油液劣化")
    if factors["冲击峭度"] > 0.62 or factors["包络峰值"] > 0.70:
        return fault_by_type("轴承点蚀/剥落")
    if factors["振动 RMS"] > 0.72 and factors["冲击峭度"] < 0.45 and factors["齿轮箱油温"] < 0.45:
        return fault_by_type("箱体或基础松动")
    if factors["峰值因子"] > 0.58 and factors["振动 RMS"] > 0.45:
        return fault_by_type("轴系不对中")
    if vibration >= 4.5 and oil_quality >= 8:
        return fault_by_type("齿轮啮合异常")
    if risk_score > 0.38:
        return fault_by_type("齿轮齿面磨损")
    return fault_by_type("正常运行")


def calculate_health_score(risk_score, severity):
    base = 100 - risk_score * 62
    if severity == "警告":
        base -= 6
    elif severity == "严重":
        base -= 16
    return int(max(25, min(99, round(base))))


def predict_rul(health_score, risk_score, severity):
    base = 520 * (health_score / 100)
    penalty = risk_score * 130
    if severity == "严重":
        penalty += 90
    elif severity == "警告":
        penalty += 35
    return int(max(7, base - penalty))


def build_explanation(features, severity, rul, risk_score, factors, fault):
    top_factors = sorted(factors.items(), key=lambda item: item[1], reverse=True)[:3]
    risk_level = "低风险" if severity == "正常" else ("中风险" if severity == "警告" else "高风险")
    if severity == "正常":
        conclusion = "当前振动、油温和油液风险处于可控范围，按日常点检和月度趋势跟踪执行。"
    elif severity == "警告":
        conclusion = "检测到早期退化信号，建议先复测数据并结合油样、频谱和运行负荷确认趋势。"
    else:
        conclusion = "检测到明显异常特征，建议尽快安排现场复核，并根据风险准备检修窗口。"
    return {
        "risk_level": risk_level,
        "risk_score": round(risk_score * 100, 1),
        "conclusion": conclusion,
        "diagnostic_basis": fault["basis"],
        "top_risk_factors": [{"name": name, "score": round(score * 100, 1)} for name, score in top_factors],
        "feature_meaning": {
            "rms": "振动 RMS 反映整体振动能量。",
            "kurtosis": "峭度对轴承或齿面早期冲击较敏感。",
            "crest_factor": "峰值因子用于观察局部冲击和不对中风险。",
            "envelope_peak": "包络峰值用于捕捉轴承与齿面冲击调制特征。",
        },
        "rul_note": f"基于健康评分和风险因子估算齿轮箱 RUL 约 {rul} 天。",
    }


def run_diagnosis(unit_id="WTG-001", raw_signal=None, status=None):
    raw_signal = raw_signal or generate_demo_signal()
    features = process_signals(raw_signal)
    risk_score, risk_factors, operating_snapshot = score_risk(features, status)
    fault = classify_fault(features, risk_score, risk_factors, status)
    health_score = calculate_health_score(risk_score, fault["severity"])
    rul = predict_rul(health_score, risk_score, fault["severity"])
    probability = 0.72 + min(0.25, risk_score * 0.45)
    if fault["severity"] == "正常":
        probability = 0.94 + random.uniform(0, 0.04)
    explanation = build_explanation(features, fault["severity"], rul, risk_score, risk_factors, fault)
    maintenance_actions = [
        "保存本次诊断记录，并纳入周报趋势分析。",
        "对比近 7 天油温、振动 RMS、峭度、包络峰值和油液 NAS 趋势。",
        "若同类风险连续两次升高，升级为现场复检工单。",
    ]
    if fault["severity"] == "严重":
        maintenance_actions.insert(0, "24 小时内安排现场复核，必要时降载或申请停机检查窗口。")
    elif fault["severity"] == "警告":
        maintenance_actions.insert(0, "72 小时内安排振动复测和油样复检。")
    persistence = {"saved": True, "message": "诊断记录已写入故障数据表"}
    record = FaultRecord(
        unit_id=unit_id,
        fault_type=fault["type"],
        severity=fault["severity"],
        probability=probability,
        advice=fault["advice"],
        status="processed" if fault["severity"] == "正常" else "pending",
    )
    try:
        db.session.add(record)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        persistence = {"saved": False, "message": f"数据库暂时不可写，诊断结果已返回但未落库：{exc.__class__.__name__}"}
    return {
        "unit_id": unit_id,
        "fault_type": fault["type"],
        "fault_component": fault["component"],
        "probability": round(probability, 4),
        "advice": fault["advice"],
        "severity": fault["severity"],
        "features": features,
        "risk_factors": {name: round(value * 100, 1) for name, value in risk_factors.items()},
        "operating_snapshot": operating_snapshot,
        "predicted_rul_days": rul,
        "health_score": health_score,
        "explanation": explanation,
        "maintenance_actions": maintenance_actions,
        "persistence": persistence,
    }
