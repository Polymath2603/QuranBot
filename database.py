from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import json
from config import DATA_DIR

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "qbot.db"

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    language = Column(String, default="ar")
    voice = Column(String, default="Alafasy_64kbps")
    text_source = Column(String, default="uthmani")
    tafsir_source = Column(String, default="muyassar")
    preferences = Column(JSON, default=lambda: {"text_format": "msg"})  # msg, txt, lrc, srt, off
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def set_preference(self, key, value):
        prefs = dict(self.preferences) if self.preferences else {}
        prefs[key] = value
        self.preferences = prefs

    def get_preference(self, key, default=None):
        return self.preferences.get(key, default) if self.preferences else default

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session()
