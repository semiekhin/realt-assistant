# Realt Assistant — База знаний

## 🔑 Критически важные знания

### 1. Запуск бота — только через полный путь к python
```bash
# НЕПРАВИЛЬНО — venv не активируется в фоне
nohup python run_polling.py &

# ПРАВИЛЬНО — полный путь к интерпретатору
cd /opt/realt-assistant
/opt/realt-assistant/venv/bin/python -u run_polling.py > bot.log 2>&1 &
```

### 2. Другие сервисы на сервере — НЕ ТРОГАТЬ
- /opt/bot — RIZALTA PROD (порт 8000)
- /opt/bot-dev — RIZALTA DEV (порт 8002)
- /opt/sofia-claude, /opt/sofia-gpt

При pkill всегда указывать полный путь:
```bash
pkill -f "realt-assistant.*run_polling"
```

### 3. Модель — gpt-4o (НЕ mini!)
**Критично:** Для точной работы с числами и поиска по ценам используем gpt-4o, не gpt-4o-mini. Mini пропускает данные при фильтрации.

### 4. RAG-ядро (v0.5.1)
- ChromaDB в `/opt/realt-assistant/data/chroma/`
- Эмбеддинги: OpenAI text-embedding-3-small
- Чанки: 800 символов, overlap 100
- Коллекции по пользователям: `user_{telegram_id}`
- **limit=50** для полноты результатов поиска

### 5. YGroup API (NEW)
```
Base URL: https://api-ru.ygroup.ru/v2/
Auth: Bearer token (из аккаунта риэлтора)

Endpoints:
- GET /facilities?types=6&city_id={id} — список ЖК
- GET /clusters?facility_id={id} — корпуса/подъезды  
- GET /lots?cluster_id={id} — квартиры
```

---

## 🏗 Архитектурные решения

### YGroup API вместо парсинга PDF (08.01.2026)
**Было:** Риэлтор загружает PDF → Vision парсит → RAG индексирует
**Стало:** Бот загружает данные из YGroup API → структурированное хранение

**Почему:**
- 100% точные данные (не зависим от качества PDF)
- Структурированные квартиры в таблице units
- SQL запросы для точного поиска по ценам/площадям
- Шахматки и прайсы уже распаршены в YGroup

### Гибридная архитектура SQL + RAG (08.01.2026)
**Проблема:** RAG с limit=50 не масштабируется. При 1000+ чанков теряем данные.

**Решение:**
- Точные запросы (цены, площади) → SQL к таблице units
- Семантические запросы (описания, УТП) → RAG
- Смешанные → комбинируем оба подхода

**Пример:**
```
"от 15 до 19 млн" → SELECT * FROM units WHERE price BETWEEN 15M AND 19M
"чем лучше конкурентов?" → RAG поиск по описаниям
"недорогие у моря" → SQL (цена) + RAG (море)
```

### Кастомные поля от риэлтора (08.01.2026)
**Концепция:** YGroup даёт структуру, риэлтор добавляет своё:
- УТП / фишки объекта
- Особые условия рассрочки
- Своя комиссия (если отличается)
- Заметки

### Универсальный handler вместо FSM (08.01.2026)
**Было:** FSM с кучей состояний и меню
**Стало:** handle_universal() — любое сообщение → RAG → LLM → ответ

FSM оставлен ТОЛЬКО для загрузки файлов (ADD_PROPERTY_NAME, ADD_PROPERTY_FILES, ADD_PROPERTY_CONFIRM)

### LLM → HTML → PDF вместо фиксированных стилей (08.01.2026)
**Было:** 6 фиксированных стилей PDF (premium, business и т.д.)
**Стало:** LLM генерирует HTML → wkhtmltopdf конвертирует в PDF

---

## 🌐 YGroup API — детали

### Структура данных
```
facilities (ЖК)
├── id, name, city_name, district_name
├── min_total_price, min_price_per_m2
├── min_area_m2, max_area_m2
├── commission_percent
├── active_lots_amount
└── facility_main_image

clusters (корпуса)
├── id, facility_id, name
├── total_floors, apartments_per_floor
├── commissioning_year, commissioning_quarter
└── is_completed

lots (квартиры)
├── id, cluster_id, name (№ 207)
├── total_price, price_per_m2
├── area_m2, layout_type (комнатность)
├── decoration_type
├── position.vertical_position (этаж)
└── layout_images (URL планировки)
```

