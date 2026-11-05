"""
Database Connection and Engine Setup for Guardvane.
Supports PostgreSQL (Supabase / local) via psycopg (v3) with connection pooling and pre-ping.
"""

import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger("guardvane.db")

Base = declarative_base()


def get_database_url() -> str:
    """
    Retrieves and standardizes the database connection URL from environment.
    Ensures 'postgresql+psycopg://' scheme is used for psycopg v3 compatibility.
    Defaults to local PostgreSQL if not specified.
    """
    raw_url = os.getenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/guardvane")
    
    # Standardize scheme for SQLAlchemy + psycopg 3
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url[len("postgresql://"):]
    elif raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url[len("postgres://"):]
    return raw_url


DATABASE_URL = get_database_url()

# Connection pooling configuration
# pool_pre_ping checks connectivity before handing out connections from the pool
# pool_recycle prevents stale connections in hosted cloud environments (e.g. Supabase, AWS)
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 5} if "postgresql" in DATABASE_URL else {}
    )
    # Quick probe
    with engine.connect() as probe:
        logger.info("Successfully established connection with configured DATABASE_URL.")
except Exception as e:
    logger.warning(
        f"Unable to connect to primary DATABASE_URL ({e}). "
        "Falling back to local PostgreSQL (localhost:5432/guardvane)..."
    )
    FALLBACK_URL = "postgresql+psycopg://localhost:5432/guardvane"
    DATABASE_URL = FALLBACK_URL
    engine = create_engine(
        FALLBACK_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields an independent database session per request.
    Ensures safe cleanup and rollback on exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

