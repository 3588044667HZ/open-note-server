from flask import Blueprint, request, g
from app.database import (
    get_notes_db, now_iso, generate_id, success, error,
    require_auth, _token_from_header, _touch_expiry, note_row_to_dict
)
from app.backup import backup_note, remove_backup

notes_bp = Blueprint('notes', __name__)

COLORS = ['blue', 'green', 'yellow', 'orange', 'red', 'gray']
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@notes_bp.route('/api/notes', methods=['GET'])
@require_auth
def get_notes():
    _touch_expiry(_token_from_header())
    keyword = request.args.get('keyword', '').strip()
    notebook_id = request.args.get('notebookId', '').strip()
    color = request.args.get('color', '').strip()
    sort_by = request.args.get('sortBy', 'updatedAt').strip()
    page = max(1, int(request.args.get('page', 1)))
    size = min(MAX_PAGE_SIZE, max(1, int(request.args.get('size', DEFAULT_PAGE_SIZE))))

    if sort_by == 'createdAt':
        order_col = 'created_at'
    else:
        order_col = 'updated_at'

    db = get_notes_db()
    conditions = ['user_id = ?', 'deleted_at IS NULL']
    params = [g.user_id]

    if keyword:
        conditions.append('(title LIKE ? OR content LIKE ?)')
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    if notebook_id:
        conditions.append('notebook_id = ?')
        params.append(notebook_id)
    if color:
        conditions.append('color = ?')
        params.append(color)

    where = ' AND '.join(conditions)

    count_row = db.execute(f'SELECT COUNT(*) as cnt FROM notes WHERE {where}', params).fetchone()
    total = count_row['cnt']

    rows = db.execute(
        f'SELECT * FROM notes WHERE {where} ORDER BY is_pinned DESC, {order_col} DESC LIMIT ? OFFSET ?',
        params + [size, (page - 1) * size]
    ).fetchall()

    return success([note_row_to_dict(r) for r in rows], extra={
        'pagination': {
            'page': page,
            'size': size,
            'total': total,
            'totalPages': max(1, (total + size - 1) // size),
        }
    })


@notes_bp.route('/api/notes/sync', methods=['GET'])
@require_auth
def sync_notes():
    _touch_expiry(_token_from_header())
    since = request.args.get('since', '').strip()
    db = get_notes_db()

    if since:
        updated_rows = db.execute(
            'SELECT * FROM notes WHERE user_id = ? AND updated_at > ? AND deleted_at IS NULL',
            (g.user_id, since)
        ).fetchall()
        deleted_rows = db.execute(
            'SELECT id FROM notes WHERE user_id = ? AND deleted_at IS NOT NULL AND deleted_at > ?',
            (g.user_id, since)
        ).fetchall()
        deleted_ids = [r['id'] for r in deleted_rows]
    else:
        updated_rows = db.execute(
            'SELECT * FROM notes WHERE user_id = ? AND deleted_at IS NULL',
            (g.user_id,)
        ).fetchall()
        deleted_ids = []

    return success({
        'updated': [note_row_to_dict(r) for r in updated_rows],
        'deletedIds': deleted_ids,
        'serverTime': now_iso(),
    })


@notes_bp.route('/api/notes/<note_id>', methods=['GET'])
@require_auth
def get_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found')
    return success(note_row_to_dict(row))


@notes_bp.route('/api/notes', methods=['POST'])
@require_auth
def create_note():
    _touch_expiry(_token_from_header())
    data = request.get_json(silent=True) or {}
    note_id = generate_id('n')
    now_ts = now_iso()
    title = data.get('title', '').strip()
    content = data.get('content', '')
    notebook_id = data.get('notebookId')
    color = data.get('color', 'blue')
    is_pinned = 1 if data.get('isPinned', False) else 0

    db = get_notes_db()
    db.execute(
        '''INSERT INTO notes (id, user_id, title, content, notebook_id, color, is_pinned, version, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)''',
        (note_id, g.user_id, title, content, notebook_id, color, is_pinned, now_ts, now_ts)
    )
    db.commit()

    note = {
        'id': note_id, 'title': title, 'content': content,
        'notebookId': notebook_id, 'color': color,
        'isPinned': bool(is_pinned), 'version': 1,
        'createdAt': now_ts, 'updatedAt': now_ts, 'deletedAt': None,
    }
    backup_note(g.username, note)
    return success(note)


@notes_bp.route('/api/notes/<note_id>', methods=['PUT'])
@require_auth
def update_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found')

    client_updated_at = request.headers.get('If-Match', '')
    if client_updated_at:
        server_updated_at = row['updated_at']
        if client_updated_at != server_updated_at:
            return error(
                f'Conflict: note was modified by another device. Server version: {server_updated_at}',
                code=409,
                status=409,
            )

    data = request.get_json(silent=True) or {}
    title = data.get('title', row['title'])
    content = data.get('content', row['content'])
    notebook_id = data.get('notebookId', row['notebook_id'])
    color = data.get('color', row['color'])
    is_pinned = 1 if data.get('isPinned', row['is_pinned']) else 0
    new_version = row['version'] + 1
    now_ts = now_iso()

    db.execute(
        '''UPDATE notes SET title=?, content=?, notebook_id=?, color=?, is_pinned=?,
           version=?, updated_at=? WHERE id=? AND user_id=?''',
        (title, content, notebook_id, color, is_pinned, new_version, now_ts, note_id, g.user_id)
    )
    db.commit()

    note = {
        'id': note_id, 'title': title, 'content': content,
        'notebookId': notebook_id, 'color': color,
        'isPinned': bool(is_pinned), 'version': new_version,
        'createdAt': row['created_at'], 'updatedAt': now_ts,
        'deletedAt': row['deleted_at'],
    }
    backup_note(g.username, note)
    return success(note)


@notes_bp.route('/api/notes/<note_id>', methods=['DELETE'])
@require_auth
def delete_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found')
    now_ts = now_iso()
    new_version = row['version'] + 1
    db.execute(
        'UPDATE notes SET deleted_at=?, updated_at=?, version=? WHERE id=? AND user_id=?',
        (now_ts, now_ts, new_version, note_id, g.user_id)
    )
    db.commit()

    note = note_row_to_dict(row)
    note['deletedAt'] = now_ts
    note['updatedAt'] = now_ts
    note['version'] = new_version
    backup_note(g.username, note)
    return success(None)


@notes_bp.route('/api/notes/<note_id>/pin', methods=['PUT'])
@require_auth
def pin_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found')
    new_pinned = 0 if row['is_pinned'] else 1
    new_version = row['version'] + 1
    now_ts = now_iso()
    db.execute(
        'UPDATE notes SET is_pinned=?, version=?, updated_at=? WHERE id=? AND user_id=?',
        (new_pinned, new_version, now_ts, note_id, g.user_id)
    )
    db.commit()

    note = note_row_to_dict(row)
    note['isPinned'] = bool(new_pinned)
    note['version'] = new_version
    note['updatedAt'] = now_ts
    backup_note(g.username, note)
    return success(note)


@notes_bp.route('/api/notes/trash', methods=['GET'])
@require_auth
def get_trash_notes():
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    rows = db.execute(
        'SELECT * FROM notes WHERE user_id = ? AND deleted_at IS NOT NULL ORDER BY deleted_at DESC',
        (g.user_id,)
    ).fetchall()
    return success([note_row_to_dict(r) for r in rows])


@notes_bp.route('/api/notes/<note_id>/recover', methods=['PUT'])
@require_auth
def recover_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NOT NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found in trash')
    new_version = row['version'] + 1
    now_ts = now_iso()
    db.execute(
        'UPDATE notes SET deleted_at=NULL, updated_at=?, version=? WHERE id=? AND user_id=?',
        (now_ts, new_version, note_id, g.user_id)
    )
    db.commit()

    note = note_row_to_dict(row)
    note['deletedAt'] = None
    note['updatedAt'] = now_ts
    note['version'] = new_version
    backup_note(g.username, note)
    return success(note)


@notes_bp.route('/api/notes/<note_id>/permanent', methods=['DELETE'])
@require_auth
def permanent_delete_note(note_id):
    _touch_expiry(_token_from_header())
    db = get_notes_db()
    row = db.execute('SELECT * FROM notes WHERE id = ? AND user_id = ? AND deleted_at IS NOT NULL',
                     (note_id, g.user_id)).fetchone()
    if not row:
        return error('Note not found in trash')
    db.execute('DELETE FROM notes WHERE id = ? AND user_id = ?', (note_id, g.user_id))
    db.commit()
    remove_backup(g.username, note_id)
    return success(None)
