import numpy as np


def _kurtosis(signal):
    arr = np.array(signal, dtype=float)
    std = np.std(arr) or 1e-6
    centered = arr - np.mean(arr)
    return float(np.mean(centered ** 4) / (std ** 4))


def generate_vibration_data():
    """生成实时振动波形，并附带基础特征值。"""
    t = np.linspace(0, 1, 500)
    base_freq = np.sin(2 * np.pi * 50 * t)
    shaft_freq = 0.35 * np.sin(2 * np.pi * 12 * t)
    mesh_freq = 0.25 * np.sin(2 * np.pi * 160 * t)
    noise = np.random.normal(0, 0.16, len(t))

    signal = base_freq + shaft_freq + mesh_freq + noise
    if np.random.random() < 0.2:
        center = np.random.randint(80, 420)
        signal[center:center + 10] += np.hanning(10) * np.random.uniform(0.6, 1.0)

    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))
    return {
        "time": t.tolist(),
        "signal": signal.tolist(),
        "features": {
            "rms": round(rms, 4),
            "peak": round(peak, 4),
            "crest_factor": round(peak / rms if rms else 0, 4),
            "kurtosis": round(_kurtosis(signal), 4),
        },
        "sampling_rate_hz": 25600,
    }


def get_system_status():
    """兼容旧调用的系统状态生成函数。"""
    return {
        "oil_temp": round(np.random.uniform(60, 66), 1),
        "vibration_rms": round(np.random.uniform(2.4, 3.2), 2),
        "power": round(np.random.uniform(1180, 1230), 0),
        "alerts": 0,
    }
