from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import update, select

from db.engine import async_session
from db.models import User
from utils.texts import TEXTS

settings_router = Router()

async def get_lang(chat_id: int):
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.chat_id == chat_id))).scalar()
        return user.language if user else 'uz'

@settings_router.message(Command("settings"))
async def show_settings(message: types.Message):
    lang = await get_lang(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS[lang]['change_lang_btn'], callback_data="change_language")
    await message.answer(TEXTS[lang]['settings_menu'], reply_markup=builder.as_markup())

@settings_router.callback_query(F.data == "change_language")
async def change_lang_step(call: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="newlang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="newlang_ru")
    builder.button(text="🇺🇸 English", callback_data="newlang_en")
    builder.adjust(1)
    await call.message.edit_text("Выберите язык:", reply_markup=builder.as_markup())

@settings_router.callback_query(F.data.startswith("newlang_"))
async def update_lang(call: types.CallbackQuery):
    new_lang = call.data.split("_")[-1]
    async with async_session() as session:
        await session.execute(update(User).where(User.chat_id == call.from_user.id).values(language=new_lang))
        await session.commit()
    await call.message.edit_text(TEXTS[new_lang]['lang_changed'])
