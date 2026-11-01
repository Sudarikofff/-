"""Persistent, application-only reminders for vehicle insurance expiry."""
from contextlib import closing
from datetime import date
import json
import re

from database.connection import get_connection
from personnel_fields import parse_date


DEFAULT_SETTINGS = dict(enabled=True, days=[30, 14, 7, 1], on_expiry=True,
                        overdue=True, repeat_overdue=True, include_archive=False,
                        startup_summary=True)

SCHEMA = '''
CREATE TABLE IF NOT EXISTS notification_settings (
    category TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS osago_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES personal_vehicles(id) ON DELETE CASCADE,
    expiry_date TEXT NOT NULL,
    phase TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    snoozed_until TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(vehicle_id, expiry_date)
);
'''


def migrate_notifications():
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)


def validate_settings(values):
    result = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key != 'days':
            value = values.get(key, DEFAULT_SETTINGS[key])
            if not isinstance(value, (bool, int)) or value not in (0, 1):
                raise ValueError('Некорректное значение переключателя.')
            result[key] = bool(value)
    raw = values.get('days', DEFAULT_SETTINGS['days'])
    tokens = re.split(r'[,;\s]+', raw.strip()) if isinstance(raw, str) else raw
    days = []
    for token in tokens:
        if token == '':
            continue
        if isinstance(token, bool) or not str(token).isdigit() or not 1 <= int(token) <= 365:
            raise ValueError('Сроки напоминаний: целые числа от 1 до 365, через запятую. Например: 30, 14, 7, 1.')
        days.append(int(token))
    result['days'] = sorted(set(days), reverse=True)
    return result


def reminder_phase(days_left, settings, today):
    if not settings['enabled']:
        return None
    if days_left < 0:
        if not settings['overdue']:
            return None
        return 'overdue:' + (today.isoformat() if settings['repeat_overdue'] else 'once')
    if days_left == 0:
        return 'today' if settings['on_expiry'] else None
    reached = [days for days in settings['days'] if days_left <= days]
    return f'before:{min(reached)}' if reached else None


class OsagoNotifications:
    def get_settings(self):
        with closing(get_connection()) as conn:
            row = conn.execute("SELECT value FROM notification_settings WHERE category='osago'").fetchone()
        return validate_settings(json.loads(row['value']) if row else DEFAULT_SETTINGS)

    def save_settings(self, values):
        settings = validate_settings(values)
        with closing(get_connection()) as conn, conn:
            conn.execute("INSERT INTO notification_settings(category,value) VALUES ('osago',?) "
                         'ON CONFLICT(category) DO UPDATE SET value=excluded.value',
                         (json.dumps(settings),))
        return settings

    def refresh(self, today=None):
        today = today or date.today()
        settings = self.get_settings()
        invalid_dates = 0
        with closing(get_connection()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            old = {(r['vehicle_id'], r['expiry_date']): dict(r) for r in conn.execute('SELECT * FROM osago_notifications')}
            active_ids = []
            vehicles = conn.execute('''SELECT v.*, p.service_status FROM personal_vehicles v
                                       JOIN personnel p ON p.id=v.personnel_id''').fetchall()
            for vehicle in vehicles:
                if vehicle['service_status'] == 'Архив' and not settings['include_archive']:
                    continue
                try:
                    expiry = parse_date(vehicle['insurance_expiry'])
                except ValueError:
                    invalid_dates += 1
                    continue
                if not expiry:
                    continue
                phase = reminder_phase((expiry-today).days, settings, today)
                if phase is None:
                    continue
                previous = old.get((vehicle['id'], expiry.isoformat()))
                if previous is None:
                    ident = conn.execute('''INSERT INTO osago_notifications(vehicle_id,expiry_date,phase)
                                            VALUES (?,?,?)''', (vehicle['id'], expiry.isoformat(), phase)).lastrowid
                else:
                    ident = previous['id']
                    read = previous['is_read'] if previous['phase'] == phase else 0
                    snoozed = previous['snoozed_until']
                    if snoozed and snoozed <= today.isoformat():
                        snoozed, read = None, 0
                    if (previous['phase'], previous['is_read'], previous['snoozed_until'], previous['active']) != (phase, read, snoozed, 1):
                        conn.execute('UPDATE osago_notifications SET phase=?, is_read=?, snoozed_until=?, active=1 WHERE id=?',
                                     (phase, read, snoozed, ident))
                active_ids.append(ident)
            # A renewal, deletion, archive or changed settings closes stale reminders.
            active = set(active_ids)
            for row in old.values():
                if row['active'] and row['id'] not in active:
                    conn.execute('UPDATE osago_notifications SET active=0 WHERE id=?', (row['id'],))
        return dict(settings=settings, invalid_dates=invalid_dates, rows=self.list_current(today))

    def list_current(self, today=None):
        today = today or date.today()
        with closing(get_connection()) as conn:
            rows = conn.execute('''SELECT n.*, v.personnel_id, v.model, v.plate, v.insurance_number,
                                  p.full_name FROM osago_notifications n
                                  JOIN personal_vehicles v ON v.id=n.vehicle_id
                                  JOIN personnel p ON p.id=v.personnel_id WHERE n.active=1
                                  ORDER BY n.expiry_date, p.full_name, n.id''').fetchall()
        result = []
        for row in rows:
            row = dict(row)
            days = (parse_date(row['expiry_date'])-today).days
            row['days'] = days
            row['deferred'] = bool(row['snoozed_until'] and row['snoozed_until'] > today.isoformat())
            row['status'] = 'Просрочено' if days < 0 else ('Сегодня' if days == 0 else 'Предстоит')
            row['title'] = (f'ОСАГО просрочено: {abs(days)} дн.' if days < 0 else
                            'ОСАГО заканчивается сегодня' if days == 0 else f'ОСАГО заканчивается через {days} дн.')
            row['reading'] = 'Отложено' if row['deferred'] else ('Прочитано' if row['is_read'] else 'Новое')
            row['vehicle'] = ' · '.join(str(v) for v in (row['model'], row['plate']) if v) or 'Автомобиль не указан'
            result.append(row)
        return result

    def mark_read(self, notification_id):
        with closing(get_connection()) as conn, conn:
            conn.execute('UPDATE osago_notifications SET is_read=1 WHERE id=? AND active=1', (notification_id,))

    def mark_all_read(self, today=None):
        today = today or date.today()
        with closing(get_connection()) as conn, conn:
            conn.execute('UPDATE osago_notifications SET is_read=1 WHERE active=1 AND (snoozed_until IS NULL OR snoozed_until<=?)',
                         (today.isoformat(),))

    def snooze(self, notification_id, until, today=None):
        today = today or date.today()
        until = parse_date(until)
        if not until or until <= today:
            raise ValueError('Выберите дату позже сегодняшней.')
        with closing(get_connection()) as conn, conn:
            conn.execute('UPDATE osago_notifications SET snoozed_until=?, is_read=1 WHERE id=? AND active=1',
                         (until.isoformat(), notification_id))

    def resume(self, notification_id):
        with closing(get_connection()) as conn, conn:
            conn.execute('UPDATE osago_notifications SET snoozed_until=NULL, is_read=0 WHERE id=? AND active=1',
                         (notification_id,))
