from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import AsyncGenerator
import os

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self):
        # Use SQLite for development, PostgreSQL for production
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bybit_trader.db")

        self.engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for debugging
            pool_pre_ping=True,
        )

        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """Create all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        async with self.async_session() as session:
            try:
                yield session
            finally:
                await session.close()

# Global database instance
db = DatabaseConfig()