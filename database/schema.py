from database.connection import get_connection

SCHEMA = """
PRAGMA foreign_keys = ON;

------------------------------------------------------------
-- Звания
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ranks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    sort_order INTEGER
);

------------------------------------------------------------
-- Подразделения
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS units(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER,
    FOREIGN KEY(parent_id) REFERENCES units(id)
);

------------------------------------------------------------
-- Должности
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS positions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit_id INTEGER,
    UNIQUE(name, unit_id),
    FOREIGN KEY(unit_id) REFERENCES units(id)
);

------------------------------------------------------------
-- Военнослужащие
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS personnel(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    full_name TEXT NOT NULL,
    personal_number TEXT UNIQUE,

    birth_date TEXT,

    rank_id INTEGER,
    rank_date TEXT,

    unit_id INTEGER,
    position_id INTEGER,
    position_date TEXT,

    phone TEXT,

    service_status TEXT DEFAULT 'Служит',

    comment TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(rank_id) REFERENCES ranks(id),
    FOREIGN KEY(unit_id) REFERENCES units(id),
    FOREIGN KEY(position_id) REFERENCES positions(id)

);
CREATE TABLE IF NOT EXISTS service_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    personnel_id INTEGER NOT NULL,

    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,

    old_rank_id INTEGER,
    new_rank_id INTEGER,

    old_unit_id INTEGER,
    new_unit_id INTEGER,

    old_position_id INTEGER,
    new_position_id INTEGER,

    document_number TEXT,
    basis TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(personnel_id) REFERENCES personnel(id),
    FOREIGN KEY(old_rank_id) REFERENCES ranks(id),
    FOREIGN KEY(new_rank_id) REFERENCES ranks(id),
    FOREIGN KEY(old_unit_id) REFERENCES units(id),
    FOREIGN KEY(new_unit_id) REFERENCES units(id),
    FOREIGN KEY(old_position_id) REFERENCES positions(id),
    FOREIGN KEY(new_position_id) REFERENCES positions(id)

);
------------------------------------------------------------
-- Типы дисциплины
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS event_types(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

------------------------------------------------------------
-- Виды дисциплины
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS event_kinds(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type_id INTEGER,
    name TEXT,
    UNIQUE(event_type_id,name),
    FOREIGN KEY(event_type_id) REFERENCES event_types(id)
);

------------------------------------------------------------
-- Органы
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS authorities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

------------------------------------------------------------
-- Дисциплинарная практика
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS disciplinary_events(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    personnel_id INTEGER NOT NULL,

    event_type_id INTEGER NOT NULL,
    event_kind_id INTEGER NOT NULL,
    authority_id INTEGER,

    event_date TEXT,

    document_number TEXT,

    basis TEXT,
    comment TEXT,

    status TEXT DEFAULT 'Активно',

    removal_date TEXT,
    removal_document TEXT,
    removal_basis TEXT,
    removal_comment TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(personnel_id) REFERENCES personnel(id),
    FOREIGN KEY(event_type_id) REFERENCES event_types(id),
    FOREIGN KEY(event_kind_id) REFERENCES event_kinds(id),
    FOREIGN KEY(authority_id) REFERENCES authorities(id)

);

------------------------------------------------------------
-- Служебные разбирательства
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS investigations(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    personnel_id INTEGER,

    number TEXT,

    start_date TEXT,
    end_date TEXT,

    reason TEXT,

    result TEXT,

    status TEXT DEFAULT 'Проводится',

    comment TEXT,

    FOREIGN KEY(personnel_id) REFERENCES personnel(id)

);

------------------------------------------------------------
-- История службы
------------------------------------------------------------


------------------------------------------------------------
-- Семья
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS family_members(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    personnel_id INTEGER,

    relation TEXT,

    full_name TEXT,

    birth_date TEXT,

    phone TEXT,

    FOREIGN KEY(personnel_id) REFERENCES personnel(id)

);

------------------------------------------------------------
-- Журнал действий
------------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_log(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_time TEXT DEFAULT CURRENT_TIMESTAMP,

    section TEXT,

    action TEXT,

    personnel_id INTEGER,

    description TEXT

);

"""


def init_database():
    from database.profile_migration import backup_before_upgrade, migrate_profile
    backup_before_upgrade()
    connection = get_connection()

    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()

    # После создания таблиц сразу выполняем миграции
    run_migrations()
    migrate_profile()
    from database.osago_notifications import migrate_notifications
    migrate_notifications()

# ==========================================================
# Миграции базы данных
# ==========================================================

def run_migrations():

    connection = get_connection()

    try:

        service_history_columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(service_history)"
            ).fetchall()
        ]

        required_columns = {
            "old_rank_id": "INTEGER",
            "new_rank_id": "INTEGER",
            "old_unit_id": "INTEGER",
            "new_unit_id": "INTEGER",
            "old_position_id": "INTEGER",
            "new_position_id": "INTEGER",
            "document_number": "TEXT",
            "basis": "TEXT"
        }

        for column_name, column_type in required_columns.items():

            if column_name not in service_history_columns:

                connection.execute(f"""
                    ALTER TABLE service_history
                    ADD COLUMN {column_name} {column_type}
                """)

        disciplinary_event_columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(disciplinary_events)"
            ).fetchall()
        ]

        if "removal_basis" not in disciplinary_event_columns:
            connection.execute("""
                ALTER TABLE disciplinary_events
                ADD COLUMN removal_basis TEXT
            """)

        connection.commit()

    finally:
        connection.close()
