from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.postgres_config import postgres_config

engine = create_engine(
    postgres_config.sync_url,
    pool_size=postgres_config.pool_size,
    max_overflow=postgres_config.max_overflow,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
