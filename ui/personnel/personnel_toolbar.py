from ui.widgets.filter_controls import label_filter
import customtkinter as ctk
import theme


class PersonnelToolbar(ctk.CTkFrame):

    def __init__(
        self,
        parent,
        reference_repository,
        on_search,
        on_add,
        on_edit,
        on_archive,
        on_refresh
    ):
        super().__init__(
            parent,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER
        )

        self.reference_repository = reference_repository

        self.on_search = on_search
        self.on_add = on_add
        self.on_edit = on_edit
        self.on_archive = on_archive
        self.on_refresh = on_refresh

        self.grid_columnconfigure(1, weight=1)

        self._load_references()
        self._build_ui()

    # ---------------------------------------------------------
    # Справочники
    # ---------------------------------------------------------

    def _load_references(self):

        self.units = ["Все подразделения"]
        self.units.extend(
            row["name"]
            for row in self.reference_repository.get_units()
        )

        self.ranks = ["Все звания"]
        self.ranks.extend(
            row["name"]
            for row in self.reference_repository.get_ranks()
        )

    # ---------------------------------------------------------
    # Интерфейс
    # ---------------------------------------------------------

    def _build_ui(self):
        # ---------- Заголовок ----------

        title = ctk.CTkLabel(
            self,
            text="Личный состав КПП",
            font=("DejaVu Sans", 20, "bold"),
            text_color=theme.TEXT
        )

        title.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

        subtitle = ctk.CTkLabel(
            self,
            text="Поиск и фильтрация военнослужащих",
            font=theme.SMALL_FONT,
            text_color=theme.TEXT_SECONDARY
        )

        subtitle.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

        # ---------- Поиск ----------

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="🔍 Поиск по ФИО или личному номеру...",
            height=42,
            corner_radius=10,

            fg_color=theme.INPUT_BG,
            border_color=theme.INPUT_BORDER,
            border_width=1,

            text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.PLACEHOLDER
        )

        self.search_entry.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20
        )

        self.search_entry.bind("<KeyRelease>", self._filters_changed)

        # ---------- Фильтры ----------

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=18
        )

        filters.grid_columnconfigure((0, 1, 2), weight=1)

        combo_style = {
            "height": 40,
            "corner_radius": 10,
            "fg_color": theme.INPUT_BG,
            "border_color": theme.INPUT_BORDER,
            "button_color": theme.DROPDOWN_BUTTON,
            "button_hover_color": theme.DROPDOWN_BUTTON_HOVER,
            "dropdown_fg_color": theme.DROPDOWN_BG,
            "dropdown_hover_color": theme.DROPDOWN_HOVER,
            "dropdown_text_color": theme.INPUT_TEXT,
            "text_color": theme.INPUT_TEXT
        }

        self.unit_combo = ctk.CTkComboBox(
            filters,
            values=self.units,
            command=lambda _: self._filters_changed(),
            **combo_style
        )

        self.unit_combo.set("Все подразделения")
        self.unit_combo.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.rank_combo = ctk.CTkComboBox(
            filters,
            values=self.ranks,
            command=lambda _: self._filters_changed(),
            **combo_style
        )

        self.rank_combo.set("Все звания")
        self.rank_combo.grid(row=0, column=1, sticky="ew", padx=10)

        self.status_combo = ctk.CTkComboBox(
            filters,
            values=[
                "Все статусы",
                "Служит",
                "Командировка",
                "Отпуск",
                "Архив"
            ],
            command=lambda _: self._filters_changed(),
            **combo_style
        )

        self.status_combo.set("Все статусы")
        self.status_combo.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        label_filter(self.search_entry,'Поиск по ФИО или личному номеру')
        label_filter(self.unit_combo,'Подразделение')
        label_filter(self.rank_combo,'Воинское звание')
        label_filter(self.status_combo,'Статус')

        # ---------- Кнопки ----------

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(0, 18)
        )

        ctk.CTkButton(
            buttons,
            text="➕ Добавить",
            width=150,
            height=40,
            corner_radius=10,
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            text_color="white",
            font=theme.BUTTON_FONT,
            command=self.on_add
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="✏️ Редактировать",
            width=150,
            height=40,
            corner_radius=10,
            fg_color="#E8ECE8",
            hover_color="#D8E0D8",
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            font=theme.BUTTON_FONT,
            command=self.on_edit
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            buttons,
            text="📦 Архивировать",
            width=160,
            height=40,
            corner_radius=10,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color="white",
            font=theme.BUTTON_FONT,
            command=self.on_archive
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            buttons,
            text="🔄 Обновить",
            width=140,
            height=40,
            corner_radius=10,
            fg_color="#E8ECE8",
            hover_color="#D8E0D8",
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            font=theme.BUTTON_FONT,
            command=self.on_refresh
        ).pack(side="right")

    # ---------------------------------------------------------
    # Возвращает фильтры
    # ---------------------------------------------------------

    def get_filters(self):

        return {
            "search_text": self.search_entry.get().strip(),
            "unit": self.unit_combo.get(),
            "rank": self.rank_combo.get(),
            "status": self.status_combo.get()
        }

    # ---------------------------------------------------------
    # Изменение фильтров
    # ---------------------------------------------------------

    def _filters_changed(self, event=None):
        self.on_search(self.get_filters())