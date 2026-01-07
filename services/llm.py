"""
Сервис для работы с LLM (OpenAI GPT-4)
"""
import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


EXTRACT_PROPERTY_PROMPT = """Ты — помощник риэлтора. Проанализируй предоставленные материалы о жилом комплексе и извлеки структурированную информацию.

Верни JSON со следующими полями (если данные не найдены, оставь пустую строку или null):

{
    "name": "Название ЖК",
    "address": "Адрес (город, улица)",
    "developer": "Название застройщика",
    "completion_date": "Срок сдачи (Q1 2025, Сдан, 4 квартал 2025, и т.д.)",
    
    "price_min": 4200000,
    "price_max": 15800000,
    "price_per_sqm_min": 120000,
    "price_per_sqm_max": 180000,
    
    "apartment_types": "студии, 1к, 2к, 3к",
    "area_min": 24.5,
    "area_max": 95.0,
    
    "payment_options": "100%, рассрочка, ипотека",
    "installment_terms": "30% первый взнос, рассрочка 24 месяца",
    "mortgage_info": "Ипотека от 5.9%, аккредитация: Сбербанк, ВТБ",
    
    "installment_min_pv": 30,
    "installment_max_months": 24,
    "installment_markup": 0,
    
    "commission": "3% или 150 000 ₽",
    
    "description": "Краткое описание ЖК (2-3 предложения)",
    "features": "Особенности: парковка, детский сад, консьерж, и т.д."
}

ВАЖНО ПО УСЛОВИЯМ РАССРОЧКИ:
- installment_min_pv: минимальный первоначальный взнос В ПРОЦЕНТАХ (число: 10, 20, 30, 50)
- installment_max_months: максимальный срок рассрочки В МЕСЯЦАХ (число: 12, 18, 24, 36)
- installment_markup: удорожание за рассрочку В ПРОЦЕНТАХ (число: 0 если без удорожания, 5, 10, 15)

Примеры извлечения:
- "ПВ от 30%, рассрочка до сдачи (18 мес)" → installment_min_pv: 30, installment_max_months: 18
- "Рассрочка 0%" → installment_markup: 0
- "Удорожание 10% годовых" → installment_markup: 10
- "Беспроцентная рассрочка" → installment_markup: 0

ОБЩИЕ ПРАВИЛА:
- Цены указывай в рублях (числом, без пробелов)
- Площади в квадратных метрах (числом с точкой)
- Если видишь таблицу с ценами — извлеки минимальную и максимальную
- Если есть несколько корпусов/очередей — укажи в описании

Отвечай ТОЛЬКО валидным JSON, без markdown и комментариев."""


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
