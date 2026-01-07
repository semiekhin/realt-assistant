"""
Обработчик генерации КП — с выбором стиля
"""
from typing import Dict
import json

from services.telegram import send_message, send_message_with_buttons, send_document
from services.content_composer import compose_kp_content, compose_summary_content, property_to_dict
from services.kp_generator_v2 import render_kp_from_content, render_summary_from_content
from db.database import (
    get_property,
    get_property_files,
    update_user_state,
    get_user_state,
    clear_user_state
)

# Описания стилей для пользователя
STYLE_DESCRIPTIONS = {
    "premium": "🖤 Премиум — тёмный, золотые акценты, роскошь",
    "business": "💼 Деловой — строгий, зелёные акценты, факты",
    "modern": "🎨 Современный — яркий, дружелюбный",
    "minimal": "⬜ Минимал — чистый, чёрно-белый",
    "warm": "🧡 Тёплый — уютный, для семей",
    "corporate": "🔷 Корпоративный — сдержанный, профессиональный"
}


async def handle_kp_for_property(chat_id: int, property_id: int):
    """Начать создание КП — запрос описания"""
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    update_user_state(chat_id, "kp_query", {"property_id": property_id})
    
    text = f"📄 <b>КП для {prop.name}</b>\n\n"
    text += "Опиши для кого и что нужно:\n\n"
    text += "<i>• «двушка для молодой семьи»\n"
    text += "• «студия под инвестиции»\n"
    text += "• «трёшка с видом на парк»\n"
    text += "• «самый выгодный вариант»</i>"
    
    buttons = [
        [{"text": "❌ Отмена", "callback_data": f"open_property_{property_id}"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_kp_query_received(chat_id: int, property_id: int, query: str):
    """Получили запрос — предлагаем выбор стиля"""
    
    # Сохраняем запрос и переходим к выбору стиля
    update_user_state(chat_id, "kp_style", {
        "property_id": property_id,
        "query": query
    })
    
    text = "🎨 <b>Выбери стиль оформления:</b>\n\n"
    
    buttons = [
        [{"text": "🖤 Премиум", "callback_data": "kp_style_premium"}],
        [{"text": "💼 Деловой", "callback_data": "kp_style_business"}],
        [{"text": "🔷 Корпоративный", "callback_data": "kp_style_corporate"}],
        [{"text": "🎨 Современный", "callback_data": "kp_style_modern"}],
        [{"text": "⬜ Минимал", "callback_data": "kp_style_minimal"}],
        [{"text": "🧡 Тёплый", "callback_data": "kp_style_warm"}],
        [{"text": "🤖 Авто (AI выберет)", "callback_data": "kp_style_auto"}],
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_kp_style_selected(chat_id: int, style: str):
    """Выбран стиль — генерируем КП"""
    
    state, state_data = get_user_state(chat_id)
    
    if state != "kp_style":
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    
    property_id = state_data.get("property_id")
    query = state_data.get("query", "")
    
    if not property_id:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    await handle_kp_generate(chat_id, property_id, query, style)


async def handle_kp_generate(chat_id: int, property_id: int, query: str, style_override: str = None):
    """Генерация КП через Content Composer"""
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    style_text = STYLE_DESCRIPTIONS.get(style_override, "автоматический") if style_override else "автоматический"
    await send_message(chat_id, f"⏳ Создаю КП...\n🎨 Стиль: {style_text}")
    
    # Собираем данные
    files = get_property_files(property_id)
    extracted_text = "\n\n".join([
        f"=== {f.file_name} ===\n{f.extracted_text}"
        for f in files 
        if f.extracted_text and len(f.extracted_text) > 50
    ])
    
    # Content Composer создаёт контент
    property_data = property_to_dict(prop)
    
    content = await compose_kp_content(
        property_data=property_data,
        extracted_text=extracted_text,
        query=query
    )
    
    if not content:
        await send_message(chat_id, "⚠️ Не удалось создать контент, делаю базовое КП...")
        
        content = {
            "headline": prop.name,
            "subheadline": query,
            "hero_section": {
                "price": f"{prop.price_min/1_000_000:.1f} млн ₽" if prop.price_min else "",
                "key_fact": f"{prop.apartment_types}" if prop.apartment_types else ""
            },
            "apartment_description": prop.description or "",
            "terms": {
                "payment": prop.payment_options or "",
                "deadline": prop.completion_date or ""
            },
            "style_recommendation": style_override or "modern"
        }
    
    # Применяем выбранный стиль (если не auto)
    if style_override and style_override != "auto":
        content["style_recommendation"] = style_override
    
    # Рендерим PDF
    pdf_path = await render_kp_from_content(
        content=content,
        property_name=prop.name
    )
    
    clear_user_state(chat_id)
    
    if pdf_path:
        headline = content.get("headline", "")
        style = content.get("style_recommendation", "modern")
        
        await send_document(chat_id, pdf_path, f"📄 {prop.name}")
        
        result_text = f"✅ <b>КП готово!</b>\n"
        result_text += f"🎨 Стиль: {STYLE_DESCRIPTIONS.get(style, style)}"
        
        buttons = [
            [{"text": "🔄 Другой стиль", "callback_data": f"kp_restyle_{property_id}"}],
            [{"text": "📄 Новое КП", "callback_data": f"kp_for_{property_id}"}],
            [{"text": "🔙 К ЖК", "callback_data": f"open_property_{property_id}"}]
        ]
        await send_message_with_buttons(chat_id, result_text, buttons)
    else:
        await send_message(chat_id, "❌ Ошибка генерации PDF")


async def handle_kp_restyle(chat_id: int, property_id: int):
    """Перегенерация с другим стилем — используем сохранённый запрос"""
    
    state, state_data = get_user_state(chat_id)
    query = state_data.get("query", "")
    
    # Сохраняем для выбора стиля
    update_user_state(chat_id, "kp_style", {
        "property_id": property_id,
        "query": query
    })
    
    text = "🎨 <b>Выбери другой стиль:</b>"
    
    buttons = [
        [{"text": "🖤 Премиум", "callback_data": "kp_style_premium"}],
        [{"text": "💼 Деловой", "callback_data": "kp_style_business"}],
        [{"text": "🔷 Корпоративный", "callback_data": "kp_style_corporate"}],
        [{"text": "🎨 Современный", "callback_data": "kp_style_modern"}],
        [{"text": "⬜ Минимал", "callback_data": "kp_style_minimal"}],
        [{"text": "🧡 Тёплый", "callback_data": "kp_style_warm"}],
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_summary_generate(chat_id: int, property_id: int):
    """Генерация выжимки через Content Composer"""
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    await send_message(chat_id, "⏳ Анализирую и готовлю выжимку...")
    
    files = get_property_files(property_id)
    extracted_text = "\n\n".join([
        f"=== {f.file_name} ===\n{f.extracted_text}"
        for f in files 
        if f.extracted_text and len(f.extracted_text) > 50
    ])
    
    property_data = property_to_dict(prop)
    
    content = await compose_summary_content(
        property_data=property_data,
        extracted_text=extracted_text
    )
    
    if not content:
        await send_message(chat_id, "⚠️ Не удалось создать выжимку")
        return
    
    pdf_path = await render_summary_from_content(
        content=content,
        property_name=prop.name
    )
    
    if pdf_path:
        await send_document(chat_id, pdf_path, f"📋 {prop.name} — Выжимка")
        
        conclusion = content.get("conclusion", "")
        result_text = "✅ <b>Выжимка готова!</b>"
        if conclusion:
            result_text += f"\n\n💡 <i>{conclusion}</i>"
        
        buttons = [[{"text": "🔙 К ЖК", "callback_data": f"open_property_{property_id}"}]]
        await send_message_with_buttons(chat_id, result_text, buttons)
    else:
        await send_message(chat_id, "❌ Ошибка генерации")


# Legacy
async def handle_kp_menu(chat_id: int):
    from bot.handlers.start import handle_my_properties
    await handle_my_properties(chat_id)

async def handle_kp_select_property(chat_id: int, property_id: int):
    await handle_kp_for_property(chat_id, property_id)
