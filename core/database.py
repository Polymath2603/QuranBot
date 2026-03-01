"""
database.py — SQLAlchemy models and session management for QBot.
"""
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from config import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "qbot.db"

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    telegram_id   = Column(Integer, unique=True, nullable=False)
    language      = Column(String, default="ar")
    voice         = Column(String, default="Alafasy_64kbps")
    tafsir_source = Column(String, default="muyassar")
    preferences   = Column(JSON, default=lambda: {"text_format": "msg"})
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_preference(self, key: str, value) -> None:
        prefs = dict(self.preferences) if self.preferences else {}
        prefs[key] = value
        self.preferences = prefs

    def get_preference(self, key: str, default=None):
        return self.preferences.get(key, default) if self.preferences else default


class TafsirCache(Base):
    """Persistent cache for tafsir API responses."""
    __tablename__ = "tafsir_cache"

    id         = Column(Integer, primary_key=True)
    cache_key  = Column(String, unique=True, nullable=False, index=True)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BotStats(Base):
    """Singleton row (id=1) accumulating lifetime bot statistics."""
    __tablename__ = "bot_stats"

    id                      = Column(Integer, primary_key=True, default=1)
    generated_audio         = Column(Integer, default=0)   # total MP3s generated
    generated_video         = Column(Integer, default=0)   # total MP4s generated
    hadiths_sent_personal   = Column(Integer, default=0)   # /hadith command uses
    hadiths_sent_channel    = Column(Integer, default=0)   # /chadith command uses
    stars_donations         = Column(Integer, default=0)   # successful Stars payments


def get_stats(session) -> "BotStats":
    """Fetch (or create) the singleton stats row."""
    row = session.query(BotStats).filter_by(id=1).first()
    if not row:
        row = BotStats(id=1)
        session.add(row)
        session.commit()
    return row


def increment_stat(field: str, amount: int = 1) -> None:
    """Atomically increment a BotStats counter field."""
    session = get_session()
    try:
        row = get_stats(session)
        setattr(row, field, (getattr(row, field) or 0) + amount)
        session.commit()
    finally:
        session.close()


engine  = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=engine)


def init_db() -> None:
    # Import queue model here to ensure its table is created
    from core.queue import QueueItem  # noqa: F401
    Base.metadata.create_all(engine)


def get_session():
    return Session()


# ---------------------------------------------------------------------------
# User helpers (moved from bot.py)
# ---------------------------------------------------------------------------

def get_db_user(telegram_user) -> User:
    """Fetch or create a User record for the given Telegram user."""
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_user.id).first()
    if not user:
        user = User(telegram_id=telegram_user.id, language="ar")
        session.add(user)
        session.commit()
    session.refresh(user)
    session.expunge(user)
    session.close()
    return user


def update_user_field(telegram_id: int, **fields) -> None:
    """Update one or more fields on a User record in a single session."""
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        for key, value in fields.items():
            setattr(user, key, value)
        session.commit()
    session.close()
