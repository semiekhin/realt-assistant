# Realt Assistant — Деплой на сервер

## Структура проекта

```
realt-assistant/
├── app.py                 # FastAPI + webhook
├── run_polling.py         # Dev режим (polling)
├── config.py              # Настройки
├── requirements.txt
│
├── bot/
│   ├── states.py          # FSM состояния
│   └── handlers/
│       ├── start.py       # /start, меню
│       ├── add_property.py # Добавление ЖК
│       └── query.py       # Просмотр, вопросы
│
├── services/
│   ├── telegram.py        # Telegram API
│   ├── llm.py             # OpenAI GPT-4
│   └── parser.py          # Парсинг файлов
│
├── db/
│   ├── database.py        # SQLite
│   └── models.py          # Модели данных
│
└── data/
    └── uploads/           # Загруженные файлы
```

## Деплой на сервер

### 1. Подключение и создание папки

```bash
ssh -p 2222 root@72.56.64.91

mkdir -p /opt/realt-assistant
cd /opt/realt-assistant
```

### 2. Загрузка файлов

**Вариант A: Через scp (с локальной машины)**
```bash
scp -P 2222 realt-assistant.tar.gz root@72.56.64.91:/opt/
ssh -p 2222 root@72.56.64.91
cd /opt && tar -xzvf realt-assistant.tar.gz
mv realt-assistant/* /opt/realt-assistant/
```

**Вариант B: Через git (когда создадим репо)**
```bash
git clone https://github.com/USER/realt-assistant.git /opt/realt-assistant
```

### 3. Настройка окружения

```bash
cd /opt/realt-assistant

# Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаём .env
cp .env.example .env
nano .env
```

### 4. Заполняем .env

```env
TELEGRAM_BOT_TOKEN=7xxxxxx:AAxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
```

### 5. Тестовый запуск (polling)

```bash
cd /opt/realt-assistant
source venv/bin/activate
python run_polling.py
```

Открываем бота в Telegram, проверяем /start

### 6. Systemd сервис (production)

```bash
nano /etc/systemd/system/realt-assistant.service
```

```ini
[Unit]
Description=Realt Assistant Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/realt-assistant
Environment=PATH=/opt/realt-assistant/venv/bin
ExecStart=/opt/realt-assistant/venv/bin/python run_polling.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable realt-assistant
systemctl start realt-assistant
systemctl status realt-assistant
```

### 7. Логи

```bash
journalctl -u realt-assistant -f
```

---

## Сценарий использования

```
Пользователь: /start
Бот: "Привет! Я твой ассистент. Добавим первый ЖК?"

Пользователь: нажимает "➕ Добавить ЖК"
Бот: "Как называется ЖК?"

Пользователь: "ЖК Солнечный"
Бот: "Отправь материалы..."

Пользователь: [файл.pdf] [файл.xlsx] [фото]
Бот: "📄 Принял..." "📊 Принял..." "🖼 Принял..."

Пользователь: "готово"
Бот: "⏳ Анализирую..."
Бот: "✅ ЖК добавлен! [сводка данных]"

Пользователь: "что есть до 5 млн?"
Бот: "[ответ на основе базы]"
```

---

## TODO

- [ ] Webhook вместо polling (Cloudflare Tunnel)
- [ ] Голосовой ввод (Whisper)
- [ ] Генерация КП (PDF)
- [ ] Редактирование ЖК
- [ ] CRM (клиенты)
