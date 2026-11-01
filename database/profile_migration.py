"""Idempotent, additive migration. Existing records and IDs are preserved."""
from contextlib import closing
from datetime import datetime
import sqlite3
from database import connection
from personnel_fields import PERSONAL, MILITARY, COLLECTIONS


def backup_before_upgrade():
    path = connection.DATABASE_PATH
    if not path.exists() or path.stat().st_size == 0:
        return
    with closing(sqlite3.connect(path)) as source:
        columns = {r[1] for r in source.execute('PRAGMA table_info(personnel)')}
        if 'contract_end_date' in columns:
            return
        target_dir = path.parent.parent / 'backup'
        target_dir.mkdir(exist_ok=True)
        target = target_dir / ('before-profile-v2-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.db')
        with closing(sqlite3.connect(target)) as dest:
            source.backup(dest)


def migrate_profile():
    with closing(connection.get_connection()) as conn, conn:
        conn.execute('BEGIN')
        columns = {r['name'] for r in conn.execute('PRAGMA table_info(personnel)')}
        for f in PERSONAL + MILITARY:
            if f.key not in columns:
                conn.execute(f'ALTER TABLE personnel ADD COLUMN {f.key} TEXT')
        for table, (_, fields) in COLLECTIONS.items():
            conn.execute(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                         'personnel_id INTEGER NOT NULL REFERENCES personnel(id))')
            columns = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
            for f in fields:
                if f.key not in columns:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {f.key} TEXT')
            conn.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_personnel ON {table}(personnel_id)')
        columns = {r['name'] for r in conn.execute('PRAGMA table_info(disciplinary_events)')}
        for name, kind in [('due_date', 'TEXT'), ('linked_penalty_id', 'INTEGER REFERENCES disciplinary_events(id)')]:
            if name not in columns:
                conn.execute(f'ALTER TABLE disciplinary_events ADD COLUMN {name} {kind}')
