import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry

import theme
from ui.widgets.modal import grab_when_visible
from personnel_fields import parse_date, display_date
from database.discipline_repository import REMOVAL_REWARD


class DisciplineForm(ctk.CTkToplevel):

    def __init__(
            self,
            parent,
            personnel_repository,
            discipline_repository,
            reference_repository,
            on_saved,
            event_type=None,
            event=None,
            personnel_id=None
    ):
        super().__init__(parent)

        self.personnel_repository = personnel_repository
        self.discipline_repository = discipline_repository
        self.reference_repository = reference_repository
        self.on_saved = on_saved
        self.event = event
        self.default_event_type = event_type
        self.personnel_id = personnel_id

        self.title(
            "Добавить дисциплинарное событие"
            if event is None
            else "Редактировать дисциплинарное событие"
        )

        self.geometry("900x720")
        self.minsize(900, 720)

        self.configure(fg_color=theme.BACKGROUND)
        self.previous_grab = self.grab_current()
        grab_when_visible(self)

        self._load_references()
        self._build_ui()

        if event:
            self._fill_form()

    # ======================================================
    # Загрузка справочников
    # ======================================================

    def _load_references(self):

        # Военнослужащие
        self.personnel_rows = self.personnel_repository.get_all()

        self.personnel_map = {
            self.person_label(row): row["id"]
            for row in self.personnel_rows
        }

        # Типы событий
        self.event_types = self.reference_repository.get_event_types()

        self.event_type_map = {
            row["name"]: row["id"]
            for row in self.event_types
        }

        # Органы
        self.authority_rows = self.reference_repository.get_authorities()

        self.authority_map = {
            row["name"]: row["id"]
            for row in self.authority_rows
        }

    # ======================================================
    # Интерфейс
    # ======================================================

    def _build_ui(self):

        container = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.BACKGROUND,
            scrollbar_button_color="#D6E3D4",
            scrollbar_button_hover_color="#BFD3BC"
        )

        container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        ctk.CTkLabel(
            container,
            text="Учёт дисциплинарной практики",
            font=theme.TITLE_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text="Добавление поощрения или дисциплинарного взыскания",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(5, 20))

        self.main_section = self._section(
            container,
            "Основные сведения"
        )

        self.extra_section = self._section(
            container,
            "Основание и комментарий"
        )

        self._build_main_fields()
        self._build_extra_fields()
        self._build_deadline_and_removal()

        self._build_buttons(container)

    # ======================================================
    # Основные поля формы
    # ======================================================

    def _build_main_fields(self):

        frame = self.main_section

        # Военнослужащий
        ctk.CTkLabel(
            frame,
            text="Военнослужащий",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.personnel = ctk.CTkComboBox(
            frame,
            values=sorted(self.personnel_map.keys()) or [""],
            command=lambda value: self._refresh_removals(),
            height=36,

            fg_color=theme.INPUT_BG,
            border_color=theme.INPUT_BORDER,
            button_color=theme.DROPDOWN_BUTTON,
            button_hover_color=theme.DROPDOWN_BUTTON_HOVER,
            dropdown_fg_color=theme.DROPDOWN_BG,
            dropdown_hover_color=theme.DROPDOWN_HOVER,
            dropdown_text_color=theme.INPUT_TEXT,
            text_color=theme.INPUT_TEXT
        )

        # Если форма открыта из личного дела — сразу выбираем военнослужащего.
        # Если форма открыта из личного дела — сразу выбираем военнослужащего.
        if self.personnel_id is not None:

            person = self.personnel_repository.get_by_id(self.personnel_id)

            if person:
                self.personnel.set(self.person_label(person))
                self.personnel.configure(state="disabled")
        self.personnel.pack(fill="x", padx=15, pady=(0, 12))

        # Тип события
        ctk.CTkLabel(
            frame,
            text="Тип события",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.event_type = ctk.CTkComboBox(
            frame,
            values=["Поощрение", "Взыскание"],
            height=38,
            corner_radius=10,
            command=self._event_type_changed,

            fg_color="#FFFFFF",
            border_color="#C8D6C8",
            text_color="#173B2A",

            button_color="#EAF3E7",
            button_hover_color="#DCEAD8",

            dropdown_fg_color="#FFFFFF",
            dropdown_hover_color="#EEF6EC",
            dropdown_text_color="#173B2A"
        )

        self.event_type.pack(fill="x", padx=15, pady=(0, 12))

        if self.default_event_type:
            self.event_type.set(self.default_event_type)
        else:
            self.event_type.set("Поощрение")

        # Вид события
        ctk.CTkLabel(
            frame,
            text="Вид события",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.event_kind = ctk.CTkComboBox(
            frame,
            values=[],
            command=lambda value: self._refresh_removals(),
            height=38,
            corner_radius=10,

            fg_color="#FFFFFF",
            border_color="#C8D6C8",
            text_color="#173B2A",

            button_color="#EAF3E7",
            button_hover_color="#DCEAD8",

            dropdown_fg_color="#FFFFFF",
            dropdown_hover_color="#EEF6EC",
            dropdown_text_color="#173B2A"
        )
        self.event_kind.pack(fill="x", padx=15, pady=(0, 12))

        self._event_type_changed(self.event_type.get())

        # Орган
        ctk.CTkLabel(
            frame,
            text="Орган, применивший меру",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.authority = ctk.CTkComboBox(
            frame,
            values=list(self.authority_map.keys()),
            height=38,
            corner_radius=10,

            fg_color="#FFFFFF",
            border_color="#C8D6C8",
            text_color="#173B2A",

            button_color="#EAF3E7",
            button_hover_color="#DCEAD8",

            dropdown_fg_color="#FFFFFF",
            dropdown_hover_color="#EEF6EC",
            dropdown_text_color="#173B2A"
        )

        self.authority.pack(fill="x", padx=15, pady=(0, 12))

        # Дата
        ctk.CTkLabel(
            frame,
            text="Дата события",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.event_date = DateEntry(
            frame,
            date_pattern="yyyy-mm-dd",
            width=18,

            background="#0F5B35",
            foreground="white",

            borderwidth=1,

            selectbackground="#0F5B35",
            selectforeground="white",

            normalbackground="white",
            normalforeground="#173B2A",

            weekendbackground="white",
            weekendforeground="#173B2A",

            headersbackground="#EAF3E7",
            headersforeground="#173B2A"
        )

        self.event_date.pack(fill="x", padx=15, pady=(0, 12))

        # Номер документа
        ctk.CTkLabel(
            frame,
            text="Номер приказа / документа",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.document_number = ctk.CTkEntry(
            frame,
            height=36,

            fg_color=theme.INPUT_BG,
            border_color=theme.INPUT_BORDER,
            text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.PLACEHOLDER
        )

        self.document_number.pack(fill="x", padx=15, pady=(0, 12))

        # Статус
        ctk.CTkLabel(
            frame,
            text="Статус",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.status = ctk.CTkComboBox(
            frame,
            values=["Активно", "Снято"],
            height=38,
            corner_radius=10,

            fg_color="#FFFFFF",
            border_color="#C8D6C8",
            text_color="#173B2A",

            button_color="#EAF3E7",
            button_hover_color="#DCEAD8",

            dropdown_fg_color="#FFFFFF",
            dropdown_hover_color="#EEF6EC",
            dropdown_text_color="#173B2A"
        )

        self.status.set("Активно")
        self.status.configure(state="disabled")
        self.status.pack(fill="x", padx=15, pady=(0, 15))

    # ======================================================
    # Основание и комментарий
    # ======================================================

    def _build_extra_fields(self):

        frame = self.extra_section

        ctk.CTkLabel(
            frame,
            text="Основание",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.basis = ctk.CTkTextbox(
            frame,
            height=120,

            fg_color=theme.INPUT_BG,
            border_width=1,
            border_color=theme.INPUT_BORDER,
            text_color=theme.INPUT_TEXT
        )

        self.basis.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            frame,
            text="Комментарий",
            font=theme.TEXT_FONT
        ).pack(anchor="w", padx=15, pady=(10, 2))

        self.comment = ctk.CTkTextbox(
            frame,
            height=120,

            fg_color="#FFFFFF",
            border_width=1,
            border_color="#C8D6C8",

            text_color="#173B2A",
            corner_radius=10
        )

        self.comment.pack(fill="x", padx=15, pady=(0, 15))

    # ======================================================
    # Кнопки
    # ======================================================

    def _build_buttons(self, parent):

        frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            frame,
            text="💾 Сохранить",
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            height=42,
            font=theme.BUTTON_FONT,
            command=self._save
        ).pack(side="left")

        ctk.CTkButton(
            frame,
            text="Отмена",
            fg_color="#E8ECE8",
            hover_color="#D8E0D8",
            text_color=theme.TEXT,
            border_width=1,
            border_color=theme.BORDER,
            height=42,
            command=self.destroy
        ).pack(side="right")

    # ======================================================
    # Переключение типа события
    # ======================================================

    def _event_type_changed(self, event_type):

        event_type_id = self.event_type_map.get(event_type)

        kinds = self.reference_repository.get_event_kinds(event_type_id)

        self.event_kind_rows = kinds

        values = [row["name"] for row in kinds]

        if not values:
            values = ["Нет записей"]

        self.event_kind.configure(values=values)
        self.event_kind.set(values[0])
        if hasattr(self, "removal_frame"):
            self._refresh_removals()

    # ======================================================
    # Карточка раздела
    # ======================================================

    def _section(self, parent, title):

        frame = ctk.CTkFrame(
            parent,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER
        )

        frame.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            frame,
            text=title,
            font=theme.SUBTITLE_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 10))

        return frame

    # ======================================================
    # Заполнение формы при редактировании
    # ======================================================

    def _fill_form(self):

        event = self.event

        self.personnel.set(self.person_label(self.personnel_repository.get_by_id(event["personnel_id"])))
        self.event_type.set(event["event_type"])
        self._event_type_changed(event["event_type"])

        self.event_kind.set(event["event_kind"])
        self.authority.set(event["authority_name"] or "")

        if event["event_date"]:
            self.event_date.set_date(event["event_date"])

        self.document_number.insert(
            0,
            event["document_number"] or ""
        )

        self.status.set(event["status"] or "Активно")
        self.due_date.insert(0, display_date(event["due_date"]))
        self._refresh_removals()

        if event["basis"]:
            self.basis.insert("1.0", event["basis"])

        if event["comment"]:
            self.comment.insert("1.0", event["comment"])

    # ======================================================
    # Сохранение
    # ======================================================

    def _save(self):

        if self.personnel_id is not None:
            personnel_id = self.personnel_id
        else:
            full_name = self.personnel.get()

            if full_name not in self.personnel_map:
                messagebox.showwarning(
                    "Ошибка",
                    "Выберите военнослужащего из списка."
                )
                return

            personnel_id = self.personnel_map[full_name]

        event_kind = self.event_kind.get()
        known_kinds = {row["name"] for row in self.event_kind_rows}

        if event_kind not in known_kinds:
            messagebox.showwarning(
                "Ошибка",
                "Добавьте и выберите вид дисциплинарного события в справочнике."
            )
            return

        data = {

            "personnel_id": personnel_id,

            "event_type": self.event_type.get(),
            "event_kind": event_kind,
            "authority_name": self.authority.get(),

            "event_date": self.event_date.get_date().strftime("%Y-%m-%d"),

            "document_number": self.document_number.get().strip(),

            "basis": self.basis.get("1.0", "end").strip(),

            "comment": self.comment.get("1.0", "end").strip(),

            "status": self.status.get(),
            "due_date": self.due_date.get().strip() or None,
            "removed_event_id": self.removal_map.get(self.removal_choice.get()) if self.event_kind.get()==REMOVAL_REWARD else None

        }

        try:

            if self.event is None:

                self.discipline_repository.create(**data)

                messagebox.showinfo(
                    "Добавлено в форму" if getattr(self.discipline_repository, "is_draft", False) else "Сохранено",
                    "Событие добавлено в форму. Для сохранения карточки нажмите «Сохранить всё»."
                    if getattr(self.discipline_repository, "is_draft", False) else "Дисциплинарное событие добавлено.",
                    parent=self
                )

            else:

                self.discipline_repository.update(
                    self.event["id"],
                    **data
                )

                messagebox.showinfo(
                    "Изменено в форме" if getattr(self.discipline_repository, "is_draft", False) else "Сохранено",
                    "Запись изменена в форме. Для сохранения карточки нажмите «Сохранить всё»."
                    if getattr(self.discipline_repository, "is_draft", False) else "Запись обновлена.",
                    parent=self
                )

            self.on_saved()

            self.destroy()

        except Exception as error:

            messagebox.showerror(
                "Ошибка сохранения",
                str(error)
            )

    @staticmethod
    def person_label(row):
        return f"{row['full_name']} · {row['personal_number'] or 'без номера'} · #{row['id']}"

    def _build_deadline_and_removal(self):
        frame = self.extra_section
        ctk.CTkLabel(frame, text="Срок контроля (необязательно, ДД.ММ.ГГГГ)", text_color=theme.TEXT).pack(anchor="w", padx=15)
        self.due_date = ctk.CTkEntry(frame, placeholder_text="ДД.ММ.ГГГГ", fg_color=theme.INPUT_BG, text_color=theme.TEXT)
        self.due_date.pack(fill="x", padx=15, pady=(0,12))
        self.removal_frame = ctk.CTkFrame(frame, fg_color=theme.WARNING_BG)
        ctk.CTkLabel(self.removal_frame, text="Какое взыскание снимается", text_color=theme.TEXT).pack(anchor="w", padx=12, pady=6)
        self.removal_choice = ctk.CTkComboBox(self.removal_frame, values=[""], state="readonly", text_color=theme.TEXT, fg_color=theme.CARD)
        self.removal_choice.pack(fill="x", padx=12, pady=(0,12))
        self.removal_map = {}
        self._refresh_removals()

    def _refresh_removals(self):
        if not hasattr(self, "removal_frame"):
            return
        if self.event_type.get() != "Поощрение" or self.event_kind.get() != REMOVAL_REWARD:
            self.removal_frame.pack_forget()
            return
        self.removal_frame.pack(fill="x", padx=15, pady=(0,15))
        pid = self.personnel_id or self.personnel_map.get(self.personnel.get())
        rows = self.discipline_repository.get_personnel_history(pid) if pid else []
        linked = self.event["linked_penalty_id"] if self.event else None
        eligible = [r for r in rows if r["event_type"] == "Взыскание" and (r["status"] == "Активно" or r["id"] == linked)]
        self.removal_map = {f"#{r['id']} · {display_date(r['event_date'])} · {r['event_kind']} · приказ {r['document_number'] or '—'}": r['id'] for r in eligible}
        values = list(self.removal_map) or ["Нет активных взысканий"]
        self.removal_choice.configure(values=values, state="readonly")
        self.removal_choice.set(next((label for label, ident in self.removal_map.items() if ident == linked), values[0]))
        if linked:
            self.removal_choice.configure(state="disabled")

    def destroy(self):
        previous = getattr(self, "previous_grab", None)
        super().destroy()
        if previous and previous.winfo_exists():
            grab_when_visible(previous)
