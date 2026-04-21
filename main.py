import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from db.engine import engine
from db.models import Base

# Menyu buyruqlarini (chap burchakdagi ko'k tugma) o'rnatish funksiyasi
from utils.help_menu import set_main_menu

# Routerlarni import qilish (fayl yo'llari to'g'riligini tekshiring)
from handlers.register import router as register_router
from handlers.menu import menu_router
from handlers.admin import admin_router
from handlers.transfer import transfer_router
from handlers.settings import settings_router

async def main():
    # 1. Loggingni sozlash (Bot xatti-harakatlarini terminalda ko'rish uchun)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )

    # 2. Ma'lumotlar bazasi jadvallarini avtomatik yaratish/tekshirish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logging.info("Ma'lumotlar bazasi jadvallari muvaffaqiyatli tekshirildi!")

    # 3. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=settings.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 4. Routerlarni Dispatcherga ulash (Tartibga e'tibor bering)
    dp.include_router(admin_router)      # Admin buyruqlari birinchi
    dp.include_router(register_router)   # Ro'yxatdan o'tish logikasi
    dp.include_router(menu_router)       # Asosiy menyu (/my_cards, /history)
    dp.include_router(transfer_router)   # Pul o'tkazmalari (P2P)
    dp.include_router(settings_router)   # Sozlamalar (Tilni o'zgartirish)

    # 5. Bot buyruqlar menyusini o'rnatish (/start, /settings va h.k.lar menyuda chiqishi uchun)
    await set_main_menu(bot)

    logging.info("Bot muvaffaqiyatli ishga tushdi!")
    
    # Bot o'chiq bo'lgan vaqtda kelgan eski xabarlarni tozalash (xavfsizlik uchun)
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        # Botni ishga tushirish (Polling)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot ishga tushishida xatolik yuz berdi: {e}")
    finally:
        # Sessiyani xavfsiz yopish
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot foydalanuvchi tomonidan to'xtatildi!")
