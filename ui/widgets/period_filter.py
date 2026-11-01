from datetime import date
import customtkinter as ctk
from personnel_fields import parse_date
from ui.widgets.filter_controls import CalendarFilterEntry, label_filter, FilterActions


def filter_events(rows, text='', year='', start='', end='', event_type='', status='', authority=''):
    lower, upper = parse_date(start), parse_date(end)
    if lower and upper and lower > upper:
        raise ValueError('Начало периода должно быть не позднее окончания.')
    result=[]
    for original in rows:
        row=dict(original)
        if event_type and row.get('event_type')!=event_type: continue
        if status and row.get('status')!=status: continue
        if authority and row.get('authority_name')!=authority: continue
        if text.casefold() not in ' '.join(str(v or '') for v in row.values()).casefold(): continue
        if year or lower or upper:
            try: d=parse_date(row.get('event_date'))
            except ValueError: continue
            if not d: continue
            if year and str(d.year)!=str(year): continue
            if lower and d<lower: continue
            if upper and d>upper: continue
        result.append(row)
    return result


class PeriodFilter(ctk.CTkFrame):
    def __init__(self, parent, on_change, show_actions=True):
        super().__init__(parent, fg_color='transparent')
        self.on_change=on_change
        self.grid_columnconfigure((0,1,2), weight=1)
        self.year=ctk.CTkComboBox(self, values=['Все годы'], state='readonly', width=140, command=self.choose_year)
        self.year.set('Все годы')
        self.year.grid(row=0, column=0, sticky='ew', padx=(0,8))
        self.start=CalendarFilterEntry(self, on_selected=lambda:self.year.set('Все годы'), width=150)
        self.start.grid(row=0,column=1,sticky='ew',padx=(0,8))
        self.end=CalendarFilterEntry(self, on_selected=lambda:self.year.set('Все годы'), width=150)
        self.end.grid(row=0,column=2,sticky='ew',padx=(0,8))
        if show_actions:
            FilterActions(self,[
                ('Применить',on_change,False),('Сбросить',self.reset,True)
            ]).grid(row=1,column=0,columnspan=3,sticky='ew',pady=(8,0))
        for widget, caption in ((self.year,'Год'),(self.start,'Дата с'),(self.end,'Дата по')):
            label_filter(widget,caption)

    def set_years(self, rows):
        years={str(date.today().year)}
        for r in rows:
            try:
                d=parse_date(r['event_date'])
                if d: years.add(str(d.year))
            except ValueError: pass
        self.year.configure(values=['Все годы']+sorted(years,reverse=True))

    def choose_year(self, value):
        self.start.clear(); self.end.clear(); self.on_change()

    def values(self):
        return dict(year='' if self.year.get()=='Все годы' else self.year.get(),start=self.start.get().strip(),end=self.end.get().strip())

    def reset(self):
        self.year.set('Все годы'); self.start.clear(); self.end.clear(); self.on_change()
