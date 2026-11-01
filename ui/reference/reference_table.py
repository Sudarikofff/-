from ui.widgets.record_editor import DataTable


class ReferenceTable(DataTable):
    def __init__(self, parent, on_select=None):
        super().__init__(parent, [('id', 'ID', 80), ('name', 'Название', 500)])
        self.on_select = on_select
        self.tree.bind('<<TreeviewSelect>>', self._selected)

    def _selected(self, event=None):
        row = self.selected()
        if row and self.on_select:
            self.on_select(row)

    def load_rows(self, rows):
        self.load(rows)
