import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from ui.widgets.record_editor import DataTable
from ui.widgets.copyable_treeview import CopyableTreeview


class TableCopyTests(unittest.TestCase):
    def table(self):
        table=Mock()
        table.tree.selection.return_value=('row',)
        table.tree.item.return_value=('Иванов', 'ОСАГО')
        table.selected_column='#2'
        return table

    def test_cell_and_row_clipboard(self):
        table=self.table()
        self.assertEqual(DataTable.copy_cell(table),'break')
        table.clipboard_append.assert_called_once_with('ОСАГО')
        table.clipboard_append.reset_mock()
        DataTable.copy(table)
        table.clipboard_append.assert_called_once_with('Иванов\tОСАГО')

    def test_popup_stays_alive_for_user_to_choose_action(self):
        table=self.table()
        table.tree.identify_row.return_value='row'
        table.tree.identify_column.return_value='#2'
        DataTable._popup_menu(table,SimpleNamespace(x=5,y=6,x_root=100,y_root=200))
        table.copy_menu.tk_popup.assert_called_once_with(100,200)
        table.copy_menu.destroy.assert_not_called()
        table.copy_menu.grab_release.assert_not_called()
        table.tree.selection_set.assert_called_once_with('row')


    def test_treeview_popup_keeps_native_menu_grab(self):
        tree = Mock()
        tree.identify_row.return_value = 'row'
        tree.identify_column.return_value = '#2'
        CopyableTreeview._show_menu(tree, SimpleNamespace(x=5,y=6,x_root=100,y_root=200))
        tree.menu.tk_popup.assert_called_once_with(100,200)
        tree.menu.grab_release.assert_not_called()
        self.assertEqual(tree.selected_cell, ('row','#2'))
