import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from db.engine import async_session
from db.models import User
from utils.filters import IsAdmin

admin_router = Router()
admin_router.message.filter(IsAdmin())

class Broadcast(StatesGroup):
    message = State()

@admin_router.message(Command("send_all"))
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing (matn, rasm yoki video):")
    await state.set_state(Broadcast.message)

@admin_router.message(Broadcast.message)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    async with async_session() as session:
        # Barcha foydalanuvchilarning chat_id larini olish
        result = await session.execute(select(User.chat_id))
        users = result.scalars().all()

    count = 0
    await message.answer(f"Xabar yuborish boshlandi (Jami: {len(users)} ta)...")

    for chat_id in users:
        try:
            # Xabarni nusxasini yuborish (copy_message)
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            count += 1
            await asyncio.sleep(0.05) # Telegram bloklab qo'ymasligi uchun kichik pauza
        except Exception:
            continue

    await message.answer(f"Xabar yuborish yakunlandi! {count} ta foydalanuvchiga yetib bordi.")
    await state.clear()
