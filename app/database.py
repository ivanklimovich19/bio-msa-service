from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from app.config import get_settings

settings = get_settings()

# Для продакшена лучше asyncpg + SQLAlchemy 2.0 async, но для простоты sync
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # True для отладки SQL
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Создаёт таблицы при старте (для прототипа). В проде — Alembic."""
    Base.metadata.create_all(bind=engine)