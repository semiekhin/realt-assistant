"""
Запуск бота в режиме polling (для разработки)
"""
import asyncio
import aiohttp
from config import TELEGRAM_BOT_TOKEN

# Импортируем обработку из app
from app import process_message, process_callback
from db.database import init_db


async def get_updates(offset: int = 0) -> list:
    """Получить обновления от Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "offset": offset,
        "timeout": 30,
        "allowed_updates": ["message", "callback_query"]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result", [])
    except Exception as e:
        print(f"[POLLING] Error: {e}")
    
    return []


async def main():
    """Главный цикл polling"""
    print("[POLLING] Starting...")
    init_db()
    
    offset = 0
    
    while True:
        updates = await get_updates(offset)
        
        for update in updates:
            offset = update["update_id"] + 1
            
            try:
                if "callback_query" in update:
                    await process_callback(update["callback_query"])
                elif "message" in update:
                    await process_message(update["message"])
            except Exception as e:
                print(f"[POLLING] Process error: {e}")
        
        if not updates:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
