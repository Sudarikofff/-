from pathlib import Path

APP_NAME = "Личный состав"
APP_VERSION = "1.1.0"

ROOT_DIR = Path(__file__).parent

DATABASE_FILE = ROOT_DIR / "database" / "discipline.db"

BACKUP_DIR = ROOT_DIR / "backup"

LOGO_FILE = ROOT_DIR / "assets" / "logo.png"
ICON_FILE = ROOT_DIR / "assets" / "logo.ico"