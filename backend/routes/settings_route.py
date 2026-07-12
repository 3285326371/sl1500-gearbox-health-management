from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from models.database import SystemConfig, User, db

settings_bp = Blueprint("settings_bp", __name__)

ALLOWED_CONFIGS = {
    "temp_warning_threshold": "齿轮箱油温关注阈值(°C)",
    "vibration_critical_threshold": "振动 RMS 告警阈值(mm/s)",
    "oil_warning_threshold": "油液颗粒度关注阈值(NAS)",
    "temp_threshold": "最高油温告警阈值(°C)",
    "vibration_threshold": "最大振动烈度阈值(mm/s)",
    "oil_quality_threshold": "油液颗粒度预警阈值(NAS)",
}

CONFIG_RANGES = {
    "temp_warning_threshold": (40, 120),
    "vibration_critical_threshold": (0.5, 20),
    "oil_warning_threshold": (1, 16),
    "temp_threshold": (40, 120),
    "vibration_threshold": (0.5, 20),
    "oil_quality_threshold": (1, 16),
}


@settings_bp.route("/configs", methods=["GET"])
def get_configs():
    configs = SystemConfig.query.all()
    values = {config.config_key: config.config_value for config in configs}
    return jsonify({
        "temp_warning_threshold": values.get("temp_warning_threshold", "75"),
        "vibration_critical_threshold": values.get("vibration_critical_threshold", "7.1"),
        "oil_warning_threshold": values.get("oil_warning_threshold", "8"),
        "temp_threshold": values.get("temp_threshold", "85"),
        "vibration_threshold": values.get("vibration_threshold", "4.5"),
        "oil_quality_threshold": values.get("oil_quality_threshold", "10"),
    })


@settings_bp.route("/configs", methods=["POST"])
def update_configs():
    data = request.json or {}
    existing = {config.config_key: config.config_value for config in SystemConfig.query.all()}
    defaults = {
        "temp_warning_threshold": "75",
        "temp_threshold": "85",
        "vibration_threshold": "4.5",
        "vibration_critical_threshold": "7.1",
        "oil_warning_threshold": "8",
        "oil_quality_threshold": "10",
    }
    candidate = {**defaults, **existing, **{key: value for key, value in data.items() if key in ALLOWED_CONFIGS}}
    threshold_pairs = [
        ("temp_warning_threshold", "temp_threshold"),
        ("vibration_threshold", "vibration_critical_threshold"),
        ("oil_warning_threshold", "oil_quality_threshold"),
    ]
    for warning_key, critical_key in threshold_pairs:
        try:
            warning_value = float(candidate.get(warning_key, 0))
            critical_value = float(candidate.get(critical_key, 0))
        except (TypeError, ValueError):
            continue
        if warning_value >= critical_value:
            return jsonify({"status": "error", "message": "关注阈值必须小于告警阈值。"}), 400
    updated = {}
    for key, value in data.items():
        if key not in ALLOWED_CONFIGS:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": f"{ALLOWED_CONFIGS[key]} 必须是数字。"}), 400

        min_value, max_value = CONFIG_RANGES[key]
        if not min_value <= numeric_value <= max_value:
            return jsonify({
                "status": "error",
                "message": f"{ALLOWED_CONFIGS[key]} 应在 {min_value:g} 到 {max_value:g} 之间。",
            }), 400

        config = SystemConfig.query.filter_by(config_key=key).first()
        if not config:
            config = SystemConfig(config_key=key, description=ALLOWED_CONFIGS[key])
            db.session.add(config)
        config.config_value = str(value)
        updated[key] = str(value)

    db.session.commit()
    return jsonify({"status": "success", "message": "系统参数已更新。", "configs": updated})


@settings_bp.route("/users", methods=["GET"])
def get_users():
    users = User.query.order_by(User.role, User.username).all()
    return jsonify([{"username": user.username, "role": user.role} for user in users])


@settings_bp.route("/users", methods=["POST"])
def add_user():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "operator")

    if not username or not password:
        return jsonify({"status": "error", "message": "请填写用户名和密码。"}), 400

    if role not in ["admin", "operator"]:
        return jsonify({"status": "error", "message": "无效的用户角色。"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"status": "error", "message": "用户已存在。"}), 400

    db.session.add(User(username=username, password=generate_password_hash(password), role=role))
    db.session.commit()
    return jsonify({"status": "success", "message": "用户已添加。"})


@settings_bp.route("/users/<username>", methods=["DELETE"])
def delete_user(username):
    if username == "admin":
        return jsonify({"status": "error", "message": "不能删除系统默认管理员。"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "error", "message": "找不到该用户。"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success", "message": "用户已删除。"})


@settings_bp.route("/users/<username>/role", methods=["PUT"])
def update_user_role(username):
    data = request.json or {}
    new_role = data.get("role")

    if username == "admin":
        return jsonify({"status": "error", "message": "不能修改系统默认管理员权限。"}), 400

    if new_role not in ["admin", "operator"]:
        return jsonify({"status": "error", "message": "无效的角色权限类型。"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"status": "error", "message": "找不到该用户。"}), 404

    user.role = new_role
    db.session.commit()
    return jsonify({"status": "success", "message": "用户权限已更新。"})
