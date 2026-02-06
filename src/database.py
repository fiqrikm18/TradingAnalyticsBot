import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

# Load Env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# If no DB URL is set, we warn but don't crash immediately (screener can still run text-only)
if not DATABASE_URL:
    logging.warning(
        "⚠️ DATABASE_URL not found in .env. Database features will be disabled.")

Base = declarative_base()

# --- MODELS ---


class Stock(Base):
    __tablename__ = 'stocks'

    ticker = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)

    results = relationship("ScreenerResult", back_populates="stock")
    prices = relationship("DailyPrice", back_populates="stock")


class DailyPrice(Base):
    __tablename__ = 'daily_prices'

    # TimescaleDB Hypertable
    # Note: No primary key on ID because TimescaleDB partitions by time

    time = Column(DateTime, nullable=False, primary_key=True)
    ticker = Column(String, ForeignKey('stocks.ticker'),
                    nullable=False, primary_key=True)

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

    stock = relationship("Stock", back_populates="prices")


class ScreenerResult(Base):
    __tablename__ = 'screener_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_date = Column(DateTime, default=datetime.now)
    ticker = Column(String, ForeignKey('stocks.ticker'))

    score = Column(Float)  # AI Confidence
    phase = Column(String)  # e.g., "Accumulation"

    # Technicals
    volatility = Column(Float)
    dist_from_low = Column(Float)

    # Status (For future use/backtesting)
    status = Column(String, default="NEW")  # NEW, TP_HIT, SL_HIT, INVALID

    stock = relationship("Stock", back_populates="results")

# --- ENGINE ---


engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        logging.error(f"Failed to create DB engine: {e}")


def get_db():
    if SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        yield None
