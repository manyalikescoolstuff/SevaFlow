"""List/clean an explicitly named schema left by an interrupted browser fixture."""
import asyncio
import re
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as db:
            if len(sys.argv) == 1:
                names = (await db.execute(text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'test_customer_browser_%'"))).scalars().all()
                print('\n'.join(names) or 'No browser fixture schemas remain.')
            else:
                schema = sys.argv[1]
                if not re.fullmatch(r'test_customer_browser_[a-f0-9]{32}', schema):
                    raise ValueError('Not a generated browser fixture schema')
                await db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                print('Removed isolated browser fixture schema.')
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
