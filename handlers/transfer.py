import re
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime

from db.engine import async_session
from db.models import User, Card, Transaction
from utils.texts import TEXTS

transfer_router = Router()

class TransferState(StatesGroup):
    receiver_card = State()
    amount = State()

async def get_lang(chat_id: int):
    """Foydalanuvchi tilini bazadan olish"""
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == chat_id))).scalar()
        return user.language if user else 'uz'

def mask_name(name: str):
    """Ismni M****** formatiga o'tkazish (Xavfsizlik uchun)"""
    if not name or len(name) < 1: return "***"
    return f"{name[0]}{'*' * (len(name)-1)}"

@transfer_router.message(Command("transfer"))
async def start_transfer(message: types.Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    await message.answer(TEXTS[lang]['transfer_req'])
    await state.set_state(TransferState.receiver_card)

@transfer_router.message(TransferState.receiver_card)
async def get_receiver_card(message: types.Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    card_no = re.sub(r'\D', '', message.text)
    
    if len(card_no) != 16:
        await message.answer(TEXTS[lang]['card_error'])
        return

    async with async_session() as session:
        # 1. Kartani qidirish
        card_res = await session.execute(select(Card).where(Card.card_number == card_no))
        receiver_card = card_res.scalar_one_or_none()
        
        if not receiver_card:
            await message.answer(TEXTS[lang]['card_not_found'])
            return
            
        # 2. Karta egasini topish
        user_res = await session.execute(select(User).where(User.phone == receiver_card.phone))
        receiver_user = user_res.scalar_one_or_none()
        
        masked_name = mask_name(receiver_user.fullname if receiver_user else "Foydalanuvchi")
        
        await state.update_data(
            to_card=card_no, 
            receiver_chat_id=receiver_user.chat_id if receiver_user else None,
            receiver_name=masked_name
        )
        
        # Tasdiqlash: Ismni ko'rsatib, summani so'rash
        confirm_text = TEXTS[lang]['receiver_found'].format(name=masked_name)
        await message.answer(f"{confirm_text}\n{TEXTS[lang]['transfer_amount']}", parse_mode="HTML")
        await state.set_state(TransferState.amount)

@transfer_router.message(TransferState.amount)
async def process_transfer(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_lang(message.from_user.id)
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except:
        await message.answer("Iltimos, miqdorni raqamda kiriting:")
        return

    data = await state.get_data()
    async with async_session() as session:
        # Sender (Jo'natuvchi)
        sender_res = await session.execute(select(User).where(User.chat_id == message.from_user.id))
        sender = sender_res.scalar_one_or_none()
        
        sender_card_res = await session.execute(select(Card).where(Card.phone == sender.phone).limit(1))
        sender_card = sender_card_res.scalar_one_or_none()
        
        # Receiver (Qabul qiluvchi)
        receiver_card_res = await session.execute(select(Card).where(Card.card_number == data['to_card']))
        receiver_card = receiver_card_res.scalar_one_or_none()

        if sender_card.card_number == receiver_card.card_number:
            await message.answer(TEXTS[lang]['transfer_self'])
            return

        if sender_card.balance < amount:
            await message.answer(TEXTS[lang]['insufficient_funds'])
            return

        # Pul o'tkazish logikasi
        sender_card.balance -= amount
        receiver_card.balance += amount
        
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Tranzaksiyalar tarixiga qo'shish
        session.add(Transaction(card_id=sender_card.id, amount=amount, type="P2P OUT"))
        session.add(Transaction(card_id=receiver_card.id, amount=amount, type="P2P IN"))
        await session.commit()

        # Sender SMS (Jo'natuvchiga)
        await message.answer(
            TEXTS[lang]['transfer_success_sender'].format(
                to=data['receiver_name'],
                card=data['to_card'][-4:],
                amount=amount,
                date=now,
                balance=sender_card.balance
            ), parse_mode="HTML"
        )

        # Receiver SMS (Qabul qiluvchiga)
        if data['receiver_chat_id']:
            try:
                # Qabul qiluvchi tilini aniqlash
                r_res = await session.execute(select(User).where(User.chat_id == data['receiver_chat_id']))
                r_user = r_res.scalar_one_or_none()
                r_lang = r_user.language if r_user else 'uz'

                await bot.send_message(
                    data['receiver_chat_id'],
                    TEXTS[r_lang]['transfer_success_receiver'].format(
                        from_user=mask_name(sender.fullname),
                        card=data['to_card'][-4:],
                        amount=amount,
                        date=now,
                        balance=receiver_card.balance
                    ), parse_mode="HTML"
                )
            except: pass

    await state.clear()
