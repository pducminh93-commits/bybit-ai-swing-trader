#!/usr/bin/env python3
"""
Force recreate database script
"""
import os
import asyncio
from core.database.config import db

async def recreate_database():
    """Drop and recreate database"""
    db_path = "./bybit_trader.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    print("Creating new database tables...")
    await db.create_tables()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(recreate_database())