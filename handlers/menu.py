from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc

from db.engine import async_session
from db.models import User, Card, Transaction  
from config import settings
from utils.texts import TEXTS

menu_router = Router()

async def get_user_lang(chat_id: int):
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == chat_id))).scalar()
        return user.language if user else 'uz'

@menu_router.message(Command("my_cards"))
async def show_my_cards(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == message.from_user.id))).scalar()

        if not user or not user.phone:
            await message.answer(TEXTS[lang]['not_registered'])
            return

        cards = (await session.execute(select(Card).where(Card.phone == user.phone))).scalars().all()

    if cards:
        for i, card in enumerate(cards, 1):
            c_num = card.card_number
            hidden_num = f"{c_num[:4]} **** **** {c_num[-4:]}"
            
            txt = f"{i}. 🆔 <b>{hidden_num}</b>\n"
            txt += TEXTS[lang]['card_balance'].format(balance=card.balance)
            txt += TEXTS[lang]['card_status'].format(status=card.status)
            txt += "----------------------------"
            
            builder = InlineKeyboardBuilder()
            builder.button(text="💸 Transfer", callback_data=f"transfer_{card.id}")
            builder.button(text="📜 Tarix", callback_data=f"history_{card.id}")
            builder.adjust(2)
            
            await message.answer(txt, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await message.answer(TEXTS[lang]['no_cards'])

# --- Tugmalar uchun Callback handlerlar ---

@menu_router.callback_query(F.data.startswith("transfer_"))
async def callback_transfer(call: types.CallbackQuery, state: FSMContext):
    from handlers.transfer import start_transfer
    await start_transfer(call.message, state)
    await call.answer()

@menu_router.callback_query(F.data.startswith("history_"))
async def callback_history(call: types.CallbackQuery):
    # Karta ID sini callback_data dan ajratib olamiz
    card_id = int(call.data.split("_")[1])
    
    lang = await get_user_lang(call.from_user.id)
    async with async_session() as session:
        # Aynan shu karta ma'lumotlarini olamiz
        card = (await session.execute(select(Card).where(Card.id == card_id))).scalar()
        
        # Shu kartaga tegishli tranzaksiyalar
        transactions = (await session.execute(
            select(Transaction).where(Transaction.card_id == card_id)
            .order_by(desc(Transaction.created_at)).limit(5)
        )).scalars().all()

    if transactions:
        txt = TEXTS[lang]['history_title'].format(last4=card.card_number[-4:])
        for tr in transactions:
            is_in = tr.type in [TEXTS['uz']['trans_in'], TEXTS['ru']['trans_in'], TEXTS['en']['trans_in'], 'P2P IN', 'Korreksiya']
            icon = "🟢" if is_in else "🔴"
            sign = "+" if is_in else "-"
            date = tr.created_at.strftime("%d.%m %H:%M")
            txt += f"{icon} {date} | <b>{sign}{tr.amount:,}</b> UZS\n"
        await call.message.answer(txt, parse_mode="HTML")
    else:
        await call.message.answer(TEXTS[lang]['history_empty'])
    
    await call.answer()

@menu_router.message(Command("help"))
async def help_command(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS[lang]['admin_btn'], url=settings.ADMIN_CHAT_LINK)
    
    await message.answer(TEXTS[lang]['help_text'], reply_markup=builder.as_markup(), parse_mode="HTML")
