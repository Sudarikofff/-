"""Exercise reference deletion across real application process restarts."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
START_APPLICATION = '''
import sys
from types import ModuleType
from unittest.mock import Mock

# Run the production startup, replacing only the graphical event loop.
ui_app = ModuleType('ui.app')
ui_app.CadryApp = Mock()
sys.modules['ui.app'] = ui_app
from main import main
main()
'''


class ReferencePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'references.db'
        self.env = dict(os.environ, DISCIPLINE_DB_PATH=str(self.path), PYTHONPATH=str(PROJECT))

    def run_python(self, code):
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=self.temp.name, env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def delete_references(self):
        # Use the same repository methods as the reference screen.
        self.run_python('''
from database.repositories import ReferenceRepository
repo = ReferenceRepository()
for table in ('units', 'positions', 'ranks', 'authorities'):
    for row in repo.get_reference(table):
        repo.delete_reference(table, row['id'])
for row in repo.get_event_kinds():
    repo.delete_event_kind(row['id'])
''')

    def assert_references_empty(self):
        with sqlite3.connect(self.path) as conn:
            for table in ('units', 'positions', 'ranks', 'authorities', 'event_kinds'):
                with self.subTest(table=table):
                    self.assertEqual(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)

    def test_deleted_references_stay_deleted_after_restarts(self):
        self.run_python(START_APPLICATION)
        with sqlite3.connect(self.path) as conn:
            for table in ('ranks', 'authorities', 'event_kinds'):
                self.assertGreater(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)
        self.delete_references()
        self.assert_references_empty()
        for _ in range(2):
            self.run_python(START_APPLICATION)
            self.assert_references_empty()

    def test_legacy_database_keeps_deleted_references_on_upgrade(self):
        self.run_python(START_APPLICATION)
        self.delete_references()
        with sqlite3.connect(self.path) as conn:
            conn.execute('DROP TABLE seed_history')
        for _ in range(2):
            self.run_python(START_APPLICATION)
            self.assert_references_empty()
