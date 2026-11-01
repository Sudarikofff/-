import customtkinter as ctk
from tkinter import messagebox

import theme

from ui.reference.reference_table import ReferenceTable
from ui.reference.reference_dialog import ReferenceDialog


class ReferenceView(ctk.CTkFrame):

    def __init__(self, parent, repository):
        super().__init__(parent, fg_color=theme.BACKGROUND)

        self.repository = repository
        self.current_reference = "units"
        self.selected_record = None
        self.table_map = {
            "units": "units",
            "positions": "positions",
            "ranks": "ranks",
            "authorities": "authorities",
            "rewards": "event_kinds",
            "penalties": "event_kinds"
        }

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

        self.load_reference("units")

    # ---------------------------------------------------------
    # Левое меню
    # ---------------------------------------------------------

    def _build_sidebar(self):

        sidebar = ctk.CTkFrame(
            self,
            width=220,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER
        )

        sidebar.grid(row=0, column=0, sticky="ns", padx=(20, 10), pady=20)
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="Справочники",
            font=theme.SUBTITLE_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=20, pady=(20, 15))

        items = [
            ("Подразделения", "units"),
            ("Воинские должности", "positions"),
            ("Воинские звания", "ranks"),
            ("Органы", "authorities"),
            ("Поощрения", "rewards"),
            ("Взыскания", "penalties")
        ]

        self.buttons = {}

        for text, key in items:

            btn = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=40,
                fg_color="transparent",
                hover_color="#EAF3E7",
                text_color=theme.TEXT,
                command=lambda k=key: self.load_reference(k)
            )

            btn.pack(fill="x", padx=10, pady=2)

            self.buttons[key] = btn

    # ---------------------------------------------------------
    # Правая часть
    # ---------------------------------------------------------

    def _build_content(self):

        self.content = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER
        )

        self.content.grid(row=0, column=1, sticky="nsew",
                          padx=(10, 20), pady=20)

        self.title_label = ctk.CTkLabel(
            self.content,
            text="",
            font=theme.TITLE_FONT,
            text_color=theme.TEXT
        )

        self.title_label.pack(anchor="w", padx=20, pady=(20, 10))
        self.content.bind('<Configure>', lambda event: self.title_label.configure(wraplength=max(250, event.width-40)))
        # ---------------------------------------------------------
        # Панель кнопок
        # ---------------------------------------------------------

        toolbar = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        toolbar.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            toolbar,
            text="➕ Добавить",
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            width=140,
            command=self.add_record
        ).pack(side="left")

        ctk.CTkButton(
            toolbar,
            text="✏️ Изменить",
            fg_color="#2F6B9A",
            hover_color="#25577D",
            width=140,
            command=self.edit_record
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            toolbar,
            text="🗑 Удалить",
            fg_color=theme.DANGER,
            hover_color="#8E1F13",
            width=140,
            command=self.delete_record
        ).pack(side="left")

        self.table = ReferenceTable(
            self.content,
            on_select=self.select_record
        )

        self.table.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.table.on_open = lambda row: self.edit_record()

    # ---------------------------------------------------------
    # Загрузка справочника
    # ---------------------------------------------------------

    def load_reference(self, key):

        self.current_reference = key
        self.selected_record = None

        titles = {
            "units": "Подразделения",
            "positions": "Воинские должности",
            "ranks": "Воинские звания",
            "authorities": "Органы, применившие меры",
            "rewards": "Виды поощрений",
            "penalties": "Виды взысканий"
        }

        self.title_label.configure(text=titles[key])

        for button_key, button in self.buttons.items():
            button.configure(
                fg_color="#EAF3E7" if button_key == key else "transparent",
                text_color=theme.PRIMARY if button_key == key else theme.TEXT
            )

        # Какие таблицы можно редактировать напрямую
        editable_tables = {
            "units": "units",
            "positions": "positions",
            "ranks": "ranks",
            "authorities": "authorities"
        }

        if key in editable_tables:
            rows = self.repository.get_reference(editable_tables[key])



        elif key == "rewards":

            rows = self.repository.get_event_kinds(event_type_id=self.event_type_id("Поощрение"))


        elif key == "penalties":

            rows = self.repository.get_event_kinds(event_type_id=self.event_type_id("Взыскание"))

        else:
            rows = []

        self.table.load_rows(rows)

    # ======================================================
    # Добавить запись
    # ======================================================

    def add_record(self):

        titles = {
            "units": "Добавить подразделение",
            "positions": "Добавить должность",
            "ranks": "Добавить воинское звание",
            "authorities": "Добавить орган",
            "rewards": "Добавить вид поощрения",
            "penalties": "Добавить вид взыскания"
        }

        ReferenceDialog(
            self,
            title=titles[self.current_reference],
            on_save=self._save_new_record
        )

    def _save_new_record(self, name):

        if self.current_reference == "rewards":

            self.repository.create_event_kind(name, self.event_type_id("Поощрение"))

        elif self.current_reference == "penalties":

            self.repository.create_event_kind(name, self.event_type_id("Взыскание"))

        else:

            self.repository.create_reference(
                self.table_map[self.current_reference],
                name
            )

        self.load_reference(self.current_reference)


    # ======================================================
    # Изменить запись
    # ======================================================

    def edit_record(self):

        if self.selected_record is None:
            messagebox.showwarning(
                "Редактирование",
                "Выберите запись."
            )
            return

        titles = {
            "units": "Изменить подразделение",
            "positions": "Изменить должность",
            "ranks": "Изменить воинское звание",
            "authorities": "Изменить орган",
            "rewards": "Изменить вид поощрения",
            "penalties": "Изменить вид взыскания"
        }

        if self.current_reference not in titles:
            messagebox.showinfo(
                "Недоступно",
                "Этот справочник будет подключён следующим этапом."
            )
            return

        ReferenceDialog(
            self,
            title=titles[self.current_reference],
            value=self.selected_record["name"],
            on_save=self._save_edit_record
        )

    def _save_edit_record(self, name):

        if self.current_reference in ("rewards", "penalties"):

            self.repository.update_event_kind(
                self.selected_record["id"],
                name
            )

        else:

            self.repository.update_reference(
                self.table_map[self.current_reference],
                self.selected_record["id"],
                name
            )

        self.load_reference(self.current_reference)


    # ======================================================
    # Удалить запись
    # ======================================================

    def delete_record(self):

        if self.selected_record is None:
            messagebox.showwarning(
                "Удаление",
                "Выберите запись."
            )
            return

        # Какой таблице соответствует выбранный справочник
        table_map = {
            "units": "units",
            "positions": "positions",
            "ranks": "ranks",
            "authorities": "authorities",
            "rewards": "event_kinds",
            "penalties": "event_kinds"
        }

        if self.current_reference not in table_map:
            messagebox.showinfo(
                "Недоступно",
                "Удаление для этого справочника не поддерживается."
            )
            return

        answer = messagebox.askyesno(
            "Удаление записи",
            f"Удалить запись\n\n{self.selected_record['name']}?"
        )

        if not answer:
            return

        try:
            if self.current_reference in ("rewards", "penalties"):

                self.repository.delete_event_kind(
                    self.selected_record["id"]
                )
                self.load_reference(self.current_reference)

            else:

                can_delete, count = self.repository.can_delete_reference(
                    table_map[self.current_reference],
                    self.selected_record["id"]
                )

                if not can_delete:
                    messagebox.showwarning(
                        "Удаление невозможно",
                        f"Запись используется в {count} месте(ах) базы данных."
                    )
                    return

                self.repository.delete_reference(
                    table_map[self.current_reference],
                    self.selected_record["id"]
                )

                self.load_reference(self.current_reference)

        except Exception as error:
            messagebox.showerror(
                "Ошибка удаления",
                str(error)
            )

    # ---------------------------------------------------------
    # Выбрана запись
    # ---------------------------------------------------------

    def select_record(self, row):
        self.selected_record = row

    def event_type_id(self, name):
        return next(row["id"] for row in self.repository.get_event_types() if row["name"] == name)
