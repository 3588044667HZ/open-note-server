from flask import Blueprint, request, g
from app.database import (
    get_notes_db, success, error,
    require_auth, _token_from_header, _touch_expiry
)
from config import SHARE_DEFAULT_LOGO_TEXT, SHARE_DEFAULT_WATERMARK

settings_bp = Blueprint('settings', __name__)


def _get_share_settings(user_id):
    db = get_notes_db()
    row = db.execute('SELECT * FROM share_settings WHERE user_id = ?', (user_id,)).fetchone()
    if row:
        return {'logoText': row['logo_text'], 'watermark': row['watermark']}
    return {'logoText': SHARE_DEFAULT_LOGO_TEXT, 'watermark': SHARE_DEFAULT_WATERMARK}


@settings_bp.route('/api/settings/share', methods=['GET'])
@require_auth
def get_share_settings():
    _touch_expiry(_token_from_header())
    return success(_get_share_settings(g.user_id))


@settings_bp.route('/api/settings/share', methods=['PUT'])
@require_auth
def update_share_settings():
    _touch_expiry(_token_from_header())
    data = request.get_json(silent=True) or {}
    current = _get_share_settings(g.user_id)
    if 'logoText' in data:
        current['logoText'] = data['logoText']
    if 'watermark' in data:
        current['watermark'] = data['watermark']

    db = get_notes_db()
    db.execute(
        'INSERT OR REPLACE INTO share_settings (user_id, logo_text, watermark) VALUES (?, ?, ?)',
        (g.user_id, current['logoText'], current['watermark'])
    )
    db.commit()
    return success(current)
