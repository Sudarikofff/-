from database.connection import get_connection


# ==========================================================
# Personnel Repository
# ==========================================================

class PersonnelRepository:

    # ------------------------------------------------------
    # Получить весь личный состав
    # ------------------------------------------------------

    def get_all(self):

        connection = get_connection()

        try:
            return connection.execute("""
                                      SELECT p.*,

                                             r.name                               AS rank_name,
                                             u.name                               AS unit_name,
                                             pos.name                             AS position_name,

                                             COALESCE(p.service_status, 'Служит') AS service_status

                                      FROM personnel p

                                               LEFT JOIN ranks r
                                                         ON r.id = p.rank_id

                                               LEFT JOIN units u
                                                         ON u.id = p.unit_id

                                               LEFT JOIN positions pos
                                                         ON pos.id = p.position_id

                                      ORDER BY p.full_name
                                      """).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Получить военнослужащего по ID
    # ------------------------------------------------------

    def get_by_id(self, personnel_id):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    p.*,

                    r.name AS rank_name,
                    u.name AS unit_name,
                    pos.name AS position_name

                FROM personnel p

                LEFT JOIN ranks r
                    ON p.rank_id = r.id

                LEFT JOIN units u
                    ON p.unit_id = u.id

                LEFT JOIN positions pos
                    ON p.position_id = pos.id

                WHERE p.id = ?
            """, (personnel_id,)).fetchone()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Добавить военнослужащего
    # ------------------------------------------------------

    def create(
        self,
        full_name,
        personal_number="",
        birth_date=None,
        rank_id=None,
        rank_date=None,
        unit_id=None,
            position_id=None,
        position_date=None,
        phone="",
        service_status="Служит",
        comment=""
    ):

        connection = get_connection()

        try:
            if personal_number == "":
                personal_number = None
            cursor = connection.execute("""
                INSERT INTO personnel(
                    full_name,
                    personal_number,
                    birth_date,
                    rank_id,
                    rank_date,
                    unit_id,
                    position_id,
                    position_date,
                    phone,
                    service_status,
                    comment
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                full_name,
                personal_number,
                birth_date,
                rank_id,
                rank_date,
                unit_id,
                position_id,
                position_date,
                phone,
                service_status,
                comment
            ))

            connection.commit()

            return cursor.lastrowid

        finally:
            connection.close()

    # ------------------------------------------------------
    # Редактировать военнослужащего
    # ------------------------------------------------------

    def update(
        self,
        personnel_id,
        full_name,
        personal_number,
        birth_date,
        rank_id,
        rank_date,
        unit_id,
        position_id,
        position_date,
        phone,
        service_status,
        comment
    ):

        connection = get_connection()

        try:
            if personal_number == "":
                personal_number = None
            connection.execute("""
                UPDATE personnel
                SET
                    full_name = ?,
                    personal_number = ?,
                    birth_date = ?,
                    rank_id = ?,
                    rank_date = ?,
                    unit_id = ?,
                    position_id = ?,
                    position_date = ?,
                    phone = ?,
                    service_status = ?,
                    comment = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                full_name,
                personal_number,
                birth_date,
                rank_id,
                rank_date,
                unit_id,
                position_id,
                position_date,
                phone,
                service_status,
                comment,
                personnel_id
            ))

            connection.commit()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Изменить статус службы
    # ------------------------------------------------------

    def change_status(self, personnel_id, status):

        connection = get_connection()

        try:

            connection.execute("""
                UPDATE personnel
                SET
                    service_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                status,
                personnel_id
            ))

            connection.commit()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Поиск военнослужащих
    # ------------------------------------------------------

    def search(self, text=""):

        connection = get_connection()

        try:

            pattern = f"%{text}%"

            return connection.execute("""
                SELECT
                    p.id,
                    p.full_name,
                    p.personal_number,
                    p.service_status,

                    r.name AS rank_name,
                    u.name AS unit_name,
                    pos.name AS position_name

                FROM personnel p

                LEFT JOIN ranks r
                    ON p.rank_id = r.id

                LEFT JOIN units u
                    ON p.unit_id = u.id

                LEFT JOIN positions pos
                    ON p.position_id = pos.id

                WHERE
                    p.full_name LIKE ?
                    OR p.personal_number LIKE ?

                ORDER BY p.full_name COLLATE NOCASE
            """, (
                pattern,
                pattern
            )).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Статистика для главной панели
    # ------------------------------------------------------

    def get_statistics(self):

        connection = get_connection()

        try:

            stats = {}

            stats["total"] = connection.execute("""
                SELECT COUNT(*)
                FROM personnel
            """).fetchone()[0]

            stats["active"] = connection.execute("""
                SELECT COUNT(*)
                FROM personnel
                WHERE service_status='Служит'
            """).fetchone()[0]

            stats["archive"] = connection.execute("""
                SELECT COUNT(*)
                FROM personnel
                WHERE service_status='Архив'
            """).fetchone()[0]

            return stats

        finally:
            connection.close()
    # ======================================================
    # Статистика личного состава
    # ======================================================

    def get_dashboard_statistics(self):

        connection = get_connection()

        try:

            total = connection.execute("""
                SELECT COUNT(*) FROM personnel
            """).fetchone()[0]

            active = connection.execute("""
                SELECT COUNT(*)
                FROM personnel
                WHERE service_status != 'Архив'
            """).fetchone()[0]

            archive = connection.execute("""
                SELECT COUNT(*)
                FROM personnel
                WHERE service_status = 'Архив'
            """).fetchone()[0]

            return {
                "total": total,
                "active": active,
                "archive": archive
            }

        finally:
            connection.close()

    # ======================================================
    # Ближайшие дни рождения
    # ======================================================

    def get_upcoming_birthdays(self, limit=5):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    full_name,
                    birth_date,
                    unit_id
                FROM personnel
                WHERE birth_date IS NOT NULL
                ORDER BY strftime('%m-%d', birth_date)
                LIMIT ?
            """, (limit,)).fetchall()

        finally:
            connection.close()

    # ======================================================
    # Проверка личного номера
    # ======================================================

    def personal_number_exists(self, personal_number, exclude_id=None):

        if personal_number is None:
            return False

        connection = get_connection()

        try:

            if exclude_id is None:

                row = connection.execute("""
                    SELECT id
                    FROM personnel
                    WHERE personal_number = ?
                """, (personal_number,)).fetchone()

            else:

                row = connection.execute("""
                    SELECT id
                    FROM personnel
                    WHERE personal_number = ?
                      AND id != ?
                """, (
                    personal_number,
                    exclude_id
                )).fetchone()

            return row is not None

        finally:
            connection.close()

    def get_personnel_statistics(self, personnel_id):

        connection = get_connection()

        try:

            return {
                "rewards": rewards,
                "penalties": penalties,
                "active_penalties": active
            }

        finally:
            connection.close()


# ==========================================================
# Reference Repository
# ==========================================================

class ReferenceRepository:

    # ------------------------------------------------------
    # Звания
    # ------------------------------------------------------

    def get_ranks(self):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT *
                FROM ranks
                ORDER BY sort_order
            """).fetchall()

        finally:
            connection.close()

    # ======================================================
    # Подразделения
    # ======================================================

    def get_units(self):

        connection = get_connection()

        try:
            return connection.execute("""
                                      SELECT id, name
                                      FROM units
                                      ORDER BY name
                                      """).fetchall()

        finally:
            connection.close()

    def create_unit(self, name):

        connection = get_connection()

        try:
            connection.execute(
                "INSERT INTO units(name) VALUES (?)",
                (name,)
            )

            connection.commit()

        finally:
            connection.close()

    def update_unit(self, unit_id, name):

        connection = get_connection()

        try:
            connection.execute(
                "UPDATE units SET name=? WHERE id=?",
                (name, unit_id)
            )

            connection.commit()

        finally:
            connection.close()

    def delete_unit(self, unit_id):

        connection = get_connection()

        try:
            connection.execute(
                "DELETE FROM units WHERE id=?",
                (unit_id,)
            )

            connection.commit()

        finally:
            connection.close()

    # ======================================================
    # Универсальное получение записей справочника
    # ======================================================

    def get_reference(self, table):

        allowed_tables = {
            "units",
            "positions",
            "ranks",
            "authorities",
            "event_kinds"
        }

        if table not in allowed_tables:
            raise ValueError("Недопустимый справочник")

        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT id, name FROM {table} ORDER BY name"
            ).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Должности
    # ------------------------------------------------------

    def get_positions(self, unit_id=None):

        connection = get_connection()

        try:

            if unit_id is None:
                return connection.execute("""
                    SELECT *
                    FROM positions
                    ORDER BY name
                """).fetchall()

            return connection.execute("""
                SELECT *
                FROM positions
                WHERE unit_id = ?
                ORDER BY name
            """, (unit_id,)).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Типы дисциплинарных событий
    # ------------------------------------------------------

    def get_event_types(self):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT *
                FROM event_types
                ORDER BY id
            """).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Виды дисциплинарных событий
    # ------------------------------------------------------

    def get_event_kinds(self, event_type_id=None):

        connection = get_connection()

        try:

            if event_type_id is None:
                return connection.execute("""
                    SELECT *
                    FROM event_kinds
                    ORDER BY name
                """).fetchall()

            return connection.execute("""
                SELECT *
                FROM event_kinds
                WHERE event_type_id = ?
                ORDER BY name
            """, (event_type_id,)).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Органы, применяющие меры
    # ------------------------------------------------------

    def get_authorities(self):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT *
                FROM authorities
                ORDER BY name
            """).fetchall()

        finally:
            connection.close()

    # ======================================================
    # Универсальные справочники
    # ======================================================

    def get_reference(self, table):

        allowed = {
            "units",
            "ranks",
            "positions",
            "authorities"
        }

        if table not in allowed:
            raise ValueError(f"Недопустимый справочник: {table}")

        connection = get_connection()

        try:
            return connection.execute(
                f"SELECT id, name FROM {table} ORDER BY name"
            ).fetchall()

        finally:
            connection.close()

    def create_reference(self, table, name):

        allowed = {
            "units",
            "positions",
            "ranks",
            "authorities",
            "event_kinds"
        }

        if table not in allowed:
            raise ValueError("Недопустимый справочник")

        connection = get_connection()

        try:
            connection.execute(
                f"INSERT INTO {table}(name) VALUES (?)",
                (name,)
            )

            connection.commit()

        finally:
            connection.close()

    def update_reference(self, table, record_id, name):

        allowed = {
            "units",
            "positions",
            "ranks",
            "authorities",
            "event_kinds"
        }

        if table not in allowed:
            raise ValueError("Недопустимый справочник")

        connection = get_connection()

        try:
            connection.execute(
                f"UPDATE {table} SET name=? WHERE id=?",
                (name, record_id)
            )

            connection.commit()

        finally:
            connection.close()

    def delete_reference(self, table, record_id, event_type_id=None):

        connection = get_connection()

        try:
            if table == "event_kinds" and event_type_id is not None:
                connection.execute(
                    "DELETE FROM event_kinds WHERE id=? AND event_type_id=?",
                    (record_id, event_type_id)
                )
            else:
                connection.execute(
                    f"DELETE FROM {table} WHERE id=?",
                    (record_id,)
                )

            connection.commit()

        finally:
            connection.close()

    def can_delete_reference(self, table, record_id):

        connection = get_connection()

        try:
            checks = {
                "units": [
                    ("personnel", "unit_id"),
                    ("service_history", "new_unit_id"),
                    ("service_history", "old_unit_id")
                ],

                "positions": [
                    ("personnel", "position_id"),
                    ("service_history", "new_position_id"),
                    ("service_history", "old_position_id")
                ],

                "ranks": [
                    ("personnel", "rank_id"),
                    ("service_history", "new_rank_id"),
                    ("service_history", "old_rank_id")
                ],

                # ИСПРАВЛЕНО
                "authorities": [
                    ("disciplinary_events", "authority_id")
                ],

                # Добавил проверку для справочника поощрений/взысканий
                "event_kinds": [
                    ("disciplinary_events", "event_kind_id")
                ]
            }

            if table not in checks:
                return True, 0

            total = 0

            for table_name, field in checks[table]:
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE {field}=?",
                    (record_id,)
                ).fetchone()[0]

                total += count

            return total == 0, total

        finally:
            connection.close()

    # ======================================================
    # Виды поощрений / взысканий
    # ======================================================

    def create_event_kind(self, name, event_type_id):

        connection = get_connection()

        try:
            connection.execute("""
                               INSERT INTO event_kinds (name, event_type_id)
                               VALUES (?, ?)
                               """, (name, event_type_id))

            connection.commit()

        finally:
            connection.close()

    def update_event_kind(self, record_id, name):

        connection = get_connection()

        try:
            connection.execute("""
                               UPDATE event_kinds
                               SET name = ?
                               WHERE id = ?
                               """, (name, record_id))

            connection.commit()

        finally:
            connection.close()

    def delete_event_kind(self, record_id):

        connection = get_connection()

        try:
            connection.execute("""
                               DELETE
                               FROM event_kinds
                               WHERE id = ?
                               """, (record_id,))

            connection.commit()

        finally:
            connection.close()

