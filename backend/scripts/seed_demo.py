#!/usr/bin/env python3
"""Manually seed demo data into the current database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db
from app.services.demo_seed import seed_demo_data

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        if seed_demo_data(db):
            print("Demo data seeded successfully.")
        else:
            print("Demo data already present or admin user missing — skipped.")
    finally:
        db.close()
