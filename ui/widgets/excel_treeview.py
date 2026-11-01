"""Compatibility widget with shared styling and cell keyboard navigation."""
from ui.widgets.copyable_treeview import CopyableTreeview


class ExcelTreeview(CopyableTreeview):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind('<Left>', lambda event: self._move_to(col_offset=-1), add='+')
        self.bind('<Right>', lambda event: self._move_to(col_offset=1), add='+')
        self.bind('<Up>', lambda event: self._move_to(row_offset=-1), add='+')
        self.bind('<Down>', lambda event: self._move_to(row_offset=1), add='+')

    def _move_to(self, row_offset=0, col_offset=0):
        rows = list(self.get_children())
        if not self.selected_cell or not rows or not self['columns']:
            return 'break'
        item, column = self.selected_cell
        if item not in rows:
            return 'break'
        row_index = max(0, min(len(rows)-1, rows.index(item)+row_offset))
        col_index = max(1, min(len(self['columns']), int(column[1:])+col_offset))
        item = rows[row_index]
        self.selected_cell = (item, f'#{col_index}')
        self.selection_set(item)
        self.focus(item)
        self.see(item)
        return 'break'
