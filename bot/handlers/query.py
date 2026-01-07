"""
Обработчик просмотра ЖК и вопросов по базе
"""
from typing import Optional

from services.telegram import send_message, send_message_with_buttons, send_document
from services.llm import answer_query
from services.rag import search as rag_search
from db.database import (
    get_user_properties,
    get_property,
    get_property_files,
    get_file_by_id,
    delete_property,
    clear_user_state,
    update_user_state
)


async def handle_open_property(chat_id: int, property_id: int):
    """Открыть ЖК — рабочее пространство"""
    
    prop = get_property(property_id)
    
    if not prop or prop.user_id != chat_id:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    # Сохраняем контекст — пользователь работает с этим ЖК
    update_user_state(chat_id, "working_property", {"property_id": property_id})
    
    # Карточка ЖК
    text = f"📁 <b>{prop.name}</b>\n\n"
    
    if prop.address:
        text += f"📍 {prop.address}\n"
    if prop.developer:
        text += f"🏗 {prop.developer}\n"
    if prop.completion_date:
        text += f"📅 Сдача: {prop.completion_date}\n"
    
    if prop.price_min and prop.price_max:
        text += f"💰 {prop.price_min/1_000_000:.1f} – {prop.price_max/1_000_000:.1f} млн ₽\n"
    elif prop.price_min:
        text += f"💰 от {prop.price_min/1_000_000:.1f} млн ₽\n"
    
    if prop.apartment_types:
        text += f"🏠 {prop.apartment_types}\n"
    
    # Список документов
    files = get_property_files(property_id)
    
    if files:
        text += f"\n📎 <b>Документы ({len(files)}):</b>\n"
    
    text += "\n💬 <b>Напиши что сделать:</b>\n"
    text += "<i>• «что есть до 15 млн»\n"
    text += "• «сделай КП на студию»\n"
    text += "• «скинь презентацию»</i>"
    
    # Кнопки
    buttons = []
    
    # Документы (первые 6)
    for f in files[:6]:
        short_name = f.file_name[:28] + "…" if len(f.file_name) > 28 else f.file_name
        buttons.append([{
            "text": f"📄 {short_name}",
            "callback_data": f"download_{f.id}"
        }])
    
    if len(files) > 6:
        buttons.append([{
            "text": f"📂 Все документы ({len(files)})",
            "callback_data": f"all_files_{property_id}"
        }])
    
    # Действия
    buttons.append([
        {"text": "📄 КП", "callback_data": f"kp_for_{property_id}"},
        {"text": "🧮 Расчёт", "callback_data": f"calc_for_{property_id}"},
        {"text": "📋 Выжимка", "callback_data": f"summary_{property_id}"}
    ])
    
    buttons.append([
        {"text": "✏️ Изменить", "callback_data": f"edit_{property_id}"},
        {"text": "🗑", "callback_data": f"delete_{property_id}"}
    ])
    
    buttons.append([{"text": "🔙 К списку ЖК", "callback_data": "my_properties"}])
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_download_file(chat_id: int, file_id: int):
    """Скачать документ"""
    
    file_info = get_file_by_id(file_id)
    
    if not file_info:
        await send_message(chat_id, "❌ Файл не найден")
        return
    
    from pathlib import Path
    file_path = Path(file_info.file_path)
    
    if not file_path.exists():
        await send_message(chat_id, "❌ Файл не найден на сервере")
        return
    
    await send_document(chat_id, str(file_path), f"📎 {file_info.file_name}")


