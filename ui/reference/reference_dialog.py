import customtkinter as ctk
from tkinter import messagebox

import theme
from ui.widgets.modal import grab_when_visible


class ReferenceDialog(ctk.CTkToplevel):

    def __init__(
        self,
        parent,
        title,
        on_save,
        value=""
    ):
        super().__init__(parent)

        self.on_save = on_save

        self.title(title)
        self.geometry("640x230")
        self.minsize(520, 230)

        self.configure(fg_color=theme.BACKGROUND)

        self.transient(parent.winfo_toplevel())
        grab_when_visible(self)

        frame = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=theme.BORDER
        )

        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            frame,
            text="Название",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.entry = ctk.CTkEntry(
            frame,
            height=38,
            corner_radius=10,
            fg_color="#FFFFFF",
            border_color="#C8D6C8",
            text_color="#173B2A"
        )

        self.entry.pack(fill="x", padx=15)

        if value:
            self.entry.insert(0, value)

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            buttons,
            text="💾 Сохранить",
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            command=self.save
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Отмена",
            fg_color="#EEF2EE",
            hover_color="#DCE6DB",
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            command=self.destroy
        ).pack(side="right")

    def save(self):

        name = self.entry.get().strip()

        if not name:
            messagebox.showwarning(
                "Заполните данные",
                "Введите название."
            )
            return

        import sqlite3
        try:
            self.on_save(name)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Не удалось сохранить', str(error), parent=self)
            return
        self.destroy()
