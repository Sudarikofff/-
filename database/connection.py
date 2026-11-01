import sqlite3
import os
from pathlib import Path

# Папка рядом с EXE
BASE_DIR = Path(__file__).resolve().parent.parent

# Папка database
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

# Файл базы данных
DATABASE_PATH = Path(os.environ.get("DISCIPLINE_DB_PATH", DATABASE_DIR / "discipline.db"))


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection