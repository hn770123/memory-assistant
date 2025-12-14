from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import json

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Models

class UserProfile(Base):
    __tablename__ = "user_profile"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String)  # 'personality', 'skill', 'preference'
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    deadline: Mapped[Optional[datetime]] = mapped_column(Date)
    priority: Mapped[Optional[str]] = mapped_column(String) # 'low', 'medium', 'high'
    status: Mapped[str] = mapped_column(String, default='active') # 'active', 'completed', 'archived'
    progress: Mapped[int] = mapped_column(Integer, default=0) # 0-100
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(Date, unique=True)
    summary: Mapped[str] = mapped_column(Text)
    key_events: Mapped[Optional[str]] = mapped_column(Text) # JSON format
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def set_key_events(self, events: dict | list):
        self.key_events = json.dumps(events)

    def get_key_events(self):
        if self.key_events:
            return json.loads(self.key_events)
        return None

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    consolidated: Mapped[bool] = mapped_column(Boolean, default=False)
    importance_score: Mapped[Optional[float]] = mapped_column(Float) # 0.0-1.0

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(DateTime)
    recurrence: Mapped[Optional[str]] = mapped_column(String) # 'daily', 'weekly', 'monthly', null
    status: Mapped[str] = mapped_column(String, default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
