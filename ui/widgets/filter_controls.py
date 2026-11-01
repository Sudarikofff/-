"""Shared captions and calendar selection for filter fields."""
from datetime import date
import customtkinter as ctk
from tkcalendar import Calendar
import theme
from personnel_fields import parse_date


def label_filter(widget, text):
    """Keep a field's geometry, placing a persistent caption above it."""
    manager = widget.winfo_manager()
    options = widget.grid_info() if manager == 'grid' else widget.pack_info()
    options.pop('in', None)
    container = ctk.CTkFrame(widget.master, fg_color='transparent')
    if manager == 'grid':
        widget.grid_forget()
        container.grid(**options)
    else:
        # Preserve packing order when inserting the caption.
        siblings = widget.master.pack_slaves()
        index = siblings.index(widget)
        following = siblings[index + 1] if index + 1 < len(siblings) else None
        widget.pack_forget()
        if following is not None:
            options['before'] = following
        container.pack(**options)
    ctk.CTkLabel(container, text=text, font=theme.SMALL_FONT,
                 text_color=theme.TEXT_SECONDARY, anchor='w').pack(fill='x', pady=(0, 3))
    widget.pack(in_=container, fill='x')
    widget.lift()
    return container


class CalendarFilterEntry(ctk.CTkEntry):
    def __init__(self, parent, on_selected=None, **kwargs):
        self.value = ctk.StringVar()
        super().__init__(parent, textvariable=self.value, state='readonly', **kwargs)
        self.on_selected = on_selected
        self.calendar_window = None
        for sequence in ('<Button-1>', '<Return>', '<space>'):
            self.bind(sequence, self.open_calendar)

    def clear(self):
        self.value.set('')

    def open_calendar(self, event=None):
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.lift()
            return
        window = self.calendar_window = ctk.CTkToplevel(self)
        window.title('Выберите дату')
        window.resizable(False, False)
        window.transient(self.winfo_toplevel())
        window.configure(fg_color=theme.BACKGROUND)
        selected = parse_date(self.get()) or date.today()
        calendar = Calendar(window, selectmode='day', locale='ru_RU', date_pattern='dd.mm.yyyy',
                            year=selected.year, month=selected.month, day=selected.day,
                            background=theme.PRIMARY, headersbackground=theme.CARD)
        calendar.pack(padx=12, pady=12)

        def choose():
            self.value.set(calendar.get_date())
            window.destroy()
            if self.on_selected:
                self.on_selected()

        ctk.CTkButton(window, text='Выбрать', command=choose, fg_color=theme.PRIMARY,
                      hover_color=theme.PRIMARY_HOVER).pack(pady=(0, 12))


class FilterActions(ctk.CTkFrame):
    """A centered group that wraps buttons together on narrow panels."""
    BUTTON_WIDTH = 120
    GAP = 8

    def __init__(self, parent, actions):
        super().__init__(parent, fg_color='transparent')
        self.group = ctk.CTkFrame(self, fg_color='transparent')
        self.group.pack(anchor='center')
        self.buttons = []
        self.columns = None
        for text, command, secondary in actions:
            self.buttons.append(ctk.CTkButton(
                self.group, text=text, command=command, width=self.BUTTON_WIDTH, height=36,
                fg_color=theme.CARD_HOVER if secondary else theme.PRIMARY,
                text_color=theme.TEXT if secondary else 'white',
                hover_color=theme.BORDER if secondary else theme.PRIMARY_HOVER,
                border_width=1 if secondary else 0, border_color=theme.BORDER))
        self.bind('<Configure>', self._layout)
        self._layout()

    def _layout(self, event=None):
        width = (event.width / self._get_widget_scaling()) if event else self.winfo_width()
        columns = max(1, min(len(self.buttons), int(width // (self.BUTTON_WIDTH + self.GAP))))
        if columns == self.columns:
            return
        self.columns = columns
        for index, widget in enumerate(self.buttons):
            widget.grid(row=index // columns, column=index % columns, padx=self.GAP // 2, pady=4)
