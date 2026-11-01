from ui.widgets.filter_controls import label_filter
"""Reusable forms and sortable tables for the personnel card."""
from tkinter import ttk, messagebox, Menu
from ui.widgets.table_style import StyledTreeview
import sqlite3
import customtkinter as ctk
import theme
from ui.widgets.modal import grab_when_visible
from ui.widgets.data_events import notify_data_changed
from personnel_fields import display_date, parse_date, validate, COLLECTIONS


def button(parent, text, command, secondary=False, **kw):
    return ctk.CTkButton(parent, text=text, command=command, height=36,
                         fg_color=theme.CARD_HOVER if secondary else theme.PRIMARY,
                         text_color=theme.TEXT if secondary else 'white',
                         hover_color=theme.BORDER if secondary else theme.PRIMARY_HOVER,
                         border_width=1 if secondary else 0, border_color=theme.BORDER, **kw)


class FieldsPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, fields, values):
        super().__init__(parent, fg_color=theme.CARD)
        self.fields, self.inputs = fields, {}
        self.grid_columnconfigure((0, 1), weight=1, uniform='fields')
        row, col = 0, 0
        for f in fields:
            if f.group:
                if col: row, col = row+1, 0
                ctk.CTkLabel(self, text=f.group, font=theme.HEADER_FONT, text_color=theme.PRIMARY).grid(
                    row=row, column=0, columnspan=2, sticky='w', padx=12, pady=(16, 4))
                row += 1
            if f.kind == 'multiline' and col: row, col = row+1, 0
            frame = ctk.CTkFrame(self, fg_color='transparent')
            span = 2 if f.kind == 'multiline' else 1
            frame.grid(row=row, column=col, columnspan=span, sticky='ew', padx=12, pady=6)
            ctk.CTkLabel(frame, text=f.label + (' *' if f.required else ''), anchor='w',
                         text_color=theme.TEXT_SECONDARY, wraplength=650 if span==2 else 305).pack(anchor='w')
            value = values.get(f.key) or ''
            if f.kind == 'date': value = display_date(value)
            if f.choices:
                # Retain historical free-text values until the user deliberately changes them.
                choices = ([''] if not f.required else []) + list(f.choices)
                if value and value not in choices: choices.append(value)
                widget = ctk.CTkComboBox(frame, values=choices, state='readonly', height=36,
                                        fg_color=theme.INPUT_BG, text_color=theme.TEXT,
                                        border_color=theme.INPUT_BORDER,
                                        button_color=theme.PRIMARY, dropdown_fg_color=theme.CARD,
                                        dropdown_text_color=theme.TEXT)
                widget.set(value or (choices[0] if f.required else ''))
            elif f.kind == 'multiline':
                widget = ctk.CTkTextbox(frame, height=74, fg_color=theme.INPUT_BG,
                                       text_color=theme.TEXT, border_width=1, border_color=theme.INPUT_BORDER)
                widget.insert('1.0', str(value))
            else:
                widget = ctk.CTkEntry(frame, height=36, fg_color=theme.INPUT_BG,
                                     text_color=theme.TEXT, border_color=theme.INPUT_BORDER,
                                     placeholder_text='ДД.ММ.ГГГГ' if f.kind=='date' else '')
                widget.insert(0, str(value))
            widget.pack(fill='x')
            self.inputs[f.key] = widget
            col += span
            if col >= 2: row, col = row+1, 0

    def values(self):
        return {f.key: self.inputs[f.key].get('1.0', 'end').strip() if f.kind == 'multiline'
                else self.inputs[f.key].get().strip() for f in self.fields}


class RecordDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, fields, values, on_save):
        super().__init__(parent.winfo_toplevel())
        self.title(title)
        self.geometry('800x690')
        self.minsize(650, 500)
        self.configure(fg_color=theme.BACKGROUND)
        self.fields, self.on_save, self.inputs = fields, on_save, {}
        self.owner = parent.winfo_toplevel()
        self.transient(self.owner)
        self.previous_grab = self.grab_current()
        grab_when_visible(self)
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        ctk.CTkLabel(self, text=title, font=theme.SUBTITLE_FONT, text_color=theme.TEXT).pack(anchor='w', padx=24, pady=(18, 4))
        ctk.CTkLabel(self, text='* Обязательные поля. Даты: ДД.ММ.ГГГГ. Неизвестные значения можно оставить пустыми.',
                     text_color=theme.TEXT_SECONDARY, font=theme.SMALL_FONT, wraplength=720).pack(anchor='w', padx=24, pady=(0, 12))
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=24, pady=16)
        self.error = ctk.CTkLabel(footer, text='', text_color=theme.DANGER, wraplength=700, justify='left')
        self.error.pack(fill='x', pady=(0, 6))
        button(footer, 'Сохранить', self.save).pack(side='left')
        button(footer, 'Отмена', self.cancel, True).pack(side='right')
        self.form = FieldsPanel(self, fields, values)
        self.form.pack(fill='both', expand=True, padx=24)
        self.inputs = self.form.inputs
        self.initial = self.values()
        self.bind('<Control-Return>', lambda e: self.save())
        self.bind('<Escape>', lambda e: self.cancel())

    def values(self):
        return {f.key: self.inputs[f.key].get('1.0', 'end').strip() if f.kind=='multiline'
                else self.inputs[f.key].get().strip() for f in self.fields}

    def save(self):
        try:
            self.on_save(self.values())
        except (ValueError, sqlite3.Error) as error:
            self.error.configure(text=str(error))
            return
        self.close()

    def cancel(self):
        if self.values() != self.initial and not messagebox.askyesno(
                'Несохранённые изменения', 'Закрыть форму без сохранения?', parent=self):
            return
        self.close()

    def close(self):
        self.grab_release()
        self.destroy()
        if self.previous_grab and self.previous_grab.winfo_exists():
            grab_when_visible(self.previous_grab)


