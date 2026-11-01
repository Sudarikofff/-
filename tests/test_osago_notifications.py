from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from database import connection
from database.schema import init_database
from database.seed import seed_database
from database.repositories import PersonnelRepository
from database.profile_repository import ProfileRepository
from database.osago_notifications import OsagoNotifications, DEFAULT_SETTINGS, validate_settings
from database.personnel_editor import PersonnelEditorSession


class OsagoNotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = connection.DATABASE_PATH
        connection.DATABASE_PATH = Path(self.temp.name)/'notifications.db'
        init_database()
        seed_database()
        self.people = PersonnelRepository()
        self.profile = ProfileRepository()
        self.notifications = OsagoNotifications()
        self.pid = self.people.create('Тестовый Военнослужащий')
        self.today = date(2026, 10, 1)

    def tearDown(self):
        connection.DATABASE_PATH = self.previous
        self.temp.cleanup()

    def vehicle(self, days=30, **values):
        data = dict(model='Автомобиль', plate='ТЕСТ', insurance_expiry=(self.today+timedelta(days=days)).isoformat())
        data.update(values)
        return self.profile.save_record('personal_vehicles', self.pid, data)

    def rows(self, today=None):
        return self.notifications.refresh(today or self.today)['rows']

    def settings(self, **values):
        current = self.notifications.get_settings()
        current.update(values)
        return self.notifications.save_settings(current)

    def test_defaults_and_custom_settings_persist(self):
        self.assertEqual(self.notifications.get_settings(), DEFAULT_SETTINGS)
        self.settings(days='3, 14; 3 7', on_expiry=False)
        saved = OsagoNotifications().get_settings()
        self.assertEqual(saved['days'], [14, 7, 3])
        self.assertFalse(saved['on_expiry'])
        for invalid in ('-1', '0', '366', '1.5', 'завтра'):
            with self.assertRaises(ValueError): self.settings(days=invalid)
        self.assertEqual(self.notifications.get_settings(), saved)
        self.assertEqual(validate_settings({'days':''})['days'], [])

    def test_threshold_boundary_and_no_duplicates_on_restart(self):
        self.vehicle(31)
        self.assertEqual(self.rows(), [])
        row = self.rows(self.today+timedelta(days=1))[0]
        self.assertEqual(row['phase'], 'before:30')
        self.notifications.mark_read(row['id'])
        for _ in range(3):
            again = OsagoNotifications().refresh(self.today+timedelta(days=2))['rows']
            self.assertEqual(len(again), 1)
            self.assertEqual(again[0]['id'], row['id'])
            self.assertEqual(again[0]['is_read'], 1)

    def test_missed_thresholds_produce_only_current_reminder(self):
        self.vehicle(5)
        row = self.rows()[0]
        self.assertEqual(row['phase'], 'before:7')
        self.assertEqual(row['days'], 5)
        self.assertEqual(len(self.rows()), 1)

    def test_next_threshold_is_unread_without_adding_row(self):
        self.vehicle(30)
        row = self.rows()[0]
        self.notifications.mark_read(row['id'])
        new = self.rows(self.today+timedelta(days=16))[0]
        self.assertEqual(new['phase'], 'before:14')
        self.assertEqual(new['id'], row['id'])
        self.assertEqual(new['is_read'], 0)

    def test_expiry_day_and_overdue_can_be_disabled_independently(self):
        self.vehicle(0)
        self.assertEqual(self.rows()[0]['status'], 'Сегодня')
        self.settings(on_expiry=False)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.rows(self.today+timedelta(days=1))[0]['status'], 'Просрочено')
        self.settings(overdue=False)
        self.assertEqual(self.rows(self.today+timedelta(days=1)), [])

    def test_overdue_repeats_once_per_day(self):
        self.vehicle(-1)
        row = self.rows()[0]
        self.notifications.mark_read(row['id'])
        self.assertEqual(self.rows()[0]['is_read'], 1)
        following = self.rows(self.today+timedelta(days=1))[0]
        self.assertEqual(following['id'], row['id'])
        self.assertEqual(following['is_read'], 0)
        self.notifications.mark_read(row['id'])
        self.assertEqual(self.rows(self.today+timedelta(days=1))[0]['is_read'], 1)

    def test_overdue_can_remain_read_across_days(self):
        self.settings(repeat_overdue=False)
        self.vehicle(-1)
        row = self.rows()[0]
        self.notifications.mark_read(row['id'])
        self.assertEqual(self.rows(self.today+timedelta(days=4))[0]['is_read'], 1)

    def test_snooze_survives_threshold_and_resumes_on_selected_date(self):
        self.vehicle(15)
        row = self.rows()[0]
        until = self.today+timedelta(days=3)
        self.notifications.snooze(row['id'], until.isoformat(), self.today)
        self.assertTrue(self.rows(self.today+timedelta(days=1))[0]['deferred'])
        resumed = self.rows(until)[0]
        self.assertFalse(resumed['deferred'])
        self.assertEqual(resumed['is_read'], 0)
        self.assertIsNone(resumed['snoozed_until'])
        with self.assertRaises(ValueError):
            self.notifications.snooze(row['id'], self.today.isoformat(), self.today)

    def test_mark_all_read_skips_snoozed(self):
        self.vehicle(7)
        self.vehicle(10)
        first, second = self.rows()
        self.notifications.snooze(first['id'], (self.today+timedelta(days=3)).isoformat(), self.today)
        self.notifications.mark_all_read(self.today)
        self.assertEqual(next(r for r in self.rows() if r['id']==second['id'])['is_read'], 1)
        self.notifications.resume(first['id'])
        resumed = next(r for r in self.rows() if r['id']==first['id'])
        self.assertFalse(resumed['deferred'])
        self.assertEqual(resumed['is_read'], 0)

    def test_renewal_closes_old_reminder_and_schedules_new_policy(self):
        ident = self.vehicle(2)
        old = self.rows()[0]
        self.profile.save_record('personal_vehicles', self.pid,
                                 dict(model='Автомобиль', insurance_expiry=(self.today+timedelta(days=365)).isoformat()), ident)
        self.assertEqual(self.rows(), [])
        future = self.rows(self.today+timedelta(days=335))[0]
        self.assertNotEqual(future['id'], old['id'])
        self.assertEqual(future['phase'], 'before:30')

    def test_archive_and_global_disable(self):
        self.vehicle()
        self.people.change_status(self.pid, 'Архив')
        self.assertEqual(self.rows(), [])
        self.settings(include_archive=True)
        self.assertEqual(len(self.rows()), 1)
        self.settings(enabled=False)
        self.assertEqual(self.rows(), [])
        self.settings(enabled=True)
        self.assertEqual(len(self.rows()), 1)

    def test_deleted_vehicle_cascades_notifications(self):
        ident = self.vehicle()
        self.rows()
        self.profile.delete_record('personal_vehicles', self.pid, ident)
        self.assertEqual(self.rows(), [])
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM osago_notifications').fetchone()[0], 0)

    def test_missing_invalid_dates_and_other_deadlines_do_not_notify(self):
        ident = self.vehicle(insurance_expiry=None, license_expiry=self.today.isoformat())
        self.profile.save_record('personal_loans', self.pid, dict(lender='Банк', status='Действует', repayment_date=self.today.isoformat()))
        self.assertEqual(self.rows(), [])
        with closing(connection.get_connection()) as conn, conn:
            conn.execute('UPDATE personal_vehicles SET insurance_expiry=? WHERE id=?', ('неизвестно', ident))
        state = self.notifications.refresh(self.today)
        self.assertEqual(state['rows'], [])
        self.assertEqual(state['invalid_dates'], 1)

    def test_multiple_vehicles_and_migration_are_independent(self):
        self.vehicle(14)
        self.vehicle(30)
        rows = self.rows()
        self.notifications.mark_read(rows[0]['id'])
        init_database()
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(r['is_read'] for r in rows), 1)

    def test_unsaved_renewal_does_not_close_notification(self):
        ident = self.vehicle(2)
        self.rows()
        session = PersonnelEditorSession(self.pid)
        try:
            session.profile.save_record('personal_vehicles', self.pid,
                                         dict(model='Автомобиль', insurance_expiry='2030-01-01'), ident)
            self.assertEqual(len(self.rows()), 1)
        finally:
            session.close()
        self.assertEqual(len(self.rows()), 1)

    def test_notifications_do_not_conflict_with_full_card_save(self):
        self.vehicle(2)
        session = PersonnelEditorSession(self.pid)
        try:
            row = self.rows()[0]
            self.notifications.mark_read(row['id'])
            session.save(dict(full_name='Новое имя', service_status='Служит'))
        finally:
            session.close()
        self.assertEqual(self.rows()[0]['full_name'], 'Новое имя')


if __name__ == '__main__':
    unittest.main()
