import customtkinter as ctk
from tkinter import messagebox

import theme
from ui.widgets.data_events import notify_data_changed

from ui.personnel.personnel_toolbar import PersonnelToolbar
from ui.personnel.personnel_table import PersonnelTable
from ui.personnel.personnel_form import PersonnelForm
from ui.personnel.personnel_card import PersonnelCard


class PersonnelView(ctk.CTkFrame):

    def __init__(self, parent, repository, reference_repository):
        super().__init__(parent, fg_color=theme.BACKGROUND)

        self.repository = repository
        self.reference_repository = reference_repository

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Панель поиска и кнопок
        self.toolbar = PersonnelToolbar(
            self,
            reference_repository=self.reference_repository,
            on_search=self.search,
            on_add=self.add_personnel,
            on_edit=self.edit_personnel,
            on_archive=self.archive_personnel,
            on_refresh=self.refresh
        )

        self.toolbar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 10)
        )

        # Панель статистики
        self.stats_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.stats_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10)
        )

        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.total_label = self._stat_card(
            0, "👤 Военнослужащих", theme.PRIMARY
        )

        self.active_label = self._stat_card(
            1, "🟢 На службе", theme.SUCCESS
        )

        self.archive_label = self._stat_card(
            2, "📦 Архив", "#6B7280"
        )

        # Таблица
        self.table = PersonnelTable(
            self,
            on_open=self.open_personnel
        )

        self.table.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 10)
        )

        # Нижняя строка
        footer = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        footer.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 15)
        )

        self.count_label = ctk.CTkLabel(
            footer,
            text="Всего записей: 0",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        )

        self.count_label.pack(side="left")

        self.refresh()

    # ======================================================
    # Карточка статистики
    # ======================================================

    def _stat_card(self, column, title, color):

        card = ctk.CTkFrame(
            self.stats_frame,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER
        )

        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=5
        )

        ctk.CTkLabel(
            card,
            text=title,
            font=theme.SMALL_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=15, pady=(12, 2))

        value = ctk.CTkLabel(
            card,
            text="0",
            font=("DejaVu Sans", 24, "bold"),
            text_color=color
        )

        value.pack(anchor="w", padx=15, pady=(0, 12))

        return value

    # ======================================================
    # Обновление данных
    # ======================================================

    def refresh(self):

        self.toolbar._load_references()
        self.toolbar.unit_combo.configure(values=self.toolbar.units)
        self.toolbar.rank_combo.configure(values=self.toolbar.ranks)
        self.search(self.toolbar.get_filters())

    # ======================================================
    # Статистика
    # ======================================================

    def _update_statistics(self, rows):

        total = len(rows)

        active = sum(
            1 for row in rows
            if row["service_status"] == "Служит"
        )

        archive = sum(
            1 for row in rows
            if row["service_status"] == "Архив"
        )

        self.total_label.configure(text=str(total))
        self.active_label.configure(text=str(active))
        self.archive_label.configure(text=str(archive))

        self.count_label.configure(
            text=f"Всего записей: {total}"
        )

    # ======================================================
    # Поиск и фильтры
    # ======================================================

    def search(self, filters):

        search_text = filters["search_text"]
        unit = filters["unit"]
        rank = filters["rank"]
        status = filters["status"]

        needle = search_text.casefold()
        rows = [row for row in self.repository.get_all()
                if needle in f"{row['full_name']} {row['personal_number'] or ''}".casefold()]

        # Фильтр подразделения
        if unit != "Все подразделения":
            rows = [
                row for row in rows
                if row["unit_name"] == unit
            ]

        # Фильтр звания
        if rank != "Все звания":
            rows = [
                row for row in rows
                if row["rank_name"] == rank
            ]

        # Фильтр статуса
        if status != "Все статусы":
            rows = [
                row for row in rows
                if row["service_status"] == status
            ]

        self.table.load_rows(rows)
        self._update_statistics(rows)

    # ======================================================
    # Добавить
    # ======================================================

    def add_personnel(self):

        PersonnelForm(
            self,
            repository=self.repository,
            reference_repository=self.reference_repository,
            personnel=None,
            on_saved=self.refresh
        )

    # ======================================================
    # Редактировать
    # ======================================================

    def edit_personnel(self):

        row = self.table.selected()

        if row is None:
            messagebox.showwarning(
                "Редактирование",
                "Выберите военнослужащего."
            )
            return

        PersonnelForm(
            self,
            repository=self.repository,
            reference_repository=self.reference_repository,
            personnel=self.repository.get_by_id(row["id"]),
            on_saved=self.refresh
        )

    # ======================================================
    # Архивировать
    # ======================================================

    def archive_personnel(self):

        row = self.table.selected()

        if row is None:
            messagebox.showwarning(
                "Архив",
                "Выберите военнослужащего."
            )
            return

        answer = messagebox.askyesno(
            "Архивирование",
            f"Перевести\n\n{row['full_name']}\n\nв архив?"
        )

        if not answer:
            return

        self.repository.change_status(row["id"], "Архив")
        notify_data_changed(self)

        self.refresh()

    # ======================================================
    # Открыть карточку
    # ======================================================

    def open_personnel(self, row):

        # Если карточка уже открыта — закрываем её
        if hasattr(self, "card_window") and self.card_window.winfo_exists():
            self.card_window.destroy()

        # PersonnelCard сам создаёт CTkToplevel
        self.card_window = PersonnelCard(
            self,
            personnel_repository=self.repository,
            reference_repository=self.reference_repository,
            personnel_id=row["id"]
        )