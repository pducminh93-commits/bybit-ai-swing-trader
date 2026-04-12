#!/usr/bin/env python3
"""
Database initialization script for Bybit AI Swing Trader
Creates all database tables and sets up initial data
"""

import asyncio
import logging
from core.database.config import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Initialize database tables"""
    try:
        logger.info("Creating database tables...")
        await db.create_tables()
        logger.info("Database tables created successfully!")

        # Optional: Add some initial data or migrations here
        logger.info("Database initialization complete!")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_database())