### Авторизация
- Токен из аккаунта риэлтора
- Header: `Authorization: Bearer {token}`
- Токен может истекать — нужна обработка 401

### Рекомендации по использованию
- **Кэширование** — загрузили ЖК → сохранили в БД → не дёргаем API
- **Редкие обновления** — кнопка "Обновить данные" для синхронизации
- **Паузы между запросами** — 1-2 сек чтобы не палиться

---

## 🛠 Частые команды

### Запуск и остановка
```bash
cd /opt/realt-assistant
/opt/realt-assistant/venv/bin/python -u run_polling.py > bot.log 2>&1 &
pkill -f "realt-assistant.*run_polling"
ps aux | grep "realt-assistant" | grep -v grep
```

### Перезапуск одной командой
```bash
pkill -f "realt-assistant.*run_polling" 2>/dev/null; sleep 1 && cd /opt/realt-assistant && /opt/realt-assistant/venv/bin/python -u run_polling.py > bot.log 2>&1 & sleep 2 && tail -5 bot.log
```

### Логи
```bash
tail -f /opt/realt-assistant/bot.log
tail -50 /opt/realt-assistant/bot.log
```

### База данных
```bash
sqlite3 /opt/realt-assistant/data/assistant.db "SELECT id, name, price_min, price_max FROM properties;"
```

### RAG — проверка квартир в диапазоне цен
```bash
cat > /tmp/count_apts.py << 'PYEOF'
import sys
sys.path.insert(0, '/opt/realt-assistant')
from services.rag import get_collection
import re

collection = get_collection(512319063)
all_data = collection.get(include=['documents', 'metadatas'])

apartments = []
for i, doc in enumerate(all_data['documents']):
    price_match = re.search(r'Цена\s*[–-]\s*(\d+)', doc)
    if price_match:
        price = int(price_match.group(1))
        if 15000000 <= price <= 19000000:
            meta = all_data['metadatas'][i]
            num_match = re.search(r'Номер помещения\s*[–-]\s*(\d+)', doc)
            num = num_match.group(1) if num_match else '?'
            apartments.append({'jk': meta.get('property_name', ''), 'num': num, 'price': price})

print(f"Всего квартир в диапазоне: {len(apartments)}\n")
for apt in sorted(apartments, key=lambda x: x['price']):
    print(f"{apt['jk']} №{apt['num']} — {apt['price']/1_000_000:.2f} млн")
PYEOF
/opt/realt-assistant/venv/bin/python /tmp/count_apts.py
```

### Git
```bash
cd /opt/realt-assistant
git add -A && git status
git commit -m "описание"
git push
```

---

## 🐛 Решённые проблемы

### RAG находит не все квартиры (08.01.2026)
**Проблема:** Запрос "от 15 до 19 млн" находил 2 из 5 квартир
**Причины:**
1. limit=10 — мало чанков
2. gpt-4o-mini — пропускает данные
3. Слабый промпт

**Решение:**
1. limit=50
2. Сменили на gpt-4o
3. Добавили алгоритм в промпт

**Системное решение (планируется):** Таблица units + SQL запросы

### RAG не масштабируется (08.01.2026)
**Проблема:** При 1000+ чанков limit=50 это 5% данных
**Решение:** Гибрид SQL + RAG. Точные запросы → SQL, семантические → RAG

### Галлюцинации — бот выдумывает комиссию
**Причина:** Промпт не запрещал выдумывать данные
**Решение:** Добавить в промпт явный запрет и инструкцию ставить null

---

## 📊 Маршрут обработки запроса (текущий)
```
1. Telegram → app.py process_message()
2. Роутинг:
   - /start, /help, /add, /calc → спец. handlers
   - FSM состояния → handlers добавления ЖК
   - Всё остальное → handle_universal()
3. handle_universal():
   - save_message() → история
   - enrich_query_for_rag() → ключевые слова
   - rag_search() → ChromaDB, limit=50
   - extract_price_range() → фильтр по цене
   - get_chat_history() → контекст
   - universal_respond() → GPT-4o
4. execute_action():
   - text → send_message()
   - calc_* → калькулятор → format → send
   - generate_kp → HTML → PDF → send_document()
```

---

## 🔗 Полезные ссылки

- GitHub: https://github.com/semiekhin/realt-assistant
- ТЗ RAG: docs/RAG_CORE_SPEC.md
- YGroup: https://web.ygroup.ru/
- ChromaDB: https://docs.trychroma.com/
