import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from .models import Base, Card, Transaction


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:

    DATABASE_URL = "sqlite+aiosqlite:///./bot.db"


engine = create_async_engine(DATABASE_URL)


async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def process_transaction(card_id: int, amount: float, trans_type: str):
    """
    Karta balansini o'zgartiradi va tranzaksiyalar tarixiga yozadi.
    """
    async with async_session() as session:
 
        result = await session.execute(select(Card).where(Card.id == card_id))
        card = result.scalar_one_or_none()
        
        if not card:
            return None, "Karta topilmadi"


        if trans_type == 'tushum':
            card.balance += amount
        elif trans_type == 'yechildi':
            if card.balance < amount:
                return None, "Mablag' yetarli emas"
            card.balance -= amount


        new_trans = Transaction(
            card_id=card.id, 
            amount=amount, 
            type=trans_type
        )
        session.add(new_trans)
        

        await session.commit()
        await session.refresh(card)
        
        return card.balance, "Muvaffaqiyatli"
