"""Word export of saved personnel data, without changing the database."""
from datetime import datetime
from pathlib import Path
import os
import tempfile
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from personnel_fields import PERSONAL, MILITARY, COLLECTIONS, Field, display_date


def export_personnel(path, personnel, profile, discipline, history):
    person = dict(personnel)
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.2)
    for name in ('Normal', 'Title', 'Heading 1', 'Heading 2'):
        style = doc.styles[name]
        style.font.name = 'Arial'
        style.font.color.rgb = RGBColor(0, 0, 0)
    doc.styles['Normal'].font.size = Pt(11)
    doc.styles['Normal'].paragraph_format.space_after = Pt(5)
    doc.add_heading('Сведения о военнослужащем', 0)
    doc.add_paragraph(person['full_name'])
    doc.add_paragraph('Личные сведения, прохождение службы и связанные записи личного дела.\n'
                      'Дата формирования: ' + datetime.now().strftime('%d.%m.%Y %H:%M'))

    def fields(record, definitions):
        record = dict(record)
        for field in definitions:
            value = record.get(field.key)
            if field.kind == 'date':
                value = display_date(value)
            paragraph = doc.add_paragraph()
            paragraph.add_run(field.label + ': ').bold = True
            paragraph.add_run(str(value) if value is not None and value != '' else 'Не указано')

    def records(title, rows, definitions):
        doc.add_heading(title, 1)
        if not rows:
            doc.add_paragraph('Записей нет.')
        for index, row in enumerate(rows, 1):
            doc.add_heading(f'Запись {index}', 2)
            fields(row, definitions)

    doc.add_heading('Личные данные', 1)
    fields(person, PERSONAL)
    doc.add_heading('Военная служба', 1)
    fields(person, [Field(k, label, 'date' if k.endswith('_date') else 'text') for k, label in (
        ('personal_number', 'Личный номер'), ('service_status', 'Статус службы'),
        ('rank_name', 'Звание'), ('rank_date', 'Дата присвоения звания'),
        ('unit_name', 'Подразделение'), ('position_name', 'Должность'),
        ('position_date', 'Дата назначения'))] + MILITARY)
    records('История службы', history, [Field(k, label, 'date' if k.endswith('_date') else 'text') for k, label in (
        ('event_type','Событие'), ('event_date','Дата'), ('document_number','Приказ'), ('basis','Основание'),
        ('old_rank','Прежнее звание'), ('new_rank','Новое звание'), ('old_unit','Прежнее подразделение'),
        ('new_unit','Новое подразделение'), ('old_position','Прежняя должность'), ('new_position','Новая должность'))])
    records('Дисциплина', discipline, [Field(k, label, 'date' if k.endswith('_date') else 'text') for k, label in (
        ('event_type','Тип события'), ('event_kind','Вид события'), ('authority_name','Орган'),
        ('event_date','Дата'), ('document_number','Приказ'), ('basis','Основание'), ('comment','Комментарий'),
        ('status','Состояние'), ('due_date','Срок контроля'), ('removal_date','Дата снятия'),
        ('removal_document','Приказ о снятии'), ('removal_basis','Основание снятия'), ('removal_comment','Комментарий к снятию'),
        ('linked_penalty_id','ID связанного взыскания'))])
    for table, (title, definitions) in COLLECTIONS.items():
        records(title, profile.list_records(table, person['id']), definitions)
    doc.core_properties.author = ''
    doc.core_properties.title = 'Сведения о военнослужащем'
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.docx', delete=False) as handle:
            temporary = Path(handle.name)
        doc.save(temporary)
        os.replace(temporary, destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return destination
