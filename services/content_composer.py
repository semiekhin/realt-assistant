"""
Content Composer — LLM создаёт контент документа, а не просто подставляет данные
"""
import json
import re
from typing import Dict, Any, Optional, List
from services.llm import client
from config import OPENAI_MODEL


COMPOSE_KP_PROMPT = """Ты — профессиональный копирайтер в недвижимости. Создаёшь продающие коммерческие предложения.

ЗАДАЧА: Создай контент для КП на основе сырых данных. Не просто перечисли факты — сделай текст, который продаёт.

СЫРЫЕ ДАННЫЕ О ЖК:
{property_data}

ДАННЫЕ ИЗ ДОКУМЕНТОВ:
{extracted_text}

ЗАПРОС КЛИЕНТА: {query}

ЦЕЛЕВАЯ АУДИТОРИЯ: {audience}

ПРИНЦИПЫ:
1. Выдели 3-5 главных преимуществ под эту аудиторию
2. Цену подай выгодно (сравни с рынком если есть данные)
3. Убери технический мусор, оставь суть
4. Добавь эмоцию где уместно
5. Если данных нет — не выдумывай, пропусти

СОЗДАЙ JSON:
{
    "headline": "Цепляющий заголовок (5-8 слов)",
    "subheadline": "Подзаголовок с ключевой выгодой",
    
    "hero_section": {
        "price": "Цена с контекстом (например: '12.5 млн — на 10% ниже рынка')",
        "price_per_sqm": "Цена за метр если есть",
        "key_fact": "Главный факт (площадь, этаж, вид)"
    },
    
    "features": [
        {
            "title": "Название преимущества",
            "description": "Описание в 1-2 предложения"
        }
    ],
    
    "apartment_description": "2-3 предложения о самой квартире, планировке, что в ней хорошего",
    
    "location_description": "1-2 предложения о локации, если есть данные",
    
    "terms": {
        "payment": "Условия оплаты человеческим языком",
        "deadline": "Сроки сдачи с контекстом"
    },
    
    "call_to_action": "Призыв к действию (1 предложение)",
    
    "style_recommendation": "premium|business|modern|minimal|warm — какой стиль оформления подойдёт"
}

Отвечай ТОЛЬКО валидным JSON."""


COMPOSE_SUMMARY_PROMPT = """Ты — аналитик недвижимости. Создаёшь понятные информационные сводки по ЖК.

ЗАДАЧА: Создай структурированную выжимку по ЖК. Выдели главное, убери воду.

СЫРЫЕ ДАННЫЕ:
{property_data}

ДАННЫЕ ИЗ ДОКУМЕНТОВ:
{extracted_text}

ПРИНЦИПЫ:
1. Структурируй хаотичную информацию
2. Выдели ключевые цифры
3. Отметь плюсы и возможные минусы
4. Сравни с рынком если можешь
5. Не выдумывай — если данных нет, так и напиши

СОЗДАЙ JSON:
{
    "title": "Название ЖК",
    "subtitle": "Класс/позиционирование (1 строка)",
    
    "quick_facts": [
        {"label": "Застройщик", "value": "..."},
        {"label": "Локация", "value": "..."},
        {"label": "Срок сдачи", "value": "..."},
        {"label": "Цены", "value": "от X до Y млн"}
    ],
    
    "description": "3-4 предложения — что это за проект, для кого, чем выделяется",
    
    "apartments": {
        "types": "Какие квартиры есть",
        "areas": "Диапазон площадей",
        "price_analysis": "Анализ цен (дорого/дёшево/средне для района)"
    },
    
    "pros": ["Плюс 1", "Плюс 2", "Плюс 3"],
    "cons": ["Минус или нюанс 1", "Минус 2"],
    
    "buying_conditions": "Условия покупки простым языком",
    
    "conclusion": "Вывод в 1-2 предложения — кому подойдёт этот ЖК",
    
    "style_recommendation": "minimal|business"
}

Отвечай ТОЛЬКО валидным JSON."""


