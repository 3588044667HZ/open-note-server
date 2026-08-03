from flask import Blueprint, request
from app.database import (
    get_accounts_db, get_notes_db, now_iso, success, error,
    require_admin, create_admin_token, note_row_to_dict
)
from config import ADMIN_PASSWORD, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.backup import remove_backup
import os

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '').strip()
    if not password:
        return error('Password is required')
    if password != ADMIN_PASSWORD:
        return error('Invalid password', status=401)
    token = create_admin_token()
    return success({'token': token, 'expiresIn': 7200})


@admin_bp.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    accounts_db = get_accounts_db()
    notes_db = get_notes_db()

    user_count = accounts_db.execute('SELECT COUNT(*) as cnt FROM users').fetchone()['cnt']
    note_count = notes_db.execute('SELECT COUNT(*) as cnt FROM notes WHERE deleted_at IS NULL').fetchone()['cnt']
    trash_count = notes_db.execute('SELECT COUNT(*) as cnt FROM notes WHERE deleted_at IS NOT NULL').fetchone()['cnt']

    rows = notes_db.execute('SELECT COALESCE(SUM(LENGTH(content)), 0) as total_size FROM notes').fetchone()
    total_size = rows['total_size']

    return success({
        'userCount': user_count,
        'noteCount': note_count,
        'trashCount': trash_count,
        'totalContentSize': total_size,
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    size = min(MAX_PAGE_SIZE, max(1, int(request.args.get('size', DEFAULT_PAGE_SIZE))))

    accounts_db = get_accounts_db()
    notes_db = get_notes_db()

    params = []
    where = ''
    if keyword:
        where = 'WHERE u.username LIKE ?'
        params.append(f'%{keyword}%')

    count_sql = f'SELECT COUNT(*) as cnt FROM users u {where}'
    count = accounts_db.execute(count_sql, params).fetchone()['cnt']

    users_sql = f'SELECT u.id, u.username, u.created_at FROM users u {where} ORDER BY u.id ASC LIMIT ? OFFSET ?'
    rows = accounts_db.execute(users_sql, params + [size, (page - 1) * size]).fetchall()

    users = []
    for r in rows:
        note_cnt = notes_db.execute(
            'SELECT COUNT(*) as cnt FROM notes WHERE user_id = ? AND deleted_at IS NULL', (r['id'],)
        ).fetchone()['cnt']
        users.append({
            'id': r['id'],
            'username': r['username'],
            'createdAt': r['created_at'],
            'noteCount': note_cnt,
        })

    return success(users, extra={
        'pagination': {
            'page': page, 'size': size, 'total': count,
            'totalPages': max(1, (count + size - 1) // size),
        }
    })


@admin_bp.route('/api/admin/users', methods=['POST'])
@require_admin
def admin_create_user():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or len(username) < 2:
        return error('Username must be at least 2 characters')
    if not password or len(password) < 3:
        return error('Password must be at least 3 characters')

    accounts_db = get_accounts_db()
    existing = accounts_db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return error('Username already exists')

    accounts_db.execute(
        'INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
        (username, password, now_iso())
    )
    accounts_db.commit()
    user = accounts_db.execute('SELECT id, username, created_at FROM users WHERE username = ?', (username,)).fetchone()
    return success({
        'id': user['id'],
        'username': user['username'],
        'createdAt': user['created_at'],
        'noteCount': 0,
    })


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def admin_delete_user(user_id):
    accounts_db = get_accounts_db()
    notes_db = get_notes_db()

    user = accounts_db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return error('User not found')

    note_rows = notes_db.execute('SELECT id FROM notes WHERE user_id = ?', (user_id,)).fetchall()
    for nr in note_rows:
        remove_backup(user['username'], nr['id'])

    notes_db.execute('DELETE FROM notes WHERE user_id = ?', (user_id,))
    notes_db.execute('DELETE FROM notebooks WHERE user_id = ?', (user_id,))
    notes_db.execute('DELETE FROM share_settings WHERE user_id = ?', (user_id,))
    notes_db.commit()

    accounts_db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    accounts_db.commit()

    backup_dir = os.path.join('backup', user['username'])
    if os.path.isdir(backup_dir):
        try:
            for f in os.listdir(backup_dir):
                os.remove(os.path.join(backup_dir, f))
            os.rmdir(backup_dir)
        except OSError:
            pass

    return success(None)


@admin_bp.route('/api/admin/users/<int:user_id>/password', methods=['PUT'])
@require_admin
def admin_reset_password(user_id):
    data = request.get_json(silent=True) or {}
    new_password = data.get('password', '').strip()
    if not new_password or len(new_password) < 3:
        return error('Password must be at least 3 characters')

    accounts_db = get_accounts_db()
    user = accounts_db.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return error('User not found')

    accounts_db.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
    accounts_db.commit()
    return success(None)


@admin_bp.route('/api/admin/notes', methods=['GET'])
@require_admin
def admin_notes():
    user_id = request.args.get('userId', '').strip()
    keyword = request.args.get('keyword', '').strip()
    include_trash = request.args.get('includeTrash', '').lower() == 'true'
    page = max(1, int(request.args.get('page', 1)))
    size = min(MAX_PAGE_SIZE, max(1, int(request.args.get('size', DEFAULT_PAGE_SIZE))))

    notes_db = get_notes_db()
    accounts_db = get_accounts_db()

    conditions = []
    params = []

    if user_id:
        conditions.append('n.user_id = ?')
        params.append(int(user_id))
    if keyword:
        conditions.append('(n.title LIKE ? OR n.content LIKE ?)')
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    if not include_trash:
        conditions.append('n.deleted_at IS NULL')

    where = ' AND '.join(conditions) if conditions else '1=1'

    count = notes_db.execute(f'SELECT COUNT(*) as cnt FROM notes n WHERE {where}', params).fetchone()['cnt']

    rows = notes_db.execute(
        f'SELECT n.* FROM notes n WHERE {where} ORDER BY n.updated_at DESC LIMIT ? OFFSET ?',
        params + [size, (page - 1) * size]
    ).fetchall()

    user_ids = list(set(r['user_id'] for r in rows))
    usernames = {}
    if user_ids:
        placeholders = ','.join('?' * len(user_ids))
        user_rows = accounts_db.execute(
            f'SELECT id, username FROM users WHERE id IN ({placeholders})', user_ids
        ).fetchall()
        usernames = {r['id']: r['username'] for r in user_rows}

    notes = []
    for r in rows:
        note = note_row_to_dict(r)
        note['username'] = usernames.get(r['user_id'], 'unknown')
        notes.append(note)

    return success(notes, extra={
        'pagination': {
            'page': page, 'size': size, 'total': count,
            'totalPages': max(1, (count + size - 1) // size),
        }
    })


@admin_bp.route('/api/admin/notes/<note_id>', methods=['DELETE'])
@require_admin
def admin_delete_note(note_id):
    notes_db = get_notes_db()
    accounts_db = get_accounts_db()

    row = notes_db.execute('SELECT * FROM notes WHERE id = ?', (note_id,)).fetchone()
    if not row:
        return error('Note not found')

    user = accounts_db.execute('SELECT username FROM users WHERE id = ?', (row['user_id'],)).fetchone()
    username = user['username'] if user else 'unknown'
    remove_backup(username, note_id)

    notes_db.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    notes_db.commit()
    return success(None)
