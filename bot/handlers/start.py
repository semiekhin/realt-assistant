"""
Обработчик /start и главное меню
"""
from typing import Dict, Any

from services.telegram import send_message, send_message_with_buttons
from db.database import get_or_create_user, get_user_properties, clear_user_state


async def handle_start(chat_id: int, user_info: Dict[str, Any]):
    user = get_or_create_user(
        telegram_id=chat_id,
        username=user_info.get("username", ""),
        first_name=user_info.get("first_name", ""),
        last_name=user_info.get("last_name", "")
    )
    clear_user_state(chat_id)
    properties = get_user_properties(chat_id)
    first_name = user_info.get("first_name", "")
    greeting = f"Привет, {first_name}! 👋\n\n" if first_name else "Привет! 👋\n\n"
    if properties:
        text = greeting + f"У тебя {len(properties)} ЖК в базе."
    else:
        text = greeting + "Я помогу тебе работать с базой ЖК.\n\nДобавь первый объект — загрузи прайс, презентацию или фото."
    buttons = [
        [{"text": "🏢 Мои ЖК", "callback_data": "my_properties"}],
        [{"text": "➕ Добавить ЖК", "callback_data": "add_property"}],
        [{"text": "🧮 Калькуляторы", "callback_data": "calc_menu"}],
    ]
    if properties:
        buttons.append([{"text": "🔍 Поиск по всем ЖК", "callback_data": "search"}])
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_help(chat_id: int):
    text = """📖 <b>Как пользоваться</b>

<b>1. Добавить ЖК:</b>
Нажми "➕ Добавить ЖК" → введи название → загрузи файлы → готово

<b>2. Работа с ЖК:</b>
Зайди в "🏢 Мои ЖК" → выбери объект → работай с документами

<b>Внутри ЖК можно:</b>
- Скачать любой документ
- Спросить "что есть до 10 млн?"
- Попросить "сделай КП на двушку"
- Запросить "скинь презентацию"

<b>3. Калькуляторы:</b>
- 📅 Рассрочка — расчёт ежемесячного платежа
- 🏦 Ипотека — сравнение программ
- 💹 ROI — доходность от аренды

<b>4. Поиск по всем ЖК:</b>
Нажми "🔍 Поиск" и задай вопрос по всей базе

<b>Команды:</b>
/start — главное меню
/calc — калькуляторы
/cancel — отменить действие"""
    buttons = [[{"text": "🔙 Назад", "callback_data": "menu"}]]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_menu(chat_id: int):
    properties = get_user_properties(chat_id)
    if properties:
        text = f"📋 <b>Главное меню</b>\n\nЖК в базе: {len(properties)}"
    else:
        text = "📋 <b>Главное меню</b>\n\nБаза пуста — добавь первый ЖК"
    buttons = [
        [{"text": "🏢 Мои ЖК", "callback_data": "my_properties"}],
        [{"text": "➕ Добавить ЖК", "callback_data": "add_property"}],
        [{"text": "🧮 Калькуляторы", "callback_data": "calc_menu"}],
    ]
    if properties:
        buttons.append([{"text": "🔍 Поиск по всем ЖК", "callback_data": "search"}])
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_my_properties(chat_id: int):
    properties = get_user_properties(chat_id)
    if not properties:
        text = "📂 <b>Мои ЖК</b>\n\nПока пусто. Добавь первый объект!"
        buttons = [
            [{"text": "➕ Добавить ЖК", "callback_data": "add_property"}],
            [{"text": "🔙 Назад", "callback_data": "menu"}]
        ]
    else:
        text = f"📂 <b>Мои ЖК</b> ({len(properties)})\n\nВыбери объект:"
        buttons = []
        for prop in properties[:10]:
            buttons.append([{"text": f"📁 {prop.name}", "callback_data": f"open_property_{prop.id}"}])
        buttons.append([{"text": "➕ Добавить ЖК", "callback_data": "add_property"}])
        buttons.append([{"text": "🔙 Назад", "callback_data": "menu"}])
    await send_message_with_buttons(chat_id, text, buttons)