async def handle_all_files(chat_id: int, property_id: int):
    """Показать все документы ЖК"""
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    files = get_property_files(property_id)
    
    text = f"📂 <b>Документы: {prop.name}</b>\n\n"
    
    buttons = []
    for f in files:
        short_name = f.file_name[:28] + "…" if len(f.file_name) > 28 else f.file_name
        buttons.append([{
            "text": f"📄 {short_name}",
            "callback_data": f"download_{f.id}"
        }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": f"open_property_{property_id}"}])
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_summary(chat_id: int, property_id: int):
    """Генерация выжимки — перенаправляем на новый генератор"""
    from bot.handlers.kp import handle_summary_generate
    await handle_summary_generate(chat_id, property_id)


async def handle_delete_property(chat_id: int, property_id: int):
    """Удаление ЖК"""
    
    prop = get_property(property_id)
    
    if not prop or prop.user_id != chat_id:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    text = f"🗑 Удалить <b>{prop.name}</b>?\n\nВсе документы тоже удалятся."
    
    buttons = [
        [
            {"text": "✅ Да", "callback_data": f"confirm_delete_{property_id}"},
            {"text": "❌ Нет", "callback_data": f"open_property_{property_id}"}
        ]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_confirm_delete(chat_id: int, property_id: int):
    """Подтверждение удаления"""
    
    prop = get_property(property_id)
    
    if not prop or prop.user_id != chat_id:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    name = prop.name
    delete_property(property_id)
    clear_user_state(chat_id)
    
    text = f"🗑 «{name}» удалён"
    buttons = [[{"text": "🔙 К списку ЖК", "callback_data": "my_properties"}]]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_query(chat_id: int, property_id: int, query: str):
    """Вопрос в контексте конкретного ЖК — через RAG"""
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    await send_message(chat_id, "🔍 Ищу...")
    
    # RAG поиск
    chunks = rag_search(chat_id, query, property_id=property_id, limit=10)
    
    # Формируем контекст
    context = prop.to_summary() + "\n\n"
    
    if chunks:
        context += "ДЕТАЛЬНЫЕ ДАННЫЕ (из документов):\n\n"
        for chunk in chunks:
            context += f"{chunk['text']}\n\n"
    else:
        # Fallback на старый метод если RAG пустой
        files = get_property_files(property_id)
        for f in files:
            if f.extracted_text and len(f.extracted_text) > 50:
                context += f"--- {f.file_name} ---\n{f.extracted_text[:3000]}\n\n"
    
    response = await answer_query(query, context)
    
    # Определяем нужны ли кнопки
    query_lower = query.lower()
    buttons = []
    
    if "кп" in query_lower or "предложение" in query_lower:
        buttons.append([{"text": "📄 Создать КП", "callback_data": f"kp_for_{property_id}"}])
    
    if "скач" in query_lower or "презент" in query_lower or "файл" in query_lower:
        for f in files[:3]:
            short_name = f.file_name[:25] + "…" if len(f.file_name) > 25 else f.file_name
            buttons.append([{"text": f"📥 {short_name}", "callback_data": f"download_{f.id}"}])
    
    buttons.append([{"text": "🔙 К ЖК", "callback_data": f"open_property_{property_id}"}])
    
    await send_message_with_buttons(chat_id, response, buttons)


async def handle_search_all(chat_id: int, query: str):
    """Поиск по всем ЖК — через RAG"""
    
    properties = get_user_properties(chat_id)
    
    if not properties:
        await send_message(chat_id, "🏢 База пуста. Сначала добавь ЖК.")
        return
    
    await send_message(chat_id, "🔍 Ищу по всей базе...")
    
    # RAG поиск по всем ЖК
    chunks = rag_search(chat_id, query, property_id=None, limit=15)
    
    # Формируем контекст
    context_parts = []
    for prop in properties:
        context_parts.append(prop.to_summary())
    
    context = "СПИСОК ЖК:\n" + "\n\n".join(context_parts)
    
    if chunks:
        context += "\n\nДЕТАЛЬНЫЕ ДАННЫЕ (из документов):\n\n"
        for chunk in chunks:
            meta = chunk.get('metadata', {})
            prop_name = meta.get('property_name', '')
            context += f"[{prop_name}] {chunk['text']}\n\n"
    
    response = await answer_query(query, context)
    
    await send_message(chat_id, response)


async def handle_search_start(chat_id: int):
    """Начало поиска по всем ЖК"""
    
    properties = get_user_properties(chat_id)
    
    if not properties:
        text = "🏢 База пуста."
        buttons = [
            [{"text": "➕ Добавить ЖК", "callback_data": "add_property"}],
            [{"text": "🔙 Назад", "callback_data": "menu"}]
        ]
    else:
        text = f"🔍 <b>Поиск по всем ЖК</b>\n\nВ базе: {len(properties)} объектов\n\n"
        text += "Напиши вопрос, например:\n"
        text += "• <i>что есть до 10 млн?</i>\n"
        text += "• <i>где самая низкая цена за метр?</i>\n"
        text += "• <i>какие ЖК сдаются в 2025?</i>"
        
        buttons = [[{"text": "🔙 Назад", "callback_data": "menu"}]]
    
    await send_message_with_buttons(chat_id, text, buttons)


# Legacy функции для совместимости
async def handle_view_property(chat_id: int, property_id: int):
    await handle_open_property(chat_id, property_id)

async def handle_query(chat_id: int, query: str):
    await handle_search_all(chat_id, query)

async def handle_doc_to_pdf(chat_id: int, property_id: int):
    await handle_property_summary(chat_id, property_id)


async def handle_summary_pdf(chat_id: int, property_id: int):
    """Сохранить выжимку в PDF"""
    from services.kp_generator import generate_property_info_pdf
    
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    await send_message(chat_id, "⏳ Генерирую PDF...")
    
    # Собираем информацию
    files = get_property_files(property_id)
    extracted_info = "\n\n".join([
        f.extracted_text for f in files 
        if f.extracted_text and len(f.extracted_text) > 50
    ])
    
    pdf_path = await generate_property_info_pdf(prop, extracted_info)
    
    if pdf_path:
        await send_document(chat_id, pdf_path, f"📄 {prop.name} — Информация")
        
        buttons = [[{"text": "🔙 К ЖК", "callback_data": f"open_property_{property_id}"}]]
        await send_message_with_buttons(chat_id, "✅ PDF готов!", buttons)
    else:
        await send_message(chat_id, "❌ Ошибка генерации PDF")
