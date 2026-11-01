import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry

import theme
from ui.widgets.modal import grab_when_visible


class RemovePenaltyDialog(ctk.CTkToplevel):

    def __init__(
        self,
        parent,
        repository,
        event_id,
        on_saved
    ):
        super().__init__(parent)

        self.repository = repository
        self.event_id = event_id
        self.on_saved = on_saved

        self.title("Снять дисциплинарное взыскание")
        self.geometry("620x680")
        self.minsize(620, 680)
        self.resizable(False, False)

        self.configure(fg_color=theme.BACKGROUND)
        self.previous_grab = self.grab_current()
        grab_when_visible(self)

        self._build_ui()

    # ======================================================
    # Интерфейс
    # ======================================================

    def _build_ui(self):

        container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text="Снятие дисциплинарного взыскания",
            font=theme.TITLE_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text="Заполните реквизиты приказа о снятии взыскания.",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(4, 20))

        card = ctk.CTkFrame(
            container,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER
        )

        card.pack(fill="x")

        # Дата
        ctk.CTkLabel(
            card,
            text="Дата снятия",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 4))

        date_frame = ctk.CTkFrame(
            card,
            fg_color="white",
            corner_radius=8,
            border_width=1,
            border_color=theme.BORDER
        )

        date_frame.pack(fill="x", padx=15)

        self.removal_date = DateEntry(
            date_frame,
            date_pattern="yyyy-mm-dd",
            borderwidth=0,
            background="white",
            foreground="black"
        )

        self.removal_date.pack(fill="x", padx=8, pady=6)

        # Документ
        ctk.CTkLabel(
            card,
            text="Номер приказа",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 4))

        self.document = ctk.CTkEntry(
            card,
            height=38,
            fg_color="white",
            border_color=theme.BORDER,
            text_color=theme.TEXT
        )

        self.document.pack(fill="x", padx=15)

        # Основание
        ctk.CTkLabel(
            card,
            text="Основание снятия",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 4))

        self.reason = ctk.CTkTextbox(
            card,
            height=90,
            fg_color="white",
            border_color=theme.BORDER,
            text_color=theme.TEXT
        )

        self.reason.pack(fill="x", padx=15)

        # Комментарий
        ctk.CTkLabel(
            card,
            text="Комментарий",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 4))

        self.comment = ctk.CTkTextbox(
            card,
            height=90,
            fg_color="white",
            border_color=theme.BORDER,
            text_color=theme.TEXT
        )

        self.comment.pack(fill="x", padx=15, pady=(0, 15))

        buttons = ctk.CTkFrame(
            container,
            fg_color="transparent",
            height=60
        )

        buttons.pack(fill="x", side="bottom", pady=(20, 0))
        buttons.pack_propagate(False)

        ctk.CTkButton(
            buttons,
            text="✅ Снять взыскание",
            fg_color=theme.SUCCESS,
            hover_color="#256428",
            command=self._save
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Отмена",
            fg_color="#64748B",
            hover_color="#475569",
            command=self.destroy
        ).pack(side="right")

    # ======================================================
    # Сохранение
    # ======================================================

    def _save(self):

        document = self.document.get().strip()

        if not document:
            messagebox.showwarning(
                "Ошибка",
                "Введите номер приказа."
            )
            return

        try:

            self.repository.remove_penalty(
                event_id=self.event_id,
                removal_date=self.removal_date.get_date().strftime("%Y-%m-%d"),
                removal_document=document,
                removal_basis=self.reason.get("1.0", "end").strip(),
                removal_comment=self.comment.get("1.0", "end").strip()
            )

            self.on_saved()
            self.destroy()

            messagebox.showinfo(
                "Готово",
                "Снятие внесено в форму. Для сохранения карточки нажмите «Сохранить всё»."
                if getattr(self.repository, "is_draft", False) else "Взыскание успешно снято."
            )

        except Exception as error:

            messagebox.showerror(
                "Ошибка",
                str(error)
            )

    def destroy(self):
        previous = getattr(self, "previous_grab", None)
        super().destroy()
        if previous and previous.winfo_exists():
            grab_when_visible(previous)
