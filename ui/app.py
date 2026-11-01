import customtkinter as ctk
from datetime import datetime
import sqlite3
from database.osago_notifications import OsagoNotifications
from database.notification_center import NotificationCenter, OsagoNotificationProvider
from ui.notifications_view import NotificationsView, NotificationSettingsView
from ui.reference.reference_view import ReferenceView
from ui.deadlines_view import DeadlinesView


import theme

from database.repositories import PersonnelRepository, ReferenceRepository
from database.discipline_repository import DisciplineRepository

from ui.personnel.personnel_view import PersonnelView
from ui.discipline.discipline_view import DisciplineView


class CadryApp(ctk.CTk):

    def __init__(self):
        ctk.set_appearance_mode("light")
        super().__init__()

        self.title(theme.APP_NAME)
        self.geometry("1440x900")
        self.minsize(1280, 760)
        self.configure(fg_color=theme.BACKGROUND)

        self.personnel_repository = PersonnelRepository()
        self.reference_repository = ReferenceRepository()
        self.discipline_repository = DisciplineRepository()

        self.osago_notifications = OsagoNotifications()
        self.notifications = NotificationCenter([OsagoNotificationProvider(self.osago_notifications)])
        self.notification_state = None
        self.banner_visible = False

        self.pages = {}
        self.menu_buttons = {}

        self._create_layout()
        self.show_page("personnel")
        self.bind("<<PersonnelDataChanged>>", self._personnel_data_changed)
        self.after_idle(self._start_notifications)

    # ======================================================
    # Общий макет окна
    # ======================================================

    def _create_layout(self):

        self.sidebar = ctk.CTkFrame(
            self,
            width=260,
            fg_color=theme.SIDEBAR,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = ctk.CTkFrame(
            self,
            fg_color=theme.BACKGROUND,
            corner_radius=0
        )
        self.main_area.pack(side="left", fill="both", expand=True)

        self._create_sidebar()
        self._create_topbar()
        self._create_notification_banner()
        self._create_content()

    # ======================================================
    # Левая панель
    # ======================================================

    def _create_sidebar(self):

        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(22, 12))

        ctk.CTkLabel(header, text=theme.APP_NAME,
                     font=("DejaVu Sans", 18, "bold"), text_color=theme.SECONDARY).pack(anchor="w")
        ctk.CTkLabel(header, text=f"Пограничная служба ФСБ России, версия {theme.APP_VERSION}",
                     font=theme.SMALL_FONT, text_color="#D7E4D7",
                     wraplength=220, justify="left").pack(anchor="w", pady=(4, 8))

        ctk.CTkFrame(
            self.sidebar,
            fg_color=theme.SECONDARY,
            height=2
        ).pack(fill="x", padx=18, pady=(0, 20))

        menu = [
            ("personnel", "Военнослужащие"),
            ("discipline", "Дисциплинарная практика"),
            ("deadlines", "Контроль сроков"),
            ("references", "Справочники"),
            ("notifications", "Уведомления"),
            ("settings", "Настройки")
        ]

        for page_name, title in menu:
            button = ctk.CTkButton(
                self.sidebar,
                text="   " + title,
                anchor="w",
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color=theme.SIDEBAR_LIGHT,
                text_color="white",
                font=("DejaVu Sans", 13, "bold"),
                command=lambda p=page_name: self.show_page(p)
            )

            button.pack(fill="x", padx=10, pady=4)
            self.menu_buttons[page_name] = button

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True, fill="both")

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=20)

        # Дата
        self.date_label = ctk.CTkLabel(
            footer,
            text="",
            font=("DejaVu Sans", 11),
            text_color=theme.SECONDARY
        )
        self.date_label.pack(anchor="w")

        # Время
        self.time_label = ctk.CTkLabel(
            footer,
            text="",
            font=("DejaVu Sans", 20, "bold"),
            text_color="white"
        )
        self.time_label.pack(anchor="w", pady=(2, 8))

        ctk.CTkButton(footer, text="О программе", command=self.show_about,
                      fg_color=theme.SECONDARY, hover_color=theme.SECONDARY_HOVER,
                      bg_color=theme.SIDEBAR, border_width=1, border_color=theme.SECONDARY,
                      text_color=theme.SIDEBAR, text_color_disabled=theme.TEXT_SECONDARY,
                      state="normal", height=34).pack(anchor="w")

        self._update_clock()

    # ======================================================
    # Верхняя панель
    # ======================================================

    def show_about(self):
        existing = getattr(self, "about_window", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_set()
            return
        window = self.about_window = ctk.CTkToplevel(self)
        window.title("О программе")
        window.geometry("560x430")
        window.resizable(False, False)
        window.configure(fg_color=theme.BACKGROUND)
        window.transient(self)
        ctk.CTkLabel(window, text=theme.APP_NAME, font=theme.TITLE_FONT,
                     text_color=theme.PRIMARY).pack(pady=(24, 8))
        ctk.CTkLabel(window, text=f"Пограничная служба ФСБ России\nВерсия {theme.APP_VERSION}",
                     text_color=theme.TEXT).pack(pady=(0, 16))
        for title, value in (
            ("Разработчик", "Судариков Владимир Александрович"),
            ("Телефон", "+7 (924) 137-62-78"),
            ("Электронная почта", "Sudarikov12345@gmail.com"),
        ):
            ctk.CTkLabel(window, text=title, text_color=theme.TEXT_SECONDARY).pack(anchor="w", padx=28)
            entry = ctk.CTkEntry(window, textvariable=ctk.StringVar(value=value),
                                 state="readonly", text_color=theme.TEXT)
            entry.pack(fill="x", padx=28, pady=(0, 8))
        ctk.CTkButton(window, text="Закрыть", command=window.destroy,
                      fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER).pack(pady=12)

    def _create_topbar(self):

        topbar = ctk.CTkFrame(
            self.main_area,
            height=74,
            fg_color=theme.CARD,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=0
        )
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        left = ctk.CTkFrame(topbar, fg_color="transparent")
        left.pack(side="left", padx=24)

        self.page_title = ctk.CTkLabel(
            left,
            text=theme.APP_NAME,
            font=("DejaVu Sans", 22, "bold"),
            text_color=theme.TEXT
        )
        self.page_title.pack(anchor="w")

        self.page_subtitle = ctk.CTkLabel(
            left,
            text=f"Пограничная служба ФСБ России, версия {theme.APP_VERSION}",
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        )
        self.page_subtitle.pack(anchor="w")

        right = ctk.CTkFrame(topbar, fg_color="transparent")
        right.pack(side="right", padx=24)

        self.notification_button = ctk.CTkButton(
            right, text="🔔 Уведомления · 0", width=195, height=36,
            fg_color=theme.PRIMARY, hover_color=theme.PRIMARY_HOVER,
            command=lambda: self.show_page("notifications")
        )
        self.notification_button.pack(side="left", padx=(0, 16))
        now = datetime.now()

        ctk.CTkLabel(
            right,
            text=now.strftime("%d.%m.%Y"),
            font=theme.TEXT_FONT,
            text_color=theme.TEXT_SECONDARY
        ).pack(side="left")

    # ======================================================
    # Контейнер страниц
    # ======================================================

    def _create_content(self):

        self.container = ctk.CTkFrame(
            self.main_area,
            fg_color=theme.BACKGROUND,
            corner_radius=0
        )
        self.container.pack(fill="both", expand=True, padx=18, pady=18)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._create_pages()

    # ======================================================
    # Страницы
    # ======================================================

    def _create_pages(self):

        self.pages["personnel"] = PersonnelView(
            self.container,
            repository=self.personnel_repository,
            reference_repository=self.reference_repository
        )

        self.pages["discipline"] = DisciplineView(
            self.container,
            repository=self.discipline_repository,
            personnel_repository=self.personnel_repository,
            reference_repository=self.reference_repository
        )

        self.pages["references"] = ReferenceView(
            self.container,
            repository=self.reference_repository
        )

        self.pages["deadlines"] = DeadlinesView(self.container, self.personnel_repository, self.reference_repository)

        self.pages["notifications"] = NotificationsView(
            self.container, self.notifications, self.personnel_repository,
            self.reference_repository, self.refresh_notifications)
        self.pages["settings"] = NotificationSettingsView(
            self.container, self.osago_notifications, self.refresh_notifications)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    # ======================================================
    # Переключение страниц
    # ======================================================

    def show_page(self, page_name):

        for page in self.pages.values():
            page.grid_remove()

        self.pages[page_name].grid(row=0, column=0, sticky="nsew")

        if hasattr(self.pages[page_name], "refresh"):
            self.pages[page_name].refresh()

        for name, button in self.menu_buttons.items():
            if name == page_name:
                button.configure(
                    fg_color=theme.SIDEBAR_ACTIVE,
                    text_color=theme.SECONDARY
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color="white"
                )

    # ======================================================
    # Часы
    # ======================================================

    def _personnel_data_changed(self, event=None):
        self.pages['deadlines'].refresh()
        self.refresh_notifications()

    def _update_clock(self):

        now = datetime.now()

        self.date_label.configure(text=now.strftime("%d.%m.%Y"))
        self.time_label.configure(text=now.strftime("%H:%M:%S"))

        self.after(1000, self._update_clock)

    def _create_notification_banner(self):
        self.notification_banner = ctk.CTkFrame(self.main_area, fg_color=theme.WARNING_BG)
        self.notification_summary = ctk.CTkLabel(self.notification_banner, text="", text_color=theme.TEXT,
                                                wraplength=650, justify="left")
        self.notification_summary.pack(side="left", padx=16, pady=12)
        ctk.CTkButton(self.notification_banner, text="Посмотреть", width=110,
                      fg_color=theme.PRIMARY, command=lambda: self.show_page("notifications")).pack(side="left", padx=12)
        ctk.CTkButton(self.notification_banner, text="Закрыть", width=80,
                      fg_color=theme.WARNING, command=self._hide_notification_banner).pack(side="right", padx=12)

    def _hide_notification_banner(self):
        self.notification_banner.pack_forget()
        self.banner_visible = False

    def refresh_notifications(self):
        try:
            state = self.notifications.refresh()
        except (sqlite3.Error, ValueError) as error:
            self.notification_button.configure(text="Уведомления · ошибка")
            if "notifications" in self.pages:
                self.pages["notifications"].summary.configure(text=f"Не удалось обновить уведомления: {error}")
            return
        self.notification_state = state
        visible = [row for row in state['rows'] if not row['deferred']]
        unread = sum(not row['is_read'] for row in visible)
        self.notification_button.configure(text=f"🔔 Уведомления · {unread}")
        self.pages['notifications'].set_state(state)
        summary_unread = any(not row['is_read'] and row['startup_summary'] for row in visible)
        if not summary_unread or not state['settings']['enabled']:
            self._hide_notification_banner()
        elif self.banner_visible:
            self._update_notification_summary()

    def _update_notification_summary(self):
        rows = [row for row in self.notification_state['rows'] if not row['deferred'] and not row['is_read'] and row['startup_summary']]
        overdue = sum(row['days'] < 0 for row in rows)
        upcoming = len(rows)-overdue
        self.notification_summary.configure(text=f"Новые уведомления: {len(rows)}. Просрочено: {overdue}. Предстоящие: {upcoming}.")

    def _start_notifications(self):
        self.refresh_notifications()
        state = self.notification_state
        if state and state['settings']['enabled'] and state['settings']['startup_summary']:
            if any(not row['is_read'] and not row['deferred'] and row['startup_summary'] for row in state['rows']):
                self.banner_visible = True
                self._update_notification_summary()
                self.notification_banner.pack(fill="x", padx=18, pady=(12, 0), before=self.container)
        self.after(60000, self._poll_notifications)

    def _poll_notifications(self):
        self.refresh_notifications()
        self.after(60000, self._poll_notifications)
