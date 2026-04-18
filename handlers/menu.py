from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from db.engine import async_session
from db.models import User, Card
from config import settings

menu_router = Router()

@menu_router.message(Command("my_cards"))
async def show_my_cards(message: types.Message):
    async with async_session() as session:
        user_phone_query = select(User.phone).where(User.chat_id == message.from_user.id)
        user_phone = (await session.execute(user_phone_query)).scalar()

        if not user_phone:
            await message.answer("Avval ro'yxatdan o'ting: /start")
            return

        cards_query = select(Card).filter(Card.phone == user_phone)
        result = await session.execute(cards_query)
        cards = result.scalars().all()

    if cards:
        txt = "Sizning kartalaringiz:\n\n"
        for i, card in enumerate(cards, 1):
            txt += (f"Balans: {card.balance} UZS\n"
                    f"Status: {card.status}\n\n")
        await message.answer(txt)
    else:
        await message.answer("Sizda hali karta yo'q.")

@menu_router.message(Command("help"))
async def help_command(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Admin bilan bog'lanish", url=settings.ADMIN_CHAT_LINK)
    
    txt = (
        "Yordam bo'limi:\n\n"
        "/start - Botni qayta ishga tushirish\n"
        "/my_cards - Mening kartalarim\n\n"
        "Savollaringiz bo'lsa, pastdagi tugma orqali admin bilan bog'lanishingiz mumkin."
    )
    
    await message.answer(txt, reply_markup=builder.as_markup())
