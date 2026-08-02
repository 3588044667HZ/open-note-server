from flask import Blueprint, request, g
from app.database import (
    get_accounts_db, get_notes_db, now_iso, success, error,
    require_auth, _token_from_header, _create_tokens, _touch_expiry,
    sessions, utc_ts
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return error('Username and password are required')
    if len(username) < 2:
        return error('Username must be at least 2 characters')
    if len(password) < 3:
        return error('Password must be at least 3 characters')
    db = get_accounts_db()
    existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return error('Username already exists')
    db.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
               (username, password, now_iso()))
    db.commit()
    return success({'username': username})


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return error('Username and password are required')
    db = get_accounts_db()
    user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                      (username, password)).fetchone()
    if not user:
        return error('Invalid username or password')
    access, refresh = _create_tokens(user['id'], user['username'])
    return success({
        'token': access,
        'refreshToken': refresh,
        'expiresIn': 3600,
        'user': {'username': user['username'], 'createdAt': user['created_at']},
    })


@auth_bp.route('/api/auth/refresh', methods=['POST'])
def refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get('refreshToken', '').strip()
    skey = f'refresh:{refresh_token}'
    s = sessions.get(skey)
    if not s or s['expires_at'] < utc_ts():
        sessions.pop(skey, None)
        return error('Refresh token expired', 401, 401)
    old_access = s['access_token']
    sessions.pop(old_access, None)
    sessions.pop(skey, None)
    access, refresh = _create_tokens(s['user_id'], s['username'])
    return success({
        'token': access,
        'refreshToken': refresh,
        'expiresIn': 3600,
    })


@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    _touch_expiry(_token_from_header())
    db = get_accounts_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (g.user_id,)).fetchone()
    if not user:
        return error('User not found')
    return success({'username': user['username'], 'createdAt': user['created_at']})


@auth_bp.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    _touch_expiry(_token_from_header())
    token = _token_from_header()
    s = sessions.pop(token, None)
    if s and s.get('refresh_token'):
        sessions.pop(f'refresh:{s["refresh_token"]}', None)
    return success(None)
