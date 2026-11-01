from contextlib import closing
from database.connection import get_connection
from personnel_fields import parse_date

REMOVAL_REWARD = 'Снятие ранее примененного дисциплинарного взыскания'
SELECT_EVENTS = '''SELECT d.*, p.full_name, et.name AS event_type,
                         ek.name AS event_kind, a.name AS authority_name
                  FROM disciplinary_events d
                  JOIN personnel p ON p.id=d.personnel_id
                  JOIN event_types et ON et.id=d.event_type_id
                  JOIN event_kinds ek ON ek.id=d.event_kind_id
                  LEFT JOIN authorities a ON a.id=d.authority_id'''


class DisciplineRepository:
    def __init__(self, connection_factory=None):
        self.connection_factory = connection_factory or get_connection

    def get_all(self):
        with closing(self.connection_factory()) as conn:
            return conn.execute(SELECT_EVENTS+' ORDER BY d.event_date DESC, d.id DESC').fetchall()

    def search(self,text=''):
        needle=text.casefold()
        return [r for r in self.get_all() if needle in ' '.join(str(v or '') for v in dict(r).values()).casefold()]

    def get_by_id(self,event_id):
        with closing(self.connection_factory()) as conn:
            return conn.execute(SELECT_EVENTS+' WHERE d.id=?',(event_id,)).fetchone()

    def get_personnel_history(self,personnel_id):
        with closing(self.connection_factory()) as conn:
            return conn.execute(SELECT_EVENTS+' WHERE d.personnel_id=? ORDER BY d.event_date DESC, d.id DESC',(personnel_id,)).fetchall()

    def _references(self,conn,event_type,event_kind,authority_name):
        kind=conn.execute('''SELECT k.id, k.event_type_id FROM event_kinds k JOIN event_types t ON t.id=k.event_type_id
                             WHERE t.name=? AND k.name=?''',(event_type,event_kind)).fetchone()
        if not kind: raise ValueError('Выберите тип и вид события из справочника.')
        authority=conn.execute('SELECT id FROM authorities WHERE name=?',(authority_name,)).fetchone()
        if not authority: raise ValueError('Выберите орган из справочника.')
        return kind['event_type_id'],kind['id'],authority['id']

    def _dates(self,event_date,due_date):
        start,end=parse_date(event_date),parse_date(due_date)
        if start is None: raise ValueError('Укажите дату события.')
        if end and end<start: raise ValueError('Срок не может быть раньше даты события.')
        return start.isoformat(),end.isoformat() if end else None

    def _remove(self,conn,event_id,personnel_id,removal_date,document,basis,comment):
        if not document.strip(): raise ValueError('Укажите номер приказа о снятии взыскания.')
        row=conn.execute(SELECT_EVENTS+' WHERE d.id=?',(event_id,)).fetchone()
        if not row or row['personnel_id']!=personnel_id or row['event_type']!='Взыскание' or row['status']!='Активно':
            raise ValueError('Выберите активное взыскание этого военнослужащего.')
        prior=parse_date(row['event_date'])
        if prior and parse_date(removal_date)<prior:
            raise ValueError('Дата снятия раньше даты взыскания.')
        cur=conn.execute('''UPDATE disciplinary_events SET status='Снято', removal_date=?, removal_document=?,
                           removal_basis=?, removal_comment=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='Активно' ''',
                         (removal_date,document,basis,comment,event_id))
        if cur.rowcount!=1: raise ValueError('Взыскание уже изменено. Обновите список.')

    def create(self,personnel_id,event_type,event_kind,authority_name,event_date,document_number,basis,comment,
               status='Активно',due_date=None,removed_event_id=None):
        event_date,due_date=self._dates(event_date,due_date)
        is_removal=event_type=='Поощрение' and event_kind==REMOVAL_REWARD
        if is_removal and not removed_event_id: raise ValueError('Выберите взыскание, которое снимается.')
        if not is_removal and removed_event_id: raise ValueError('Связь со взысканием доступна только для поощрения о снятии.')
        with closing(self.connection_factory()) as conn, conn:
            refs=self._references(conn,event_type,event_kind,authority_name)
            if is_removal:
                self._remove(conn,removed_event_id,personnel_id,event_date,document_number,basis,comment)
            cur=conn.execute('''INSERT INTO disciplinary_events (personnel_id,event_type_id,event_kind_id,authority_id,
                                event_date,document_number,basis,comment,status,due_date,linked_penalty_id)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                             (personnel_id,*refs,event_date,document_number,basis,comment,'Активно',due_date,removed_event_id))
            return cur.lastrowid

    def update(self,event_id,personnel_id,event_type,event_kind,authority_name,event_date,document_number,basis,comment,
               status='Активно',due_date=None,removed_event_id=None):
        event_date,due_date=self._dates(event_date,due_date)
        with closing(self.connection_factory()) as conn, conn:
            old=conn.execute(SELECT_EVENTS+' WHERE d.id=?',(event_id,)).fetchone()
            if not old: raise ValueError('Запись не найдена.')
            refs=self._references(conn,event_type,event_kind,authority_name)
            link=old['linked_penalty_id']
            if link:
                if (personnel_id!=old['personnel_id'] or event_type!='Поощрение' or event_kind!=REMOVAL_REWARD
                        or removed_event_id not in (None,link)):
                    raise ValueError('Нельзя менять военнослужащего, вид или связь поощрения о снятии взыскания.')
                penalty=conn.execute('SELECT event_date FROM disciplinary_events WHERE id=?',(link,)).fetchone()
                if not document_number.strip(): raise ValueError('Укажите номер приказа о снятии.')
                if penalty['event_date'] and parse_date(event_date)<parse_date(penalty['event_date']):
                    raise ValueError('Дата снятия раньше даты взыскания.')
                conn.execute('''UPDATE disciplinary_events SET removal_date=?,removal_document=?,removal_basis=?,removal_comment=?,
                                updated_at=CURRENT_TIMESTAMP WHERE id=?''',(event_date,document_number,basis,comment,link))
            elif event_type=='Поощрение' and event_kind==REMOVAL_REWARD:
                if not removed_event_id: raise ValueError('Выберите взыскание, которое снимается.')
                self._remove(conn,removed_event_id,personnel_id,event_date,document_number,basis,comment)
                link=removed_event_id
            elif removed_event_id:
                raise ValueError('Недопустимая связь со взысканием.')
            if old['status']=='Снято':
                if personnel_id!=old['personnel_id'] or event_type!='Взыскание':
                    raise ValueError('Нельзя менять военнослужащего или тип снятого взыскания.')
                if old['removal_date'] and parse_date(event_date)>parse_date(old['removal_date']):
                    raise ValueError('Дата взыскания позже даты снятия.')
            conn.execute('''UPDATE disciplinary_events SET personnel_id=?,event_type_id=?,event_kind_id=?,authority_id=?,
                            event_date=?,document_number=?,basis=?,comment=?,due_date=?,linked_penalty_id=?,
                            updated_at=CURRENT_TIMESTAMP WHERE id=?''',
                         (personnel_id,*refs,event_date,document_number,basis,comment,due_date,link,event_id))

    def remove_penalty(self,event_id,removal_date,removal_document,removal_basis,removal_comment):
        removal=parse_date(removal_date)
        if removal is None: raise ValueError('Укажите дату снятия.')
        with closing(self.connection_factory()) as conn, conn:
            row=conn.execute('SELECT personnel_id FROM disciplinary_events WHERE id=?',(event_id,)).fetchone()
            if not row: raise ValueError('Взыскание не найдено.')
            self._remove(conn,event_id,row['personnel_id'],removal.isoformat(),removal_document,removal_basis,removal_comment)

    def get_personnel_statistics(self,personnel_id):
        return self._statistics(self.get_personnel_history(personnel_id))

    def get_statistics(self): return self._statistics(self.get_all())

    @staticmethod
    def _statistics(rows):
        return dict(rewards=sum(r['event_type']=='Поощрение' for r in rows),
                    penalties=sum(r['event_type']=='Взыскание' for r in rows),
                    active_penalties=sum(r['event_type']=='Взыскание' and r['status']=='Активно' for r in rows),
                    removed_penalties=sum(r['event_type']=='Взыскание' and r['status']=='Снято' for r in rows))

    def get_recent_events(self,limit=10): return self.get_all()[:limit]
