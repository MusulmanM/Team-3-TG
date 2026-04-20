from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    fullname: Mapped[str] = mapped_column(String(100), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default='uz')

class Card(Base):
    __tablename__ = 'cards'
    id: Mapped[int] = mapped_column(primary_key=True)
    card_number: Mapped[str] = mapped_column(String(30), unique=True)
    phone: Mapped[str] = mapped_column(String(30))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default='active')
    
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="card")

class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey('cards.id'))
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(20)) 
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    

    card: Mapped["Card"] = relationship(back_populates="transactions")
