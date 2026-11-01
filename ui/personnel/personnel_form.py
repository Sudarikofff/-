"""Complete personnel editor shared by Add, Edit and the personnel card."""
from collections import Counter
from tkinter import messagebox
import sqlite3
import customtkinter as ctk

import theme
from database.personnel_editor import PersonnelEditorSession
from database.service_history_repository import ServiceHistoryRepository
from personnel_fields import Field, PERSONAL, MILITARY, COLLECTIONS
from ui.widgets.modal import grab_when_visible
from ui.widgets.data_events import notify_data_changed
from ui.widgets.record_editor import FieldsPanel, CollectionPanel, button
from ui.discipline.discipline_view import DisciplineView
from ui.personnel.personnel_service_history_table import PersonnelServiceHistoryTable


class PersonnelForm(ctk.CTkToplevel):
    SECTIONS = ('Личные данные', 'Военная служба', 'Дисциплина', 'Семья',
                'Образование', 'Личный транспорт', 'Кредиты', 'Другие сроки')

    def __init__(self, parent, repository, reference_repository, on_saved, personnel=None,
                 initial_section='Личные данные'):
        super().__init__(parent.winfo_toplevel())
        self.previous_grab = self.grab_current()
        self.repository = repository
        self.reference_repository = reference_repository
        self.on_saved = on_saved
        self.pages = {}
        self.nav = {}
        self.collection_names = {title: table for table, (title, _) in COLLECTIONS.items()}
        try:
            self.session = PersonnelEditorSession(personnel['id'] if personnel is not None else None)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Не удалось открыть форму', str(error), parent=parent)
            self.destroy()
            return
        self.personnel = dict(self.session.people.get_by_id(self.session.personnel_id))
        if personnel is None:
            self.personnel['full_name'] = ''
        self.title('Добавить военнослужащего' if personnel is None else 'Редактировать военнослужащего')
        self.geometry('1220x830')
        self.minsize(1060, 680)
        self.configure(fg_color=theme.BACKGROUND)
        self.transient(parent.winfo_toplevel())
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self._build_ui()
        self.initial_values = self.values()
        self.show_section(initial_section if initial_section in self.SECTIONS else 'Личные данные')
        self.bind('<Control-Return>', lambda event: self.save())
        self.bind('<Escape>', lambda event: self.cancel())
        grab_when_visible(self)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=0)
        header.pack(fill='x')
        ctk.CTkLabel(header, text=self.title(), font=theme.TITLE_FONT,
                     text_color=theme.TEXT).pack(anchor='w', padx=24, pady=(18, 4))
        ctk.CTkLabel(header, text='Заполните нужные разделы. Все изменения сохраняются одной кнопкой внизу.',
                     text_color=theme.TEXT_SECONDARY).pack(anchor='w', padx=24, pady=(0, 16))

        footer = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=0)
        footer.pack(side='bottom', fill='x')
        self.error = ctk.CTkLabel(footer, text='', text_color=theme.DANGER, wraplength=1000, justify='left')
        self.error.pack(anchor='w', padx=24, pady=(4, 0))
        actions = ctk.CTkFrame(footer, fg_color='transparent')
        actions.pack(fill='x', padx=24, pady=(4, 16))
        self.save_button = button(actions, 'Сохранить всё', self.save, width=170)
        self.save_button.pack(side='left')
        ctk.CTkLabel(actions, text='Ctrl+Enter — сохранить · Escape — отменить',
                     font=theme.SMALL_FONT, text_color=theme.TEXT_SECONDARY).pack(side='left', padx=18)
        button(actions, 'Отмена', self.cancel, True, width=110).pack(side='right')

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=20, pady=16)
        navigation = ctk.CTkFrame(body, width=210, fg_color=theme.CARD)
        navigation.pack(side='left', fill='y', padx=(0, 16))
        navigation.pack_propagate(False)
        ctk.CTkLabel(navigation, text='РАЗДЕЛЫ КАРТОЧКИ', font=theme.SMALL_FONT,
                     text_color=theme.TEXT_SECONDARY).pack(anchor='w', padx=16, pady=(18, 10))
        for name in self.SECTIONS:
            control = ctk.CTkButton(navigation, text=name, anchor='w', height=42,
                                    fg_color='transparent', text_color=theme.TEXT,
                                    hover_color=theme.TABLE_SELECTED,
                                    command=lambda value=name: self.show_section(value))
            control.pack(fill='x', padx=8, pady=3)
            self.nav[name] = control
        self.content = ctk.CTkFrame(body, fg_color='transparent')
        self.content.pack(side='left', fill='both', expand=True)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        personal = self._page('Личные данные', 'Обязательно только ФИО. Остальные сведения можно заполнить позже.')
        self.personal_fields = FieldsPanel(personal, PERSONAL, self.personnel)
        self.personal_fields.pack(fill='both', expand=True)
        military = self._page('Военная служба', 'Звание, должность, контракт, аттестация и служебные документы.')
        self._build_service(military)
        self.refresh_counts()

    def _page(self, title, subtitle):
        page = ctk.CTkFrame(self.content, fg_color='transparent')
        page.grid(row=0, column=0, sticky='nsew')
        ctk.CTkLabel(page, text=title, font=theme.SUBTITLE_FONT,
                     text_color=theme.TEXT).pack(anchor='w', pady=(0, 4))
        ctk.CTkLabel(page, text=subtitle, text_color=theme.TEXT_SECONDARY,
                     wraplength=830, justify='left').pack(anchor='w', pady=(0, 12))
        self.pages[title] = page
        page.grid_remove()
        return page

    def _build_service(self, parent):
        rows = {
            'rank_id': self.reference_repository.get_ranks(),
            'unit_id': self.reference_repository.get_units(),
            'position_id': self.reference_repository.get_positions(),
        }
        self.reference_maps = {}
        values = dict(self.personnel)
        for key, records in rows.items():
            counts = Counter(row['name'] for row in records)
            choices = {(row['name'] if counts[row['name']] == 1 else f"{row['name']} · #{row['id']}"): row['id']
                       for row in records}
            self.reference_maps[key] = choices
            values[key] = next((label for label, ident in choices.items() if ident == self.personnel.get(key)), '')
        fields = [
            Field('personal_number', 'Личный номер', group='Прохождение службы'),
            Field('service_status', 'Статус службы', choices=('Служит', 'Командировка', 'Отпуск', 'Архив'), required=True),
            Field('rank_id', 'Воинское звание', choices=tuple(self.reference_maps['rank_id']) or ('',)),
            Field('rank_date', 'Дата присвоения звания', 'date'),
            Field('unit_id', 'Подразделение', choices=tuple(self.reference_maps['unit_id']) or ('',)),
            Field('position_id', 'Воинская должность', choices=tuple(self.reference_maps['position_id']) or ('',)),
            Field('position_date', 'Дата назначения на должность', 'date'),
            *MILITARY,
        ]
        tabs = ctk.CTkTabview(parent, fg_color=theme.CARD,
                             segmented_button_selected_color=theme.PRIMARY)
        tabs.pack(fill='both', expand=True)
        details = tabs.add('Сведения')
        history = tabs.add('История службы')
        self.service_fields = FieldsPanel(details, fields, values)
        self.service_fields.pack(fill='both', expand=True)
        ctk.CTkLabel(history, text='Изменения звания, подразделения и должности попадут в историю после сохранения всей карточки.',
                     text_color=theme.TEXT_SECONDARY, wraplength=800).pack(anchor='w', pady=8)
        table = PersonnelServiceHistoryTable(history)
        table.pack(fill='both', expand=True)
        table.load_rows(ServiceHistoryRepository().get_by_personnel(self.session.original_id)
                        if self.session.original_id is not None else [])

    def show_section(self, name):
        self.session.preview_name(self.personal_fields.inputs['full_name'].get())
        if name not in self.pages:
            if name == 'Дисциплина':
                page = self._page(name, 'Поощрения и взыскания сохранятся вместе с остальной карточкой.')
                self.discipline_page = DisciplineView(page, self.session.discipline, self.session.people,
                                                      self.reference_repository, self.session.personnel_id,
                                                      self.refresh_counts)
                self.discipline_page.pack(fill='both', expand=True)
            else:
                page = self._page(name, 'Добавляйте любое количество записей. Итоговое сохранение — кнопкой «Сохранить всё».')
                CollectionPanel(page, self.session.profile, self.collection_names[name],
                                self.session.personnel_id, self.refresh_counts).pack(fill='both', expand=True)
        for key, page in self.pages.items():
            if key == name:
                page.grid()
            else:
                page.grid_remove()
        for key, control in self.nav.items():
            control.configure(fg_color=theme.PRIMARY if key == name else 'transparent',
                              text_color='white' if key == name else theme.TEXT)

    def refresh_counts(self):
        for title, table in self.collection_names.items():
            count = len(self.session.profile.list_records(table, self.session.personnel_id))
            self.nav[title].configure(text=f'{title} ({count})')
        count = len(self.session.discipline.get_personnel_history(self.session.personnel_id))
        self.nav['Дисциплина'].configure(text=f'Дисциплина ({count})')

    def values(self):
        result = self.personal_fields.values()
        result.update(self.service_fields.values())
        for key, mapping in self.reference_maps.items():
            label = result[key]
            result[key] = mapping.get(label) if label else None
        return result

    def save(self):
        try:
            self.session.save(self.values())
        except (ValueError, sqlite3.Error) as error:
            self.error.configure(text=str(error))
            return
        notify_data_changed(self)
        self.destroy()
        self.on_saved()

    def cancel(self):
        changed = self.values() != self.initial_values or self.session.has_record_changes()
        if changed and not messagebox.askyesno('Несохранённые изменения',
                                               'Закрыть форму и отменить изменения во всех разделах?', parent=self):
            return
        self.destroy()

    def destroy(self):
        previous = getattr(self, 'previous_grab', None)
        session = getattr(self, 'session', None)
        if session:
            session.close()
        super().destroy()
        if previous and previous.winfo_exists():
            grab_when_visible(previous)
