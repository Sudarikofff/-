from database.connection import get_connection


def seed_database(preserve_existing=False):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS seed_history (name TEXT PRIMARY KEY)')
        if cursor.execute("SELECT 1 FROM seed_history WHERE name='reference_defaults'").fetchone():
            return
        if preserve_existing:
            cursor.execute("INSERT INTO seed_history(name) VALUES ('reference_defaults')")
            connection.commit()
            return
        # ==================================================
        # Воинские звания (заполняем только если пусто)
        # ==================================================

        rank_count = cursor.execute(
            "SELECT COUNT(*) FROM ranks"
        ).fetchone()[0]

        if rank_count == 0:

            ranks = [
                ("Рядовой", 1),
                ("Ефрейтор", 2),

                ("Младший сержант", 3),
                ("Сержант", 4),
                ("Старший сержант", 5),
                ("Старшина", 6),

                ("Прапорщик", 7),
                ("Старший прапорщик", 8),

                ("Младший лейтенант", 9),
                ("Лейтенант", 10),
                ("Старший лейтенант", 11),
                ("Капитан", 12),

                ("Майор", 13),
                ("Подполковник", 14),
                ("Полковник", 15),

                ("Генерал-майор", 16),
                ("Генерал-лейтенант", 17),
                ("Генерал-полковник", 18),
                ("Генерал армии", 19)
            ]

            cursor.executemany("""
                INSERT INTO ranks(name, sort_order)
                VALUES (?, ?)
            """, ranks)

        # ==================================================
        # Типы дисциплинарных событий (всегда проверяем)
        # ==================================================

        cursor.executemany("""
            INSERT OR IGNORE INTO event_types(name)
            VALUES (?)
        """, [
            ("Поощрение",),
            ("Взыскание",)
        ])

        rewards = [
            "Снятие ранее примененного дисциплинарного взыскания", "Благодарность", "Грамота", "Деньги",
            "Ценный подарок", "Присвоение звания на ступень выше занимаемой должности", "Нагрудный знак/медаль"
        ]
        penalties = ["Выговор", "Строгий выговор", "Предупреждение о неполном служебном соответствии",
                     "Снижение в должности", "Снижение в звании"]
        for name, kinds in [("Поощрение", rewards), ("Взыскание", penalties)]:
            type_id = cursor.execute("SELECT id FROM event_types WHERE name=?", (name,)).fetchone()[0]
            cursor.executemany("INSERT OR IGNORE INTO event_kinds(event_type_id,name) VALUES (?,?)",
                               [(type_id, kind) for kind in kinds])
        cursor.executemany("INSERT OR IGNORE INTO authorities(name) VALUES (?)", [(name,) for name in
                           ["Знак", "ПОПК", "Группа", "ЗНКОП", "НКАП", "ЗНО", "НО", "НС", "НПУ", "Руководитель ПС", "Директор ФСБ"]])
        cursor.execute("INSERT INTO seed_history(name) VALUES ('reference_defaults')")
        connection.commit()

    finally:
        connection.close()
