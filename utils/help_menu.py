from aiogram import Bot
from aiogram.types import BotCommand

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='Botni ishga tushirish'),
        BotCommand(command='/my_cards', description='Mening kartalarim'),
        BotCommand(command='/transfer', description='Pul o\'tkazish (P2P)'),
        BotCommand(command='/history', description='Tranzaksiyalar tarixi'),
        BotCommand(command='/settings', description='Sozlamalar (Tilni o\'zgartirish)'),
        BotCommand(command='/help', description='Yordam va admin bilan bog\'lanish')
    ]
    
    await bot.set_my_commands(commands=main_menu_commands)
