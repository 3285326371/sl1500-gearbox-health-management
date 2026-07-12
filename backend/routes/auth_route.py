from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import User, db

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"status": "error", "message": "请输入用户名和密码。"}), 400

    user = User.query.filter_by(username=username).first()
    password_ok = False

    if user:
        try:
            password_ok = check_password_hash(user.password, password)
        except ValueError:
            password_ok = False

        if not password_ok and user.password == password:
            password_ok = True
            user.password = generate_password_hash(password)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    if user and password_ok:
        return jsonify({
            "status": "success",
            "user": {"username": user.username, "role": user.role},
        })

    return jsonify({"status": "error", "message": "用户名或密码错误。"}), 401


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "operator")

    if not username or not password:
        return jsonify({"status": "error", "message": "请填写用户名和密码。"}), 400

    if role not in ["admin", "operator"]:
        return jsonify({"status": "error", "message": "无效的用户角色。"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"status": "error", "message": "用户名已存在。"}), 400

    db.session.add(User(username=username, password=generate_password_hash(password), role=role))
    db.session.commit()

    return jsonify({"status": "success", "message": "注册成功。"})
