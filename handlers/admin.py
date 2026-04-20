import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from db.engine import async_session
from db.models import User, Card, Transaction
from utils.filters import IsAdmin

admin_router = Router()
admin_router.message.filter(IsAdmin())

class Broadcast(StatesGroup):
    message = State()

@admin_router.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Adminlar uchun asosiy menyu"""
    txt = (
        "👨‍💻 <b>Admin panel</b>\n\n"
        "📊 /stats - Bot statistikasi\n"
        "📢 /send_all - Barcha foydalanuvchilarga xabar yuborish\n"
        "💳 /add_test_data - Test uchun karta yaratish\n"
    )
    await message.answer(txt, parse_mode="HTML")

@admin_router.message(Command("stats"))
async def bot_stats(message: types.Message):
    """Bot statistikasi (foydalanuvchilar va kartalar soni)"""
    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        cards_count = await session.scalar(select(func.count(Card.id)))
        trans_count = await session.scalar(select(func.count(Transaction.id)))

    txt = (
        "📊 <b>Bot statistikasi:</b>\n\n"
        f"👤 Foydalanuvchilar: {users_count} ta\n"
        f"💳 Ulangan kartalar: {cards_count} ta\n"
        f"🔄 Tranzaksiyalar: {trans_count} ta"
    )
    await message.answer(txt, parse_mode="HTML")

@admin_router.message(Command("send_all"))
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabarni (rasm, matn, video) yuboring:")
    await state.set_state(Broadcast.message)

@admin_router.message(Broadcast.message)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    async with async_session() as session:
        result = await session.execute(select(User.chat_id))
        users = result.scalars().all()

    count = 0
    progress_msg = await message.answer(f"⏳ Xabar yuborish boshlandi (0/{len(users)})...")

    for chat_id in users:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            continue

    await message.answer(f"✅ Xabar yuborish yakunlandi!\n👤 {count} ta foydalanuvchiga yetib bordi.")
    await state.clear()

@admin_router.message(Command("add_test_data"))
async def add_test_data(message: types.Message):
    """Faqat admin o'zi uchun test karta yaratib olishi uchun"""
    async with async_session() as session:
        user_query = select(User).where(User.chat_id == message.from_user.id)
        user = (await session.execute(user_query)).scalar()

        if not user or not user.phone:
            await message.answer("Siz hali ro'yxatdan o'tmagansiz!")
            return

        new_card = Card(
            card_number="8600" + "".join([str(i) for i in range(12)]),
            phone=user.phone,
            balance=500000.0,
            status="active"
        )
        session.add(new_card)
        await session.commit()
    
    await message.answer("✅ Sizga 500,000 UZS balansli test karta biriktirildi!\nEndi /my_cards orqali ko'rishingiz mumkin.")
