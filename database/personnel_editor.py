"""Isolated editor draft and atomic persistence of a complete personnel record."""
from contextlib import closing
import sqlite3
from uuid import uuid4

from database.connection import get_connection
from database.profile_repository import ProfileRepository
from database.discipline_repository import DisciplineRepository
from personnel_fields import Field, PERSONAL, MILITARY, COLLECTIONS, validate


SERVICE_FIELDS = [
    Field('personal_number', 'Личный номер'),
    Field('rank_date', 'Дата присвоения звания', 'date'),
    Field('position_date', 'Дата назначения на должность', 'date'),
    Field('service_status', 'Статус службы', choices=('Служит', 'Командировка', 'Отпуск', 'Архив'), required=True),
]
RELATED_TABLES = (*COLLECTIONS, 'disciplinary_events', 'service_history')


class DraftPersonnelRepository:
    def __init__(self, session):
        self.session = session

    def get_by_id(self, personnel_id):
        with closing(self.session.connect()) as conn:
            return conn.execute('''SELECT p.*, r.name AS rank_name, u.name AS unit_name,
                                   pos.name AS position_name FROM personnel p
                                   LEFT JOIN ranks r ON r.id=p.rank_id
                                   LEFT JOIN units u ON u.id=p.unit_id
                                   LEFT JOIN positions pos ON pos.id=p.position_id
                                   WHERE p.id=?''', (personnel_id,)).fetchone()

    def get_all(self):
        return [self.get_by_id(self.session.personnel_id)]


