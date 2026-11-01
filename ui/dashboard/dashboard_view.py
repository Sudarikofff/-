import customtkinter as ctk
import theme


class DashboardView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color=theme.BACKGROUND)

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._header()
        self._statistics()
        self._bottom_blocks()

    # =====================================================
    # Заголовок
    # =====================================================

    def _header(self):

        frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        frame.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=25,
            pady=(20, 15)
        )

        ctk.CTkLabel(
            frame,
            text="Главная панель",
            font=theme.TITLE_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text="Учёт дисциплинарной практики • ПС ФСБ РФ",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(5, 0))

    # =====================================================
    # Карточки статистики
    # =====================================================

    def _statistics(self):

        stats = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        stats.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=25
        )

        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.total_card = self._card(
            stats, 0,
            "👤",
            "Военнослужащих",
            "0",
            theme.PRIMARY
        )

        self.reward_card = self._card(
            stats, 1,
            "🏅",
            "Поощрений",
            "0",
            theme.SUCCESS
        )

        self.penalty_card = self._card(
            stats, 2,
            "⚠️",
            "Взысканий",
            "0",
            theme.DANGER
        )

        self.investigation_card = self._card(
            stats, 3,
            "📋",
            "Разбирательств",
            "0",
            theme.WARNING
        )

    def _card(self, parent, column, icon, title, value, color):

        card = ctk.CTkFrame(
            parent,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER
        )

        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=8
        )

        ctk.CTkFrame(
            card,
            fg_color=color,
            height=5,
            corner_radius=20
        ).pack(fill="x")

        ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI Emoji", 26)
        ).pack(anchor="w", padx=18, pady=(18, 0))

        ctk.CTkLabel(
            card,
            text=title,
            font=theme.SMALL_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", padx=18, pady=(5, 0))

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=("DejaVu Sans", 30, "bold"),
            text_color=color
        )

        value_label.pack(anchor="w", padx=18, pady=(0, 18))

        return value_label

    # =====================================================
    # Нижние блоки
    # =====================================================

    def _bottom_blocks(self):

        left = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER
        )

        left.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(25, 12),
            pady=20
        )

        ctk.CTkLabel(
            left,
            text="Последние события",
            font=theme.HEADER_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=20, pady=(18, 15))

        self.events_box = ctk.CTkTextbox(left, height=260)
        self.events_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.events_box.insert(
            "1.0",
            "Добро пожаловать в систему.\n\n"
            "Здесь будут отображаться:\n\n"
            "• последние взыскания;\n"
            "• новые поощрения;\n"
            "• завершённые разбирательства;\n"
            "• изменения в личном составе."
        )

        self.events_box.configure(state="disabled")

        right = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER
        )

        right.grid(
            row=2,
            column=1,
            sticky="nsew",
            padx=(12, 25),
            pady=20
        )

        ctk.CTkLabel(
            right,
            text="Сводка кадрового подразделения",
            font=theme.HEADER_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=20, pady=(18, 15))

        rows = [
            ("Подразделений КПП", "0"),
            ("Воинских должностей", "0"),
            ("Офицеров", "0"),
            ("Прапорщиков", "0"),
            ("Сержантов", "0"),
            ("Солдат", "0"),
        ]

        self.summary_labels = {}

        for title, value in rows:

            line = ctk.CTkFrame(right, fg_color="transparent")
            line.pack(fill="x", padx=20, pady=6)

            ctk.CTkLabel(
                line,
                text=title,
                font=theme.TEXT_FONT,
                text_color=theme.TEXT_SECONDARY
            ).pack(side="left")

            lbl = ctk.CTkLabel(
                line,
                text=value,
                font=("DejaVu Sans", 15, "bold"),
                text_color=theme.TEXT
            )

            lbl.pack(side="right")

            self.summary_labels[title] = lbl

    # =====================================================
    # Обновление статистики
    # =====================================================

    def update_dashboard(self, stats):

        self.total_card.configure(text=str(stats["total"]))
        self.reward_card.configure(text=str(stats["rewards"]))
        self.penalty_card.configure(text=str(stats["penalties"]))
        self.investigation_card.configure(text=str(stats["investigations"]))

        self.summary_labels["Подразделений КПП"].configure(
            text=str(stats["units"])
        )

        self.summary_labels["Воинских должностей"].configure(
            text=str(stats["positions"])
        )

        self.summary_labels["Офицеров"].configure(
            text=str(stats["officers"])
        )

        self.summary_labels["Прапорщиков"].configure(
            text=str(stats["warrant"])
        )

        self.summary_labels["Сержантов"].configure(
            text=str(stats["sergeants"])
        )

        self.summary_labels["Солдат"].configure(
            text=str(stats["soldiers"])
        )