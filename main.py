import asyncio
import logging
import sys
import os

VERSION = "2.0.1"  # 2026-09-08: fix CV file upload, add stats, remove cooldown

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, TARGET_GROUP_ID
from database.db import init_db
from handlers import admin, user, group

async def main():
    # --- Настройка логирования (stdout + файл) ---
    log_handlers = [logging.StreamHandler(sys.stdout)]
    log_file = os.path.join(os.path.dirname(__file__), "bot.log")
    try:
        log_handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except Exception:
        pass  # нет прав на запись — работаем без файла

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=log_handlers
    )

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logging.error("❌ BOT_TOKEN не указан в файле .env!")
        return

    # Инициализация базы данных
    await init_db()
    logging.info("База данных инициализирована.")
    logging.info(f"TARGET_GROUP_ID = {TARGET_GROUP_ID} (type: {type(TARGET_GROUP_ID).__name__})")
    if not TARGET_GROUP_ID or TARGET_GROUP_ID == 0:
        logging.warning("⚠️ TARGET_GROUP_ID не задан! Заявки НЕ будут отправляться в группу.")

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)

    # SqliteFSMStorage — FSM-состояния переживают перезапуск бота
    fsm_db_path = os.path.join(os.path.dirname(__file__), "fsm_states.db")
    from database.fsm_storage import SqliteFSMStorage
    storage = SqliteFSMStorage(fsm_db_path)
    await storage.init()
    logging.info(f"FSM storage: SqliteFSMStorage ({fsm_db_path})")

    dp = Dispatcher(storage=storage)

    # Подключение роутеров
    dp.include_router(admin.router)
    dp.include_router(group.router)
    dp.include_router(user.router)

    # Пропуск накопившихся обновлений и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен и готов к работе!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
