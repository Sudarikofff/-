from database.connection import get_connection


class ServiceHistoryRepository:

    # ======================================================
    # История службы военнослужащего
    # ======================================================

    def get_by_personnel(self, personnel_id):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    sh.id,
                    sh.event_type,
                    sh.event_date,
                    sh.document_number,
                    sh.basis,

                    old_rank.name AS old_rank,
                    new_rank.name AS new_rank,

                    old_unit.name AS old_unit,
                    new_unit.name AS new_unit,

                    old_position.name AS old_position,
                    new_position.name AS new_position

                FROM service_history sh

                LEFT JOIN ranks old_rank
                    ON sh.old_rank_id = old_rank.id

                LEFT JOIN ranks new_rank
                    ON sh.new_rank_id = new_rank.id

                LEFT JOIN units old_unit
                    ON sh.old_unit_id = old_unit.id

                LEFT JOIN units new_unit
                    ON sh.new_unit_id = new_unit.id

                LEFT JOIN positions old_position
                    ON sh.old_position_id = old_position.id

                LEFT JOIN positions new_position
                    ON sh.new_position_id = new_position.id

                WHERE sh.personnel_id = ?

                ORDER BY sh.event_date DESC, sh.id DESC
            """, (personnel_id,)).fetchall()

        finally:
            connection.close()

    # ======================================================
    # Добавить событие истории службы
    # ======================================================

    def create(
        self,
        personnel_id,
        event_type,
        event_date,
        old_rank_id=None,
        new_rank_id=None,
        old_unit_id=None,
        new_unit_id=None,
        old_position_id=None,
        new_position_id=None,
        document_number="",
        basis=""
    ):

        connection = get_connection()

        try:
            connection.execute("""
                INSERT INTO service_history(
                    personnel_id,
                    event_type,
                    event_date,
                    old_rank_id,
                    new_rank_id,
                    old_unit_id,
                    new_unit_id,
                    old_position_id,
                    new_position_id,
                    document_number,
                    basis
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                personnel_id,
                event_type,
                event_date,
                old_rank_id,
                new_rank_id,
                old_unit_id,
                new_unit_id,
                old_position_id,
                new_position_id,
                document_number,
                basis
            ))

            connection.commit()

        finally:
            connection.close()

    # ======================================================
    # Первичное назначение военнослужащего
    # ======================================================

    def create_initial_record(
        self,
        personnel_id,
        rank_id,
        unit_id,
        position_id,
        event_date
    ):

        self.create(
            personnel_id=personnel_id,
            event_type="Первичное назначение",
            event_date=event_date,
            new_rank_id=rank_id,
            new_unit_id=unit_id,
            new_position_id=position_id,
            document_number="",
            basis="Создание личного дела"
        )

    # ======================================================
    # Статистика истории службы
    # ======================================================

    def get_statistics(self, personnel_id):

        connection = get_connection()

        try:

            total_events = connection.execute("""
                SELECT COUNT(*)
                FROM service_history
                WHERE personnel_id = ?
            """, (personnel_id,)).fetchone()[0]

            transfers = connection.execute("""
                SELECT COUNT(*)
                FROM service_history
                WHERE
                    personnel_id = ?
                    AND event_type = 'Перевод'
            """, (personnel_id,)).fetchone()[0]

            promotions = connection.execute("""
                SELECT COUNT(*)
                FROM service_history
                WHERE
                    personnel_id = ?
                    AND event_type = 'Присвоение звания'
            """, (personnel_id,)).fetchone()[0]

            appointments = connection.execute("""
                SELECT COUNT(*)
                FROM service_history
                WHERE
                    personnel_id = ?
                    AND event_type IN (
                        'Назначение',
                        'Первичное назначение'
                    )
            """, (personnel_id,)).fetchone()[0]

            return {
                "total_events": total_events,
                "transfers": transfers,
                "promotions": promotions,
                "appointments": appointments
            }

        finally:
            connection.close()
    # ======================================================
    # Последние кадровые события
    # ======================================================

    def get_recent_events(self, limit=10):

        connection = get_connection()

        try:
            return connection.execute("""
                SELECT
                    sh.event_date,
                    sh.event_type,
                    p.full_name

                FROM service_history sh

                JOIN personnel p
                    ON p.id = sh.personnel_id

                ORDER BY sh.event_date DESC, sh.id DESC

                LIMIT ?
            """, (limit,)).fetchall()

        finally:
            connection.close()