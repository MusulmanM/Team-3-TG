import csv
from sqlalchemy import select
from db.engine import async_session
from db.models import Card

async def export_cards():
    async with async_session() as session:
        cards = (await session.execute(select(Card))).scalars().all()
        with open('export.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Number', 'Balance', 'Status'])
            for c in cards:
                writer.writerow([c.card_number, c.balance, c.status])
    print("Export done!")
