from ui.widgets.record_editor import DataTable


class PersonnelServiceHistoryTable(DataTable):
    def __init__(self, parent):
        super().__init__(parent, [
            ('event_date', 'Дата', 120), ('event_type', 'Кадровое событие', 200),
            ('before', 'Было', 240), ('after', 'Стало', 240), ('document_number', 'Приказ', 140),
        ])

    def load_rows(self, rows):
        records = []
        for original in rows:
            row = dict(original)
            if row['event_type'] == 'Присвоение звания':
                row['before'], row['after'] = row['old_rank'], row['new_rank']
            elif row['event_type'] == 'Перевод':
                row['before'], row['after'] = row['old_unit'], row['new_unit']
            else:
                row['before'], row['after'] = row['old_position'], row['new_position']
            records.append(row)
        self.load(records)
