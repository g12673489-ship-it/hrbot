import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import admin, user, group

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logging.error("❌ BOT_TOKEN не указан в файле .env! Пожалуйста, укажите токен вашего бота от @BotFather.")
        print("\n[ОШИБКА] В файле .env отсутствует валидный BOT_TOKEN.")
        print("Укажите токен бота в файле .env и запустите снова.\n")
        return

    # Инициализация базы данных
    await init_db()
    logging.info("База данных инициализирована.")

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

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
