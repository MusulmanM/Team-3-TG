import asyncio
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func

from db.engine import async_session
from db.models import User, Card, Transaction
from utils.filters import IsAdmin
from utils.texts import TEXTS

admin_router = Router()
admin_router.message.filter(IsAdmin())

# Admin uchun holatlar
class AdminStates(StatesGroup):
    broadcast = State()
    pay_user_id = State()
    pay_amount = State()

async def get_admin_lang(chat_id: int):
    """Admin tilini aniqlash"""
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == chat_id))).scalar()
        return user.language if user else 'uz'

@admin_router.message(Command("admin-1324"))
async def admin_panel(message: types.Message):
    """Adminlar uchun asosiy menyu (Balans boshqarish bilan)"""
    lang = await get_admin_lang(message.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS[lang].get('adm_btn_stats', "📊 Statistika"), callback_data="adm_stats")
    builder.button(text=TEXTS[lang].get('adm_btn_send', "📢 Xabar yuborish"), callback_data="adm_send")
    builder.button(text=TEXTS[lang].get('adm_btn_pay', "💰 Balansni boshqarish"), callback_data="adm_pay")
    builder.adjust(1)
    
    txt = TEXTS[lang].get('admin_panel', "👨‍💻 <b>Admin panel</b>")
    await message.answer(txt, reply_markup=builder.as_markup(), parse_mode="HTML")

# --- Balansni boshqarish (Admin ixtiyoriy summa qo'shadi/ayiradi) ---

@admin_router.callback_query(F.data == "adm_pay")
async def admin_pay_start(call: types.CallbackQuery, state: FSMContext):
    lang = await get_admin_lang(call.from_user.id)
    await call.message.answer(TEXTS[lang].get('adm_pay_req', "Foydalanuvchi Chat ID sini kiriting:"))
    await state.set_state(AdminStates.pay_user_id)
    await call.answer()

@admin_router.message(AdminStates.pay_user_id)
async def admin_pay_id(message: types.Message, state: FSMContext):
    lang = await get_admin_lang(message.from_user.id)
    if not message.text.isdigit():
        await message.answer("Chat ID faqat raqamlardan iborat bo'lishi kerak!")
        return
    await state.update_data(target_id=int(message.text))
    await message.answer(TEXTS[lang].get('adm_amount_req', "Summani kiriting (masalan: 50000 yoki -20000):"))
    await state.set_state(AdminStates.pay_amount)

@admin_router.message(AdminStates.pay_amount)
async def admin_pay_final(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_admin_lang(message.from_user.id)
    data = await state.get_data()
    
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Iltimos, summani raqamda kiriting!")
        return

    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == data['target_id']))).scalar()
        if not user:
            await message.answer("Foydalanuvchi topilmadi!")
            await state.clear()
            return

        card = (await session.execute(select(Card).where(Card.phone == user.phone).limit(1))).scalar()
        if card:
            card.balance += amount
            trans_type = "Korreksiya"
            session.add(Transaction(card_id=card.id, amount=abs(amount), type=trans_type))
            await session.commit()
            
            await message.answer(TEXTS[lang].get('adm_pay_success', "✅ Balans o'zgartirildi!"))
            
            # Foydalanuvchiga bildirishnoma yuborish
            try:
                prefix = "+" if amount > 0 else ""
                await bot.send_message(
                    user.chat_id, 
                    f"💰 <b>Balansingiz o'zgardi!</b>\n━━━━━━━━━━━━━━━\nSumma: <b>{prefix}{amount:,} UZS</b>\nYangi balans: <b>{card.balance:,} UZS</b>",
                    parse_mode="HTML"
                )
            except: pass
        else:
            await message.answer("Foydalanuvchining kartasi topilmadi!")
    
    await state.clear()

# --- Statistika handler ---

@admin_router.callback_query(F.data == "adm_stats")
async def handle_stats(call: types.CallbackQuery):
    lang = await get_admin_lang(call.from_user.id)
    async with async_session() as session:
        u_count = await session.scalar(select(func.count(User.id)))
        c_count = await session.scalar(select(func.count(Card.id)))
        t_count = await session.scalar(select(func.count(Transaction.id)))

    txt = TEXTS[lang].get('stats_text', "📊 Statistika:\nUserlar: {u}\nKartalar: {c}\nTranzaksiyalar: {t}").format(
        u=u_count, c=c_count, t=t_count
    )
    await call.message.edit_text(txt, reply_markup=call.message.reply_markup, parse_mode="HTML")
    await call.answer()

# --- Xabar yuborish (Broadcast) handler ---

@admin_router.callback_query(F.data == "adm_send")
async def handle_send_all(call: types.CallbackQuery, state: FSMContext):
    lang = await get_admin_lang(call.from_user.id)
    await call.message.answer(TEXTS[lang].get('broadcast_req', "Xabar yuboring:"))
    await state.set_state(AdminStates.broadcast)
    await call.answer()

@admin_router.message(AdminStates.broadcast)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_admin_lang(message.from_user.id)
    async with async_session() as session:
        users = (await session.execute(select(User.chat_id))).scalars().all()

    count = 0
    total = len(users)
    await message.answer(TEXTS[lang].get('broadcast_start', "Boshlandi...").format(total=total))

    for chat_id in users:
        try:
            await bot.copy_message(chat_id=chat_id, from_chat_id=message.chat.id, message_id=message.message_id)
            count += 1
            await asyncio.sleep(0.05) 
        except: continue

    await message.answer(TEXTS[lang].get('broadcast_done', "Tayyor!").format(count=count))
    await state.clear()
