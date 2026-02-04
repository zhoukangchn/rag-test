
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 请在下方填入你硬写的那个真实 URL
# URL = "mysql+aiomysql://user:pass@host:port/dbname"
# 由于我看不到你填的，我这里只能尝试读取环境变量
from src.app.core.config import settings
URL = settings.database_url

async def test_conn():
    print(f"Testing connection to: {URL}")
    try:
        engine = create_async_engine(URL, echo=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Result: {result.fetchone()}")
        await engine.dispose()
    except Exception as e:
        print(f"!!! Error type: {type(e)}")
        print(f"!!! Error details: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conn())
