import os
import webbrowser
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS


def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    CORS(app)
    

    project_root = Path(app.root_path).resolve().parent
    instance_dir = project_root / 'instance'
    instance_dir.mkdir(exist_ok=True)
    database_path = instance_dir / 'gearbox_system.db'

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{database_path.as_posix()}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from models.database import init_db
    init_db(app)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/health')
    def health():
        return jsonify({
            "status": "ok",
            "service": "SL1500 gearbox health system",
            "database": str(database_path)
        })

    from routes.qa_route import qa_bp
    from routes.data_route import data_bp
    from routes.auth_route import auth_bp
    from routes.settings_route import settings_bp
    from routes.report_route import report_bp
    from routes.windfarm_route import windfarm_bp
    from routes.ops_route import ops_bp

    app.register_blueprint(qa_bp, url_prefix='/api/qa')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(windfarm_bp, url_prefix='/api/windfarm')
    app.register_blueprint(ops_bp, url_prefix='/api/ops')

    return app


if __name__ == '__main__':
    app = create_app()

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        url = "http://127.0.0.1:5000"
        print(f"Opening browser: {url}")
        webbrowser.open(url)

    print("Starting server at http://127.0.0.1:5000")
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(debug=debug, host='127.0.0.1', port=5000)
