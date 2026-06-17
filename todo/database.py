import asyncpg
from dotenv import load_dotenv
from todo.models import Settings

load_dotenv()
settings = Settings()

DATABASE_URL = settings.DATABASE_URL

async def get_db_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()