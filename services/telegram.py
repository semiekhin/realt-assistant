"""
Сервис для работы с Telegram API
"""
import os
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from pathlib import Path

from config import TELEGRAM_BOT_TOKEN, UPLOADS_DIR


def get_token() -> str:
    return TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[Dict] = None,
    disable_preview: bool = True
) -> bool:
    """Отправить текстовое сообщение"""
    token = get_token()
    if not token:
        print("[TG] Token not set")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    print(f"[TG] Error: {result}")
                return result.get("ok", False)
    except Exception as e:
        print(f"[TG] send_message error: {e}")
        return False


async def send_message_with_buttons(
    chat_id: int,
    text: str,
    buttons: List[List[Dict[str, str]]],
    parse_mode: str = "HTML"
) -> bool:
    """Отправить сообщение с inline-кнопками"""
    reply_markup = {"inline_keyboard": buttons}
    return await send_message(chat_id, text, parse_mode, reply_markup)


async def send_message_with_keyboard(
    chat_id: int,
    text: str,
    keyboard: List[List[str]],
    parse_mode: str = "HTML",
    one_time: bool = True,
    resize: bool = True
) -> bool:
    """Отправить сообщение с reply-клавиатурой"""
    reply_markup = {
        "keyboard": [[{"text": btn} for btn in row] for row in keyboard],
        "resize_keyboard": resize,
        "one_time_keyboard": one_time
    }
    return await send_message(chat_id, text, parse_mode, reply_markup)


async def remove_keyboard(chat_id: int, text: str = "👍") -> bool:
    """Удалить reply-клавиатуру"""
    reply_markup = {"remove_keyboard": True}
    return await send_message(chat_id, text, reply_markup=reply_markup)


async def answer_callback(callback_id: str, text: Optional[str] = None) -> bool:
    """Ответить на callback query"""
    token = get_token()
    if not token:
        return False
    
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                result = await resp.json()
                return result.get("ok", False)
    except Exception as e:
        print(f"[TG] answer_callback error: {e}")
        return False


async def download_file(file_id: str, save_as: Optional[str] = None) -> Optional[str]:
    """
    Скачать файл из Telegram
    
    Returns:
        Путь к сохранённому файлу или None
    """
    token = get_token()
    if not token:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            # Получаем информацию о файле
            url = f"https://api.telegram.org/bot{token}/getFile"
            async with session.post(url, json={"file_id": file_id}) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    print(f"[TG] getFile error: {result}")
                    return None
                
                file_path = result["result"]["file_path"]
                file_name = save_as or Path(file_path).name
            
            # Скачиваем файл
            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            async with session.get(download_url) as resp:
                if resp.status != 200:
                    print(f"[TG] download error: {resp.status}")
                    return None
                
                content = await resp.read()
            
            # Сохраняем
            save_path = UPLOADS_DIR / file_name
            save_path.write_bytes(content)
            
            print(f"[TG] Downloaded: {save_path}")
            return str(save_path)
            
    except Exception as e:
        print(f"[TG] download_file error: {e}")
        return None


async def send_document(
    chat_id: int,
    file_path: str,
    caption: Optional[str] = None
) -> bool:
    """Отправить документ"""
    token = get_token()
    if not token or not Path(file_path).exists():
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field("chat_id", str(chat_id))
            data.add_field("document", 
                          open(file_path, "rb"),
                          filename=Path(file_path).name)
            if caption:
                data.add_field("caption", caption)
                data.add_field("parse_mode", "HTML")
            
            async with session.post(url, data=data) as resp:
                result = await resp.json()
                return result.get("ok", False)
    except Exception as e:
        print(f"[TG] send_document error: {e}")
        return False


def get_file_type(message: Dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Определить тип файла из сообщения
    
    Returns:
        (file_id, file_name, file_type) или (None, None, None)
    """
    # Документ
    if "document" in message:
        doc = message["document"]
        return doc["file_id"], doc.get("file_name", "document"), "document"
    
    # Фото (берём самое большое)
    if "photo" in message:
        photo = message["photo"][-1]  # последнее = самое большое
        return photo["file_id"], f"photo_{photo['file_id'][:8]}.jpg", "photo"
    
    # Голосовое
    if "voice" in message:
        voice = message["voice"]
        return voice["file_id"], "voice.ogg", "voice"
    
    return None, None, None
