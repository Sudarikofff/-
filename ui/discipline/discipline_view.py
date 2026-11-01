from ui.widgets.filter_controls import label_filter, FilterActions
from tkinter import messagebox
import customtkinter as ctk
import theme
from ui.widgets.record_editor import DataTable, button
from ui.widgets.period_filter import PeriodFilter, filter_events
from ui.discipline.discipline_form import DisciplineForm
from ui.discipline.remove_penalty_dialog import RemovePenaltyDialog


class DisciplineView(ctk.CTkFrame):
    def __init__(self, parent, repository, personnel_repository, reference_repository, personnel_id=None, on_changed=None):
        super().__init__(parent, fg_color='transparent')
        self.repository, self.personnel_repository = repository, personnel_repository
        self.reference_repository=reference_repository
        self.personnel_id, self.on_changed=personnel_id,on_changed
        bar=ctk.CTkFrame(self,fg_color=theme.CARD)
        bar.pack(fill='x',pady=(0,12))
        actions=ctk.CTkFrame(bar,fg_color='transparent'); actions.pack(fill='x',padx=16,pady=12)
        button(actions,'Добавить поощрение',lambda:self.add_event('Поощрение'),width=175).pack(side='left')
        ctk.CTkButton(actions,text='Добавить взыскание',fg_color=theme.DANGER,hover_color='#8E1F13',height=36,
                      command=lambda:self.add_event('Взыскание'),width=175).pack(side='left',padx=8)
        button(actions,'Снять взыскание',self.remove_penalty,True,width=150).pack(side='left')
        button(actions,'Обновить',self.refresh,True,width=100).pack(side='right')
        filters=ctk.CTkFrame(bar,fg_color='transparent'); filters.pack(fill='x',padx=16,pady=(0,10))
        filters.grid_columnconfigure(0,weight=1)
        self.search_entry=ctk.CTkEntry(filters,placeholder_text='ФИО, вид события, приказ, основание…',height=36)
        self.search_entry.grid(row=0,column=0,sticky='ew',padx=(0,8))
        self.search_entry.bind('<KeyRelease>',lambda e:self.apply_filters())
        self.type_filter=ctk.CTkComboBox(filters,values=['Все события','Поощрение','Взыскание'],state='readonly',width=145,command=lambda v:self.apply_filters())
        self.type_filter.grid(row=0,column=1,padx=(0,8))
        self.status_filter=ctk.CTkComboBox(filters,values=['Все статусы','Активно','Снято'],state='readonly',width=130,command=lambda v:self.apply_filters())
        self.status_filter.grid(row=0,column=2)
        self.period=PeriodFilter(bar,self.apply_filters,show_actions=False); self.period.pack(fill='x',padx=16,pady=(0,10))
        last=ctk.CTkFrame(bar,fg_color='transparent'); last.pack(fill='x',padx=16,pady=(0,12))
        self.authority=ctk.CTkComboBox(last,values=['Все органы'],state='readonly',width=220,command=lambda v:self.apply_filters())
        self.authority.pack(side='left')
        self.error=ctk.CTkLabel(last,text='',text_color=theme.DANGER,wraplength=480); self.error.pack(side='left',padx=12)
        FilterActions(bar,[
            ('Применить',self.apply_filters,False),
            ('Сбросить',self.period.reset,True),
            ('Сбросить всё',self.reset,True),
        ]).pack(fill='x',padx=16,pady=(0,12))
        label_filter(self.search_entry,'Поиск: ФИО, событие, приказ')
        label_filter(self.type_filter,'Тип записи')
        label_filter(self.status_filter,'Статус')
        label_filter(self.authority,'Орган')

        self.summary=ctk.CTkLabel(self,text='',font=theme.TEXT_FONT,text_color=theme.TEXT_SECONDARY); self.summary.pack(anchor='w',pady=(0,8))
        cols=[('event_date','Дата',115),('full_name','Военнослужащий',230),('event_type','Тип',130),
              ('event_kind','Вид события',320),('authority_name','Орган',150),('document_number','Приказ',130),('due_date','Срок',115),('status','Статус',110)]
        if personnel_id is not None: cols=[c for c in cols if c[0]!='full_name']
        self.table=DataTable(self,cols,on_open=self.open_event); self.table.pack(fill='both',expand=True)
        ctk.CTkLabel(self,text='Заголовок — сортировка. Двойной щелчок — изменить. Сроки не снимают взыскания автоматически.',
                     font=theme.SMALL_FONT,text_color=theme.TEXT_SECONDARY,wraplength=900).pack(anchor='w',pady=(8,0))
        self.refresh()

    def refresh(self):
        self.rows=[dict(r) for r in self.repository.get_all() if self.personnel_id is None or r['personnel_id']==self.personnel_id]
        self.period.set_years(self.rows)
        self.authority.configure(values=['Все органы']+sorted({r['authority_name'] for r in self.rows if r['authority_name']}))
        self.apply_filters()

    def apply_filters(self):
        if not hasattr(self,'rows'): return
        try:
            rows=filter_events(self.rows,text=self.search_entry.get().strip(),**self.period.values(),
                               event_type='' if self.type_filter.get()=='Все события' else self.type_filter.get(),
                               status='' if self.status_filter.get()=='Все статусы' else self.status_filter.get(),
                               authority='' if self.authority.get()=='Все органы' else self.authority.get())
        except ValueError as error:
            self.error.configure(text=str(error)); return
        self.error.configure(text=''); self.table.load(rows)
        rewards=sum(r['event_type']=='Поощрение' for r in rows)
        penalties=sum(r['event_type']=='Взыскание' for r in rows)
        active=sum(r['event_type']=='Взыскание' and r['status']=='Активно' for r in rows)
        self.summary.configure(text=f'Показано {len(rows)} из {len(self.rows)}  ·  Поощрения: {rewards}  ·  Взыскания: {penalties}  ·  Активные: {active}')

    def reset(self):
        self.search_entry.delete(0,'end'); self.type_filter.set('Все события')
        self.status_filter.set('Все статусы'); self.authority.set('Все органы'); self.period.reset()

    def saved(self):
        self.refresh()
        if self.on_changed: self.on_changed()

    def add_event(self,event_type):
        DisciplineForm(self.winfo_toplevel(),self.personnel_repository,self.repository,self.reference_repository,
                       self.saved,event_type=event_type,personnel_id=self.personnel_id)

    def open_event(self,row):
        event=self.repository.get_by_id(row['id'])
        DisciplineForm(self.winfo_toplevel(),self.personnel_repository,self.repository,self.reference_repository,
                       self.saved,event=event,personnel_id=self.personnel_id)

    def remove_penalty(self):
        row=self.table.selected()
        if not row or row['event_type']!='Взыскание' or row['status']!='Активно':
            messagebox.showinfo('Снятие взыскания','Выберите активное взыскание в таблице.',parent=self); return
        RemovePenaltyDialog(self.winfo_toplevel(),self.repository,row['id'],self.saved)
