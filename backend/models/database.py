from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="operator")


class FaultRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    fault_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    probability = db.Column(db.Float)
    advice = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")


class FaultClosure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_ref = db.Column(db.String(120), unique=True, nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    unit_id = db.Column(db.String(50), nullable=False)
    fault_type = db.Column(db.String(120), default="")
    owner = db.Column(db.String(80), default="")
    action = db.Column(db.String(120), default="")
    result = db.Column(db.String(120), default="")
    note = db.Column(db.Text, default="")
    closed_at = db.Column(db.DateTime, default=datetime.utcnow)


class TurbineAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(50), unique=True, nullable=False)
    number = db.Column(db.Integer, unique=True, nullable=False)
    model = db.Column(db.String(80), default="SL1500")
    location = db.Column(db.String(120), default="")
    status = db.Column(db.String(20), default="normal")
    design_life_years = db.Column(db.Integer, default=20)
    commissioned_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False)
    config_value = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))


def init_db(app):
    db.init_app(app)
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        db.create_all()

        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password=generate_password_hash("admin"), role="admin")
            db.session.add(admin)

        default_configs = [
            ("temp_warning_threshold", "75", "齿轮箱油温关注阈值(°C)"),
            ("vibration_critical_threshold", "7.1", "振动 RMS 告警阈值(mm/s)"),
            ("oil_warning_threshold", "8", "油液颗粒度关注阈值(NAS)"),
            ("temp_threshold", "85", "齿轮箱油温告警阈值(°C)"),
            ("vibration_threshold", "4.5", "振动 RMS 预警阈值(mm/s)"),
            ("oil_quality_threshold", "10", "油液颗粒度预警阈值(NAS)"),
        ]
        for key, val, desc in default_configs:
            if not SystemConfig.query.filter_by(config_key=key).first():
                db.session.add(SystemConfig(config_key=key, config_value=val, description=desc))

        db.session.commit()
