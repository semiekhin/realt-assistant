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
from services.parser_v2 import extract_all as extract_text, get_file_info
from services.llm import extract_property_data
from services.rag import add_document
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
    update_user_state(chat_id, States.ADD_PROPERTY_NAME, {})
    text = """➕ <b>Добавляем новый ЖК</b>

Как называется жилой комплекс?

<i>Например: ЖК Солнечный, ЖК Парковый Квартал</i>"""
    buttons = [[{"text": "❌ Отмена", "callback_data": "cancel"}]]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_name(chat_id: int, name: str):
    name = name.strip()
    if len(name) < 2:
        await send_message(chat_id, "⚠️ Название слишком короткое. Попробуй ещё раз.")
        return
    update_user_state(chat_id, States.ADD_PROPERTY_FILES, {"name": name, "files_count": 0})
    text = f"""📁 <b>Отлично! ЖК "{name}"</b>

Теперь отправь материалы по этому ЖК:
- 📄 Прайс-лист (PDF, Excel)
- 📊 Презентация
- 🖼 Фото планировок
- 📋 Любые документы

Отправляй файлы по одному или несколько сразу.
Когда закончишь — напиши <b>готово</b>"""
    buttons = [
        [{"text": "✅ Готово", "callback_data": "files_done"}],
        [{"text": "❌ Отмена", "callback_data": "cancel"}]
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_file_upload(chat_id: int, message: Dict[str, Any]):
    state, data = get_user_state(chat_id)
    if state != States.ADD_PROPERTY_FILES:
        await send_message(chat_id, "❓ Сначала начни добавление ЖК командой /add")
        return
    file_id, file_name, file_type = get_file_type(message)
    if not file_id:
        await send_message(chat_id, "⚠️ Не удалось определить тип файла")
        return
    file_path = await download_file(file_id, file_name)
    if not file_path:
        await send_message(chat_id, "⚠️ Не удалось скачать файл")
        return
    info = get_file_info(file_path)
    db_file_id = save_property_file(
        user_id=chat_id,
        property_id=None,
        file_id=file_id,
        file_name=file_name,
        file_type=file_type,
        file_path=file_path
    )
    data["files_count"] = data.get("files_count", 0) + 1
    update_user_state(chat_id, States.ADD_PROPERTY_FILES, data)
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
    state, data = get_user_state(chat_id)
    if state != States.ADD_PROPERTY_FILES:
        await send_message(chat_id, "❓ Нет активного добавления ЖК")
        return
    property_name = data.get("name", "")
    files_count = data.get("files_count", 0)
    if files_count == 0:
        await send_message(chat_id, "⚠️ Ты не загрузил ни одного файла.\nОтправь хотя бы один документ или фото.")
        return
    await send_message(chat_id, "⏳ Анализирую материалы, это может занять минуту...")
    pending_files = get_pending_files(chat_id)
    all_text_parts = []
    for pf in pending_files:
        try:
            text = await extract_text(pf.file_path)
            update_file_extracted_text(pf.id, text)
            if text and not text.startswith("["):
                all_text_parts.append(f"=== Файл: {pf.file_name} ===\n{text}")
        except Exception as e:
            print(f"[ADD] Error extracting {pf.file_name}: {e}")
    if not all_text_parts:
        await send_message(chat_id, "⚠️ Не удалось извлечь текст из файлов.\nПопробуй загрузить другие материалы.")
        return
    combined_text = "\n\n".join(all_text_parts)
    extracted_data = await extract_property_data(combined_text, property_name)
    if not extracted_data:
        await send_message(chat_id, "⚠️ Не удалось проанализировать материалы.\nПопробуй загрузить более детальные документы.")
        return
    property_id = create_property(chat_id, property_name)
    attach_files_to_property(chat_id, property_id)
    
    # Индексируем в RAG
    for pf in pending_files:
        if pf.extracted_text and not pf.extracted_text.startswith("["):
            add_document(chat_id, property_id, property_name, pf.file_name, pf.extracted_text)
    
    # Сохраняем все данные включая условия рассрочки
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
        # Новые структурированные поля условий рассрочки
        installment_min_pv=extracted_data.get("installment_min_pv"),
        installment_max_months=extracted_data.get("installment_max_months"),
        installment_markup=extracted_data.get("installment_markup"),
        commission=extracted_data.get("commission", ""),
        distance_to_sea=extracted_data.get("distance_to_sea", ""),
        territory_area=extracted_data.get("territory_area", ""),
        hotel_operator=extracted_data.get("hotel_operator", ""),
        description=extracted_data.get("description", ""),
        features=extracted_data.get("features", ""),
        raw_data=json.dumps(extracted_data, ensure_ascii=False)
    )
    
    prop = get_property(property_id)
    update_user_state(chat_id, States.ADD_PROPERTY_CONFIRM, {"property_id": property_id})
    
    # Формируем расширенную сводку с условиями рассрочки
    text = f"✅ <b>ЖК добавлен!</b>\n\n{prop.to_full_info()}"
    
    # Показываем условия рассрочки для подтверждения
    if prop.installment_min_pv is not None or prop.installment_max_months is not None:
        text += "\n\n📋 <b>Условия рассрочки (для калькулятора):</b>"
        if prop.installment_min_pv is not None:
            text += f"\n• Мин. ПВ: {prop.installment_min_pv:.0f}%"
        if prop.installment_max_months is not None:
            text += f"\n• Макс. срок: {prop.installment_max_months} мес"
        if prop.installment_markup is not None:
            if prop.installment_markup == 0:
                text += "\n• Удорожание: без удорожания"
            else:
                text += f"\n• Удорожание: {prop.installment_markup:.0f}%"
    
    text += "\n\n✏️ Всё верно? Или скажи что исправить."
    
    buttons = [
        [{"text": "✅ Всё верно", "callback_data": "confirm_property"}],
        [{"text": "✏️ Редактировать", "callback_data": f"edit_property_{property_id}"}],
        [{"text": "🗑 Удалить", "callback_data": f"delete_property_{property_id}"}],
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_confirm_property(chat_id: int):
    clear_user_state(chat_id)
    text = "🎉 Отлично! ЖК сохранён в базе.\n\nЧто делаем дальше?"
    buttons = [
        [{"text": "➕ Добавить ещё ЖК", "callback_data": "add_property"}],
        [{"text": "🏢 Мои ЖК", "callback_data": "my_properties"}],
        [{"text": "🔙 В меню", "callback_data": "menu"}],
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_property_correction(chat_id: int, text: str):
    state, data = get_user_state(chat_id)
    if state != States.ADD_PROPERTY_CONFIRM:
        return False
    property_id = data.get("property_id")
    if not property_id:
        return False
    prop = get_property(property_id)
    if not prop:
        return False
    from services.llm import quick_chat
    context = f"""Пользователь добавил ЖК с данными:
{prop.to_summary()}

Условия рассрочки:
- Мин. ПВ: {prop.installment_min_pv}%
- Макс. срок: {prop.installment_max_months} мес
- Удорожание: {prop.installment_markup}%

Пользователь хочет внести корректировку: "{text}"

Определи, какое поле нужно изменить и на какое значение.
Ответь в формате: ПОЛЕ: новое_значение
Например: completion_date: Q3 2025

Доступные поля: name, address, developer, completion_date, price_min, price_max, 
apartment_types, installment_terms, commission, description,
installment_min_pv (число %), installment_max_months (число месяцев), installment_markup (число %)"""
    
    response = await quick_chat(text, context)
    try:
        if ":" in response:
            parts = response.split(":", 1)
            field = parts[0].strip().lower()
            value = parts[1].strip()
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
                "пв": "installment_min_pv",
                "первый взнос": "installment_min_pv",
                "installment_min_pv": "installment_min_pv",
                "срок рассрочки": "installment_max_months",
                "месяцев": "installment_max_months",
                "installment_max_months": "installment_max_months",
                "удорожание": "installment_markup",
                "installment_markup": "installment_markup",
            }
            db_field = field_map.get(field)
            if db_field:
                # Конвертируем числовые поля
                if db_field in ("installment_min_pv", "installment_markup"):
                    value = float(value.replace("%", "").strip())
                elif db_field == "installment_max_months":
                    value = int(value.replace("мес", "").strip())
                
                update_property(property_id, **{db_field: value})
                prop = get_property(property_id)
                await send_message(chat_id, f"✅ Исправлено!\n\n{prop.to_summary()}\n\nЕщё что-то изменить?")
                return True
    except Exception as e:
        print(f"[ADD] Correction parse error: {e}")
    await send_message(chat_id, "🤔 Не совсем понял. Попробуй сказать иначе.\nНапример: «ПВ 20%» или «срок рассрочки 24 месяца»")
    return True


async def handle_cancel(chat_id: int):
    clear_user_state(chat_id)
    text = "❌ Действие отменено"
    buttons = [[{"text": "🔙 В меню", "callback_data": "menu"}]]
    await send_message_with_buttons(chat_id, text, buttons)
