"""
Сервис для работы с LLM (OpenAI GPT-4)
"""
import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


EXTRACT_PROPERTY_PROMPT = """Ты — помощник риэлтора. Проанализируй материалы о жилом комплексе и извлеки структурированную информацию.

Верни JSON со следующими полями (если данных НЕТ в материалах — ставь null, НЕ ВЫДУМЫВАЙ):

{
    "name": "Название ЖК",
    "address": "Полный адрес (город, район, улица, дом)",
    "city": "Город",
    "developer": "Полное название застройщика",
    "completion_date": "Срок сдачи (Q1 2030, 1 квартал 2030, и т.д.)",
    
    "price_min": 21000000,
    "price_max": 58000000,
    "price_per_sqm_min": 800000,
    "price_per_sqm_max": 900000,
    
    "apartment_types": "студии, 1к, 2к, 3к",
    "area_min": 24.0,
    "area_max": 70.0,
    
    "payment_options": "100%, рассрочка, ипотека",
    "installment_terms": "50% первый взнос, рассрочка 12 месяцев",
    "mortgage_info": "Ипотека от банков",
    
    "installment_min_pv": 50,
    "installment_max_months": 12,
    "installment_markup": 0,
    
    "commission": null,
    
    "distance_to_sea": "350 м",
    "territory_area": "9 га",
    "hotel_operator": "Lee Prime",
    
    "description": "Краткое описание ЖК (2-3 предложения)",
    "features": "Ключевые особенности: пляж, дендропарк, wellness 3600 м², медцентр"
}

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

1. ЦЕНЫ — собери ВСЕ цены из материалов и найди минимум/максимум:
   - Если видишь: 21 172 800, 33 680 640, 51 837 100 → price_min: 21172800, price_max: 51837100
   - Если видишь "от 25 760 000" → это price_min
   - Если видишь цену за м² — запиши в price_per_sqm_min/max

2. НЕ ВЫДУМЫВАЙ ДАННЫЕ:
   - Если комиссия НЕ указана в документах → "commission": null
   - Если нет информации о поле → ставь null или пустую строку
   - НИКОГДА не придумывай проценты, суммы, сроки

3. РАССРОЧКА — извлекай точные числа:
   - "50/50" → installment_min_pv: 50
   - "рассрочка до сдачи (12 мес)" → installment_max_months: 12
   - "без удорожания" или "0%" → installment_markup: 0
   - "удорожание 5%" → installment_markup: 5

4. АДРЕС — собери полный:
   - Город + район + улица + дом если есть

5. ОСОБЕННОСТИ — выпиши всё важное:
   - До моря, пляж, территория, дендропарк, wellness, медцентр, оператор

Отвечай ТОЛЬКО валидным JSON, без markdown и пояснений."""


async def extract_property_data(text: str, property_name: str = "") -> Optional[Dict[str, Any]]:
    if not client:
        print("[LLM] OpenAI client not initialized")
        return None
    
    user_prompt = f"Название ЖК: {property_name}\n\n" if property_name else ""
    user_prompt += f"Материалы:\n\n{text[:15000]}"
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": EXTRACT_PROPERTY_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        data = json.loads(result_text)
        print(f"[LLM] Extracted property data: {data.get('name', 'unknown')}")
        return data
        
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[LLM] extract_property_data error: {e}")
        return None


async def extract_text_from_image(image_base64: str) -> Optional[str]:
    if not client:
        return None
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Проанализируй это изображение недвижимости. 

Если это планировка квартиры:
- Укажи общую площадь
- Перечисли комнаты и их площади
- Опиши особенности (балкон, гардеробная, санузлы)

Если это прайс-лист или таблица:
- Извлеки все данные с ценами и площадями
- Сохрани структуру

Если есть текст — извлеки его полностью.
Отвечай на русском языке."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[LLM] Vision API error: {e}")
        return None


QUERY_PROMPT = """Ты — помощник риэлтора. У тебя есть база данных ЖК с детальной информацией.

База ЖК:
{properties_context}

ВАЖНО:
- Если в "ДЕТАЛЬНЫЕ ДАННЫЕ" есть информация о конкретных квартирах, планировках, ценах — используй её!
- Отвечай конкретно: площадь, цена, этаж, комнатность
- Если спрашивают "какие предложения" — перечисли все доступные варианты из данных
- Если данных нет — так и скажи

Формат ответа: краткий, структурированный, с эмодзи, удобный для Telegram."""


async def answer_query(query: str, properties_context: str) -> str:
    if not client:
        return "❌ Сервис временно недоступен"
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": QUERY_PROMPT.format(properties_context=properties_context)},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[LLM] answer_query error: {e}")
        return "❌ Произошла ошибка при обработке запроса"


