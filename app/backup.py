import json
import os
from config import BACKUP_DIR


def _backup_path(username, note_id):
    user_dir = os.path.join(BACKUP_DIR, username)
    return user_dir, os.path.join(user_dir, f'{note_id}.txt')


def backup_note(username, note):
    user_dir, filepath = _backup_path(username, note['id'])
    os.makedirs(user_dir, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(note, f, ensure_ascii=False, indent=2)


def remove_backup(username, note_id):
    _, filepath = _backup_path(username, note_id)
    if os.path.exists(filepath):
        os.remove(filepath)
