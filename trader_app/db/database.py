import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker


def normalize_database_url(url):
    if not url:
        return ""
    url = url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL") or "")

engine = create_engine(
    DATABASE_URL or "sqlite:///:memory:",
    pool_pre_ping=True,
    future=True,
)
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        future=True,
    )
)
Base = declarative_base()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