class DataTable(ctk.CTkFrame):
    def __init__(self, parent, columns, on_open=None):
        super().__init__(parent, fg_color=theme.CARD)
        self.columns, self.on_open, self.rows = columns, on_open, {}
        self.sort_column, self.descending = None, False
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.tree = StyledTreeview(self, columns=[c[0] for c in columns], show='headings')
        for key, label, width in columns:
            self.tree.heading(key, text=label, command=lambda k=key: self.sort(k))
            self.tree.column(key, width=width, minwidth=80, stretch=True)
        self.tree.grid(row=0, column=0, sticky='nsew')
        y = ttk.Scrollbar(self, command=self.tree.yview, style='App.Vertical.TScrollbar')
        y.grid(row=0, column=1, sticky='ns')
        x = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview, style='App.Horizontal.TScrollbar')
        x.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        self.empty = ctk.CTkLabel(self, text='Нет записей', text_color=theme.TEXT_SECONDARY)
        self.tree.bind('<Double-1>', self.open)
        self.tree.bind('<Return>', self.open)
        self.tree.bind('<Control-c>', self.copy_cell)
        self.tree.bind('<Control-C>', self.copy_cell)
        self.tree.bind('<Control-Shift-c>', self.copy)
        self.tree.bind('<Control-Shift-C>', self.copy)
        self.selected_column = None
        self.copy_menu = Menu(self, tearoff=0, font=theme.TEXT_FONT)
        self.copy_menu.add_command(label='Копировать ячейку', accelerator='Ctrl+C', command=self.copy_cell)
        self.copy_menu.add_command(label='Копировать строку', accelerator='Ctrl+Shift+C', command=self.copy)
        self.tree.bind('<Button-1>', self._select_cell, add='+')
        self.tree.bind('<Button-3>', self._popup_menu, add='+')

    def load(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for i, row in enumerate(rows):
            row = dict(row)
            iid = str(i)
            self.rows[iid] = row
            values = []
            for key, _, _ in self.columns:
                value = row.get(key)
                if key.endswith(('_date', '_expiry')) or key in ('event_date', 'snoozed_until'): value=display_date(value)
                values.append('—' if value is None or value=='' else value)
            self.tree.insert('', 'end', iid=iid, values=values, tags=(row.get('status', ''),))
        if self.rows: self.empty.place_forget()
        else: self.empty.place(relx=.5, rely=.5, anchor='center')
        if self.sort_column: self.sort(self.sort_column, toggle=False)

    def sort(self, key, toggle=True):
        if toggle:
            self.descending = not self.descending if self.sort_column==key else False
        self.sort_column=key
        def sort_key(iid):
            value=self.rows[iid].get(key)
            if value is None or value=='': return (1, '')
            if key in ('id', 'days', 'amount', 'balance', 'monthly_payment', 'debt_amount'):
                try: return (0, float(value))
                except (ValueError, TypeError): return (1, str(value))
            if key.endswith(('_date', '_expiry')):
                try: return (0, parse_date(value).isoformat())
                except ValueError: pass
            return (0, str(value).casefold())
        for pos, iid in enumerate(sorted(self.rows, key=sort_key, reverse=self.descending)):
            self.tree.move(iid, '', pos)
        for col, label, _ in self.columns:
            self.tree.heading(col, text=label + (' ↓' if self.descending else ' ↑') if col==key else label)

    def selected(self):
        selected=self.tree.selection()
        return self.rows.get(selected[0]) if selected else None

    def open(self, event=None):
        if event and getattr(event, 'num', None)==1 and self.tree.identify_region(event.x, event.y)!='cell':
            return
        row=self.selected()
        if row and self.on_open: self.on_open(row)

    def copy(self, event=None):
        selection=self.tree.selection()
        if selection:
            self.clipboard_clear()
            self.clipboard_append('\t'.join(self.tree.item(selection[0], 'values')))
        return 'break'


    def _select_cell(self, event):
        self.selected_column = self.tree.identify_column(event.x)

    def _popup_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.selected_column = self.tree.identify_column(event.x)
        self.tree.focus(item)
        menu = self.copy_menu
        # Keep Tk's native grab: its Menu bindings dismiss and restore focus.
        menu.tk_popup(event.x_root, event.y_root)

    def copy_cell(self, event=None):
        selection = self.tree.selection()
        if not selection or not self.selected_column:
            return 'break'
        values = self.tree.item(selection[0], 'values')
        index = int(self.selected_column[1:])-1
        if 0 <= index < len(values):
            self.clipboard_clear()
            self.clipboard_append(str(values[index]))
        return 'break'


RECORD_COLUMNS = {
    'family_members': [('relation', 'Родство', 100), ('full_name', 'ФИО', 240), ('birth_date', 'Дата рождения', 140), ('phone', 'Телефон', 140), ('workplace', 'Работа / учёба', 220), ('comment', 'Комментарий', 200)],
    'education_records': [('level', 'Уровень', 160), ('institution', 'Учебное заведение', 280), ('graduation_year', 'Год окончания', 140), ('specialty', 'Специальность', 200)],
    'personal_vehicles': [('model', 'Автомобиль', 200), ('plate', 'Госномер', 140), ('manufacture_year', 'Год', 80), ('license_number', 'Водительское удостоверение', 220), ('license_expiry', 'Срок ВУ', 130), ('insurance_expiry', 'Срок ОСАГО', 130)],
    'personal_loans': [('lender', 'Кредитор', 220), ('amount', 'Сумма, ₽', 140), ('monthly_payment', 'Платёж, ₽', 140), ('balance', 'Остаток, ₽', 140), ('repayment_date', 'Погашение', 140), ('has_debt', 'Задолженность', 140), ('status', 'Статус', 120)],
    'personnel_deadlines': [('title', 'Что необходимо выполнить', 280), ('category', 'Раздел', 160), ('due_date', 'Срок', 140), ('status', 'Состояние', 120)],
}


class CollectionPanel(ctk.CTkFrame):
    def __init__(self, parent, repository, table, personnel_id, on_changed=None):
        super().__init__(parent, fg_color='transparent')
        self.repository, self.table_name, self.personnel_id = repository, table, personnel_id
        self.on_changed = on_changed
        self.fields = COLLECTIONS[table][1]
        bar=ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', pady=(0, 12))
        button(bar, 'Добавить', self.add, width=110).pack(side='left')
        button(bar, 'Изменить', self.edit_selected, True, width=110).pack(side='left', padx=8)
        button(bar, 'Удалить', self.delete, True, width=90).pack(side='left')
        self.search=ctk.CTkEntry(bar, placeholder_text='Поиск по всем полям', width=230,
                                fg_color=theme.CARD, text_color=theme.TEXT)
        self.search.pack(side='right', padx=4)
        self.search.bind('<KeyRelease>', lambda e: self.refresh())
        label_filter(self.search,'Поиск по всем полям')
        self.table=DataTable(self, RECORD_COLUMNS[table], on_open=self.edit)
        self.table.pack(fill='both', expand=True)
        self.count=ctk.CTkLabel(self, text='', text_color=theme.TEXT_SECONDARY, font=theme.SMALL_FONT)
        self.count.pack(anchor='w', pady=(4, 0))
        self.refresh()

    def refresh(self):
        rows=self.repository.list_records(self.table_name, self.personnel_id)
        term=self.search.get().strip().casefold()
        filtered=[r for r in rows if term in ' '.join(str(r.get(f.key) or '') for f in self.fields).casefold()]
        self.table.load(filtered)
        self.count.configure(text=f'Показано {len(filtered)} из {len(rows)}. Двойной щелчок — изменить. Заголовок столбца — сортировать.')

    def add(self): self.edit({})

    def edit_selected(self):
        row=self.table.selected()
        if row: self.edit(row)
        else: messagebox.showinfo('Изменить запись', 'Выберите строку в таблице.', parent=self)

    def edit(self, row):
        def save(values):
            self.repository.save_record(self.table_name, self.personnel_id, values, row.get('id'))
            if not getattr(self.repository, "is_draft", False):
                notify_data_changed(self)
            self.refresh()
            if self.on_changed: self.on_changed()
        RecordDialog(self, COLLECTIONS[self.table_name][0] + (' — изменение' if row else ' — новая запись'),
                     self.fields, row, save)

    def delete(self):
        row=self.table.selected()
        if not row:
            messagebox.showinfo('Удалить запись', 'Выберите строку в таблице.', parent=self)
            return
        label=next((str(row.get(k)) for k in ('full_name','institution','model','license_number','lender','title') if row.get(k)), 'Запись')
        if messagebox.askyesno('Удаление записи', f'Удалить «{label}»?', parent=self):
            try:
                self.repository.delete_record(self.table_name, self.personnel_id, row['id'])
                if not getattr(self.repository, 'is_draft', False):
                    notify_data_changed(self)
                self.refresh()
                if self.on_changed: self.on_changed()
            except sqlite3.Error as error:
                messagebox.showerror('Не удалось удалить запись', str(error), parent=self)
