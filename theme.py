import customtkinter as ctk

# ==========================================================
# Палитра ПС ФСБ РФ
# ==========================================================

BACKGROUND = "#F3F5F7"

SIDEBAR = "#0B3D2E"
SIDEBAR_LIGHT = "#14532D"

PRIMARY = "#0F5132"
PRIMARY_HOVER = "#146C43"

SECONDARY = "#C99A2E"
SECONDARY_HOVER = "#A67C1C"

SUCCESS = "#1E7A46"
INFO = "#0E7490"
WARNING = "#B7791F"
DANGER = "#B42318"

CARD = "#FFFFFF"
CARD_HOVER = "#F8FAF8"

BORDER = "#DEE5E2"

TEXT = "#10261A"
TEXT_SECONDARY = "#5E6B63"
TEXT_LIGHT = "#FFFFFF"

TABLE_HEADER = "#0F5132"
TABLE_SELECTED = "#DDEEDF"

# ==========================================================
# Совместимость со старыми файлами
# ==========================================================

# Золотой цвет (используется в app.py и других модулях)
GOLD = SECONDARY

# Активная кнопка бокового меню
SIDEBAR_ACTIVE = SIDEBAR_LIGHT

# Цвета карточек статистики
SUCCESS_BG = "#EAF6EE"
WARNING_BG = "#FFF8E8"
DANGER_BG = "#FDECEC"
INFO_BG = "#EAF5FB"

# Цвет текста на кнопках
BUTTON_TEXT = "#FFFFFF"

# ==========================================================
# Поля ввода (светлая тема)
# ==========================================================

INPUT_BG = "#FFFFFF"            # фон полей ввода
INPUT_BORDER = "#C8D6C8"        # рамка
INPUT_HOVER = "#B5C8B5"         # рамка при наведении

INPUT_TEXT = "#173B2A"          # текст в полях
PLACEHOLDER = "#65736A"         # текст подсказки

DROPDOWN_BG = "#FFFFFF"         # выпадающий список
DROPDOWN_HOVER = "#EEF6EC"      # наведение в списке
DROPDOWN_BUTTON = "#E8EFE6"     # кнопка справа у ComboBox
DROPDOWN_BUTTON_HOVER = "#D8E8D5"

TABLE_HEADER = "#173B2A"
TABLE_HEADER_HOVER = "#2E5E3E"
TABLE_SELECT = "#DCEFD8"
TABLE_TEXT = "#173B2A"

# ==========================================================
# Шрифты
# ==========================================================

TITLE_FONT = ("DejaVu Sans", 28, "bold")
SUBTITLE_FONT = ("DejaVu Sans", 18, "bold")
HEADER_FONT = ("DejaVu Sans", 14, "bold")
TEXT_FONT = ("DejaVu Sans", 14)
BUTTON_FONT = ("DejaVu Sans", 14, "bold")
SMALL_FONT = ("DejaVu Sans", 12)

APP_NAME = "Личный состав"
APP_VERSION = "1.1.0"
# Consistent defaults for controls without an explicit font.
ctk.ThemeManager.theme["CTkFont"]["family"] = "DejaVu Sans"
ctk.ThemeManager.theme["CTkFont"]["size"] = 14
