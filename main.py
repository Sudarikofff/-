from database.schema import init_database
from database.seed import seed_database


def main():
    from database.connection import DATABASE_PATH
    existing_database = DATABASE_PATH.exists() and DATABASE_PATH.stat().st_size > 0
    init_database()
    seed_database(preserve_existing=existing_database)
    from ui.app import CadryApp
    app = CadryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
