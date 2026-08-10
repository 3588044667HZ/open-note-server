import sqlite3
import uuid
import time as _time
from datetime import datetime
from functools import wraps
from flask import request, jsonify, g
from config import (
    ACCOUNTS_DB, NOTES_DB, DATA_DIR, BACKUP_DIR,
    ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL, ADMIN_TOKEN_TTL
)

sessions = {}

def get_accounts_db():
    """Return the accounts database connection, creating it if needed."""
    db = getattr(g, '_accounts_db', None)
    if db is None:
        db = g._accounts_db = sqlite3.connect(ACCOUNTS_DB)
        db.row_factory = sqlite3.Row
    return db

def get_notes_db():
    """Return the notes database connection, creating it if needed."""
    db = getattr(g, '_notes_db', None)
    if db is None:
        db = g._notes_db = sqlite3.connect(NOTES_DB)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA foreign_keys=ON')
    return db

def close_db(exc=None):
    db1 = getattr(g, '_accounts_db', None)
    if db1 is not None:
        db1.close()
    db2 = getattr(g, '_notes_db', None)
    if db2 is not None:
        db2.close()

def init_db():
    import os
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

    db = sqlite3.connect(ACCOUNTS_DB)
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    db.commit()
    db.close()

    db = sqlite3.connect(NOTES_DB)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('''
        CREATE TABLE IF NOT EXISTS notebooks (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#4A90D9',
            created_at TEXT NOT NULL
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id)')
    db.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            notebook_id TEXT,
            color TEXT NOT NULL DEFAULT 'blue',
            is_pinned INTEGER NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_notes_notebook ON notes(notebook_id)')
    db.execute('''
        CREATE TABLE IF NOT EXISTS share_settings (
            user_id INTEGER PRIMARY KEY,
            logo_text TEXT NOT NULL DEFAULT '分享来自 Open Note',
            watermark TEXT NOT NULL DEFAULT '备忘录'
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS attachments (
            attach_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            note_id TEXT NOT NULL,
            type INTEGER NOT NULL DEFAULT 0,
            file_name TEXT NOT NULL DEFAULT '',
            file_id TEXT NOT NULL,
            width INTEGER NOT NULL DEFAULT 0,
            height INTEGER NOT NULL DEFAULT 0,
            md5 TEXT NOT NULL DEFAULT '',
            state INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_attachments_note ON attachments(note_id)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_attachments_user ON attachments(user_id)')
    db.commit()
    db.close()

def now_iso():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def utc_ts():
    return int(_time.time())

def generate_id(prefix='n'):
    return f'{prefix}{uuid.uuid4().hex[:10]}'

def success(data=None, extra=None):
    body = {'code': 0, 'msg': 'success', 'data': data}
    if extra:
        body.update(extra)
    return jsonify(body)

def error(msg, code=1, status=400):
    return jsonify({'code': code, 'msg': msg, 'data': None}), status

def _token_from_header():
    header = request.headers.get('Authorization', '')
    return header.replace('Bearer ', '') if header.startswith('Bearer ') else ''

def _session_valid(token):
    s = sessions.get(token)
    if not s:
        return False
    if s['expires_at'] < utc_ts():
        sessions.pop(token, None)
        return False
    return True

def _cleanup_sessions():
    now = utc_ts()
    expired = [t for t, s in sessions.items() if s['expires_at'] < now]
    for t in expired:
        sessions.pop(t, None)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _cleanup_sessions()
        token = _token_from_header()
        if not _session_valid(token):
            return error('Unauthorized', 401, 401)
        s = sessions[token]
        g.username = s['username']
        g.user_id = s['user_id']
        return f(*args, **kwargs)
    return decorated

def _create_tokens(user_id, username):
    access = uuid.uuid4().hex
    refresh = uuid.uuid4().hex
    now = utc_ts()
    sessions[access] = {
        'user_id': user_id,
        'username': username,
        'expires_at': now + ACCESS_TOKEN_TTL,
        'refresh_token': refresh,
    }
    sessions[f'refresh:{refresh}'] = {
        'user_id': user_id,
        'username': username,
        'expires_at': now + REFRESH_TOKEN_TTL,
        'access_token': access,
    }
    return access, refresh

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _cleanup_sessions()
        token = _token_from_header()
        s = sessions.get(token)
        if not s or not s.get('is_admin'):
            return error('Unauthorized', 401, 401)
        if s['expires_at'] < utc_ts():
            sessions.pop(token, None)
            return error('Token expired', 401, 401)
        return f(*args, **kwargs)
    return decorated

def create_admin_token():
    token = uuid.uuid4().hex
    sessions[token] = {
        'is_admin': True,
        'expires_at': utc_ts() + ADMIN_TOKEN_TTL,
    }
    return token

def _touch_expiry(token):
    if token in sessions:
        ttl = ADMIN_TOKEN_TTL if sessions[token].get('is_admin') else ACCESS_TOKEN_TTL
        sessions[token]['expires_at'] = utc_ts() + ttl

def note_row_to_dict(row):
    return {
        'id': row['id'],
        'title': row['title'],
        'content': row['content'],
        'notebookId': row['notebook_id'],
        'color': row['color'],
        'isPinned': bool(row['is_pinned']),
        'version': row['version'],
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
        'deletedAt': row['deleted_at'],
    }

def notebook_row_to_dict(row):
    return {
        'id': row['id'],
        'name': row['name'],
        'color': row['color'],
        'createdAt': row['created_at'],
    }

def attachment_row_to_dict(row):
    return {
        'attachId': row['attach_id'],
        'noteId': row['note_id'],
        'type': row['type'],
        'fileName': row['file_name'],
        'fileId': row['file_id'],
        'width': row['width'],
        'height': row['height'],
        'md5': row['md5'],
        'url': '',
        'state': row['state'],
        'createdAt': row['created_at'],
    }
