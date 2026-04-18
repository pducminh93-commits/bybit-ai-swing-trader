#!/usr/bin/env python3
"""
Check database status and ensure tables exist
"""
import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def check_database():
    """Check if database tables exist"""
    try:
        # Change to backend directory to match application working directory
        import os
        os.chdir('backend')

        from core.database.config import db
        from sqlalchemy import text

        # Check if we can connect
        async with db.async_session() as session:
            try:
                # Try to query the backtest_results table
                result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_results'"))
                table_exists = result.scalar() is not None

                if table_exists:
                    print("SUCCESS: Table 'backtest_results' exists")

                    # Check table structure
                    result = await session.execute(text("PRAGMA table_info(backtest_results)"))
                    columns = result.fetchall()
                    print(f"INFO: Table has {len(columns)} columns:")
                    for col in columns:
                        print(f"   - {col[1]} ({col[2]})")

                    # Check if there are any records
                    result = await session.execute(text("SELECT COUNT(*) FROM backtest_results"))
                    count = result.scalar()
                    print(f"INFO: Current records: {count}")

                else:
                    print("ERROR: Table 'backtest_results' does NOT exist")
                    print("INFO: Creating tables...")
                    await db.create_tables()
                    print("SUCCESS: Tables created successfully!")

            except Exception as e:
                print(f"ERROR: Database error: {e}")
                print("INFO: Attempting to create tables...")
                try:
                    await db.create_tables()
                    print("SUCCESS: Tables created successfully!")
                except Exception as create_error:
                    print(f"ERROR: Failed to create tables: {create_error}")

    except ImportError as e:
        print(f"ERROR: Import error: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())