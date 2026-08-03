import os
from flask import request, g, send_from_directory, abort
from config import STATIC_DESKTOP, STATIC_MOBILE, STATIC_ADMIN, MOBILE_UA_KEYWORDS


def detect_device():
    ua = request.user_agent.string.lower()
    g.is_mobile = any(kw in ua for kw in MOBILE_UA_KEYWORDS)


def _send_admin(path):
    if not path:
        return send_from_directory(STATIC_ADMIN, 'index.html')
    full = os.path.join(STATIC_ADMIN, path)
    if os.path.isfile(full):
        return send_from_directory(STATIC_ADMIN, path)
    return send_from_directory(STATIC_ADMIN, 'index.html')


def _send_static(path):
    base = STATIC_MOBILE if g.get('is_mobile') else STATIC_DESKTOP
    full = os.path.join(base, path)
    if os.path.isfile(full):
        return send_from_directory(base, path)
    return send_from_directory(base, 'index.html')


def register_frontend_routes(app):

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path == 'admin' or path.startswith('admin/'):
            if os.path.isdir(STATIC_ADMIN):
                sub = path[6:] if path.startswith('admin/') else ''
                return _send_admin(sub)
            return abort(404)

        base = STATIC_MOBILE if g.get('is_mobile') else STATIC_DESKTOP
        if not os.path.isdir(base):
            return abort(404)
        if not path:
            return send_from_directory(base, 'index.html')
        return _send_static(path)
