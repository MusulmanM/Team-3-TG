import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from db.engine import engine
from db.models import Base

from utils.help_menu import set_main_menu


from handlers.register import router as register_router
from handlers.menu import menu_router
from handlers.admin import admin_router

async def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )


    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)
    
    logging.info("Ma'lumotlar bazasi va jadvallar muvaffaqiyatli tekshirildi/yaratildi!")


    bot = Bot(
        token=settings.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()


    dp.include_router(admin_router)
    dp.include_router(register_router)
    dp.include_router(menu_router)


    await set_main_menu(bot)

    logging.info("Bot muvaffaqiyatli ishga tushdi!")
    

    await bot.delete_webhook(drop_pending_updates=True)
    
    try:

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot ishlashida xatolik: {e}")
    finally:

        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot foydalanuvchi tomonidan to'xtatildi!")
