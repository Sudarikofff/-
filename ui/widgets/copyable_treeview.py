import tkinter as tk
from ui.widgets.table_style import StyledTreeview


class CopyableTreeview(StyledTreeview):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.selected_cell = None

        # Контекстное меню
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Копировать ячейку", command=self.copy_cell)
        self.menu.add_command(label="Копировать строку", command=self.copy_row)


        # События
        self.bind("<Button-1>", self._select_cell, add="+")
        self.bind("<Button-3>", self._show_menu, add="+")
        self.bind("<Control-c>", self.copy_cell, add="+")
        self.bind("<Control-C>", self.copy_cell, add="+")
        self.bind("<Control-Shift-c>", self.copy_row, add="+")
        self.bind("<Control-Shift-C>", self.copy_row, add="+")



    # ----------------------------------------------------
    # Выбор ячейки
    # ----------------------------------------------------

    def _select_cell(self, event):
        row = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if not row or not column:
            return

        self.selected_cell = (row, column)

        self.selection_set(row)
        self.focus(row)


    # ----------------------------------------------------
    # ПКМ
    # ----------------------------------------------------

    def _show_menu(self, event):
        row = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if row:
            self.selected_cell = (row, column)
            self.selection_set(row)
            self.focus(row)

        # Tk owns the menu grab until dismissal (outside click, Escape or command).
        self.menu.tk_popup(event.x_root, event.y_root)

    # ----------------------------------------------------
    # Копировать ячейку
    # ----------------------------------------------------

    def copy_cell(self, event=None):

        if not self.selected_cell:
            return "break"

        row, column = self.selected_cell

        values = self.item(row)["values"]
        index = int(column[1:]) - 1

        if 0 <= index < len(values):
            self.clipboard_clear()
            self.clipboard_append(str(values[index]))

        return "break"

    # ----------------------------------------------------
    # Копировать строку
    # ----------------------------------------------------

    def copy_row(self, event=None):

        selected = self.selection()

        if not selected:
            return "break"

        values = self.item(selected[0])["values"]

        self.clipboard_clear()
        self.clipboard_append("\t".join(map(str, values)))

        return "break"