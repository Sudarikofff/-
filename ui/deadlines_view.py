from datetime import date
import sqlite3
from tkinter import messagebox
import customtkinter as ctk
import theme
from database.profile_repository import ProfileRepository
from personnel_fields import parse_date, DEADLINES, Field
from ui.widgets.record_editor import DataTable, RecordDialog, button
from ui.widgets.data_events import notify_data_changed
from ui.widgets.filter_controls import CalendarFilterEntry, label_filter, FilterActions


def filter_deadlines(rows, horizon='Все сроки', category='Все разделы', text='', year='', start='', end='', mode='На контроле'):
    lower,upper=parse_date(start),parse_date(end)
    if lower and upper and lower>upper: raise ValueError('Начало периода позже окончания.')
    result=[]
    for r in rows:
        if mode=='На контроле' and r.get('completed', False): continue
        if mode=='Выполненные' and not r.get('completed', False): continue
        if category!='Все разделы' and r['category']!=category: continue
        if text.casefold() not in f"{r['full_name']} {r['title']} {r['unit_name']}".casefold(): continue
        if year and not str(r['due_date']).startswith(str(year)): continue
        days=r['days']
        if horizon=='Просрочено' and (days is None or days>=0): continue
        if horizon=='Сегодня' and days!=0: continue
        if horizon=='Без точной даты' and days is not None: continue
        if horizon in ('30 дней','60 дней','90 дней') and (days is None or not 0<=days<=int(horizon.split()[0])): continue
        if lower or upper:
            try: d=parse_date(r['due_date'])
            except ValueError: continue
            if not d or (lower and d<lower) or (upper and d>upper): continue
        result.append(r)
    return result


