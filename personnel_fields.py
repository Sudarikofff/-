"""Fields shared by forms, validation and additive database migrations."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = 'text'
    choices: tuple = ()
    required: bool = False
    group: str = ''


PERSONAL = [
    Field('full_name', 'Фамилия, имя, отчество', required=True, group='Основные сведения'),
    Field('birth_date', 'Дата рождения', 'date'),
    Field('birth_place', 'Место рождения'),
    Field('nationality', 'Национальность'),
    Field('religion', 'Вероисповедание'),
    Field('phone', 'Телефон'),
    Field('actual_address', 'Адрес фактического проживания', 'multiline', group='Адреса и жильё'),
    Field('residence_type', 'Тип проживания', choices=('Собственное', 'У родственников', 'Съёмное', 'Иное')),
    Field('registration_address', 'Место регистрации', 'multiline'),
    Field('housing_program', 'Жилищная программа', choices=('НИС', 'Субсидия', 'Сертификат', 'Очередь', 'Иное')),
    Field('housing_realized', 'Реализация программы', choices=('Реализовано', 'Не реализовано', 'Не участвует')),
    Field('housing_comment', 'Сведения об обеспеченности жильём', 'multiline'),
    Field('owned_property', 'Недвижимость в собственности', 'multiline'),
    Field('passport_number', 'Паспорт: серия и номер', group='Документы'),
    Field('passport_issuer', 'Кем выдан паспорт', 'multiline'),
    Field('passport_issue_date', 'Дата выдачи паспорта', 'date'),
    Field('passport_due_date', 'Дата замены / окончания срока паспорта', 'date'),
    Field('snils', 'СНИЛС'),
    Field('inn', 'ИНН'),
    Field('comment', 'Комментарий', 'multiline', group='Дополнительно'),
]
MILITARY = [
    Field('military_id', 'Удостоверение личности / военный билет', group='Военная служба'),
    Field('military_id_due_date', 'Срок действия удостоверения', 'date'),
    Field('service_start_date', 'Дата поступления на службу', 'date'),
    Field('combat_participation', 'Участие в боевых действиях', 'multiline'),
    Field('attestation_year', 'Год аттестации', 'year', group='Аттестация и контракт'),
    Field('attestation_due_date', 'Точный срок аттестации, если назначен', 'date'),
    Field('contract_start_date', 'Дата заключения контракта', 'date'),
    Field('contract_period', 'Период заключения контракта'),
    Field('contract_end_date', 'Дата окончания контракта', 'date'),
    Field('contract_comment', 'Сведения о продлении контракта', 'multiline'),
]
FAMILY = [
    Field('relation', 'Родство', choices=('Отец', 'Мать', 'Супруг', 'Супруга', 'Брат', 'Сестра', 'Сын', 'Дочь', 'Ребёнок'), required=True),
    Field('full_name', 'Фамилия, имя, отчество', required=True),
    Field('birth_date', 'Дата рождения', 'date'),
    Field('phone', 'Телефон'),
    Field('address', 'Адрес', 'multiline'),
    Field('workplace', 'Место работы / учебное заведение'),
    Field('occupation', 'Должность / род занятий'),
    Field('education_type', 'Тип учебного заведения', choices=('Детский сад', 'Школа', 'Колледж', 'Институт', 'Университет', 'Иное')),
    Field('comment', 'Комментарий (умер, связь не поддерживается и др.)', 'multiline'),
]
EDUCATION = [
    Field('level', 'Уровень образования', choices=('Высшее', 'Среднее общее', 'Среднее профессиональное', 'Основное общее', 'Дополнительное'), required=True),
    Field('institution', 'Учебное заведение', required=True),
    Field('graduation_year', 'Год окончания', 'year'),
    Field('specialty', 'Специальность / квалификация'),
    Field('document', 'Документ об образовании'),
    Field('comment', 'Комментарий', 'multiline'),
]
VEHICLES = [
    Field('license_number', 'Номер водительского удостоверения', group='Водительское удостоверение'),
    Field('license_categories', 'Категории'),
    Field('license_expiry', 'Срок действия удостоверения', 'date'),
    Field('model', 'Марка / модель', group='Автомобиль'),
    Field('manufacture_year', 'Год выпуска', 'year'),
    Field('plate', 'Государственный регистрационный знак'),
    Field('registration_number', 'СОР: номер'),
    Field('registration_date', 'СОР: дата выдачи', 'date'),
    Field('insurance_number', 'Номер полиса ОСАГО', group='ОСАГО'),
    Field('insurance_expiry', 'Срок действия ОСАГО', 'date'),
    Field('comment', 'Примечание', 'multiline'),
]
LOANS = [
    Field('lender', 'Кредитная организация / физическое лицо', required=True),
    Field('lender_address', 'Место нахождения кредитора'),
    Field('amount', 'Сумма кредита, ₽', 'money'),
    Field('monthly_payment', 'Ежемесячный платёж, ₽', 'money'),
    Field('purpose', 'Цель кредита'),
    Field('repayment_date', 'Дата погашения кредита', 'date'),
    Field('next_payment_date', 'Дата ближайшего платежа', 'date'),
    Field('has_debt', 'Наличие задолженности', choices=('Нет', 'Да')),
    Field('debt_amount', 'Сумма задолженности, ₽', 'money'),
    Field('balance', 'Остаток, ₽', 'money'),
    Field('status', 'Статус кредита', choices=('Действует', 'Погашен'), required=True),
    Field('comment', 'Примечание', 'multiline'),
]
DEADLINES = [
    Field('title', 'Что необходимо продлить / выполнить', required=True),
    Field('category', 'Раздел', choices=('Документы', 'Военная служба', 'Классность', 'Образование', 'Транспорт', 'Кредиты', 'Иное'), required=True),
    Field('due_date', 'Срок', 'date', required=True),
    Field('status', 'Состояние', choices=('Открыто', 'Выполнено'), required=True),
    Field('comment', 'Комментарий', 'multiline'),
]
COLLECTIONS = {
    'family_members': ('Семья', FAMILY), 'education_records': ('Образование', EDUCATION),
    'personal_vehicles': ('Личный транспорт', VEHICLES), 'personal_loans': ('Кредиты', LOANS),
    'personnel_deadlines': ('Другие сроки', DEADLINES),
}


def parse_date(value):
    if not value or not str(value).strip():
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError('Введите дату в формате ДД.ММ.ГГГГ или ГГГГ-ММ-ДД.')


def display_date(value):
    try:
        parsed = parse_date(value)
        return parsed.strftime('%d.%m.%Y') if parsed else ''
    except ValueError:
        return str(value)


def validate(fields, values):
    result = {}
    for f in fields:
        value = str(values.get(f.key) or '').strip()
        if f.required and not value:
            raise ValueError(f'Заполните поле «{f.label}».')
        if value:
            try:
                if f.kind == 'date':
                    parsed = parse_date(value)
                    if f.key == 'birth_date' and parsed > date.today():
                        raise ValueError('Дата рождения не может быть в будущем.')
                    value = parsed.isoformat()
                elif f.kind == 'year':
                    if not value.isdigit() or not 1900 <= int(value) <= 2200:
                        raise ValueError('Укажите год от 1900 до 2200.')
                elif f.kind == 'money':
                    amount = Decimal(value.replace(' ', '').replace('\u00a0', '').replace(',', '.'))
                    if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal('.01')):
                        raise ValueError('Укажите неотрицательную сумму с точностью до копеек.')
                    value = format(amount.quantize(Decimal('.01')), 'f')
                if f.choices and value not in f.choices:
                    raise ValueError('Выберите значение из списка.')
            except (ValueError, InvalidOperation) as error:
                raise ValueError(f'{f.label}: {error}') from error
        result[f.key] = value or None
    if result.get('contract_start_date') and result.get('contract_end_date'):
        if result['contract_end_date'] < result['contract_start_date']:
            raise ValueError('Дата окончания контракта раньше даты заключения.')
    if fields is VEHICLES and not (result.get('model') or result.get('license_number')):
        raise ValueError('Укажите автомобиль или номер водительского удостоверения.')
    if fields is LOANS and result.get('has_debt') == 'Нет' and Decimal(result.get('debt_amount') or '0') > 0:
        raise ValueError('При отсутствии задолженности её сумма должна быть пустой или равна нулю.')
    return result
