"""
Конфигурация Realt Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "assistant.db"

# Создаём папки если нет
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # https://yourdomain.com/webhook

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Настройки
MAX_FILE_SIZE_MB = 20
SUPPORTED_EXTENSIONS = {
    "documents": [".pdf", ".docx", ".doc", ".txt"],
    "spreadsheets": [".xlsx", ".xls", ".csv"],
    "images": [".jpg", ".jpeg", ".png", ".webp"],
}
