from ui.widgets.filter_controls import label_filter
from datetime import date, timedelta
from tkinter import messagebox
import customtkinter as ctk

import theme
from personnel_fields import Field
from ui.widgets.record_editor import DataTable, RecordDialog, button


class NotificationsView(ctk.CTkFrame):
    def __init__(self, parent, repository, personnel_repository, reference_repository, on_change):
        super().__init__(parent, fg_color='transparent')
        self.repository = repository
        self.personnel_repository = personnel_repository
        self.reference_repository = reference_repository
        self.on_change = on_change
        controls = ctk.CTkFrame(self, fg_color=theme.CARD)
        controls.pack(fill='x', pady=(0, 12))
        filters = ctk.CTkFrame(controls, fg_color='transparent')
        filters.pack(fill='x', padx=16, pady=14)
        self.search = ctk.CTkEntry(filters, placeholder_text='Поиск по всем уведомлениям', height=36)
        self.search.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self.search.bind('<KeyRelease>', lambda event: self.render())
        self.filter = ctk.CTkComboBox(filters, values=['Все актуальные', 'Новые', 'Предстоящие', 'Просроченные', 'Отложенные'],
                                      state='readonly', width=170, command=lambda value: self.render())
        self.filter.pack(side='left', padx=(0, 12))
        self.category = ctk.CTkComboBox(filters, values=['Все типы'], state='readonly', width=150,
                                       command=lambda value: self.render())
        self.category.pack(side='left', padx=(0, 12))
        button(filters, 'Обновить', self.refresh, True, width=100).pack(side='right')
        label_filter(self.search,'Поиск по уведомлениям')
        label_filter(self.filter,'Статус')
        label_filter(self.category,'Тип уведомления')

        actions = ctk.CTkFrame(controls, fg_color='transparent')
        actions.pack(fill='x', padx=16, pady=(0, 14))
        button(actions, 'Открыть карточку', self.open_selected, width=155).pack(side='left')
        button(actions, 'Прочитано', self.read_selected, True, width=105).pack(side='left', padx=8)
        button(actions, 'Напомнить позже', self.snooze, True, width=155).pack(side='left')
        button(actions, 'Вернуть сейчас', self.resume, True, width=135).pack(side='left', padx=8)
        button(actions, 'Прочитать все', self.read_all, True, width=125).pack(side='right')
        self.summary = ctk.CTkLabel(self, text='', text_color=theme.TEXT_SECONDARY, wraplength=1050, justify='left')
        self.summary.pack(anchor='w', pady=(0, 10))
        self.table = DataTable(self, [('reading', 'Прочтение', 110), ('category', 'Тип', 130), ('full_name', 'Военнослужащий', 230),
                                    ('subject', 'Документ / объект', 230), ('title', 'Уведомление', 300),
                                    ('due_date', 'Срок', 130), ('snoozed_until', 'Отложено до', 130)],
                               on_open=self.open_card)
        self.table.pack(fill='both', expand=True)
        ctk.CTkLabel(self, text='Здесь собраны все уведомления. «Прочитано» не снимает событие с контроля. Откройте карточку, чтобы изменить данные.',
                     text_color=theme.TEXT_SECONDARY, font=theme.SMALL_FONT, wraplength=1000, justify='left').pack(anchor='w', pady=12)
        self.rows = []
        self.settings = {}
        self.warnings = []

    def refresh(self):
        self.on_change()

    def set_state(self, state):
        self.rows = state['rows']
        self.settings = state['settings']
        self.warnings = state['warnings']
        categories = ['Все типы'] + sorted({source['label'] for source in state['sources']})
        self.category.configure(values=categories)
        if self.category.get() not in categories:
            self.category.set('Все типы')
        self.render()

    def render(self):
        selected = self.table.selected()
        selected_id = selected['id'] if selected else None
        term = self.search.get().strip().casefold()
        mode = self.filter.get()
        rows = []
        for row in self.rows:
            if self.category.get() != 'Все типы' and row['category'] != self.category.get(): continue
            if mode == 'Отложенные':
                if not row['deferred']: continue
            elif row['deferred']:
                continue
            if mode == 'Новые' and row['is_read']: continue
            if mode == 'Предстоящие' and row['days'] < 0: continue
            if mode == 'Просроченные' and row['days'] >= 0: continue
            if term not in ' '.join(str(row.get(key) or '') for key in ('full_name', 'subject', 'title', 'category', 'search_text')).casefold():
                continue
            rows.append(row)
        self.table.load(rows)
        if selected_id is not None:
            for item, row in self.table.rows.items():
                if row['id'] == selected_id:
                    self.table.tree.selection_set(item)
                    self.table.tree.focus(item)
                    break
        visible = [row for row in self.rows if not row['deferred']]
        unread = sum(not row['is_read'] for row in visible)
        summary = f'Показано: {len(rows)} · Новых: {unread} · Отложено: {len(self.rows)-len(visible)}'
        if not self.settings.get('enabled', True):
            summary = 'Все типы уведомлений выключены. Включить их можно в настройках.'
        if self.warnings:
            summary += ' ' + ' '.join(self.warnings)
        self.summary.configure(text=summary)

    def selected(self):
        row = self.table.selected()
        if not row:
            messagebox.showinfo('Уведомления', 'Выберите уведомление в таблице.', parent=self)
        return row

    def open_selected(self):
        row = self.selected()
        if row: self.open_card(row)

    def open_card(self, row):
        from ui.personnel.personnel_card import PersonnelCard
        self.repository.mark_read(row['id'])
        self.on_change()
        PersonnelCard(self, self.personnel_repository, self.reference_repository,
                      row['personnel_id'], initial_section=row['section'])

    def read_selected(self):
        row = self.selected()
        if row:
            self.repository.mark_read(row['id'])
            self.on_change()

    def read_all(self):
        self.repository.mark_all_read()
        self.on_change()

    def snooze(self):
        row = self.selected()
        if not row: return

        def save(values):
            self.repository.snooze(row['id'], values['until'])
            self.on_change()

        dialog = RecordDialog(self, 'Напомнить позже',
                              [Field('until', 'Дата следующего напоминания (по умолчанию завтра)', 'date', required=True)],
                              {'until': (date.today()+timedelta(days=1)).isoformat()}, save)
        dialog.minsize(650, 340)
        dialog.geometry('700x380')

    def resume(self):
        row = self.selected()
        if row:
            self.repository.resume(row['id'])
            self.on_change()


