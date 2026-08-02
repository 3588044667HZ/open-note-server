#!/usr/bin/env python
"""Restore notes from cold backup (.txt files) into SQLite database."""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import NOTES_DB, ACCOUNTS_DB, BACKUP_DIR


def restore():
    if not os.path.isdir(BACKUP_DIR):
        print(f'Backup directory not found: {BACKUP_DIR}')
        return

    account_db = sqlite3.connect(ACCOUNTS_DB)
    account_db.row_factory = sqlite3.Row
    notes_db = sqlite3.connect(NOTES_DB)

    restored = 0

    for username in os.listdir(BACKUP_DIR):
        user_dir = os.path.join(BACKUP_DIR, username)
        if not os.path.isdir(user_dir):
            continue
        user = account_db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            print(f'  [skip] user not found: {username}')
            continue
        user_id = user['id']

        for fname in os.listdir(user_dir):
            if not fname.endswith('.txt'):
                continue
            filepath = os.path.join(user_dir, fname)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    note = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f'  [error] reading {filepath}: {e}')
                continue

            notes_db.execute(
                '''INSERT OR REPLACE INTO notes
                   (id, user_id, title, content, notebook_id, color, is_pinned, version, created_at, updated_at, deleted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    note.get('id'),
                    user_id,
                    note.get('title', ''),
                    note.get('content', ''),
                    note.get('notebookId'),
                    note.get('color', 'blue'),
                    1 if note.get('isPinned') else 0,
                    note.get('version', 1),
                    note.get('createdAt', ''),
                    note.get('updatedAt', ''),
                    note.get('deletedAt'),
                )
            )
            restored += 1

    notes_db.commit()
    notes_db.close()
    account_db.close()
    print(f'Restored {restored} notes.')


if __name__ == '__main__':
    restore()
