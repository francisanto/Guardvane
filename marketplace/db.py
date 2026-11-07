"""
Database Layer for Guardvane Marketplace.
Supports PostgreSQL (Supabase / local) with connection pooling and psycopg (v3),
with seamless fallback to SQLite for offline testing.
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("guardvane.marketplace.db")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "marketplace.db"


def _smart_row_factory(cursor):
    """Row factory enabling both dict-like and index-like access."""
    desc = cursor.description
    if desc is None:
        return lambda values: values

    col_map = {col.name: i for i, col in enumerate(desc)}
    
    class SmartRow(tuple):
        def __getitem__(self, key):
            if isinstance(key, str):
                return super().__getitem__(col_map[key])
            return super().__getitem__(key)

        def get(self, key, default=None):
            if key in col_map:
                return super().__getitem__(col_map[key])
            return default

        def keys(self):
            return col_map.keys()

    return lambda values: SmartRow(values)


class PgCursorWrapper:
    """Cursor wrapper that translates SQLite-style '?' placeholders into PostgreSQL '%s'."""
    def __init__(self, raw_cur):
        self._cur = raw_cur

    def execute(self, sql: str, params=None):
        pg_sql = sql.replace("?", "%s")
        if params is not None:
            if isinstance(params, (list, tuple)):
                self._cur.execute(pg_sql, params)
            else:
                self._cur.execute(pg_sql, (params,))
        else:
            self._cur.execute(pg_sql)
        return self

    def executemany(self, sql: str, seq_of_params):
        pg_sql = sql.replace("?", "%s")
        self._cur.executemany(pg_sql, seq_of_params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __iter__(self):
        return iter(self._cur)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class PgConnWrapper:
    """Connection wrapper for PostgreSQL providing SQLite-like interface."""
    def __init__(self, raw_conn):
        self._raw = raw_conn

    def cursor(self):
        return PgCursorWrapper(self._raw.cursor())

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()


class MarketplaceDB:
    """
    Database manager for Guardvane Marketplace.
    Uses PostgreSQL by default, with automatic fallback to SQLite.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.use_postgres = False
        self.pg_url = None
        self._detect_backend()

    def _detect_backend(self):
        """Attempts connection to PostgreSQL (Supabase), falling back to SQLite only if unreachable."""
        import psycopg
        urls_to_try = []
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            # Clean up psycopg scheme prefix if present
            clean = env_url
            if clean.startswith("postgresql+psycopg://"):
                clean = "postgresql://" + clean[len("postgresql+psycopg://"):]
            if "aws-0-ap-northeast-1.pooler.supabase.com" in clean and "hostaddr" not in clean:
                sep = "&" if "?" in clean else "?"
                clean = f"{clean}{sep}hostaddr=54.64.190.72"
            urls_to_try.append(clean)

        for url in urls_to_try:
            for attempt in range(2):
                try:
                    conn = psycopg.connect(url, connect_timeout=12)
                    self.use_postgres = True
                    self.pg_url = url
                    logger.info("MarketplaceDB successfully connected to Supabase PostgreSQL backend.")
                    self._init_postgres_db(conn)
                    conn.close()
                    return
                except Exception as e:
                    logger.warning(f"PostgreSQL connection attempt {attempt + 1} to Supabase skipped: {e}")

        logger.info("MarketplaceDB using SQLite fallback backend.")
        self.use_postgres = False
        self._init_sqlite_db()

    def _init_postgres_db(self, raw_conn):
        """Ensures supporting tables exist and platform agents are present. Does not insert demo customers."""
        try:
            wrapped = PgConnWrapper(raw_conn)
            with wrapped:
                self._ensure_supporting_tables(wrapped)
                self._ensure_optional_columns(wrapped)
                self._ensure_platform_agents(wrapped)
        except Exception as e:
            logger.warning(f"Failed to initialize PostgreSQL marketplace data: {e}")

    def _get_connection(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            if self.use_postgres:
                import psycopg
                raw_conn = psycopg.connect(
                    self.pg_url,
                    row_factory=_smart_row_factory,
                    autocommit=False
                )
                self._local.conn = PgConnWrapper(raw_conn)
            else:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                self._local.conn = conn
        return self._local.conn

    def _init_sqlite_db(self):
        """
        Creates SQLite tables if they do not exist, and seeds initial demo data if empty.
        """
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        with conn:

            conn.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                title TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                description TEXT NOT NULL,
                avatar_url TEXT,
                skills TEXT NOT NULL,
                categories TEXT NOT NULL,
                wallet_address TEXT,
                portfolio_url TEXT,
                endpoint_url TEXT,
                io_format TEXT,
                x402_supported INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'available',
                verified INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'published',
                reputation_metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                estimated_delivery TEXT NOT NULL,
                supported_tasks TEXT NOT NULL,
                execution_type TEXT NOT NULL DEFAULT 'manual',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                service_id TEXT NOT NULL,
                service_title TEXT NOT NULL,
                service_category TEXT NOT NULL,
                prompt_content TEXT NOT NULL,
                requirements TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL,
                execution_type TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                report_id TEXT,
                deliverable_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (provider_id) REFERENCES providers (id),
                FOREIGN KEY (service_id) REFERENCES services (id)
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                service_title TEXT NOT NULL,
                summary TEXT NOT NULL,
                findings TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                hardened_prompt TEXT,
                swarm_reference TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            );

            CREATE TABLE IF NOT EXISTS saved_prompts (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                analysis_result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS arkiv_records (
                entity_key TEXT PRIMARY KEY,
                schema_tag TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                owner_wallet TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_arkiv_records_schema_entity ON arkiv_records(schema_tag, entity_id);
            CREATE INDEX IF NOT EXISTS ix_arkiv_records_owner ON arkiv_records(owner_wallet);
            """)

        self._ensure_supporting_tables(conn)
        self._ensure_optional_columns(conn)
        self._ensure_platform_agents(conn)
        conn.commit()

    def _ensure_supporting_tables(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS arkiv_records (
                entity_key TEXT PRIMARY KEY,
                schema_tag TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                owner_wallet TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_intents (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL,
                gateway TEXT NOT NULL,
                external_reference TEXT,
                failure_reason TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                verified_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_payment_intents_order ON payment_intents(order_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_attachments (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT,
                storage_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_request_attachments_order ON request_attachments(order_id)")

    def _ensure_optional_columns(self, conn):
        additions = {
            "providers": [
                ("is_platform_managed", "INTEGER NOT NULL DEFAULT 0"),
                ("updated_at", "TEXT"),
            ],
            "orders": [
                ("rejection_reason", "TEXT"),
                ("payment_intent_id", "TEXT"),
                ("payment_type", "TEXT"),
                ("escrow_tx_hash", "TEXT"),
                ("escrow_release_tx_hash", "TEXT"),
                ("escrow_state", "TEXT"),
                ("token_usage", "TEXT"),
            ],
        }
        for table, cols in additions.items():
            existing = self._table_columns(conn, table)
            if existing is None:
                continue
            for name, decl in cols:
                if name not in existing:
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
                    except Exception as exc:
                        logger.debug(f"Column {table}.{name} not added: {exc}")

    def _table_columns(self, conn, table: str):
        cursor = conn.cursor()
        try:
            if self.use_postgres:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
                    (table,),
                )
                return {row[0] for row in cursor.fetchall()}
            cursor.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cursor.fetchall()}
        except Exception:
            return None

    def _ensure_platform_agents(self, conn):
        """
        Upserts the two Guardvane-managed agents. Does not insert fake wallets,
        ratings, customer orders, or demo prompts.
        """
        from marketplace.platform_agents import PLATFORM_AGENTS

        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()
        for agent in PLATFORM_AGENTS:
            reputation = json.dumps({
                "platform_managed": True,
                "audits_completed": 0,
                "source": "guardvane_platform",
            })
            cursor.execute("SELECT id FROM providers WHERE id = ?", (agent["id"],))
            exists = cursor.fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE providers SET
                        display_name = ?, title = ?, provider_type = ?, description = ?,
                        skills = ?, categories = ?, wallet_address = NULL,
                        portfolio_url = NULL, endpoint_url = NULL,
                        io_format = ?, x402_supported = 0, availability = 'available',
                        verified = 0, status = 'published', reputation_metadata = ?,
                        is_platform_managed = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        agent["display_name"],
                        agent["title"],
                        agent["provider_type"],
                        agent["description"],
                        json.dumps(agent["skills"]),
                        json.dumps(agent["categories"]),
                        "JSON / Prompt-in, analysis-out",
                        reputation,
                        now,
                        agent["id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO providers (
                        id, display_name, title, provider_type, description, avatar_url,
                        skills, categories, wallet_address, portfolio_url, endpoint_url,
                        io_format, x402_supported, availability, verified, status,
                        reputation_metadata, created_at, is_platform_managed, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent["id"],
                        agent["display_name"],
                        agent["title"],
                        agent["provider_type"],
                        agent["description"],
                        None,
                        json.dumps(agent["skills"]),
                        json.dumps(agent["categories"]),
                        None,
                        None,
                        None,
                        "JSON / Prompt-in, analysis-out",
                        0,
                        "available",
                        0,
                        "published",
                        reputation,
                        now,
                        1,
                        now,
                    ),
                )

            for service in agent["services"]:
                cursor.execute("SELECT id FROM services WHERE id = ?", (service["id"],))
                srv_exists = cursor.fetchone()
                if srv_exists:
                    conn.execute(
                        """
                        UPDATE services SET
                            provider_id = ?, title = ?, description = ?, category = ?,
                            price = ?, currency = 'USD', estimated_delivery = ?,
                            supported_tasks = ?, execution_type = 'automated', is_active = 1
                        WHERE id = ?
                        """,
                        (
                            agent["id"],
                            service["title"],
                            service["description"],
                            service["category"],
                            service["price"],
                            service["estimated_delivery"],
                            json.dumps([service["category"]]),
                            service["id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO services (
                            id, provider_id, title, description, category, price,
                            currency, estimated_delivery, supported_tasks, execution_type,
                            is_active, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            service["id"],
                            agent["id"],
                            service["title"],
                            service["description"],
                            service["category"],
                            service["price"],
                            "USD",
                            service["estimated_delivery"],
                            json.dumps([service["category"]]),
                            "automated",
                            1,
                            now,
                        ),
                    )
        logger.info("Platform-managed agents ensured (0G Defence Agent, Prompt Guard Agent).")


db = MarketplaceDB()

