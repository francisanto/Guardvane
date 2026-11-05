"""
Migration Script: Transfer existing SQLite marketplace data to PostgreSQL.
Ensures zero data loss and idempotent execution.
"""

import json
import logging
import sqlite3
from pathlib import Path
from sqlalchemy.orm import Session

from db.database import SessionLocal, engine
from db.models import Order, Provider, Report, SavedPrompt, Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_sqlite_to_pg")

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "marketplace.db"


def migrate_data():
    if not SQLITE_PATH.exists():
        logger.warning(f"SQLite file not found at {SQLITE_PATH}. Nothing to migrate.")
        return

    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    db: Session = SessionLocal()
    try:
        # 1. Providers
        cursor.execute("SELECT * FROM providers")
        providers = cursor.fetchall()
        prov_migrated = 0
        for p in providers:
            p_dict = dict(p)
            existing = db.query(Provider).filter_by(id=p_dict["id"]).first()
            if not existing:
                db.add(Provider(**p_dict))
                prov_migrated += 1
        db.commit()
        logger.info(f"Providers: {prov_migrated} inserted (out of {len(providers)} total).")

        # 2. Services
        cursor.execute("SELECT * FROM services")
        services = cursor.fetchall()
        srv_migrated = 0
        for s in services:
            s_dict = dict(s)
            existing = db.query(Service).filter_by(id=s_dict["id"]).first()
            if not existing:
                db.add(Service(**s_dict))
                srv_migrated += 1
        db.commit()
        logger.info(f"Services: {srv_migrated} inserted (out of {len(services)} total).")

        # 3. Orders
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()
        ord_migrated = 0
        for o in orders:
            o_dict = dict(o)
            existing = db.query(Order).filter_by(id=o_dict["id"]).first()
            if not existing:
                db.add(Order(**o_dict))
                ord_migrated += 1
        db.commit()
        logger.info(f"Orders: {ord_migrated} inserted (out of {len(orders)} total).")

        # 4. Reports
        cursor.execute("SELECT * FROM reports")
        reports = cursor.fetchall()
        rep_migrated = 0
        for r in reports:
            r_dict = dict(r)
            existing = db.query(Report).filter_by(id=r_dict["id"]).first()
            if not existing:
                db.add(Report(**r_dict))
                rep_migrated += 1
        db.commit()
        logger.info(f"Reports: {rep_migrated} inserted (out of {len(reports)} total).")

        # 5. Saved Prompts
        cursor.execute("SELECT * FROM saved_prompts")
        prompts = cursor.fetchall()
        prm_migrated = 0
        for pr in prompts:
            pr_dict = dict(pr)
            existing = db.query(SavedPrompt).filter_by(id=pr_dict["id"]).first()
            if not existing:
                db.add(SavedPrompt(**pr_dict))
                prm_migrated += 1
        db.commit()
        logger.info(f"Saved Prompts: {prm_migrated} inserted (out of {len(prompts)} total).")

        print("Migration from SQLite to PostgreSQL completed successfully!")

    except Exception as e:
        db.rollback()
        logger.error(f"Migration error: {e}", exc_info=True)
        raise
    finally:
        db.close()
        sqlite_conn.close()


if __name__ == "__main__":
    migrate_data()

