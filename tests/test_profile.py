import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from database import connection
from database.schema import SCHEMA, init_database
from database.seed import seed_database
from database.repositories import PersonnelRepository
from database.profile_repository import ProfileRepository
from database.discipline_repository import DisciplineRepository, REMOVAL_REWARD
from personnel_fields import PERSONAL, MILITARY, VEHICLES, LOANS, FAMILY, validate
from ui.widgets.period_filter import filter_events
from ui.deadlines_view import filter_deadlines


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = connection.DATABASE_PATH
        folder = Path(self.temp.name)/'database'
        folder.mkdir()
        connection.DATABASE_PATH = folder/'discipline.db'
        init_database(); seed_database()
        self.people = PersonnelRepository()
        self.profile = ProfileRepository()
        self.discipline = DisciplineRepository()
        self.pid = self.people.create('Тестовый Военнослужащий', personal_number='Т-001')
        self.other = self.people.create('Тестовый Военнослужащий', personal_number='Т-002')

    def tearDown(self):
        connection.DATABASE_PATH = self.old_path
        self.temp.cleanup()

    def event(self, pid=None, **overrides):
        data = dict(personnel_id=pid or self.pid, event_type='Взыскание', event_kind='Выговор',
                    authority_name='НО', event_date='2026-10-01', document_number='Т-1', basis='Тест', comment='', status='Активно')
        data.update(overrides)
        return self.discipline.create(**data)

    def test_migration_preserves_old_records_and_backs_up(self):
        legacy = Path(self.temp.name)/'legacy'
        legacy.mkdir()
        connection.DATABASE_PATH = legacy/'old.db'
        with closing(connection.get_connection()) as conn:
            conn.executescript(SCHEMA)
            conn.execute("INSERT INTO personnel(id,full_name) VALUES (40,'Старая запись')")
            conn.execute("INSERT INTO family_members(personnel_id,relation,full_name) VALUES (40,'Мать','Существующий родственник')")
            conn.execute("INSERT INTO event_types(id,name) VALUES (10,'Поощрение'),(20,'Взыскание')")
            conn.execute("INSERT INTO event_kinds(event_type_id,name) VALUES (20,'Особый вид')")
            conn.commit()
        init_database(); seed_database(); init_database(); seed_database()
        self.assertEqual(self.people.get_by_id(40)['full_name'],'Старая запись')
        self.assertEqual(self.profile.list_records('family_members',40)[0]['full_name'],'Существующий родственник')
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM event_kinds').fetchone()[0],13)
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(len(list(Path(self.temp.name).glob('backup/before-profile-v2-*.db'))),1)

    def test_seed_does_not_restore_deleted_or_renamed_references(self):
        with closing(connection.get_connection()) as conn,conn:
            conn.execute("DELETE FROM authorities")
            conn.execute("DELETE FROM ranks")
            conn.execute("UPDATE event_kinds SET name='Моё название' WHERE name='Грамота'")
            conn.execute("DELETE FROM event_kinds WHERE name='Деньги'")
        seed_database()
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM authorities').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ranks').fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM event_kinds WHERE name IN ('Грамота','Деньги')").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM event_kinds WHERE name='Моё название'").fetchone()[0],1)

    def test_existing_database_adopts_seed_marker_without_repopulating(self):
        with closing(connection.get_connection()) as conn,conn:
            conn.execute('DROP TABLE seed_history')
            conn.execute('DELETE FROM authorities')
        seed_database(preserve_existing=True)
        seed_database()
        with closing(connection.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM authorities').fetchone()[0],0)

    def test_profile_all_fields_survive_reopen(self):
        data={f.key:'Тест' for f in PERSONAL if f.kind=='text' and not f.choices}
        data.update(full_name='Изменённое имя', birth_date='02.03.1990', residence_type='Съёмное', housing_program='НИС', housing_realized='Реализовано')
        self.profile.update_personnel(self.pid,PERSONAL,data)
        row=self.people.get_by_id(self.pid)
        self.assertEqual(row['birth_date'],'1990-03-02')
        self.assertEqual(row['housing_program'],'НИС')
        self.assertEqual(row['personal_number'],'Т-001')

    def test_multiple_children_and_educations(self):
        for n in range(3):
            self.profile.save_record('family_members',self.pid,dict(relation='Сын',full_name=f'Ребёнок {n}',birth_date='01.01.2015',workplace='Школа',education_type='Школа'))
            self.profile.save_record('education_records',self.pid,dict(level='Высшее',institution=f'Институт {n}',graduation_year='2010'))
        self.assertEqual(len(self.profile.list_records('family_members',self.pid)),3)
        self.assertEqual(len(self.profile.list_records('education_records',self.pid)),3)

    def test_record_edit_and_delete_are_scoped_to_person(self):
        ident=self.profile.save_record('family_members',self.pid,dict(relation='Отец',full_name='Родственник'))
        with self.assertRaises(ValueError):
            self.profile.save_record('family_members',self.other,dict(relation='Отец',full_name='Другой'),ident)
        self.profile.delete_record('family_members',self.other,ident)
        self.assertEqual(len(self.profile.list_records('family_members',self.pid)),1)
        self.profile.save_record('family_members',self.pid,dict(relation='Отец',full_name='Новое имя',comment='Связь не поддерживается'),ident)
        self.assertEqual(self.profile.list_records('family_members',self.pid)[0]['full_name'],'Новое имя')
        self.profile.delete_record('family_members',self.pid,ident)
        self.assertEqual(self.profile.list_records('family_members',self.pid),[])

    def test_invalid_dates_and_money(self):
        for value in ('31.02.2026','2026-99-99','не дата'):
            with self.assertRaises(ValueError): validate(FAMILY,dict(relation='Сын',full_name='Тест',birth_date=value))
        for value in ('-1','NaN','Infinity','1.001','текст'):
            with self.assertRaises(ValueError): validate(LOANS,dict(lender='Банк',amount=value,status='Действует'))
        self.assertEqual(validate(LOANS,dict(lender='Банк',amount='1 234,56',status='Действует'))['amount'],'1234.56')

    def test_reverse_contract_period_rejected(self):
        with self.assertRaises(ValueError):
            self.profile.update_personnel(self.pid,MILITARY,dict(contract_start_date='2027-01-01',contract_end_date='2026-01-01'))

    def test_blank_dates_remain_blank(self):
        self.profile.update_personnel(self.pid,MILITARY,{})
        self.assertIsNone(self.people.get_by_id(self.pid)['contract_end_date'])
        self.assertEqual(self.profile.deadlines(self.pid),[])

    def test_deadlines_aggregate_and_preserve_year_precision(self):
        self.profile.update_personnel(self.pid,MILITARY,dict(contract_end_date='2026-10-31',attestation_year='2027'))
        self.profile.save_record('personal_vehicles',self.pid,dict(model='Тестовый автомобиль',license_expiry='2026-10-30',insurance_expiry='2026-11-30'))
        self.profile.save_record('personal_loans',self.pid,dict(lender='Тестовый банк',status='Действует',repayment_date='2026-12-01',next_payment_date='2026-11-01'))
        self.profile.save_record('personnel_deadlines',self.pid,dict(title='Классность',category='Классность',due_date='2026-12-31',status='Открыто'))
        self.event(due_date='2026-11-15')
        rows=self.profile.deadlines(self.pid,today=date(2026,10,31))
        self.assertEqual(len(rows),8)
        self.assertEqual(len(filter_deadlines(rows,horizon='Просрочено')),1)
        self.assertEqual(len(filter_deadlines(rows,horizon='Сегодня')),1)
        self.assertEqual(len(filter_deadlines(rows,horizon='30 дней')),4)
        self.assertEqual(len(filter_deadlines(rows,horizon='Без точной даты')),1)
        self.assertEqual(filter_deadlines(rows,horizon='Без точной даты')[0]['due_date'],'2027')
        self.assertEqual(len(filter_deadlines(rows,start='30.11.2026',end='30.11.2026')),1)

    def test_completed_and_archive_deadlines_excluded(self):
        self.profile.save_record('personal_loans',self.pid,dict(lender='Банк',repayment_date='2026-11-01',status='Погашен'))
        self.profile.save_record('personnel_deadlines',self.pid,dict(title='Выполнено',category='Иное',due_date='2026-11-01',status='Выполнено'))
        self.assertEqual(self.profile.deadlines(self.pid),[])
        self.profile.update_personnel(self.pid,MILITARY,dict(contract_end_date='2026-11-01'))
        self.people.change_status(self.pid,'Архив')
        self.assertEqual(self.profile.deadlines(self.pid),[])
        self.assertEqual(len(self.profile.deadlines(self.pid,include_archive=True)),1)

    def test_unknown_legacy_date_visible(self):
        with closing(connection.get_connection()) as conn,conn:
            conn.execute('UPDATE personnel SET contract_end_date=? WHERE id=?',('неизвестно',self.pid))
        self.assertEqual(self.profile.deadlines(self.pid)[0]['status'],'Проверьте дату')

    def test_manual_deadline_lifecycle_and_filters(self):
        ident=self.profile.save_record('personnel_deadlines',self.pid,dict(
            title='Проверить классность',category='Классность',due_date='30.10.2026',status='Открыто',comment='Проверка'))
        self.profile.update_personnel(self.pid,MILITARY,dict(contract_end_date='2026-10-30'))
        today=date(2026,10,31)
        rows=self.profile.deadlines(self.pid,today=today)
        manual=next(r for r in rows if r['source_table']=='personnel_deadlines')
        self.assertEqual((manual['record_id'],manual['source'],manual['status']),(ident,'Добавлен вручную','Просрочено'))
        self.profile.set_deadline_completed(self.pid,ident)
        self.assertEqual(len(self.profile.deadlines(self.pid,today=today)),1)
        rows=self.profile.deadlines(self.pid,today=today,include_completed=True)
        self.assertEqual(len(filter_deadlines(rows)),1)
        completed=filter_deadlines(rows,mode='Выполненные')
        self.assertEqual(len(completed),1)
        self.assertEqual(completed[0]['status'],'Выполнено')
        self.assertEqual(len(filter_deadlines(rows,mode='Все записи')),2)
        self.profile.set_deadline_completed(self.pid,ident,False)
        self.assertEqual(len(self.profile.deadlines(self.pid,today=today)),2)
        record=self.profile.list_records('personnel_deadlines',self.pid)[0]
        self.assertEqual(record['comment'],'Проверка')
        self.profile.save_record('personnel_deadlines',self.pid,dict(record,due_date='05.11.2026'),ident)
        manual=next(r for r in self.profile.deadlines(self.pid,today=today) if r['source_table']=='personnel_deadlines')
        self.assertEqual((manual['days'],manual['status']),(5,'Предстоит'))

    def test_deadline_completion_is_scoped_to_person(self):
        ident=self.profile.save_record('personnel_deadlines',self.pid,dict(
            title='Обучение',category='Образование',due_date='2026-11-01',status='Открыто'))
        with self.assertRaises(ValueError):
            self.profile.set_deadline_completed(self.other,ident)
        self.assertEqual(self.profile.list_records('personnel_deadlines',self.pid)[0]['status'],'Открыто')
        with self.assertRaises(ValueError):
            self.profile.set_deadline_completed(self.pid,ident+100)

    def test_automatic_deadline_sources_distinguish_vehicle_dates(self):
        ident=self.profile.save_record('personal_vehicles',self.pid,dict(
            model='Автомобиль',license_expiry='2026-11-01',insurance_expiry='2026-12-01'))
        rows=self.profile.deadlines(self.pid)
        self.assertEqual({r['source_table'] for r in rows},{'personal_vehicles'})
        self.assertEqual({r['source_field'] for r in rows},{'license_expiry','insurance_expiry'})
        self.assertEqual({r['record_id'] for r in rows},{ident})
        self.assertTrue(all(r['source']=='Из карточки' and not r['completed'] for r in rows))

    def test_period_filters_inclusive_case_insensitive(self):
        self.event(event_date='2025-12-31')
        self.event(event_date='2026-01-01')
        self.event(event_date='2026-12-31')
        self.event(event_date='2027-01-01')
        rows=self.discipline.get_all()
        self.assertEqual(len(filter_events(rows,year='2026',text='тестовый',authority='НО',status='Активно')),2)
        self.assertEqual(len(filter_events(rows,start='01.01.2026',end='31.12.2026')),2)
        with self.assertRaises(ValueError): filter_events(rows,start='2026-12-31',end='2026-01-01')

    def test_reward_removal_is_atomic(self):
        penalty=self.event()
        reward=self.event(event_type='Поощрение',event_kind=REMOVAL_REWARD,removed_event_id=penalty,event_date='2026-10-20')
        self.assertEqual(self.discipline.get_by_id(penalty)['status'],'Снято')
        self.assertEqual(self.discipline.get_by_id(reward)['linked_penalty_id'],penalty)
        self.assertEqual(self.discipline.get_personnel_statistics(self.pid)['active_penalties'],0)
        with self.assertRaises(ValueError):
            self.event(event_type='Поощрение',event_kind=REMOVAL_REWARD,removed_event_id=penalty)
        self.assertEqual(len(self.discipline.get_all()),2)

    def test_removal_rejects_wrong_person_without_partial_insert(self):
        penalty=self.event(pid=self.other)
        with self.assertRaises(ValueError):
            self.event(event_type='Поощрение',event_kind=REMOVAL_REWARD,removed_event_id=penalty)
        self.assertEqual(self.discipline.get_by_id(penalty)['status'],'Активно')
        self.assertEqual(len(self.discipline.get_all()),1)

    def test_invalid_reference_rolls_back(self):
        penalty=self.event()
        with self.assertRaises(ValueError):
            self.event(event_type='Поощрение',event_kind=REMOVAL_REWARD,removed_event_id=penalty,authority_name='Неверный орган')
        self.assertEqual(self.discipline.get_by_id(penalty)['status'],'Активно')

    def test_removal_needs_document_and_valid_date(self):
        penalty=self.event()
        for when,doc in [('2026-09-30','1'),('2026-10-02','')]:
            with self.assertRaises(ValueError): self.discipline.remove_penalty(penalty,when,doc,'','')
        self.assertEqual(self.discipline.get_by_id(penalty)['status'],'Активно')

    def test_edit_linked_reward_updates_removal_details(self):
        penalty=self.event()
        reward=self.event(event_type='Поощрение',event_kind=REMOVAL_REWARD,removed_event_id=penalty,event_date='2026-10-20')
        args=dict(personnel_id=self.pid,event_type='Поощрение',event_kind=REMOVAL_REWARD,authority_name='НС',event_date='2026-10-21',document_number='Новый приказ',basis='Основание',comment='')
        self.discipline.update(reward,**args)
        self.assertEqual(self.discipline.get_by_id(penalty)['removal_document'],'Новый приказ')
        args['personnel_id']=self.other
        with self.assertRaises(ValueError): self.discipline.update(reward,**args)

    def test_event_edits_preserve_removed_status(self):
        penalty=self.event()
        self.discipline.remove_penalty(penalty,'2026-10-20','2','','')
        self.discipline.update(penalty,self.pid,'Взыскание','Строгий выговор','НО','2026-10-01','3','','',status='Активно')
        self.assertEqual(self.discipline.get_by_id(penalty)['status'],'Снято')


if __name__=='__main__': unittest.main()
