from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class User(Base):
   __tablename__ = 'users'

   id: Mapped[int] = mapped_column(primary_key=True)
   tg_id = mapped_column(BigInteger, unique=True)
   username: Mapped[str] = mapped_column(String(150))

   categories = relationship('Category', back_populates = 'user', cascade = "all, delete-orphan")
   transactions = relationship('Transaction', back_populates = 'user', cascade= "all, delete-orphan")
   limits = relationship('Limit', back_populates= 'user', cascade="all, delete-orphan")
   settings = relationship('Setting', back_populates='user', cascade="all, delete-orphan")
   

class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(150))
    is_deleted = mapped_column(Boolean, default=False)
    deleted_at = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='categories')
    transactions = relationship('Transaction', back_populates='category', cascade="all, delete-orphan")
    limits = relationship('Limit', back_populates='category', cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    currency_id: Mapped[int] = mapped_column(ForeignKey('currencies.id'))
    amount = mapped_column(Numeric(10, 2))
    is_expense = mapped_column(Boolean, default= True)
    comment = mapped_column(Text)

    user = relationship('User', back_populates='transactions')
    category = relationship('Category', back_populates='transactions')

class Limit(Base):
    __tablename__ = 'limits'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    currency_id: Mapped[int] = mapped_column(ForeignKey('currencies.id'))
    limit_amount = mapped_column(Numeric)
    period = mapped_column(Text)
    is_updating = mapped_column(Boolean, default = False)
    start_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='limits')
    category = relationship('Category', back_populates='limits')
    #currency = relationship('Currency', back_populates = 'limits', cascade = "all, delete-orphan")

class Setting(Base):
    __tablename__ = 'settings'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    currency_id: Mapped[int] = mapped_column(ForeignKey('currencies.id'))

    user = relationship('User', back_populates='settings')
    #currency = relationship('Currency', back_populates = 'currencies', cascade = "all, delete-orphan")


class Currency(Base):
    __tablename__ =  'currencies'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    rate_to_base: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=True)

    #limits = relationship('Limit', back_populates='currency', cascade="all, delete-orphan")
