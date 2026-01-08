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

### 5. Vision-first парсинг
PDF рендерится в JPEG страницы и отправляется в GPT-4o Vision. Видим прайсы, планировки, таблицы.

### 6. Запрет галлюцинаций в промпте
В промпте LLM: "Если данных нет — ставь null. ЗАПРЕЩЕНО выдумывать."

---

## 🏗 Архитектурные решения

### Универсальный handler вместо FSM (08.01.2026 вечер)
**Было:** FSM с кучей состояний и меню
**Стало:** handle_universal() — любое сообщение → RAG → LLM → ответ

FSM оставлен ТОЛЬКО для загрузки файлов (ADD_PROPERTY_NAME, ADD_PROPERTY_FILES, ADD_PROPERTY_CONFIRM)

### LLM → HTML → PDF вместо фиксированных стилей (08.01.2026 вечер)
**Было:** 6 фиксированных стилей PDF (premium, business и т.д.)
**Стало:** LLM генерирует HTML → wkhtmltopdf конвертирует в PDF

Файл: services/html_to_pdf.py

### gpt-4o вместо gpt-4o-mini (08.01.2026 вечер)
**Проблема:** gpt-4o-mini пропускал квартиры при поиске по ценам (находил 2 из 5)
**Решение:** Сменили на gpt-4o — находит все 5 из 5

**Принцип:** Не экономить на модели. Это коммерческий продукт, важен результат.

### RAG вместо жёстких таблиц (08.01.2026)
**Было предложено:** таблица `units` для квартир
**Решение:** Отказ в пользу RAG

**Почему:**
- Жёсткие таблицы = шаблонный подход
- Каждый новый тип данных = новый код
- RAG: любые данные → LLM понимает ВСЁ

### Никаких роутеров и интентов
**Было предложено:** Router LLM с фиксированными интентами
**Решение:** Отказ — LLM сам разберётся что делать

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
cat > /tmp/count_apts.py << 'EOF'
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
        if 15000000 <= price <= 19000000:  # изменить диапазон
            meta = all_data['metadatas'][i]
            num_match = re.search(r'Номер помещения\s*[–-]\s*(\d+)', doc)
            num = num_match.group(1) if num_match else '?'
            apartments.append({'jk': meta.get('property_name', ''), 'num': num, 'price': price})

print(f"Всего квартир в диапазоне: {len(apartments)}\n")
for apt in sorted(apartments, key=lambda x: x['price']):
    print(f"{apt['jk']} №{apt['num']} — {apt['price']/1_000_000:.2f} млн")
