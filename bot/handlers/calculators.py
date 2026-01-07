"""
Обработчики калькуляторов
"""
from typing import Dict, Any

from services.telegram import send_message, send_message_with_buttons
from services.calculators import (
    calc_installment,
    calc_mortgage,
    calc_mortgage_comparison,
    calc_roi,
    format_installment_result,
    format_mortgage_result,
    format_roi_result,
    format_money,
    MORTGAGE_PROGRAMS
)
from db.database import update_user_state, get_user_state, clear_user_state, get_property


async def handle_calc_menu(chat_id: int):
    clear_user_state(chat_id)
    text = "🧮 <b>Калькуляторы</b>\n\nВыбери тип расчёта:"
    buttons = [
        [{"text": "📅 Рассрочка", "callback_data": "calc_installment"}],
        [{"text": "🏦 Ипотека", "callback_data": "calc_mortgage"}],
        [{"text": "💹 Доходность (ROI)", "callback_data": "calc_roi"}],
        [{"text": "🔙 Меню", "callback_data": "menu"}]
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_installment_start(chat_id: int):
    update_user_state(chat_id, "calc_installment_price", {})
    text = "📅 <b>Расчёт рассрочки</b>\n\nВведи стоимость квартиры в рублях:\n\n<i>Например: 15000000 или 15 млн</i>"
    buttons = [[{"text": "❌ Отмена", "callback_data": "calc_menu"}]]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_installment_price(chat_id: int, text: str):
    price = parse_price(text)
    if not price or price < 100000:
        await send_message(chat_id, "❌ Не понял сумму. Введи число, например: 15000000")
        return
    update_user_state(chat_id, "calc_installment_pv", {"price": price})
    msg = f"💰 Стоимость: {format_money(price)}\n\nВведи первоначальный взнос в %:\n\n<i>Например: 30</i>"
    buttons = [
        [{"text": "10%", "callback_data": "inst_pv_10"}, {"text": "20%", "callback_data": "inst_pv_20"}, {"text": "30%", "callback_data": "inst_pv_30"}],
        [{"text": "40%", "callback_data": "inst_pv_40"}, {"text": "50%", "callback_data": "inst_pv_50"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_installment_pv(chat_id: int, pv_pct: float):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    if not price:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    update_user_state(chat_id, "calc_installment_months", {"price": price, "pv_pct": pv_pct})
    pv_amount = int(price * pv_pct / 100)
    msg = f"💰 ПВ ({pv_pct}%): {format_money(pv_amount)}\n\nВведи срок рассрочки в месяцах:\n\n<i>Например: 18</i>"
    buttons = [
        [{"text": "6 мес", "callback_data": "inst_months_6"}, {"text": "12 мес", "callback_data": "inst_months_12"}, {"text": "18 мес", "callback_data": "inst_months_18"}],
        [{"text": "24 мес", "callback_data": "inst_months_24"}, {"text": "36 мес", "callback_data": "inst_months_36"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_installment_result(chat_id: int, months: int):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    pv_pct = data.get("pv_pct", 0)
    if not price or not pv_pct:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    result = calc_installment(price, pv_pct, months)
    text = format_installment_result(result)
    clear_user_state(chat_id)
    buttons = [
        [{"text": "🔄 Другой расчёт", "callback_data": "calc_installment"}],
        [{"text": "🧮 Калькуляторы", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_mortgage_start(chat_id: int):
    update_user_state(chat_id, "calc_mortgage_price", {})
    text = "🏦 <b>Расчёт ипотеки</b>\n\nВведи стоимость квартиры в рублях:\n\n<i>Например: 15000000 или 15 млн</i>"
    buttons = [[{"text": "❌ Отмена", "callback_data": "calc_menu"}]]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_mortgage_price(chat_id: int, text: str):
    price = parse_price(text)
    if not price or price < 100000:
        await send_message(chat_id, "❌ Не понял сумму. Введи число, например: 15000000")
        return
    update_user_state(chat_id, "calc_mortgage_pv", {"price": price})
    msg = f"💰 Стоимость: {format_money(price)}\n\nВведи первоначальный взнос в %:\n\n<i>Минимум 20% для большинства программ</i>"
    buttons = [
        [{"text": "20%", "callback_data": "mort_pv_20"}, {"text": "30%", "callback_data": "mort_pv_30"}, {"text": "50%", "callback_data": "mort_pv_50"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_mortgage_pv(chat_id: int, pv_pct: float):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    if not price:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    update_user_state(chat_id, "calc_mortgage_years", {"price": price, "pv_pct": pv_pct})
    msg = "Выбери срок ипотеки:"
    buttons = [
        [{"text": "10 лет", "callback_data": "mort_years_10"}, {"text": "15 лет", "callback_data": "mort_years_15"}],
        [{"text": "20 лет", "callback_data": "mort_years_20"}, {"text": "25 лет", "callback_data": "mort_years_25"}, {"text": "30 лет", "callback_data": "mort_years_30"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_mortgage_years(chat_id: int, years: int):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    pv_pct = data.get("pv_pct", 0)
    if not price:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    update_user_state(chat_id, "calc_mortgage_program", {"price": price, "pv_pct": pv_pct, "years": years})
    msg = "Выбери программу ипотеки:\n\n"
    for key, prog in MORTGAGE_PROGRAMS.items():
        msg += f"• <b>{prog['name']}</b> — {prog['rate']}%\n  <i>{prog['description']}</i>\n\n"
    buttons = [
        [{"text": f"📊 Стандартная ({MORTGAGE_PROGRAMS['standard']['rate']}%)", "callback_data": "mort_prog_standard"}],
        [{"text": f"👨‍👩‍👧 Семейная ({MORTGAGE_PROGRAMS['family']['rate']}%)", "callback_data": "mort_prog_family"}],
        [{"text": f"💻 IT-ипотека ({MORTGAGE_PROGRAMS['it']['rate']}%)", "callback_data": "mort_prog_it"}],
        [{"text": f"🌏 Дальневосточная ({MORTGAGE_PROGRAMS['far_east']['rate']}%)", "callback_data": "mort_prog_far_east"}],
        [{"text": "📋 Сравнить все", "callback_data": "mort_prog_compare"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_mortgage_result(chat_id: int, program: str):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    pv_pct = data.get("pv_pct", 0)
    years = data.get("years", 0)
    if not price or not pv_pct or not years:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    if program == "compare":
        results = calc_mortgage_comparison(price, pv_pct, years)
        text = f"📊 <b>Сравнение ипотечных программ</b>\n\n"
        text += f"🏠 Стоимость: {format_money(price)}\n"
        text += f"💰 ПВ ({pv_pct}%): {format_money(int(price * pv_pct / 100))}\n"
        text += f"📅 Срок: {years} лет\n\n"
        for r in results:
            text += f"<b>{r.program_name}</b> ({r.rate}%)\n"
            text += f"  Платёж: {format_money(r.monthly_payment)}/мес\n"
            text += f"  Переплата: {format_money(r.overpayment)}\n\n"
    else:
        result = calc_mortgage(price, pv_pct, years, program)
        text = format_mortgage_result(result)
    clear_user_state(chat_id)
    buttons = [
        [{"text": "🔄 Другой расчёт", "callback_data": "calc_mortgage"}],
        [{"text": "🧮 Калькуляторы", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_roi_start(chat_id: int):
    update_user_state(chat_id, "calc_roi_price", {})
    text = "💹 <b>Расчёт доходности</b>\n\nВведи стоимость квартиры в рублях:\n\n<i>Например: 15000000 или 15 млн</i>"
    buttons = [[{"text": "❌ Отмена", "callback_data": "calc_menu"}]]
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_roi_price(chat_id: int, text: str):
    price = parse_price(text)
    if not price or price < 100000:
        await send_message(chat_id, "❌ Не понял сумму. Введи число, например: 15000000")
        return
    update_user_state(chat_id, "calc_roi_rent", {"price": price})
    msg = f"💰 Стоимость: {format_money(price)}\n\nВведи ставку аренды в сутки:\n\n<i>Например: 3500</i>"
    buttons = [
        [{"text": "2000 ₽", "callback_data": "roi_rent_2000"}, {"text": "3000 ₽", "callback_data": "roi_rent_3000"}, {"text": "4000 ₽", "callback_data": "roi_rent_4000"}],
        [{"text": "5000 ₽", "callback_data": "roi_rent_5000"}, {"text": "7000 ₽", "callback_data": "roi_rent_7000"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_roi_rent(chat_id: int, rent: int):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    if not price:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    update_user_state(chat_id, "calc_roi_occupancy", {"price": price, "rent": rent})
    msg = f"🛏 Ставка: {format_money(rent)}/сутки\n\nВыбери ожидаемую загрузку:\n\n<i>Средняя загрузка посуточной аренды — 60-70%</i>"
    buttons = [
        [{"text": "50%", "callback_data": "roi_occ_50"}, {"text": "60%", "callback_data": "roi_occ_60"}, {"text": "70%", "callback_data": "roi_occ_70"}],
        [{"text": "80%", "callback_data": "roi_occ_80"}, {"text": "90%", "callback_data": "roi_occ_90"}],
        [{"text": "❌ Отмена", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, msg, buttons)


async def handle_calc_roi_result(chat_id: int, occupancy: float):
    state, data = get_user_state(chat_id)
    price = data.get("price", 0)
    rent = data.get("rent", 0)
    if not price or not rent:
        await send_message(chat_id, "❌ Сессия устарела. Начни заново.")
        return
    result = calc_roi(price, rent, occupancy)
    text = format_roi_result(result)
    deposit_rate = 20
    deposit_income = int(price * deposit_rate / 100)
    text += f"\n\n📊 <b>Для сравнения:</b>\nДепозит ({deposit_rate}%): {format_money(deposit_income)}/год"
    if result.net_income > deposit_income:
        diff = result.net_income - deposit_income
        text += f"\n✅ Аренда выгоднее на {format_money(diff)}/год"
    else:
        diff = deposit_income - result.net_income
        text += f"\n⚠️ Депозит выгоднее на {format_money(diff)}/год"
    clear_user_state(chat_id)
    buttons = [
        [{"text": "🔄 Другой расчёт", "callback_data": "calc_roi"}],
        [{"text": "🧮 Калькуляторы", "callback_data": "calc_menu"}]
    ]
    await send_message_with_buttons(chat_id, text, buttons)


def parse_price(text: str) -> int:
    text = text.lower().strip().replace(" ", "").replace(",", ".")
    multiplier = 1
    if "млн" in text:
        multiplier = 1_000_000
        text = text.replace("млн", "")
    elif "м" in text:
        multiplier = 1_000_000
        text = text.replace("м", "")
    elif "тыс" in text or "к" in text:
        multiplier = 1_000
        text = text.replace("тыс", "").replace("к", "")
    text = "".join(c for c in text if c.isdigit() or c == ".")
    try:
        return int(float(text) * multiplier)
    except:
        return 0


async def handle_calc_for_property(chat_id: int, property_id: int):
    """Калькулятор с привязкой к ЖК — подставляем данные"""
    prop = get_property(property_id)
    if not prop:
        await send_message(chat_id, "❌ ЖК не найден")
        return
    
    text = f"🧮 <b>Калькулятор: {prop.name}</b>\n\n"
    
    # Показываем данные ЖК
    if prop.price_min and prop.price_max:
        text += f"💰 Цены: {prop.price_min/1_000_000:.1f} – {prop.price_max/1_000_000:.1f} млн ₽\n"
    elif prop.price_min:
        text += f"💰 Цена от: {prop.price_min/1_000_000:.1f} млн ₽\n"
    
    if prop.installment_min_pv is not None:
        text += f"📅 Рассрочка: ПВ от {prop.installment_min_pv:.0f}%"
        if prop.installment_max_months:
            text += f", до {prop.installment_max_months} мес"
        if prop.installment_markup is not None and prop.installment_markup > 0:
            text += f", +{prop.installment_markup:.0f}%"
        text += "\n"
    
    text += "\nВыбери расчёт:"
    
    buttons = []
    
    # Если есть цена — предлагаем быстрый расчёт
    if prop.price_min:
        buttons.append([{"text": f"📅 Рассрочка ({prop.price_min/1_000_000:.1f} млн)", "callback_data": f"calc_inst_prop_{property_id}"}])
        buttons.append([{"text": f"🏦 Ипотека ({prop.price_min/1_000_000:.1f} млн)", "callback_data": f"calc_mort_prop_{property_id}"}])
        buttons.append([{"text": f"💹 ROI ({prop.price_min/1_000_000:.1f} млн)", "callback_data": f"calc_roi_prop_{property_id}"}])
    
    buttons.append([{"text": "🔢 Ввести свою сумму", "callback_data": "calc_menu"}])
    buttons.append([{"text": "🔙 К ЖК", "callback_data": f"open_property_{property_id}"}])
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_installment_for_property(chat_id: int, property_id: int):
    """Рассрочка с данными ЖК"""
    prop = get_property(property_id)
    if not prop or not prop.price_min:
        await send_message(chat_id, "❌ Нет данных о цене")
        return
    
    price = prop.price_min
    
    # Используем условия рассрочки из ЖК или дефолтные
    default_pv = prop.installment_min_pv if prop.installment_min_pv else 30
    
    update_user_state(chat_id, "calc_installment_pv", {"price": price, "property_id": property_id})
    
    text = f"📅 <b>Рассрочка: {prop.name}</b>\n\n"
    text += f"💰 Стоимость: {format_money(price)}\n\n"
    
    if prop.installment_min_pv is not None:
        text += f"ℹ️ Условия застройщика: ПВ от {prop.installment_min_pv:.0f}%"
        if prop.installment_max_months:
            text += f", до {prop.installment_max_months} мес"
        text += "\n\n"
    
    text += "Выбери первоначальный взнос:"
    
    # Кнопки ПВ — выделяем рекомендуемый
    pv_buttons = []
    for pv in [10, 20, 30, 40, 50]:
        label = f"{pv}%"
        if prop.installment_min_pv and pv == int(prop.installment_min_pv):
            label = f"✓ {pv}%"
        pv_buttons.append({"text": label, "callback_data": f"inst_pv_{pv}"})
    
    buttons = [
        pv_buttons[:3],
        pv_buttons[3:],
        [{"text": "🔙 Назад", "callback_data": f"calc_for_{property_id}"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_mortgage_for_property(chat_id: int, property_id: int):
    """Ипотека с данными ЖК"""
    prop = get_property(property_id)
    if not prop or not prop.price_min:
        await send_message(chat_id, "❌ Нет данных о цене")
        return
    
    price = prop.price_min
    update_user_state(chat_id, "calc_mortgage_pv", {"price": price, "property_id": property_id})
    
    text = f"🏦 <b>Ипотека: {prop.name}</b>\n\n"
    text += f"💰 Стоимость: {format_money(price)}\n\n"
    text += "Выбери первоначальный взнос:"
    
    buttons = [
        [{"text": "20%", "callback_data": "mort_pv_20"}, {"text": "30%", "callback_data": "mort_pv_30"}, {"text": "50%", "callback_data": "mort_pv_50"}],
        [{"text": "🔙 Назад", "callback_data": f"calc_for_{property_id}"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)


async def handle_calc_roi_for_property(chat_id: int, property_id: int):
    """ROI с данными ЖК"""
    prop = get_property(property_id)
    if not prop or not prop.price_min:
        await send_message(chat_id, "❌ Нет данных о цене")
        return
    
    price = prop.price_min
    update_user_state(chat_id, "calc_roi_rent", {"price": price, "property_id": property_id})
    
    text = f"💹 <b>Доходность: {prop.name}</b>\n\n"
    text += f"💰 Стоимость: {format_money(price)}\n\n"
    text += "Введи ставку аренды в сутки:"
    
    buttons = [
        [{"text": "2000 ₽", "callback_data": "roi_rent_2000"}, {"text": "3000 ₽", "callback_data": "roi_rent_3000"}, {"text": "4000 ₽", "callback_data": "roi_rent_4000"}],
        [{"text": "5000 ₽", "callback_data": "roi_rent_5000"}, {"text": "7000 ₽", "callback_data": "roi_rent_7000"}],
        [{"text": "🔙 Назад", "callback_data": f"calc_for_{property_id}"}]
    ]
    
    await send_message_with_buttons(chat_id, text, buttons)
