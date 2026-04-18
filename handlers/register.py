import re
from aiogram import Router, F, types, html
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select

from db.engine import async_session
from db.models import User, Card
from utils.texts import TEXTS
from utils.validators import check_luhn

router = Router()

class Register(StatesGroup):
    language = State()
    fullname = State()
    phone = State()
    card_number = State()

def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.button(text="🇺🇸 English", callback_data="lang_en")
    builder.adjust(1)
    return builder.as_markup()

@router.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        res = await session.execute(select(User).filter(User.chat_id == message.from_user.id))
        user = res.scalar_one_or_none()
        
    if user:
        lang = user.language or 'uz'

        await message.answer(f"{TEXTS[lang]['success']} {html.bold(user.fullname)}!")
    else:
        await message.answer("Tilni tanlang / Выберите язык / Choose language:", reply_markup=get_lang_keyboard())
        await state.set_state(Register.language)

@router.callback_query(Register.language, F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[-1]
    await state.update_data(locale=lang)
    await callback.message.delete()
    await callback.message.answer(TEXTS[lang]['register'])
    await state.set_state(Register.fullname)
    await callback.answer()

@router.message(Register.fullname)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    data = await state.get_data()
    lang = data.get('locale', 'uz')
    
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Contact", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(TEXTS[lang]['phone'], reply_markup=markup)
    await state.set_state(Register.phone)

@router.message(Register.phone)
@router.message(F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await message.answer("Karta raqamingizni kiriting (16 xonali):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Register.card_number)

@router.message(Register.card_number)
async def get_card_number(message: types.Message, state: FSMContext):

    try:
        await message.delete()
    except Exception as e:
        print(f"Xabarni o'chirishda xatolik: {e}")

    card_no = re.sub(r'\D', '', message.text)
    data = await state.get_data()
    lang = data.get('locale', 'uz')
    
    if len(card_no) == 16 and check_luhn(card_no):
        async with async_session() as session:
            try:

                session.add(User(
                    fullname=data['fullname'],
                    chat_id=message.from_user.id,
                    phone=data['phone'],
                    language=lang
                ))

                
                session.add(Card(
                    card_number=card_no,
                    phone=data['phone'],
                    balance=0.0,
                    status='active'
                ))
                
                await session.commit()
                
                
                success_text = f"{TEXTS[lang]['success']} {html.bold(data['fullname'])}!\n(Karta raqamingiz xavfsizlik uchun o'chirildi)"
                await message.answer(success_text)
                await state.clear()
                
            except Exception as e:
                await session.rollback()
                print(f"DB ERROR: {e}")
                await message.answer("Xatolik! Ma'lumotlarni saqlab bo'lmadi.")
    else:
        await message.answer("Karta raqami xato. Qayta kiriting:")
