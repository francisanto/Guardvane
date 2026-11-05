"""
Database Connection and Engine Setup for Guardvane.
Supports PostgreSQL (Supabase Session Pooler / local) via psycopg (v3)
with connection pooling, pre-ping, health checks, and strict configuration enforcement.
"""

import os
import time
import logging
from typing import Any, Dict
from urllib.parse import urlparse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger("guardvane.db")

Base = declarative_base()


def get_database_url() -> str:
    """
    Retrieves and standardizes the database connection URL from environment.
    Ensures 'postgresql+psycopg://' scheme is used for psycopg v3 compatibility.
    Never silently invents remote credentials.
    """
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        # Explicit local fallback only when DATABASE_URL is completely unset
        logger.info("DATABASE_URL not set; using local development default: postgresql+psycopg://localhost:5432/guardvane")
        return "postgresql+psycopg://localhost:5432/guardvane"

    raw_url = raw_url.strip()

    # Standardize scheme for SQLAlchemy + psycopg 3
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url[len("postgresql://"):]
    elif raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url[len("postgres://"):]
    return raw_url


DATABASE_URL = get_database_url()


def get_safe_db_info(url: str) -> Dict[str, Any]:
    """
    Extracts sanitized connection metadata without exposing passwords or credentials.
    """
    try:
        clean = url.replace("postgresql+psycopg://", "http://").replace("postgres://", "http://").replace("postgresql://", "http://")
        parsed = urlparse(clean)
        return {
            "host": parsed.hostname or "unknown",
            "port": parsed.port or 5432,
            "database": (parsed.path or "").lstrip("/") or "postgres",
            "user": parsed.username or "postgres",
            "is_pooler": "pooler.supabase.com" in (parsed.hostname or ""),
            "is_local": parsed.hostname in ("localhost", "127.0.0.1", "::1", None)
        }
    except Exception:
        return {
            "host": "unknown",
            "port": 5432,
            "database": "unknown",
            "user": "unknown",
            "is_pooler": False,
            "is_local": False
        }


SAFE_DB_INFO = get_safe_db_info(DATABASE_URL)

# Configure SQLAlchemy engine with psycopg v3
# Hosted poolers (e.g. Supabase PgBouncer) require appropriate recycle and timeout settings
connect_args = {"connect_timeout": 8}
if not SAFE_DB_INFO["is_local"]:
    connect_args["sslmode"] = "require"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args
)

# Initial probe for startup logging (NO silent fallback to localhost)
try:
    with engine.connect() as probe:
        probe.execute(text("SELECT 1;"))
        logger.info(
            "Database connection established successfully to %s:%s/%s (user: %s)",
            SAFE_DB_INFO["host"], SAFE_DB_INFO["port"], SAFE_DB_INFO["database"], SAFE_DB_INFO["user"]
        )
except Exception as exc:
    logger.error(
        "DATABASE CONNECTION FAILED: Unable to connect to configured %s (%s:%s/%s). Error: %s",
        "Supabase Pooler" if SAFE_DB_INFO["is_pooler"] else "Database",
        SAFE_DB_INFO["host"], SAFE_DB_INFO["port"], SAFE_DB_INFO["database"],
        str(exc).splitlines()[0] if str(exc) else "Connection failed"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db_health() -> Dict[str, Any]:
    """
    Executes a lightweight query (SELECT 1) against the configured database.
    Confirms reachability, measures latency, and reports safe diagnostics.
    Never exposes passwords, tokens, or credentials.
    """
    start_time = time.perf_counter()
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1;")).scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            db_name = conn.execute(text("SELECT current_database();")).scalar()
            return {
                "status": "healthy" if res == 1 else "unexpected_result",
                "database_reachable": True,
                "latency_ms": latency_ms,
                "host": SAFE_DB_INFO["host"],
                "port": SAFE_DB_INFO["port"],
                "database": db_name or SAFE_DB_INFO["database"],
                "is_pooler": SAFE_DB_INFO["is_pooler"],
                "driver": "postgresql+psycopg (v3)",
                "error": None
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_str = str(exc)
        
        # Categorize error without leaking sensitive tokens
        if "password authentication failed" in err_str:
            category = "authentication_failure"
            detail = "Password authentication failed for configured database user."
        elif "nodename nor servname provided" in err_str or "Name or service not known" in err_str:
            category = "dns_resolution_failure"
            detail = "DNS resolution failed for database hostname."
        elif "connection timed out" in err_str.lower():
            category = "connection_timeout"
            detail = "TCP connection to database server timed out."
        elif "Connection refused" in err_str:
            category = "connection_refused"
            detail = "Database server port refused TCP connection."
        elif "too many authentication failures" in err_str:
            category = "circuit_breaker_rate_limit"
            detail = "Connection blocked by database pooler due to previous authentication failures."
        else:
            category = "connection_error"
            detail = err_str.splitlines()[0] if err_str else "Unknown connection error."

        return {
            "status": "unhealthy",
            "database_reachable": False,
            "latency_ms": latency_ms,
            "host": SAFE_DB_INFO["host"],
            "port": SAFE_DB_INFO["port"],
            "database": SAFE_DB_INFO["database"],
            "is_pooler": SAFE_DB_INFO["is_pooler"],
            "driver": "postgresql+psycopg (v3)",
            "failure_category": category,
            "error": detail
        }


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


