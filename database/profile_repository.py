from contextlib import closing
from datetime import date
from database.connection import get_connection
from personnel_fields import PERSONAL, MILITARY, COLLECTIONS, validate, parse_date


class ProfileRepository:
    def __init__(self, connection_factory=None):
        self.connection_factory = connection_factory or get_connection

    def update_personnel(self, personnel_id, fields, values):
        if fields is not PERSONAL and fields is not MILITARY:
            raise ValueError('Неизвестный раздел.')
        data = validate(fields, values)
        with closing(self.connection_factory()) as conn, conn:
            conn.execute('UPDATE personnel SET ' + ', '.join(f'{key}=?' for key in data)
                         + ', updated_at=CURRENT_TIMESTAMP WHERE id=?', [*data.values(), personnel_id])

    def list_records(self, table, personnel_id):
        if table not in COLLECTIONS:
            raise ValueError('Неизвестный раздел.')
        with closing(self.connection_factory()) as conn:
            return [dict(row) for row in conn.execute(
                f'SELECT * FROM {table} WHERE personnel_id=? ORDER BY id', (personnel_id,))]

    def save_record(self, table, personnel_id, values, record_id=None):
        fields = COLLECTIONS[table][1]
        data = validate(fields, values)
        with closing(self.connection_factory()) as conn, conn:
            if record_id is None:
                cursor = conn.execute(f'INSERT INTO {table} (personnel_id,{",".join(data)}) '
                                      f'VALUES ({",".join("?" for _ in range(len(data)+1))})',
                                      [personnel_id, *data.values()])
                return cursor.lastrowid
            cursor = conn.execute(f'UPDATE {table} SET ' + ', '.join(f'{key}=?' for key in data)
                                  + ' WHERE id=? AND personnel_id=?', [*data.values(), record_id, personnel_id])
            if cursor.rowcount != 1:
                raise ValueError('Запись не найдена. Обновите список.')
            return record_id

    def delete_record(self, table, personnel_id, record_id):
        if table not in COLLECTIONS:
            raise ValueError('Неизвестный раздел.')
        with closing(self.connection_factory()) as conn, conn:
            conn.execute(f'DELETE FROM {table} WHERE id=? AND personnel_id=?', (record_id, personnel_id))

    def set_deadline_completed(self, personnel_id, record_id, completed=True):
        with closing(self.connection_factory()) as conn, conn:
            cursor = conn.execute(
                'UPDATE personnel_deadlines SET status=? WHERE id=? AND personnel_id=?',
                ('Выполнено' if completed else 'Открыто', record_id, personnel_id))
            if cursor.rowcount != 1:
                raise ValueError('Срок не найден. Обновите список.')

    def deadlines(self, personnel_id=None, include_archive=False, today=None, include_completed=False):
        today = today or date.today()
        result = []
        with closing(self.connection_factory()) as conn:
            people = conn.execute('SELECT p.*, u.name AS unit_name FROM personnel p LEFT JOIN units u ON u.id=p.unit_id').fetchall()
            for row in people:
                p = dict(row)
                if personnel_id is not None and p['id'] != personnel_id:
                    continue
                if not include_archive and p['service_status'] == 'Архив':
                    continue
                def add(title, category, value, section, record_id=None, source_table='personnel', source_field=None, completed=False):
                    if not value:
                        return
                    try:
                        deadline = parse_date(value)
                        days = (deadline-today).days
                        state = 'Просрочено' if days < 0 else ('Сегодня' if days == 0 else 'Предстоит')
                    except ValueError:
                        deadline, days, state = None, None, 'Проверьте дату'
                    result.append(dict(personnel_id=p['id'], full_name=p['full_name'], unit_name=p['unit_name'] or '',
                                       title=title, category=category, due_date=deadline.isoformat() if deadline else value,
                                       days=days, status='Выполнено' if completed else state, section=section, record_id=record_id,
                                       source_table=source_table, source_field=source_field, completed=completed,
                                       source='Добавлен вручную' if source_table=='personnel_deadlines' else 'Из карточки'))
                for key, title, cat, section in [
                    ('contract_end_date', 'Окончание контракта', 'Военная служба', 'Военная служба'),
                    ('attestation_due_date', 'Аттестация', 'Военная служба', 'Военная служба'),
                    ('passport_due_date', 'Замена / срок паспорта', 'Документы', 'Личные данные'),
                    ('military_id_due_date', 'Срок удостоверения личности', 'Документы', 'Военная служба'),
                ]:
                    add(title, cat, p.get(key), section, source_field=key)
                # A year alone is shown without inventing a day or month.
                if p.get('attestation_year') and not p.get('attestation_due_date'):
                    result.append(dict(personnel_id=p['id'], full_name=p['full_name'], unit_name=p['unit_name'] or '',
                                       title='Аттестация (указан только год)', category='Военная служба',
                                       due_date=p['attestation_year'], days=None, status='Уточнить срок', section='Военная служба', record_id=None,
                                       source_table='personnel', source_field='attestation_year', completed=False, source='Из карточки'))
                for v in conn.execute('SELECT * FROM personal_vehicles WHERE personnel_id=?', (p['id'],)):
                    add('Водительское удостоверение ' + (v['license_number'] or ''), 'Транспорт', v['license_expiry'], 'Личный транспорт', v['id'], 'personal_vehicles', 'license_expiry')
                    add('ОСАГО ' + (v['plate'] or v['model'] or ''), 'Транспорт', v['insurance_expiry'], 'Личный транспорт', v['id'], 'personal_vehicles', 'insurance_expiry')
                for v in conn.execute("SELECT * FROM personal_loans WHERE personnel_id=? AND COALESCE(status,'Действует')!='Погашен'", (p['id'],)):
                    add('Погашение кредита: ' + v['lender'], 'Кредиты', v['repayment_date'], 'Кредиты', v['id'], 'personal_loans', 'repayment_date')
                    add('Платёж: ' + v['lender'], 'Кредиты', v['next_payment_date'], 'Кредиты', v['id'], 'personal_loans', 'next_payment_date')
                for v in conn.execute("SELECT * FROM personnel_deadlines WHERE personnel_id=?", (p['id'],)):
                    if v['status']=='Выполнено' and not include_completed:
                        continue
                    add(v['title'], v['category'], v['due_date'], 'Военная служба', v['id'], 'personnel_deadlines', 'due_date', v['status']=='Выполнено')
                for v in conn.execute("SELECT d.*, k.name AS kind FROM disciplinary_events d LEFT JOIN event_kinds k ON k.id=d.event_kind_id WHERE personnel_id=? AND status='Активно'", (p['id'],)):
                    add(v['kind'] or 'Дисциплинарное событие', 'Дисциплина', v['due_date'], 'Дисциплина', v['id'], 'disciplinary_events', 'due_date')
        return sorted(result, key=lambda r: (r['days'] is None, r['due_date'], r['full_name']))
