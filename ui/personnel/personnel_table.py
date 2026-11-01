from ui.widgets.record_editor import DataTable


class PersonnelTable(DataTable):
    def __init__(self, parent, on_open):
        super().__init__(parent, [
            ('full_name', 'ФИО', 280), ('rank_name', 'Звание', 140),
            ('position_name', 'Должность', 240), ('unit_name', 'Подразделение', 190),
            ('service_status', 'Статус', 120),
        ], on_open=on_open)

    def load_rows(self, rows):
        self.load(rows)