# ==========================================================
# Discipline Repository
# ==========================================================

class DisciplineRepository:

    # ------------------------------------------------------
    # Все дисциплинарные события
    # ------------------------------------------------------

    def get_all(self):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    d.id,
                    d.personnel_id,
                    d.event_date,
                    d.document_number,
                    d.basis,
                    d.comment,
                    d.status,

                    et.name AS event_type,
                    ek.name AS event_kind,
                    a.name AS authority_name,
                    p.full_name

                FROM disciplinary_events d

                LEFT JOIN personnel p
                    ON d.personnel_id = p.id

                LEFT JOIN event_types et
                    ON d.event_type_id = et.id

                LEFT JOIN event_kinds ek
                    ON d.event_kind_id = ek.id

                LEFT JOIN authorities a
                    ON d.authority_id = a.id

                ORDER BY d.event_date DESC
            """).fetchall()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Добавить событие
    # ------------------------------------------------------

    def create(
        self,
        personnel_id,
        event_type,
        event_kind,
        authority_name,
        event_date,
        document_number,
        basis,
        comment,
        status
    ):

        connection = get_connection()

        try:

            event_type_id = connection.execute(
                "SELECT id FROM event_types WHERE name=?",
                (event_type,)
            ).fetchone()["id"]

            kind = connection.execute(
                """
                SELECT id
                FROM event_kinds
                WHERE name=? AND event_type_id=?
                """,
                (event_kind, event_type_id)
            ).fetchone()

            authority = connection.execute(
                "SELECT id FROM authorities WHERE name=?",
                (authority_name,)
            ).fetchone()

            connection.execute("""
                INSERT INTO disciplinary_events(
                    personnel_id,
                    event_type_id,
                    event_kind_id,
                    authority_id,
                    event_date,
                    document_number,
                    basis,
                    comment,
                    status
                )
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                personnel_id,
                event_type_id,
                kind["id"] if kind else None,
                authority["id"] if authority else None,
                event_date,
                document_number,
                basis,
                comment,
                status
            ))

            connection.commit()

        finally:
            connection.close()

    # ------------------------------------------------------
    # Обновить событие
    # ------------------------------------------------------

    def update(
        self,
        event_id,
        personnel_id,
        event_type,
        event_kind,
        authority_name,
        event_date,
        document_number,
        basis,
        comment,
        status
    ):

        connection = get_connection()

        try:

            event_type_id = connection.execute(
                "SELECT id FROM event_types WHERE name=?",
                (event_type,)
            ).fetchone()["id"]

            kind = connection.execute(
                """
                SELECT id
                FROM event_kinds
                WHERE name=? AND event_type_id=?
                """,
                (event_kind, event_type_id)
            ).fetchone()

            authority = connection.execute(
                "SELECT id FROM authorities WHERE name=?",
                (authority_name,)
            ).fetchone()

            connection.execute("""
                UPDATE disciplinary_events
                SET
                    personnel_id=?,
                    event_type_id=?,
                    event_kind_id=?,
                    authority_id=?,
                    event_date=?,
                    document_number=?,
                    basis=?,
                    comment=?,
                    status=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                personnel_id,
                event_type_id,
                kind["id"] if kind else None,
                authority["id"] if authority else None,
                event_date,
                document_number,
                basis,
                comment,
                status,
                event_id
            ))

            connection.commit()

        finally:
            connection.close()

    # ======================================================
    # История дисциплинарной практики военнослужащего
    # ======================================================

    def get_personnel_history(self, personnel_id):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    d.id,
                    d.event_date,
                    d.document_number,
                    d.status,

                    et.name AS event_type,
                    ek.name AS event_kind,
                    a.name AS authority_name

                FROM disciplinary_events d

                LEFT JOIN event_types et
                    ON d.event_type_id = et.id

                LEFT JOIN event_kinds ek
                    ON d.event_kind_id = ek.id

                LEFT JOIN authorities a
                    ON d.authority_id = a.id

                WHERE d.personnel_id = ?

                ORDER BY d.event_date DESC
            """, (personnel_id,)).fetchall()

        finally:
            connection.close()

    # ======================================================
    # Виды поощрений / взысканий
    # ======================================================

    def create_event_kind(self, name, event_type_id):

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO event_kinds(name, event_type_id)
                VALUES (?, ?)
                """,
                (name, event_type_id)
            )
            connection.commit()

        finally:
            connection.close()

    def update_event_kind(self, record_id, name):

        connection = get_connection()

        try:
            connection.execute(
                "UPDATE event_kinds SET name=? WHERE id=?",
                (name, record_id)
            )
            connection.commit()

        finally:
            connection.close()

    def delete_event_kind(self, record_id):

        connection = get_connection()

        try:
            connection.execute(
                "DELETE FROM event_kinds WHERE id=?",
                (record_id,)
            )
            connection.commit()

        finally:
            connection.close()

