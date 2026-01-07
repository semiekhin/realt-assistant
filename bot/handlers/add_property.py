"""
Обработчик добавления нового ЖК
"""
from typing import Dict, Any, Optional
import json

from services.telegram import (
    send_message, 
    send_message_with_buttons,
    download_file,
    get_file_type
)
from services.parser import extract_text, get_file_info
from services.llm import extract_property_data
from db.database import (
    get_user_state,
    update_user_state,
    clear_user_state,
    create_property,
    update_property,
    get_property,
    save_property_file,
    update_file_extracted_text,
    get_property_files,
    attach_files_to_property,
    get_pending_files
)
from bot.states import States


async def handle_add_property_start(chat_id: int):
    """Начало добавления ЖК — запрос названия"""
    
    update_user_state(chat_id, States.ADD_PROPERTY_NAME, {})
    
    text = """➕ <b>Добавляем новый ЖК</b>

Как называется жилой комплекс?

<i>Например: ЖК Солнечный, ЖК Парковый Квартал</i>"""
    
    buttons = [
        [{"text": "❌ Отмена", "callback_data": "cancel"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_name(chat_id: int, name: str):
    """Получили название ЖК — переходим к файлам"""
    
    name = name.strip()
    
    if len(name) < 2:
        await send_message(chat_id, "⚠️ Название слишком короткое. Попробуй ещё раз.")
        return
    
    # Сохраняем название в state_data
    update_user_state(chat_id, States.ADD_PROPERTY_FILES, {
        "name": name,
        "files_count": 0
    })
    
    text = f"""📁 <b>Отлично! ЖК "{name}"</b>

Теперь отправь материалы по этому ЖК:
• 📄 Прайс-лист (PDF, Excel)
• 📊 Презентация
• 🖼 Фото планировок
• 📋 Любые документы

Отправляй файлы по одному или несколько сразу.
Когда закончишь — напиши <b>готово</b>"""
    
    buttons = [
        [{"text": "✅ Готово", "callback_data": "files_done"}],
        [{"text": "❌ Отмена", "callback_data": "cancel"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_file_upload(chat_id: int, message: Dict[str, Any]):
    """Обработка загруженного файла"""
    
    state, data = get_user_state(chat_id)
    
    if state != States.ADD_PROPERTY_FILES:
        await send_message(chat_id, "❓ Сначала начни добавление ЖК командой /add")
        return
    
    # Определяем тип файла
    file_id, file_name, file_type = get_file_type(message)
    
    if not file_id:
        await send_message(chat_id, "⚠️ Не удалось определить тип файла")
        return
    
    # Скачиваем файл
    file_path = await download_file(file_id, file_name)
    
    if not file_path:
        await send_message(chat_id, "⚠️ Не удалось скачать файл")
        return
    
    # Получаем информацию о файле
    info = get_file_info(file_path)
    
    # Сохраняем в БД (пока без привязки к property)
    db_file_id = save_property_file(
        user_id=chat_id,
        property_id=None,  # Привяжем позже
        file_id=file_id,
        file_name=file_name,
        file_type=file_type,
        file_path=file_path
    )
    
    # Обновляем счётчик
    data["files_count"] = data.get("files_count", 0) + 1
    update_user_state(chat_id, States.ADD_PROPERTY_FILES, data)
    
    # Определяем эмодзи
    emoji = "📄"
    if file_type == "photo":
        emoji = "🖼"
    elif info["extension"] in (".xlsx", ".xls", ".csv"):
        emoji = "📊"
    
    await send_message(
        chat_id, 
        f"{emoji} Принял: <b>{file_name}</b> ({info['size_kb']} KB)\n\n"
        f"Файлов загружено: {data['files_count']}\n"
        f"Отправь ещё или нажми <b>Готово</b>"
    )


async def handle_files_done(chat_id: int):
    """Пользователь закончил загрузку файлов"""
    
    state, data = get_user_state(chat_id)
    
    if state != States.ADD_PROPERTY_FILES:
        await send_message(chat_id, "❓ Нет активного добавления ЖК")
        return
    
    property_name = data.get("name", "")
    files_count = data.get("files_count", 0)
    
    if files_count == 0:
        await send_message(
            chat_id,
            "⚠️ Ты не загрузил ни одного файла.\n"
            "Отправь хотя бы один документ или фото."
        )
        return
    
    await send_message(chat_id, "⏳ Анализирую материалы, это может занять минуту...")
    
    # Получаем все pending файлы
    pending_files = get_pending_files(chat_id)
    
    # Извлекаем текст из каждого файла
    all_text_parts = []
    
    for pf in pending_files:
        try:
            text = await extract_text(pf.file_path)
            
            # Сохраняем извлечённый текст
            update_file_extracted_text(pf.id, text)
            
            if text and not text.startswith("["):
                all_text_parts.append(f"=== Файл: {pf.file_name} ===\n{text}")
        except Exception as e:
            print(f"[ADD] Error extracting {pf.file_name}: {e}")
    
    if not all_text_parts:
        await send_message(
            chat_id,
            "⚠️ Не удалось извлечь текст из файлов.\n"
            "Попробуй загрузить другие материалы."
        )
        return
    
    # Объединяем весь текст
    combined_text = "\n\n".join(all_text_parts)
    
    # Отправляем в LLM для анализа
    extracted_data = await extract_property_data(combined_text, property_name)
    
    if not extracted_data:
        await send_message(
            chat_id,
            "⚠️ Не удалось проанализировать материалы.\n"
            "Попробуй загрузить более детальные документы."
        )
        return
    
    # Создаём объект в БД
    property_id = create_property(chat_id, property_name)
    
    # Привязываем файлы
    attach_files_to_property(chat_id, property_id)
    
    # Обновляем данные объекта
    update_property(
        property_id,
        name=extracted_data.get("name") or property_name,
        address=extracted_data.get("address", ""),
        developer=extracted_data.get("developer", ""),
        completion_date=extracted_data.get("completion_date", ""),
        price_min=extracted_data.get("price_min"),
        price_max=extracted_data.get("price_max"),
        price_per_sqm_min=extracted_data.get("price_per_sqm_min"),
        price_per_sqm_max=extracted_data.get("price_per_sqm_max"),
        apartment_types=extracted_data.get("apartment_types", ""),
        area_min=extracted_data.get("area_min"),
        area_max=extracted_data.get("area_max"),
        payment_options=extracted_data.get("payment_options", ""),
        installment_terms=extracted_data.get("installment_terms", ""),
        mortgage_info=extracted_data.get("mortgage_info", ""),
        commission=extracted_data.get("commission", ""),
        description=extracted_data.get("description", ""),
        features=extracted_data.get("features", ""),
        raw_data=json.dumps(extracted_data, ensure_ascii=False)
    )
    
    # Получаем обновлённый объект
    prop = get_property(property_id)
    
    # Сохраняем ID в state для возможных корректировок
    update_user_state(chat_id, States.ADD_PROPERTY_CONFIRM, {
        "property_id": property_id
    })
    
    # Формируем сводку
    text = f"✅ <b>ЖК добавлен!</b>\n\n{prop.to_summary()}\n\n"
    text += "Всё верно? Или скажи что исправить."
    
    buttons = [
        [{"text": "✅ Всё верно", "callback_data": "confirm_property"}],
        [{"text": "✏️ Редактировать", "callback_data": f"edit_property_{property_id}"}],
        [{"text": "🗑 Удалить", "callback_data": f"delete_property_{property_id}"}],
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_confirm_property(chat_id: int):
    """Подтверждение добавления ЖК"""
    
    clear_user_state(chat_id)
    
    text = "🎉 Отлично! ЖК сохранён в базе.\n\nЧто делаем дальше?"
    
    buttons = [
        [{"text": "➕ Добавить ещё ЖК", "callback_data": "add_property"}],
        [{"text": "🏢 Мои ЖК", "callback_data": "my_properties"}],
        [{"text": "🔙 В меню", "callback_data": "menu"}],
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_correction(chat_id: int, text: str):
    """Обработка корректировки данных ЖК"""
    
    state, data = get_user_state(chat_id)
    
    if state != States.ADD_PROPERTY_CONFIRM:
        return False
    
    property_id = data.get("property_id")
    if not property_id:
        return False
    
    # Получаем объект
    prop = get_property(property_id)
    if not prop:
        return False
    
    # Отправляем запрос в LLM для понимания корректировки
    from services.llm import quick_chat
    
    context = f"""Пользователь добавил ЖК с данными:
{prop.to_summary()}

Пользователь хочет внести корректировку: "{text}"

Определи, какое поле нужно изменить и на какое значение.
Ответь в формате: ПОЛЕ: новое_значение
Например: completion_date: Q3 2025

Доступные поля: name, address, developer, completion_date, price_min, price_max, 
apartment_types, installment_terms, commission, description"""
    
    response = await quick_chat(text, context)
    
    # Пытаемся распарсить ответ
    try:
        if ":" in response:
            parts = response.split(":", 1)
            field = parts[0].strip().lower()
            value = parts[1].strip()
            
            # Маппинг полей
            field_map = {
                "сдача": "completion_date",
                "срок": "completion_date",
                "completion_date": "completion_date",
                "адрес": "address",
                "address": "address",
                "застройщик": "developer",
                "developer": "developer",
                "название": "name",
                "name": "name",
                "рассрочка": "installment_terms",
                "installment_terms": "installment_terms",
                "комиссия": "commission",
                "commission": "commission",
            }
            
            db_field = field_map.get(field)
            
            if db_field:
                update_property(property_id, **{db_field: value})
                
                # Получаем обновлённый объект
                prop = get_property(property_id)
                
                await send_message(
                    chat_id,
                    f"✅ Исправлено!\n\n{prop.to_summary()}\n\n"
                    "Ещё что-то изменить?"
                )
                return True
    except Exception as e:
        print(f"[ADD] Correction parse error: {e}")
    
    await send_message(
        chat_id,
        "🤔 Не совсем понял. Попробуй сказать иначе.\n"
        "Например: «сдача в 3 квартале» или «комиссия 2%»"
    )
    return True


async def handle_cancel(chat_id: int):
    """Отмена текущего действия"""
    
    clear_user_state(chat_id)
    
    text = "❌ Действие отменено"
    
    buttons = [
        [{"text": "🔙 В меню", "callback_data": "menu"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)
