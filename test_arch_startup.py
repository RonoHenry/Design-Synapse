"""Test architectural-service startup."""
import asyncio
import os
import sys

# Change to service directory first
os.chdir("apps/architectural-service")
sys.path.insert(0, ".")

# On Windows, use SelectorEventLoop for asyncmy SSL compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def test_db():
    try:
        import sqlalchemy
        from src.core.database import engine

        async with engine.connect() as conn:
            result = await conn.execute(sqlalchemy.text("SELECT 1"))
            print("DB connection OK:", result.fetchone())
    except Exception as e:
        import traceback

        print("DB connection FAILED:")
        traceback.print_exc()


asyncio.run(test_db())
print("Done")
