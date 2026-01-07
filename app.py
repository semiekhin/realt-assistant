"""
Realt Assistant — Персональный ассистент риэлтора
"""
from fastapi import FastAPI, Request
from typing import Dict, Any

from config import TELEGRAM_BOT_TOKEN
from db.database import init_db, get_user_state, clear_user_state
from bot.states import States, is_exit_command
from services.telegram import send_message, answer_callback, get_file_type

from bot.handlers.start import handle_start, handle_help, handle_menu, handle_my_properties
from db.database import save_message, get_chat_history
from services.llm import universal_respond
from services.rag import search as rag_search
from services.calculators import (
    calc_installment, calc_mortgage, calc_roi,
    format_installment_result, format_mortgage_result, format_roi_result
)

from bot.handlers.add_property import (
    handle_add_property_start, handle_property_name, handle_file_upload,
    handle_files_done, handle_confirm_property, handle_property_correction, handle_cancel
)
from bot.handlers.query import (
    handle_open_property, handle_download_file, handle_all_files, handle_property_summary,
    handle_delete_property, handle_confirm_delete, handle_property_query, handle_search_all, handle_search_start
)
from bot.handlers.kp import (
    handle_kp_for_property, handle_kp_query_received, handle_kp_style_selected, handle_kp_generate, handle_kp_restyle
)
from bot.handlers.calculators import (
    handle_calc_menu, handle_calc_installment_start, handle_calc_installment_price,
    handle_calc_installment_pv, handle_calc_installment_result, handle_calc_mortgage_start,
    handle_calc_mortgage_price, handle_calc_mortgage_pv, handle_calc_mortgage_years,
    handle_calc_mortgage_result, handle_calc_roi_start, handle_calc_roi_price,
    handle_calc_roi_rent, handle_calc_roi_result, parse_price,
    handle_calc_for_property, handle_calc_installment_for_property,
    handle_calc_mortgage_for_property, handle_calc_roi_for_property
)

app = FastAPI(title="Realt Assistant", version="0.5.0")


@app.on_event("startup")
async def startup():
    init_db()
    print("[APP] Started v0.5.0 — Calculators")