class PersonnelEditorSession:
    def __init__(self, personnel_id=None):
        self.original_id = personnel_id
        self.uri = f'file:personnel-editor-{uuid4().hex}?mode=memory&cache=shared'
        self.closed = False
        self.saved = False
        self.anchor = self.connect()
        try:
            # The private in-memory database lets existing forms operate normally
            # without writing anything to the application's database before Save All.
            with closing(get_connection()) as source:
                source.backup(self.anchor)
            self.baseline = self.snapshot(self.anchor, personnel_id) if personnel_id is not None else None
            if personnel_id is not None and self.baseline['personnel'] is None:
                raise ValueError('Военнослужащий не найден. Обновите список.')
            if personnel_id is None:
                with self.anchor:
                    personnel_id = self.anchor.execute(
                        "INSERT INTO personnel(full_name, service_status) VALUES ('Новый военнослужащий', 'Служит')"
                    ).lastrowid
            self.personnel_id = personnel_id
            self.initial_draft = self.snapshot(self.anchor, personnel_id)
            self.profile = ProfileRepository(self.connect)
            self.profile.is_draft = True
            self.discipline = DisciplineRepository(self.connect)
            self.discipline.is_draft = True
            self.people = DraftPersonnelRepository(self)
        except Exception:
            self.close()
            raise

    def connect(self):
        if self.closed:
            raise ValueError('Форма уже закрыта.')
        conn = sqlite3.connect(self.uri, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    @staticmethod
    def snapshot(conn, personnel_id):
        row = conn.execute('SELECT * FROM personnel WHERE id=?', (personnel_id,)).fetchone()
        result = {'personnel': dict(row) if row else None}
        for table in RELATED_TABLES:
            result[table] = {r['id']: dict(r) for r in conn.execute(
                f'SELECT * FROM {table} WHERE personnel_id=? ORDER BY id', (personnel_id,))}
        return result

    def has_record_changes(self):
        current = self.snapshot(self.anchor, self.personnel_id)
        return any(current[table] != self.initial_draft[table] for table in RELATED_TABLES)

    def preview_name(self, name):
        with self.anchor:
            self.anchor.execute('UPDATE personnel SET full_name=? WHERE id=?',
                                (name.strip() or 'Новый военнослужащий', self.personnel_id))

    def _validate_personnel(self, values):
        data = validate(PERSONAL, values)
        data.update(validate(MILITARY, values))
        data.update(validate(SERVICE_FIELDS, values))
        for key, table in [('rank_id', 'ranks'), ('unit_id', 'units'), ('position_id', 'positions')]:
            value = values.get(key)
            if value in (None, ''):
                data[key] = None
                continue
            try:
                ident = int(value)
            except (ValueError, TypeError) as error:
                raise ValueError('Выберите звание, подразделение и должность из справочников.') from error
            if not self.anchor.execute(f'SELECT id FROM {table} WHERE id=?', (ident,)).fetchone():
                raise ValueError('Выбранное значение отсутствует в справочнике.')
            data[key] = ident
        return data

    @staticmethod
    def _write_row(conn, table, values, record_id=None):
        if record_id is None:
            return conn.execute(f'INSERT INTO {table} ({",".join(values)}) VALUES ({",".join("?" for _ in values)})',
                                list(values.values())).lastrowid
        conn.execute(f'UPDATE {table} SET '+', '.join(f'{key}=?' for key in values)+' WHERE id=?',
                     [*values.values(), record_id])
        return record_id

    def _sync_records(self, conn, table, draft_rows, personnel_id):
        old = self.baseline[table] if self.baseline else {}
        for ident in old.keys() - draft_rows.keys():
            conn.execute(f'DELETE FROM {table} WHERE id=? AND personnel_id=?', (ident, personnel_id))
        identities = {}
        for ident, row in draft_rows.items():
            if ident in old and row == old[ident]:
                identities[ident] = ident
                continue
            values = {k: v for k, v in row.items() if k != 'id'}
            values['personnel_id'] = personnel_id
            # New disciplinary IDs may differ from the private draft. Resolve
            # links after every event has a durable ID, independent of row order.
            if table == 'disciplinary_events':
                values['linked_penalty_id'] = None
            identities[ident] = self._write_row(conn, table, values, ident if ident in old else None)
        if table == 'disciplinary_events':
            for ident, row in draft_rows.items():
                link = row['linked_penalty_id']
                if link is not None:
                    if link not in identities:
                        raise ValueError('Не найдено взыскание, связанное с поощрением.')
                    conn.execute('UPDATE disciplinary_events SET linked_penalty_id=? WHERE id=?',
                                 (identities[link], identities[ident]))

    def _save_service_history(self, conn, personnel_id, data):
        old = self.baseline['personnel'] if self.baseline else {}

        def add(event_type, event_date, **values):
            self._write_row(conn, 'service_history', dict(personnel_id=personnel_id, event_type=event_type,
                            event_date=event_date or '', **values))

        if not old:
            add('Первичное назначение', data['position_date'], new_rank_id=data['rank_id'],
                new_unit_id=data['unit_id'], new_position_id=data['position_id'], basis='Создание личного дела')
            return
        if old['rank_id'] != data['rank_id']:
            add('Присвоение звания', data['rank_date'], old_rank_id=old['rank_id'], new_rank_id=data['rank_id'])
        if old['unit_id'] != data['unit_id']:
            add('Перевод', data['position_date'], old_unit_id=old['unit_id'], new_unit_id=data['unit_id'],
                old_position_id=old['position_id'], new_position_id=data['position_id'])
        elif old['position_id'] != data['position_id']:
            add('Назначение', data['position_date'], old_unit_id=data['unit_id'], new_unit_id=data['unit_id'],
                old_position_id=old['position_id'], new_position_id=data['position_id'])

    def save(self, values):
        if self.saved or self.closed:
            raise ValueError('Форма уже сохранена или закрыта.')
        data = self._validate_personnel(values)
        draft = self.snapshot(self.anchor, self.personnel_id)
        with closing(get_connection()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            if self.original_id is not None and self.snapshot(conn, self.original_id) != self.baseline:
                raise ValueError('Карточка изменена в другом окне. Закройте форму и откройте её снова, чтобы не потерять изменения.')
            if data['personal_number'] and conn.execute(
                'SELECT id FROM personnel WHERE personal_number=? AND id!=?',
                (data['personal_number'], self.original_id or -1)
            ).fetchone():
                raise ValueError('Военнослужащий с таким личным номером уже существует.')
            personnel_id = self._write_row(conn, 'personnel', data, self.original_id)
            conn.execute('UPDATE personnel SET updated_at=CURRENT_TIMESTAMP WHERE id=?', (personnel_id,))
            for table in (*COLLECTIONS, 'disciplinary_events'):
                self._sync_records(conn, table, draft[table], personnel_id)
            self._save_service_history(conn, personnel_id, data)
        self.saved = True
        return personnel_id

    def close(self):
        if not self.closed:
            self.anchor.close()
            self.closed = True
