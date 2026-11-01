from ui.widgets.record_editor import DataTable


class DisciplineTable(DataTable):
    def __init__(self, parent, on_open=None):
        super().__init__(parent, [
            ('event_date', 'Дата', 120), ('full_name', 'Военнослужащий', 260),
            ('event_type', 'Тип', 130), ('event_kind', 'Вид события', 300),
            ('authority_name', 'Орган', 180), ('status', 'Статус', 120),
        ], on_open=on_open)

    def load_rows(self, rows):
        self.load(rows)
