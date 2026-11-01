from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from database import connection
from database.schema import init_database
from database.seed import seed_database
from database.repositories import PersonnelRepository
from database.profile_repository import ProfileRepository
from database.discipline_repository import DisciplineRepository, REMOVAL_REWARD
from database.personnel_editor import PersonnelEditorSession


class PersonnelEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp.name)/'editor.db'
        init_database()
        seed_database()
        self.sessions = []
        self.people = PersonnelRepository()
        self.profile = ProfileRepository()
        self.discipline = DisciplineRepository()

    def tearDown(self):
        for session in self.sessions:
            session.close()
        connection.DATABASE_PATH = self.previous
        self.temp.cleanup()

    def editor(self, personnel_id=None):
        session = PersonnelEditorSession(personnel_id)
        self.sessions.append(session)
        return session

    def values(self, **overrides):
        values = dict(full_name='Тестовый Сотрудник', service_status='Служит')
        values.update(overrides)
        return values

    def event(self, repository, personnel_id, **overrides):
        values = dict(personnel_id=personnel_id, event_type='Взыскание', event_kind='Выговор',
                      authority_name='НО', event_date='2026-01-01', document_number='1', basis='', comment='')
        values.update(overrides)
        return repository.create(**values)

    def test_cancel_new_person_with_related_records_writes_nothing(self):
        session = self.editor()
        session.profile.save_record('family_members', session.personnel_id, dict(relation='Сын', full_name='Ребёнок'))
        self.event(session.discipline, session.personnel_id)
        self.assertTrue(session.has_record_changes())
        self.assertEqual(self.people.get_all(), [])
        session.close()
        with closing(connection.get_connection()) as conn:
            for table in ('personnel', 'family_members', 'disciplinary_events', 'service_history'):
                self.assertEqual(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)

    def test_new_person_all_sections_saved_together(self):
        session = self.editor()
        pid = session.personnel_id
        for n in range(2):
            session.profile.save_record('family_members', pid, dict(relation='Дочь', full_name=f'Ребёнок {n}'))
            session.profile.save_record('education_records', pid, dict(level='Высшее', institution=f'Институт {n}'))
        session.profile.save_record('personal_vehicles', pid, dict(model='Автомобиль', plate='ТЕСТ', license_expiry='01.01.2030'))
        session.profile.save_record('personal_loans', pid, dict(lender='Банк', amount='100000', status='Действует'))
        session.profile.save_record('personnel_deadlines', pid, dict(title='Аттестация', category='Военная служба', due_date='01.02.2027', status='Открыто'))
        self.event(session.discipline, pid)
        durable = session.save(self.values(personal_number='Т-1', phone='123', birth_place='Город',
                                           military_id='У-1', contract_start_date='01.01.2026', contract_end_date='01.01.2028'))
        person = self.people.get_by_id(durable)
        self.assertEqual(person['phone'], '123')
        self.assertEqual(person['birth_place'], 'Город')
        self.assertEqual(person['military_id'], 'У-1')
        self.assertEqual(person['contract_end_date'], '2028-01-01')
        for table, expected in [('family_members',2),('education_records',2),('personal_vehicles',1),('personal_loans',1),('personnel_deadlines',1)]:
            self.assertEqual(len(self.profile.list_records(table, durable)), expected)
        self.assertEqual(len(self.discipline.get_personnel_history(durable)), 1)
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM service_history WHERE personnel_id=?', (durable,)).fetchone()[0], 1)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_id_remapping_after_other_person_added_and_linked_reward(self):
        session = self.editor()
        penalty = self.event(session.discipline, session.personnel_id)
        self.event(session.discipline, session.personnel_id, event_type='Поощрение', event_kind=REMOVAL_REWARD, removed_event_id=penalty, event_date='2026-02-01')
        other = self.people.create('Другой человек')
        other_penalty = self.event(self.discipline, other)
        durable = session.save(self.values())
        self.assertNotEqual(durable, session.personnel_id)
        rows = self.discipline.get_personnel_history(durable)
        reward = next(r for r in rows if r['event_type'] == 'Поощрение')
        saved_penalty = next(r for r in rows if r['event_type'] == 'Взыскание')
        self.assertEqual(reward['linked_penalty_id'], saved_penalty['id'])
        self.assertEqual(saved_penalty['status'], 'Снято')
        self.assertNotEqual(saved_penalty['id'], other_penalty)
        self.assertEqual(self.discipline.get_by_id(other_penalty)['status'], 'Активно')

    def test_edit_and_delete_related_records_preserve_ids_and_other_people(self):
        pid = self.people.create('Существующий')
        other = self.people.create('Другой')
        first = self.profile.save_record('family_members', pid, dict(relation='Отец', full_name='Первый'))
        second = self.profile.save_record('family_members', pid, dict(relation='Мать', full_name='Вторая'))
        self.profile.save_record('family_members', other, dict(relation='Брат', full_name='Чужой'))
        session = self.editor(pid)
        session.profile.save_record('family_members', pid, dict(relation='Отец', full_name='Изменённый'), first)
        session.profile.delete_record('family_members', pid, second)
        session.save(self.values(full_name='Новое ФИО'))
        rows = self.profile.list_records('family_members', pid)
        self.assertEqual([r['id'] for r in rows], [first])
        self.assertEqual(rows[0]['full_name'], 'Изменённый')
        self.assertEqual(len(self.profile.list_records('family_members', other)), 1)

    def test_cancel_existing_disciplines_does_not_remove_real_penalty(self):
        pid = self.people.create('Существующий')
        penalty = self.event(self.discipline, pid)
        session = self.editor(pid)
        session.discipline.remove_penalty(penalty, '2026-02-01', '2', '', '')
        session.close()
        self.assertEqual(self.discipline.get_by_id(penalty)['status'], 'Активно')

    def test_existing_penalty_removal_and_reward_commit_together(self):
        pid = self.people.create('Существующий')
        penalty = self.event(self.discipline, pid)
        session = self.editor(pid)
        self.event(session.discipline, pid, event_type='Поощрение', event_kind=REMOVAL_REWARD, removed_event_id=penalty, event_date='2026-02-01')
        self.assertEqual(self.discipline.get_by_id(penalty)['status'], 'Активно')
        session.save(self.values(full_name='Существующий'))
        self.assertEqual(self.discipline.get_by_id(penalty)['status'], 'Снято')
        self.assertEqual(len(self.discipline.get_personnel_history(pid)), 2)

    def test_validation_failure_leaves_draft_and_database_intact(self):
        session = self.editor()
        session.profile.save_record('family_members', session.personnel_id, dict(relation='Сын', full_name='Ребёнок'))
        with self.assertRaises(ValueError):
            session.save(self.values(birth_date='31.02.2026'))
        self.assertEqual(self.people.get_all(), [])
        self.assertEqual(len(session.profile.list_records('family_members', session.personnel_id)), 1)
        session.save(self.values())
        self.assertEqual(len(self.people.get_all()), 1)

    def test_duplicate_number_does_not_save_any_sections(self):
        self.people.create('Другой', personal_number='Т-1')
        session = self.editor()
        session.profile.save_record('personal_loans', session.personnel_id, dict(lender='Банк', status='Действует'))
        with self.assertRaises(ValueError): session.save(self.values(personal_number='Т-1'))
        self.assertEqual(len(self.people.get_all()), 1)
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM personal_loans').fetchone()[0], 0)

    def test_database_failure_rolls_back_every_section(self):
        session = self.editor()
        session.profile.save_record('family_members', session.personnel_id, dict(relation='Сын', full_name='Ребёнок'))
        with closing(connection.get_connection()) as conn, conn:
            conn.execute("CREATE TRIGGER fail_history BEFORE INSERT ON service_history BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): session.save(self.values())
        self.assertFalse(session.saved)
        self.assertEqual(self.people.get_all(), [])
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM family_members').fetchone()[0], 0)

    def test_concurrent_changes_are_not_overwritten(self):
        pid = self.people.create('Начальное имя')
        session = self.editor(pid)
        session.profile.save_record('family_members', pid, dict(relation='Сын', full_name='Ребёнок'))
        self.people.change_status(pid, 'Отпуск')
        with self.assertRaises(ValueError): session.save(self.values())
        self.assertEqual(self.people.get_by_id(pid)['service_status'], 'Отпуск')
        self.assertEqual(self.profile.list_records('family_members', pid), [])

    def test_service_history_saved_once_with_actual_dates(self):
        pid = self.people.create('Имя', rank_id=1)
        session = self.editor(pid)
        session.save(self.values(rank_id=2, rank_date='01.02.2026'))
        with closing(connection.get_connection()) as conn:
            rows = conn.execute('SELECT * FROM service_history WHERE personnel_id=?', (pid,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event_type'], 'Присвоение звания')
        self.assertEqual(rows[0]['event_date'], '2026-02-01')
        self.assertEqual(rows[0]['old_rank_id'], 1)
        self.assertEqual(rows[0]['new_rank_id'], 2)
        with self.assertRaises(ValueError): session.save(self.values())


if __name__ == '__main__':
    unittest.main()
