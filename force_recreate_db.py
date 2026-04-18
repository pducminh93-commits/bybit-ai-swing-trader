#!/usr/bin/env python3
"""
Force recreate database by deleting file first
"""
import os
import asyncio
from core.database.config import db

async def force_recreate_database():
    """Force drop and recreate database"""
    db_path = "./backend/bybit_trader.db"

    # Force delete the file
    if os.path.exists(db_path):
        print(f"Removing database file: {db_path}")
        try:
            os.remove(db_path)
            print("Database file removed successfully")
        except Exception as e:
            print(f"Failed to remove database file: {e}")
            return

    print("Creating new database tables...")
    try:
        await db.create_tables()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Failed to create tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(force_recreate_database())