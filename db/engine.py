from sqlalchemy import select
from .models import Card, Transaction

async def process_transaction(card_id: int, amount: float, trans_type: str):
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