async def quick_chat(message: str, context: str = "") -> str:
    if not client:
        return "❌ Сервис временно недоступен"
    
    system = "Ты — дружелюбный помощник риэлтора. Отвечай кратко и по делу."
    if context:
        system += f"\n\nКонтекст: {context}"
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[LLM] quick_chat error: {e}")
        return "❌ Произошла ошибка"


# === Универсальный handler (Этап 2) ===

import re

UNIVERSAL_PROMPT = """Ты — умный ассистент риэлтора.

Данные из документов:
---
{chunks}
---

ВАЖНО: Если пользователь просит СДЕЛАТЬ/СОЗДАТЬ/СГЕНЕРИРОВАТЬ документ (КП, предложение, PDF) — ОБЯЗАТЕЛЬНО верни JSON!

Действия:
1. Вопрос/информация — отвечай текстом
2. "сделай КП" / "создай предложение" — ВЕРНИ: {{"action": "generate_kp", "query": "что именно"}}
3. "посчитай рассрочку" — ВЕРНИ: {{"action": "calc_installment", "price": число, "pv": процент, "months": число}}
4. "посчитай ипотеку" — ВЕРНИ: {{"action": "calc_mortgage", "price": число, "pv": процент, "years": число, "program": "standard"}}
5. "посчитай доходность/ROI" — ВЕРНИ: {{"action": "calc_roi", "price": число, "rent": число, "occupancy": процент}}
6. "скинь файл/презентацию" — ВЕРНИ: {{"action": "send_file", "file_name": "название"}}

Ключевые слова для generate_kp: кп, КП, предложение, коммерческое, сделай документ, создай pdf
Ключевые слова для calc: рассрочка, ипотека, посчитай, расчёт, roi, доходность

Правила:
- Для КП ВСЕГДА возвращай JSON, НЕ пиши текст предложения сам
- Данных нет — скажи честно
- Отвечай кратко, на русском"""


async def universal_respond(query: str, chunks: list, history: list = None) -> dict:
    """Универсальный ответ на любой запрос"""
    if not client:
        return {"action": "text", "content": "❌ Сервис временно недоступен"}
    
    # Формируем контекст из чанков
    chunks_text = ""
    if chunks:
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            prop_name = meta.get("property_name", "")
            chunks_text += f"[{prop_name}] {chunk['text']}\n\n"
    else:
        chunks_text = "(нет данных)"
    
    # Собираем сообщения
    messages = [
        {"role": "system", "content": UNIVERSAL_PROMPT.format(chunks=chunks_text[:12000])}
    ]
    
    # Добавляем историю
    if history:
        for msg in history[-6:]:  # последние 6 сообщений
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": query})
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content.strip()
        return parse_llm_response(result_text)
        
    except Exception as e:
        print(f"[LLM] universal_respond error: {e}")
        return {"action": "text", "content": "❌ Произошла ошибка"}


def parse_llm_response(text: str) -> dict:
    """Парсим ответ LLM — текст или JSON с action"""
    
    # Ищем JSON в ответе
    json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', text)
    
    if json_match:
        try:
            action_data = json.loads(json_match.group())
            if "action" in action_data:
                return action_data
        except json.JSONDecodeError:
            pass
    
    # Если JSON не найден — это текстовый ответ
    return {"action": "text", "content": text}


# === Генерация HTML документов ===

GENERATE_HTML_PROMPT = """Ты — эксперт по созданию продающих коммерческих предложений для недвижимости.

Данные об объекте:
---
{property_data}
---

Дополнительные данные из документов:
---
{chunks}
---

Запрос клиента: {query}

Создай HTML-документ коммерческого предложения. Требования:
1. Профессиональный, продающий стиль
2. Акцент на преимуществах для клиента
3. Конкретные цифры и факты
4. Визуально привлекательный дизайн

ВЕРНИ ТОЛЬКО HTML КОД с инлайн-стилями. Структура:
- Шапка с названием ЖК
- Ключевые преимущества
- Характеристики объекта
- Цены и условия покупки
- Инфраструктура
- Контактная информация (оставить плейсхолдер)

Используй современный CSS: градиенты, скругления, тени.
Цветовая схема: профессиональная (темно-синий, белый, акценты).
HTML должен быть самодостаточным (inline styles)."""


async def generate_html_document(property_data: str, chunks: list, query: str = "") -> Optional[str]:
    """Генерирует HTML документ через LLM"""
    if not client:
        return None
    
    chunks_text = ""
    if chunks:
        for chunk in chunks:
            chunks_text += f"{chunk.get('text', '')}\n\n"
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": GENERATE_HTML_PROMPT.format(
                    property_data=property_data,
                    chunks=chunks_text[:8000],
                    query=query or "стандартное коммерческое предложение"
                )},
                {"role": "user", "content": f"Создай КП. {query}" if query else "Создай коммерческое предложение"}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        html = response.choices[0].message.content.strip()
        
        # Убираем markdown обёртку если есть
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        
        return html.strip()
        
    except Exception as e:
        print(f"[LLM] generate_html_document error: {e}")
        return None