async def compose_kp_content(
    property_data: Dict[str, Any],
    extracted_text: str = "",
    query: str = "",
    audience: str = ""
) -> Optional[Dict[str, Any]]:
    """
    LLM создаёт контент для КП
    
    Args:
        property_data: Данные о ЖК из базы
        extracted_text: Сырой текст из файлов
        query: Запрос пользователя ("КП на двушку для семьи")
        audience: Целевая аудитория
    
    Returns:
        Структурированный контент для генерации PDF
    """
    
    if not client:
        return None
    
    # Определяем аудиторию из запроса если не указана
    if not audience:
        query_lower = query.lower()
        if any(w in query_lower for w in ["семь", "дет", "ребен"]):
            audience = "молодая семья с детьми"
        elif any(w in query_lower for w in ["инвест", "сдавать", "аренд"]):
            audience = "инвестор"
        elif any(w in query_lower for w in ["студ", "перв", "молод"]):
            audience = "молодой человек, первая квартира"
        else:
            audience = "покупатель квартиры для себя"
    
    # Форматируем данные о ЖК
    prop_str = json.dumps(property_data, ensure_ascii=False, indent=2) if isinstance(property_data, dict) else str(property_data)
    
    # Ограничиваем extracted_text
    extracted_text = extracted_text[:8000] if extracted_text else "Нет дополнительных данных"
    
    prompt = COMPOSE_KP_PROMPT.replace(
        "{property_data}", prop_str
    ).replace(
        "{extracted_text}", extracted_text
    ).replace(
        "{query}", query or "стандартное КП"
    ).replace(
        "{audience}", audience
    )
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты создаёшь продающий контент. Отвечай только JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Больше креатива
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Чистим от markdown
        if "```" in result_text:
            # Убираем ```json и ```
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
        
        # Ищем JSON объект
        match = re.search(r'\{[\s\S]*\}', result_text)
        if match:
            result_text = match.group(0)
        
        print(f"[COMPOSER] Raw response length: {len(result_text)}")
        print(f"[COMPOSER] First 200 chars: {result_text[:200]}")
        
        content = json.loads(result_text)
        print(f"[COMPOSER] Created KP content: {content.get('headline', 'no headline')}")
        return content
        
    except json.JSONDecodeError as e:
        print(f"[COMPOSER] JSON parse error: {e}")
        print(f"[COMPOSER] Raw response: {result_text[:1000]}")
        return None
    except Exception as e:
        print(f"[COMPOSER] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def compose_summary_content(
    property_data: Dict[str, Any],
    extracted_text: str = ""
) -> Optional[Dict[str, Any]]:
    """
    LLM создаёт контент для информационной выжимки
    """
    
    if not client:
        return None
    
    prop_str = json.dumps(property_data, ensure_ascii=False, indent=2) if isinstance(property_data, dict) else str(property_data)
    extracted_text = extracted_text[:10000] if extracted_text else "Нет дополнительных данных"
    
    prompt = COMPOSE_SUMMARY_PROMPT.replace(
        "{property_data}", prop_str
    ).replace(
        "{extracted_text}", extracted_text
    )
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты аналитик недвижимости. Отвечай только JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,  # Меньше креатива, больше точности
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Чистим от markdown
        if "```" in result_text:
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
        
        # Ищем JSON объект
        match = re.search(r'\{[\s\S]*\}', result_text)
        if match:
            result_text = match.group(0)
        
        content = json.loads(result_text)
        print(f"[COMPOSER] Created summary content: {content.get('title', 'no title')}")
        return content
        
    except Exception as e:
        print(f"[COMPOSER] Summary error: {e}")
        return None


def property_to_dict(prop) -> Dict[str, Any]:
    """Конвертирует Property объект в словарь для LLM"""
    return {
        "name": prop.name,
        "address": prop.address,
        "developer": prop.developer,
        "completion_date": prop.completion_date,
        "price_min": prop.price_min,
        "price_max": prop.price_max,
        "price_per_sqm_min": prop.price_per_sqm_min,
        "price_per_sqm_max": prop.price_per_sqm_max,
        "apartment_types": prop.apartment_types,
        "area_min": prop.area_min,
        "area_max": prop.area_max,
        "payment_options": prop.payment_options,
        "installment_terms": prop.installment_terms,
        "mortgage_info": prop.mortgage_info,
        "commission": prop.commission,
        "description": prop.description,
        "features": prop.features
    }