@app.get("/")
async def health():
    return {"ok": True, "service": "realt-assistant", "version": "0.3.0"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
    except:
        return {"ok": False}
    if "callback_query" in update:
        await process_callback(update["callback_query"])
    elif "message" in update:
        await process_message(update["message"])
    return {"ok": True}


async def process_callback(callback: Dict[str, Any]):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return
    if callback_id:
        await answer_callback(callback_id)

    # Навигация
    if data == "menu":
        await handle_menu(chat_id)
    elif data == "help":
        await handle_help(chat_id)
    elif data == "my_properties":
        await handle_my_properties(chat_id)
    elif data == "add_property":
        await handle_add_property_start(chat_id)
    elif data == "search":
        await handle_search_start(chat_id)
    elif data == "cancel":
        await handle_cancel(chat_id)

    # Калькуляторы
    elif data == "calc_menu":
        await handle_calc_menu(chat_id)
    elif data == "calc_installment":
        await handle_calc_installment_start(chat_id)
    elif data.startswith("inst_pv_"):
        pv = float(data.replace("inst_pv_", ""))
        await handle_calc_installment_pv(chat_id, pv)
    elif data.startswith("inst_months_"):
        months = int(data.replace("inst_months_", ""))
        await handle_calc_installment_result(chat_id, months)
    elif data == "calc_mortgage":
        await handle_calc_mortgage_start(chat_id)
    elif data.startswith("mort_pv_"):
        pv = float(data.replace("mort_pv_", ""))
        await handle_calc_mortgage_pv(chat_id, pv)
    elif data.startswith("mort_years_"):
        years = int(data.replace("mort_years_", ""))
        await handle_calc_mortgage_years(chat_id, years)
    elif data.startswith("mort_prog_"):
        program = data.replace("mort_prog_", "")
        await handle_calc_mortgage_result(chat_id, program)
    elif data == "calc_roi":
        await handle_calc_roi_start(chat_id)
    elif data.startswith("roi_rent_"):
        rent = int(data.replace("roi_rent_", ""))
        await handle_calc_roi_rent(chat_id, rent)
    elif data.startswith("roi_occ_"):
        occ = float(data.replace("roi_occ_", ""))
        await handle_calc_roi_result(chat_id, occ)

    # Калькуляторы с привязкой к ЖК
    elif data.startswith("calc_for_"):
        property_id = int(data.replace("calc_for_", ""))
        await handle_calc_for_property(chat_id, property_id)
    elif data.startswith("calc_inst_prop_"):
        property_id = int(data.replace("calc_inst_prop_", ""))
        await handle_calc_installment_for_property(chat_id, property_id)
    elif data.startswith("calc_mort_prop_"):
        property_id = int(data.replace("calc_mort_prop_", ""))
        await handle_calc_mortgage_for_property(chat_id, property_id)
    elif data.startswith("calc_roi_prop_"):
        property_id = int(data.replace("calc_roi_prop_", ""))
        await handle_calc_roi_for_property(chat_id, property_id)

    # Работа с ЖК
    elif data.startswith("open_property_"):
        property_id = int(data.replace("open_property_", ""))
        await handle_open_property(chat_id, property_id)
    elif data.startswith("download_"):
        file_id = int(data.replace("download_", ""))
        await handle_download_file(chat_id, file_id)
    elif data.startswith("all_files_"):
        property_id = int(data.replace("all_files_", ""))
        await handle_all_files(chat_id, property_id)
    elif data.startswith("summary_pdf_"):
        property_id = int(data.replace("summary_pdf_", ""))
        from bot.handlers.query import handle_summary_pdf
        await handle_summary_pdf(chat_id, property_id)
    elif data.startswith("summary_"):
        property_id = int(data.replace("summary_", ""))
        await handle_property_summary(chat_id, property_id)
    elif data.startswith("kp_for_"):
        property_id = int(data.replace("kp_for_", ""))
        await handle_kp_for_property(chat_id, property_id)
    elif data.startswith("kp_style_"):
        style = data.replace("kp_style_", "")
        await handle_kp_style_selected(chat_id, style)
    elif data.startswith("kp_restyle_"):
        property_id = int(data.replace("kp_restyle_", ""))
        await handle_kp_restyle(chat_id, property_id)
    elif data.startswith("edit_"):
        property_id = int(data.replace("edit_", ""))
        await send_message(chat_id, "✏️ Редактирование в разработке.")
    elif data.startswith("delete_"):
        property_id = int(data.replace("delete_", ""))
        await handle_delete_property(chat_id, property_id)
    elif data.startswith("confirm_delete_"):
        property_id = int(data.replace("confirm_delete_", ""))
        await handle_confirm_delete(chat_id, property_id)
    elif data == "files_done":
        await handle_files_done(chat_id)
    elif data == "confirm_property":
        await handle_confirm_property(chat_id)


async def process_message(message: Dict[str, Any]):
    chat_id = message["chat"]["id"]
    user_info = message.get("from", {})
    text = (message.get("text") or "").strip()
    file_id, file_name, file_type = get_file_type(message)

    # Команды
    if text and is_exit_command(text):
        await handle_cancel(chat_id)
        return
    if text == "/start":
        await handle_start(chat_id, user_info)
        return
    if text == "/help":
        await handle_help(chat_id)
        return
    if text == "/add":
        await handle_add_property_start(chat_id)
        return
    if text == "/calc":
        await handle_calc_menu(chat_id)
        return

    state, state_data = get_user_state(chat_id)

    # FSM для добавления ЖК (оставляем)
    if state == States.ADD_PROPERTY_NAME:
        if text:
            await handle_property_name(chat_id, text)
        else:
            await send_message(chat_id, "✏️ Введи название ЖК")
        return
    if state == States.ADD_PROPERTY_FILES:
        if file_id:
            await handle_file_upload(chat_id, message)
            return
        if text and text.lower() in ("готово", "done", "всё", "все", "хватит"):
            await handle_files_done(chat_id)
            return
        await send_message(chat_id, "📁 Отправь файлы или нажми «Готово»")
        return
    if state == States.ADD_PROPERTY_CONFIRM:
        if text:
            await handle_property_correction(chat_id, text)
        return

    # Универсальный handler — всё остальное
    if text:
        await handle_universal(chat_id, text, state_data)
    elif file_id:
        await send_message(chat_id, "📁 Чтобы добавить файл, сначала начни /add")


async def handle_universal(chat_id: int, text: str, state_data: dict = None):
    """Универсальный обработчик через RAG + LLM"""
    
    # Сохраняем сообщение пользователя
    save_message(chat_id, "user", text)
    
    # RAG поиск
    property_id = state_data.get("property_id") if state_data else None
    chunks = rag_search(chat_id, text, property_id=property_id, limit=10)
    
    # История диалога
    history = get_chat_history(chat_id, limit=6)
    
    # LLM ответ
    result = await universal_respond(text, chunks, history)
    
    # Выполняем действие
    await execute_action(chat_id, result, property_id)


async def execute_action(chat_id: int, result: dict, property_id: int = None):
    """Выполнить действие из LLM"""
    action = result.get("action", "text")
    
    if action == "text":
        response = result.get("content", "🤔 Не понял запрос")
        save_message(chat_id, "assistant", response)
        await send_message(chat_id, response)
    
    elif action == "calc_installment":
        price = result.get("price", 10000000)
        pv = result.get("pv", 30)
        months = result.get("months", 12)
        calc_result = calc_installment(price, pv, months)
        response = format_installment_result(calc_result)
        save_message(chat_id, "assistant", response)
        await send_message(chat_id, response)
    
    elif action == "calc_mortgage":
        price = result.get("price", 10000000)
        pv = result.get("pv", 20)
        years = result.get("years", 20)
        program = result.get("program", "standard")
        calc_result = calc_mortgage(price, pv, years, program)
        response = format_mortgage_result(calc_result)
        save_message(chat_id, "assistant", response)
        await send_message(chat_id, response)
    
    elif action == "calc_roi":
        price = result.get("price", 10000000)
        rent = result.get("rent", 3000)
        occupancy = result.get("occupancy", 70)
        calc_result = calc_roi(price, rent, occupancy)
        response = format_roi_result(calc_result)
        save_message(chat_id, "assistant", response)
        await send_message(chat_id, response)
    
    elif action == "generate_kp":
        prop_id = result.get("property_id") or property_id
        query = result.get("query", "")
        if prop_id:
            await handle_kp_for_property(chat_id, prop_id)
        else:
            await send_message(chat_id, "🏢 Сначала выбери ЖК для КП")
    
    elif action == "send_file":
        file_name = result.get("file_name", "")
        await send_message(chat_id, f"📁 Ищу файл: {file_name}...")
        # TODO: поиск и отправка файла
    
    else:
        await send_message(chat_id, "🤔 Не понял что делать")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
