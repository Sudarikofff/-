from ui.widgets.record_editor import DataTable


class PersonnelDisciplineTable(DataTable):
    def __init__(self, parent):
        super().__init__(parent, [
            ('event_date', 'Дата', 120), ('event_type', 'Тип', 130),
            ('event_kind', 'Вид события', 300), ('authority_name', 'Орган', 180),
            ('status', 'Статус', 120),
        ])

    def load_rows(self, rows):
        self.load(rows)
