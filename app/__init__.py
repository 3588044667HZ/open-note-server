from flask import Flask, jsonify
from flask_cors import CORS
from app.database import init_db, close_db
from app.frontend import register_frontend_routes


def create_app():
    app = Flask(__name__)
    CORS(app)

    init_db()

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    from app.auth import auth_bp
    from app.notebooks import notebooks_bp
    from app.notes import notes_bp
    from app.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(notebooks_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(settings_bp)

    from app.frontend import detect_device
    app.before_request(detect_device)

    register_frontend_routes(app)

    app.teardown_appcontext(close_db)

    return app
