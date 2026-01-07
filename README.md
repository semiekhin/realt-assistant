# 🏢 Realt Assistant

AI-ассистент для риэлторов. Telegram-бот для работы с базой ЖК, генерации КП и расчётов.

## 🎯 Возможности

- **База ЖК** — загружай документы (PDF, Excel, фото), бот автоматически парсит и структурирует
- **Умный поиск** — вопросы на естественном языке: "что есть до 15 млн?"
- **Генерация КП** — AI создаёт продающий контент, выбор из 6 стилей оформления
- **Выжимки** — краткая аналитика по ЖК в PDF
- **Vision API** — распознавание планировок и прайсов с изображений

## 🛠 Стек

- Python 3.12+
- FastAPI
- SQLite
- OpenAI GPT-4o-mini
- ReportLab (PDF)
- PyMuPDF, Pandas, Pillow

## 📁 Структура
```
realt-assistant/
├── app.py                 # FastAPI + роутинг
├── run_polling.py         # Запуск в режиме polling
├── config.py              # Конфигурация
├── bot/
│   ├── states.py          # FSM состояния
│   └── handlers/          # Обработчики команд
│       ├── start.py       # /start, меню
│       ├── add_property.py # Добавление ЖК
│       ├── query.py       # Поиск, просмотр
│       └── kp.py          # Генерация КП
├── services/
│   ├── telegram.py        # Telegram API
│   ├── llm.py             # OpenAI API
│   ├── parser.py          # Парсинг файлов
│   ├── content_composer.py # AI-контент для документов
│   ├── kp_generator_v2.py # PDF рендеринг
│   └── pdf_styles.py      # Стили оформления
├── db/
│   ├── database.py        # SQLite операции
│   └── models.py          # Dataclass модели
└── data/
    ├── assistant.db       # База данных
    ├── uploads/           # Загруженные файлы
    └── kp_output/         # Сгенерированные PDF
```

## 🚀 Установка
```bash
# Клонировать репо
git clone https://github.com/YOUR_USERNAME/realt-assistant.git
cd realt-assistant

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные
cp .env.example .env
# Заполнить TELEGRAM_BOT_TOKEN и OPENAI_API_KEY

# Запустить
python run_polling.py
```

## ⚙️ Конфигурация (.env)
```
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
```

## 📖 Использование

1. `/start` — главное меню
2. **Добавить ЖК** → ввести название → загрузить файлы → бот парсит
3. **Мои ЖК** → выбрать объект → работать с документами
4. **Создать КП** → описать запрос → выбрать стиль → получить PDF
5. **Поиск** → вопрос на естественном языке

## 🎨 Стили КП

| Стиль | Описание |
|-------|----------|
| 🖤 Premium | Тёмный, золотые акценты, роскошь |
| 💼 Business | Строгий, зелёные акценты, факты |
| 🔷 Corporate | Сдержанный, профессиональный |
| 🎨 Modern | Яркий, дружелюбный |
| ⬜ Minimal | Чистый, чёрно-белый |
| 🧡 Warm | Тёплый, для семей |

## 📋 Roadmap

См. [ROADMAP.md](ROADMAP.md)

## 📄 Лицензия

MIT