class NotificationSettingsView(ctk.CTkFrame):
    def __init__(self, parent, repository, on_saved):
        super().__init__(parent, fg_color='transparent')
        self.repository, self.on_saved = repository, on_saved
        body = ctk.CTkScrollableFrame(self, fg_color=theme.CARD)
        body.pack(fill='both', expand=True)
        ctk.CTkLabel(body, text='Настройки уведомлений', font=theme.SUBTITLE_FONT,
                     text_color=theme.TEXT).pack(anchor='w', padx=24, pady=(24, 8))
        ctk.CTkLabel(body, text='Проверка при запуске, сохранении данных и раз в минуту, пока программа открыта.\nВсе уведомления показываются внутри программы.',
                     text_color=theme.TEXT_SECONDARY, justify='left', wraplength=850).pack(anchor='w', padx=24, pady=(0, 20))
        ctk.CTkLabel(body, text='ОСАГО', font=theme.HEADER_FONT, text_color=theme.PRIMARY).pack(anchor='w', padx=24, pady=(0, 8))
        self.controls = {}
        labels = [
            ('enabled', 'Включить уведомления по ОСАГО'),
            ('on_expiry', 'Напоминать в день окончания'),
            ('overdue', 'Уведомлять о просроченном ОСАГО'),
            ('repeat_overdue', 'Повторять просроченное напоминание раз в день'),
            ('include_archive', 'Включать военнослужащих из архива'),
            ('startup_summary', 'Показывать сводку новых уведомлений при запуске'),
        ]
        for key, label in labels:
            widget = ctk.CTkCheckBox(body, text=label, text_color=theme.TEXT, fg_color=theme.PRIMARY)
            widget.pack(anchor='w', padx=24, pady=10)
            self.controls[key] = widget
        ctk.CTkLabel(body, text='За сколько дней напоминать', font=theme.HEADER_FONT,
                     text_color=theme.TEXT).pack(anchor='w', padx=24, pady=(20, 4))
        self.days = ctk.CTkEntry(body, width=380, height=38, placeholder_text='30, 14, 7, 1')
        self.days.pack(anchor='w', padx=24, pady=(0, 8))
        ctk.CTkLabel(body, text='Введите числа от 1 до 365 через запятую. Пустое поле отключает предварительные напоминания.\nЕсли вы пропустили несколько порогов, появится одно актуальное уведомление.',
                     text_color=theme.TEXT_SECONDARY, wraplength=850, justify='left').pack(anchor='w', padx=24)
        self.feedback = ctk.CTkLabel(body, text='', text_color=theme.TEXT_SECONDARY, wraplength=850)
        self.feedback.pack(anchor='w', padx=24, pady=(20, 8))
        actions = ctk.CTkFrame(body, fg_color='transparent')
        actions.pack(fill='x', padx=24, pady=(0, 24))
        button(actions, 'Сохранить настройки', self.save, width=190).pack(side='left')
        button(actions, 'По умолчанию', self.defaults, True, width=150).pack(side='left', padx=12)
        self.refresh()

    def fill(self, settings):
        for key, control in self.controls.items():
            control.select() if settings[key] else control.deselect()
        self.days.delete(0, 'end')
        self.days.insert(0, ', '.join(map(str, settings['days'])))

    def refresh(self):
        self.fill(self.repository.get_settings())
        self.feedback.configure(text='')

    def defaults(self):
        from database.osago_notifications import DEFAULT_SETTINGS
        self.fill(DEFAULT_SETTINGS)
        self.feedback.configure(text='Значения восстановлены в форме. Нажмите «Сохранить настройки».', text_color=theme.TEXT_SECONDARY)

    def save(self):
        import sqlite3
        try:
            settings = self.repository.save_settings(dict(days=self.days.get(), **{key: bool(control.get()) for key, control in self.controls.items()}))
        except (ValueError, sqlite3.Error) as error:
            self.feedback.configure(text=str(error), text_color=theme.DANGER)
            return
        self.fill(settings)
        self.feedback.configure(text='Настройки сохранены.', text_color=theme.SUCCESS)
        self.on_saved()
