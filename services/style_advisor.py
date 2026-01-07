"""
Style Advisor — LLM определяет оптимальный стиль документа
"""
import json
from typing import Dict, Any, Optional
from services.llm import client
from config import OPENAI_MODEL


STYLE_ADVISOR_PROMPT = """Ты — эксперт по дизайну коммерческих предложений в недвижимости.

Проанализируй контекст и определи оптимальный стиль оформления PDF.

КОНТЕКСТ:
- ЖК: {property_name}
- Класс: {property_class}
- Цена: {price_range}
- Запрос клиента: {query}

ДОСТУПНЫЕ СТИЛИ:
1. premium — для элитной недвижимости. Тёмные тона, золотые акценты, минимализм, роскошь. Без emoji.
2. business — для инвесторов и деловых людей. Строгий, таблицы, зелёные акценты (деньги), факты.
3. modern — универсальный современный. Яркие акценты, градиенты, иконки, дружелюбный.
4. minimal — чистый и простой. Много воздуха, чёрно-белый, акцент на контенте.
5. warm — для семей. Тёплые цвета, уютный, эмоциональный, с иконками.

ОПРЕДЕЛИ:
1. Какой стиль лучше подходит
2. На чём сделать акцент (цена/локация/площадь/инфраструктура/инвестиции)
3. Тон коммуникации

Ответь ТОЛЬКО JSON:
{
    "style": "premium|business|modern|minimal|warm",
    "emphasis": ["price", "location", "area", "features", "investment"],
    "tone": "formal|neutral|friendly",
    "headline": "Короткий цепляющий заголовок для КП",
    "reasoning": "Почему этот стиль (1 предложение)"
}"""


async def get_style_recommendation(
    property_name: str,
    property_class: str = "",
    price_range: str = "",
    query: str = ""
) -> Dict[str, Any]:
    """
    Получить рекомендацию по стилю от LLM
    
    Returns:
        {
            "style": "modern",
            "emphasis": ["price", "area"],
            "tone": "friendly",
            "headline": "Ваша идеальная квартира",
            "reasoning": "..."
        }
    """
    
    # Дефолтный результат
    default = {
        "style": "modern",
        "emphasis": ["price", "area"],
        "tone": "neutral",
        "headline": f"Предложение: {property_name}",
        "reasoning": "Стиль по умолчанию"
    }
    
    if not client:
        return default
    
    # Определяем класс ЖК по цене если не указан
    if not property_class and price_range:
        try:
            # Пытаемся понять класс по цене
            if "млн" in price_range.lower():
                import re
                numbers = re.findall(r'[\d.]+', price_range)
                if numbers:
                    max_price = max(float(n) for n in numbers)
                    if max_price > 30:
                        property_class = "премиум"
                    elif max_price > 15:
                        property_class = "бизнес"
                    elif max_price > 8:
                        property_class = "комфорт"
                    else:
                        property_class = "эконом"
        except:
            pass
    
    prompt = STYLE_ADVISOR_PROMPT.format(
        property_name=property_name,
        property_class=property_class or "не указан",
        price_range=price_range or "не указана",
        query=query or "стандартное КП"
    )
    
    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты дизайн-консультант. Отвечай только JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Убираем markdown
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Валидация
        valid_styles = ["premium", "business", "modern", "minimal", "warm"]
        if result.get("style") not in valid_styles:
            result["style"] = "modern"
        
        print(f"[STYLE] Recommended: {result.get('style')} for {property_name}")
        return result
        
    except Exception as e:
        print(f"[STYLE] Advisor error: {e}")
        return default


def get_quick_style(property_name: str, price_min: int = None, price_max: int = None) -> str:
    """
    Быстрое определение стиля без LLM (по эвристикам)
    """
    name_lower = property_name.lower()
    
    # По названию
    premium_keywords = ["премиум", "elite", "luxury", "парк", "резиденц", "tower", "plaza"]
    business_keywords = ["бизнес", "central", "сити", "city", "офис"]
    warm_keywords = ["семейн", "дом", "уютн", "солнеч", "зелён"]
    
    for kw in premium_keywords:
        if kw in name_lower:
            return "premium"
    
    for kw in business_keywords:
        if kw in name_lower:
            return "business"
    
    for kw in warm_keywords:
        if kw in name_lower:
            return "warm"
    
    # По цене
    if price_max:
        if price_max > 30_000_000:
            return "premium"
        elif price_max > 15_000_000:
            return "business"
    
    return "modern"
