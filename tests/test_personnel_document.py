import tempfile
import unittest
from pathlib import Path
from docx import Document
from personnel_document import export_personnel
from personnel_fields import COLLECTIONS


class ProfileStub:
    def list_records(self, table, pid):
        assert pid == 7
        return [{field.key: 'Проверка ' + field.key for field in COLLECTIONS[table][1] if field.kind != 'date'}]


class DocumentTests(unittest.TestCase):
    def test_export_contains_sections_and_saved_records(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'result.docx'
            export_personnel(path, dict(id=7,full_name='Иванов Иван Иванович',birth_date='1990-01-02'),
                             ProfileStub(), [dict(event_kind='Благодарность',removal_comment='Снятие')],
                             [dict(event_type='Перевод',new_unit='Новое подразделение')])
            document = Document(path)
            text = '\n'.join(p.text for p in document.paragraphs)
            for value in ('Иванов Иван Иванович','02.01.1990','Благодарность','Новое подразделение','Снятие'):
                self.assertIn(value,text)
            for title, fields in COLLECTIONS.values():
                self.assertIn(title,text)
                for field in fields:
                    self.assertIn(field.label,text)
            self.assertEqual(list(Path(folder).iterdir()),[path])

    def test_failed_export_preserves_existing_file(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'existing.docx'
            path.write_bytes(b'original')
            with patch('docx.document.Document.save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    export_personnel(path,dict(id=7,full_name='Тест'),ProfileStub(),[],[])
            self.assertEqual(path.read_bytes(),b'original')
            self.assertEqual(list(Path(folder).iterdir()),[path])
