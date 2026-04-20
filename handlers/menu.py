from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update
from datetime import datetime

from db.engine import async_session
from db.models import User, Card, Transaction # Transaction modelini ham import qiling
from config import settings

menu_router = Router()

@menu_router.message(Command("my_cards"))
async def show_my_cards(message: types.Message):
    async with async_session() as session:
        # Userni chat_id orqali topish
        user_query = select(User).where(User.chat_id == message.from_user.id)
        user = (await session.execute(user_query)).scalar()

        if not user or not user.phone:
            await message.answer("⚠️ Avval ro'yxatdan o'ting: /start")
            return

        # User telefoniga bog'langan kartalarni topish
        cards_query = select(Card).where(Card.phone == user.phone)
        result = await session.execute(cards_query)
        cards = result.scalars().all()

    if cards:
        txt = "💳 <b>Sizning kartalaringiz:</b>\n\n"
        for i, card in enumerate(cards, 1):
            # Karta raqamini yashirish (masalan: 8600 **** **** 1234)
            c_num = card.card_number
            hidden_num = f"{c_num[:4]} **** **** {c_num[-4:]}"
            
            txt += (f"{i}. 🆔 <b>{hidden_num}</b>\n"
                    f"💰 Balans: <code>{card.balance:,}</code> UZS\n"
                    f"🟢 Status: {card.status}\n"
                    f"----------------------------\n")
        
        txt += "\n<i>Simulyatsiya uchun: /pay_in yoki /pay_out</i>"
        await message.answer(txt, parse_mode="HTML")
    else:
        await message.answer("❌ Sizda hali karta ulanmagan.")

# --- PRAKTIKA UCHUN SIMULYATSIYA KOMANDALARI ---

@menu_router.message(Command("pay_in", "pay_out"))
async def simulate_transaction(message: types.Message):
    is_income = message.text == "/pay_in"
    amount = 50000.0 if is_income else 20000.0
    
    async with async_session() as session:
        # Foydalanuvchining birinchi kartasini olamiz
        user_query = select(User).where(User.chat_id == message.from_user.id)
        user = (await session.execute(user_query)).scalar()
        
        if not user: return
        
        card_query = select(Card).where(Card.phone == user.phone).limit(1)
        card = (await session.execute(card_query)).scalar()
        
        if not card:
            await message.answer("Simulyatsiya uchun avval karta qo'shilgan bo'lishi kerak.")
            return

        # 1. Balansni o'zgartirish
        if is_income:
            card.balance += amount
            trans_type = "tushum"
        else:
            if card.balance < amount:
                await message.answer("Mablag' yetarli emas!")
                return
            card.balance -= amount
            trans_type = "yechildi"

        # 2. Transaction modeliga yozish
        new_trans = Transaction(card_id=card.id, amount=amount, type=trans_type)
        session.add(new_trans)
        
        current_balance = card.balance
        await session.commit()

    # 3. SMS Xabarnoma
    date_now = datetime.now().strftime("%d.%m.%Y %H:%M")
    status_icon = "📈" if is_income else "📉"
    prefix = "+" if is_income else "-"
    
    sms_text = (
        f"{status_icon} <b>Karta operatsiyasi</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Summa: <b>{prefix}{amount:,} UZS</b>\n"
        f"📅 Sana: {date_now}\n"
        f"💳 Balans: <b>{current_balance:,} UZS</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Muvaffaqiyatli bajarildi."
    )
    await message.answer(sms_text, parse_mode="HTML")

@menu_router.message(Command("help"))
async def help_command(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💻 Admin bilan bog'lanish", url=settings.ADMIN_CHAT_LINK)
    
    txt = (
        "❓ <b>Yordam bo'limi:</b>\n\n"
        "🔹 /start - Botni ishga tushirish\n"
        "🔹 /my_cards - Kartalar ro'yxati va balans\n"
        "🔹 /pay_in - +50,000 so'm (Simulyatsiya)\n"
        "🔹 /pay_out - -20,000 so'm (Simulyatsiya)\n\n"
        "Savollaringiz bo'lsa, adminga murojaat qiling."
    )
    await message.answer(txt, reply_markup=builder.as_markup(), parse_mode="HTML")