class DeadlinesView(ctk.CTkFrame):
    def __init__(self,parent,personnel_repository,reference_repository):
        super().__init__(parent,fg_color='transparent')
        self.repository=ProfileRepository()
        self.personnel_repository,self.reference_repository=personnel_repository,reference_repository
        ctk.CTkLabel(self,text='Контроль сроков',font=theme.SUBTITLE_FONT,
                     text_color=theme.TEXT).pack(anchor='w',pady=(0,12))
        actions=ctk.CTkFrame(self,fg_color='transparent'); actions.pack(fill='x',pady=(0,12))
        button(actions,'+ Добавить срок',self.add_deadline,width=160).pack(side='left',padx=(0,8))
        self.edit_button=button(actions,'Изменить',self.edit_selected,True,width=180,state='disabled')
        self.edit_button.pack(side='left',padx=(0,8))
        self.complete_button=button(actions,'Отметить выполненным',self.toggle_completed,True,width=210,state='disabled')
        self.complete_button.pack(side='left',padx=(0,8))
        self.open_button=button(actions,'Открыть карточку',self.open_selected,True,width=160,state='disabled')
        self.open_button.pack(side='left')
        self.filters=ctk.CTkFrame(self,fg_color=theme.CARD); self.filters.pack(fill='x',pady=(0,14))
        top=ctk.CTkFrame(self.filters,fg_color='transparent'); top.pack(fill='x',padx=16,pady=14)
        self.search=ctk.CTkEntry(top,placeholder_text='ФИО, подразделение или документ',width=330,height=36)
        self.search.pack(side='left',fill='x',expand=True,padx=(0,10)); self.search.bind('<KeyRelease>',lambda e:self.apply_filters())
        self.horizon=ctk.CTkComboBox(top,values=['Все сроки','Просрочено','Сегодня','30 дней','60 дней','90 дней','Без точной даты'],state='readonly',command=lambda v:self.apply_filters())
        self.horizon.pack(side='left',padx=(0,10))
        self.category=ctk.CTkComboBox(top,values=['Все разделы','Военная служба','Документы','Транспорт','Кредиты','Дисциплина','Классность','Образование','Иное'],state='readonly',width=170,command=lambda v:self.apply_filters())
        self.category.pack(side='left')
        second=ctk.CTkFrame(self.filters,fg_color='transparent'); second.pack(fill='x',padx=16,pady=(0,12))
        self.year=ctk.CTkComboBox(second,values=['Все годы'],state='readonly',width=120,command=lambda v:self.apply_filters())
        self.year.pack(side='left',padx=(0,8))
        self.start=CalendarFilterEntry(second,width=145); self.start.pack(side='left',padx=(0,8))
        self.end=CalendarFilterEntry(second,width=145); self.end.pack(side='left',padx=(0,8))
        button(second,'Обновить',self.refresh,True,width=100).pack(side='right')
        third=ctk.CTkFrame(self.filters,fg_color='transparent'); third.pack(fill='x',padx=16,pady=(0,12))
        self.mode=ctk.CTkComboBox(third,values=['На контроле','Выполненные','Все записи'],state='readonly',width=180,command=lambda v:self.apply_filters())
        self.mode.pack(side='left',padx=(0,16))
        self.include_archive=ctk.CTkCheckBox(third,text='Включая архив',command=self.refresh,text_color=theme.TEXT)
        self.include_archive.pack(side='left')
        FilterActions(self.filters,[
            ('Применить',self.apply_filters,False),('Сбросить',self.reset,True)
        ]).pack(fill='x',padx=16,pady=(0,8))
        self.error=ctk.CTkLabel(self.filters,text='',text_color=theme.DANGER)
        self.error.pack(anchor='w',padx=16)
        for widget, caption in ((self.search,'Поиск: ФИО, подразделение, документ'),
                                (self.horizon,'Срок'),(self.category,'Категория'),
                                (self.year,'Год'),(self.start,'Дата с'),(self.end,'Дата по'),
                                (self.mode,'Статус')):
            label_filter(widget,caption)
        self.summary=ctk.CTkLabel(self,text='',font=theme.TEXT_FONT,text_color=theme.TEXT_SECONDARY); self.summary.pack(anchor='w',pady=(0,10))
        self.table=DataTable(self,[('full_name','Военнослужащий',240),('unit_name','Подразделение',180),
                                   ('category','Раздел',150),('title','Документ / событие',290),('due_date','Срок',130),
                                   ('days','Осталось дней',140),('status','Состояние',150),('source','Источник',170)],self.edit_row)
        self.table.pack(fill='both',expand=True)
        self.table.tree.bind('<<TreeviewSelect>>',lambda event:self.update_actions(),add='+')
        self.table.empty.configure(text='Сроков по выбранным условиям нет.\nДобавьте срок или измените фильтры.')
        self.selection_hint=ctk.CTkLabel(self,text='Выберите строку, чтобы изменить срок или открыть карточку.',
                     text_color=theme.TEXT_SECONDARY,font=theme.SMALL_FONT,wraplength=1050,justify='left')
        self.selection_hint.pack(anchor='w',pady=(8,0))
        self.refresh()

    def refresh(self):
        self.rows=self.repository.deadlines(include_archive=bool(self.include_archive.get()),include_completed=True)
        years={str(date.today().year)}
        years.update(str(r['due_date'])[:4] for r in self.rows if str(r['due_date'])[:4].isdigit())
        years=['Все годы']+sorted(years)
        self.year.configure(values=years)
        if self.year.get() not in years: self.year.set('Все годы')
        self.apply_filters()

    def apply_filters(self):
        if not hasattr(self,'rows'): return
        try:
            rows=filter_deadlines(self.rows,self.horizon.get(),self.category.get(),self.search.get().strip(),
                                  '' if self.year.get()=='Все годы' else self.year.get(),self.start.get(),self.end.get(),self.mode.get())
        except ValueError as error:
            self.error.configure(text=str(error)); return
        selected=self.table.selected()
        self.error.configure(text=''); self.table.load(rows)
        if selected:
            for item,row in self.table.rows.items():
                if self.row_key(row)==self.row_key(selected):
                    self.table.tree.selection_set(item); self.table.tree.focus(item); self.table.tree.see(item); break
        self.update_actions()
        overdue=sum(not r['completed'] and r['days'] is not None and r['days']<0 for r in rows)
        upcoming=sum(not r['completed'] and r['days'] is not None and 0<=r['days']<=30 for r in rows)
        self.summary.configure(text=f'Показано {len(rows)} из {len(self.rows)}  ·  Просрочено: {overdue}  ·  Ближайшие 30 дней: {upcoming}')

    def reset(self):
        self.search.delete(0,'end'); self.start.clear(); self.end.clear()
        self.year.set('Все годы'); self.horizon.set('Все сроки'); self.category.set('Все разделы')
        self.mode.set('На контроле')
        self.include_archive.deselect(); self.refresh()

    def open_card(self,row):
        from ui.personnel.personnel_card import PersonnelCard
        PersonnelCard(self,self.personnel_repository,self.reference_repository,row['personnel_id'],initial_section=row['section'])

    @staticmethod
    def row_key(row):
        return (row['personnel_id'],row['source_table'],row['record_id'],row['source_field'])

    def update_actions(self):
        row=self.table.selected()
        manual=bool(row and row['source_table']=='personnel_deadlines')
        self.edit_button.configure(state='normal' if row else 'disabled',text='Изменить срок' if manual else 'Изменить в карточке')
        self.open_button.configure(state='normal' if row else 'disabled')
        self.complete_button.configure(state='normal' if manual else 'disabled',
                                       text='Вернуть на контроль' if row and row['completed'] else 'Отметить выполненным')
        if not row:
            hint='Выберите строку, чтобы изменить срок или открыть карточку.'
        elif manual:
            hint='Срок добавлен вручную. Его можно изменить, отметить выполненным или вернуть на контроль.'
        else:
            hint=f'Срок из карточки → {row["section"]}. Нажмите «Изменить в карточке» и обновите дату или состояние исходной записи.'
        self.selection_hint.configure(text=hint)

    def changed(self):
        self.refresh()
        notify_data_changed(self)

    def add_deadline(self):
        people=[dict(row) for row in self.personnel_repository.get_all()
                if self.include_archive.get() or row['service_status']!='Архив']
        if not people:
            messagebox.showinfo('Добавить срок','Сначала добавьте военнослужащего в разделе «Военнослужащие». Для выбора из архива включите «Включая архив».',parent=self)
            return
        choices={f"{p['full_name']} · {p['personal_number'] or 'без личного номера'} · {p['unit_name'] or 'без подразделения'} · ID {p['id']}":p['id'] for p in people}
        fields=[Field('person','Военнослужащий',choices=('',*choices),required=True),*[f for f in DEADLINES if f.key!='status']]
        def save(values):
            if values.get('person') not in choices:
                raise ValueError('Выберите военнослужащего.')
            ident=self.repository.save_record('personnel_deadlines',choices[values['person']],dict(values,status='Открыто'))
            self.search.delete(0,'end'); self.start.clear(); self.end.clear()
            self.year.set('Все годы'); self.horizon.set('Все сроки'); self.category.set('Все разделы'); self.mode.set('На контроле')
            self.refresh()
            for item,row in self.table.rows.items():
                if row['source_table']=='personnel_deadlines' and row['record_id']==ident:
                    self.table.tree.selection_set(item); self.table.tree.focus(item); self.table.tree.see(item)
                    break
            self.update_actions()
            notify_data_changed(self)
        RecordDialog(self,'Добавить срок',fields,{'category':'Иное'},save)

    def edit_selected(self):
        row=self.table.selected()
        if row: self.edit_row(row)

    def edit_row(self,row):
        if row['source_table']=='personnel_deadlines':
            records=self.repository.list_records('personnel_deadlines',row['personnel_id'])
            record=next((r for r in records if r['id']==row['record_id']),None)
            if record is None:
                self.refresh()
                messagebox.showinfo('Контроль сроков','Запись уже удалена. Список обновлён.',parent=self)
                return
            def save(values):
                self.repository.save_record('personnel_deadlines',row['personnel_id'],values,row['record_id'])
                self.changed()
            RecordDialog(self,f"Изменить срок — {row['full_name']}",DEADLINES,record,save)
        else:
            from ui.personnel.personnel_form import PersonnelForm
            PersonnelForm(self,self.personnel_repository,self.reference_repository,self.refresh,
                          personnel=self.personnel_repository.get_by_id(row['personnel_id']),initial_section=row['section'])

    def open_selected(self):
        row=self.table.selected()
        if row: self.open_card(row)

    def toggle_completed(self):
        row=self.table.selected()
        if not row or row['source_table']!='personnel_deadlines': return
        try:
            self.repository.set_deadline_completed(row['personnel_id'],row['record_id'],not row['completed'])
        except (ValueError,sqlite3.Error) as error:
            messagebox.showerror('Не удалось изменить срок',str(error),parent=self)
            return
        self.changed()
